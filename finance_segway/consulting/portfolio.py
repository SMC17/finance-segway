"""Confidence-adjusted business cases and constrained initiative selection."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import inf
from typing import Iterable, Mapping

from .schema import AutomationCase, RiskTier


RISK_PENALTY = {
    RiskTier.LOW: 0.00,
    RiskTier.MODERATE: 0.05,
    RiskTier.HIGH: 0.15,
    RiskTier.CRITICAL: 0.30,
}


@dataclass(frozen=True)
class CaseEconomics:
    case_id: str
    gross_annual_value: float
    net_annual_value: float
    npv: float
    confidence_adjusted_npv: float
    risk_adjusted_npv: float
    payback_months: float
    priority_score: float


@dataclass(frozen=True)
class PortfolioSelection:
    selected_case_ids: tuple[str, ...]
    implementation_cost: float
    risk_adjusted_npv: float
    unspent_budget: float


def evaluate_case(
    case: AutomationCase,
    *,
    hurdle_rate: float = 0.12,
    life_years: int = 3,
) -> CaseEconomics:
    if hurdle_rate < 0 or life_years <= 0:
        raise ValueError("hurdle_rate must be nonnegative and life_years positive")
    gross = case.annual_labor_savings + case.annual_revenue_gain + case.annual_loss_avoided
    net = gross - case.recurring_annual_cost
    npv = -case.implementation_cost + case.working_capital_release
    for year in range(1, life_years + 1):
        npv += net / ((1 + hurdle_rate) ** year)
    confidence = case.feasibility * case.adoption_probability * case.evidence_confidence
    confidence_adjusted = npv * confidence
    risk_adjusted = confidence_adjusted - abs(npv) * RISK_PENALTY[case.risk_tier]
    if net <= 0:
        payback = inf
    else:
        payback = 12 * max(case.implementation_cost - case.working_capital_release, 0) / net
    priority = risk_adjusted / max(case.implementation_cost, 1.0) / max(case.delivery_months, 0.25)
    return CaseEconomics(
        case_id=case.case_id,
        gross_annual_value=gross,
        net_annual_value=net,
        npv=npv,
        confidence_adjusted_npv=confidence_adjusted,
        risk_adjusted_npv=risk_adjusted,
        payback_months=payback,
        priority_score=priority,
    )


def _dependencies_satisfied(selected: set[str], cases: Mapping[str, AutomationCase]) -> bool:
    return all(set(cases[case_id].dependencies).issubset(selected) for case_id in selected)


def select_portfolio(
    cases: Iterable[AutomationCase],
    *,
    budget: float,
    max_high_risk: int = 1,
    hurdle_rate: float = 0.12,
    life_years: int = 3,
) -> PortfolioSelection:
    items = list(cases)
    if budget < 0 or max_high_risk < 0:
        raise ValueError("budget and max_high_risk must be nonnegative")
    if len(items) > 20:
        raise ValueError("exact portfolio selection is limited to 20 cases")
    by_id = {item.case_id: item for item in items}
    if len(by_id) != len(items):
        raise ValueError("case ids must be unique")
    unknown_dependencies = {
        dependency
        for item in items
        for dependency in item.dependencies
        if dependency not in by_id
    }
    if unknown_dependencies:
        raise ValueError(f"unknown dependencies: {sorted(unknown_dependencies)}")
    economics = {item.case_id: evaluate_case(item, hurdle_rate=hurdle_rate, life_years=life_years) for item in items}
    best_ids: tuple[str, ...] = ()
    best_value = 0.0
    best_cost = 0.0
    for size in range(1, len(items) + 1):
        for subset in combinations(items, size):
            selected = {item.case_id for item in subset}
            if not _dependencies_satisfied(selected, by_id):
                continue
            cost = sum(item.implementation_cost for item in subset)
            if cost > budget + 1e-9:
                continue
            high_risk = sum(item.risk_tier >= RiskTier.HIGH for item in subset)
            if high_risk > max_high_risk:
                continue
            value = sum(economics[item.case_id].risk_adjusted_npv for item in subset)
            ids = tuple(sorted(selected))
            if value > best_value + 1e-9 or (
                abs(value - best_value) <= 1e-9 and (cost < best_cost or not best_ids)
            ):
                best_ids, best_value, best_cost = ids, value, cost
    return PortfolioSelection(best_ids, best_cost, best_value, budget - best_cost)


def realization_variance(
    *,
    baseline: float,
    target: float,
    actual: float,
    higher_is_better: bool = True,
) -> Mapping[str, float]:
    planned_change = target - baseline
    actual_change = actual - baseline
    if not higher_is_better:
        planned_change *= -1
        actual_change *= -1
    realization = actual_change / planned_change if planned_change > 0 else 0.0
    return {
        "baseline": baseline,
        "target": target,
        "actual": actual,
        "planned_change": planned_change,
        "actual_change": actual_change,
        "realization_pct": realization,
        "variance_to_target": actual - target,
    }
