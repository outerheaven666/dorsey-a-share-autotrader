from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from dorsey_as.adapters.validation import validate_provider_contract
from dorsey_as.audit import append_audit_record, new_run_id
from dorsey_as.backtest.engine import BacktestEngine
from dorsey_as.backtest.models import BacktestConfig as RuntimeBacktestConfig
from dorsey_as.broker.paper import PaperBroker
from dorsey_as.config.loader import DEFAULT_CONFIG_PATH, load_config
from dorsey_as.config.models import AppConfig
from dorsey_as.config.defaults import DEFAULT_OUTPUT_DIR, DEFAULT_SAMPLE_DATA_DIR
from dorsey_as.data.loaders import load_sample_data
from dorsey_as.data_source.local_csv import LocalCsvDataSource
from dorsey_as.data_source.schema import validate_csv_schema
from dorsey_as.data_quality.report import write_data_quality_report
from dorsey_as.data_quality.validators import run_data_quality_checks
from dorsey_as.factors.audit import write_factor_audit_log
from dorsey_as.engine.artifact_validation import RuntimeArtifactValidator
from dorsey_as.engine.runtime import RuntimeEngine
from dorsey_as.models import ScoreResult, TargetPortfolio
from dorsey_as.notify.summary import generate_notify_summary
from dorsey_as.point_in_time import build_point_in_time_snapshot
from dorsey_as.portfolio.constructor import build_target_portfolio
from dorsey_as.reporting.html import generate_backtest_html_report, generate_run_html_report
from dorsey_as.reporting.markdown import generate_backtest_report, generate_run_report
from dorsey_as.schema_migration.loader import load_migration_plan
from dorsey_as.schema_migration.report import write_schema_migration_report, write_schema_migration_summary
from dorsey_as.schema_migration.validator import build_compatibility_matrix, validate_migration_plan
from dorsey_as.schema_migration.visualization import generate_contract_diff_visualization
from dorsey_as.scoring import calculate_scores
from dorsey_as.scenarios.scenario_runner import RuntimeScenarioRunner
from dorsey_as.schema_versioning.diff import diff_contracts
from dorsey_as.schema_versioning.loader import load_provider_contract
from dorsey_as.schema_versioning.report import write_contract_diff_report, write_contract_diff_summary
from dorsey_as.safety.gates import PreLiveSafetyGate
from dorsey_as.safety.report import (
    write_pre_live_safety_report,
    write_pre_live_safety_summary,
    write_safety_explanation,
    write_simulated_live_request_report,
    write_simulated_live_request_summary,
)
from dorsey_as.system_health.checks import evaluate_system_health
from dorsey_as.system_health.release import build_release_checklist, build_release_notes_draft
from dorsey_as.system_health.report import (
    write_artifact_manifest,
    write_release_checklist,
    write_release_notes,
    write_sensitive_scan_report,
    write_sensitive_scan_summary,
    write_system_health_report,
    write_system_health_summary,
)
from dorsey_as.system_health.scanner import scan_sensitive_content


def _write_scores(path: Path, scores: list[ScoreResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "symbol",
                "quality_score",
                "moat_score",
                "valuation_score",
                "risk_score",
                "composite_score",
                "blocked",
                "reasons",
                "warnings",
            ],
        )
        writer.writeheader()
        for score in scores:
            writer.writerow(
                {
                    "symbol": score.symbol,
                    "quality_score": score.quality_score,
                    "moat_score": score.moat_score,
                    "valuation_score": score.valuation_score,
                    "risk_score": score.risk_score,
                    "composite_score": score.composite_score,
                    "blocked": score.blocked,
                    "reasons": ";".join(score.reasons),
                    "warnings": ";".join(score.warnings),
                }
            )


def _write_portfolio(path: Path, portfolio: TargetPortfolio) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["symbol", "name", "industry", "target_weight", "score"])
        writer.writeheader()
        for position in portfolio.positions:
            writer.writerow(
                {
                    "symbol": position.symbol,
                    "name": position.name,
                    "industry": position.industry,
                    "target_weight": position.target_weight,
                    "score": position.score,
                }
            )
        writer.writerow({"symbol": "CASH", "name": "Cash Reserve", "industry": "Cash", "target_weight": portfolio.cash_weight, "score": ""})


def _default_as_of_date(markets: dict) -> str:
    if not markets:
        return ""
    return max(market.trade_date for market in markets.values())


def _runtime_backtest_config(config: AppConfig, cash: float | None = None) -> RuntimeBacktestConfig:
    return RuntimeBacktestConfig(
        initial_cash=config.backtest.initial_cash if cash is None else cash,
        commission_rate=config.transaction_cost.commission_rate,
        minimum_commission=config.transaction_cost.minimum_commission,
        stamp_duty_rate=config.transaction_cost.stamp_duty_rate,
        slippage_rate=config.transaction_cost.slippage_rate,
        risk_free_rate=config.backtest.risk_free_rate,
    )


def _audit(
    output_dir: Path,
    config: AppConfig,
    *,
    run_id: str,
    stage: str,
    as_of_date: str = "",
    symbol: str = "",
    decision_type: str,
    decision: str,
    reason: str,
    input_summary: str = "",
    output_summary: str = "",
    severity: str = "info",
) -> None:
    if not config.audit.enabled:
        return
    append_audit_record(
        output_dir,
        stage=stage,
        as_of_date=as_of_date,
        symbol=symbol,
        decision_type=decision_type,
        decision=decision,
        reason=reason,
        input_summary=input_summary,
        output_summary=output_summary,
        severity=severity,
        run_id=run_id,
    )


