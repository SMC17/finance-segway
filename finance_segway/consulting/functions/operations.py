"""Demand, capacity, dispatch, and quality-control kernels."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


def demand_forecast(
    history: Sequence[float],
    *,
    horizon: int,
    window: int = 3,
    season_length: int | None = None,
) -> tuple[float, ...]:
    if not history or horizon <= 0 or window <= 0:
        raise ValueError("history, positive horizon, and positive window are required")
    if any(value < 0 for value in history):
        raise ValueError("demand history must be nonnegative")
    if season_length is not None:
        if season_length <= 0 or len(history) < season_length:
            raise ValueError("season_length requires a complete historical season")
        season = list(history[-season_length:])
        return tuple(season[index % season_length] for index in range(horizon))
    values = list(history)
    forecast = []
    for _ in range(horizon):
        prediction = sum(values[-window:]) / min(window, len(values))
        forecast.append(prediction)
        values.append(prediction)
    return tuple(forecast)


@dataclass(frozen=True)
class CapacityPeriod:
    label: str
    demand_units: float
    capacity_units: float
    contribution_per_unit: float = 0.0


def capacity_plan(periods: Iterable[CapacityPeriod]) -> tuple[Mapping[str, float | str], ...]:
    results = []
    for period in periods:
        if period.demand_units < 0 or period.capacity_units < 0 or period.contribution_per_unit < 0:
            raise ValueError("capacity-plan inputs must be nonnegative")
        shortfall = max(period.demand_units - period.capacity_units, 0.0)
        utilization = period.demand_units / period.capacity_units if period.capacity_units else float("inf")
        results.append({
            "label": period.label,
            "demand_units": period.demand_units,
            "capacity_units": period.capacity_units,
            "shortfall_units": shortfall,
            "utilization": utilization,
            "contribution_at_risk": shortfall * period.contribution_per_unit,
        })
    return tuple(results)


@dataclass(frozen=True)
class Worker:
    worker_id: str
    skills: frozenset[str]
    available_hours: float


@dataclass(frozen=True)
class WorkOrder:
    order_id: str
    required_skills: frozenset[str]
    duration_hours: float
    priority: int
    contribution: float = 0.0


@dataclass(frozen=True)
class DispatchResult:
    assignments: Mapping[str, str]
    remaining_hours: Mapping[str, float]
    unassigned_order_ids: tuple[str, ...]
    scheduled_contribution: float


def dispatch_work(workers: Iterable[Worker], orders: Iterable[WorkOrder]) -> DispatchResult:
    worker_items = {worker.worker_id: worker for worker in workers}
    remaining = {worker.worker_id: worker.available_hours for worker in worker_items.values()}
    if any(hours < 0 for hours in remaining.values()):
        raise ValueError("worker availability must be nonnegative")
    assignments: dict[str, str] = {}
    unassigned: list[str] = []
    contribution = 0.0
    sorted_orders = sorted(orders, key=lambda item: (-item.priority, -item.contribution, item.order_id))
    for order in sorted_orders:
        if order.duration_hours <= 0 or order.contribution < 0:
            raise ValueError("work-order duration must be positive and contribution nonnegative")
        eligible = [
            worker for worker in worker_items.values()
            if order.required_skills.issubset(worker.skills)
            and remaining[worker.worker_id] >= order.duration_hours
        ]
        if not eligible:
            unassigned.append(order.order_id)
            continue
        selected = min(
            eligible,
            key=lambda worker: (
                len(worker.skills - order.required_skills),
                -remaining[worker.worker_id],
                worker.worker_id,
            ),
        )
        assignments[order.order_id] = selected.worker_id
        remaining[selected.worker_id] -= order.duration_hours
        contribution += order.contribution
    return DispatchResult(assignments, remaining, tuple(sorted(unassigned)), contribution)


@dataclass(frozen=True)
class QualityBatch:
    batch_id: str
    units: int
    defects: int
    reworked: int = 0
    compliance_failures: int = 0


def quality_metrics(batches: Iterable[QualityBatch]) -> Mapping[str, float]:
    items = list(batches)
    if any(
        item.units < 0 or item.defects < 0 or item.reworked < 0
        or item.compliance_failures < 0 or item.defects > item.units
        for item in items
    ):
        raise ValueError("invalid quality batch")
    units = sum(item.units for item in items)
    defects = sum(item.defects for item in items)
    reworked = sum(item.reworked for item in items)
    compliance = sum(item.compliance_failures for item in items)
    return {
        "units": float(units),
        "first_pass_yield": (units - defects) / units if units else 0.0,
        "defect_rate": defects / units if units else 0.0,
        "rework_rate": reworked / units if units else 0.0,
        "compliance_failure_rate": compliance / units if units else 0.0,
    }
