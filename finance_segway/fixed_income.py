"""Fixed-income curve, pricing, duration, and convexity engines."""
from __future__ import annotations

from math import exp
from typing import Mapping

from .common import require_finite, require_nonnegative, require_positive


def linear_zero_rate(tenor: float, curve: Mapping[float, float]) -> float:
    if not curve:
        raise ValueError("curve cannot be empty")
    tenor = require_nonnegative("tenor", tenor)
    points = sorted((float(time), float(rate)) for time, rate in curve.items())
    if tenor <= points[0][0]:
        return points[0][1]
    if tenor >= points[-1][0]:
        return points[-1][1]
    for (time0, rate0), (time1, rate1) in zip(points, points[1:]):
        if time0 <= tenor <= time1:
            weight = (tenor - time0) / (time1 - time0)
            return rate0 + weight * (rate1 - rate0)
    raise RuntimeError("curve interpolation failed")


def bond_cash_flows(face: float, coupon_rate: float, maturity: float,
                    frequency: int = 2) -> list[tuple[float, float]]:
    face = require_positive("face", face)
    maturity = require_positive("maturity", maturity)
    coupon_rate = require_finite("coupon_rate", coupon_rate)
    if frequency <= 0:
        raise ValueError("frequency must be positive")
    periods_float = maturity * frequency
    periods = round(periods_float)
    if abs(periods - periods_float) > 1e-9:
        raise ValueError("maturity must align with coupon frequency")
    coupon = face * coupon_rate / frequency
    flows = [(period / frequency, coupon) for period in range(1, periods + 1)]
    flows[-1] = (maturity, flows[-1][1] + face)
    return flows


def bond_price(face: float, coupon_rate: float, maturity: float,
               yield_to_maturity: float, frequency: int = 2) -> float:
    ytm = require_finite("yield_to_maturity", yield_to_maturity)
    if 1.0 + ytm / frequency <= 0:
        raise ValueError("yield produces a nonpositive discount base")
    return sum(cash / ((1.0 + ytm / frequency) ** (time * frequency))
               for time, cash in bond_cash_flows(face, coupon_rate, maturity, frequency))


def bond_price_curve(face: float, coupon_rate: float, maturity: float,
                     zero_curve: Mapping[float, float], frequency: int = 2) -> float:
    return sum(cash * exp(-linear_zero_rate(time, zero_curve) * time)
               for time, cash in bond_cash_flows(face, coupon_rate, maturity, frequency))


def macaulay_duration(face: float, coupon_rate: float, maturity: float,
                      ytm: float, frequency: int = 2) -> float:
    price = bond_price(face, coupon_rate, maturity, ytm, frequency)
    weighted = sum(time * cash / ((1.0 + ytm / frequency) ** (time * frequency))
                   for time, cash in bond_cash_flows(face, coupon_rate, maturity, frequency))
    return weighted / price


def modified_duration(face: float, coupon_rate: float, maturity: float,
                      ytm: float, frequency: int = 2) -> float:
    return macaulay_duration(face, coupon_rate, maturity, ytm, frequency) / (1.0 + ytm / frequency)


def numerical_convexity(face: float, coupon_rate: float, maturity: float,
                        ytm: float, frequency: int = 2, bump: float = 1e-4) -> float:
    bump = require_positive("bump", bump)
    base = bond_price(face, coupon_rate, maturity, ytm, frequency)
    up = bond_price(face, coupon_rate, maturity, ytm + bump, frequency)
    down = bond_price(face, coupon_rate, maturity, ytm - bump, frequency)
    return (up + down - 2.0 * base) / (base * bump * bump)


def key_rate_dv01(*, face: float, coupon_rate: float, maturity: float,
                  zero_curve: Mapping[float, float], key_tenor: float,
                  bump: float = 1e-4, frequency: int = 2) -> float:
    base = bond_price_curve(face, coupon_rate, maturity, zero_curve, frequency)
    bumped = dict(zero_curve)
    if key_tenor not in bumped:
        bumped[key_tenor] = linear_zero_rate(key_tenor, zero_curve)
    bumped[key_tenor] += bump
    return base - bond_price_curve(face, coupon_rate, maturity, bumped, frequency)
