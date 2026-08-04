"""Independent cross-domain finance oracles.

These calculations are intentionally separate from workbook formulas.  They are
small, deterministic reference engines for portfolio capital allocation,
liquidity contagion, counterparty exposure, collateral and margin, tax leakage,
legal-entity priority, and regime scenarios.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from math import isfinite
from typing import Any, Iterable

TOLERANCE = 1e-9


def _require_nonnegative(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return value


def _bounded(name: str, value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    value = float(value)
    if not isfinite(value) or value < lower or value > upper:
        raise ValueError(f"{name} must be between {lower} and {upper}")
    return value


def capital_allocation(case: dict[str, Any]) -> dict[str, Any]:
    """Allocate scarce capital and liquidity by positive risk-adjusted value.

    Units declare a requested capital amount, expected return, expected loss,
    economic-capital charge and minimum liquidity reserve.  The allocator ranks
    marginal risk-adjusted value per dollar and fills requests subject to both
    group capital and group liquidity constraints.
    """

    available_capital = _require_nonnegative("available_capital", case["available_capital"])
    available_liquidity = _require_nonnegative("available_liquidity", case["available_liquidity"])
    units = []
    for raw in case["units"]:
        requested = _require_nonnegative("requested_capital", raw["requested_capital"])
        expected_return = float(raw["expected_return"])
        expected_loss = _require_nonnegative("expected_loss", raw["expected_loss"])
        capital_charge = _require_nonnegative("capital_charge", raw["capital_charge"])
        liquidity_per_capital = _require_nonnegative(
            "liquidity_per_capital", raw["liquidity_per_capital"]
        )
        risk_adjusted_value = expected_return - expected_loss - capital_charge
        score = risk_adjusted_value / requested if requested else 0.0
        units.append(
            {
                "name": str(raw["name"]),
                "requested": requested,
                "liquidity_per_capital": liquidity_per_capital,
                "risk_adjusted_value": risk_adjusted_value,
                "score": score,
            }
        )

    allocations: dict[str, float] = {unit["name"]: 0.0 for unit in units}
    remaining_capital = available_capital
    remaining_liquidity = available_liquidity
    for unit in sorted(units, key=lambda item: (item["score"], item["name"]), reverse=True):
        if unit["score"] <= 0 or remaining_capital <= TOLERANCE:
            continue
        liquidity_limit = (
            remaining_liquidity / unit["liquidity_per_capital"]
            if unit["liquidity_per_capital"] > 0
            else unit["requested"]
        )
        amount = min(unit["requested"], remaining_capital, liquidity_limit)
        allocations[unit["name"]] = max(0.0, amount)
        remaining_capital -= amount
        remaining_liquidity -= amount * unit["liquidity_per_capital"]

    allocated_capital = sum(allocations.values())
    used_liquidity = sum(
        allocations[unit["name"]] * unit["liquidity_per_capital"] for unit in units
    )
    value_created = sum(
        allocations[unit["name"]]
        * (unit["risk_adjusted_value"] / unit["requested"] if unit["requested"] else 0.0)
        for unit in units
    )
    identities = {
        "capital_conservation": abs(available_capital - allocated_capital - remaining_capital)
        <= TOLERANCE,
        "liquidity_conservation": abs(available_liquidity - used_liquidity - remaining_liquidity)
        <= TOLERANCE,
        "allocation_bounds": all(
            allocations[unit["name"]] <= unit["requested"] + TOLERANCE for unit in units
        ),
    }
    flags = []
    if remaining_liquidity <= TOLERANCE and any(
        allocations[unit["name"]] + TOLERANCE < unit["requested"] and unit["score"] > 0
        for unit in units
    ):
        flags.append("liquidity_binding")
    if remaining_capital <= TOLERANCE and any(
        allocations[unit["name"]] + TOLERANCE < unit["requested"] and unit["score"] > 0
        for unit in units
    ):
        flags.append("capital_binding")
    if any(unit["score"] <= 0 for unit in units):
        flags.append("negative_risk_adjusted_opportunity")
    return {
        "allocations": allocations,
        "metrics": {
            "allocated_capital": allocated_capital,
            "remaining_capital": remaining_capital,
            "used_liquidity": used_liquidity,
            "remaining_liquidity": remaining_liquidity,
            "risk_adjusted_value_created": value_created,
        },
        "identity_checks": identities,
        "active_risk_flags": flags,
    }


@dataclass(frozen=True)
class Exposure:
    lender: str
    borrower: str
    amount: float
    recovery: float
    collateral: float = 0.0
    netting_set: str = "default"


def liquidity_contagion(case: dict[str, Any]) -> dict[str, Any]:
    """Propagate liquidity losses through a directed exposure network."""

    liquidity = {
        str(name): _require_nonnegative(f"liquidity[{name}]", value)
        for name, value in case["liquidity"].items()
    }
    minimum = {
        str(name): _require_nonnegative(f"minimum_liquidity[{name}]", value)
        for name, value in case["minimum_liquidity"].items()
    }
    if set(liquidity) != set(minimum):
        raise ValueError("liquidity and minimum_liquidity must cover the same entities")
    exposures = [
        Exposure(
            lender=str(item["lender"]),
            borrower=str(item["borrower"]),
            amount=_require_nonnegative("exposure amount", item["amount"]),
            recovery=_bounded("recovery", item.get("recovery", 0.0)),
            collateral=_require_nonnegative("collateral", item.get("collateral", 0.0)),
            netting_set=str(item.get("netting_set", "default")),
        )
        for item in case.get("exposures", [])
    ]
    shocked = {
        str(name): _require_nonnegative(f"shock[{name}]", value)
        for name, value in case.get("initial_outflows", {}).items()
    }
    for name, value in shocked.items():
        if name not in liquidity:
            raise ValueError(f"unknown shocked entity {name}")
        liquidity[name] -= value

    defaulted: set[str] = set()
    queue: deque[str] = deque(
        name for name in liquidity if liquidity[name] < minimum[name] - TOLERANCE
    )
    losses_by_lender: dict[str, float] = defaultdict(float)
    rounds = 0
    while queue:
        borrower = queue.popleft()
        if borrower in defaulted:
            continue
        defaulted.add(borrower)
        rounds += 1
        for exposure in exposures:
            if exposure.borrower != borrower or exposure.lender in defaulted:
                continue
            unsecured = max(0.0, exposure.amount - exposure.collateral)
            loss = unsecured * (1.0 - exposure.recovery)
            liquidity[exposure.lender] -= loss
            losses_by_lender[exposure.lender] += loss
            if (
                exposure.lender not in defaulted
                and liquidity[exposure.lender] < minimum[exposure.lender] - TOLERANCE
            ):
                queue.append(exposure.lender)

    initial_liquidity = sum(
        _require_nonnegative(f"liquidity[{name}]", value)
        for name, value in case["liquidity"].items()
    )
    initial_outflows = sum(shocked.values())
    transmitted_losses = sum(losses_by_lender.values())
    ending_liquidity = sum(liquidity.values())
    identities = {
        "liquidity_loss_conservation": abs(
            initial_liquidity - initial_outflows - transmitted_losses - ending_liquidity
        )
        <= TOLERANCE,
        "default_threshold_consistency": all(
            liquidity[name] < minimum[name] + TOLERANCE for name in defaulted
        ),
    }
    flags = []
    if defaulted:
        flags.append("entity_default")
    if len(defaulted) > len(shocked):
        flags.append("contagion_propagated")
    if transmitted_losses > 0:
        flags.append("counterparty_loss")
    return {
        "ending_liquidity": liquidity,
        "defaulted_entities": sorted(defaulted),
        "losses_by_lender": dict(sorted(losses_by_lender.items())),
        "metrics": {
            "rounds": rounds,
            "initial_outflows": initial_outflows,
            "transmitted_losses": transmitted_losses,
            "ending_liquidity": ending_liquidity,
        },
        "identity_checks": identities,
        "active_risk_flags": flags,
    }


def counterparty_exposure(case: dict[str, Any]) -> dict[str, Any]:
    """Calculate gross, netted, collateralized and stressed counterparty exposure."""

    grouped: dict[tuple[str, str], dict[str, float]] = defaultdict(
        lambda: {"positive": 0.0, "negative": 0.0, "collateral": 0.0}
    )
    for trade in case["trades"]:
        counterparty = str(trade["counterparty"])
        netting_set = str(trade.get("netting_set", "default"))
        mtm = float(trade["mtm"])
        collateral = _require_nonnegative("collateral", trade.get("collateral", 0.0))
        group = grouped[(counterparty, netting_set)]
        if mtm >= 0:
            group["positive"] += mtm
        else:
            group["negative"] += -mtm
        group["collateral"] += collateral

    stress_multiplier = _require_nonnegative(
        "stress_multiplier", case.get("stress_multiplier", 1.0)
    )
    wrong_way_addon = _bounded("wrong_way_addon", case.get("wrong_way_addon", 0.0))
    results = {}
    total_gross = total_netted = total_secured = total_stressed = 0.0
    for key, values in sorted(grouped.items()):
        counterparty, netting_set = key
        gross = values["positive"]
        netted = max(0.0, values["positive"] - values["negative"])
        secured = max(0.0, netted - values["collateral"])
        stressed = secured * stress_multiplier * (1.0 + wrong_way_addon)
        results[f"{counterparty}:{netting_set}"] = {
            "gross_positive": gross,
            "netted_exposure": netted,
            "collateralized_exposure": secured,
            "stressed_exposure": stressed,
        }
        total_gross += gross
        total_netted += netted
        total_secured += secured
        total_stressed += stressed

    identities = {
        "netting_not_increasing_exposure": total_netted <= total_gross + TOLERANCE,
        "collateral_not_increasing_exposure": total_secured <= total_netted + TOLERANCE,
        "stress_nonnegative": total_stressed >= -TOLERANCE,
    }
    flags = []
    concentration_limit = _require_nonnegative(
        "concentration_limit", case.get("concentration_limit", float("inf"))
    )
    if any(item["stressed_exposure"] > concentration_limit for item in results.values()):
        flags.append("counterparty_concentration")
    if wrong_way_addon > 0:
        flags.append("wrong_way_risk")
    return {
        "netting_sets": results,
        "metrics": {
            "gross_positive_exposure": total_gross,
            "netted_exposure": total_netted,
            "collateralized_exposure": total_secured,
            "stressed_exposure": total_stressed,
        },
        "identity_checks": identities,
        "active_risk_flags": flags,
    }


def collateral_margin(case: dict[str, Any]) -> dict[str, Any]:
    """Value eligible collateral after haircuts and reconcile margin requirements."""

    variation_margin = max(0.0, float(case["variation_margin_requirement"]))
    initial_margin = _require_nonnegative(
        "initial_margin_requirement", case["initial_margin_requirement"]
    )
    liquidity_addon = _require_nonnegative("liquidity_addon", case.get("liquidity_addon", 0.0))
    collateral_value = 0.0
    concentration: dict[str, float] = defaultdict(float)
    for asset in case["collateral"]:
        market_value = _require_nonnegative("market_value", asset["market_value"])
        haircut = _bounded("haircut", asset["haircut"])
        fx_haircut = _bounded("fx_haircut", asset.get("fx_haircut", 0.0))
        eligible = bool(asset.get("eligible", True))
        adjusted = market_value * (1.0 - haircut) * (1.0 - fx_haircut) if eligible else 0.0
        collateral_value += adjusted
        concentration[str(asset.get("issuer", "unknown"))] += adjusted
    requirement = variation_margin + initial_margin + liquidity_addon
    shortfall = max(0.0, requirement - collateral_value)
    excess = max(0.0, collateral_value - requirement)
    identities = {
        "margin_reconciliation": abs(requirement - collateral_value - shortfall + excess)
        <= TOLERANCE,
        "nonnegative_shortfall": shortfall >= -TOLERANCE,
    }
    flags = []
    if shortfall > TOLERANCE:
        flags.append("margin_shortfall")
    concentration_limit = _bounded(
        "concentration_limit", case.get("concentration_limit", 1.0)
    )
    if collateral_value > 0 and any(
        value / collateral_value > concentration_limit + TOLERANCE
        for value in concentration.values()
    ):
        flags.append("collateral_concentration")
    return {
        "metrics": {
            "margin_requirement": requirement,
            "haircut_collateral_value": collateral_value,
            "shortfall": shortfall,
            "excess": excess,
        },
        "issuer_concentration": dict(sorted(concentration.items())),
        "identity_checks": identities,
        "active_risk_flags": flags,
    }


def tax_leakage(case: dict[str, Any]) -> dict[str, Any]:
    """Calculate jurisdictional cash tax, interest limits, NOL use and leakage."""

    total_pre_tax = total_tax = total_interest = total_disallowed = 0.0
    by_jurisdiction = {}
    for item in case["jurisdictions"]:
        name = str(item["name"])
        ebitda = float(item["ebitda"])
        depreciation = _require_nonnegative("depreciation", item.get("depreciation", 0.0))
        interest = _require_nonnegative("interest", item.get("interest", 0.0))
        interest_cap = _bounded("interest_cap", item.get("interest_cap", 1.0))
        tax_rate = _bounded("tax_rate", item["tax_rate"])
        nol = _require_nonnegative("nol", item.get("nol", 0.0))
        withholding = _require_nonnegative("withholding_tax", item.get("withholding_tax", 0.0))
        deductible_interest = min(interest, max(0.0, ebitda) * interest_cap)
        disallowed_interest = interest - deductible_interest
        pre_tax = ebitda - depreciation - deductible_interest
        nol_used = min(nol, max(0.0, pre_tax))
        taxable_income = max(0.0, pre_tax - nol_used)
        cash_tax = taxable_income * tax_rate + withholding
        by_jurisdiction[name] = {
            "pre_tax_income": pre_tax,
            "deductible_interest": deductible_interest,
            "disallowed_interest": disallowed_interest,
            "nol_used": nol_used,
            "taxable_income": taxable_income,
            "cash_tax": cash_tax,
        }
        total_pre_tax += pre_tax
        total_tax += cash_tax
        total_interest += interest
        total_disallowed += disallowed_interest
    effective_rate = total_tax / total_pre_tax if total_pre_tax > 0 else 0.0
    identities = {
        "interest_reconciliation": abs(
            total_interest
            - sum(item["deductible_interest"] for item in by_jurisdiction.values())
            - total_disallowed
        )
        <= TOLERANCE,
        "tax_nonnegative": total_tax >= -TOLERANCE,
    }
    flags = []
    if total_disallowed > TOLERANCE:
        flags.append("interest_deduction_limited")
    if effective_rate > _bounded("effective_tax_warning", case.get("effective_tax_warning", 1.0)):
        flags.append("tax_leakage")
    return {
        "jurisdictions": by_jurisdiction,
        "metrics": {
            "pre_tax_income": total_pre_tax,
            "cash_tax": total_tax,
            "effective_tax_rate": effective_rate,
            "disallowed_interest": total_disallowed,
        },
        "identity_checks": identities,
        "active_risk_flags": flags,
    }


def legal_entity_waterfall(case: dict[str, Any]) -> dict[str, Any]:
    """Distribute entity value by legal priority and structural subordination."""

    entity_values = {
        str(name): _require_nonnegative(f"entity_values[{name}]", value)
        for name, value in case["entity_values"].items()
    }
    claims = []
    for raw in case["claims"]:
        entity = str(raw["entity"])
        if entity not in entity_values:
            raise ValueError(f"unknown claim entity {entity}")
        claims.append(
            {
                "name": str(raw["name"]),
                "entity": entity,
                "priority": int(raw["priority"]),
                "claim": _require_nonnegative("claim", raw["claim"]),
                "guarantors": [str(name) for name in raw.get("guarantors", [])],
            }
        )
    recoveries: dict[str, float] = {claim["name"]: 0.0 for claim in claims}
    remaining = dict(entity_values)
    for claim in sorted(claims, key=lambda item: (item["priority"], item["name"])):
        sources = [claim["entity"], *claim["guarantors"]]
        unpaid = claim["claim"]
        for entity in sources:
            if entity not in remaining or unpaid <= TOLERANCE:
                continue
            payment = min(unpaid, remaining[entity])
            recoveries[claim["name"]] += payment
            remaining[entity] -= payment
            unpaid -= payment
    total_value = sum(entity_values.values())
    total_recovery = sum(recoveries.values())
    residual = sum(remaining.values())
    identities = {
        "waterfall_conservation": abs(total_value - total_recovery - residual) <= TOLERANCE,
        "claim_bounds": all(
            recoveries[claim["name"]] <= claim["claim"] + TOLERANCE for claim in claims
        ),
        "entity_value_nonnegative": all(value >= -TOLERANCE for value in remaining.values()),
    }
    flags = []
    if any(recoveries[claim["name"]] + TOLERANCE < claim["claim"] for claim in claims):
        flags.append("impaired_claim")
    holdco_claims = [claim for claim in claims if claim["entity"].lower().startswith("holdco")]
    if any(recoveries[claim["name"]] + TOLERANCE < claim["claim"] for claim in holdco_claims):
        flags.append("structural_subordination")
    return {
        "recoveries": recoveries,
        "remaining_entity_value": remaining,
        "metrics": {
            "total_entity_value": total_value,
            "total_recovery": total_recovery,
            "residual_value": residual,
        },
        "identity_checks": identities,
        "active_risk_flags": flags,
    }


def regime_scenario(case: dict[str, Any]) -> dict[str, Any]:
    """Apply a coherent macro regime vector to portfolio sensitivities."""

    factors = {str(name): float(value) for name, value in case["factor_shocks"].items()}
    pnl_by_position = {}
    total_pnl = 0.0
    for position in case["positions"]:
        name = str(position["name"])
        base_value = float(position.get("base_value", 0.0))
        linear = 0.0
        for factor, sensitivity in position.get("sensitivities", {}).items():
            linear += float(sensitivity) * factors.get(str(factor), 0.0)
        convex = 0.0
        for factor, gamma in position.get("convexities", {}).items():
            shock = factors.get(str(factor), 0.0)
            convex += 0.5 * float(gamma) * shock * shock
        pnl = linear + convex
        pnl_by_position[name] = pnl
        total_pnl += pnl
        if not isfinite(base_value + pnl):
            raise ValueError(f"non-finite shocked value for {name}")
    loss_limit = _require_nonnegative("loss_limit", case.get("loss_limit", float("inf")))
    identities = {
        "pnl_additivity": abs(total_pnl - sum(pnl_by_position.values())) <= TOLERANCE,
        "finite_shocked_values": True,
    }
    flags = []
    if -total_pnl > loss_limit:
        flags.append("regime_loss_limit_breach")
    if len([value for value in factors.values() if abs(value) > TOLERANCE]) >= 3:
        flags.append("multi_factor_regime")
    return {
        "pnl_by_position": pnl_by_position,
        "metrics": {"portfolio_pnl": total_pnl, "loss_limit": loss_limit},
        "identity_checks": identities,
        "active_risk_flags": flags,
    }


ORACLES = {
    "capital_allocation": capital_allocation,
    "liquidity_contagion": liquidity_contagion,
    "counterparty_network": counterparty_exposure,
    "collateral_margin": collateral_margin,
    "tax_leakage": tax_leakage,
    "legal_entity_waterfall": legal_entity_waterfall,
    "regime_scenario": regime_scenario,
}


def validate_case(engine: str, inputs: dict[str, Any]) -> dict[str, Any]:
    if engine not in ORACLES:
        raise KeyError(f"unknown cross-domain oracle {engine}")
    result = ORACLES[engine](inputs)
    result["identity_status"] = (
        "PASS" if all(result["identity_checks"].values()) else "FAIL"
    )
    return result


def validate_cases(cases: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": case["id"],
            "engine": case["engine"],
            "type": case["type"],
            **validate_case(case["engine"], case["inputs"]),
        }
        for case in cases
    ]
