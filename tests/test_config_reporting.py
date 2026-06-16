from pathlib import Path

import pytest

from dorsey_as.backtest.models import BacktestConfig as RuntimeBacktestConfig
from dorsey_as.config.loader import ConfigError, load_config
from dorsey_as.config.models import PortfolioConfig, ScoringConfig
from dorsey_as.data.loaders import load_sample_data
from dorsey_as.data_quality.validators import run_data_quality_checks
from dorsey_as.models import ScoreResult, StockBasic
from dorsey_as.portfolio.constructor import build_target_portfolio
from dorsey_as.reporting.markdown import generate_backtest_report, generate_run_report
from dorsey_as.scoring import calculate_score


def test_default_config_loads_successfully() -> None:
    config = load_config()

    assert config.scoring.quality_weight == 0.35
    assert config.portfolio.cash_reserve == 0.05
    assert config.transaction_cost.commission_rate == 0.0003
    assert config.report.output_format == "markdown"


def test_missing_config_file_raises_clear_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="Config file not found"):
        load_config(tmp_path / "missing.yaml")


def test_invalid_config_is_rejected(tmp_path: Path) -> None:
    bad_config = tmp_path / "bad.yaml"
    bad_config.write_text(
        """
scoring:
  quality_weight: -0.1
  moat_weight: 0.3
  valuation_weight: 0.25
  risk_weight: 0.1
transaction_cost:
  commission_rate: -0.0003
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError):
        load_config(bad_config)


def test_composite_score_uses_configured_weights() -> None:
    stocks, financials, markets = load_sample_data(Path("data/sample"))
    symbol = "600519.SH"

    score = calculate_score(
        stocks[symbol],
        financials[symbol],
        markets[symbol],
        scoring_config=ScoringConfig(quality_weight=1.0, moat_weight=0.0, valuation_weight=0.0, risk_weight=0.0),
    )

    assert score.composite_score == score.quality_score


def test_portfolio_uses_configured_limits() -> None:
    stocks = {
        f"0000{i:02d}.SZ": StockBasic(f"0000{i:02d}.SZ", f"Stock {i}", "Tech")
        for i in range(1, 10)
    }
    scores = [
        ScoreResult(symbol=symbol, quality_score=80, moat_score=80, valuation_score=80, risk_score=100, composite_score=100 - i, blocked=False)
        for i, symbol in enumerate(stocks)
    ]

    portfolio = build_target_portfolio(
        scores,
        stocks,
        portfolio_config=PortfolioConfig(max_positions=3, max_stock_weight=0.04, max_industry_weight=0.08, cash_reserve=0.10),
    )

    assert len(portfolio.positions) == 2
    assert all(position.target_weight == 0.04 for position in portfolio.positions)
    assert portfolio.cash_weight == 0.10


def test_transaction_cost_uses_configured_parameters() -> None:
    runtime_config = RuntimeBacktestConfig(
        initial_cash=100_000.0,
        commission_rate=0.001,
        minimum_commission=1.0,
        stamp_duty_rate=0.002,
        slippage_rate=0.003,
    )

    cost = runtime_config.transaction_cost("SELL", quantity=1000, price=10)

    assert cost.commission == 10.0
    assert cost.stamp_duty == 20.0
    assert cost.slippage == 30.0
    assert cost.total_cost == 60.0


def test_data_quality_uses_configured_stale_threshold() -> None:
    config = load_config()
    config.data_quality.stale_days_threshold = 1
    stocks, financials, markets = load_sample_data(Path("data/sample"))

    report = run_data_quality_checks("2024-03-29", stocks, financials, markets, data_quality_config=config.data_quality)

    assert any(issue.check_name == "StaleDataCheck" for issue in report.issues)


def test_generate_report_writes_markdown_files(tmp_path: Path) -> None:
    config = load_config()
    run_report = generate_run_report(output_dir=tmp_path, config=config, config_path=Path("config/default.yaml"))
    backtest_report = generate_backtest_report(output_dir=tmp_path, config=config, config_path=Path("config/default.yaml"))

    assert run_report.exists()
    assert backtest_report.exists()
    run_text = run_report.read_text(encoding="utf-8")
    backtest_text = backtest_report.read_text(encoding="utf-8")
    assert "No real-money trading" in run_text
    assert "Top Scores" in run_text
    assert "Backtest Metrics" in backtest_text
    assert "No real broker connection" in backtest_text
