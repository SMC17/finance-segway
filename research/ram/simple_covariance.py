\"\"\"Stage-0 RAM risk skeleton: simple covariance risk on a tiny universe.

This is deliberately minimal. It exists to establish the testing and
scaling pattern before any attempt at S&P 500 or larger universes.

Rules:
- Pure Python, no external numerical dependencies beyond the standard library.
- Every public function has a corresponding conservation or identity test.
- Universe size is hard-capped at 10 for Stage 0.
\"\"\"
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


MAX_STAGE0_UNIVERSE = 10


@dataclass(frozen=True)
class RiskResult:
    variance: float
    volatility: float
    weights: tuple[float, ...]


def _validate_universe(n: int) -> None:
    if n < 1:
        raise ValueError("universe must contain at least one name")
    if n > MAX_STAGE0_UNIVERSE:
        raise ValueError(
            f"Stage-0 RAM models are capped at {MAX_STAGE0_UNIVERSE} names; "
            f"received {n}. Promote only after Stage-0 gates pass."
        )


def portfolio_variance(weights: Sequence[float], cov: Sequence[Sequence[float]]) -> float:
    "\"\"\"w' Σ w. Simple triple loop; clarity over speed for Stage 0.\"\"\"
    n = len(weights)
    _validate_universe(n)
    if len(cov) != n or any(len(row) != n for row in cov):
        raise ValueError("covariance matrix must be square and match weight length")
    total = 0.0
    for i in range(n):
        for j in range(n):
            total += weights[i] * cov[i][j] * weights[j]
    return total


def equal_weight_risk(cov: Sequence[Sequence[float]]) -> RiskResult:
    n = len(cov)
    _validate_universe(n)
    w = tuple(1.0 / n for _ in range(n))
    var = portfolio_variance(w, cov)
    return RiskResult(variance=var, volatility=math.sqrt(max(var, 0.0)), weights=w)


def inverse_vol_weights(vols: Sequence[float]) -> tuple[float, ...]:
    n = len(vols)
    _validate_universe(n)
    if any(v <= 0 for v in vols):
        raise ValueError("volatilities must be positive")
    inv = [1.0 / v for v in vols]
    s = sum(inv)
    return tuple(x / s for x in inv)


def is_positive_semidefinite(cov: Sequence[Sequence[float]], tol: float = 1e-9) -> bool:
    "\"\"\"Stage-0 PSD check via Cholesky attempt (no external libs).

    For n <= 10 a simple Cholesky decomposition is sufficient and keeps the
    dependency surface zero. Returns False on any failure or negative pivot.
    \"\"\"
    n = len(cov)
    _validate_universe(n)
    if any(len(row) != n for row in cov):
        return False

    # Symmetry check
    for i in range(n):
        for j in range(i + 1, n):
            if abs(cov[i][j] - cov[j][i]) > tol:
                return False

    # Cholesky (in-place on a copy)
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


def frobenius_norm(cov: Sequence[Sequence[float]]) -> float:
    n = len(cov)
    _validate_universe(n)
    return math.sqrt(sum(cov[i][j] ** 2 for i in range(n) for j in range(n)))


if __name__ == "__main__":
    example_cov = [
        [0.04, 0.01, 0.00],
        [0.01, 0.09, 0.02],
        [0.00, 0.02, 0.16],
    ]
    res = equal_weight_risk(example_cov)
    print(f"Equal-weight variance={res.variance:.6f} vol={res.volatility:.6f}")
    print(f"Weights={res.weights}")
    print(f"PSD={is_positive_semidefinite(example_cov)}")
