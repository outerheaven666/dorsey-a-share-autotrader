from __future__ import annotations

from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path

from dorsey_as.config.models import AppConfig
from dorsey_as.reporting.charts import render_drawdown_chart, render_equity_curve_chart
from dorsey_as.reporting.markdown import SAFETY_TEXT
from dorsey_as.reporting.summary import latest_rows_by_date, read_csv_rows, top_rows


STYLE = """
body{font-family:Arial,Helvetica,sans-serif;margin:0;background:#f6f8fa;color:#1f2937}
main{max-width:1080px;margin:0 auto;padding:32px}
section{margin:24px 0;padding:20px;background:#fff;border:1px solid #d8dee9;border-radius:8px}
h1,h2{margin-top:0} .notice{border-left:4px solid #d1242f}
table{width:100%;border-collapse:collapse;font-size:14px} th,td{padding:8px;border-bottom:1px solid #e5e7eb;text-align:left}
.metric-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}
.metric{padding:12px;border:1px solid #e5e7eb;border-radius:8px;background:#f9fafb}.metric strong{display:block;font-size:13px;color:#4b5563}.metric span{font-size:18px}
.chart{width:100%;height:auto}.chart-empty{padding:16px;border:1px dashed #a7b0bd;border-radius:8px;background:#f9fafb}
"""


def _html_page(title: str, body: str) -> str:
    return f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>{escape(title)}</title><style>{STYLE}</style></head><body><main>{body}</main></body></html>"