def _evaluate_safety(output_dir: Path, config: AppConfig, run_id: str, command: str) -> None:
    if not config.pre_live_safety.enabled:
        return
    result = PreLiveSafetyGate(config, output_dir).evaluate()
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="pre_live_safety",
        decision_type="evaluate_safety_gate",
        decision="allow" if result.passed else "block",
        reason=f"command={command}, blocking={len(result.blocking_issues)}, warnings={len(result.warnings)}",
        severity="info" if result.passed else "error",
    )
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="execution_policy",
        decision_type={
            "research_only": "allow_research_only",
            "paper": "allow_paper_mode",
            "backtest": "allow_backtest_mode",
            "dry_run": "allow_dry_run_notify",
        }.get(config.execution_policy.mode, "evaluate_safety_gate"),
        decision=config.execution_policy.mode,
        reason=(
            f"live={config.execution_policy.allow_live_trading}, "
            f"broker={config.execution_policy.allow_real_broker}, "
            f"orders={config.execution_policy.allow_real_orders}, "
            f"network={config.execution_policy.allow_real_network_data}"
        ),
    )
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="safety_acknowledgement",
        decision_type="validate_safety_ack",
        decision="configured" if config.pre_live_safety.safety_ack_phrase else "missing",
        reason="manual acknowledgement phrase metadata checked",
        severity="info" if config.pre_live_safety.safety_ack_phrase else "error",
    )
    if result.blocking_issues:
        raise SystemExit(1)


def _load_checked_sample_data(data_dir: Path, output_dir: Path, config: AppConfig, as_of_date: str | None = None):
    if config.schema_validation.enabled:
        schema_report = validate_csv_schema(LocalCsvDataSource(config.data_source), config.schema_validation, output_dir)
        if not schema_report.passed:
            reasons = "; ".join(row.message for row in schema_report.rows if row.status == "fail")
            print(f"Schema validation failed: {reasons}")
            raise SystemExit(1)
    stocks, financials, markets = load_sample_data(data_dir)
    effective_as_of = as_of_date or config.point_in_time.as_of_date or _default_as_of_date(markets)
    pit = build_point_in_time_snapshot(financials, effective_as_of, config.point_in_time, output_dir)
    report = run_data_quality_checks(effective_as_of, stocks, financials, markets, data_quality_config=config.data_quality)
    write_data_quality_report(report, output_dir / "data_quality_report.csv")
    if not report.passed:
        reasons = "; ".join(issue.message for issue in report.blocking_issues)
        print(f"Data quality check failed for {effective_as_of}: {reasons}")
        raise SystemExit(1)
    return stocks, pit.visible_financials, markets, report


def _build_scores_and_portfolio(data_dir: Path, output_dir: Path, config: AppConfig, as_of_date: str | None = None) -> tuple[list[ScoreResult], TargetPortfolio, dict[str, float]]:
    stocks, financials, markets, _report = _load_checked_sample_data(data_dir, output_dir, config, as_of_date)
    scores = calculate_scores(stocks, financials, markets, scoring_config=config.scoring)
    portfolio = build_target_portfolio(scores, stocks, portfolio_config=config.portfolio)
    prices = {symbol: market.close_price for symbol, market in markets.items()}
    return scores, portfolio, prices


def check_data_quality(data_dir: Path, output_dir: Path, as_of_date: str | None = None, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    run_id = new_run_id("data-quality")
    stocks, financials, markets = load_sample_data(data_dir)
    effective_as_of = as_of_date or config.point_in_time.as_of_date or _default_as_of_date(markets)
    report = run_data_quality_checks(effective_as_of, stocks, financials, markets, data_quality_config=config.data_quality)
    output_path = output_dir / "data_quality_report.csv"
    write_data_quality_report(report, output_path)
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="data_quality",
        as_of_date=effective_as_of,
        decision_type="allow" if report.passed else "block",
        decision="check_data_quality",
        reason=f"blocking={len(report.blocking_issues)}, warnings={len(report.warnings)}",
        output_summary=str(output_path),
        severity="info" if report.passed else "error",
    )
    status = "passed" if report.passed else "failed"
    print(f"Data quality {status} for {effective_as_of}; wrote report to {output_path}")
    return output_path


def validate_schema(data_dir: Path, output_dir: Path, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    run_id = new_run_id("schema")
    report = validate_csv_schema(LocalCsvDataSource(config.data_source), config.schema_validation, output_dir)
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="schema_validation",
        decision_type="validate_schema",
        decision="pass" if report.passed else "block",
        reason=f"rows={len(report.rows)}",
        output_summary=str(output_dir / "schema_validation_report.csv"),
        severity="info" if report.passed else "error",
    )
    print(f"Schema validation {'passed' if report.passed else 'failed'}; wrote report to {output_dir / 'schema_validation_report.csv'}")
    if not report.passed:
        raise SystemExit(1)
    return output_dir / "schema_validation_report.csv"


def validate_provider_contract_cli(data_dir: Path, output_dir: Path, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    run_id = new_run_id("provider-contract")
    _evaluate_safety(output_dir, config, run_id, "validate-provider-contract")
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="provider_registry",
        decision_type="reject_network_access",
        decision="allow_mock_only",
        reason="adapter_contract.allow_network=false and allow_real_provider=false",
        input_summary=f"provider={config.adapter_contract.provider}, mode={config.adapter_contract.mode}",
    )
    report = validate_provider_contract(config, output_dir)
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="adapter_contract",
        decision_type="validate_provider_contract",
        decision="pass" if report.passed else "block",
        reason=f"provider={report.provider}, failures={sum(1 for row in report.rows if row.status == 'fail')}",
        output_summary=str(output_dir / "provider_contract_report.csv"),
        severity="info" if report.passed else "error",
    )
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="field_mapping",
        decision_type="map_fields",
        decision="write_adapter_mapped_preview",
        reason=f"mapped_rows={len(report.mapped_preview)}",
        output_summary=str(output_dir / "adapter_mapped_preview.csv"),
    )
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="mock_provider",
        decision_type="validate_provider_contract",
        decision="fixture_provider_only",
        reason="mock provider is used only for adapter contract testing",
        output_summary=str(output_dir / "provider_contract_summary.md"),
    )
    print(
        "Provider contract "
        f"{'passed' if report.passed else 'failed'}; "
        f"wrote report to {output_dir / 'provider_contract_report.csv'}"
    )
    if not report.passed and config.provider_tests.block_on_contract_failure:
        raise SystemExit(1)
    return output_dir / "provider_contract_report.csv"


