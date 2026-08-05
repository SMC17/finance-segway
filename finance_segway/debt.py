"""Debt schedules, covenant, recovery, and return reference engines."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .common import require_finite, require_nonnegative, require_positive


@dataclass(frozen=True)
class DebtTranche:
    name: str
    opening_balance: float
    cash_rate: float
    pik_rate: float = 0.0
    mandatory_amort_pct: float = 0.0
    cash_sweep_pct: float = 0.0
    maturity_period: int | None = None
    priority: int = 0

    def __post_init__(self) -> None:
        require_nonnegative("opening_balance", self.opening_balance)
        require_nonnegative("cash_rate", self.cash_rate)
        require_nonnegative("pik_rate", self.pik_rate)
        if not 0.0 <= self.mandatory_amort_pct <= 1.0:
            raise ValueError("mandatory_amort_pct must be between 0 and 1")
        if not 0.0 <= self.cash_sweep_pct <= 1.0:
            raise ValueError("cash_sweep_pct must be between 0 and 1")
        if self.maturity_period is not None and self.maturity_period <= 0:
            raise ValueError("maturity_period must be positive")


@dataclass(frozen=True)
class DebtPeriod:
    period: int
    tranche: str
    beginning_balance: float
    cash_interest: float
    pik_interest: float
    mandatory_amortization: float
    cash_sweep: float
    maturity_payment: float
    ending_balance: float


def build_debt_schedule(
    tranches: Sequence[DebtTranche],
    cash_available: Sequence[float],
    *,
    refinance_at_maturity: bool = True,
) -> list[DebtPeriod]:
    """Apply interest, amortization, PIK, priority sweeps, and maturity payments.

    Cash interest and mandatory amortization must be funded: the schedule
    raises ValueError when a period's cash cannot cover them, because the
    engine has no revolver or cash carryforward to bridge the gap - model it
    explicitly (PIK the coupon, cut the amortization, or treat it as a
    default).

    A tranche reaching maturity_period is retired in full. With the default
    refinance_at_maturity=True the repayment is treated as refinanced at par
    and consumes no operating cash - the standard assumption for a bullet
    maturing inside a projection window. With refinance_at_maturity=False
    the balloon must be paid from the period's remaining cash, and the
    schedule raises when it cannot be.
    """
    if not tranches:
        return []
    balances = {tranche.name: float(tranche.opening_balance) for tranche in tranches}
    ordered = sorted(tranches, key=lambda tranche: (tranche.priority, tranche.name))
    output: list[DebtPeriod] = []
    for period, available in enumerate(cash_available, start=1):
        remaining_cash = max(0.0, require_finite("cash_available", available))
        interim: dict[str, dict[str, float]] = {}
        for tranche in ordered:
            beginning = balances[tranche.name]
            cash_interest = beginning * tranche.cash_rate
            pik_interest = beginning * tranche.pik_rate
            amort = min(beginning + pik_interest, tranche.opening_balance * tranche.mandatory_amort_pct)
            post_amort = max(0.0, beginning + pik_interest - amort)
            interim[tranche.name] = {
                "beginning": beginning, "cash_interest": cash_interest,
                "pik_interest": pik_interest, "amort": amort, "post_amort": post_amort,
            }
            due = cash_interest + amort
            if remaining_cash + max(1e-9, 1e-12 * due) < due:
                raise ValueError(
                    f"period {period}: tranche {tranche.name!r} needs {due:.6f} for "
                    f"cash interest plus mandatory amortization but only "
                    f"{remaining_cash:.6f} cash remains; model the funding gap "
                    "explicitly (PIK, reduced amortization, or default)"
                )
            remaining_cash = max(0.0, remaining_cash - cash_interest - amort)
        for tranche in ordered:
            state = interim[tranche.name]
            sweep = min(state["post_amort"], remaining_cash * tranche.cash_sweep_pct)
            remaining_cash -= sweep
            post_sweep = max(0.0, state["post_amort"] - sweep)
            maturity = post_sweep if tranche.maturity_period == period else 0.0
            if maturity > 0.0 and not refinance_at_maturity:
                if maturity > remaining_cash + max(1e-9, 1e-12 * maturity):
                    raise ValueError(
                        f"period {period}: tranche {tranche.name!r} matures with "
                        f"balance {maturity:.6f} but only {remaining_cash:.6f} cash "
                        "remains and refinance_at_maturity is False; model "
                        "refinancing or extension explicitly"
                    )
                remaining_cash = max(0.0, remaining_cash - maturity)
            ending = max(0.0, post_sweep - maturity)
            balances[tranche.name] = ending
            output.append(DebtPeriod(
                period, tranche.name, state["beginning"], state["cash_interest"],
                state["pik_interest"], state["amort"], sweep, maturity, ending,
            ))
    return output


def covenant_headroom(actual: float, threshold: float, *, maximum: bool) -> float:
    actual = require_finite("actual", actual)
    threshold = require_finite("threshold", threshold)
    return threshold - actual if maximum else actual - threshold


def recovery_waterfall(enterprise_value: float, claims: Sequence[tuple[str, float]]) -> dict[str, float]:
    remaining = require_nonnegative("enterprise_value", enterprise_value)
    result: dict[str, float] = {}
    for name, claim in claims:
        claim = require_nonnegative(f"claim:{name}", claim)
        recovered = min(remaining, claim)
        result[name] = recovered
        remaining -= recovered
    result["residual_equity"] = remaining
    return result


def moic(distributions: Sequence[float], invested_equity: float) -> float:
    return sum(float(value) for value in distributions) / require_positive("invested_equity", invested_equity)


def irr(cash_flows: Sequence[float], *, low: float = -0.999999, high: float = 100.0) -> float:
    flows = [float(value) for value in cash_flows]
    if len(flows) < 2 or not any(value < 0 for value in flows) or not any(value > 0 for value in flows):
        raise ValueError("IRR requires at least one negative and one positive cash flow")
    def npv(rate: float) -> float:
        return sum(cash / ((1.0 + rate) ** period) for period, cash in enumerate(flows))
    left, right = low, high
    left_value, right_value = npv(left), npv(right)
    if left_value * right_value > 0:
        raise ValueError("cash flows do not bracket a root in the search interval")
    for _ in range(240):
        mid = (left + right) / 2.0
        mid_value = npv(mid)
        if abs(mid_value) < 1e-12:
            return mid
        if left_value * mid_value <= 0:
            right, right_value = mid, mid_value
        else:
            left, left_value = mid, mid_value
    return (left + right) / 2.0
