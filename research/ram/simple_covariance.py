"""Stage-0 pure-Python covariance risk engine capped at ten assets."""

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


def _validate_universe(size: int) -> None:
    if size < 1:
        raise ValueError("universe must contain at least one asset")
    if size > MAX_STAGE0_UNIVERSE:
        raise ValueError(
            f"Stage-0 RAM is capped at {MAX_STAGE0_UNIVERSE} assets; got {size}"
        )


def _validated_covariance(
    covariance: Sequence[Sequence[float]], *, tolerance: float = 1e-9
) -> tuple[tuple[float, ...], ...]:
    size = len(covariance)
    _validate_universe(size)
    if any(len(row) != size for row in covariance):
        raise ValueError("covariance matrix must be square")
    matrix = tuple(tuple(float(value) for value in row) for row in covariance)
    if any(not math.isfinite(value) for row in matrix for value in row):
        raise ValueError("covariance matrix must contain finite values")
    for index in range(size):
        if matrix[index][index] < -tolerance:
            raise ValueError("covariance diagonal cannot be negative")
        for other in range(index + 1, size):
            if not math.isclose(
                matrix[index][other],
                matrix[other][index],
                rel_tol=0.0,
                abs_tol=tolerance,
            ):
                raise ValueError("covariance matrix must be symmetric")
    return matrix


def portfolio_variance(
    weights: Sequence[float], covariance: Sequence[Sequence[float]]
) -> float:
    """Return ``w'Σw`` after finite, shape, and symmetry validation."""

    size = len(weights)
    _validate_universe(size)
    numeric_weights = tuple(float(weight) for weight in weights)
    if any(not math.isfinite(weight) for weight in numeric_weights):
        raise ValueError("weights must be finite")
    matrix = _validated_covariance(covariance)
    if len(matrix) != size:
        raise ValueError("covariance size must match weight length")
    if not is_positive_semidefinite(matrix):
        raise ValueError("covariance matrix must be positive semidefinite")
    variance = sum(
        numeric_weights[row] * matrix[row][column] * numeric_weights[column]
        for row in range(size)
        for column in range(size)
    )
    if variance < -1e-9:
        raise ValueError("covariance produces materially negative variance")
    return max(variance, 0.0)


def equal_weight_risk(covariance: Sequence[Sequence[float]]) -> RiskResult:
    size = len(covariance)
    _validate_universe(size)
    weights = tuple(1.0 / size for _ in range(size))
    variance = portfolio_variance(weights, covariance)
    return RiskResult(variance, math.sqrt(variance), weights)


def inverse_vol_weights(volatilities: Sequence[float]) -> tuple[float, ...]:
    _validate_universe(len(volatilities))
    values = tuple(float(value) for value in volatilities)
    if any(not math.isfinite(value) or value <= 0 for value in values):
        raise ValueError("volatilities must be finite and positive")
    inverse = tuple(1.0 / value for value in values)
    total = math.fsum(inverse)
    return tuple(value / total for value in inverse)


def is_positive_semidefinite(
    covariance: Sequence[Sequence[float]], tolerance: float = 1e-9
) -> bool:
    """Semidefinite-aware Cholesky test without external dependencies.

    A zero pivot is allowed only when its remaining cross-residual is also zero.
    This accepts singular PSD matrices, including the zero matrix, while
    rejecting asymmetric and indefinite inputs.
    """

    try:
        matrix = _validated_covariance(covariance, tolerance=tolerance)
    except (TypeError, ValueError):
        return False
    size = len(matrix)
    lower = [[0.0] * size for _ in range(size)]
    for row in range(size):
        for column in range(row + 1):
            residual = matrix[row][column] - math.fsum(
                lower[row][prior] * lower[column][prior]
                for prior in range(column)
            )
            if row == column:
                if residual < -tolerance:
                    return False
                lower[row][column] = math.sqrt(max(residual, 0.0))
            elif lower[column][column] > tolerance:
                lower[row][column] = residual / lower[column][column]
            elif abs(residual) > tolerance:
                return False
    return True


def frobenius_norm(covariance: Sequence[Sequence[float]]) -> float:
    matrix = _validated_covariance(covariance)
    return math.sqrt(math.fsum(value * value for row in matrix for value in row))
