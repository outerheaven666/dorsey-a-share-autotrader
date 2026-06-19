from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from dorsey_as.config.models import AppConfig
from dorsey_as.notify.feishu import send_feishu_notification
from dorsey_as.reporting.markdown import SAFETY_TEXT
from dorsey_as.reporting.summary import read_csv_rows


def _metric_map(output_dir: Path) -> dict[str, str]:
    return {row.get("metric", ""): row.get("value", "") for row in read_csv_rows(output_dir / "backtest_metrics.csv")}


def build_notify_payload(output_dir: Path, config: AppConfig, config_path: Path | None = None) -> dict[str, object]:
    metrics = _metric_map(output_dir)
    quality_rows = read_csv_rows(output_dir / "data_quality_report.csv")
    blocking = sum(1 for row in quality_rows if row.get("blocking") == "True")
    warnings = sum(1 for row in quality_rows if row.get("severity") == "warning")
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "phase": "MVP 5 local paper/backtest reporting",
        "config_file": str(config_path or "config/default.yaml"),
        "dry_run": not config.notify.enabled or config.notify.mode == "dry_run",
        "would_send": bool(config.notify.enabled and config.notify.mode == "send"),
        "channel": config.notify.channel,
        "data_quality_blocking_issues": blocking,
        "data_quality_warnings": warnings,
        "total_return": metrics.get("total_return", ""),
        "max_drawdown": metrics.get("max_drawdown", ""),
        "sharpe_ratio": metrics.get("sharpe_ratio", ""),
        "number_of_trades": metrics.get("number_of_trades", ""),
        "reports": {
            "run_markdown": str(output_dir / "run_report.md"),
            "backtest_markdown": str(output_dir / "backtest_report.md"),
            "run_html": str(output_dir / "run_report.html"),
            "backtest_html": str(output_dir / "backtest_report.html"),
        },
        "safety_statement": SAFETY_TEXT,
    }


def _summary_markdown(payload: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Notification Summary",
            "",
            f"- Generated at: {payload['generated_at']}",
            f"- Phase: {payload['phase']}",
            f"- Channel: {payload['channel']}",
            f"- Dry run: {payload['dry_run']}",
            f"- Would send: {payload['would_send']}",
            f"- Data quality blocking issues: {payload['data_quality_blocking_issues']}",
            f"- Data quality warnings: {payload['data_quality_warnings']}",
            f"- Total return: {payload['total_return']}",
            f"- Max drawdown: {payload['max_drawdown']}",
            f"- Sharpe ratio: {payload['sharpe_ratio']}",
            f"- Number of trades: {payload['number_of_trades']}",
            "",
            "## Safety Statement",
            "",
            str(payload["safety_statement"]),
            "",
        ]
    )


def generate_notify_summary(output_dir: Path, config: AppConfig, config_path: Path | None = None) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = build_notify_payload(output_dir, config, config_path)
    send_result = send_feishu_notification(payload, config.notify, output_dir)
    payload["send_result"] = send_result
    payload_path = output_dir / "notify_payload.json"
    summary_path = output_dir / "notify_summary.md"
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path.write_text(_summary_markdown(payload), encoding="utf-8")
    return payload_path, summary_path
