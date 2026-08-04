"""Shared validation helpers for Finance-Segway reference engines."""
from __future__ import annotations

from math import isfinite

EPS = 1e-12


def require_finite(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def require_nonnegative(name: str, value: float) -> float:
    value = require_finite(name, value)
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return value


def require_positive(name: str, value: float) -> float:
    value = require_finite(name, value)
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def clamp(value: float, lower: float, upper: float) -> float:
    return min(upper, max(lower, value))
