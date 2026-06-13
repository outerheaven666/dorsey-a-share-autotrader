from __future__ import annotations

import argparse
import csv
from pathlib import Path

from dorsey_as.backtest.engine import BacktestEngine
from dorsey_as.backtest.models import BacktestConfig
from dorsey_as.broker.paper import PaperBroker
from dorsey_as.config.defaults import DEFAULT_OUTPUT_DIR, DEFAULT_SAMPLE_DATA_DIR
from dorsey_as.data.loaders import load_sample_data
from dorsey_as.models import ScoreResult, TargetPortfolio
from dorsey_as.portfolio.constructor import build_target_portfolio
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


def _build_scores_and_portfolio(data_dir: Path) -> tuple[list[ScoreResult], TargetPortfolio, dict[str, float]]:
    stocks, financials, markets = load_sample_data(data_dir)
    scores = calculate_scores(stocks, financials, markets)
    portfolio = build_target_portfolio(scores, stocks)
    prices = {symbol: market.close_price for symbol, market in markets.items()}
    return scores, portfolio, prices


def run_score(data_dir: Path, output_dir: Path) -> Path:
    stocks, financials, markets = load_sample_data(data_dir)
    scores = calculate_scores(stocks, financials, markets)
    output_path = output_dir / "scores.csv"
    _write_scores(output_path, scores)
    print(f"Wrote {len(scores)} scores to {output_path}")
    return output_path


def build_portfolio(data_dir: Path, output_dir: Path) -> Path:
    scores, portfolio, _prices = _build_scores_and_portfolio(data_dir)
    _write_scores(output_dir / "scores.csv", scores)
    output_path = output_dir / "target_portfolio.csv"
    _write_portfolio(output_path, portfolio)
    print(f"Wrote {len(portfolio.positions)} target positions to {output_path}")
    return output_path


def paper_rebalance(data_dir: Path, output_dir: Path, cash: float) -> Path:
    scores, portfolio, prices = _build_scores_and_portfolio(data_dir)
    _write_scores(output_dir / "scores.csv", scores)
    _write_portfolio(output_dir / "target_portfolio.csv", portfolio)
    broker = PaperBroker.from_state(
        output_dir / "paper_state.csv",
        output_dir / "paper_trades.csv",
        default_cash=cash,
    )
    orders = broker.rebalance(portfolio, prices)
    broker.save_state(output_dir / "paper_state.csv")
    print(f"Simulated {len(orders)} paper orders; wrote trades to {output_dir / 'paper_trades.csv'}")
    return output_dir / "paper_trades.csv"


def run_backtest(data_dir: Path, output_dir: Path, cash: float) -> Path:
    engine = BacktestEngine.from_sample_data(
        data_dir=data_dir,
        output_dir=output_dir,
        config=BacktestConfig(initial_cash=cash),
    )
    result = engine.run()
    print(
        "Backtest complete: "
        f"{len(result.equity_curve)} equity points, "
        f"{len(result.trades)} trade records; "
        f"wrote outputs to {output_dir}"
    )
    return output_dir / "backtest_equity_curve.csv"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m dorsey_as")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_SAMPLE_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("run-score", help="Generate ranked stock scores from local sample CSV data.")
    subparsers.add_parser("build-portfolio", help="Generate a target portfolio from local sample CSV data.")
    paper = subparsers.add_parser("paper-rebalance", help="Run a local paper rebalance with no broker connection.")
    paper.add_argument("--cash", type=float, default=1_000_000.0)
    backtest = subparsers.add_parser("run-backtest", help="Run quarterly local CSV backtest with paper-only simulated trades.")
    backtest.add_argument("--cash", type=float, default=1_000_000.0)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run-score":
        run_score(args.data_dir, args.output_dir)
    elif args.command == "build-portfolio":
        build_portfolio(args.data_dir, args.output_dir)
    elif args.command == "paper-rebalance":
        paper_rebalance(args.data_dir, args.output_dir, args.cash)
    elif args.command == "run-backtest":
        run_backtest(args.data_dir, args.output_dir, args.cash)
    else:
        parser.error(f"unknown command: {args.command}")
