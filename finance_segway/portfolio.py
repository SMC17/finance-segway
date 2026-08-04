"""Long-horizon liquidity and total-portfolio reference engines."""
from __future__ import annotations

from typing import Sequence

from .common import EPS, require_finite, require_nonnegative


def liquidity_coverage(liquid_assets: float, projected_calls: Sequence[float],
                       projected_distributions: Sequence[float],
                       spending: Sequence[float]) -> list[float]:
    if not (len(projected_calls) == len(projected_distributions) == len(spending)):
        raise ValueError("liquidity vectors must have equal length")
    cash = require_nonnegative("liquid_assets", liquid_assets)
    output = []
    for calls, distributions, spend in zip(projected_calls, projected_distributions, spending):
        cash += float(distributions) - float(calls) - float(spend)
        output.append(cash)
    return output


def denominator_effect(private_nav: float, public_nav: float,
                       public_drawdown: float) -> float:
    private_nav = require_nonnegative("private_nav", private_nav)
    public_nav = require_nonnegative("public_nav", public_nav)
    shocked_public = public_nav * (1.0 + require_finite("public_drawdown", public_drawdown))
    total = private_nav + shocked_public
    return 0.0 if total <= EPS else private_nav / total