def _table(headers: list[str], rows: list[list[str]], empty: str = "No data available.") -> str:
    if not rows:
        return f"<p>{escape(empty)}</p>"
    header_html = "".join(f"<th>{escape(header)}</th>" for header in headers)
    row_html = "".join("<tr>" + "".join(f"<td>{escape(str(value))}</td>" for value in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{header_html}</tr></thead><tbody>{row_html}</tbody></table>"


def _config_summary(config: AppConfig) -> str:
    return _table(
        ["Section", "Summary"],
        [
            ["Scoring", f"quality={config.scoring.quality_weight}, moat={config.scoring.moat_weight}, valuation={config.scoring.valuation_weight}, risk={config.scoring.risk_weight}"],
            ["Portfolio", f"max_positions={config.portfolio.max_positions}, max_stock={config.portfolio.max_stock_weight}, cash={config.portfolio.cash_reserve}"],
            ["Transaction Cost", f"commission={config.transaction_cost.commission_rate}, min={config.transaction_cost.minimum_commission}, stamp={config.transaction_cost.stamp_duty_rate}, slippage={config.transaction_cost.slippage_rate}"],
            ["Notify", f"enabled={config.notify.enabled}, mode={config.notify.mode}, channel={config.notify.channel}"],
            ["Adapter Contract", f"mode={config.adapter_contract.mode}, provider={config.adapter_contract.provider}, network={config.adapter_contract.allow_network}, real_provider={config.adapter_contract.allow_real_provider}"],
        ],
    )


def generate_run_html_report(output_dir: Path, config: AppConfig, config_path: Path | None = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    quality_rows = read_csv_rows(output_dir / "data_quality_report.csv")
    scores = top_rows(output_dir / "scores.csv", 10)
    portfolio = read_csv_rows(output_dir / "target_portfolio.csv")
    trades = read_csv_rows(output_dir / "paper_trades.csv")
    schema_rows = read_csv_rows(output_dir / "schema_validation_report.csv")
    pit_rows = read_csv_rows(output_dir / "point_in_time_snapshot.csv")
    factor_rows = read_csv_rows(output_dir / "factor_audit_log.csv")
    manifest_rows = read_csv_rows(output_dir / "data_source_manifest.csv")
    provider_contract_rows = read_csv_rows(output_dir / "provider_contract_report.csv")
    mapped_preview_rows = read_csv_rows(output_dir / "adapter_mapped_preview.csv")
    contract_diff_rows = read_csv_rows(output_dir / "provider_contract_diff_report.csv")
    migration_rows = read_csv_rows(output_dir / "schema_migration_report.csv")
    safety_rows = read_csv_rows(output_dir / "pre_live_safety_report.csv")
    health_rows = read_csv_rows(output_dir / "system_health_report.csv")
    checklist_rows = read_csv_rows(output_dir / "release_checklist.csv")
    sensitive_rows = read_csv_rows(output_dir / "sensitive_scan_report.csv")
    artifact_rows = read_csv_rows(output_dir / "output_artifact_manifest.csv")
    visual_exists = (output_dir / "provider_contract_diff.html").exists()
    blocking_count = sum(1 for row in quality_rows if row.get("blocking") == "True")
    warning_count = sum(1 for row in quality_rows if row.get("severity") == "warning")
    body = "\n".join(
        [
            "<h1>Strategy Run Report</h1>",
            f"<p>Generated at: {escape(datetime.now().isoformat(timespec='seconds'))}</p>",
            f"<p>Config file: {escape(str(config_path or 'config/default.yaml'))}</p>",
            f"<section class=\"notice\"><h2>Safety Statement</h2><p>{escape(SAFETY_TEXT)}</p></section>",
            "<section><h2>Config Summary</h2>" + _config_summary(config) + "</section>",
            f"<section><h2>Data Source Summary</h2><p>Manifest rows: {len(manifest_rows)}. Mode is local_csv only; network access is disabled.</p></section>",
            f"<section><h2>Adapter Contract Summary</h2><p>Mode: {escape(config.adapter_contract.mode)}; mock provider: {escape(config.adapter_contract.provider)}; real data source status: not enabled; network data source status: disabled; contract rows: {len(provider_contract_rows)}; mapping preview rows: {len(mapped_preview_rows)}.</p></section>",
            f"<section><h2>Schema Versioning Summary</h2><p>Current contract version: {escape(config.schema_versioning.current_version)}; baseline: {escape(config.schema_versioning.baseline_contract)}; candidate: {escape(config.schema_versioning.candidate_contract)}; disabled provider template: {'disabled' if not config.provider_templates.real_provider_templates_enabled else 'enabled'}.</p></section>",
            f"<section><h2>Contract Diff Summary</h2><p>Rows: {len(contract_diff_rows)}; breaking changes: {sum(1 for row in contract_diff_rows if row.get('breaking') == 'True')}; additive changes: {sum(1 for row in contract_diff_rows if row.get('change_type', '').startswith('additive'))}; real data source status: not enabled; network data source status: disabled.</p></section>",
            f"<section><h2>Schema Migration Summary</h2><p>Current version: {escape(config.schema_migration.current_version)}; target version: {escape(config.schema_migration.target_version)}; migration plan: {escape(config.schema_migration.migration_plan)}; compatibility window: {config.schema_migration.compatibility_window_days} days; expired deprecations: {sum(1 for row in migration_rows if row.get('check_type') == 'expired_deprecation')}; contract diff visualization: {'generated' if visual_exists else 'not generated'}.</p></section>",
            f"<section><h2>Pre-Live Safety Summary</h2><p>Execution policy mode: {escape(config.execution_policy.mode)}; live trading blocked: true; real broker blocked: true; real network data blocked: true; dry-run notify allowed: {config.execution_policy.allow_dry_run_notify}; paper trading allowed: {config.execution_policy.allow_paper_trading}; backtest allowed: {config.execution_policy.allow_backtest}; safety acknowledgement: {'configured' if config.pre_live_safety.safety_ack_phrase else 'missing'}; safety rows: {len(safety_rows)}.</p></section>",
            f"<section><h2>System Health And Release Summary</h2><p>Release version: {escape(config.system_health.release_version)}; system health rows: {len(health_rows)}; system health blocking: {sum(1 for row in health_rows if row.get('blocking') == 'True')}; release checklist rows: {len(checklist_rows)}; release checklist blocking: {sum(1 for row in checklist_rows if row.get('blocking') == 'True')}; sensitive scan findings: {len(sensitive_rows)}; sensitive scan blocking: {sum(1 for row in sensitive_rows if row.get('blocking') == 'True')}; artifact manifest rows: {len(artifact_rows)}.</p></section>",
            f"<section><h2>Data Quality Check Result</h2><p>Blocking issues: {blocking_count}; warnings: {warning_count}</p></section>",
            f"<section><h2>Schema Validation Summary</h2><p>Rows: {len(schema_rows)}; failures: {sum(1 for row in schema_rows if row.get('status') == 'fail')}; warnings: {sum(1 for row in schema_rows if row.get('severity') == 'warning')}</p></section>",
            f"<section><h2>Point-in-Time Summary</h2><p>Snapshot rows: {len(pit_rows)}; visible rows: {sum(1 for row in pit_rows if row.get('visible') == 'True')}; future disclosure exclusions: {sum(1 for row in pit_rows if row.get('reason') == 'future_disclosure')}</p></section>",
            f"<section><h2>Factor Audit Summary</h2><p>Rows: {len(factor_rows)}; risk blocks: {sum(1 for row in factor_rows if row.get('factor_group') == 'risk' and row.get('severity') == 'error')}</p></section>",
            "<section><h2>Top 10 Stock Scores</h2>"
            + _table(["symbol", "composite", "quality", "moat", "valuation", "risk"], [[row.get("symbol", ""), row.get("composite_score", ""), row.get("quality_score", ""), row.get("moat_score", ""), row.get("valuation_score", ""), row.get("risk_score", "")] for row in scores])
            + "</section>",
            "<section><h2>Target Portfolio</h2>"
            + _table(["symbol", "name", "industry", "target_weight", "score"], [[row.get("symbol", ""), row.get("name", ""), row.get("industry", ""), row.get("target_weight", ""), row.get("score", "")] for row in portfolio[:20]])
            + "</section>",
            f"<section><h2>PaperBroker Simulated Trade Summary</h2><p>Trade records: {len(trades)}</p></section>",
            "<section><h2>Current Limitations</h2><p>Local sample CSV only. Reports are static. No real trading or broker integration.</p></section>",
        ]
    )
    path = output_dir / "run_report.html"
    path.write_text(_html_page("Strategy Run Report", body), encoding="utf-8")
    return path


def generate_backtest_html_report(output_dir: Path, config: AppConfig, config_path: Path | None = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    equity = read_csv_rows(output_dir / "backtest_equity_curve.csv")
    metrics_rows = read_csv_rows(output_dir / "backtest_metrics.csv")
    metrics = {row.get("metric", ""): row.get("value", "") for row in metrics_rows}
    trades = read_csv_rows(output_dir / "backtest_trades.csv")
    audit = read_csv_rows(output_dir / "backtest_audit_log.csv")
    quality = read_csv_rows(output_dir / "data_quality_report.csv")
    schema_rows = read_csv_rows(output_dir / "schema_validation_report.csv")
    pit_rows = read_csv_rows(output_dir / "point_in_time_snapshot.csv")
    factor_rows = read_csv_rows(output_dir / "factor_audit_log.csv")
    provider_contract_rows = read_csv_rows(output_dir / "provider_contract_report.csv")
    contract_diff_rows = read_csv_rows(output_dir / "provider_contract_diff_report.csv")
    migration_rows = read_csv_rows(output_dir / "schema_migration_report.csv")
    safety_rows = read_csv_rows(output_dir / "pre_live_safety_report.csv")
    health_rows = read_csv_rows(output_dir / "system_health_report.csv")
    final_holdings = latest_rows_by_date(output_dir / "backtest_holdings.csv", "trade_date")
    skipped = Counter(row.get("reason", "") for row in trades if row.get("status") == "SKIPPED")
    start_date = equity[0]["trade_date"] if equity else ""
    end_date = equity[-1]["trade_date"] if equity else ""
    end_equity = equity[-1]["total_value"] if equity else ""
    warning_count = sum(int(row.get("warnings", "0") or 0) for row in audit)
    blocking_count = sum(int(row.get("blocking_issues", "0") or 0) for row in audit)
    metric_names = ["total_return", "annualized_return", "max_drawdown", "sharpe_ratio", "turnover", "number_of_trades", "win_rate"]
    metric_cards = "".join(f"<div class=\"metric\"><strong>{escape(name)}</strong><span>{escape(metrics.get(name, ''))}</span></div>" for name in metric_names)
    body = "\n".join(
        [
            "<h1>Backtest Report</h1>",
            f"<p>Generated at: {escape(datetime.now().isoformat(timespec='seconds'))}</p>",
            f"<p>Config file: {escape(str(config_path or 'config/default.yaml'))}</p>",
            f"<section class=\"notice\"><h2>Safety Statement</h2><p>{escape(SAFETY_TEXT)}</p></section>",
            "<section><h2>Config Summary</h2>" + _config_summary(config) + "</section>",
            f"<section><h2>Backtest Summary</h2><p>Range: {escape(start_date)} to {escape(end_date)}; Initial cash: {config.backtest.initial_cash}; Ending equity: {escape(end_equity)}</p></section>",
            "<section><h2>Backtest Metrics</h2><div class=\"metric-grid\">" + metric_cards + "</div></section>",
            f"<section><h2>Data Source Boundary</h2><p>Backtest uses local_csv sample data only. Mock provider is contract-test only and is not used for backtest trading simulation. Network data sources are disabled. Contract version used: {escape(config.schema_versioning.current_version)}. Provider contract rows: {len(provider_contract_rows)}. Contract diff rows: {len(contract_diff_rows)}. Schema migration rows: {len(migration_rows)}. Contract diff and migration metadata do not participate in trading decisions. Execution policy mode: {escape(config.execution_policy.mode)}. Release candidate version: {escape(config.system_health.release_version)}. System health rows: {len(health_rows)}. Current system has no live trading, no real broker, no real orders, and no real network data. Pre-live safety rows: {len(safety_rows)}.</p></section>",
            "<section><h2>Equity Curve Chart</h2>" + render_equity_curve_chart(output_dir / "backtest_equity_curve.csv") + "</section>",
            "<section><h2>Drawdown Chart</h2>" + render_drawdown_chart(output_dir / "backtest_equity_curve.csv") + "</section>",
            "<section><h2>Trade Summary Table</h2>"
            + _table(["reason", "count"], [[reason or "filled_or_none", str(count)] for reason, count in skipped.items()])
            + "</section>",
            "<section><h2>Final Holdings Table</h2>"
            + _table(["symbol", "quantity", "price", "market_value"], [[row.get("symbol", ""), row.get("quantity", ""), row.get("price", ""), row.get("market_value", "")] for row in final_holdings])
            + "</section>",
            f"<section><h2>Data Quality Summary</h2><p>Warning count: {warning_count}; blocking issue count: {blocking_count}; report rows: {len(quality)}</p></section>",
            f"<section><h2>Point-in-Time Summary</h2><p>Snapshot rows: {len(pit_rows)}; future disclosure exclusions: {sum(1 for row in pit_rows if row.get('reason') == 'future_disclosure')}</p></section>",
            f"<section><h2>Schema Validation Summary</h2><p>Failures: {sum(1 for row in schema_rows if row.get('status') == 'fail')}; warnings: {sum(1 for row in schema_rows if row.get('severity') == 'warning')}</p></section>",
            f"<section><h2>Factor Audit Summary</h2><p>Rows: {len(factor_rows)}</p></section>",
            f"<section><h2>Audit Log Summary</h2><p>Audit rows: {len(audit)}</p></section>",
            "<section><h2>Current Limitations</h2><p>Local sample CSV only. Static charts. No real trading or broker integration.</p></section>",
        ]
    )
    path = output_dir / "backtest_report.html"
    path.write_text(_html_page("Backtest Report", body), encoding="utf-8")
    return path
