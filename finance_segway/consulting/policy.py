"""Explainable policy-as-code with deny overrides and segregation of duties."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Iterable, Mapping

from .evidence import sha256_payload


class PolicyEffect(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class ConditionOperator(StrEnum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    INTERSECTS = "intersects"
    EXISTS = "exists"


_MISSING = object()


def _resolve(values: Mapping[str, Any], path: str) -> Any:
    current: Any = values
    for part in path.split("."):
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        else:
            return _MISSING
    return current


@dataclass(frozen=True)
class PolicyCondition:
    path: str
    operator: ConditionOperator
    value: Any = None

    def __post_init__(self) -> None:
        if not self.path:
            raise ValueError("condition path is required")

    def matches(self, values: Mapping[str, Any]) -> bool:
        actual = _resolve(values, self.path)
        if self.operator is ConditionOperator.EXISTS:
            return (actual is not _MISSING) is bool(self.value)
        if actual is _MISSING:
            return False
        if self.operator is ConditionOperator.EQ:
            return actual == self.value
        if self.operator is ConditionOperator.NE:
            return actual != self.value
        if self.operator is ConditionOperator.GT:
            return actual > self.value
        if self.operator is ConditionOperator.GTE:
            return actual >= self.value
        if self.operator is ConditionOperator.LT:
            return actual < self.value
        if self.operator is ConditionOperator.LTE:
            return actual <= self.value
        if self.operator is ConditionOperator.IN:
            return actual in self.value
        if self.operator is ConditionOperator.NOT_IN:
            return actual not in self.value
        if self.operator is ConditionOperator.CONTAINS:
            return self.value in actual
        if self.operator is ConditionOperator.INTERSECTS:
            return bool(set(actual).intersection(self.value))
        raise ValueError(f"unsupported condition operator: {self.operator}")


@dataclass(frozen=True)
class PolicyRule:
    rule_id: str
    action: str
    effect: PolicyEffect
    conditions: tuple[PolicyCondition, ...] = ()
    obligations: tuple[str, ...] = ()
    approval_roles: tuple[str, ...] = ()
    segregate_approver_from: tuple[str, ...] = ("requester", "executor")
    priority: int = 0

    def __post_init__(self) -> None:
        if not self.rule_id or not self.action:
            raise ValueError("rule_id and action are required")
        if self.effect is PolicyEffect.REQUIRE_APPROVAL and not self.approval_roles:
            raise ValueError("approval rules require at least one approval role")
        if any(value not in {"requester", "executor"} for value in self.segregate_approver_from):
            raise ValueError("segregate_approver_from supports requester and executor")


@dataclass(frozen=True)
class PolicyRequest:
    action: str
    actor: str
    request_hash: str
    attributes: Mapping[str, Any]
    requester: str = ""
    executor: str = ""
    at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.action or not self.actor or not self.request_hash:
            raise ValueError("action, actor, and request_hash are required")
        if self.at is not None and self.at.tzinfo is None:
            raise ValueError("policy request time must be timezone-aware")

    @classmethod
    def from_payload(
        cls,
        action: str,
        actor: str,
        payload: Mapping[str, Any],
        *,
        attributes: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> "PolicyRequest":
        return cls(
            action,
            actor,
            sha256_payload(payload),
            payload if attributes is None else attributes,
            **kwargs,
        )


@dataclass(frozen=True)
class ApprovalGrant:
    approval_id: str
    actor: str
    role: str
    action: str
    request_hash: str
    granted_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        if not all((self.approval_id, self.actor, self.role, self.action, self.request_hash)):
            raise ValueError("approval identity, scope, and actor are required")
        if self.granted_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("approval timestamps must be timezone-aware")
        if self.expires_at <= self.granted_at:
            raise ValueError("approval must expire after it is granted")


@dataclass(frozen=True)
class PolicyDecision:
    status: str
    allowed: bool
    matched_rule_ids: tuple[str, ...]
    obligations: tuple[str, ...]
    approval_ids: tuple[str, ...]
    missing_approval_roles: tuple[str, ...]
    reasons: tuple[str, ...]
    decision_hash: str


class PolicyEngine:
    """Evaluates attribute rules with explicit, default-deny semantics."""

    def __init__(self, rules: Iterable[PolicyRule]) -> None:
        items = list(rules)
        ids = [item.rule_id for item in items]
        if len(ids) != len(set(ids)):
            raise ValueError("policy rule ids must be unique")
        self._rules = tuple(sorted(items, key=lambda item: (-item.priority, item.rule_id)))

    def evaluate(
        self,
        request: PolicyRequest,
        approvals: Iterable[ApprovalGrant] = (),
    ) -> PolicyDecision:
        values = {
            "actor": request.actor,
            "requester": request.requester,
            "executor": request.executor,
            "attributes": request.attributes,
        }
        matched = tuple(
            rule for rule in self._rules
            if rule.action in {request.action, "*"}
            and all(condition.matches(values) for condition in rule.conditions)
        )
        obligations = tuple(sorted({item for rule in matched for item in rule.obligations}))
        deny_rules = tuple(rule.rule_id for rule in matched if rule.effect is PolicyEffect.DENY)
        if deny_rules:
            return self._decision(
                "denied", False, matched, obligations, (), (),
                tuple(f"deny_override:{rule_id}" for rule_id in deny_rules),
            )

        authorization_rules = tuple(
            rule for rule in matched
            if rule.effect in {PolicyEffect.ALLOW, PolicyEffect.REQUIRE_APPROVAL}
        )
        if not authorization_rules:
            return self._decision(
                "denied", False, matched, obligations, (), (), ("default_deny",),
            )

        now = request.at or datetime.now(timezone.utc)
        valid_grants = [
            grant for grant in approvals
            if grant.request_hash == request.request_hash
            and grant.action in {request.action, "*"}
            and grant.granted_at <= now < grant.expires_at
        ]
        selected: list[ApprovalGrant] = []
        missing_roles: list[str] = []
        used_actors: set[str] = set()
        segregation_reasons: list[str] = []
        for rule in authorization_rules:
            if rule.effect is not PolicyEffect.REQUIRE_APPROVAL:
                continue
            excluded = {
                getattr(request, relation)
                for relation in rule.segregate_approver_from
                if getattr(request, relation)
            }
            for role in rule.approval_roles:
                candidates = [
                    grant for grant in valid_grants
                    if grant.role == role
                    and grant.actor not in used_actors
                    and grant.actor not in excluded
                ]
                if not candidates:
                    missing_roles.append(role)
                    if any(grant.role == role and grant.actor in excluded for grant in valid_grants):
                        segregation_reasons.append(f"segregation_of_duties:{role}")
                    continue
                chosen = sorted(candidates, key=lambda item: (item.expires_at, item.approval_id))[0]
                selected.append(chosen)
                used_actors.add(chosen.actor)
        if missing_roles:
            reasons = tuple(sorted(set(segregation_reasons + ["approval_required"])))
            return self._decision(
                "approval_required", False, matched, obligations,
                tuple(item.approval_id for item in selected), tuple(sorted(missing_roles)), reasons,
            )
        return self._decision(
            "allowed", True, matched, obligations,
            tuple(item.approval_id for item in selected), (), (),
        )

    @staticmethod
    def _decision(
        status: str,
        allowed: bool,
        matched: Iterable[PolicyRule],
        obligations: tuple[str, ...],
        approval_ids: tuple[str, ...],
        missing_roles: tuple[str, ...],
        reasons: tuple[str, ...],
    ) -> PolicyDecision:
        rule_ids = tuple(rule.rule_id for rule in matched)
        body = {
            "status": status,
            "allowed": allowed,
            "matched_rule_ids": rule_ids,
            "obligations": obligations,
            "approval_ids": approval_ids,
            "missing_approval_roles": missing_roles,
            "reasons": reasons,
        }
        return PolicyDecision(decision_hash=sha256_payload(body), **body)
