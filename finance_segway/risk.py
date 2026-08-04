"""Systematic-research, transaction-cost, and risk reference engines."""
from __future__ import annotations

from math import sqrt
from statistics import fmean, pstdev
from typing import Sequence

from .common import EPS, require_nonnegative, require_positive


def cumulative_returns(returns: Sequence[float]) -> list[float]:
    wealth = 1.0
    output = []
    for value in returns:
        wealth *= 1.0 + float(value)
        output.append(wealth - 1.0)
    return output


def max_drawdown(returns: Sequence[float]) -> float:
    wealth = peak = 1.0
    worst = 0.0
    for value in returns:
        wealth *= 1.0 + float(value)
        peak = max(peak, wealth)
        worst = min(worst, wealth / peak - 1.0)
    return worst


def sharpe_ratio(returns: Sequence[float], *, periods_per_year: int = 252,
                 risk_free_per_period: float = 0.0) -> float:
    values = [float(value) - risk_free_per_period for value in returns]
    if len(values) < 2:
        return 0.0
    volatility = pstdev(values)
    return 0.0 if volatility <= EPS else sqrt(periods_per_year) * fmean(values) / volatility


def sortino_ratio(returns: Sequence[float], *, periods_per_year: int = 252,
                  target_per_period: float = 0.0) -> float:
    values = [float(value) - target_per_period for value in returns]
    if not values:
        return 0.0
    downside = [min(0.0, value) for value in values]
    deviation = sqrt(fmean(value * value for value in downside))
    return 0.0 if deviation <= EPS else sqrt(periods_per_year) * fmean(values) / deviation


def historical_var(returns: Sequence[float], confidence: float = 0.95) -> float:
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")
    values = sorted(float(value) for value in returns)
    if not values:
        raise ValueError("returns cannot be empty")
    index = max(0, min(len(values) - 1, int((1.0 - confidence) * len(values))))
    return -values[index]


def expected_shortfall(returns: Sequence[float], confidence: float = 0.95) -> float:
    threshold = -historical_var(returns, confidence)
    tail = [float(value) for value in returns if float(value) <= threshold]
    return -fmean(tail) if tail else 0.0


def apply_transaction_costs(gross_returns: Sequence[float], turnover: Sequence[float],
                            cost_bps: float) -> list[float]:
    if len(gross_returns) != len(turnover):
        raise ValueError("gross_returns and turnover must have equal length")
    cost_rate = require_nonnegative("cost_bps", cost_bps) / 10_000.0
    return [float(ret) - abs(float(turn)) * cost_rate
            for ret, turn in zip(gross_returns, turnover)]


def walk_forward_splits(observations: int, *, train: int, test: int,
                        step: int | None = None,
                        anchored: bool = False) -> list[tuple[range, range]]:
    if observations <= 0 or train <= 0 or test <= 0:
        raise ValueError("observations, train and test must be positive")
    step = test if step is None else step
    if step <= 0:
        raise ValueError("step must be positive")
    output: list[tuple[range, range]] = []
    train_start, train_end = 0, train
    while train_end + test <= observations:
        output.append((range(train_start, train_end), range(train_end, train_end + test)))
        train_end += step
        if not anchored:
            train_start += step
    return output


def capacity_adjusted_returns(gross_returns: Sequence[float], turnover: Sequence[float],
                              *, capital: float, adv: Sequence[float],
                              linear_cost_bps: float,
                              impact_coefficient: float) -> list[float]:
    if not (len(gross_returns) == len(turnover) == len(adv)):
        raise ValueError("gross_returns, turnover and adv must have equal length")
    capital = require_positive("capital", capital)
    impact_coefficient = require_nonnegative("impact_coefficient", impact_coefficient)
    linear_rate = require_nonnegative("linear_cost_bps", linear_cost_bps) / 10_000.0
    output = []
    for gross, turn, daily_volume in zip(gross_returns, turnover, adv):
        daily_volume = require_positive("adv", daily_volume)
        traded = abs(float(turn)) * capital
        participation = traded / daily_volume
        cost = abs(float(turn)) * linear_rate + impact_coefficient * participation**1.5
        output.append(float(gross) - cost)
    return output
