"""Skills-first talent, customer-service, and retention kernels."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import median
from typing import Iterable, Mapping


@dataclass(frozen=True)
class RoleProfile:
    role_id: str
    skill_weights: Mapping[str, float]
    minimum_levels: Mapping[str, float]
    minimum_evidence_count: int = 1


@dataclass(frozen=True)
class CandidateProfile:
    candidate_id: str
    skill_levels: Mapping[str, float]
    evidence_counts: Mapping[str, int]
    availability: float = 1.0
    internal: bool = False


@dataclass(frozen=True)
class CandidateScore:
    candidate_id: str
    score: float
    eligible: bool
    skill_coverage: float
    evidence_coverage: float
    missing_skills: tuple[str, ...]


def rank_candidates(role: RoleProfile, candidates: Iterable[CandidateProfile]) -> tuple[CandidateScore, ...]:
    if not role.skill_weights or any(weight < 0 for weight in role.skill_weights.values()):
        raise ValueError("role skill weights must be nonnegative and nonempty")
    total_weight = sum(role.skill_weights.values())
    if total_weight <= 0:
        raise ValueError("role skill weights must sum to a positive number")
    results: list[CandidateScore] = []
    for candidate in candidates:
        if not 0 <= candidate.availability <= 1:
            raise ValueError("candidate availability must be between 0 and 1")
        missing: list[str] = []
        weighted_skill = 0.0
        weighted_evidence = 0.0
        for skill, weight in role.skill_weights.items():
            level = candidate.skill_levels.get(skill, 0.0)
            if not 0 <= level <= 1:
                raise ValueError("skill levels must be between 0 and 1")
            minimum = role.minimum_levels.get(skill, 0.0)
            if level < minimum:
                missing.append(skill)
            weighted_skill += weight * level
            evidence_count = candidate.evidence_counts.get(skill, 0)
            if evidence_count < 0:
                raise ValueError("evidence counts must be nonnegative")
            evidence_ratio = min(evidence_count / max(role.minimum_evidence_count, 1), 1.0)
            weighted_evidence += weight * evidence_ratio
        skill_coverage = weighted_skill / total_weight
        evidence_coverage = weighted_evidence / total_weight
        score = 100 * (0.65 * skill_coverage + 0.25 * evidence_coverage + 0.10 * candidate.availability)
        if candidate.internal:
            score = min(100.0, score + 3.0)
        eligible = not missing and evidence_coverage >= 0.5
        results.append(CandidateScore(
            candidate.candidate_id,
            score,
            eligible,
            skill_coverage,
            evidence_coverage,
            tuple(sorted(missing)),
        ))
    return tuple(sorted(results, key=lambda item: (-item.eligible, -item.score, item.candidate_id)))


@dataclass(frozen=True)
class HiringEvent:
    application_id: str
    applied_at: datetime
    first_human_at: datetime | None
    qualified: bool
    progressed: bool


def hiring_funnel(events: Iterable[HiringEvent], *, target_hours_to_human: float = 24.0) -> Mapping[str, float]:
    items = list(events)
    durations = []
    within_target = 0
    for item in items:
        if item.first_human_at is None:
            continue
        hours = (item.first_human_at - item.applied_at).total_seconds() / 3600
        if hours < 0:
            raise ValueError("first_human_at cannot precede applied_at")
        durations.append(hours)
        within_target += hours <= target_hours_to_human
    qualified = sum(item.qualified for item in items)
    progressed = sum(item.progressed for item in items)
    return {
        "applications": float(len(items)),
        "human_contact_coverage": len(durations) / len(items) if items else 0.0,
        "median_hours_to_human": median(durations) if durations else 0.0,
        "target_attainment": within_target / len(items) if items else 0.0,
        "qualification_rate": qualified / len(items) if items else 0.0,
        "qualified_progression_rate": progressed / qualified if qualified else 0.0,
    }


@dataclass(frozen=True)
class ServiceCase:
    case_id: str
    severity: int
    customer_value: float
    age_hours: float
    compliance_sensitive: bool = False
    repeat_contact: bool = False


@dataclass(frozen=True)
class CasePriority:
    case_id: str
    score: float
    sla_hours: float
    escalation_required: bool


def prioritize_service_cases(cases: Iterable[ServiceCase]) -> tuple[CasePriority, ...]:
    results = []
    for case in cases:
        if case.severity not in {1, 2, 3, 4}:
            raise ValueError("severity must be 1 through 4")
        if not 0 <= case.customer_value <= 1 or case.age_hours < 0:
            raise ValueError("invalid service-case inputs")
        score = 25 * case.severity + 20 * case.customer_value + min(case.age_hours, 72) / 4
        score += 20 if case.compliance_sensitive else 0
        score += 10 if case.repeat_contact else 0
        sla = {4: 1.0, 3: 4.0, 2: 24.0, 1: 72.0}[case.severity]
        escalation = case.compliance_sensitive or case.severity == 4 or case.age_hours > sla
        results.append(CasePriority(case.case_id, score, sla, escalation))
    return tuple(sorted(results, key=lambda item: (-item.score, item.case_id)))


@dataclass(frozen=True)
class CustomerHealth:
    customer_id: str
    usage_ratio: float
    support_burden: float
    payment_delay_ratio: float
    sponsor_engagement: float
    renewal_days: int


@dataclass(frozen=True)
class HealthScore:
    customer_id: str
    health_score: float
    churn_risk: float
    intervention_required: bool
    drivers: Mapping[str, float]


def score_customer_health(accounts: Iterable[CustomerHealth]) -> tuple[HealthScore, ...]:
    results = []
    for account in accounts:
        values = (
            account.usage_ratio, account.support_burden,
            account.payment_delay_ratio, account.sponsor_engagement,
        )
        if any(not 0 <= value <= 1 for value in values) or account.renewal_days < 0:
            raise ValueError("customer-health ratios must be between 0 and 1")
        risks = {
            "low_usage": 1 - account.usage_ratio,
            "support_burden": account.support_burden,
            "payment_delay": account.payment_delay_ratio,
            "low_sponsor_engagement": 1 - account.sponsor_engagement,
            "renewal_proximity": max(0.0, 1 - account.renewal_days / 180),
        }
        churn = (
            0.30 * risks["low_usage"]
            + 0.20 * risks["support_burden"]
            + 0.15 * risks["payment_delay"]
            + 0.20 * risks["low_sponsor_engagement"]
            + 0.15 * risks["renewal_proximity"]
        )
        results.append(HealthScore(
            account.customer_id,
            100 * (1 - churn),
            churn,
            churn >= 0.45,
            risks,
        ))
    return tuple(sorted(results, key=lambda item: (-item.churn_risk, item.customer_id)))
