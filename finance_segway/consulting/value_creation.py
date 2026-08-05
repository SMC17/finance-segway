"""Portfolio-company value creation, 100-day sequencing, and exit bridges."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Mapping

from .evidence import sha256_payload


@dataclass(frozen=True)
class InitiativeImpact:
    initiative_id: str
    owner: str
    annual_revenue_uplift: float = 0.0
    incremental_gross_margin: float = 0.0
    annual_labor_savings: float = 0.0
    annual_other_savings: float = 0.0
    annual_recurring_cost: float = 0.0
    working_capital_release: float = 0.0
    one_time_cost: float = 0.0
    capex: float = 0.0
    realization_fraction_at_exit: float = 1.0
    dependencies: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.initiative_id or not self.owner or not self.evidence_ids:
            raise ValueError("initiative id, owner, and evidence are required")
        for name in (
            "annual_revenue_uplift", "annual_labor_savings", "annual_other_savings",
            "annual_recurring_cost", "working_capital_release", "one_time_cost", "capex",
        ):
            if not isfinite(getattr(self, name)) or getattr(self, name) < 0:
                raise ValueError(f"{name} must be nonnegative")
        if not isfinite(self.incremental_gross_margin) or not 0 <= self.incremental_gross_margin <= 1:
            raise ValueError("incremental_gross_margin must be between zero and one")
        if not isfinite(self.realization_fraction_at_exit) or not 0 <= self.realization_fraction_at_exit <= 1:
            raise ValueError("realization_fraction_at_exit must be between zero and one")

    @property
    def realized_ebitda_impact(self) -> float:
        gross_profit = self.annual_revenue_uplift * self.incremental_gross_margin
        gross_benefit = gross_profit + self.annual_labor_savings + self.annual_other_savings
        return gross_benefit * self.realization_fraction_at_exit - self.annual_recurring_cost

    @property
    def net_cash_release(self) -> float:
        return (
            self.working_capital_release * self.realization_fraction_at_exit
            - self.one_time_cost
            - self.capex
        )


@dataclass(frozen=True)
class InvestmentBaseline:
    entry_equity: float
    exit_years: float
    baseline_exit_ebitda: float
    baseline_exit_net_debt: float
    exit_multiple: float

    def __post_init__(self) -> None:
        if not all(isfinite(value) for value in (
            self.entry_equity, self.exit_years, self.baseline_exit_ebitda,
            self.baseline_exit_net_debt, self.exit_multiple,
        )):
            raise ValueError("investment baseline values must be finite")
        if self.entry_equity <= 0 or self.exit_years <= 0:
            raise ValueError("entry equity and exit years must be positive")
        if self.baseline_exit_ebitda < 0 or self.exit_multiple <= 0:
            raise ValueError("exit EBITDA must be nonnegative and multiple positive")


@dataclass(frozen=True)
class InitiativeContribution:
    initiative_id: str
    realized_ebitda_impact: float
    net_cash_release: float
    enterprise_value_impact: float
    equity_value_impact: float


@dataclass(frozen=True)
class PortfolioValueBridge:
    baseline_exit_ebitda: float
    value_plan_exit_ebitda: float
    ebitda_uplift: float
    baseline_exit_net_debt: float
    value_plan_exit_net_debt: float
    baseline_exit_enterprise_value: float
    value_plan_exit_enterprise_value: float
    baseline_exit_equity_value: float
    value_plan_exit_equity_value: float
    equity_value_uplift: float
    baseline_moic: float
    value_plan_moic: float
    moic_uplift: float
    baseline_irr: float
    value_plan_irr: float
    irr_uplift: float
    contributions: tuple[InitiativeContribution, ...]
    evidence_ids: tuple[str, ...]
    bridge_hash: str


def _irr(entry_equity: float, exit_equity: float, years: float) -> float:
    if exit_equity <= 0:
        return -1.0
    return (exit_equity / entry_equity) ** (1 / years) - 1


def _validate_dependencies(initiatives: Mapping[str, InitiativeImpact]) -> None:
    unknown = {
        dependency
        for item in initiatives.values()
        for dependency in item.dependencies
        if dependency not in initiatives
    }
    if unknown:
        raise ValueError(f"unknown initiative dependencies: {sorted(unknown)}")
    pending = set(initiatives)
    completed: set[str] = set()
    while pending:
        ready = {
            initiative_id for initiative_id in pending
            if set(initiatives[initiative_id].dependencies) <= completed
        }
        if not ready:
            raise ValueError("initiative dependencies contain a cycle")
        completed.update(ready)
        pending -= ready


def build_value_creation_bridge(
    baseline: InvestmentBaseline,
    initiatives: Iterable[InitiativeImpact],
) -> PortfolioValueBridge:
    items = list(initiatives)
    by_id = {item.initiative_id: item for item in items}
    if not items or len(by_id) != len(items):
        raise ValueError("initiatives must be nonempty and unique")
    _validate_dependencies(by_id)
    contributions = tuple(
        InitiativeContribution(
            initiative_id=item.initiative_id,
            realized_ebitda_impact=item.realized_ebitda_impact,
            net_cash_release=item.net_cash_release,
            enterprise_value_impact=item.realized_ebitda_impact * baseline.exit_multiple,
            equity_value_impact=(
                item.realized_ebitda_impact * baseline.exit_multiple + item.net_cash_release
            ),
        )
        for item in sorted(items, key=lambda value: value.initiative_id)
    )
    ebitda_uplift = sum(item.realized_ebitda_impact for item in contributions)
    net_cash_release = sum(item.net_cash_release for item in contributions)
    baseline_ev = baseline.baseline_exit_ebitda * baseline.exit_multiple
    plan_ebitda = baseline.baseline_exit_ebitda + ebitda_uplift
    plan_ev = plan_ebitda * baseline.exit_multiple
    plan_net_debt = baseline.baseline_exit_net_debt - net_cash_release
    baseline_equity = baseline_ev - baseline.baseline_exit_net_debt
    plan_equity = plan_ev - plan_net_debt
    baseline_moic = baseline_equity / baseline.entry_equity
    plan_moic = plan_equity / baseline.entry_equity
    baseline_irr = _irr(baseline.entry_equity, baseline_equity, baseline.exit_years)
    plan_irr = _irr(baseline.entry_equity, plan_equity, baseline.exit_years)
    evidence = tuple(sorted({evidence for item in items for evidence in item.evidence_ids}))
    body = {
        "baseline": baseline,
        "contributions": contributions,
        "plan_ebitda": plan_ebitda,
        "plan_net_debt": plan_net_debt,
        "plan_equity": plan_equity,
        "evidence_ids": evidence,
    }
    return PortfolioValueBridge(
        baseline_exit_ebitda=baseline.baseline_exit_ebitda,
        value_plan_exit_ebitda=plan_ebitda,
        ebitda_uplift=ebitda_uplift,
        baseline_exit_net_debt=baseline.baseline_exit_net_debt,
        value_plan_exit_net_debt=plan_net_debt,
        baseline_exit_enterprise_value=baseline_ev,
        value_plan_exit_enterprise_value=plan_ev,
        baseline_exit_equity_value=baseline_equity,
        value_plan_exit_equity_value=plan_equity,
        equity_value_uplift=plan_equity - baseline_equity,
        baseline_moic=baseline_moic,
        value_plan_moic=plan_moic,
        moic_uplift=plan_moic - baseline_moic,
        baseline_irr=baseline_irr,
        value_plan_irr=plan_irr,
        irr_uplift=plan_irr - baseline_irr,
        contributions=contributions,
        evidence_ids=evidence,
        bridge_hash=sha256_payload(body),
    )


@dataclass(frozen=True)
class Workstream:
    workstream_id: str
    initiative_id: str
    owner: str
    duration_days: int
    dependencies: tuple[str, ...] = ()
    earliest_start_day: int = 0
    decision_gate: str = ""
    required_evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.workstream_id or not self.initiative_id or not self.owner:
            raise ValueError("workstream id, initiative, and owner are required")
        if self.duration_days <= 0 or self.earliest_start_day < 0:
            raise ValueError("workstream timing is invalid")
        if self.decision_gate and not self.required_evidence:
            raise ValueError("decision gates require declared evidence")


@dataclass(frozen=True)
class ScheduledWorkstream:
    workstream_id: str
    initiative_id: str
    owner: str
    start_day: int
    finish_day: int
    decision_gate: str
    required_evidence: tuple[str, ...]


@dataclass(frozen=True)
class HundredDayPlan:
    schedule: tuple[ScheduledWorkstream, ...]
    critical_path: tuple[str, ...]
    completion_day: int
    within_100_days: bool
    unresolved_gate_ids: tuple[str, ...]
    plan_hash: str


def schedule_100_day_plan(
    workstreams: Iterable[Workstream],
    *,
    available_evidence_ids: Iterable[str] = (),
) -> HundredDayPlan:
    items = list(workstreams)
    by_id = {item.workstream_id: item for item in items}
    if not items or len(by_id) != len(items):
        raise ValueError("workstreams must be nonempty and unique")
    unknown = {
        dependency
        for item in items
        for dependency in item.dependencies
        if dependency not in by_id
    }
    if unknown:
        raise ValueError(f"unknown workstream dependencies: {sorted(unknown)}")
    pending = set(by_id)
    finish: dict[str, int] = {}
    schedule: list[ScheduledWorkstream] = []
    while pending:
        ready = sorted(
            workstream_id for workstream_id in pending
            if set(by_id[workstream_id].dependencies) <= set(finish)
        )
        if not ready:
            raise ValueError("workstream dependencies contain a cycle")
        for workstream_id in ready:
            item = by_id[workstream_id]
            dependency_finish = max((finish[value] for value in item.dependencies), default=0)
            start = max(item.earliest_start_day, dependency_finish)
            finish[workstream_id] = start + item.duration_days
            schedule.append(ScheduledWorkstream(
                item.workstream_id,
                item.initiative_id,
                item.owner,
                start,
                finish[workstream_id],
                item.decision_gate,
                item.required_evidence,
            ))
            pending.remove(workstream_id)
    completion_day = max(finish.values())
    endpoint = min(
        (item for item in schedule if item.finish_day == completion_day),
        key=lambda item: item.workstream_id,
    ).workstream_id
    critical = [endpoint]
    while by_id[endpoint].dependencies:
        endpoint = max(
            by_id[endpoint].dependencies,
            key=lambda dependency: (finish[dependency], dependency),
        )
        critical.append(endpoint)
    critical.reverse()
    available = set(available_evidence_ids)
    unresolved = tuple(sorted(
        item.workstream_id for item in items
        if item.decision_gate and not set(item.required_evidence) <= available
    ))
    body = {
        "schedule": schedule,
        "critical_path": critical,
        "completion_day": completion_day,
        "unresolved_gate_ids": unresolved,
    }
    return HundredDayPlan(
        tuple(schedule),
        tuple(critical),
        completion_day,
        completion_day <= 100,
        unresolved,
        sha256_payload(body),
    )
