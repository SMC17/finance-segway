"""Pure-Python reference engines for independent spreadsheet verification.

These functions are intentionally small and dependency-free. They are not a
production pricing library; they are independent oracles used to test workbook
identities, monotonicity, conservation, and closed-form results.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import erf, exp, log, pi, sqrt
from typing import Iterable, Sequence


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def norm_pdf(x: float) -> float:
    return exp(-0.5 * x * x) / sqrt(2.0 * pi)


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


def black_scholes(
    spot: float,
    strike: float,
    years: float,
    rate: float,
    dividend_yield: float,
    volatility: float,
) -> BlackScholesResult:
    if min(spot, strike, years, volatility) <= 0:
        raise ValueError("spot, strike, years, and volatility must be positive")

    root_t = sqrt(years)
    discount_r = exp(-rate * years)
    discount_q = exp(-dividend_yield * years)
    d1 = (
        log(spot / strike)
        + (rate - dividend_yield + 0.5 * volatility * volatility) * years
    ) / (volatility * root_t)
    d2 = d1 - volatility * root_t

    call = spot * discount_q * norm_cdf(d1) - strike * discount_r * norm_cdf(d2)
    put = strike * discount_r * norm_cdf(-d2) - spot * discount_q * norm_cdf(-d1)
    gamma = discount_q * norm_pdf(d1) / (spot * volatility * root_t)
    vega = spot * discount_q * norm_pdf(d1) * root_t
    common_theta = -(spot * discount_q * norm_pdf(d1) * volatility) / (2.0 * root_t)
    call_theta = (
        common_theta
        - rate * strike * discount_r * norm_cdf(d2)
        + dividend_yield * spot * discount_q * norm_cdf(d1)
    )
    put_theta = (
        common_theta
        + rate * strike * discount_r * norm_cdf(-d2)
        - dividend_yield * spot * discount_q * norm_cdf(-d1)
    )

    return BlackScholesResult(
        call=call,
        put=put,
        call_delta=discount_q * norm_cdf(d1),
        put_delta=discount_q * (norm_cdf(d1) - 1.0),
        gamma=gamma,
        vega=vega,
        call_theta=call_theta,
        put_theta=put_theta,
        call_rho=strike * years * discount_r * norm_cdf(d2),
        put_rho=-strike * years * discount_r * norm_cdf(-d2),
    )


def put_call_parity_residual(
    spot: float,
    strike: float,
    years: float,
    rate: float,
    dividend_yield: float,
    call: float,
    put: float,
) -> float:
    return (call - put) - (
        spot * exp(-dividend_yield * years) - strike * exp(-rate * years)
    )


def bond_cashflows(
    face: float,
    coupon_rate: float,
    years: float,
    frequency: int,
) -> list[tuple[float, float]]:
    if face <= 0 or years <= 0 or frequency <= 0:
        raise ValueError("face, years, and frequency must be positive")
    periods = int(round(years * frequency))
    coupon = face * coupon_rate / frequency
    flows: list[tuple[float, float]] = []
    for period in range(1, periods + 1):
        amount = coupon + (face if period == periods else 0.0)
        flows.append((period / frequency, amount))
    return flows


def bond_price(
    face: float,
    coupon_rate: float,
    years: float,
    ytm: float,
    frequency: int = 2,
) -> float:
    periodic_yield = ytm / frequency
    if periodic_yield <= -1:
        raise ValueError("periodic yield must be greater than -100%")
    return sum(
        amount / ((1.0 + periodic_yield) ** int(round(time * frequency)))
        for time, amount in bond_cashflows(face, coupon_rate, years, frequency)
    )


def macaulay_duration(
    face: float,
    coupon_rate: float,
    years: float,
    ytm: float,
    frequency: int = 2,
) -> float:
    price = bond_price(face, coupon_rate, years, ytm, frequency)
    periodic_yield = ytm / frequency
    weighted = 0.0
    for time, amount in bond_cashflows(face, coupon_rate, years, frequency):
        period = int(round(time * frequency))
        pv = amount / ((1.0 + periodic_yield) ** period)
        weighted += time * pv
    return weighted / price


def modified_duration(
    face: float,
    coupon_rate: float,
    years: float,
    ytm: float,
    frequency: int = 2,
) -> float:
    return macaulay_duration(face, coupon_rate, years, ytm, frequency) / (
        1.0 + ytm / frequency
    )


def numerical_duration(
    face: float,
    coupon_rate: float,
    years: float,
    ytm: float,
    frequency: int = 2,
    shock: float = 1e-4,
) -> float:
    price = bond_price(face, coupon_rate, years, ytm, frequency)
    down = bond_price(face, coupon_rate, years, ytm - shock, frequency)
    up = bond_price(face, coupon_rate, years, ytm + shock, frequency)
    return (down - up) / (2.0 * price * shock)


def numerical_convexity(
    face: float,
    coupon_rate: float,
    years: float,
    ytm: float,
    frequency: int = 2,
    shock: float = 1e-4,
) -> float:
    price = bond_price(face, coupon_rate, years, ytm, frequency)
    down = bond_price(face, coupon_rate, years, ytm - shock, frequency)
    up = bond_price(face, coupon_rate, years, ytm + shock, frequency)
    return (down + up - 2.0 * price) / (price * shock * shock)


@dataclass(frozen=True)
class DebtSweepPeriod:
    opening_debt: float
    cash_interest: float
    mandatory_amortization: float
    cash_sweep: float
    closing_debt: float
    excess_cash_after_sweep: float


def debt_sweep(
    opening_debt: float,
    cash_available: Sequence[float],
    annual_rate: float,
    mandatory_amortization_rate: float = 0.0,
    sweep_percent: float = 1.0,
) -> list[DebtSweepPeriod]:
    if opening_debt < 0:
        raise ValueError("opening debt cannot be negative")
    if not 0 <= mandatory_amortization_rate <= 1:
        raise ValueError("mandatory amortization rate must be between 0 and 1")
    if not 0 <= sweep_percent <= 1:
        raise ValueError("sweep percent must be between 0 and 1")

    periods: list[DebtSweepPeriod] = []
    debt = opening_debt
    for available in cash_available:
        if available < 0:
            raise ValueError("cash available cannot be negative")
        interest = debt * annual_rate
        post_interest_cash = max(0.0, available - interest)
        mandatory = min(debt, debt * mandatory_amortization_rate)
        post_mandatory_debt = debt - mandatory
        post_mandatory_cash = max(0.0, post_interest_cash - mandatory)
        sweep = min(post_mandatory_debt, post_mandatory_cash * sweep_percent)
        closing = post_mandatory_debt - sweep
        excess = post_mandatory_cash - sweep
        periods.append(
            DebtSweepPeriod(
                opening_debt=debt,
                cash_interest=interest,
                mandatory_amortization=mandatory,
                cash_sweep=sweep,
                closing_debt=closing,
                excess_cash_after_sweep=excess,
            )
        )
        debt = closing
    return periods


def moic(equity_proceeds: float, invested_equity: float) -> float:
    if invested_equity <= 0:
        raise ValueError("invested equity must be positive")
    return equity_proceeds / invested_equity


def annualized_irr_single_exit(
    equity_proceeds: float,
    invested_equity: float,
    years: float,
) -> float:
    if years <= 0:
        raise ValueError("years must be positive")
    return moic(equity_proceeds, invested_equity) ** (1.0 / years) - 1.0


def dscr(cfads: float, debt_service: float) -> float:
    if debt_service <= 0:
        raise ValueError("debt service must be positive")
    return cfads / debt_service


def llcr(
    projected_cfads: Iterable[float],
    discount_rate: float,
    debt_balance: float,
) -> float:
    if debt_balance <= 0:
        raise ValueError("debt balance must be positive")
    if discount_rate <= -1:
        raise ValueError("discount rate must be greater than -100%")
    pv = sum(
        cashflow / ((1.0 + discount_rate) ** period)
        for period, cashflow in enumerate(projected_cfads, start=1)
    )
    return pv / debt_balance


def sequential_pay_waterfall(
    available_principal: float,
    tranche_balances: Sequence[float],
) -> tuple[list[float], float]:
    if available_principal < 0 or any(balance < 0 for balance in tranche_balances):
        raise ValueError("principal and balances cannot be negative")
    remaining = available_principal
    payments: list[float] = []
    for balance in tranche_balances:
        payment = min(balance, remaining)
        payments.append(payment)
        remaining -= payment
    return payments, remaining
