from __future__ import annotations

import csv
from pathlib import Path

from dorsey_as.models import PaperOrder, TargetPortfolio


class PaperBroker:
    """Deterministic paper broker with no real broker connectivity."""

    def __init__(self, cash: float, positions: dict[str, float], trade_log_path: Path) -> None:
        self.cash = cash
        self.positions = dict(positions)
        self.trade_log_path = trade_log_path

    @classmethod
    def from_state(cls, state_path: Path, trade_log_path: Path, default_cash: float = 1_000_000.0) -> "PaperBroker":
        if not state_path.exists():
            return cls(default_cash, {}, trade_log_path)

        cash = default_cash
        positions: dict[str, float] = {}
        with state_path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row["symbol"] == "CASH":
                    cash = float(row["quantity"])
                else:
                    positions[row["symbol"]] = float(row["quantity"])
        return cls(cash, positions, trade_log_path)

    def save_state(self, state_path: Path) -> None:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        with state_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["symbol", "quantity"])
            writer.writeheader()
            writer.writerow({"symbol": "CASH", "quantity": round(self.cash, 6)})
            for symbol, quantity in sorted(self.positions.items()):
                writer.writerow({"symbol": symbol, "quantity": round(quantity, 6)})

    def rebalance(self, target: TargetPortfolio, prices: dict[str, float]) -> list[PaperOrder]:
        if not target.positions:
            raise ValueError("target portfolio is empty; refusing to paper trade")

        total_value = self.cash + sum(quantity * prices.get(symbol, 0.0) for symbol, quantity in self.positions.items())
        orders: list[PaperOrder] = []

        for position in target.positions:
            price = prices.get(position.symbol)
            if price is None or price <= 0:
                raise ValueError(f"missing or invalid price for {position.symbol}; refusing to paper trade")

            current_quantity = self.positions.get(position.symbol, 0.0)
            current_value = current_quantity * price
            target_value = total_value * position.target_weight
            diff_value = target_value - current_value
            if abs(diff_value) < 1e-6:
                continue

            side = "BUY" if diff_value > 0 else "SELL"
            quantity = abs(diff_value) / price
            amount = quantity * price
            if side == "BUY":
                if amount > self.cash + 1e-6:
                    raise ValueError("insufficient paper cash; refusing to overbuy")
                self.cash -= amount
                self.positions[position.symbol] = current_quantity + quantity
            else:
                self.cash += amount
                remaining = current_quantity - quantity
                if remaining <= 1e-8:
                    self.positions.pop(position.symbol, None)
                else:
                    self.positions[position.symbol] = remaining

            orders.append(PaperOrder(position.symbol, side, quantity, price, amount))

        self._append_trade_log(orders)
        return orders

    def _append_trade_log(self, orders: list[PaperOrder]) -> None:
        if not orders:
            return
        self.trade_log_path.parent.mkdir(parents=True, exist_ok=True)
        write_header = not self.trade_log_path.exists()
        with self.trade_log_path.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["symbol", "side", "quantity", "price", "amount", "mode"])
            if write_header:
                writer.writeheader()
            for order in orders:
                writer.writerow(
                    {
                        "symbol": order.symbol,
                        "side": order.side,
                        "quantity": round(order.quantity, 6),
                        "price": round(order.price, 6),
                        "amount": round(order.amount, 6),
                        "mode": order.mode,
                    }
                )
