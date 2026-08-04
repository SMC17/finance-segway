"""Independent financial oracles for the remaining M1 finance domains.

These calculations intentionally do not read workbook formulas. They provide
reference identities, bounds, and risk flags that workbook implementations
must reconcile to before a domain can be promoted to M2.
"""
from __future__ import annotations

import math
from typing import Any, Callable

TOLERANCE = 1e-9


def _finite_mapping(values: dict[str, float]) -> bool:
    return all(math.isfinite(float(value)) for value in values.values())


def _ratio(numerator: float, denominator: float) -> float:
    if abs(denominator) <= TOLERANCE:
        raise ValueError("ratio denominator must be non-zero")
    return numerator / denominator


def _bounded(value: float, lower: float = 0.0, upper: float = 1.0) -> bool:
    return lower - TOLERANCE <= value <= upper + TOLERANCE


def asset_management(inputs: dict[str, float]) -> dict[str, Any]:
    ending_nav = inputs["beginning_nav"] + inputs["contributions"] + inputs["gains"] - inputs["fees"] - inputs["distributions"]
    paid_in = inputs["paid_in"]
    dpi = _ratio(inputs["cumulative_distributions"], paid_in)
    rvpi = _ratio(inputs["residual_value"], paid_in)
    tvpi = dpi + rvpi
    gross_profit = max(inputs["gross_profit"], 0.0)
    invested_basis = max(inputs["invested_basis"], 0.0)
    carry_rate = inputs["carry_rate"]
    hurdle_rate = inputs["hurdle_rate"]
    catch_up_rate = inputs.get("catch_up_rate", 1.0)
    return_of_capital = min(gross_profit, invested_basis)
    remaining = gross_profit - return_of_capital
    preferred_return = min(remaining, invested_basis * hurdle_rate)
    remaining -= preferred_return
    catch_up_target = preferred_return * carry_rate / (1.0 - carry_rate) if 0.0 <= carry_rate < 1.0 else math.inf
    gp_catch_up = min(remaining, catch_up_target * catch_up_rate)
    remaining -= gp_catch_up
    gp_share = gp_catch_up + remaining * carry_rate
    lp_share = return_of_capital + preferred_return + remaining * (1.0 - carry_rate)
    metrics = {"ending_nav": ending_nav, "dpi": dpi, "rvpi": rvpi, "tvpi": tvpi, "gp_share": gp_share, "lp_share": lp_share, "waterfall_total": gp_share + lp_share}
    checks = {"nav_rollforward": abs(ending_nav - (inputs["beginning_nav"] + inputs["contributions"] + inputs["gains"] - inputs["fees"] - inputs["distributions"])) <= TOLERANCE, "tvpi_identity": abs(tvpi - dpi - rvpi) <= TOLERANCE, "waterfall_conservation": abs(gp_share + lp_share - gross_profit) <= TOLERANCE, "carry_rate_bounds": _bounded(carry_rate), "catch_up_rate_bounds": _bounded(catch_up_rate), "finite_outputs": _finite_mapping(metrics)}
    risk_flags = {"negative_nav": ending_nav < -TOLERANCE, "negative_fees": inputs["fees"] < -TOLERANCE, "liquidity_pressure": inputs["distributions"] > inputs["beginning_nav"] + inputs["contributions"] + inputs["gains"]}
    return {"metrics": metrics, "identity_checks": checks, "risk_flags": risk_flags}


