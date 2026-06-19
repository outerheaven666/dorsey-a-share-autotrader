from __future__ import annotations

import argparse
import csv
from pathlib import Path

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
from dorsey_as.models import ScoreResult, TargetPortfolio
from dorsey_as.notify.summary import generate_notify_summary
from dorsey_as.point_in_time import build_point_in_time_snapshot
from dorsey_as.portfolio.constructor import build_target_portfolio
from dorsey_as.reporting.html import generate_backtest_html_report, generate_run_html_report
from dorsey_as.reporting.markdown import generate_backtest_report, generate_run_report
from dorsey_as.scoring import calculate_scores


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


def _load_checked_sample_data(data_dir: Path, output_dir: Path, config: AppConfig, as_of_date: str | None = None):
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


def run_score(data_dir: Path, output_dir: Path, as_of_date: str | None = None, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    run_id = new_run_id("score")
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


def generate_report(data_dir: Path, output_dir: Path, config_path: Path | None = None) -> tuple[Path, Path]:
    config = load_config(config_path)
    run_id = new_run_id("report")
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
    print(f"Wrote notify dry-run summary to {payload_path} and {summary_path}")
    return payload_path, summary_path


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
    elif args.command == "explain-score":
        explain_score(args.data_dir, args.output_dir, args.symbol, config_path=args.config)
    else:
        parser.error(f"unknown command: {args.command}")
