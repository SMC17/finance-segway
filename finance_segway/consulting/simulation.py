"""Seeded uncertainty underwriting and a small service-process digital twin."""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil, inf, isfinite, sqrt
import random
from statistics import mean, median
from typing import Iterable, Mapping

from .evidence import sha256_payload


def _percentile(values: Iterable[float], probability: float) -> float:
    items = sorted(float(value) for value in values)
    if not items:
        return 0.0
    position = probability * (len(items) - 1)
    lower = int(position)
    upper = min(lower + 1, len(items) - 1)
    weight = position - lower
    return items[lower] * (1 - weight) + items[upper] * weight


@dataclass(frozen=True)
class TriangularDistribution:
    low: float
    mode: float
    high: float

    def __post_init__(self) -> None:
        if not all(isfinite(value) for value in (self.low, self.mode, self.high)):
            raise ValueError("triangular inputs must be finite")
        if not self.low <= self.mode <= self.high:
            raise ValueError("triangular inputs require low <= mode <= high")

    def sample(self, generator: random.Random) -> float:
        if self.low == self.high:
            return float(self.low)
        return generator.triangular(self.low, self.high, self.mode)


@dataclass(frozen=True)
class InitiativeSimulation:
    simulation_id: str
    implementation_cost: TriangularDistribution
    annual_gross_value: TriangularDistribution
    annual_recurring_cost: TriangularDistribution
    adoption_fraction: TriangularDistribution
    delivery_months: TriangularDistribution
    working_capital_release: TriangularDistribution = TriangularDistribution(0, 0, 0)
    feasibility_probability: float = 1.0
    life_years: int = 3
    discount_rate: float = 0.12
    ramp_months: int = 6

    def __post_init__(self) -> None:
        if not self.simulation_id:
            raise ValueError("simulation_id is required")
        if self.implementation_cost.low < 0 or self.annual_gross_value.low < 0:
            raise ValueError("cost and value distributions must be nonnegative")
        if self.annual_recurring_cost.low < 0 or self.delivery_months.low < 0:
            raise ValueError("recurring cost and delivery distributions must be nonnegative")
        if self.working_capital_release.low < 0:
            raise ValueError("working-capital release must be nonnegative")
        if not 0 <= self.adoption_fraction.low <= self.adoption_fraction.high <= 1:
            raise ValueError("adoption fraction must remain between zero and one")
        if not 0 <= self.feasibility_probability <= 1:
            raise ValueError("feasibility_probability must be between zero and one")
        if self.life_years <= 0 or self.discount_rate < 0 or self.ramp_months < 0:
            raise ValueError("simulation horizon and rates are invalid")


@dataclass(frozen=True)
class MonteCarloResult:
    simulation_id: str
    iterations: int
    seed: int
    mean_npv: float
    median_npv: float
    downside_p05_npv: float
    upside_p95_npv: float
    expected_shortfall_p05: float
    probability_positive_npv: float
    probability_payback_within_horizon: float
    median_payback_months: float
    sensitivity: Mapping[str, float]
    sample_checksum: str