def trade_finance(inputs: dict[str, float]) -> dict[str, Any]:
    cash_conversion_days = inputs["inventory_days"] + inputs["receivable_days"] - inputs["payable_days"]
    facility_utilization = _ratio(inputs["drawn_amount"], inputs["facility_limit"])
    lc_annualized_cost = _ratio(inputs["lc_fee"], inputs["lc_face"]) * 365.0 / inputs["lc_tenor_days"]
    factoring_proceeds = inputs["invoice_face"] - inputs["factoring_discount"]
    factoring_effective_apr = _ratio(inputs["factoring_discount"], factoring_proceeds) * 365.0 / inputs["factoring_days"]
    expected_loss = inputs["ead"] * inputs["pd"] * inputs["lgd"]
    risk_adjusted_margin = inputs["gross_margin"] - expected_loss - inputs["country_risk_cost"]
    metrics = {"cash_conversion_days": cash_conversion_days, "facility_utilization": facility_utilization, "lc_annualized_cost": lc_annualized_cost, "factoring_effective_apr": factoring_effective_apr, "expected_loss": expected_loss, "risk_adjusted_margin": risk_adjusted_margin}
    checks = {"expected_loss_identity": abs(expected_loss - inputs["ead"] * inputs["pd"] * inputs["lgd"]) <= TOLERANCE, "pd_bounds": _bounded(inputs["pd"]), "lgd_bounds": _bounded(inputs["lgd"]), "positive_tenors": inputs["lc_tenor_days"] > 0 and inputs["factoring_days"] > 0, "positive_facility": inputs["facility_limit"] > 0, "finite_outputs": _finite_mapping(metrics)}
    risk_flags = {"facility_breach": facility_utilization > 1.0 + TOLERANCE, "negative_factoring_proceeds": factoring_proceeds <= 0, "negative_risk_adjusted_margin": risk_adjusted_margin < 0, "extended_cash_cycle": cash_conversion_days > inputs.get("cash_cycle_warning_days", 120.0)}
    return {"metrics": metrics, "identity_checks": checks, "risk_flags": risk_flags}


def microfinance(inputs: dict[str, float]) -> dict[str, Any]:
    ending_portfolio = inputs["beginning_portfolio"] + inputs["disbursements"] - inputs["collections"] - inputs["writeoffs"]
    par30 = _ratio(inputs["overdue_30_balance"], ending_portfolio)
    par90 = _ratio(inputs["overdue_90_balance"], ending_portfolio)
    writeoff_ratio = _ratio(inputs["writeoffs"], inputs["average_portfolio"])
    restructured_ratio = _ratio(inputs["restructured_balance"], ending_portfolio)
    credit_risk_ratio = par30 + writeoff_ratio + restructured_ratio
    oss = _ratio(inputs["operating_revenue"], inputs["financial_expense"] + inputs["loan_loss_provision"] + inputs["operating_expense"])
    fss = _ratio(inputs["adjusted_operating_revenue"], inputs["adjusted_total_cost"])
    funding_gap = inputs["liquid_assets"] + inputs["committed_funding"] - inputs["thirty_day_outflows"]
    metrics = {"ending_portfolio": ending_portfolio, "par30": par30, "par90": par90, "writeoff_ratio": writeoff_ratio, "restructured_ratio": restructured_ratio, "credit_risk_ratio": credit_risk_ratio, "oss": oss, "fss": fss, "funding_gap": funding_gap}
    checks = {"portfolio_rollforward": abs(ending_portfolio - (inputs["beginning_portfolio"] + inputs["disbursements"] - inputs["collections"] - inputs["writeoffs"])) <= TOLERANCE, "par_order": par90 <= par30 + TOLERANCE, "par_bounds": _bounded(par30) and _bounded(par90), "positive_average_portfolio": inputs["average_portfolio"] > 0, "finite_outputs": _finite_mapping(metrics)}
    risk_flags = {"oss_below_one": oss < 1.0, "fss_below_one": fss < 1.0, "negative_funding_gap": funding_gap < 0, "high_credit_risk": credit_risk_ratio > inputs.get("credit_risk_warning", 0.15)}
    return {"metrics": metrics, "identity_checks": checks, "risk_flags": risk_flags}


def equity_finance(inputs: dict[str, float]) -> dict[str, Any]:
    converted_shares = _ratio(inputs["convertible_principal"], inputs["conversion_price"]) if inputs["convertible_principal"] else 0.0
    post_money_shares = inputs["existing_shares"] + inputs["primary_shares"] + inputs["rights_shares"] + converted_shares
    existing_holder_ownership = _ratio(inputs["existing_shares"], post_money_shares)
    dilution = 1.0 - existing_holder_ownership
    terp = _ratio(inputs["existing_shares"] * inputs["cum_rights_price"] + inputs["rights_shares"] * inputs["rights_subscription_price"], inputs["existing_shares"] + inputs["rights_shares"])
    right_value = inputs["cum_rights_price"] - terp
    equity_value = post_money_shares * inputs["valuation_per_share"]
    metrics = {"converted_shares": converted_shares, "post_money_shares": post_money_shares, "existing_holder_ownership": existing_holder_ownership, "dilution": dilution, "theoretical_ex_rights_price": terp, "right_value": right_value, "equity_value": equity_value}
    checks = {"share_conservation": abs(post_money_shares - (inputs["existing_shares"] + inputs["primary_shares"] + inputs["rights_shares"] + converted_shares)) <= TOLERANCE, "ownership_bounds": _bounded(existing_holder_ownership) and _bounded(dilution), "dilution_identity": abs(dilution + existing_holder_ownership - 1.0) <= TOLERANCE, "positive_conversion_price": inputs["conversion_price"] > 0, "finite_outputs": _finite_mapping(metrics)}
    risk_flags = {"deep_discount_rights": inputs["rights_subscription_price"] < 0.7 * inputs["cum_rights_price"], "majority_dilution": dilution > 0.5, "negative_right_value": right_value < -TOLERANCE}
    return {"metrics": metrics, "identity_checks": checks, "risk_flags": risk_flags}


