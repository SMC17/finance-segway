"""Structured-credit collateral and sequential-pay waterfall engines."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .common import clamp, require_nonnegative


@dataclass(frozen=True)
class CollateralPeriod:
    period: int
    beginning_balance: float
    scheduled_principal: float
    prepayment: float
    defaults: float
    recoveries: float
    interest: float
    ending_balance: float


def collateral_cash_flows(*, opening_balance: float, periods: int,
                          annual_coupon: float, annual_cpr: float,
                          annual_cdr: float, recovery_rate: float,
                          frequency: int = 12) -> list[CollateralPeriod]:
    balance = require_nonnegative("opening_balance", opening_balance)
    if periods <= 0 or frequency <= 0:
        raise ValueError("periods and frequency must be positive")
    if not 0.0 <= recovery_rate <= 1.0:
        raise ValueError("recovery_rate must be between 0 and 1")
    smm = 1.0 - (1.0 - clamp(annual_cpr, 0.0, 1.0)) ** (1.0 / frequency)
    mdr = 1.0 - (1.0 - clamp(annual_cdr, 0.0, 1.0)) ** (1.0 / frequency)
    remaining_periods = periods
    output: list[CollateralPeriod] = []
    for period in range(1, periods + 1):
        beginning = balance
        scheduled = min(beginning, beginning / remaining_periods)
        after_scheduled = max(0.0, beginning - scheduled)
        defaults = after_scheduled * mdr
        after_defaults = max(0.0, after_scheduled - defaults)
        prepayment = after_defaults * smm
        recoveries = defaults * recovery_rate
        ending = max(0.0, after_defaults - prepayment)
        interest = beginning * annual_coupon / frequency
        output.append(CollateralPeriod(
            period, beginning, scheduled, prepayment, defaults,
            recoveries, interest, ending,
        ))
        balance = ending
        remaining_periods -= 1
    return output


@dataclass(frozen=True)
class Tranche:
    name: str
    balance: float
    coupon: float
    priority: int


@dataclass(frozen=True)
class TranchePayment:
    period: int
    tranche: str
    interest_due: float
    interest_paid: float
    principal_paid: float
    ending_balance: float
    interest_shortfall: float


def sequential_waterfall(collateral: Sequence[CollateralPeriod],
                         tranches: Sequence[Tranche], *,
                         frequency: int = 12) -> list[TranchePayment]:
    """Pay collateral collections through the tranche stack in priority order.

    Interest collections pay tranche interest; scheduled principal,
    prepayments, and default recoveries pay principal sequentially.
    Collections left after the stack is served (excess spread on the
    interest side, over-collateralization release on the principal side)
    are the period residual: collections minus the sum of that period's
    interest_paid and principal_paid across tranches.
    """
    balances = {tranche.name: require_nonnegative(f"balance:{tranche.name}", tranche.balance)
                for tranche in tranches}
    shortfalls = {tranche.name: 0.0 for tranche in tranches}
    ordered = sorted(tranches, key=lambda tranche: (tranche.priority, tranche.name))
    output: list[TranchePayment] = []
    for period in collateral:
        interest_cash = period.interest
        principal_cash = period.scheduled_principal + period.prepayment + period.recoveries
        for tranche in ordered:
            beginning = balances[tranche.name]
            due = beginning * tranche.coupon / frequency + shortfalls[tranche.name]
            interest_paid = min(interest_cash, due)
            interest_cash -= interest_paid
            shortfall = due - interest_paid
            principal_paid = min(principal_cash, beginning)
            principal_cash -= principal_paid
            ending = max(0.0, beginning - principal_paid)
            balances[tranche.name] = ending
            shortfalls[tranche.name] = shortfall
            output.append(TranchePayment(
                period.period, tranche.name, due, interest_paid,
                principal_paid, ending, shortfall,
            ))
    return output


def weighted_average_life(principal_cash_flows: Sequence[float],
                          frequency: int = 12) -> float:
    if frequency <= 0:
        raise ValueError("frequency must be positive")
    total = sum(float(cash) for cash in principal_cash_flows)
    if total <= 0:
        return 0.0
    return sum((period / frequency) * float(cash)
               for period, cash in enumerate(principal_cash_flows, start=1)) / total
