"""Typed contracts for the Finance-Segway consulting operating system.

The consulting layer models decisions and controls, not vendor integrations.
All core records are dependency-free and serializable so the same contracts can
later back Excel, a CLI, a service, or a Zig implementation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from math import isfinite
from typing import Any, Mapping


class BusinessFunction(StrEnum):
    ENGINEERING = "engineering"
    DATA = "data_analytics"
    KNOWLEDGE = "knowledge_meetings"
    MARKETING = "marketing_geo"
    SALES = "sales_pricing"
    CUSTOMER = "customer_service_success"
    FINANCE = "finance_treasury"
    PROCUREMENT = "procurement"
    PEOPLE = "people_talent"
    OPERATIONS = "operations_delivery"
    QUALITY = "quality_compliance"
    LEGAL = "legal_contracts"
    IT_SECURITY = "it_security"
    CREATIVE = "creative_production"


class RiskTier(IntEnum):
    LOW = 1
    MODERATE = 2
    HIGH = 3
    CRITICAL = 4


class AutonomyLevel(IntEnum):
    ANALYZE = 0
    DRAFT = 1
    EXECUTE_REVERSIBLE = 2
    EXECUTE_MATERIAL = 3


class Direction(StrEnum):
    HIGHER = "higher_is_better"
    LOWER = "lower_is_better"
    RANGE = "target_range"


def _probability(name: str, value: float) -> float:
    result = float(value)
    if not isfinite(result) or not 0 <= result <= 1:
        raise ValueError(f"{name} must be between 0 and 1")
    return result


def _nonnegative(name: str, value: float) -> float:
    result = float(value)
    if not isfinite(result) or result < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return result


@dataclass(frozen=True)
class EvidenceRef:
    evidence_id: str
    source: str
    as_of: str
    checksum: str = ""
    confidence: float = 1.0
    restrictions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.source or not self.as_of:
            raise ValueError("evidence_id, source, and as_of are required")
        _probability("confidence", self.confidence)


@dataclass(frozen=True)
class MetricDefinition:
    metric_id: str
    function: BusinessFunction
    name: str
    unit: str
    owner: str
    direction: Direction
    target: float
    lower_bound: float | None = None
    upper_bound: float | None = None
    formula: str = ""

    def __post_init__(self) -> None:
        if not self.metric_id or not self.name or not self.owner:
            raise ValueError("metric_id, name, and owner are required")
        if not isfinite(float(self.target)):
            raise ValueError("target must be finite")
        if self.direction is Direction.RANGE:
            if self.lower_bound is None or self.upper_bound is None:
                raise ValueError("range metrics require lower and upper bounds")
            if self.lower_bound > self.upper_bound:
                raise ValueError("lower_bound cannot exceed upper_bound")


@dataclass(frozen=True)
class MetricObservation:
    metric_id: str
    value: float
    as_of: str
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.metric_id or not self.as_of:
            raise ValueError("metric_id and as_of are required")
        if not isfinite(float(self.value)):
            raise ValueError("metric value must be finite")


@dataclass(frozen=True)
class DiagnosticQuestion:
    question_id: str
    function: BusinessFunction
    executive_owner: str
    question: str
    metric_ids: tuple[str, ...]
    required_evidence: tuple[str, ...]
    risk_tier: RiskTier = RiskTier.MODERATE

    def __post_init__(self) -> None:
        if not self.question_id or not self.executive_owner or not self.question:
            raise ValueError("question_id, executive_owner, and question are required")
        if not self.metric_ids:
            raise ValueError("a diagnostic question requires at least one metric")


@dataclass(frozen=True)
class Activity:
    activity_id: str
    name: str
    function: BusinessFunction
    pnl_driver: str
    predecessors: tuple[str, ...] = ()
    annual_volume: float = 0.0
    capacity_units: float = 0.0
    minutes_per_unit: float = 0.0
    loaded_cost_per_hour: float = 0.0
    contribution_per_unit: float = 0.0
    error_rate: float = 0.0
    cost_per_error: float = 0.0

    def __post_init__(self) -> None:
        if not self.activity_id or not self.name or not self.pnl_driver:
            raise ValueError("activity_id, name, and pnl_driver are required")
        for name in (
            "annual_volume", "capacity_units", "minutes_per_unit",
            "loaded_cost_per_hour", "contribution_per_unit", "cost_per_error",
        ):
            _nonnegative(name, getattr(self, name))
        _probability("error_rate", self.error_rate)


@dataclass(frozen=True)
class AutomationCase:
    case_id: str
    activity_id: str
    function: BusinessFunction
    implementation_cost: float
    recurring_annual_cost: float
    annual_labor_savings: float = 0.0
    annual_revenue_gain: float = 0.0
    annual_loss_avoided: float = 0.0
    working_capital_release: float = 0.0
    feasibility: float = 1.0
    adoption_probability: float = 1.0
    evidence_confidence: float = 1.0
    delivery_months: float = 1.0
    risk_tier: RiskTier = RiskTier.MODERATE
    dependencies: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.case_id or not self.activity_id:
            raise ValueError("case_id and activity_id are required")
        for name in (
            "implementation_cost", "recurring_annual_cost",
            "annual_labor_savings", "annual_revenue_gain",
            "annual_loss_avoided", "working_capital_release", "delivery_months",
        ):
            _nonnegative(name, getattr(self, name))
        for name in ("feasibility", "adoption_probability", "evidence_confidence"):
            _probability(name, getattr(self, name))
        if self.delivery_months == 0:
            raise ValueError("delivery_months must be positive")


@dataclass(frozen=True)
class AgentSpec:
    agent_id: str
    function: BusinessFunction
    purpose: str
    skills: frozenset[str]
    autonomy: AutonomyLevel
    allowed_read_scopes: frozenset[str]
    allowed_write_scopes: frozenset[str] = field(default_factory=frozenset)
    required_evidence: frozenset[str] = field(default_factory=frozenset)
    success_metrics: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.agent_id or not self.purpose:
            raise ValueError("agent_id and purpose are required")
        if not self.skills:
            raise ValueError("an agent requires at least one skill")


@dataclass(frozen=True)
class DecisionRecord:
    decision_id: str
    decision_type: str
    recommendation: str
    rationale: tuple[str, ...]
    metric_values: Mapping[str, float]
    evidence_ids: tuple[str, ...]
    owner: str
    risk_tier: RiskTier
    limitations: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.decision_id or not self.decision_type or not self.owner:
            raise ValueError("decision_id, decision_type, and owner are required")
        if not self.recommendation:
            raise ValueError("recommendation is required")