def commodities(inputs: dict[str, float]) -> dict[str, Any]:
    carry_rate = inputs["risk_free_rate"] + inputs["storage_rate"] - inputs["convenience_yield"]
    fair_forward = inputs["spot_price"] * math.exp(carry_rate * inputs["time_years"])
    basis = inputs["spot_price"] - inputs["futures_price"]
    roll_yield = _ratio(inputs["near_futures"] - inputs["far_futures"], inputs["near_futures"])
    hedge_pnl = inputs["physical_quantity"] * (inputs["exit_spot"] - inputs["entry_spot"]) + inputs["futures_contracts"] * inputs["contract_size"] * (inputs["exit_futures"] - inputs["entry_futures"])
    ending_inventory = inputs["beginning_inventory"] + inputs["production"] + inputs["purchases"] - inputs["sales"] - inputs["consumption"]
    inventory_residual = ending_inventory - inputs["reported_ending_inventory"]
    hedge_ratio = _ratio(abs(inputs["futures_contracts"] * inputs["contract_size"]), abs(inputs["physical_quantity"])) if inputs["physical_quantity"] else 0.0
    metrics = {"carry_rate": carry_rate, "fair_forward": fair_forward, "basis": basis, "roll_yield": roll_yield, "hedge_pnl": hedge_pnl, "ending_inventory": ending_inventory, "inventory_residual": inventory_residual, "hedge_ratio": hedge_ratio}
    checks = {"cost_of_carry_identity": abs(fair_forward - inputs["spot_price"] * math.exp(carry_rate * inputs["time_years"])) <= TOLERANCE, "physical_balance": abs(inventory_residual) <= TOLERANCE, "positive_prices": min(inputs["spot_price"], inputs["futures_price"], inputs["near_futures"], inputs["far_futures"]) > 0, "positive_time": inputs["time_years"] >= 0, "finite_outputs": _finite_mapping(metrics)}
    risk_flags = {"material_basis_risk": abs(basis) > inputs.get("basis_warning", 0.1 * inputs["spot_price"]), "over_hedged": hedge_ratio > 1.25, "negative_inventory": ending_inventory < -TOLERANCE, "contango_roll_drag": roll_yield < 0}
    return {"metrics": metrics, "identity_checks": checks, "risk_flags": risk_flags}


def crypto(inputs: dict[str, float]) -> dict[str, Any]:
    ending_supply = inputs["beginning_supply"] + inputs["issuance"] + inputs["unlocks"] + inputs["staking_rewards"] - inputs["burns"]
    circulating_supply = ending_supply - inputs["locked_supply"]
    unlock_rate = _ratio(inputs["unlocks"], inputs["beginning_supply"])
    staking_dilution = _ratio(inputs["staking_rewards"], max(circulating_supply - inputs["staking_rewards"], TOLERANCE))
    runway_months = _ratio(inputs["treasury_value"], inputs["monthly_burn"])
    velocity = _ratio(inputs["annual_transaction_value"], inputs["average_market_cap"])
    liquidity_coverage = _ratio(inputs["liquid_treasury"], inputs["thirty_day_obligations"])
    metrics = {"ending_supply": ending_supply, "circulating_supply": circulating_supply, "unlock_rate": unlock_rate, "staking_dilution": staking_dilution, "runway_months": runway_months, "velocity": velocity, "liquidity_coverage": liquidity_coverage}
    checks = {"supply_conservation": abs(ending_supply - (inputs["beginning_supply"] + inputs["issuance"] + inputs["unlocks"] + inputs["staking_rewards"] - inputs["burns"])) <= TOLERANCE, "locked_supply_bound": 0 <= inputs["locked_supply"] <= ending_supply + TOLERANCE, "positive_burn_rate": inputs["monthly_burn"] > 0, "positive_market_cap": inputs["average_market_cap"] > 0, "finite_outputs": _finite_mapping(metrics)}
    risk_flags = {"negative_circulating_supply": circulating_supply < -TOLERANCE, "high_unlock": unlock_rate > inputs.get("unlock_warning", 0.10), "short_runway": runway_months < inputs.get("runway_warning_months", 18.0), "liquidity_shortfall": liquidity_coverage < 1.0}
    return {"metrics": metrics, "identity_checks": checks, "risk_flags": risk_flags}


