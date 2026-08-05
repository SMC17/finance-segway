"""Stage-1 covariance / risk primitives — design capacity 50.

This module mirrors the Stage-0 API so promotion is a gate, not a rewrite.
Until the Stage-1 evidence pack exists, callers should continue to use
`research.ram.simple_covariance` (cap 10).

When Stage-1 is promoted:
- raise the enforced cap to MAX_STAGE1_DESIGN_UNIVERSE
- add tests and a bench under research/ram/evidence/
- keep pure-Python clarity first; profile before any acceleration
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

# Design target. Enforced only after Stage-1 evidence is complete.
MAX_STAGE1_DESIGN_UNIVERSE = 50

# Temporary runtime guard: still Stage-0 sized until promotion.
_RUNTIME_CAP = 10


@dataclass(frozen=True)
class RiskResult:
    variance: float
    volatility: float
    weights: tuple[float, ...]


def _validate(n: int) -> None:
    if n < 1:
        raise ValueError("universe must contain at least one name")
    if n > _RUNTIME_CAP:
        raise ValueError(
            f"Stage-1 runtime cap is still {_RUNTIME_CAP} until evidence promotion; "
            f"design capacity is {MAX_STAGE1_DESIGN_UNIVERSE}. Received {n}."
        )


def portfolio_variance(weights: Sequence[float], cov: Sequence[Sequence[float]]) -> float:
    n = len(weights)
    _validate(n)
    if len(cov) != n or any(len(row) != n for row in cov):
        raise ValueError("covariance matrix must be square and match weight length")
    total = 0.0
    for i in range(n):
        for j in range(n):
            total += weights[i] * cov[i][j] * weights[j]
    return total


def equal_weight_risk(cov: Sequence[Sequence[float]]) -> RiskResult:
    n = len(cov)
    _validate(n)
    w = tuple(1.0 / n for _ in range(n))
    var = portfolio_variance(w, cov)
    return RiskResult(variance=var, volatility=math.sqrt(max(var, 0.0)), weights=w)


def inverse_vol_weights(vols: Sequence[float]) -> tuple[float, ...]:
    n = len(vols)
    _validate(n)
    if any(v <= 0 for v in vols):
        raise ValueError("volatilities must be positive")
    inv = [1.0 / v for v in vols]
    s = sum(inv)
    return tuple(x / s for x in inv)


def is_positive_semidefinite(cov: Sequence[Sequence[float]], tol: float = 1e-9) -> bool:
    n = len(cov)
    _validate(n)
    if any(len(row) != n for row in cov):
        return False
    for i in range(n):
        for j in range(i + 1, n):
            if abs(cov[i][j] - cov[j][i]) > tol:
                return False
    L = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = sum(L[i][k] * L[j][k] for k in range(j))
            if i == j:
                val = cov[i][i] - s
                if val <= tol:
                    return False
                L[i][j] = math.sqrt(val)
            else:
                if abs(L[j][j]) < tol:
                    return False
                L[i][j] = (cov[i][j] - s) / L[j][j]
    return True
