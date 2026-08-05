"""Frozen baselines, guarded outcome measurement, and explicit attribution.

The module separates arithmetic from causal claims.  Difference-in-differences
is reported as a controlled estimate only when the caller documents and accepts
the design assumptions; otherwise it remains a descriptive comparison.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from math import isfinite, sqrt
from statistics import mean, variance
from typing import Iterable, Mapping

from .evidence import sha256_payload


class OutcomePeriod(StrEnum):
    BASELINE = "baseline"
    OUTCOME = "outcome"


class GuardrailOperator(StrEnum):
    GTE = "gte"
    LTE = "lte"


@dataclass(frozen=True)
class OutcomeObservation:
    unit_id: str
    period: OutcomePeriod
    treated: bool
    value: float
    evidence_id: str

    def __post_init__(self) -> None:
        if not self.unit_id or not self.evidence_id:
            raise ValueError("unit_id and evidence_id are required")
        if not isfinite(self.value):
            raise ValueError("outcome values must be finite")


@dataclass(frozen=True)
class AttributionResult:
    treated_baseline_mean: float
    treated_outcome_mean: float
    control_baseline_mean: float
    control_outcome_mean: float
    treated_change: float
    control_change: float
    difference_in_differences: float
    standard_error: float
    confidence_interval_95: tuple[float, float]
    cell_counts: Mapping[str, int]
    interpretation: str
    identification_assumptions: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    result_hash: str


def difference_in_differences(
    observations: Iterable[OutcomeObservation],
    *,
    design_validated: bool = False,
    identification_assumptions: Iterable[str] = (),
) -> AttributionResult:
    items = list(observations)
    assumptions = tuple(identification_assumptions)
    if design_validated and not assumptions:
        raise ValueError("validated designs require documented identification assumptions")
    cells = {
        "treated_baseline": [
            item.value for item in items
            if item.treated and item.period is OutcomePeriod.BASELINE
        ],
        "treated_outcome": [
            item.value for item in items
            if item.treated and item.period is OutcomePeriod.OUTCOME
        ],
        "control_baseline": [
            item.value for item in items
            if not item.treated and item.period is OutcomePeriod.BASELINE
        ],
        "control_outcome": [
            item.value for item in items
            if not item.treated and item.period is OutcomePeriod.OUTCOME
        ],
    }
    missing = [name for name, values in cells.items() if not values]
    if missing:
        raise ValueError(f"difference-in-differences requires all four cells: {missing}")
    means = {name: mean(values) for name, values in cells.items()}
    treated_change = means["treated_outcome"] - means["treated_baseline"]
    control_change = means["control_outcome"] - means["control_baseline"]
    estimate = treated_change - control_change
    sampling_variance = sum(
        variance(values) / len(values) if len(values) > 1 else 0.0
        for values in cells.values()
    )
    standard_error = sqrt(sampling_variance)
    interval = (estimate - 1.96 * standard_error, estimate + 1.96 * standard_error)
    evidence_ids = tuple(sorted({item.evidence_id for item in items}))
    interpretation = (
        "controlled_estimate_subject_to_documented_assumptions"
        if design_validated
        else "descriptive_comparison_not_a_causal_claim"
    )
    body = {
        "means": means,
        "treated_change": treated_change,
        "control_change": control_change,
        "estimate": estimate,
        "standard_error": standard_error,
        "cell_counts": {name: len(values) for name, values in cells.items()},
        "interpretation": interpretation,
        "assumptions": assumptions,
        "evidence_ids": evidence_ids,
    }
    return AttributionResult(
        treated_baseline_mean=means["treated_baseline"],
        treated_outcome_mean=means["treated_outcome"],
        control_baseline_mean=means["control_baseline"],
        control_outcome_mean=means["control_outcome"],
        treated_change=treated_change,
        control_change=control_change,
        difference_in_differences=estimate,
        standard_error=standard_error,
        confidence_interval_95=interval,
        cell_counts={name: len(values) for name, values in cells.items()},
        interpretation=interpretation,
        identification_assumptions=assumptions,
        evidence_ids=evidence_ids,
        result_hash=sha256_payload(body),
    )


@dataclass(frozen=True)
class Guardrail:
    metric_id: str
    operator: GuardrailOperator
    threshold: float

    def __post_init__(self) -> None:
        if not self.metric_id:
            raise ValueError("guardrail metric_id is required")
        if not isfinite(self.threshold):
            raise ValueError("guardrail threshold must be finite")


@dataclass(frozen=True)
class RealizationPlan:
    plan_id: str
    metric_id: str
    owner: str
    baseline: float
    target: float
    higher_is_better: bool
    frozen_at: datetime
    measurement_due_at: datetime
    baseline_evidence_ids: tuple[str, ...]
    guardrails: tuple[Guardrail, ...] = ()
    attribution_method: str = "pre_post"
    assumptions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.plan_id or not self.metric_id or not self.owner:
            raise ValueError("plan_id, metric_id, and owner are required")
        if not isfinite(self.baseline) or not isfinite(self.target):
            raise ValueError("baseline and target must be finite")
        if self.frozen_at.tzinfo is None or self.measurement_due_at.tzinfo is None:
            raise ValueError("realization plan timestamps must be timezone-aware")
        if self.measurement_due_at <= self.frozen_at:
            raise ValueError("measurement must be due after the baseline is frozen")
        if not self.baseline_evidence_ids:
            raise ValueError("a frozen baseline requires evidence")
        planned_change = self.target - self.baseline
        if self.higher_is_better and planned_change <= 0:
            raise ValueError("higher-is-better target must exceed baseline")
        if not self.higher_is_better and planned_change >= 0:
            raise ValueError("lower-is-better target must be below baseline")


@dataclass(frozen=True)
class RealizationMeasurement:
    plan_id: str
    as_of: datetime
    actual: float
    planned_improvement: float
    actual_improvement: float
    realization_rate: float
    status: str
    guardrail_breaches: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    measurement_hash: str


def measure_realization(
    plan: RealizationPlan,
    *,
    actual: float,
    as_of: datetime,
    evidence_ids: Iterable[str],
    guardrail_values: Mapping[str, float] | None = None,
) -> RealizationMeasurement:
    if as_of.tzinfo is None:
        raise ValueError("measurement time must be timezone-aware")
    if not isfinite(actual):
        raise ValueError("actual outcome must be finite")
    evidence = tuple(sorted(set(evidence_ids)))
    if not evidence:
        raise ValueError("outcome measurement requires evidence")
    direction = 1 if plan.higher_is_better else -1
    planned_improvement = (plan.target - plan.baseline) * direction
    actual_improvement = (actual - plan.baseline) * direction
    realization_rate = actual_improvement / planned_improvement
    breaches: list[str] = []
    observed_guardrails = guardrail_values or {}
    for guardrail in plan.guardrails:
        if guardrail.metric_id not in observed_guardrails:
            breaches.append(f"missing_guardrail:{guardrail.metric_id}")
            continue
        value = observed_guardrails[guardrail.metric_id]
        if guardrail.operator is GuardrailOperator.GTE and value < guardrail.threshold:
            breaches.append(f"guardrail_breach:{guardrail.metric_id}")
        if guardrail.operator is GuardrailOperator.LTE and value > guardrail.threshold:
            breaches.append(f"guardrail_breach:{guardrail.metric_id}")
    if breaches:
        status = "guardrail_breached"
    elif realization_rate >= 1:
        status = "target_met"
    elif actual_improvement <= 0:
        status = "no_realized_improvement"
    elif as_of >= plan.measurement_due_at:
        status = "target_missed"
    else:
        status = "in_progress"
    body = {
        "plan_id": plan.plan_id,
        "as_of": as_of,
        "actual": actual,
        "planned_improvement": planned_improvement,
        "actual_improvement": actual_improvement,
        "realization_rate": realization_rate,
        "status": status,
        "guardrail_breaches": breaches,
        "evidence_ids": evidence,
    }
    return RealizationMeasurement(
        plan.plan_id,
        as_of,
        actual,
        planned_improvement,
        actual_improvement,
        realization_rate,
        status,
        tuple(breaches),
        evidence,
        sha256_payload(body),
    )


@dataclass(frozen=True)
class DriverOutcome:
    driver_id: str
    planned_value: float
    actual_value: float
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.driver_id or not self.evidence_ids:
            raise ValueError("driver outcomes require an id and evidence")


@dataclass(frozen=True)
class RealizationBridge:
    planned_total: float
    actual_total: float
    variance: float
    by_driver: Mapping[str, float]
    evidence_ids: tuple[str, ...]
    bridge_hash: str


def bridge_forecast_to_actual(outcomes: Iterable[DriverOutcome]) -> RealizationBridge:
    items = list(outcomes)
    ids = [item.driver_id for item in items]
    if not items or len(ids) != len(set(ids)):
        raise ValueError("driver outcomes must be nonempty and unique")
    planned = sum(item.planned_value for item in items)
    actual = sum(item.actual_value for item in items)
    by_driver = {item.driver_id: item.actual_value - item.planned_value for item in items}
    evidence = tuple(sorted({evidence for item in items for evidence in item.evidence_ids}))
    body = {
        "planned_total": planned,
        "actual_total": actual,
        "by_driver": by_driver,
        "evidence_ids": evidence,
    }
    return RealizationBridge(
        planned, actual, actual - planned, by_driver, evidence, sha256_payload(body),
    )
