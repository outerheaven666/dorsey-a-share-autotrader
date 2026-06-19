from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path

from dorsey_as.config.models import AppConfig
from dorsey_as.reporting.summary import count_rows, latest_rows_by_date, read_csv_rows, top_rows


SAFETY_TEXT = (
    "No real-money trading is supported. No real broker connection exists. "
    "No real network data source connection exists. "
    "This system is for personal research, system development, paper trading, and backtest simulation only. "
    "It does not provide investment advice and does not guarantee returns."
)


def _table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_No data available._"
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def generate_run_report(output_dir: Path, config: AppConfig, config_path: Path | None = None) -> Path:
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
    blocking_count = sum(1 for row in quality_rows if row.get("blocking") == "True")
    warning_count = sum(1 for row in quality_rows if row.get("severity") == "warning")

    lines = [
        "# Strategy Run Report",
        "",
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        f"- Config file: {config_path or 'config/default.yaml'}",
        f"- Output format: {config.report.output_format}",
        "",
        "## Data Quality Summary",
        "",
        f"- Issues: {len(quality_rows)}",
        f"- Blocking issues: {blocking_count}",
        f"- Warnings: {warning_count}",
        "",
        "## Data Source Summary",
        "",
        f"- Manifest rows: {len(manifest_rows)}",
        "- Mode: local_csv only; network access is disabled.",
        "",
        "## Adapter Contract Summary",
        "",
        f"- Adapter mode: {config.adapter_contract.mode}",
        f"- Mock provider: {config.adapter_contract.provider}",
        f"- Network data source status: disabled",
        f"- Real data provider status: not enabled",
        f"- Provider contract validation rows: {len(provider_contract_rows)}",
        f"- Provider contract failures: {sum(1 for row in provider_contract_rows if row.get('status') == 'fail')}",
        f"- Field mapping preview rows: {len(mapped_preview_rows)}",
        "",
        "## Schema Validation Summary",
        "",
        f"- Validation rows: {len(schema_rows)}",
        f"- Failures: {sum(1 for row in schema_rows if row.get('status') == 'fail')}",
        f"- Warnings: {sum(1 for row in schema_rows if row.get('severity') == 'warning')}",
        "",
        "## Point-in-Time Summary",
        "",
        f"- Snapshot rows: {len(pit_rows)}",
        f"- Visible rows: {sum(1 for row in pit_rows if row.get('visible') == 'True')}",
        f"- Future disclosure exclusions: {sum(1 for row in pit_rows if row.get('reason') == 'future_disclosure')}",
        "",
        "## Factor Audit Summary",
        "",
        f"- Factor audit rows: {len(factor_rows)}",
        f"- Blocked risk rows: {sum(1 for row in factor_rows if row.get('factor_group') == 'risk' and row.get('severity') == 'error')}",
        "",
        "## Scoring Summary",
        "",
        f"- Score rows: {count_rows(output_dir / 'scores.csv')}",
        "",
        "## Top Scores",
        "",
        _table(
            ["symbol", "composite", "quality", "moat", "valuation", "risk", "blocked"],
            [
                [
                    row.get("symbol", ""),
                    row.get("composite_score", ""),
                    row.get("quality_score", ""),
                    row.get("moat_score", ""),
                    row.get("valuation_score", ""),
                    row.get("risk_score", ""),
                    row.get("blocked", ""),
                ]
                for row in scores
            ],
        ),
        "",
        "## Target Portfolio",
        "",
        f"- Position rows: {len([row for row in portfolio if row.get('symbol') != 'CASH'])}",
        _table(
            ["symbol", "name", "industry", "target_weight", "score"],
            [[row.get("symbol", ""), row.get("name", ""), row.get("industry", ""), row.get("target_weight", ""), row.get("score", "")] for row in portfolio[:10]],
        ),
        "",
        "## PaperBroker Trade Summary",
        "",
        f"- Simulated trade records: {len(trades)}",
        "",
        "## Safety Statement",
        "",
        SAFETY_TEXT,
    ]

    path = output_dir / "run_report.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def generate_backtest_report(output_dir: Path, config: AppConfig, config_path: Path | None = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    equity = read_csv_rows(output_dir / "backtest_equity_curve.csv")
    metrics_rows = read_csv_rows(output_dir / "backtest_metrics.csv")
    metrics = {row.get("metric", ""): row.get("value", "") for row in metrics_rows}
    trades = read_csv_rows(output_dir / "backtest_trades.csv")
    audit = read_csv_rows(output_dir / "backtest_audit_log.csv")
    pit_rows = read_csv_rows(output_dir / "point_in_time_snapshot.csv")
    schema_rows = read_csv_rows(output_dir / "schema_validation_report.csv")
    factor_rows = read_csv_rows(output_dir / "factor_audit_log.csv")
    provider_contract_rows = read_csv_rows(output_dir / "provider_contract_report.csv")
    final_holdings = latest_rows_by_date(output_dir / "backtest_holdings.csv", "trade_date")
    skipped = Counter(row.get("reason", "") for row in trades if row.get("status") == "SKIPPED")
    start_date = equity[0]["trade_date"] if equity else ""
    end_date = equity[-1]["trade_date"] if equity else ""
    end_equity = equity[-1]["total_value"] if equity else ""
    blocking_count = sum(int(row.get("blocking_issues", "0") or 0) for row in audit)
    warning_count = sum(int(row.get("warnings", "0") or 0) for row in audit)

    lines = [
        "# Backtest Report",
        "",
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        f"- Config file: {config_path or 'config/default.yaml'}",
        f"- Backtest range: {start_date} to {end_date}",
        f"- Rebalance checks: {len(audit)}",
        f"- Initial cash: {config.backtest.initial_cash}",
        f"- Ending equity: {end_equity}",
        "",
        "## Backtest Metrics",
        "",
        _table(
            ["metric", "value"],
            [[name, metrics.get(name, "")] for name in ["total_return", "annualized_return", "max_drawdown", "sharpe_ratio", "turnover", "number_of_trades", "win_rate"]],
        ),
        "",
        "## Data Quality Summary",
        "",
        f"- Blocking issue count: {blocking_count}",
        f"- Warning count: {warning_count}",
        "",
        "## Data Source Boundary",
        "",
        "- Backtest uses local_csv sample data only.",
        "- Mock provider is used only for adapter contract tests.",
        "- Network data sources and real providers are disabled.",
        f"- Provider contract validation rows: {len(provider_contract_rows)}",
        "",
        "## Point-in-Time Summary",
        "",
        f"- Snapshot rows: {len(pit_rows)}",
        f"- Future disclosure exclusions: {sum(1 for row in pit_rows if row.get('reason') == 'future_disclosure')}",
        f"- Missing disclosure rows: {sum(1 for row in pit_rows if row.get('reason') == 'missing_disclosure_date')}",
        "",
        "## Schema And Factor Audit Summary",
        "",
        f"- Schema warnings: {sum(1 for row in schema_rows if row.get('severity') == 'warning')}",
        f"- Schema failures: {sum(1 for row in schema_rows if row.get('status') == 'fail')}",
        f"- Factor audit rows: {len(factor_rows)}",
        "",
        "## Trading Restriction Summary",
        "",
        _table(["reason", "count"], [[reason or "none", str(count)] for reason, count in skipped.items()]),
        "",
        "## Final Holdings",
        "",
        _table(
            ["symbol", "quantity", "price", "market_value"],
            [[row.get("symbol", ""), row.get("quantity", ""), row.get("price", ""), row.get("market_value", "")] for row in final_holdings[:20]],
        ),
        "",
        "## Safety Statement",
        "",
        SAFETY_TEXT,
    ]

    path = output_dir / "backtest_report.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