def diff_provider_contract_cli(data_dir: Path, output_dir: Path, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    run_id = new_run_id("contract-diff")
    _evaluate_safety(output_dir, config, run_id, "diff-provider-contract")
    baseline = load_provider_contract(Path(config.schema_versioning.baseline_contract))
    candidate = load_provider_contract(Path(config.schema_versioning.candidate_contract))
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="schema_versioning",
        decision_type="load_schema_contract",
        decision="load_baseline_and_candidate",
        reason=f"current_version={config.schema_versioning.current_version}",
        input_summary=f"baseline={baseline.path}; candidate={candidate.path}",
    )
    report = diff_contracts(baseline, candidate, config.schema_versioning.block_on_breaking_change)
    report_path = write_contract_diff_report(report, output_dir)
    summary_path = write_contract_diff_summary(report, output_dir)
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="contract_diff",
        decision_type="diff_schema_contract",
        decision="block" if report.blocking_decision else "allow",
        reason=f"breaking={report.breaking_count}, additive={report.additive_count}, compatible={report.compatible_count}",
        output_summary=f"{report_path}; {summary_path}",
        severity="error" if report.blocking_decision else "info",
    )
    for row in report.rows:
        if row.breaking:
            _audit(
                output_dir,
                config,
                run_id=run_id,
                stage="contract_diff",
                decision_type="detect_breaking_change",
                decision=row.change_type,
                reason=row.message,
                input_summary=f"{row.dataset}.{row.field}",
                output_summary=f"{row.baseline_value}->{row.candidate_value}",
                severity="error",
            )
        elif row.change_type.startswith("additive"):
            _audit(
                output_dir,
                config,
                run_id=run_id,
                stage="contract_diff",
                decision_type="detect_additive_change",
                decision=row.change_type,
                reason=row.message,
                input_summary=f"{row.dataset}.{row.field}",
                output_summary=f"{row.baseline_value}->{row.candidate_value}",
                severity="warning",
            )
    if report.blocking_decision:
        _audit(
            output_dir,
            config,
            run_id=run_id,
            stage="contract_diff",
            decision_type="block_contract_change",
            decision="blocked",
            reason="breaking contract changes detected",
            output_summary=str(report_path),
            severity="error",
        )
    print(
        "Provider contract diff complete: "
        f"breaking={report.breaking_count}, additive={report.additive_count}; "
        f"wrote report to {report_path}"
    )
    if report.blocking_decision:
        raise SystemExit(1)
    return report_path


def validate_schema_migration_cli(data_dir: Path, output_dir: Path, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    run_id = new_run_id("schema-migration")
    _evaluate_safety(output_dir, config, run_id, "validate-schema-migration")
    plan_path = Path(config.schema_migration.migration_plan)
    if not plan_path.exists():
        print(f"Schema migration plan not found: {plan_path}")
        if config.schema_migration.block_on_missing_migration_plan:
            raise SystemExit(1)
    plan = load_migration_plan(plan_path)
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="schema_migration",
        decision_type="load_migration_plan",
        decision="load",
        reason=f"{plan.from_version}->{plan.to_version}",
        input_summary=str(plan_path),
    )
    report = validate_migration_plan(plan, config.schema_migration)
    report_path = write_schema_migration_report(report, output_dir)
    summary_path = write_schema_migration_summary(report, output_dir)
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="schema_migration",
        decision_type="validate_migration_plan",
        decision="block" if report.blocking_decision else "allow",
        reason=f"expired={report.expired_deprecation_count}, pending={report.pending_deprecation_count}",
        output_summary=f"{report_path}; {summary_path}",
        severity="error" if report.blocking_decision else "info",
    )
    for row in report.rows:
        if row.check_type == "expired_deprecation":
            _audit(
                output_dir,
                config,
                run_id=run_id,
                stage="field_lifecycle",
                decision_type="detect_expired_deprecation",
                decision=row.status,
                reason=row.message,
                input_summary=f"{row.dataset}.{row.field}",
                severity="error",
            )
        elif row.check_type == "pending_deprecation":
            _audit(
                output_dir,
                config,
                run_id=run_id,
                stage="field_lifecycle",
                decision_type="detect_pending_deprecation",
                decision=row.status,
                reason=row.message,
                input_summary=f"{row.dataset}.{row.field}",
                severity="warning",
            )
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="compatibility_matrix",
        decision_type="generate_compatibility_matrix",
        decision="generate",
        reason=f"rows={len(build_compatibility_matrix(plan))}",
        output_summary=str(summary_path),
    )
    print(
        "Schema migration validation complete: "
        f"blocking={report.blocking_decision}; wrote report to {report_path}"
    )
    if report.blocking_decision:
        _audit(
            output_dir,
            config,
            run_id=run_id,
            stage="schema_migration",
            decision_type="block_schema_migration",
            decision="blocked",
            reason="blocking migration issue detected",
            output_summary=str(report_path),
            severity="error",
        )
        raise SystemExit(1)
    return report_path


def generate_contract_diff_html_cli(data_dir: Path, output_dir: Path, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    run_id = new_run_id("contract-visualization")
    _evaluate_safety(output_dir, config, run_id, "generate-contract-diff-html")
    diff_path = output_dir / "provider_contract_diff_report.csv"
    if not diff_path.exists():
        diff_provider_contract_cli(data_dir, output_dir, config_path)
    plan = load_migration_plan(Path(config.schema_migration.migration_plan))
    migration_report = validate_migration_plan(plan, config.schema_migration)
    html_path, summary_path = generate_contract_diff_visualization(output_dir, config, plan, migration_report)
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="contract_visualization",
        decision_type="generate_contract_diff_html",
        decision="generate",
        reason="static local HTML visualization generated",
        output_summary=f"{html_path}; {summary_path}",
    )
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="compatibility_matrix",
        decision_type="generate_compatibility_matrix",
        decision="generate",
        reason=f"rows={len(build_compatibility_matrix(plan))}",
        output_summary=str(html_path),
    )
    print(f"Wrote contract diff visualization to {html_path} and {summary_path}")
    return html_path