def _ranks(values: list[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda pair: pair[1])
    ranks = [0.0] * len(values)
    position = 0
    while position < len(ordered):
        end = position + 1
        while end < len(ordered) and ordered[end][1] == ordered[position][1]:
            end += 1
        average_rank = (position + 1 + end) / 2
        for index in range(position, end):
            ranks[ordered[index][0]] = average_rank
        position = end
    return ranks


def _correlation(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    left_mean = mean(left)
    right_mean = mean(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    left_scale = sum((x - left_mean) ** 2 for x in left)
    right_scale = sum((y - right_mean) ** 2 for y in right)
    denominator = sqrt(left_scale * right_scale)
    return numerator / denominator if denominator else 0.0


def simulate_initiative(
    case: InitiativeSimulation,
    *,
    iterations: int = 5_000,
    seed: int = 17,
) -> MonteCarloResult:
    if iterations < 100:
        raise ValueError("at least 100 iterations are required")
    generator = random.Random(seed)
    monthly_rate = (1 + case.discount_rate) ** (1 / 12) - 1
    horizon_months = case.life_years * 12
    npvs: list[float] = []
    paybacks: list[float] = []
    sampled: dict[str, list[float]] = {
        "implementation_cost": [],
        "annual_gross_value": [],
        "annual_recurring_cost": [],
        "adoption_fraction": [],
        "delivery_months": [],
        "working_capital_release": [],
        "feasible": [],
    }
    for _ in range(iterations):
        implementation_cost = case.implementation_cost.sample(generator)
        annual_gross_value = case.annual_gross_value.sample(generator)
        annual_recurring_cost = case.annual_recurring_cost.sample(generator)
        adoption = case.adoption_fraction.sample(generator)
        delivery = case.delivery_months.sample(generator)
        working_capital = case.working_capital_release.sample(generator)
        feasible = generator.random() <= case.feasibility_probability
        values = (
            implementation_cost,
            annual_gross_value,
            annual_recurring_cost,
            adoption,
            delivery,
            working_capital,
            float(feasible),
        )
        for name, value in zip(sampled, values):
            sampled[name].append(value)

        npv = -implementation_cost
        cumulative = -implementation_cost
        payback = inf
        go_live_month = max(ceil(delivery), 1)
        for month in range(1, horizon_months + 1):
            cash_flow = 0.0
            if feasible and month >= delivery:
                if month == go_live_month:
                    cash_flow += working_capital
                live_months = max(month - delivery, 0.0)
                ramp = 1.0 if case.ramp_months == 0 else min(live_months / case.ramp_months, 1.0)
                cash_flow += (annual_gross_value * adoption * ramp - annual_recurring_cost) / 12
            npv += cash_flow / ((1 + monthly_rate) ** month)
            cumulative += cash_flow
            if cumulative >= 0 and payback == inf:
                payback = float(month)
        npvs.append(npv)
        paybacks.append(payback)

    cutoff = max(int(iterations * 0.05), 1)
    finite_paybacks = [value for value in paybacks if value != inf]
    npv_ranks = _ranks(npvs)
    sensitivity = {
        name: _correlation(_ranks(values), npv_ranks)
        for name, values in sampled.items()
    }
    sensitivity = dict(sorted(sensitivity.items(), key=lambda item: (-abs(item[1]), item[0])))
    return MonteCarloResult(
        simulation_id=case.simulation_id,
        iterations=iterations,
        seed=seed,
        mean_npv=mean(npvs),
        median_npv=median(npvs),
        downside_p05_npv=_percentile(npvs, 0.05),
        upside_p95_npv=_percentile(npvs, 0.95),
        expected_shortfall_p05=mean(sorted(npvs)[:cutoff]),
        probability_positive_npv=sum(value > 0 for value in npvs) / iterations,
        probability_payback_within_horizon=len(finite_paybacks) / iterations,
        median_payback_months=median(finite_paybacks) if finite_paybacks else inf,
        sensitivity=sensitivity,
        sample_checksum=sha256_payload([round(value, 8) for value in npvs]),
    )


@dataclass(frozen=True)
class QueueStage:
    stage_id: str
    servers: int
    service_minutes: TriangularDistribution
    rework_probability: float = 0.0

    def __post_init__(self) -> None:
        if not self.stage_id or self.servers <= 0:
            raise ValueError("queue stages require an id and positive server count")
        if self.service_minutes.low < 0 or not 0 <= self.rework_probability <= 1:
            raise ValueError("service time and rework probability are invalid")


@dataclass(frozen=True)
class PipelineSimulationResult:
    item_count: int
    elapsed_minutes: float
    throughput_per_hour: float
    average_cycle_minutes: float
    p90_cycle_minutes: float
    total_rework_events: int
    average_wait_by_stage: Mapping[str, float]
    utilization_by_stage: Mapping[str, float]
    sample_checksum: str


def simulate_service_pipeline(
    stages: Iterable[QueueStage],
    *,
    item_count: int,
    interarrival_minutes: float,
    seed: int = 17,
) -> PipelineSimulationResult:
    stage_items = tuple(stages)
    if not stage_items or item_count <= 0 or interarrival_minutes < 0:
        raise ValueError("stages, positive item_count, and nonnegative interarrival time are required")
    ids = [stage.stage_id for stage in stage_items]
    if len(ids) != len(set(ids)):
        raise ValueError("queue stage ids must be unique")
    generator = random.Random(seed)
    availability = {stage.stage_id: [0.0] * stage.servers for stage in stage_items}
    waits = {stage.stage_id: [] for stage in stage_items}
    busy = {stage.stage_id: 0.0 for stage in stage_items}
    cycle_times: list[float] = []
    completions: list[float] = []
    rework_events = 0
    for item_index in range(item_count):
        arrival = item_index * interarrival_minutes
        current = arrival
        for stage in stage_items:
            passes = 2 if generator.random() < stage.rework_probability else 1
            rework_events += passes - 1
            for _ in range(passes):
                servers = availability[stage.stage_id]
                server_index = min(range(len(servers)), key=lambda index: (servers[index], index))
                start = max(current, servers[server_index])
                waits[stage.stage_id].append(start - current)
                service = stage.service_minutes.sample(generator)
                busy[stage.stage_id] += service
                current = start + service
                servers[server_index] = current
        completions.append(current)
        cycle_times.append(current - arrival)
    elapsed = max(completions) if completions else 0.0
    utilization = {
        stage.stage_id: min(
            busy[stage.stage_id] / (stage.servers * elapsed) if elapsed else 0.0,
            1.0,
        )
        for stage in stage_items
    }
    average_wait = {
        stage.stage_id: mean(waits[stage.stage_id]) if waits[stage.stage_id] else 0.0
        for stage in stage_items
    }
    return PipelineSimulationResult(
        item_count=item_count,
        elapsed_minutes=elapsed,
        throughput_per_hour=item_count / (elapsed / 60) if elapsed else 0.0,
        average_cycle_minutes=mean(cycle_times),
        p90_cycle_minutes=_percentile(cycle_times, 0.9),
        total_rework_events=rework_events,
        average_wait_by_stage=average_wait,
        utilization_by_stage=utilization,
        sample_checksum=sha256_payload([round(value, 8) for value in cycle_times]),
    )
