from __future__ import annotations

import csv
from pathlib import Path

from dorsey_as.backtest.metrics import calculate_metrics
from dorsey_as.backtest.models import (
    BacktestConfig,
    BacktestResult,
    BacktestTrade,
    EquityPoint,
    HistoricalMarketSnapshot,
    HoldingSnapshot,
    TradeRequest,
    TradeValidation,
    TradingCalendarEntry,
)
from dorsey_as.data.loaders import (
    load_financial_snapshots,
    load_historical_market_snapshots,
    load_stock_basic,
    load_trading_calendar,
)
from dorsey_as.data_quality.report import write_data_quality_report
from dorsey_as.data_quality.validators import filter_financials_as_of, run_data_quality_checks
from dorsey_as.models import MarketSnapshot, PortfolioPosition, TargetPortfolio
from dorsey_as.portfolio.constructor import build_target_portfolio
from dorsey_as.scoring import calculate_scores


class BacktestEngine:
    def __init__(
        self,
        config: BacktestConfig,
        stocks: dict | None = None,
        financials: dict | None = None,
        historical_market: dict[str, dict[str, HistoricalMarketSnapshot]] | None = None,
        calendar: list[TradingCalendarEntry] | None = None,
        output_dir: Path | None = None,
    ) -> None:
        self.config = config
        self.stocks = stocks or {}
        self.financials = financials or {}
        self.historical_market = historical_market or {}
        self.calendar = calendar or []
        self.output_dir = output_dir
        self.cash = config.initial_cash
        self.positions: dict[str, float] = {}
        self.cost_basis: dict[str, float] = {}
        self.trades: list[BacktestTrade] = []
        self.equity_curve: list[EquityPoint] = []
        self.holdings: list[HoldingSnapshot] = []
        self.audit_log: list[dict[str, str | int | bool]] = []

    @classmethod
    def from_sample_data(cls, data_dir: Path, output_dir: Path, config: BacktestConfig | None = None) -> "BacktestEngine":
        return cls(
            config=config or BacktestConfig(),
            stocks=load_stock_basic(data_dir / "stock_basic.csv"),
            financials=load_financial_snapshots(data_dir / "financial_snapshot.csv"),
            historical_market=load_historical_market_snapshots(data_dir / "historical_market_snapshot.csv"),
            calendar=load_trading_calendar(data_dir / "trading_calendar.csv"),
            output_dir=output_dir,
        )

    def validate_trade(self, request: TradeRequest, snapshot: HistoricalMarketSnapshot) -> TradeValidation:
        side = request.side.upper()
        if snapshot.is_suspended:
            return TradeValidation(False, "suspended")
        if side == "BUY" and snapshot.is_limit_up:
            return TradeValidation(False, "limit_up_no_buy")
        if side == "SELL" and snapshot.is_limit_down:
            return TradeValidation(False, "limit_down_no_sell")
        if request.quantity <= 0:
            return TradeValidation(False, "non_positive_quantity")
        if side not in {"BUY", "SELL"}:
            return TradeValidation(False, "invalid_side")
        return TradeValidation(True, "")

    def run(self, as_of_override: str | None = None) -> BacktestResult:
        if not self.calendar:
            raise ValueError("trading calendar is empty")

        for entry in self.calendar:
            market_by_symbol = self.historical_market.get(entry.trade_date, {})
            if entry.is_rebalance_date:
                self._check_rebalance_data_quality(entry.trade_date, market_by_symbol, as_of_override)
                self._rebalance(entry.trade_date, market_by_symbol, as_of_override)
            self._mark_to_market(entry.trade_date, market_by_symbol)

        metrics = calculate_metrics(self.equity_curve, self.trades)
        result = BacktestResult(self.equity_curve, self.trades, self.holdings, metrics)
        if self.output_dir is not None:
            self.write_outputs(result, self.output_dir)
        return result

    def _market_snapshots_from_historical(
        self,
        trade_date: str,
        market_by_symbol: dict[str, HistoricalMarketSnapshot],
    ) -> dict[str, MarketSnapshot]:
        return {
            symbol: MarketSnapshot(
                symbol=symbol,
                trade_date=trade_date,
                close_price=snapshot.close_price,
                market_cap=snapshot.close_price * 100_000_000,
                pe=20.0,
                pb=2.0,
                ev_to_fcf=15.0,
                fcf_yield=0.06,
                dividend_yield=0.02,
            )
            for symbol, snapshot in market_by_symbol.items()
        }

    def _check_rebalance_data_quality(
        self,
        trade_date: str,
        market_by_symbol: dict[str, HistoricalMarketSnapshot],
        as_of_override: str | None,
    ) -> None:
        as_of_date = as_of_override or trade_date
        market_snapshots = self._market_snapshots_from_historical(trade_date, market_by_symbol)
        report = run_data_quality_checks(
            as_of_date,
            self.stocks,
            self.financials,
            market_snapshots,
            historical_market={trade_date: market_by_symbol},
            calendar=self.calendar,
        )
        self.audit_log.append(
            {
                "trade_date": trade_date,
                "event": "data_quality_check",
                "passed": report.passed,
                "blocking_issues": len(report.blocking_issues),
                "warnings": len(report.warnings),
            }
        )
        if self.output_dir is not None:
            write_data_quality_report(report, self.output_dir / "data_quality_report.csv")
            self._write_audit_log(self.output_dir / "backtest_audit_log.csv")
        if not report.passed:
            reasons = "; ".join(issue.message for issue in report.blocking_issues)
            print(f"Backtest data quality check failed for {as_of_date}: {reasons}")
            raise SystemExit(1)

    def _rebalance(self, trade_date: str, market_by_symbol: dict[str, HistoricalMarketSnapshot], as_of_override: str | None = None) -> None:
        as_of_date = as_of_override or trade_date
        market_snapshots = {
            symbol: MarketSnapshot(
                symbol=symbol,
                trade_date=trade_date,
                close_price=snapshot.close_price,
                market_cap=snapshot.close_price * 100_000_000,
                pe=20.0,
                pb=2.0,
                ev_to_fcf=15.0,
                fcf_yield=0.06,
                dividend_yield=0.02,
            )
            for symbol, snapshot in market_by_symbol.items()
        }
        scores = calculate_scores(self.stocks, filter_financials_as_of(self.financials, as_of_date), market_snapshots)
        target = build_target_portfolio(scores, self.stocks)
        self._execute_target_portfolio(trade_date, target, market_by_symbol)

    def _execute_target_portfolio(
        self,
        trade_date: str,
        target: TargetPortfolio,
        market_by_symbol: dict[str, HistoricalMarketSnapshot],
    ) -> None:
        total_value = self._portfolio_value(market_by_symbol)
        target_weights = {position.symbol: position.target_weight for position in target.positions}
        ordered_symbols = sorted(set(self.positions) | set(target_weights))

        for symbol in ordered_symbols:
            snapshot = market_by_symbol.get(symbol)
            if snapshot is None or snapshot.close_price <= 0:
                self._record_skipped(trade_date, symbol, "BUY" if target_weights.get(symbol, 0.0) > 0 else "SELL", 0.0, 0.0, "missing_price")
                continue
            current_quantity = self.positions.get(symbol, 0.0)
            current_value = current_quantity * snapshot.close_price
            desired_value = total_value * target_weights.get(symbol, 0.0)
            diff_value = desired_value - current_value
            if abs(diff_value) < 1e-6:
                continue
            side = "BUY" if diff_value > 0 else "SELL"
            quantity = abs(diff_value) / snapshot.close_price
            if side == "SELL":
                quantity = min(quantity, current_quantity)
            self._execute_trade(trade_date, TradeRequest(symbol, side, quantity, snapshot.close_price), snapshot)

    def _execute_trade(self, trade_date: str, request: TradeRequest, snapshot: HistoricalMarketSnapshot) -> None:
        validation = self.validate_trade(request, snapshot)
        if not validation.accepted:
            self._record_skipped(trade_date, request.symbol, request.side, request.quantity, request.price, validation.reason)
            return

        amount = request.quantity * request.price
        cost = self.config.transaction_cost(request.side, request.quantity, request.price)
        if request.side == "BUY":
            cash_required = amount + cost.total_cost
            if cash_required > self.cash + 1e-8:
                affordable_quantity = max(0.0, (self.cash - cost.total_cost) / request.price)
                if affordable_quantity <= 0:
                    self._record_skipped(trade_date, request.symbol, request.side, request.quantity, request.price, "insufficient_cash")
                    return
                request = TradeRequest(request.symbol, request.side, affordable_quantity, request.price)
                amount = request.quantity * request.price
                cost = self.config.transaction_cost(request.side, request.quantity, request.price)
            self.cash -= amount + cost.total_cost
            old_quantity = self.positions.get(request.symbol, 0.0)
            old_cost = self.cost_basis.get(request.symbol, 0.0) * old_quantity
            self.positions[request.symbol] = old_quantity + request.quantity
            self.cost_basis[request.symbol] = (old_cost + amount + cost.total_cost) / self.positions[request.symbol]
        else:
            current_quantity = self.positions.get(request.symbol, 0.0)
            if request.quantity > current_quantity + 1e-8:
                self._record_skipped(trade_date, request.symbol, request.side, request.quantity, request.price, "shorting_not_allowed")
                return
            self.cash += amount - cost.total_cost
            remaining = current_quantity - request.quantity
            if remaining <= 1e-8:
                self.positions.pop(request.symbol, None)
                self.cost_basis.pop(request.symbol, None)
            else:
                self.positions[request.symbol] = remaining

        self.cash = max(self.cash, 0.0)
        self.trades.append(
            BacktestTrade(
                trade_date=trade_date,
                symbol=request.symbol,
                side=request.side,
                quantity=round(request.quantity, 6),
                price=round(request.price, 6),
                amount=round(amount, 6),
                commission=cost.commission,
                stamp_duty=cost.stamp_duty,
                slippage=cost.slippage,
                status="FILLED",
            )
        )

    def _record_skipped(self, trade_date: str, symbol: str, side: str, quantity: float, price: float, reason: str) -> None:
        self.trades.append(
            BacktestTrade(
                trade_date=trade_date,
                symbol=symbol,
                side=side,
                quantity=round(max(quantity, 0.0), 6),
                price=round(max(price, 0.0), 6),
                amount=round(max(quantity, 0.0) * max(price, 0.0), 6),
                commission=0.0,
                stamp_duty=0.0,
                slippage=0.0,
                status="SKIPPED",
                reason=reason,
            )
        )

    def _portfolio_value(self, market_by_symbol: dict[str, HistoricalMarketSnapshot]) -> float:
        return self.cash + sum(
            quantity * market_by_symbol[symbol].close_price
            for symbol, quantity in self.positions.items()
            if symbol in market_by_symbol
        )

    def _mark_to_market(self, trade_date: str, market_by_symbol: dict[str, HistoricalMarketSnapshot]) -> None:
        holdings_value = 0.0
        for symbol, quantity in sorted(self.positions.items()):
            snapshot = market_by_symbol.get(symbol)
            if snapshot is None:
                continue
            market_value = quantity * snapshot.close_price
            holdings_value += market_value
            self.holdings.append(
                HoldingSnapshot(
                    trade_date=trade_date,
                    symbol=symbol,
                    quantity=round(quantity, 6),
                    price=round(snapshot.close_price, 6),
                    market_value=round(market_value, 6),
                )
            )
        total_value = self.cash + holdings_value
        self.equity_curve.append(
            EquityPoint(
                trade_date=trade_date,
                cash=round(self.cash, 6),
                holdings_value=round(holdings_value, 6),
                total_value=round(total_value, 6),
                net_value=round(total_value / self.config.initial_cash, 6),
            )
        )

    def write_outputs(self, result: BacktestResult, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        self._write_equity_curve(result, output_dir / "backtest_equity_curve.csv")
        self._write_trades(result, output_dir / "backtest_trades.csv")
        self._write_holdings(result, output_dir / "backtest_holdings.csv")
        self._write_metrics(result, output_dir / "backtest_metrics.csv")
        self._write_audit_log(output_dir / "backtest_audit_log.csv")

    def _write_equity_curve(self, result: BacktestResult, path: Path) -> None:
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["trade_date", "cash", "holdings_value", "total_value", "net_value"])
            writer.writeheader()
            for point in result.equity_curve:
                writer.writerow(point.__dict__)

    def _write_trades(self, result: BacktestResult, path: Path) -> None:
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=[
                    "trade_date",
                    "symbol",
                    "side",
                    "quantity",
                    "price",
                    "amount",
                    "commission",
                    "stamp_duty",
                    "slippage",
                    "status",
                    "reason",
                ],
            )
            writer.writeheader()
            for trade in result.trades:
                writer.writerow(trade.__dict__)

    def _write_holdings(self, result: BacktestResult, path: Path) -> None:
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["trade_date", "symbol", "quantity", "price", "market_value"])
            writer.writeheader()
            for holding in result.holdings:
                writer.writerow(holding.__dict__)

    def _write_metrics(self, result: BacktestResult, path: Path) -> None:
        metrics = result.metrics
        if metrics is None:
            return
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["metric", "value"])
            writer.writeheader()
            for key, value in metrics.__dict__.items():
                writer.writerow({"metric": key, "value": "" if value is None else value})

    def _write_audit_log(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["trade_date", "event", "passed", "blocking_issues", "warnings"])
            writer.writeheader()
            writer.writerows(self.audit_log)