def run_score(data_dir: Path, output_dir: Path, as_of_date: str | None = None, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    run_id = new_run_id("score")
    _evaluate_safety(output_dir, config, run_id, "run-score")
    stocks, financials, markets, _report = _load_checked_sample_data(data_dir, output_dir, config, as_of_date)
    scores = calculate_scores(stocks, financials, markets, scoring_config=config.scoring)
    output_path = output_dir / "scores.csv"
    _write_scores(output_path, scores)
    if config.factor_audit.enabled:
        write_factor_audit_log(scores, stocks, financials, markets, output_dir, config, as_of_date or _default_as_of_date(markets), run_id)
        _audit(
            output_dir,
            config,
            run_id=run_id,
            stage="factor_audit",
            as_of_date=as_of_date or _default_as_of_date(markets),
            decision_type="generate_factor_audit",
            decision="write_factor_audit_log",
            reason="factor_audit.enabled=true",
            output_summary=str(output_dir / "factor_audit_log.csv"),
        )
    generate_run_report(output_dir, config, config_path or DEFAULT_CONFIG_PATH)
    generate_run_html_report(output_dir, config, config_path or DEFAULT_CONFIG_PATH)
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="scoring",
        as_of_date=as_of_date or _default_as_of_date(markets),
        decision_type="score",
        decision="generate_scores",
        reason="configured composite scoring completed",
        input_summary=f"stocks={len(stocks)}",
        output_summary=f"scores={len(scores)}",
    )
    if config.audit.include_score_decisions:
        for score in scores[:10]:
            _audit(
                output_dir,
                config,
                run_id=run_id,
                stage="scoring",
                as_of_date=as_of_date or _default_as_of_date(markets),
                symbol=score.symbol,
                decision_type="score",
                decision="rank",
                reason="top score audit sample",
                input_summary="quality/moat/valuation/risk scores",
                output_summary=f"composite={score.composite_score}",
            )
    print(f"Wrote {len(scores)} scores to {output_path}")
    return output_path


def build_portfolio(data_dir: Path, output_dir: Path, as_of_date: str | None = None, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    run_id = new_run_id("portfolio")
    scores, portfolio, _prices = _build_scores_and_portfolio(data_dir, output_dir, config, as_of_date)
    _write_scores(output_dir / "scores.csv", scores)
    output_path = output_dir / "target_portfolio.csv"
    _write_portfolio(output_path, portfolio)
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="portfolio",
        decision_type="select",
        decision="build_target_portfolio",
        reason="configured portfolio constraints applied",
        input_summary=f"scores={len(scores)}",
        output_summary=f"positions={len(portfolio.positions)}",
    )
    print(f"Wrote {len(portfolio.positions)} target positions to {output_path}")
    return output_path


def paper_rebalance(data_dir: Path, output_dir: Path, cash: float | None, as_of_date: str | None = None, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    run_id = new_run_id("paper")
    scores, portfolio, prices = _build_scores_and_portfolio(data_dir, output_dir, config, as_of_date)
    _write_scores(output_dir / "scores.csv", scores)
    _write_portfolio(output_dir / "target_portfolio.csv", portfolio)
    broker = PaperBroker.from_state(
        output_dir / "paper_state.csv",
        output_dir / "paper_trades.csv",
        default_cash=config.backtest.initial_cash if cash is None else cash,
    )
    orders = broker.rebalance(portfolio, prices)
    broker.save_state(output_dir / "paper_state.csv")
    generate_run_report(output_dir, config, config_path or DEFAULT_CONFIG_PATH)
    generate_run_html_report(output_dir, config, config_path or DEFAULT_CONFIG_PATH)
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="paper_broker",
        decision_type="buy" if orders else "hold",
        decision="paper_rebalance",
        reason="paper broker simulation only",
        input_summary=f"target_positions={len(portfolio.positions)}",
        output_summary=f"orders={len(orders)}",
    )
    print(f"Simulated {len(orders)} paper orders; wrote trades to {output_dir / 'paper_trades.csv'}")
    return output_dir / "paper_trades.csv"


def run_backtest(data_dir: Path, output_dir: Path, cash: float | None = None, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    run_id = new_run_id("backtest")
    _evaluate_safety(output_dir, config, run_id, "run-backtest")
    engine = BacktestEngine.from_sample_data(
        data_dir=data_dir,
        output_dir=output_dir,
        config=_runtime_backtest_config(config, cash),
        scoring_config=config.scoring,
        portfolio_config=config.portfolio,
        data_quality_config=config.data_quality,
        point_in_time_config=config.point_in_time,
    )
    result = engine.run()
    generate_backtest_report(output_dir, config, config_path or DEFAULT_CONFIG_PATH)
    generate_backtest_html_report(output_dir, config, config_path or DEFAULT_CONFIG_PATH)
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="backtest",
        decision_type="generate_report",
        decision="run_backtest",
        reason="local backtest simulation completed",
        input_summary=f"initial_cash={engine.config.initial_cash}",
        output_summary=f"equity_points={len(result.equity_curve)}, trades={len(result.trades)}",
    )
    if config.audit.include_rejected_trades:
        for trade in result.trades:
            if trade.status == "SKIPPED":
                _audit(
                    output_dir,
                    config,
                    run_id=run_id,
                    stage="backtest",
                    as_of_date=trade.trade_date,
                    symbol=trade.symbol,
                    decision_type="reject",
                    decision=trade.side.lower(),
                    reason=trade.reason,
                    input_summary=f"quantity={trade.quantity}, price={trade.price}",
                    output_summary="status=SKIPPED",
                    severity="warning",
                )
    print(
        "Backtest complete: "
        f"{len(result.equity_curve)} equity points, "
        f"{len(result.trades)} trade records; "
        f"wrote outputs to {output_dir}"
    )
    return output_dir / "backtest_equity_curve.csv"


