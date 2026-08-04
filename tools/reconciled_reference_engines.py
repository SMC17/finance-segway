"""Independent reference calculations for the reconciled credit and public-finance models."""
from __future__ import annotations


def approximate_cash_ytm(coupon_rate: float, issue_price: float, maturity_years: float) -> float:
    """Standard bond-yield approximation using a 100 par amount."""
    if maturity_years <= 0 or issue_price <= 0:
        raise ValueError("maturity and issue price must be positive")
    return (coupon_rate * 100.0 + (100.0 - issue_price) / maturity_years) / ((100.0 + issue_price) / 2.0)


def approximate_all_in_yield(coupon_rate: float, issue_price: float, maturity_years: float, pik_rate: float = 0.0) -> float:
    return approximate_cash_ytm(coupon_rate, issue_price, maturity_years) + pik_rate


def recovery_rate(stressed_ebitda: float, recovery_multiple: float, ev_haircut: float, debt_claim: float) -> float:
    if debt_claim <= 0:
        raise ValueError("debt claim must be positive")
    distributable = max(0.0, stressed_ebitda * recovery_multiple * (1.0 - ev_haircut))
    return min(1.0, distributable / debt_claim)


def loss_given_default(*args: float) -> float:
    return 1.0 - recovery_rate(*args)


def debt_stabilizing_primary_balance(debt_ratio: float, effective_rate: float, nominal_growth: float) -> float:
    if nominal_growth <= -1.0:
        raise ValueError("nominal growth must exceed -100%")
    return (effective_rate - nominal_growth) / (1.0 + nominal_growth) * debt_ratio


def projected_debt_ratio(debt_ratio: float, effective_rate: float, nominal_growth: float, primary_balance: float) -> float:
    if nominal_growth <= -1.0:
        raise ValueError("nominal growth must exceed -100%")
    return (1.0 + effective_rate) / (1.0 + nominal_growth) * debt_ratio - primary_balance


def refinancing_sources_uses_residual(uses: list[float], sources: list[float]) -> float:
    return sum(sources) - sum(uses)


def maturity_concentration(maturities: list[float], gross_debt: float, years: int = 3) -> float:
    if gross_debt <= 0:
        raise ValueError("gross debt must be positive")
    return sum(maturities[:years]) / gross_debt
