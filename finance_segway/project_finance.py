"""Project-finance construction, sculpting, and coverage engines."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .common import EPS, require_finite, require_nonnegative, require_positive


@dataclass(frozen=True)
class ConstructionPeriod:
    period: int
    opening_debt: float
    equity_draw: float
    debt_draw: float
    interest_during_construction: float
    closing_debt: float


def construction_draw_schedule(capex: Sequence[float], *, debt_share: float,
                               debt_rate_per_period: float) -> list[ConstructionPeriod]:
    if not 0.0 <= debt_share <= 1.0:
        raise ValueError("debt_share must be between 0 and 1")
    rate = require_nonnegative("debt_rate_per_period", debt_rate_per_period)
    debt = 0.0
    output: list[ConstructionPeriod] = []
    for period, spend in enumerate(capex, start=1):
        spend = require_nonnegative("capex", spend)
        debt_draw = spend * debt_share
        equity_draw = spend - debt_draw
        idc = (debt + 0.5 * debt_draw) * rate
        closing = debt + debt_draw + idc
        output.append(ConstructionPeriod(period, debt, equity_draw, debt_draw, idc, closing))
        debt = closing
    return output


def sculpt_debt_service(cfads: Sequence[float], target_dscr: float,
                       opening_debt: float, rate_per_period: float) -> list[dict[str, float]]:
    target_dscr = require_positive("target_dscr", target_dscr)
    balance = require_nonnegative("opening_debt", opening_debt)
    rate = require_nonnegative("rate_per_period", rate_per_period)
    output: list[dict[str, float]] = []
    for period, cash in enumerate(cfads, start=1):
        cash = require_nonnegative("cfads", cash)
        interest = balance * rate
        target_service = cash / target_dscr
        principal = min(balance, max(0.0, target_service - interest))
        service = interest + principal
        ending = max(0.0, balance - principal)
        output.append({
            "period": float(period), "beginning_debt": balance,
            "interest": interest, "principal": principal,
            "debt_service": service, "ending_debt": ending,
            "dscr": cash / service if service > EPS else float("inf"),
        })
        balance = ending
    return output


def dscr(cfads: float, debt_service: float) -> float:
    return require_finite("cfads", cfads) / require_positive("debt_service", debt_service)


def llcr(cfads: Sequence[float], discount_rate: float, debt_balance: float) -> float:
    debt_balance = require_positive("debt_balance", debt_balance)
    discount_rate = require_finite("discount_rate", discount_rate)
    present_value = sum(float(cash) / ((1.0 + discount_rate) ** period)
                        for period, cash in enumerate(cfads, start=1))
    return present_value / debt_balance


def plcr(cfads: Sequence[float], discount_rate: float, debt_balance: float) -> float:
    return llcr(cfads, discount_rate, debt_balance)