def explain_score(data_dir: Path, output_dir: Path, symbol: str, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    run_id = new_run_id("explain")
    _evaluate_safety(output_dir, config, run_id, "explain-score")
    scores_path = output_dir / "scores.csv"
    audit_path = output_dir / "factor_audit_log.csv"
    if not scores_path.exists() or not audit_path.exists():
        print("Missing scores.csv or factor_audit_log.csv; run run-score first.")
        raise SystemExit(1)
    with scores_path.open(newline="", encoding="utf-8-sig") as fh:
        scores = list(csv.DictReader(fh))
    with audit_path.open(newline="", encoding="utf-8-sig") as fh:
        audit_rows = [row for row in csv.DictReader(fh) if row.get("symbol") == symbol]
    score = next((row for row in scores if row.get("symbol") == symbol), None)
    if score is None:
        print(f"Symbol {symbol} not found in scores.csv")
        raise SystemExit(1)
    positives = sorted(audit_rows, key=lambda row: float(row.get("weighted_score") or 0), reverse=True)[:5]
    negatives = sorted(audit_rows, key=lambda row: float(row.get("weighted_score") or 0))[:5]
    red_flags = [row for row in audit_rows if row.get("factor_group") == "risk" and row.get("severity") == "error"]
    lines = [
        f"# Score Explanation: {symbol}",
        "",
        f"- Composite score: {score.get('composite_score', '')}",
        f"- Quality score: {score.get('quality_score', '')}",
        f"- Moat score: {score.get('moat_score', '')}",
        f"- Valuation score: {score.get('valuation_score', '')}",
        f"- Risk score: {score.get('risk_score', '')}",
        f"- Red flag blocked: {score.get('blocked', '')}",
        "",
        "## Top Positive Factors",
        "",
        *[f"- {row['factor_group']}.{row['factor_name']}: {row['weighted_score']} ({row['reason']})" for row in positives],
        "",
        "## Top Negative Factors",
        "",
        *[f"- {row['factor_group']}.{row['factor_name']}: {row['weighted_score']} ({row['reason']})" for row in negatives],
        "",
        "## Red Flag Reasons",
        "",
        *(["- None"] if not red_flags else [f"- {row['reason']}" for row in red_flags]),
        "",
        "## Valuation Explanation",
        "",
        *[f"- {row['factor_name']}: {row['reason']}" for row in audit_rows if row.get("factor_group") == "valuation"],
        "",
        "## Moat Proxy Explanation",
        "",
        *[f"- {row['factor_name']}: {row['reason']}" for row in audit_rows if row.get("factor_group") == "moat"],
        "",
        "## Safety Statement",
        "",
        "No real-money trading is supported. No real broker connection exists. No real network data source connection exists. This system is for personal research, system development, paper trading, and backtest simulation only. It does not provide investment advice and does not guarantee returns.",
    ]
    output_path = output_dir / f"explain_{symbol}.md"
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="explain_score",
        symbol=symbol,
        decision_type="explain_factor",
        decision="generate_explain_score",
        reason="single stock explanation requested",
        output_summary=str(output_path),
    )
    print(f"Wrote score explanation to {output_path}")
    return output_path


def explain_provider(data_dir: Path, output_dir: Path, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    run_id = new_run_id("provider-explain")
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Provider Explanation",
        "",
        f"- Current data_source.mode: {config.data_source.mode}",
        f"- Current data_source.provider: {config.data_source.provider}",
        f"- Current adapter_contract.mode: {config.adapter_contract.mode}",
        f"- Current adapter provider: {config.adapter_contract.provider}",
        f"- allow_network: {str(config.adapter_contract.allow_network).lower()}",
        f"- allow_real_provider: {str(config.adapter_contract.allow_real_provider).lower()}",
        f"- Current schema contract version: {config.schema_versioning.current_version}",
        f"- Baseline contract path: {config.schema_versioning.baseline_contract}",
        f"- Candidate contract path: {config.schema_versioning.candidate_contract}",
        f"- Contract diff enabled: {str(config.contract_diff.enabled).lower()}",
        f"- Real provider template enabled: {str(config.provider_templates.real_provider_templates_enabled).lower()}",
        f"- Schema migration enabled: {str(config.schema_migration.enabled).lower()}",
        f"- Migration current_version: {config.schema_migration.current_version}",
        f"- Migration target_version: {config.schema_migration.target_version}",
        f"- Migration plan path: {config.schema_migration.migration_plan}",
        f"- Compatibility window days: {config.schema_migration.compatibility_window_days}",
        f"- Contract diff HTML can be generated: {str(config.contract_visualization.generate_html).lower()}",
        f"- execution_policy.mode: {config.execution_policy.mode}",
        f"- Pre-live safety enabled: {str(config.pre_live_safety.enabled).lower()}",
        f"- allow_live_trading: {str(config.execution_policy.allow_live_trading).lower()}",
        f"- allow_real_broker: {str(config.execution_policy.allow_real_broker).lower()}",
        f"- allow_real_network_data: {str(config.execution_policy.allow_real_network_data).lower()}",
        f"- System health enabled: {str(config.system_health.enabled).lower()}",
        f"- Release checklist enabled: {str(config.release_checklist.enabled).lower()}",
        f"- Sensitive scan enabled: {str(config.sensitive_scan.enabled).lower()}",
        f"- Release version: {config.system_health.release_version}",
        "",
        "## Why There Is No Real Provider",
        "",
        "The current phase validates adapter contracts with local fake fixtures only. Mock provider data is used to test field mapping, schema compatibility, point-in-time compatibility, and failure reporting before any external integration is considered.",
        "",
        "## Future Provider Contract Requirements",
        "",
        "- Implement the DataProvider contract methods.",
        "- Provide stock basic, financial snapshot, market snapshot, historical market snapshot, and trading calendar datasets.",
        "- Map fields into the internal schema.",
        "- Normalize symbols, dates, numeric values, and boolean flags.",
        "- Provide disclosure_date for point-in-time financial data.",
        "- Pass schema validation, duplicate-key checks, and point-in-time checks.",
        "- Pass schema versioning and contract diff checks before any adapter can be considered.",
        "- Pass validate-provider-contract, diff-provider-contract, validate-schema-migration, generate-contract-diff-html, point-in-time checks, schema validation, and factor audit checks.",
        "- Pass the pre-live safety gate before any future real provider can be reviewed.",
        "- Pass system health, sensitive scan, and release checklist checks before a release candidate can be reviewed.",
        "- Keep network and real-provider paths disabled by default until a later explicitly approved milestone.",
        "",
        "## Field Deprecation Lifecycle",
        "",
        "Migration metadata tracks active, deprecated, pending_removal, and removed field states. Compatibility aliases are allowed only while documented and inside their validity window.",
        "",
        "## Disabled Provider Template",
        "",
        "The real provider template is disabled by default and non-executable. It is documentation-oriented scaffolding only, is not registered, and cannot be called by CLI commands.",
        "",
        "## Safety Statement",
        "",
        "No real-money trading is supported. No real broker connection exists. No real order path exists. No real network data source connection exists. Mock provider is only used for contract testing and is not an actual market data source. Real provider template is disabled-by-default and non-executable. Schema migration metadata is only for pre-integration checks and does not participate in trading decisions. Pre-live safety gate blocks live trading, real broker, real order, and real network data by default. This system is for personal research, system development, paper trading, and backtest simulation only. It does not provide investment advice and does not guarantee returns.",
    ]
    output_path = output_dir / "provider_explanation.md"
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="provider_template",
        decision_type="reject_real_provider_template",
        decision="explain_provider_boundary",
        reason="real providers are disabled; mock provider is contract-test only",
        output_summary=str(output_path),
    )
    print(f"Wrote provider explanation to {output_path}")
    return output_path


