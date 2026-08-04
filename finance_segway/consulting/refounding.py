"""Unit-economics simulator for redesigning a service business from first principles."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ProcessRedesign:
    activity_id: str
    annual_volume: float
    revenue_per_unit: float
    other_variable_cost_per_unit: float
    baseline_minutes_per_unit: float
    redesigned_minutes_per_unit: float
    loaded_labor_cost_per_hour: float
    baseline_error_rate: float = 0.0
    redesigned_error_rate: float = 0.0
    loss_per_error: float = 0.0

    def __post_init__(self) -> None:
        nonnegative = (
            self.annual_volume, self.revenue_per_unit,
            self.other_variable_cost_per_unit, self.baseline_minutes_per_unit,
            self.redesigned_minutes_per_unit, self.loaded_labor_cost_per_hour,
            self.loss_per_error,
        )
        if any(value < 0 for value in nonnegative):
            raise ValueError("process economics must be nonnegative")
        if not 0 <= self.baseline_error_rate <= 1 or not 0 <= self.redesigned_error_rate <= 1:
            raise ValueError("error rates must be between 0 and 1")


@dataclass(frozen=True)
class RefoundingResult:
    annual_revenue: float
    baseline_labor_cost: float
    redesigned_labor_cost: float
    baseline_quality_loss: float
    redesigned_quality_loss: float
    baseline_contribution: float
    redesigned_contribution: float
    baseline_contribution_margin: float
    redesigned_contribution_margin: float
    annual_value_created: float
    baseline_fte: float
    redesigned_fte: float
    capacity_multiplier_at_fixed_labor: float
    payback_months: float


def simulate_refounding(
    processes: Iterable[ProcessRedesign],
    *,
    implementation_cost: float,
    annual_platform_cost: float,
    annual_hours_per_fte: float = 1800.0,
) -> RefoundingResult:
    items = list(processes)
    if not items:
        raise ValueError("at least one process is required")
    if implementation_cost < 0 or annual_platform_cost < 0 or annual_hours_per_fte <= 0:
        raise ValueError("invalid refounding cost assumptions")
    revenue = sum(item.annual_volume * item.revenue_per_unit for item in items)
    variable_cost = sum(item.annual_volume * item.other_variable_cost_per_unit for item in items)
    baseline_hours = sum(item.annual_volume * item.baseline_minutes_per_unit / 60 for item in items)
    redesigned_hours = sum(item.annual_volume * item.redesigned_minutes_per_unit / 60 for item in items)
    baseline_labor = sum(
        item.annual_volume * item.baseline_minutes_per_unit / 60 * item.loaded_labor_cost_per_hour
        for item in items
    )
    redesigned_labor = sum(
        item.annual_volume * item.redesigned_minutes_per_unit / 60 * item.loaded_labor_cost_per_hour
        for item in items
    )
    baseline_quality = sum(
        item.annual_volume * item.baseline_error_rate * item.loss_per_error
        for item in items
    )
    redesigned_quality = sum(
        item.annual_volume * item.redesigned_error_rate * item.loss_per_error
        for item in items
    )
    baseline_contribution = revenue - variable_cost - baseline_labor - baseline_quality
    redesigned_contribution = revenue - variable_cost - redesigned_labor - redesigned_quality - annual_platform_cost
    annual_value = redesigned_contribution - baseline_contribution
    capacity_multiplier = baseline_hours / redesigned_hours if redesigned_hours else float("inf")
    payback = 12 * implementation_cost / annual_value if annual_value > 0 else float("inf")
    return RefoundingResult(
        revenue,
        baseline_labor,
        redesigned_labor,
        baseline_quality,
        redesigned_quality,
        baseline_contribution,
        redesigned_contribution,
        baseline_contribution / revenue if revenue else 0.0,
        redesigned_contribution / revenue if revenue else 0.0,
        annual_value,
        baseline_hours / annual_hours_per_fte,
        redesigned_hours / annual_hours_per_fte,
        capacity_multiplier,
        payback,
    )
