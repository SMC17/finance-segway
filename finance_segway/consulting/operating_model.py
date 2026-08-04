"""P&L-linked company operating model and bottleneck economics."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .schema import Activity, BusinessFunction


@dataclass(frozen=True)
class ActivityEconomics:
    activity_id: str
    utilization: float | None
    annual_labor_cost: float
    annual_quality_loss: float
    constrained_units: float
    constrained_contribution: float


@dataclass(frozen=True)
class InterventionEstimate:
    activity_id: str
    labor_savings: float
    quality_savings: float
    throughput_value: float
    gross_annual_value: float


class OperatingModel:
    """Directed activity graph with auditable operating economics."""

    def __init__(self, activities: Iterable[Activity]) -> None:
        items = list(activities)
        self.activities = {item.activity_id: item for item in items}
        if len(self.activities) != len(items):
            raise ValueError("activity ids must be unique")
        if not self.activities:
            raise ValueError("operating model requires at least one activity")
        self._validate_dependencies()

    def _validate_dependencies(self) -> None:
        known = set(self.activities)
        for activity in self.activities.values():
            unknown = set(activity.predecessors) - known
            if unknown:
                raise ValueError(f"{activity.activity_id} has unknown predecessors: {sorted(unknown)}")
        self.dependency_order()

    def dependency_order(self) -> tuple[str, ...]:
        remaining = {key: set(value.predecessors) for key, value in self.activities.items()}
        order: list[str] = []
        while remaining:
            ready = sorted(key for key, predecessors in remaining.items() if not predecessors)
            if not ready:
                raise ValueError("operating model contains a dependency cycle")
            order.extend(ready)
            for key in ready:
                del remaining[key]
            for predecessors in remaining.values():
                predecessors.difference_update(ready)
        return tuple(order)

    def economics(self, activity_id: str) -> ActivityEconomics:
        activity = self.activities[activity_id]
        annual_hours = activity.annual_volume * activity.minutes_per_unit / 60
        labor_cost = annual_hours * activity.loaded_cost_per_hour
        quality_loss = activity.annual_volume * activity.error_rate * activity.cost_per_error
        if activity.capacity_units > 0:
            utilization = activity.annual_volume / activity.capacity_units
            constrained_units = max(activity.annual_volume - activity.capacity_units, 0.0)
        else:
            utilization = None
            constrained_units = 0.0
        return ActivityEconomics(
            activity_id=activity_id,
            utilization=utilization,
            annual_labor_cost=labor_cost,
            annual_quality_loss=quality_loss,
            constrained_units=constrained_units,
            constrained_contribution=constrained_units * activity.contribution_per_unit,
        )

    def estimate_intervention(
        self,
        activity_id: str,
        *,
        labor_automation: float = 0.0,
        error_reduction: float = 0.0,
        capacity_increase: float = 0.0,
    ) -> InterventionEstimate:
        for name, value in (
            ("labor_automation", labor_automation),
            ("error_reduction", error_reduction),
            ("capacity_increase", capacity_increase),
        ):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        activity = self.activities[activity_id]
        baseline = self.economics(activity_id)
        labor_savings = baseline.annual_labor_cost * labor_automation
        quality_savings = baseline.annual_quality_loss * error_reduction
        incremental_capacity = activity.capacity_units * capacity_increase
        captured_units = min(baseline.constrained_units, incremental_capacity)
        throughput_value = captured_units * activity.contribution_per_unit
        return InterventionEstimate(
            activity_id=activity_id,
            labor_savings=labor_savings,
            quality_savings=quality_savings,
            throughput_value=throughput_value,
            gross_annual_value=labor_savings + quality_savings + throughput_value,
        )

    def bottlenecks(self, minimum_utilization: float = 1.0) -> tuple[ActivityEconomics, ...]:
        results = [self.economics(activity_id) for activity_id in self.activities]
        filtered = [
            item for item in results
            if item.utilization is not None and item.utilization >= minimum_utilization
        ]
        return tuple(sorted(filtered, key=lambda item: (-float(item.utilization), item.activity_id)))

    def rollup_by_function(self) -> Mapping[str, Mapping[str, float]]:
        result: dict[str, dict[str, float]] = {}
        for activity_id, activity in self.activities.items():
            economics = self.economics(activity_id)
            bucket = result.setdefault(activity.function.value, {
                "annual_labor_cost": 0.0,
                "annual_quality_loss": 0.0,
                "constrained_contribution": 0.0,
            })
            bucket["annual_labor_cost"] += economics.annual_labor_cost
            bucket["annual_quality_loss"] += economics.annual_quality_loss
            bucket["constrained_contribution"] += economics.constrained_contribution
        return result


def canonical_value_chain() -> OperatingModel:
    """Return the structural company value chain with zero-value placeholders.

    Callers populate company-specific volumes and economics. Zero defaults are
    deliberate: the library never invents a client's ROI.
    """
    activities = [
        Activity("forecast_capacity", "Forecast demand and plan capacity", BusinessFunction.OPERATIONS, "working_capital"),
        Activity("acquire_customers", "Acquire customers", BusinessFunction.MARKETING, "revenue_growth"),
        Activity("qualify_sell", "Qualify and sell", BusinessFunction.SALES, "revenue_growth", ("acquire_customers",)),
        Activity("quote_contract", "Quote, price, and contract", BusinessFunction.SALES, "gross_margin", ("qualify_sell",)),
        Activity("source_inputs", "Source and procure inputs", BusinessFunction.PROCUREMENT, "cost_of_goods", ("forecast_capacity",)),
        Activity("recruit_onboard", "Recruit and onboard people", BusinessFunction.PEOPLE, "delivery_capacity", ("forecast_capacity",)),
        Activity("schedule_dispatch", "Schedule and dispatch work", BusinessFunction.OPERATIONS, "utilization", ("quote_contract", "source_inputs", "recruit_onboard")),
        Activity("deliver", "Deliver service or manufacture product", BusinessFunction.OPERATIONS, "gross_margin", ("schedule_dispatch",)),
        Activity("quality_compliance", "Maintain quality and compliance", BusinessFunction.QUALITY, "loss_avoidance", ("deliver",)),
        Activity("retain_grow", "Retain, renew, and grow customers", BusinessFunction.CUSTOMER, "net_revenue_retention", ("quality_compliance",)),
        Activity("bill_collect", "Bill and collect", BusinessFunction.FINANCE, "cash_conversion", ("quality_compliance",)),
    ]
    return OperatingModel(activities)