def generate_report(data_dir: Path, output_dir: Path, config_path: Path | None = None) -> tuple[Path, Path]:
    config = load_config(config_path)
    run_id = new_run_id("report")
    _evaluate_safety(output_dir, config, run_id, "generate-report")
    run_path = generate_run_report(output_dir, config, config_path or DEFAULT_CONFIG_PATH)
    backtest_path = generate_backtest_report(output_dir, config, config_path or DEFAULT_CONFIG_PATH)
    run_html = generate_run_html_report(output_dir, config, config_path or DEFAULT_CONFIG_PATH)
    backtest_html = generate_backtest_html_report(output_dir, config, config_path or DEFAULT_CONFIG_PATH)
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="reporting",
        decision_type="generate_report",
        decision="generate_markdown_and_html",
        reason="report command requested",
        output_summary=f"{run_path}; {backtest_path}; {run_html}; {backtest_html}",
    )
    print(f"Wrote reports to {run_path}, {backtest_path}, {run_html}, and {backtest_html}")
    return run_path, backtest_path


def notify_summary(data_dir: Path, output_dir: Path, config_path: Path | None = None) -> tuple[Path, Path]:
    config = load_config(config_path)
    run_id = new_run_id("notify")
    _evaluate_safety(output_dir, config, run_id, "notify-summary")
    payload_path, summary_path = generate_notify_summary(output_dir, config, config_path or DEFAULT_CONFIG_PATH)
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="notify",
        decision_type="dry_run_notify" if not config.notify.enabled else "generate_report",
        decision="write_notify_summary",
        reason="notify.enabled=false" if not config.notify.enabled else f"notify.mode={config.notify.mode}",
        output_summary=f"{payload_path}; {summary_path}",
    )
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="execution_policy",
        decision_type="allow_dry_run_notify",
        decision="allow" if config.execution_policy.allow_dry_run_notify else "block",
        reason="notify-summary remains dry-run only",
        output_summary=f"{payload_path}; {summary_path}",
    )
    print(f"Wrote notify dry-run summary to {payload_path} and {summary_path}")
    return payload_path, summary_path


def check_pre_live_safety(data_dir: Path, output_dir: Path, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    run_id = new_run_id("pre-live-safety")
    result = PreLiveSafetyGate(config, output_dir).evaluate()
    report_path = write_pre_live_safety_report(result, output_dir)
    summary_path = write_pre_live_safety_summary(result, config, output_dir)
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="pre_live_safety",
        decision_type="evaluate_safety_gate",
        decision="allow" if result.passed else "block",
        reason=f"blocking={len(result.blocking_issues)}, warnings={len(result.warnings)}",
        output_summary=f"{report_path}; {summary_path}",
        severity="info" if result.passed else "error",
    )
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="execution_policy",
        decision_type="allow_research_only" if config.execution_policy.mode == "research_only" else "evaluate_safety_gate",
        decision=config.execution_policy.mode,
        reason="pre-live safety check requested",
    )
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="safety_acknowledgement",
        decision_type="validate_safety_ack",
        decision="configured" if config.pre_live_safety.safety_ack_phrase else "missing",
        reason="manual acknowledgement phrase metadata checked",
        severity="info" if config.pre_live_safety.safety_ack_phrase else "error",
    )
    print(f"Pre-live safety check complete: blocking={len(result.blocking_issues)}; wrote report to {report_path}")
    if result.blocking_issues:
        raise SystemExit(1)
    return report_path


def explain_safety(data_dir: Path, output_dir: Path, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    run_id = new_run_id("safety-explain")
    output_path = write_safety_explanation(config, output_dir)
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="pre_live_safety",
        decision_type="evaluate_safety_gate",
        decision="explain",
        reason="safety explanation requested",
        output_summary=str(output_path),
    )
    print(f"Wrote safety explanation to {output_path}")
    return output_path


