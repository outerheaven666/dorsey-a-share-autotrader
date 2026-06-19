from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from dorsey_as.config.models import AppConfig
from dorsey_as.factors.quality import calculate_quality
from dorsey_as.moat.engine import calculate_moat
from dorsey_as.models import FinancialSnapshot, MarketSnapshot, ScoreResult, StockBasic
from dorsey_as.risk.engine import evaluate_red_flags
from dorsey_as.valuation.engine import calculate_valuation


FIELDS = [
    "run_id",
    "timestamp",
    "as_of_date",
    "symbol",
    "factor_group",
    "factor_name",
    "raw_value",
    "normalized_value",
    "component_score",
    "weight",
    "weighted_score",
    "reason",
    "severity",
]


def _row(
    run_id: str,
    as_of_date: str,
    symbol: str,
    factor_group: str,
    factor_name: str,
    raw_value: str | float,
    normalized_value: str | float,
    component_score: float,
    weight: float,
    reason: str,
    severity: str = "info",
) -> dict[str, str | float]:
    return {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "as_of_date": as_of_date,
        "symbol": symbol,
        "factor_group": factor_group,
        "factor_name": factor_name,
        "raw_value": raw_value,
        "normalized_value": normalized_value,
        "component_score": round(component_score, 6),
        "weight": weight,
        "weighted_score": round(component_score * weight, 6),
        "reason": reason,
        "severity": severity,
    }


def write_factor_audit_log(
    scores: list[ScoreResult],
    stocks: dict[str, StockBasic],
    financials: dict[str, list[FinancialSnapshot]],
    markets: dict[str, MarketSnapshot],
    output_dir: Path,
    config: AppConfig,
    as_of_date: str,
    run_id: str,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "factor_audit_log.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        for score in scores:
            symbol = score.symbol
            stock = stocks[symbol]
            rows = financials.get(symbol, [])
            market = markets[symbol]
            quality = calculate_quality(stock, rows)
            moat = calculate_moat(stock, rows)
            valuation = calculate_valuation(market, roe=rows[-1].roe if rows else 0.0)
            risk = evaluate_red_flags(stock, rows)

            for name, value in quality.components.items():
                writer.writerow(_row(run_id, as_of_date, symbol, "quality", name, value, value, value, config.scoring.quality_weight, f"quality component {name} normalized to {value:.2f}"))
            for name, value in moat.components.items():
                writer.writerow(_row(run_id, as_of_date, symbol, "moat", name, value, value, value, config.scoring.moat_weight, f"moat proxy {name} contributed {value:.2f}"))
            for name, value in valuation.components.items():
                writer.writerow(_row(run_id, as_of_date, symbol, "valuation", name, value, value, value, config.scoring.valuation_weight, f"valuation component {name} scored {value:.2f}"))

            risk_reason = ";".join(risk.reasons) if risk.reasons else "no blocking red flags"
            severity = "error" if risk.blocked else "info"
            writer.writerow(_row(run_id, as_of_date, symbol, "risk", "red_flags", risk_reason, risk.risk_score, risk.risk_score, config.scoring.risk_weight, risk_reason, severity))
            writer.writerow(
                _row(
                    run_id,
                    as_of_date,
                    symbol,
                    "composite",
                    "composite_score",
                    score.composite_score,
                    score.composite_score,
                    score.composite_score,
                    1.0,
                    "composite score combines quality, moat, valuation, and risk weights; blocked stocks are forced to 0",
                    "error" if score.blocked else "info",
                )
            )
    return path
