"""Independent reference oracles for the six legacy M2 finance engines.

The calculations in this module are intentionally separate from workbook
formulas. They provide deterministic identities and failure-state cases for
Investment Banking, Corporate Finance, Private Credit, Debt Finance, Public
Finance, and Venture Capital.
"""
from __future__ import annotations

from math import isfinite
from typing import Any, Callable

TOLERANCE = 1e-9


def _nonnegative(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return value


def _bounded(name: str, value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    value = float(value)
    if not isfinite(value) or value < lower or value > upper:
        raise ValueError(f"{name} must be between {lower} and {upper}")
    return value


def investment_banking(case: dict[str, Any]) -> dict[str, Any]:
    enterprise_value = _nonnegative("enterprise_value", case["enterprise_value"])
    debt = _nonnegative("debt", case["debt"])
    cash = _nonnegative("cash", case["cash"])
    shares = _nonnegative("shares", case["shares"])
    if shares <= 0:
        raise ValueError("shares must be positive")
    discount_rate = float(case["discount_rate"])
    terminal_growth = float(case["terminal_growth"])
    if discount_rate <= terminal_growth:
        terminal_value = float("inf")
        dcf_equity_value = float("inf")
        dcf_per_share = float("inf")
    else:
        fcfs = [float(value) for value in case["forecast_fcfs"]]
        pv_fcfs = sum(
            value / ((1.0 + discount_rate) ** year)
            for year, value in enumerate(fcfs, start=1)
        )
        terminal_value = fcfs[-1] * (1.0 + terminal_growth) / (
            discount_rate - terminal_growth
        )
        pv_terminal = terminal_value / ((1.0 + discount_rate) ** len(fcfs))
        dcf_enterprise_value = pv_fcfs + pv_terminal
        dcf_equity_value = dcf_enterprise_value - debt + cash
        dcf_per_share = dcf_equity_value / shares
    equity_value = enterprise_value - debt + cash
    per_share = equity_value / shares
    offer_price = _nonnegative("offer_price", case.get("offer_price", per_share))
    synergies = float(case.get("after_tax_synergies", 0.0))
    financing_cost = float(case.get("incremental_financing_cost", 0.0))
    target_earnings = float(case.get("target_earnings", 0.0))
    shares_issued = _nonnegative("shares_issued", case.get("shares_issued", 0.0))
    buyer_earnings = float(case.get("buyer_earnings", 0.0))
    buyer_shares = _nonnegative("buyer_shares", case.get("buyer_shares", 1.0))
    if buyer_shares <= 0:
        raise ValueError("buyer_shares must be positive")
    standalone_eps = buyer_earnings / buyer_shares
    pro_forma_eps = (
        buyer_earnings + target_earnings + synergies - financing_cost
    ) / (buyer_shares + shares_issued)
    accretion = (
        pro_forma_eps / standalone_eps - 1.0 if abs(standalone_eps) > TOLERANCE else 0.0
    )
    identities = {
        "enterprise_to_equity_bridge": abs(
            enterprise_value - debt + cash - equity_value
        ) <= TOLERANCE,
        "per_share_identity": abs(equity_value - per_share * shares) <= TOLERANCE,
        "deal_eps_identity": abs(
            pro_forma_eps * (buyer_shares + shares_issued)
            - (buyer_earnings + target_earnings + synergies - financing_cost)
        ) <= TOLERANCE,
    }
    flags: list[str] = []
    if discount_rate <= terminal_growth:
        flags.append("invalid_terminal_value")
    if offer_price > per_share * (1.0 + float(case.get("premium_warning", 0.30))):
        flags.append("offer_premium")
    if accretion < float(case.get("minimum_accretion", 0.0)):
        flags.append("eps_dilution")
    if isfinite(dcf_per_share) and abs(dcf_per_share - per_share) / max(abs(per_share), 1.0) > float(
        case.get("valuation_dispersion_warning", 0.50)
    ):
        flags.append("valuation_dispersion")
    return {
        "metrics": {
            "equity_value": equity_value,
            "per_share_value": per_share,
            "dcf_equity_value": dcf_equity_value,
            "dcf_per_share": dcf_per_share,
            "offer_price": offer_price,
            "pro_forma_eps": pro_forma_eps,
            "eps_accretion": accretion,
        },
        "identity_checks": identities,
        "active_risk_flags": flags,
    }


def corporate_finance(case: dict[str, Any]) -> dict[str, Any]:
    opening_cash = _nonnegative("opening_cash", case["opening_cash"])
    operating_cash_flow = float(case["operating_cash_flow"])
    capex = _nonnegative("capex", case["capex"])
    dividends = _nonnegative("dividends", case.get("dividends", 0.0))
    buybacks = _nonnegative("buybacks", case.get("buybacks", 0.0))
    debt_issuance = _nonnegative("debt_issuance", case.get("debt_issuance", 0.0))
    debt_repayment = _nonnegative("debt_repayment", case.get("debt_repayment", 0.0))
    opening_debt = _nonnegative("opening_debt", case["opening_debt"])
    ending_cash = (
        opening_cash
        + operating_cash_flow
        - capex
        - dividends
        - buybacks
        + debt_issuance
        - debt_repayment
    )
    ending_debt = opening_debt + debt_issuance - debt_repayment
    ebitda = float(case["ebitda"])
    interest = _nonnegative("interest", case["interest"])
    minimum_cash = _nonnegative("minimum_cash", case["minimum_cash"])
    net_debt = ending_debt - ending_cash
    net_leverage = net_debt / ebitda if ebitda > 0 else float("inf")
    interest_coverage = ebitda / interest if interest > 0 else float("inf")
    financing_gap = max(0.0, minimum_cash - ending_cash)
    identities = {
        "cash_rollforward": abs(
            ending_cash
            - (
                opening_cash
                + operating_cash_flow
                - capex
                - dividends
                - buybacks
                + debt_issuance
                - debt_repayment
            )
        ) <= TOLERANCE,
        "debt_rollforward": abs(
            ending_debt - (opening_debt + debt_issuance - debt_repayment)
        ) <= TOLERANCE,
        "net_debt_identity": abs(net_debt - ending_debt + ending_cash) <= TOLERANCE,
    }
    flags: list[str] = []
    if financing_gap > TOLERANCE:
        flags.append("minimum_cash_shortfall")
    if net_leverage > float(case.get("maximum_net_leverage", 3.5)):
        flags.append("leverage_breach")
    if interest_coverage < float(case.get("minimum_interest_coverage", 2.0)):
        flags.append("interest_coverage_breach")
    if dividends + buybacks > max(0.0, operating_cash_flow - capex):
        flags.append("unfunded_shareholder_distribution")
    return {
        "metrics": {
            "ending_cash": ending_cash,
            "ending_debt": ending_debt,
            "net_debt": net_debt,
            "net_leverage": net_leverage,
            "interest_coverage": interest_coverage,
            "financing_gap": financing_gap,
        },
        "identity_checks": identities,
        "active_risk_flags": flags,
    }


def private_credit(case: dict[str, Any]) -> dict[str, Any]:
    opening_debt = _nonnegative("opening_debt", case["opening_debt"])
    mandatory_amortization = _nonnegative(
        "mandatory_amortization", case.get("mandatory_amortization", 0.0)
    )
    cash_sweep = _nonnegative("cash_sweep", case.get("cash_sweep", 0.0))
    pik_interest = _nonnegative("pik_interest", case.get("pik_interest", 0.0))
    ending_debt = max(
        0.0, opening_debt - mandatory_amortization - cash_sweep + pik_interest
    )
    cfads = float(case["cfads"])
    cash_interest = _nonnegative("cash_interest", case["cash_interest"])
    debt_service = cash_interest + mandatory_amortization
    dscr = cfads / debt_service if debt_service > 0 else float("inf")
    ebitda = float(case["ebitda"])
    leverage = ending_debt / ebitda if ebitda > 0 else float("inf")
    recovery_ev = _nonnegative("recovery_ev", case["recovery_ev"])
    senior_claims = _nonnegative("senior_claims", case.get("senior_claims", 0.0))
    lender_claim = _nonnegative("lender_claim", case.get("lender_claim", ending_debt))
    value_available = max(0.0, recovery_ev - senior_claims)
    recovery_value = min(lender_claim, value_available)
    recovery_rate = recovery_value / lender_claim if lender_claim > 0 else 1.0
    lgd = 1.0 - recovery_rate
    identities = {
        "debt_rollforward": abs(
            ending_debt
            - max(
                0.0,
                opening_debt
                - mandatory_amortization
                - cash_sweep
                + pik_interest,
            )
        ) <= TOLERANCE,
        "recovery_lgd_identity": abs(recovery_rate + lgd - 1.0) <= TOLERANCE,
        "recovery_claim_bound": recovery_value <= lender_claim + TOLERANCE,
    }
    flags: list[str] = []
    if dscr < float(case.get("minimum_dscr", 1.0)):
        flags.append("dscr_breach")
    if leverage > float(case.get("maximum_leverage", 6.0)):
        flags.append("leverage_breach")
    if recovery_rate < float(case.get("minimum_recovery", 0.60)):
        flags.append("recovery_impairment")
    if pik_interest > cash_sweep + mandatory_amortization:
        flags.append("debt_compounding")
    return {
        "metrics": {
            "ending_debt": ending_debt,
            "debt_service": debt_service,
            "dscr": dscr,
            "leverage": leverage,
            "recovery_value": recovery_value,
            "recovery_rate": recovery_rate,
            "lgd": lgd,
        },
        "identity_checks": identities,
        "active_risk_flags": flags,
    }


def debt_finance(case: dict[str, Any]) -> dict[str, Any]:
    opening_debt = _nonnegative("opening_debt", case["opening_debt"])
    issuance = _nonnegative("issuance", case.get("issuance", 0.0))
    repayments = _nonnegative("repayments", case.get("repayments", 0.0))
    maturities = [
        _nonnegative(f"maturity_{index}", value)
        for index, value in enumerate(case["maturities"], start=1)
    ]
    ending_debt = max(0.0, opening_debt + issuance - repayments)
    liquidity = _nonnegative("liquidity", case["liquidity"])
    committed_lines = _nonnegative("committed_lines", case.get("committed_lines", 0.0))
    near_term_maturities = sum(maturities[: int(case.get("near_term_years", 2))])
    refinancing_gap = max(0.0, near_term_maturities - liquidity - committed_lines)
    concentration = max(maturities) / sum(maturities) if sum(maturities) > 0 else 0.0
    tranches = case.get("tranches", [])
    total_tranche_debt = sum(_nonnegative("tranche_amount", item["amount"]) for item in tranches)
    weighted_cost = (
        sum(float(item["amount"]) * float(item["rate"]) for item in tranches)
        / total_tranche_debt
        if total_tranche_debt > 0
        else 0.0
    )
    ebitda = float(case["ebitda"])
    cash_interest = ending_debt * weighted_cost
    interest_coverage = ebitda / cash_interest if cash_interest > 0 else float("inf")
    identities = {
        "debt_rollforward": abs(
            ending_debt - max(0.0, opening_debt + issuance - repayments)
        ) <= TOLERANCE,
        "weighted_cost_identity": (
            abs(
                weighted_cost * total_tranche_debt
                - sum(float(item["amount"]) * float(item["rate"]) for item in tranches)
            ) <= TOLERANCE
        ),
        "refinancing_gap_identity": abs(
            refinancing_gap
            - max(0.0, near_term_maturities - liquidity - committed_lines)
        ) <= TOLERANCE,
    }
    flags: list[str] = []
    if refinancing_gap > TOLERANCE:
        flags.append("refinancing_gap")
    if concentration > float(case.get("maximum_maturity_concentration", 0.40)):
        flags.append("maturity_concentration")
    if interest_coverage < float(case.get("minimum_interest_coverage", 2.0)):
        flags.append("interest_coverage_breach")
    if issuance > repayments and weighted_cost > float(case.get("maximum_weighted_cost", 0.10)):
        flags.append("expensive_refinancing")
    return {
        "metrics": {
            "ending_debt": ending_debt,
            "near_term_maturities": near_term_maturities,
            "refinancing_gap": refinancing_gap,
            "maturity_concentration": concentration,
            "weighted_cost": weighted_cost,
            "cash_interest": cash_interest,
            "interest_coverage": interest_coverage,
        },
        "identity_checks": identities,
        "active_risk_flags": flags,
    }


def public_finance(case: dict[str, Any]) -> dict[str, Any]:
    opening_debt_ratio = _nonnegative("opening_debt_ratio", case["opening_debt_ratio"])
    nominal_interest_rate = float(case["nominal_interest_rate"])
    nominal_growth_rate = float(case["nominal_growth_rate"])
    primary_balance = float(case["primary_balance_ratio"])
    projected_debt_ratio = (
        (1.0 + nominal_interest_rate) / (1.0 + nominal_growth_rate)
    ) * opening_debt_ratio - primary_balance
    stabilizing_primary_balance = (
        (nominal_interest_rate - nominal_growth_rate)
        / (1.0 + nominal_growth_rate)
    ) * opening_debt_ratio
    pledged_revenue = _nonnegative("pledged_revenue", case["pledged_revenue"])
    debt_service = _nonnegative("debt_service", case["debt_service"])
    reserves = _nonnegative("reserves", case["reserves"])
    operating_expenditure = _nonnegative(
        "operating_expenditure", case["operating_expenditure"]
    )
    dscr = pledged_revenue / debt_service if debt_service > 0 else float("inf")
    reserve_coverage = reserves / operating_expenditure if operating_expenditure > 0 else float("inf")
    identities = {
        "debt_ratio_identity": abs(
            projected_debt_ratio
            - (
                (1.0 + nominal_interest_rate)
                / (1.0 + nominal_growth_rate)
                * opening_debt_ratio
                - primary_balance
            )
        ) <= TOLERANCE,
        "stabilizing_primary_balance_identity": abs(
            stabilizing_primary_balance
            - (
                (nominal_interest_rate - nominal_growth_rate)
                / (1.0 + nominal_growth_rate)
                * opening_debt_ratio
            )
        ) <= TOLERANCE,
        "coverage_nonnegative": dscr >= 0 and reserve_coverage >= 0,
    }
    flags: list[str] = []
    if projected_debt_ratio > float(case.get("maximum_debt_ratio", 1.0)):
        flags.append("debt_sustainability_breach")
    if primary_balance + TOLERANCE < stabilizing_primary_balance:
        flags.append("destabilizing_primary_balance")
    if dscr < float(case.get("minimum_dscr", 1.20)):
        flags.append("debt_service_coverage_breach")
    if reserve_coverage < float(case.get("minimum_reserve_coverage", 0.10)):
        flags.append("reserve_shortfall")
    return {
        "metrics": {
            "projected_debt_ratio": projected_debt_ratio,
            "stabilizing_primary_balance": stabilizing_primary_balance,
            "primary_balance_gap": primary_balance - stabilizing_primary_balance,
            "dscr": dscr,
            "reserve_coverage": reserve_coverage,
        },
        "identity_checks": identities,
        "active_risk_flags": flags,
    }


def venture_capital(case: dict[str, Any]) -> dict[str, Any]:
    pre_money = _nonnegative("pre_money", case["pre_money"])
    investment = _nonnegative("investment", case["investment"])
    post_money = pre_money + investment
    existing_shares = _nonnegative("existing_shares", case["existing_shares"])
    new_shares = _nonnegative("new_shares", case["new_shares"])
    pool_expansion = _nonnegative("pool_expansion", case.get("pool_expansion", 0.0))
    total_post_shares = existing_shares + new_shares + pool_expansion
    if total_post_shares <= 0:
        raise ValueError("total post-money shares must be positive")
    investor_ownership = new_shares / total_post_shares
    founder_ownership = existing_shares / total_post_shares
    pool_ownership = pool_expansion / total_post_shares
    exit_value = _nonnegative("exit_value", case["exit_value"])
    investor_exit_proceeds = exit_value * investor_ownership
    gross_moic = investor_exit_proceeds / investment if investment > 0 else float("inf")
    follow_on_required = _nonnegative(
        "follow_on_required", case.get("follow_on_required", 0.0)
    )
    reserves = _nonnegative("reserves", case.get("reserves", 0.0))
    reserve_gap = max(0.0, follow_on_required - reserves)
    implied_price_per_share = investment / new_shares if new_shares > 0 else 0.0
    implied_pre_money_per_share = pre_money / existing_shares if existing_shares > 0 else 0.0
    identities = {
        "post_money_identity": abs(post_money - pre_money - investment) <= TOLERANCE,
        "ownership_conservation": abs(
            investor_ownership + founder_ownership + pool_ownership - 1.0
        ) <= TOLERANCE,
        "exit_proceeds_identity": abs(
            investor_exit_proceeds - exit_value * investor_ownership
        ) <= TOLERANCE,
    }
    flags: list[str] = []
    if reserve_gap > TOLERANCE:
        flags.append("follow_on_reserve_shortfall")
    if investor_ownership > float(case.get("maximum_investor_ownership", 0.40)):
        flags.append("ownership_concentration")
    if pool_ownership > float(case.get("maximum_pool_dilution", 0.20)):
        flags.append("option_pool_dilution")
    if implied_price_per_share + TOLERANCE < implied_pre_money_per_share:
        flags.append("down_round")
    if gross_moic < float(case.get("minimum_gross_moic", 3.0)):
        flags.append("return_shortfall")
    return {
        "metrics": {
            "post_money": post_money,
            "investor_ownership": investor_ownership,
            "founder_ownership": founder_ownership,
            "pool_ownership": pool_ownership,
            "investor_exit_proceeds": investor_exit_proceeds,
            "gross_moic": gross_moic,
            "reserve_gap": reserve_gap,
            "implied_price_per_share": implied_price_per_share,
        },
        "identity_checks": identities,
        "active_risk_flags": flags,
    }


ORACLES: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "01": investment_banking,
    "02": corporate_finance,
    "05": private_credit,
    "06": debt_finance,
    "07": public_finance,
    "13": venture_capital,
}


def validate_case(model_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
    if model_id not in ORACLES:
        raise KeyError(f"unknown legacy model {model_id}")
    result = ORACLES[model_id](inputs)
    result["identity_status"] = (
        "PASS" if all(result["identity_checks"].values()) else "FAIL"
    )
    return result
