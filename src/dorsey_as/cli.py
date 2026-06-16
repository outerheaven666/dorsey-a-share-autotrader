from __future__ import annotations

import argparse
import csv
from pathlib import Path

from dorsey_as.backtest.engine import BacktestEngine
from dorsey_as.backtest.models import BacktestConfig as RuntimeBacktestConfig
from dorsey_as.broker.paper import PaperBroker
from dorsey_as.config.loader import DEFAULT_CONFIG_PATH, load_config
from dorsey_as.config.models import AppConfig
from dorsey_as.config.defaults import DEFAULT_OUTPUT_DIR, DEFAULT_SAMPLE_DATA_DIR
from dorsey_as.data.loaders import load_sample_data
from dorsey_as.data_quality.report import write_data_quality_report
from dorsey_as.data_quality.validators import filter_financials_as_of, run_data_quality_checks
from dorsey_as.models import ScoreResult, TargetPortfolio
from dorsey_as.portfolio.constructor import build_target_portfolio
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


def _load_checked_sample_data(data_dir: Path, output_dir: Path, config: AppConfig, as_of_date: str | None = None):
    stocks, financials, markets = load_sample_data(data_dir)
    effective_as_of = as_of_date or _default_as_of_date(markets)
    report = run_data_quality_checks(effective_as_of, stocks, financials, markets, data_quality_config=config.data_quality)
    write_data_quality_report(report, output_dir / "data_quality_report.csv")
    if not report.passed:
        reasons = "; ".join(issue.message for issue in report.blocking_issues)
        print(f"Data quality check failed for {effective_as_of}: {reasons}")
        raise SystemExit(1)
    return stocks, filter_financials_as_of(financials, effective_as_of), markets, report


def _build_scores_and_portfolio(data_dir: Path, output_dir: Path, config: AppConfig, as_of_date: str | None = None) -> tuple[list[ScoreResult], TargetPortfolio, dict[str, float]]:
    stocks, financials, markets, _report = _load_checked_sample_data(data_dir, output_dir, config, as_of_date)
    scores = calculate_scores(stocks, financials, markets, scoring_config=config.scoring)
    portfolio = build_target_portfolio(scores, stocks, portfolio_config=config.portfolio)
    prices = {symbol: market.close_price for symbol, market in markets.items()}
    return scores, portfolio, prices


def check_data_quality(data_dir: Path, output_dir: Path, as_of_date: str | None = None, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    stocks, financials, markets = load_sample_data(data_dir)
    effective_as_of = as_of_date or _default_as_of_date(markets)
    report = run_data_quality_checks(effective_as_of, stocks, financials, markets, data_quality_config=config.data_quality)
    output_path = output_dir / "data_quality_report.csv"
    write_data_quality_report(report, output_path)
    status = "passed" if report.passed else "failed"
    print(f"Data quality {status} for {effective_as_of}; wrote report to {output_path}")
    return output_path


def run_score(data_dir: Path, output_dir: Path, as_of_date: str | None = None, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    stocks, financials, markets, _report = _load_checked_sample_data(data_dir, output_dir, config, as_of_date)
    scores = calculate_scores(stocks, financials, markets, scoring_config=config.scoring)
    output_path = output_dir / "scores.csv"
    _write_scores(output_path, scores)
    generate_run_report(output_dir, config, config_path or DEFAULT_CONFIG_PATH)
    print(f"Wrote {len(scores)} scores to {output_path}")
    return output_path


def build_portfolio(data_dir: Path, output_dir: Path, as_of_date: str | None = None, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    scores, portfolio, _prices = _build_scores_and_portfolio(data_dir, output_dir, config, as_of_date)
    _write_scores(output_dir / "scores.csv", scores)
    output_path = output_dir / "target_portfolio.csv"
    _write_portfolio(output_path, portfolio)
    print(f"Wrote {len(portfolio.positions)} target positions to {output_path}")
    return output_path


def paper_rebalance(data_dir: Path, output_dir: Path, cash: float | None, as_of_date: str | None = None, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
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
    print(f"Simulated {len(orders)} paper orders; wrote trades to {output_dir / 'paper_trades.csv'}")
    return output_dir / "paper_trades.csv"


def run_backtest(data_dir: Path, output_dir: Path, cash: float | None = None, config_path: Path | None = None) -> Path:
    config = load_config(config_path)
    engine = BacktestEngine.from_sample_data(
        data_dir=data_dir,
        output_dir=output_dir,
        config=_runtime_backtest_config(config, cash),
        scoring_config=config.scoring,
        portfolio_config=config.portfolio,
        data_quality_config=config.data_quality,
    )
    result = engine.run()
    generate_backtest_report(output_dir, config, config_path or DEFAULT_CONFIG_PATH)
    print(
        "Backtest complete: "
        f"{len(result.equity_curve)} equity points, "
        f"{len(result.trades)} trade records; "
        f"wrote outputs to {output_dir}"
    )
    return output_dir / "backtest_equity_curve.csv"


def generate_report(data_dir: Path, output_dir: Path, config_path: Path | None = None) -> tuple[Path, Path]:
    config = load_config(config_path)
    run_path = generate_run_report(output_dir, config, config_path or DEFAULT_CONFIG_PATH)
    backtest_path = generate_backtest_report(output_dir, config, config_path or DEFAULT_CONFIG_PATH)
    print(f"Wrote Markdown reports to {run_path} and {backtest_path}")
    return run_path, backtest_path


def _add_config_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=Path, default=None, help="Path to YAML config file. Defaults to config/default.yaml.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m dorsey_as")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_SAMPLE_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)

    quality = subparsers.add_parser("check-data-quality", help="Validate local sample CSV data quality and write a report.")
    _add_config_arg(quality)
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
    elif args.command == "generate-report":
        generate_report(args.data_dir, args.output_dir, config_path=args.config)
    else:
        parser.error(f"unknown command: {args.command}")
