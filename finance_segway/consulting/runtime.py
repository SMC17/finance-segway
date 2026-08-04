"""A local, deterministic agent harness with controls and execution receipts."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from time import perf_counter
from typing import Any, Callable, Mapping

from .evidence import EvidenceLedger, sha256_payload
from .schema import AgentSpec, AutonomyLevel, RiskTier


SkillHandler = Callable[[Mapping[str, Any]], Mapping[str, Any]]


@dataclass(frozen=True)
class Skill:
    skill_id: str
    handler: SkillHandler
    risk_tier: RiskTier = RiskTier.LOW
    required_autonomy: AutonomyLevel = AutonomyLevel.ANALYZE
    required_evidence: frozenset[str] = field(default_factory=frozenset)
    read_scopes: frozenset[str] = field(default_factory=frozenset)
    write_scopes: frozenset[str] = field(default_factory=frozenset)
    idempotent: bool = True

    def __post_init__(self) -> None:
        if not self.skill_id:
            raise ValueError("skill_id is required")


@dataclass(frozen=True)
class ExecutionContext:
    actor: str
    evidence_ids: frozenset[str] = field(default_factory=frozenset)
    granted_read_scopes: frozenset[str] = field(default_factory=frozenset)
    granted_write_scopes: frozenset[str] = field(default_factory=frozenset)
    approved: bool = False
    approval_reference: str = ""
    timestamp: datetime | None = None


@dataclass(frozen=True)
class ExecutionResult:
    status: str
    output: Mapping[str, Any]
    receipt_hash: str
    reasons: tuple[str, ...] = ()
    cached: bool = False


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        if skill.skill_id in self._skills:
            raise ValueError(f"duplicate skill: {skill.skill_id}")
        self._skills[skill.skill_id] = skill

    def get(self, skill_id: str) -> Skill:
        try:
            return self._skills[skill_id]
        except KeyError as exc:
            raise KeyError(f"unknown skill: {skill_id}") from exc

    @property
    def skill_ids(self) -> frozenset[str]:
        return frozenset(self._skills)


class AgentRuntime:
    """Executes pure skills while enforcing declared access and approvals."""

    def __init__(self, registry: SkillRegistry, ledger: EvidenceLedger | None = None) -> None:
        self.registry = registry
        self.ledger = ledger or EvidenceLedger()
        self._cache: dict[str, ExecutionResult] = {}

    def _reasons(
        self,
        agent: AgentSpec,
        skill: Skill,
        context: ExecutionContext,
    ) -> list[str]:
        reasons: list[str] = []
        if skill.skill_id not in agent.skills:
            reasons.append("skill_not_allowed")
        if agent.autonomy < skill.required_autonomy:
            reasons.append("insufficient_autonomy")
        required_evidence = set(agent.required_evidence) | set(skill.required_evidence)
        if not required_evidence.issubset(context.evidence_ids):
            reasons.append("missing_evidence")
        if not skill.read_scopes.issubset(agent.allowed_read_scopes):
            reasons.append("agent_read_scope_violation")
        if not skill.write_scopes.issubset(agent.allowed_write_scopes):
            reasons.append("agent_write_scope_violation")
        if not skill.read_scopes.issubset(context.granted_read_scopes):
            reasons.append("context_read_scope_violation")
        if not skill.write_scopes.issubset(context.granted_write_scopes):
            reasons.append("context_write_scope_violation")
        if skill.risk_tier >= RiskTier.HIGH and not context.approved:
            reasons.append("approval_required")
        if context.approved and not context.approval_reference:
            reasons.append("approval_reference_required")
        return reasons

    def execute(
        self,
        agent: AgentSpec,
        skill_id: str,
        request: Mapping[str, Any],
        context: ExecutionContext,
    ) -> ExecutionResult:
        skill = self.registry.get(skill_id)
        request_hash = sha256_payload(request)
        cache_key = sha256_payload({
            "agent_id": agent.agent_id,
            "skill_id": skill_id,
            "request_hash": request_hash,
        })
        reasons = self._reasons(agent, skill, context)
        blocking = [reason for reason in reasons if reason != "approval_required"]
        if blocking:
            entry = self.ledger.append(
                "execution_rejected",
                {"agent_id": agent.agent_id, "skill_id": skill_id, "request_hash": request_hash, "reasons": reasons},
                actor=context.actor,
                timestamp=context.timestamp,
            )
            return ExecutionResult("rejected", {}, entry.entry_hash, tuple(reasons))
        if "approval_required" in reasons:
            entry = self.ledger.append(
                "approval_requested",
                {"agent_id": agent.agent_id, "skill_id": skill_id, "request_hash": request_hash, "risk_tier": skill.risk_tier.name},
                actor=context.actor,
                timestamp=context.timestamp,
            )
            return ExecutionResult("approval_required", {}, entry.entry_hash, tuple(reasons))
        if skill.idempotent and cache_key in self._cache:
            cached = self._cache[cache_key]
            entry = self.ledger.append(
                "execution_cache_hit",
                {
                    "agent_id": agent.agent_id,
                    "skill_id": skill_id,
                    "request_hash": request_hash,
                    "output_hash": sha256_payload(cached.output),
                    "original_receipt_hash": cached.receipt_hash,
                },
                actor=context.actor,
                timestamp=context.timestamp,
            )
            return ExecutionResult(cached.status, cached.output, entry.entry_hash, cached.reasons, True)

        start = perf_counter()
        try:
            output = dict(skill.handler(dict(request)))
            elapsed_ms = (perf_counter() - start) * 1000
            entry = self.ledger.append(
                "execution_completed",
                {
                    "agent_id": agent.agent_id,
                    "skill_id": skill_id,
                    "request_hash": request_hash,
                    "output_hash": sha256_payload(output),
                    "elapsed_ms": round(elapsed_ms, 6),
                    "approval_reference": context.approval_reference,
                },
                actor=context.actor,
                timestamp=context.timestamp,
            )
            result = ExecutionResult("completed", output, entry.entry_hash)
            if skill.idempotent:
                self._cache[cache_key] = result
            return result
        except Exception as exc:  # retained as evidence; caller receives structured failure
            elapsed_ms = (perf_counter() - start) * 1000
            entry = self.ledger.append(
                "execution_failed",
                {
                    "agent_id": agent.agent_id,
                    "skill_id": skill_id,
                    "request_hash": request_hash,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "elapsed_ms": round(elapsed_ms, 6),
                },
                actor=context.actor,
                timestamp=context.timestamp,
            )
            return ExecutionResult("failed", {}, entry.entry_hash, (f"{type(exc).__name__}:{exc}",))

    def execute_plan(
        self,
        agent: AgentSpec,
        steps: list[tuple[str, Mapping[str, Any]]],
        context: ExecutionContext,
    ) -> tuple[ExecutionResult, ...]:
        results: list[ExecutionResult] = []
        for skill_id, request in steps:
            result = self.execute(agent, skill_id, request, context)
            results.append(result)
            if result.status != "completed":
                break
        return tuple(results)
