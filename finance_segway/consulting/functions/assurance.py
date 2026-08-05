"""Engineering, legal, IT/security, and creative-control kernels."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from ..schema import RiskTier


@dataclass(frozen=True)
class EngineeringTask:
    task_id: str
    repetitive: bool
    tests_available: bool
    production_write: bool
    handles_sensitive_data: bool
    reversible: bool
    risk_tier: RiskTier


@dataclass(frozen=True)
class DelegationDecision:
    task_id: str
    mode: str
    required_controls: tuple[str, ...]
    rationale: tuple[str, ...]


def delegate_engineering_task(task: EngineeringTask) -> DelegationDecision:
    controls = ["diff_review", "test_execution", "execution_receipt"]
    rationale = []
    if task.handles_sensitive_data:
        controls.extend(["data_scope_enforcement", "secret_scan"])
        rationale.append("sensitive_data")
    if task.production_write:
        controls.extend(["named_approval", "rollback_plan"])
        rationale.append("production_write")
    if task.risk_tier >= RiskTier.HIGH:
        controls.extend(["independent_review", "change_window"])
        rationale.append("high_risk")
    if not task.tests_available:
        controls.append("tests_required_before_execution")
        rationale.append("missing_tests")
    if not task.reversible:
        controls.append("human_execution")
        rationale.append("irreversible")

    if task.risk_tier >= RiskTier.HIGH or not task.reversible or task.handles_sensitive_data:
        mode = "human_led"
    elif task.repetitive and task.tests_available and not task.production_write:
        mode = "autonomous_reversible"
    else:
        mode = "agent_draft_human_execute"
    return DelegationDecision(task.task_id, mode, tuple(sorted(set(controls))), tuple(rationale))


def engineering_productivity(
    *,
    baseline_completed: int,
    current_completed: int,
    baseline_engineer_hours: float,
    current_engineer_hours: float,
    assisted_tasks: int,
) -> Mapping[str, float]:
    values = (baseline_completed, current_completed, baseline_engineer_hours, current_engineer_hours, assisted_tasks)
    if any(value < 0 for value in values):
        raise ValueError("engineering metrics must be nonnegative")
    baseline_rate = baseline_completed / baseline_engineer_hours if baseline_engineer_hours else 0.0
    current_rate = current_completed / current_engineer_hours if current_engineer_hours else 0.0
    return {
        "baseline_tasks_per_hour": baseline_rate,
        "current_tasks_per_hour": current_rate,
        "throughput_change": current_rate / baseline_rate - 1 if baseline_rate else 0.0,
        "assisted_task_share": assisted_tasks / current_completed if current_completed else 0.0,
    }


@dataclass(frozen=True)
class ContractRecord:
    contract_id: str
    clauses: frozenset[str]
    term_months: int
    auto_renewal: bool
    liability_cap_multiple: float
    governing_law: str


@dataclass(frozen=True)
class ContractPolicy:
    required_clauses: frozenset[str]
    forbidden_clauses: frozenset[str]
    maximum_term_months: int
    allow_auto_renewal: bool
    minimum_liability_cap_multiple: float
    allowed_governing_law: frozenset[str] = frozenset()


def audit_contract(contract: ContractRecord, policy: ContractPolicy) -> tuple[str, ...]:
    if contract.term_months <= 0 or contract.liability_cap_multiple < 0:
        raise ValueError("invalid contract economics")
    exceptions = [
        f"missing_clause:{clause}"
        for clause in sorted(policy.required_clauses - contract.clauses)
    ]
    exceptions.extend(
        f"forbidden_clause:{clause}"
        for clause in sorted(policy.forbidden_clauses.intersection(contract.clauses))
    )
    if contract.term_months > policy.maximum_term_months:
        exceptions.append("term_above_policy")
    if contract.auto_renewal and not policy.allow_auto_renewal:
        exceptions.append("auto_renewal_not_allowed")
    if contract.liability_cap_multiple < policy.minimum_liability_cap_multiple:
        exceptions.append("liability_cap_below_policy")
    if policy.allowed_governing_law and contract.governing_law not in policy.allowed_governing_law:
        exceptions.append("governing_law_exception")
    return tuple(exceptions)


@dataclass(frozen=True)
class ServiceTicket:
    ticket_id: str
    category: str
    impact: int
    urgency: int
    security_related: bool = False
    executive_impact: bool = False


@dataclass(frozen=True)
class TicketRoute:
    ticket_id: str
    queue: str
    priority: int
    sla_hours: float
    human_required: bool


def route_it_ticket(ticket: ServiceTicket, routing: Mapping[str, str]) -> TicketRoute:
    if ticket.impact not in {1, 2, 3, 4} or ticket.urgency not in {1, 2, 3, 4}:
        raise ValueError("impact and urgency must be 1 through 4")
    queue = "security" if ticket.security_related else routing.get(ticket.category, "service_desk")
    priority = min(4, max(1, round((ticket.impact + ticket.urgency) / 2)))
    if ticket.security_related or ticket.executive_impact:
        priority = 4
    sla = {4: 1.0, 3: 4.0, 2: 16.0, 1: 48.0}[priority]
    human_required = ticket.security_related or priority >= 3
    return TicketRoute(ticket.ticket_id, queue, priority, sla, human_required)


@dataclass(frozen=True)
class AccessRequest:
    request_id: str
    role: str
    requested_permissions: frozenset[str]
    duration_days: int
    break_glass: bool = False


@dataclass(frozen=True)
class AccessDecision:
    request_id: str
    status: str
    granted_permissions: frozenset[str]
    exceptions: tuple[str, ...]


def decide_access(
    request: AccessRequest,
    role_permissions: Mapping[str, frozenset[str]],
    *,
    maximum_duration_days: int = 90,
) -> AccessDecision:
    if request.duration_days <= 0:
        raise ValueError("duration_days must be positive")
    allowed = role_permissions.get(request.role, frozenset())
    excess = request.requested_permissions - allowed
    exceptions = [f"permission_outside_role:{permission}" for permission in sorted(excess)]
    if request.duration_days > maximum_duration_days:
        exceptions.append("duration_above_policy")
    if request.break_glass:
        exceptions.append("break_glass_review")
    if request.role not in role_permissions:
        exceptions.append("unknown_role")
    if exceptions:
        status = "approval_required" if request.break_glass and request.role in role_permissions else "rejected"
    else:
        status = "approved"
    granted = request.requested_permissions if status == "approved" else frozenset()
    return AccessDecision(request.request_id, status, granted, tuple(exceptions))


@dataclass(frozen=True)
class CreativeBrief:
    brief_id: str
    audience: str
    objective: str
    channel: str
    claims: tuple[str, ...]
    sources: tuple[str, ...]
    external_facing: bool
    brand_risk: RiskTier
    cinematic_quality_required: bool = False


@dataclass(frozen=True)
class ProductionDecision:
    brief_id: str
    production_tier: str
    readiness_score: float
    required_reviews: tuple[str, ...]
    missing: tuple[str, ...]


def route_creative_brief(brief: CreativeBrief) -> ProductionDecision:
    fields = {
        "audience": bool(brief.audience.strip()),
        "objective": bool(brief.objective.strip()),
        "channel": bool(brief.channel.strip()),
        "claims": bool(brief.claims),
        "sources": bool(brief.sources),
    }
    missing = tuple(name for name, present in fields.items() if not present)
    readiness = 100 * sum(fields.values()) / len(fields)
    reviews = ["brand_review"]
    if brief.claims:
        reviews.append("claims_substantiation")
    if brief.external_facing:
        reviews.append("external_release_review")
    if brief.brand_risk >= RiskTier.HIGH:
        reviews.append("senior_creative_review")
    if brief.cinematic_quality_required or brief.brand_risk >= RiskTier.HIGH:
        tier = "human_origin"
    elif brief.external_facing:
        tier = "agent_assisted_human_finish"
    else:
        tier = "template_or_agent_native"
    if missing:
        tier = "blocked_incomplete_brief"
    return ProductionDecision(brief.brief_id, tier, readiness, tuple(sorted(set(reviews))), missing)
