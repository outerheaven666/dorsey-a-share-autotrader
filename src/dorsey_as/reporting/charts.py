from __future__ import annotations

from pathlib import Path

from dorsey_as.reporting.summary import read_csv_rows


def _points(values: list[float], width: int, height: int, padding: int) -> str:
    if len(values) < 2:
        return ""
    min_value = min(values)
    max_value = max(values)
    value_range = max(max_value - min_value, 1e-12)
    step = (width - padding * 2) / (len(values) - 1)
    coords = []
    for index, value in enumerate(values):
        x = padding + index * step
        y = height - padding - ((value - min_value) / value_range) * (height - padding * 2)
        coords.append(f"{x:.2f},{y:.2f}")
    return " ".join(coords)


def _fallback(title: str) -> str:
    return f"<div class=\"chart-empty\"><strong>{title}</strong>: Insufficient data, unable to generate chart.</div>"


def render_equity_curve_chart(path: Path) -> str:
    rows = read_csv_rows(path)
    values = [float(row["net_value"]) for row in rows if row.get("net_value")]
    if len(values) < 2:
        return _fallback("Equity Curve")
    width, height, padding = 720, 260, 36
    polyline = _points(values, width, height, padding)
    return f"""
<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="Equity Curve">
  <title>Equity Curve</title>
  <rect x="0" y="0" width="{width}" height="{height}" rx="8" fill="#ffffff" stroke="#d8dee9"/>
  <line x1="{padding}" y1="{height - padding}" x2="{width - padding}" y2="{height - padding}" stroke="#a7b0bd"/>
  <line x1="{padding}" y1="{padding}" x2="{padding}" y2="{height - padding}" stroke="#a7b0bd"/>
  <polyline fill="none" stroke="#1f6feb" stroke-width="3" points="{polyline}"/>
  <text x="{padding}" y="24" font-size="14" font-weight="700" fill="#1f2937">Equity Curve</text>
</svg>
""".strip()


def render_drawdown_chart(path: Path) -> str:
    rows = read_csv_rows(path)
    net_values = [float(row["net_value"]) for row in rows if row.get("net_value")]
    if len(net_values) < 2:
        return _fallback("Drawdown")
    peak = net_values[0]
    drawdowns: list[float] = []
    for value in net_values:
        peak = max(peak, value)
        drawdowns.append(value / peak - 1.0 if peak > 0 else 0.0)
    width, height, padding = 720, 260, 36
    polyline = _points(drawdowns, width, height, padding)
    return f"""
<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="Drawdown">
  <title>Drawdown</title>
  <rect x="0" y="0" width="{width}" height="{height}" rx="8" fill="#ffffff" stroke="#d8dee9"/>
  <line x1="{padding}" y1="{height - padding}" x2="{width - padding}" y2="{height - padding}" stroke="#a7b0bd"/>
  <line x1="{padding}" y1="{padding}" x2="{padding}" y2="{height - padding}" stroke="#a7b0bd"/>
  <polyline fill="none" stroke="#d1242f" stroke-width="3" points="{polyline}"/>
  <text x="{padding}" y="24" font-size="14" font-weight="700" fill="#1f2937">Drawdown</text>
</svg>
""".strip()