def simulate_live_request(data_dir: Path, output_dir: Path, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    run_id = new_run_id("simulated-live")
    report_path = write_simulated_live_request_report(output_dir)
    summary_path = write_simulated_live_request_summary(output_dir)
    for decision_type in ["block_live_trading", "block_real_broker", "block_real_order", "block_real_network_data"]:
        _audit(
            output_dir,
            config,
            run_id=run_id,
            stage="simulated_live_request",
            decision_type=decision_type,
            decision="blocked",
            reason="simulated request only; no real external action was taken",
            output_summary=f"{report_path}; {summary_path}",
            severity="error",
        )
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="simulated_live_request",
        decision_type="simulate_live_request",
        decision="blocked",
        reason="live request was simulated only; no real order, broker, or network action",
        output_summary=f"{report_path}; {summary_path}",
        severity="error",
    )
    print(f"Simulated live request blocked; wrote report to {report_path}")
    return report_path


def system_health(data_dir: Path, output_dir: Path, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    run_id = new_run_id("system-health")
    result = evaluate_system_health(config, output_dir)
    report_path = write_system_health_report(result, output_dir)
    summary_path = write_system_health_summary(result, config, output_dir)
    manifest_csv, manifest_md = write_artifact_manifest(output_dir)
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="system_health",
        decision_type="run_system_health",
        decision="allow" if result.passed else "block",
        reason=f"blocking={len(result.blocking_issues)}, warnings={len(result.warnings)}",
        output_summary=f"{report_path}; {summary_path}",
        severity="info" if result.passed else "error",
    )
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="artifact_manifest",
        decision_type="generate_artifact_manifest",
        decision="generate",
        reason="output artifact manifest generated",
        output_summary=f"{manifest_csv}; {manifest_md}",
    )
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="system_health",
        decision_type="allow_release_candidate" if result.passed else "block_release_candidate",
        decision="candidate_checked",
        reason=f"release_version={config.system_health.release_version}",
        severity="info" if result.passed else "error",
    )
    print(f"System health complete: blocking={len(result.blocking_issues)}; wrote report to {report_path}")
    if result.blocking_issues:
        raise SystemExit(1)
    return report_path


def scan_sensitive_content_cli(data_dir: Path, output_dir: Path, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    run_id = new_run_id("sensitive-scan")
    result = scan_sensitive_content(config)
    report_path = write_sensitive_scan_report(result, output_dir)
    summary_path = write_sensitive_scan_summary(result, config, output_dir)
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="sensitive_scan",
        decision_type="scan_sensitive_content",
        decision="allow" if result.passed else "block",
        reason=f"blocking={len(result.blocking_findings)}, warnings={len(result.warnings)}",
        output_summary=f"{report_path}; {summary_path}",
        severity="info" if result.passed else "error",
    )
    print(f"Sensitive scan complete: blocking={len(result.blocking_findings)}; wrote report to {report_path}")
    if result.blocking_findings:
        raise SystemExit(1)
    return report_path


def release_checklist(data_dir: Path, output_dir: Path, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    run_id = new_run_id("release-checklist")
    health = evaluate_system_health(config, output_dir)
    write_system_health_report(health, output_dir)
    write_system_health_summary(health, config, output_dir)
    items = build_release_checklist(config, health, output_dir)
    csv_path, md_path = write_release_checklist(items, config, output_dir)
    manifest_csv, manifest_md = write_artifact_manifest(output_dir)
    blocking = [item for item in items if item.blocking]
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="release_checklist",
        decision_type="generate_release_checklist",
        decision="allow" if not blocking else "block",
        reason=f"blocking={len(blocking)}, release_version={config.release_checklist.release_version}",
        output_summary=f"{csv_path}; {md_path}",
        severity="info" if not blocking else "error",
    )
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="artifact_manifest",
        decision_type="check_output_artifacts",
        decision="generate",
        reason="release checklist refreshed output artifact manifest",
        output_summary=f"{manifest_csv}; {manifest_md}",
    )
    print(f"Release checklist complete: blocking={len(blocking)}; wrote checklist to {csv_path}")
    if blocking:
        raise SystemExit(1)
    return csv_path


