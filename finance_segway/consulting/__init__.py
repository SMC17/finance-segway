"""Governed, hand-rolled consulting and enterprise decision engines."""

from .evidence import EvidenceLedger, LedgerEntry, canonical_json, sha256_payload
from .diagnostics import DiagnosticEngine, MetricScore, QuestionScore
from .operating_model import (
    ActivityEconomics,
    InterventionEstimate,
    OperatingModel,
    canonical_value_chain,
)
from .portfolio import (
    CaseEconomics,
    PortfolioSelection,
    evaluate_case,
    realization_variance,
    select_portfolio,
)
from .runtime import AgentRuntime, ExecutionContext, ExecutionResult, Skill, SkillRegistry
from .refounding import ProcessRedesign, RefoundingResult, simulate_refounding
from .schema import (
    Activity,
    AgentSpec,
    AutomationCase,
    AutonomyLevel,
    BusinessFunction,
    DecisionRecord,
    DiagnosticQuestion,
    Direction,
    EvidenceRef,
    MetricDefinition,
    MetricObservation,
    RiskTier,
)

__all__ = [
    "Activity",
    "AgentRuntime",
    "AgentSpec",
    "AutomationCase",
    "AutonomyLevel",
    "BusinessFunction",
    "DecisionRecord",
    "DiagnosticEngine",
    "DiagnosticQuestion",
    "Direction",
    "EvidenceLedger",
    "EvidenceRef",
    "ExecutionContext",
    "ExecutionResult",
    "LedgerEntry",
    "MetricScore",
    "MetricDefinition",
    "MetricObservation",
    "RiskTier",
    "Skill",
    "SkillRegistry",
    "ActivityEconomics",
    "CaseEconomics",
    "InterventionEstimate",
    "OperatingModel",
    "PortfolioSelection",
    "ProcessRedesign",
    "QuestionScore",
    "RefoundingResult",
    "canonical_json",
    "canonical_value_chain",
    "evaluate_case",
    "realization_variance",
    "select_portfolio",
    "sha256_payload",
    "simulate_refounding",
]
