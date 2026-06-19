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
        ],
    )


def generate_run_html_report(output_dir: Path, config: AppConfig, config_path: Path | None = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    quality_rows = read_csv_rows(output_dir / "data_quality_report.csv")
    scores = top_rows(output_dir / "scores.csv", 10)
    portfolio = read_csv_rows(output_dir / "target_portfolio.csv")
    trades = read_csv_rows(output_dir / "paper_trades.csv")
    blocking_count = sum(1 for row in quality_rows if row.get("blocking") == "True")
    warning_count = sum(1 for row in quality_rows if row.get("severity") == "warning")
    body = "\n".join(
        [
            "<h1>Strategy Run Report</h1>",
            f"<p>Generated at: {escape(datetime.now().isoformat(timespec='seconds'))}</p>",
            f"<p>Config file: {escape(str(config_path or 'config/default.yaml'))}</p>",
            f"<section class=\"notice\"><h2>Safety Statement</h2><p>{escape(SAFETY_TEXT)}</p></section>",
            "<section><h2>Config Summary</h2>" + _config_summary(config) + "</section>",
            f"<section><h2>Data Quality Check Result</h2><p>Blocking issues: {blocking_count}; warnings: {warning_count}</p></section>",
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
            "<section><h2>Equity Curve Chart</h2>" + render_equity_curve_chart(output_dir / "backtest_equity_curve.csv") + "</section>",
            "<section><h2>Drawdown Chart</h2>" + render_drawdown_chart(output_dir / "backtest_equity_curve.csv") + "</section>",
            "<section><h2>Trade Summary Table</h2>"
            + _table(["reason", "count"], [[reason or "filled_or_none", str(count)] for reason, count in skipped.items()])
            + "</section>",
            "<section><h2>Final Holdings Table</h2>"
            + _table(["symbol", "quantity", "price", "market_value"], [[row.get("symbol", ""), row.get("quantity", ""), row.get("price", ""), row.get("market_value", "")] for row in final_holdings])
            + "</section>",
            f"<section><h2>Data Quality Summary</h2><p>Warning count: {warning_count}; blocking issue count: {blocking_count}; report rows: {len(quality)}</p></section>",
            f"<section><h2>Audit Log Summary</h2><p>Audit rows: {len(audit)}</p></section>",
            "<section><h2>Current Limitations</h2><p>Local sample CSV only. Static charts. No real trading or broker integration.</p></section>",
        ]
    )
    path = output_dir / "backtest_report.html"
    path.write_text(_html_page("Backtest Report", body), encoding="utf-8")
    return path
