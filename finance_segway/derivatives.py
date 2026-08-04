"""Options and derivatives reference engines."""
from __future__ import annotations

from dataclasses import dataclass
from math import erf, exp, log, pi, sqrt

from .common import require_finite, require_nonnegative, require_positive


def normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + erf(value / sqrt(2.0)))


def normal_pdf(value: float) -> float:
    return exp(-0.5 * value * value) / sqrt(2.0 * pi)


@dataclass(frozen=True)
class BlackScholesResult:
    call: float
    put: float
    call_delta: float
    put_delta: float
    gamma: float
    vega: float
    call_theta: float
    put_theta: float
    call_rho: float
    put_rho: float


def black_scholes(spot: float, strike: float, maturity: float, rate: float,
                  volatility: float, dividend_yield: float = 0.0) -> BlackScholesResult:
    spot = require_positive("spot", spot)
    strike = require_positive("strike", strike)
    maturity = require_positive("maturity", maturity)
    volatility = require_positive("volatility", volatility)
    rate = require_finite("rate", rate)
    dividend_yield = require_finite("dividend_yield", dividend_yield)
    root_time = sqrt(maturity)
    d1 = (log(spot / strike) + (rate - dividend_yield + 0.5 * volatility**2) * maturity) / (volatility * root_time)
    d2 = d1 - volatility * root_time
    discounted_spot = spot * exp(-dividend_yield * maturity)
    discounted_strike = strike * exp(-rate * maturity)
    call = discounted_spot * normal_cdf(d1) - discounted_strike * normal_cdf(d2)
    put = discounted_strike * normal_cdf(-d2) - discounted_spot * normal_cdf(-d1)
    call_delta = exp(-dividend_yield * maturity) * normal_cdf(d1)
    put_delta = call_delta - exp(-dividend_yield * maturity)
    gamma = exp(-dividend_yield * maturity) * normal_pdf(d1) / (spot * volatility * root_time)
    vega = spot * exp(-dividend_yield * maturity) * normal_pdf(d1) * root_time
    theta_common = -spot * exp(-dividend_yield * maturity) * normal_pdf(d1) * volatility / (2 * root_time)
    call_theta = theta_common - rate * discounted_strike * normal_cdf(d2) + dividend_yield * discounted_spot * normal_cdf(d1)
    put_theta = theta_common + rate * discounted_strike * normal_cdf(-d2) - dividend_yield * discounted_spot * normal_cdf(-d1)
    return BlackScholesResult(
        call, put, call_delta, put_delta, gamma, vega, call_theta, put_theta,
        maturity * discounted_strike * normal_cdf(d2),
        -maturity * discounted_strike * normal_cdf(-d2),
    )


def implied_volatility(price: float, *, is_call: bool, spot: float, strike: float,
                       maturity: float, rate: float, dividend_yield: float = 0.0,
                       lower: float = 1e-6, upper: float = 8.0) -> float:
    price = require_nonnegative("price", price)
    def objective(volatility: float) -> float:
        result = black_scholes(spot, strike, maturity, rate, volatility, dividend_yield)
        return (result.call if is_call else result.put) - price
    left, right = lower, upper
    if objective(left) > 0 or objective(right) < 0:
        raise ValueError("option price is outside the Black-Scholes volatility bracket")
    for _ in range(180):
        mid = (left + right) / 2.0
        value = objective(mid)
        if abs(value) < 1e-10:
            return mid
        if value > 0:
            right = mid
        else:
            left = mid
    return (left + right) / 2.0


def american_binomial(*, spot: float, strike: float, maturity: float, rate: float,
                      volatility: float, dividend_yield: float = 0.0,
                      steps: int = 500, is_call: bool = True) -> float:
    spot = require_positive("spot", spot)
    strike = require_positive("strike", strike)
    maturity = require_positive("maturity", maturity)
    volatility = require_positive("volatility", volatility)
    if steps <= 0:
        raise ValueError("steps must be positive")
    dt = maturity / steps
    up = exp(volatility * sqrt(dt))
    down = 1.0 / up
    probability = (exp((rate - dividend_yield) * dt) - down) / (up - down)
    if not 0.0 <= probability <= 1.0:
        raise ValueError("invalid risk-neutral probability")
    discount = exp(-rate * dt)
    values = []
    for node in range(steps + 1):
        terminal_spot = spot * (up ** (steps - node)) * (down ** node)
        values.append(max(0.0, terminal_spot - strike if is_call else strike - terminal_spot))
    for step in range(steps - 1, -1, -1):
        for node in range(step + 1):
            node_spot = spot * (up ** (step - node)) * (down ** node)
            continuation = discount * (probability * values[node] + (1.0 - probability) * values[node + 1])
            intrinsic = node_spot - strike if is_call else strike - node_spot
            values[node] = max(continuation, intrinsic, 0.0)
    return values[0]