def generate_release_notes(data_dir: Path, output_dir: Path, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    run_id = new_run_id("release-notes")
    draft = build_release_notes_draft(config)
    output_path = write_release_notes(draft, output_dir)
    _audit(
        output_dir,
        config,
        run_id=run_id,
        stage="release_notes",
        decision_type="generate_release_notes",
        decision="generate",
        reason=f"release_version={draft.release_version}",
        output_summary=str(output_path),
    )
    print(f"Wrote release notes draft to {output_path}")
    return output_path


def run_runtime(data_dir: Path, output_dir: Path, config_path: Path | None = None) -> dict:
    load_config(config_path)
    result = RuntimeEngine(output_dir=output_dir).run_once(print_output=False)
    print(json.dumps(result, ensure_ascii=False))
    return result


def validate_runtime_artifacts(data_dir: Path, output_dir: Path, config_path: Path | None = None) -> dict:
    load_config(config_path)
    result = RuntimeArtifactValidator().validate(output_dir=output_dir)
    print(json.dumps(result, ensure_ascii=False))
    return result


def run_runtime_scenarios(data_dir: Path, output_dir: Path, config_path: Path | None = None) -> dict:
    load_config(config_path)
    result = RuntimeScenarioRunner().run_all(output_dir=output_dir)
    print(json.dumps(result, ensure_ascii=False))
    return result


def _add_config_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=Path, default=None, help="Path to YAML config file. Defaults to config/default.yaml.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m dorsey_as")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_SAMPLE_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)

    quality = subparsers.add_parser("check-data-quality", help="Validate local sample CSV data quality and write a report.")
    _add_config_arg(quality)
    schema = subparsers.add_parser("validate-schema", help="Validate local CSV schema and write a report.")
    _add_config_arg(schema)
    score = subparsers.add_parser("run-score", help="Generate ranked stock scores from local sample CSV data.")
    _add_config_arg(score)
    portfolio = subparsers.add_parser("build-portfolio", help="Generate a target portfolio from local sample CSV data.")
    _add_config_arg(portfolio)
    paper = subparsers.add_parser("paper-rebalance", help="Run a local paper rebalance with no broker connection.")
    _add_config_arg(paper)
    paper.add_argument("--cash", type=float, default=None)
    backtest = subparsers.add_parser("run-backtest", help="Run quarterly local CSV backtest with paper-only simulated trades.")
    _add_config_arg(backtest)
    backtest.add_argument("--cash", type=float, default=None)
    report = subparsers.add_parser("generate-report", help="Generate Markdown reports from existing output CSV files.")
    _add_config_arg(report)
    notify = subparsers.add_parser("notify-summary", help="Generate dry-run notification summary files.")
    _add_config_arg(notify)
    safety = subparsers.add_parser("check-pre-live-safety", help="Run research-only pre-live safety gate checks.")
    _add_config_arg(safety)
    safety_explain = subparsers.add_parser("explain-safety", help="Explain current safety boundary.")
    _add_config_arg(safety_explain)
    live_sim = subparsers.add_parser("simulate-live-request", help="Simulate and block a live trading request.")
    _add_config_arg(live_sim)
    health = subparsers.add_parser("system-health", help="Run local system health checks and write release candidate reports.")
    _add_config_arg(health)
    sensitive = subparsers.add_parser("scan-sensitive-content", help="Scan local project files for credential-like strings and forbidden real SDK imports.")
    _add_config_arg(sensitive)
    release = subparsers.add_parser("release-checklist", help="Generate a local release checklist without committing, tagging, or publishing.")
    _add_config_arg(release)
    notes = subparsers.add_parser("generate-release-notes", help="Generate a local release notes draft.")
    _add_config_arg(notes)
    runtime = subparsers.add_parser("run-runtime", help="Run the mock-only runtime pipeline once and print JSON output.")
    _add_config_arg(runtime)
    runtime_validation = subparsers.add_parser("validate-runtime-artifacts", help="Validate local mock runtime ledger and report artifacts.")
    _add_config_arg(runtime_validation)
    runtime_scenarios = subparsers.add_parser("run-runtime-scenarios", help="Run deterministic mock runtime scenario matrix.")
    _add_config_arg(runtime_scenarios)
    provider_contract = subparsers.add_parser("validate-provider-contract", help="Validate mock provider adapter contract fixtures.")
    _add_config_arg(provider_contract)
    contract_diff = subparsers.add_parser("diff-provider-contract", help="Diff baseline and candidate provider schema contracts.")
    _add_config_arg(contract_diff)
    provider_explain = subparsers.add_parser("explain-provider", help="Explain current data provider safety boundary.")
    _add_config_arg(provider_explain)
    migration = subparsers.add_parser("validate-schema-migration", help="Validate schema migration metadata and lifecycle rules.")
    _add_config_arg(migration)
    visual = subparsers.add_parser("generate-contract-diff-html", help="Generate static contract diff HTML visualization.")
    _add_config_arg(visual)
    explain = subparsers.add_parser("explain-score", help="Explain one stock score from scores.csv and factor_audit_log.csv.")
    _add_config_arg(explain)
    explain.add_argument("--symbol", required=True)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run-score":
        run_score(args.data_dir, args.output_dir, config_path=args.config)
    elif args.command == "build-portfolio":
        build_portfolio(args.data_dir, args.output_dir, config_path=args.config)
    elif args.command == "paper-rebalance":
        paper_rebalance(args.data_dir, args.output_dir, args.cash, config_path=args.config)
    elif args.command == "run-backtest":
        run_backtest(args.data_dir, args.output_dir, args.cash, config_path=args.config)
    elif args.command == "check-data-quality":
        check_data_quality(args.data_dir, args.output_dir, config_path=args.config)
    elif args.command == "validate-schema":
        validate_schema(args.data_dir, args.output_dir, config_path=args.config)
    elif args.command == "generate-report":
        generate_report(args.data_dir, args.output_dir, config_path=args.config)
    elif args.command == "notify-summary":
        notify_summary(args.data_dir, args.output_dir, config_path=args.config)
    elif args.command == "check-pre-live-safety":
        check_pre_live_safety(args.data_dir, args.output_dir, config_path=args.config)
    elif args.command == "explain-safety":
        explain_safety(args.data_dir, args.output_dir, config_path=args.config)
    elif args.command == "simulate-live-request":
        simulate_live_request(args.data_dir, args.output_dir, config_path=args.config)
    elif args.command == "system-health":
        system_health(args.data_dir, args.output_dir, config_path=args.config)
    elif args.command == "scan-sensitive-content":
        scan_sensitive_content_cli(args.data_dir, args.output_dir, config_path=args.config)
    elif args.command == "release-checklist":
        release_checklist(args.data_dir, args.output_dir, config_path=args.config)
    elif args.command == "generate-release-notes":
        generate_release_notes(args.data_dir, args.output_dir, config_path=args.config)
    elif args.command == "run-runtime":
        run_runtime(args.data_dir, args.output_dir, config_path=args.config)
    elif args.command == "validate-runtime-artifacts":
        validate_runtime_artifacts(args.data_dir, args.output_dir, config_path=args.config)
    elif args.command == "run-runtime-scenarios":
        run_runtime_scenarios(args.data_dir, args.output_dir, config_path=args.config)
    elif args.command == "validate-provider-contract":
        validate_provider_contract_cli(args.data_dir, args.output_dir, config_path=args.config)
    elif args.command == "diff-provider-contract":
        diff_provider_contract_cli(args.data_dir, args.output_dir, config_path=args.config)
    elif args.command == "explain-provider":
        explain_provider(args.data_dir, args.output_dir, config_path=args.config)
    elif args.command == "validate-schema-migration":
        validate_schema_migration_cli(args.data_dir, args.output_dir, config_path=args.config)
    elif args.command == "generate-contract-diff-html":
        generate_contract_diff_html_cli(args.data_dir, args.output_dir, config_path=args.config)
    elif args.command == "explain-score":
        explain_score(args.data_dir, args.output_dir, args.symbol, config_path=args.config)
    else:
        parser.error(f"unknown command: {args.command}")
