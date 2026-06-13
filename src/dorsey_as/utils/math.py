from __future__ import annotations


def clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    if denominator == 0:
        return default
    return numerator / denominator


def average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def score_ratio(value: float, excellent: float) -> float:
    if excellent <= 0:
        return 0.0
    return clamp(value / excellent * 100.0)
