"""Replayable local workflow orchestration over the governed agent runtime."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
from math import isfinite
from typing import Any, Iterable, Mapping

from .evidence import sha256_payload
from .policy import ApprovalGrant, PolicyDecision, PolicyEngine, PolicyRequest
from .runtime import AgentRuntime, ExecutionContext
from .schema import AgentSpec


class FailurePolicy(StrEnum):
    HALT = "halt"
    CONTINUE = "continue"
    ROLLBACK = "rollback"


@dataclass(frozen=True)
class WorkflowBudget:
    max_steps: int = 100
    max_attempts: int = 200
    max_cost_units: float = 1_000_000.0

    def __post_init__(self) -> None:
        if (
            self.max_steps <= 0 or self.max_attempts <= 0
            or not isfinite(self.max_cost_units) or self.max_cost_units < 0
        ):
            raise ValueError("workflow budget limits must be positive or nonnegative")


@dataclass(frozen=True)
class WorkflowStep:
    step_id: str
    skill_id: str
    dependencies: tuple[str, ...] = ()
    bindings: Mapping[str, str] = field(default_factory=dict)
    constants: Mapping[str, Any] = field(default_factory=dict)
    policy_action: str = ""
    failure_policy: FailurePolicy = FailurePolicy.HALT
    max_attempts: int = 1
    cost_units: float = 1.0
    compensation_skill_id: str = ""
    compensation_policy_action: str = ""
    compensation_bindings: Mapping[str, str] = field(default_factory=dict)
    compensation_constants: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.step_id or not self.skill_id:
            raise ValueError("step_id and skill_id are required")
        if self.max_attempts <= 0 or not isfinite(self.cost_units) or self.cost_units < 0:
            raise ValueError("step attempts must be positive and cost nonnegative")
        if (self.compensation_bindings or self.compensation_constants) and not self.compensation_skill_id:
            raise ValueError("compensation inputs require a compensation skill")


@dataclass(frozen=True)
class WorkflowDefinition:
    workflow_id: str
    version: str
    steps: tuple[WorkflowStep, ...]

    def __post_init__(self) -> None:
        if not self.workflow_id or not self.version or not self.steps:
            raise ValueError("workflow_id, version, and steps are required")
        ids = [step.step_id for step in self.steps]
        if len(ids) != len(set(ids)):
            raise ValueError("workflow step ids must be unique")
        known = set(ids)
        for step in self.steps:
            unknown = set(step.dependencies) - known
            if unknown:
                raise ValueError(f"unknown dependencies for {step.step_id}: {sorted(unknown)}")
            if step.step_id in step.dependencies:
                raise ValueError("a workflow step cannot depend on itself")
        self.ordered_steps()  # cycle validation

    @property
    def definition_hash(self) -> str:
        return sha256_payload(self)

    def ordered_steps(self) -> tuple[WorkflowStep, ...]:
        by_id = {step.step_id: step for step in self.steps}
        pending = set(by_id)
        completed: set[str] = set()
        ordered: list[WorkflowStep] = []
        while pending:
            ready = sorted(
                (step_id for step_id in pending if set(by_id[step_id].dependencies) <= completed),
            )
            if not ready:
                raise ValueError("workflow dependencies contain a cycle")
            for step_id in ready:
                ordered.append(by_id[step_id])
                completed.add(step_id)
                pending.remove(step_id)
        return tuple(ordered)


@dataclass(frozen=True)
class StepExecution:
    step_id: str
    status: str
    attempts: int
    output: Mapping[str, Any]
    receipt_hash: str = ""
    reasons: tuple[str, ...] = ()
    policy_decision_hash: str = ""
    compensation_status: str = ""
    compensation_receipt_hash: str = ""
    compensation_reasons: tuple[str, ...] = ()
    compensation_policy_decision_hash: str = ""


@dataclass(frozen=True)
class WorkflowRun:
    run_id: str
    workflow_id: str
    workflow_version: str
    status: str
    input_hash: str
    definition_hash: str
    steps: tuple[StepExecution, ...]
    attempts_used: int
    cost_units_used: float
    replay_fingerprint: str
    ledger_head: str


def _value_at(source: Any, path: str) -> Any:
    current = source
    for part in path.split(".") if path else ():
        if isinstance(current, Mapping):
            if part not in current:
                raise KeyError(f"binding path not found: {path}")
            current = current[part]
        elif isinstance(current, (tuple, list)) and part.isdigit():
            current = current[int(part)]
        else:
            raise KeyError(f"binding path not found: {path}")
    return current


def _resolve_request(
    bindings: Mapping[str, str],
    constants: Mapping[str, Any],
    state: Mapping[str, Any],
) -> dict[str, Any]:
    request = dict(constants)
    for target, source_path in sorted(bindings.items()):
        request[target] = _value_at(state, source_path)
    return request


class WorkflowExecutor:
    """Executes a typed DAG and records policy, runtime, and rollback evidence."""

    def __init__(self, runtime: AgentRuntime, policy_engine: PolicyEngine | None = None) -> None:
        self.runtime = runtime
        self.policy_engine = policy_engine

    def run(
        self,
        definition: WorkflowDefinition,
        agent: AgentSpec,
        inputs: Mapping[str, Any],
        context: ExecutionContext,
        *,
        run_id: str,
        approvals: Iterable[ApprovalGrant] = (),
        policy_attributes: Mapping[str, Any] | None = None,
        budget: WorkflowBudget | None = None,
    ) -> WorkflowRun:
        if not run_id:
            raise ValueError("run_id is required")
        limits = budget or WorkflowBudget()
        ordered = definition.ordered_steps()
        input_hash = sha256_payload(inputs)
        self.runtime.ledger.append(
            "workflow_started",
            {
                "run_id": run_id,
                "workflow_id": definition.workflow_id,
                "version": definition.version,
                "definition_hash": definition.definition_hash,
                "input_hash": input_hash,
            },
            actor=context.actor,
            timestamp=context.timestamp,
        )
        results: list[StepExecution] = []
        result_by_id: dict[str, StepExecution] = {}
        attempts_used = 0
        cost_used = 0.0
        workflow_status = "completed"
        approvals = tuple(approvals)

        for index, step in enumerate(ordered):
            if index >= limits.max_steps:
                workflow_status = "budget_exceeded"
                break
            blocked = [
                dependency for dependency in step.dependencies
                if result_by_id[dependency].status != "completed"
            ]
            if blocked:
                execution = StepExecution(
                    step.step_id, "blocked_dependency", 0, {},
                    reasons=tuple(f"dependency_not_completed:{item}" for item in blocked),
                )
                results.append(execution)
                result_by_id[step.step_id] = execution
                workflow_status = "completed_with_failures"
                continue

            state = self._state(inputs, run_id, result_by_id)
            request = _resolve_request(step.bindings, step.constants, state)
            projected_attempts = attempts_used + step.max_attempts
            projected_cost = cost_used + step.cost_units * step.max_attempts
            if projected_attempts > limits.max_attempts or projected_cost > limits.max_cost_units:
                execution = StepExecution(
                    step.step_id, "budget_exceeded", 0, {}, reasons=("workflow_budget_exceeded",),
                )
                results.append(execution)
                result_by_id[step.step_id] = execution
                workflow_status = "budget_exceeded"
                break

            policy_decision = self._authorize(
                step, request, agent, context, approvals, policy_attributes or {},
            )
            if policy_decision is not None and not policy_decision.allowed:
                status = "approval_required" if policy_decision.status == "approval_required" else "policy_denied"
                entry = self.runtime.ledger.append(
                    "workflow_policy_blocked",
                    {
                        "run_id": run_id,
                        "step_id": step.step_id,
                        "request_hash": sha256_payload(request),
                        "policy_decision_hash": policy_decision.decision_hash,
                        "status": policy_decision.status,
                    },
                    actor=context.actor,
                    timestamp=context.timestamp,
                )
                execution = StepExecution(
                    step.step_id, status, 0, {}, entry.entry_hash,
                    policy_decision.reasons, policy_decision.decision_hash,
                )
                results.append(execution)
                result_by_id[step.step_id] = execution
                workflow_status = status
                if step.failure_policy is FailurePolicy.ROLLBACK:
                    workflow_status = self._rollback(
                        ordered, agent, context, inputs, run_id, results, result_by_id,
                        approvals, policy_attributes or {},
                    )
                if step.failure_policy is not FailurePolicy.CONTINUE:
                    break
                workflow_status = "completed_with_failures"
                continue

            final = None
            runtime_context = self._runtime_context(context, policy_decision)
            for attempt in range(1, step.max_attempts + 1):
                attempts_used += 1
                cost_used += step.cost_units
                final = self.runtime.execute(agent, step.skill_id, request, runtime_context)
                if final.status != "failed":
                    break
            assert final is not None
            execution = StepExecution(
                step.step_id,
                final.status,
                attempt,
                final.output,
                final.receipt_hash,
                final.reasons,
                policy_decision.decision_hash if policy_decision else "",
            )
            results.append(execution)
            result_by_id[step.step_id] = execution
            if final.status != "completed":
                workflow_status = final.status
                if step.failure_policy is FailurePolicy.ROLLBACK:
                    workflow_status = self._rollback(
                        ordered, agent, context, inputs, run_id, results, result_by_id,
                        approvals, policy_attributes or {},
                    )
                if step.failure_policy is not FailurePolicy.CONTINUE:
                    break
                workflow_status = "completed_with_failures"

        fingerprint = sha256_payload({
            "workflow_id": definition.workflow_id,
            "version": definition.version,
            "definition_hash": definition.definition_hash,
            "input_hash": input_hash,
            "steps": [
                {
                    "step_id": item.step_id,
                    "status": item.status,
                    "attempts": item.attempts,
                    "output": item.output,
                    "reasons": item.reasons,
                    "compensation_status": item.compensation_status,
                    "compensation_reasons": item.compensation_reasons,
                }
                for item in results
            ],
        })
        completed_entry = self.runtime.ledger.append(
            "workflow_completed",
            {
                "run_id": run_id,
                "status": workflow_status,
                "attempts_used": attempts_used,
                "cost_units_used": cost_used,
                "replay_fingerprint": fingerprint,
            },
            actor=context.actor,
            timestamp=context.timestamp,
        )
        return WorkflowRun(
            run_id=run_id,
            workflow_id=definition.workflow_id,
            workflow_version=definition.version,
            status=workflow_status,
            input_hash=input_hash,
            definition_hash=definition.definition_hash,
            steps=tuple(results),
            attempts_used=attempts_used,
            cost_units_used=cost_used,
            replay_fingerprint=fingerprint,
            ledger_head=completed_entry.entry_hash,
        )

    def _authorize(
        self,
        step: WorkflowStep,
        request: Mapping[str, Any],
        agent: AgentSpec,
        context: ExecutionContext,
        approvals: tuple[ApprovalGrant, ...],
        policy_attributes: Mapping[str, Any],
    ) -> PolicyDecision | None:
        return self._authorize_action(
            step.policy_action,
            step.step_id,
            request,
            agent,
            context,
            approvals,
            policy_attributes,
            phase="forward",
        )

    def _authorize_action(
        self,
        action: str,
        step_id: str,
        request: Mapping[str, Any],
        agent: AgentSpec,
        context: ExecutionContext,
        approvals: tuple[ApprovalGrant, ...],
        policy_attributes: Mapping[str, Any],
        *,
        phase: str,
    ) -> PolicyDecision | None:
        if self.policy_engine is None or not action:
            return None
        attributes = {
            "request": request,
            "step_id": step_id,
            "agent_id": agent.agent_id,
            "phase": phase,
            **dict(policy_attributes),
        }
        policy_request = PolicyRequest.from_payload(
            action,
            context.actor,
            request,
            attributes=attributes,
            requester=context.actor,
            executor=agent.agent_id,
            at=context.timestamp,
        )
        decision = self.policy_engine.evaluate(policy_request, approvals)
        self.runtime.ledger.append(
            "workflow_policy_evaluated",
            {
                "step_id": step_id,
                "phase": phase,
                "decision_hash": decision.decision_hash,
                "status": decision.status,
                "matched_rule_ids": decision.matched_rule_ids,
                "obligations": decision.obligations,
            },
            actor=context.actor,
            timestamp=context.timestamp,
        )
        return decision

    @staticmethod
    def _runtime_context(
        context: ExecutionContext,
        policy_decision: PolicyDecision | None,
    ) -> ExecutionContext:
        if (
            policy_decision is None
            or not policy_decision.allowed
            or not policy_decision.approval_ids
        ):
            return context
        return replace(
            context,
            approved=True,
            approval_reference=f"policy:{policy_decision.decision_hash}",
        )

    def _rollback(
        self,
        ordered: tuple[WorkflowStep, ...],
        agent: AgentSpec,
        context: ExecutionContext,
        inputs: Mapping[str, Any],
        run_id: str,
        results: list[StepExecution],
        result_by_id: dict[str, StepExecution],
        approvals: tuple[ApprovalGrant, ...],
        policy_attributes: Mapping[str, Any],
    ) -> str:
        steps = {step.step_id: step for step in ordered}
        rollback_failed = False
        for prior in reversed(results):
            step = steps[prior.step_id]
            if prior.status != "completed" or not step.compensation_skill_id:
                continue
            state = self._state(inputs, run_id, result_by_id)
            if step.compensation_bindings or step.compensation_constants:
                request = _resolve_request(
                    step.compensation_bindings, step.compensation_constants, state,
                )
            else:
                request = dict(prior.output)
            policy_decision = None
            if self.policy_engine is not None:
                if step.compensation_policy_action:
                    policy_decision = self._authorize_action(
                        step.compensation_policy_action,
                        step.step_id,
                        request,
                        agent,
                        context,
                        approvals,
                        policy_attributes,
                        phase="compensation",
                    )
                else:
                    entry = self.runtime.ledger.append(
                        "workflow_compensation_policy_blocked",
                        {
                            "run_id": run_id,
                            "step_id": step.step_id,
                            "request_hash": sha256_payload(request),
                            "reason": "compensation_policy_action_required",
                        },
                        actor=context.actor,
                        timestamp=context.timestamp,
                    )
                    updated = replace(
                        prior,
                        compensation_status="policy_denied",
                        compensation_receipt_hash=entry.entry_hash,
                        compensation_reasons=("compensation_policy_action_required",),
                    )
                    location = results.index(prior)
                    results[location] = updated
                    result_by_id[prior.step_id] = updated
                    rollback_failed = True
                    continue
            if policy_decision is not None and not policy_decision.allowed:
                status = (
                    "approval_required"
                    if policy_decision.status == "approval_required"
                    else "policy_denied"
                )
                entry = self.runtime.ledger.append(
                    "workflow_compensation_policy_blocked",
                    {
                        "run_id": run_id,
                        "step_id": step.step_id,
                        "request_hash": sha256_payload(request),
                        "policy_decision_hash": policy_decision.decision_hash,
                        "status": policy_decision.status,
                    },
                    actor=context.actor,
                    timestamp=context.timestamp,
                )
                updated = replace(
                    prior,
                    compensation_status=status,
                    compensation_receipt_hash=entry.entry_hash,
                    compensation_reasons=policy_decision.reasons,
                    compensation_policy_decision_hash=policy_decision.decision_hash,
                )
                location = results.index(prior)
                results[location] = updated
                result_by_id[prior.step_id] = updated
                rollback_failed = True
                continue
            compensation = self.runtime.execute(
                agent,
                step.compensation_skill_id,
                request,
                self._runtime_context(context, policy_decision),
            )
            updated = replace(
                prior,
                compensation_status=compensation.status,
                compensation_receipt_hash=compensation.receipt_hash,
                compensation_reasons=compensation.reasons,
                compensation_policy_decision_hash=(
                    policy_decision.decision_hash if policy_decision else ""
                ),
            )
            location = results.index(prior)
            results[location] = updated
            result_by_id[prior.step_id] = updated
            rollback_failed = rollback_failed or compensation.status != "completed"
        return "rollback_failed" if rollback_failed else "rolled_back"

    @staticmethod
    def _state(
        inputs: Mapping[str, Any],
        run_id: str,
        results: Mapping[str, StepExecution],
    ) -> Mapping[str, Any]:
        return {
            "input": inputs,
            "run": {"run_id": run_id},
            "steps": {
                step_id: {
                    "status": result.status,
                    "output": result.output,
                    "receipt_hash": result.receipt_hash,
                }
                for step_id, result in results.items()
            },
        }


def replay_matches(first: WorkflowRun, second: WorkflowRun) -> bool:
    """Compares deterministic semantics while ignoring receipt/timing changes."""
    return (
        first.definition_hash == second.definition_hash
        and first.input_hash == second.input_hash
        and first.replay_fingerprint == second.replay_fingerprint
    )