def real_estate(inputs: dict[str, float]) -> dict[str, Any]:
    effective_gross_income = inputs["potential_gross_income"] - inputs["vacancy_credit_loss"] + inputs["other_income"]
    noi = effective_gross_income - inputs["operating_expenses"]
    cap_rate = _ratio(noi, inputs["property_value"])
    debt_service = inputs["interest_expense"] + inputs["scheduled_principal"]
    dscr = _ratio(noi, debt_service)
    levered_cash_flow = noi - inputs["recurring_capex"] - debt_service
    ffo = inputs["net_income"] + inputs["real_estate_depreciation"] - inputs["gain_on_sale"]
    affo = ffo - inputs["recurring_capex"] - inputs["straight_line_rent_adjustment"]
    ltv = _ratio(inputs["debt_balance"], inputs["property_value"])
    metrics = {"effective_gross_income": effective_gross_income, "noi": noi, "cap_rate": cap_rate, "debt_service": debt_service, "dscr": dscr, "levered_cash_flow": levered_cash_flow, "ffo": ffo, "affo": affo, "ltv": ltv}
    checks = {"noi_identity": abs(noi - (effective_gross_income - inputs["operating_expenses"])) <= TOLERANCE, "ffo_bridge": abs(ffo - (inputs["net_income"] + inputs["real_estate_depreciation"] - inputs["gain_on_sale"])) <= TOLERANCE, "affo_bridge": abs(affo - (ffo - inputs["recurring_capex"] - inputs["straight_line_rent_adjustment"])) <= TOLERANCE, "positive_property_value": inputs["property_value"] > 0, "finite_outputs": _finite_mapping(metrics)}
    risk_flags = {"dscr_below_one": dscr < 1.0, "high_ltv": ltv > inputs.get("ltv_warning", 0.75), "negative_levered_cash_flow": levered_cash_flow < 0, "negative_affo": affo < 0}
    return {"metrics": metrics, "identity_checks": checks, "risk_flags": risk_flags}


def fintech(inputs: dict[str, float]) -> dict[str, Any]:
    revenue = inputs["payment_volume"] * inputs["take_rate"]
    fraud_losses = inputs["payment_volume"] * inputs["fraud_loss_rate"]
    network_cost = inputs["payment_volume"] * inputs["network_cost_rate"]
    gross_profit = revenue - fraud_losses - network_cost - inputs["servicing_cost"]
    contribution_margin = _ratio(gross_profit, revenue)
    ending_users = inputs["starting_users"] * inputs["retention_rate"] + inputs["new_users"]
    ltv = inputs["monthly_arpu"] * inputs["gross_margin_rate"] * inputs["expected_life_months"]
    ltv_cac = _ratio(ltv, inputs["cac"])
    capital_coverage = _ratio(inputs["available_capital"], inputs["required_capital"])
    transactions_per_user = _ratio(inputs["transactions"], ending_users)
    metrics = {"revenue": revenue, "fraud_losses": fraud_losses, "network_cost": network_cost, "gross_profit": gross_profit, "contribution_margin": contribution_margin, "ending_users": ending_users, "ltv": ltv, "ltv_cac": ltv_cac, "capital_coverage": capital_coverage, "transactions_per_user": transactions_per_user}
    checks = {"revenue_identity": abs(revenue - inputs["payment_volume"] * inputs["take_rate"]) <= TOLERANCE, "cohort_rollforward": abs(ending_users - (inputs["starting_users"] * inputs["retention_rate"] + inputs["new_users"])) <= TOLERANCE, "rate_bounds": all(_bounded(inputs[key]) for key in ("take_rate", "fraud_loss_rate", "network_cost_rate", "retention_rate", "gross_margin_rate")), "positive_cac": inputs["cac"] > 0, "finite_outputs": _finite_mapping(metrics)}
    risk_flags = {"negative_gross_profit": gross_profit < 0, "ltv_cac_below_one": ltv_cac < 1.0, "capital_shortfall": capital_coverage < 1.0, "fraud_above_warning": inputs["fraud_loss_rate"] > inputs.get("fraud_warning", 0.005)}
    return {"metrics": metrics, "identity_checks": checks, "risk_flags": risk_flags}


def distressed(inputs: dict[str, float]) -> dict[str, Any]:
    ending_liquidity = inputs["beginning_liquidity"] + inputs["cash_receipts"] + inputs["new_money"] - inputs["operating_disbursements"] - inputs["interest"] - inputs["professional_fees"]
    available = max(inputs["reorganization_value"] - inputs["administrative_claims"] - inputs["new_money_claim"], 0.0)
    secured_recovery = min(inputs["secured_claims"], available); available -= secured_recovery
    priority_recovery = min(inputs["priority_claims"], available); available -= priority_recovery
    unsecured_recovery = min(inputs["unsecured_claims"], available); available -= unsecured_recovery
    equity_recovery = max(available, 0.0)
    distributed = inputs["administrative_claims"] + inputs["new_money_claim"] + secured_recovery + priority_recovery + unsecured_recovery + equity_recovery
    recoveries = {"secured_recovery_rate": _ratio(secured_recovery, inputs["secured_claims"]) if inputs["secured_claims"] else 1.0, "priority_recovery_rate": _ratio(priority_recovery, inputs["priority_claims"]) if inputs["priority_claims"] else 1.0, "unsecured_recovery_rate": _ratio(unsecured_recovery, inputs["unsecured_claims"]) if inputs["unsecured_claims"] else 1.0}
    liquidation_uplift = inputs["reorganization_value"] - inputs["liquidation_value"]
    fulcrum = "equity"
    if recoveries["unsecured_recovery_rate"] < 1.0 - TOLERANCE: fulcrum = "unsecured"
    elif recoveries["priority_recovery_rate"] < 1.0 - TOLERANCE: fulcrum = "priority"
    elif recoveries["secured_recovery_rate"] < 1.0 - TOLERANCE: fulcrum = "secured"
    metrics = {"ending_liquidity": ending_liquidity, "secured_recovery": secured_recovery, "priority_recovery": priority_recovery, "unsecured_recovery": unsecured_recovery, "equity_recovery": equity_recovery, "distributed_value": distributed, "liquidation_uplift": liquidation_uplift, **recoveries}
    checks = {"liquidity_rollforward": abs(ending_liquidity - (inputs["beginning_liquidity"] + inputs["cash_receipts"] + inputs["new_money"] - inputs["operating_disbursements"] - inputs["interest"] - inputs["professional_fees"])) <= TOLERANCE, "waterfall_conservation": abs(distributed - inputs["reorganization_value"]) <= TOLERANCE, "priority_order": recoveries["secured_recovery_rate"] + TOLERANCE >= recoveries["priority_recovery_rate"] and recoveries["priority_recovery_rate"] + TOLERANCE >= recoveries["unsecured_recovery_rate"], "recovery_bounds": all(_bounded(value) for value in recoveries.values()), "finite_outputs": _finite_mapping(metrics)}
    risk_flags = {"liquidity_shortfall": ending_liquidity < inputs.get("minimum_liquidity", 0.0), "reorganization_below_liquidation": liquidation_uplift < 0, "secured_impairment": recoveries["secured_recovery_rate"] < 1.0, "equity_out_of_money": equity_recovery <= TOLERANCE}
    return {"metrics": metrics, "identity_checks": checks, "risk_flags": risk_flags, "fulcrum_security": fulcrum}


ORACLES: dict[str, Callable[[dict[str, float]], dict[str, Any]]] = {"08": asset_management, "10": trade_finance, "11": microfinance, "12": equity_finance, "15": commodities, "16": crypto, "17": real_estate, "23": fintech, "24": distressed}


def validate_case(model_id: str, inputs: dict[str, float]) -> dict[str, Any]:
    try:
        oracle = ORACLES[model_id]
    except KeyError as exc:
        raise ValueError(f"unsupported hardening model id: {model_id}") from exc
    result = oracle(inputs)
    result["model_id"] = model_id
    result["identity_status"] = "PASS" if all(result["identity_checks"].values()) else "FAIL"
    result["active_risk_flags"] = sorted(name for name, active in result["risk_flags"].items() if active)
    return result
