"""Benchmark, adversarial, metamorphic, and maturity-promotion evaluation."""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import StrEnum
from math import isclose
from typing import Any, Callable, Iterable, Mapping

from .evidence import sha256_payload


class AssertionOperator(StrEnum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    CONTAINS = "contains"
    EXISTS = "exists"
    APPROX = "approx"


class RelationOperator(StrEnum):
    EQUAL = "equal"
    NONDECREASING = "nondecreasing"
    NONINCREASING = "nonincreasing"
    INCREASES = "increases"
    DECREASES = "decreases"


def _path_value(output: Any, path: str) -> tuple[bool, Any]:
    current = asdict(output) if is_dataclass(output) else output
    if not path:
        return True, current
    for part in path.split("."):
        if is_dataclass(current):
            current = asdict(current)
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        elif isinstance(current, (tuple, list)) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return False, None
    return True, current


@dataclass(frozen=True)
class OutputAssertion:
    path: str
    operator: AssertionOperator
    expected: Any = None
    tolerance: float = 1e-9

    def evaluate(self, output: Any) -> tuple[bool, str]:
        exists, actual = _path_value(output, self.path)
        if self.operator is AssertionOperator.EXISTS:
            passed = exists is bool(self.expected)
        elif not exists:
            return False, f"missing_path:{self.path}"
        elif self.operator is AssertionOperator.EQ:
            passed = actual == self.expected
        elif self.operator is AssertionOperator.NE:
            passed = actual != self.expected
        elif self.operator is AssertionOperator.GT:
            passed = actual > self.expected
        elif self.operator is AssertionOperator.GTE:
            passed = actual >= self.expected
        elif self.operator is AssertionOperator.LT:
            passed = actual < self.expected
        elif self.operator is AssertionOperator.LTE:
            passed = actual <= self.expected
        elif self.operator is AssertionOperator.IN:
            passed = actual in self.expected
        elif self.operator is AssertionOperator.CONTAINS:
            passed = self.expected in actual
        elif self.operator is AssertionOperator.APPROX:
            passed = isclose(float(actual), float(self.expected), abs_tol=self.tolerance, rel_tol=self.tolerance)
        else:  # pragma: no cover - StrEnum constrains construction
            raise ValueError(f"unsupported assertion operator: {self.operator}")
        return passed, "" if passed else f"assertion_failed:{self.path}:{self.operator.value}"


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    payload: Mapping[str, Any]
    assertions: tuple[OutputAssertion, ...]
    category: str = "reference"
    severity: int = 2
    weight: float = 1.0
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.case_id or not self.assertions:
            raise ValueError("benchmark case id and assertions are required")
        if self.category not in {"reference", "boundary", "adversarial", "regression"}:
            raise ValueError("unknown benchmark category")
        if not 1 <= self.severity <= 4 or self.weight <= 0:
            raise ValueError("severity must be 1-4 and weight must be positive")


@dataclass(frozen=True)
class MetamorphicRelation:
    relation_id: str
    base_case_id: str
    variant_case_id: str
    path: str
    operator: RelationOperator
    tolerance: float = 1e-9


@dataclass(frozen=True)
class CaseEvaluation:
    case_id: str
    passed: bool
    category: str
    severity: int
    weight: float
    failures: tuple[str, ...]
    output: Any
    output_hash: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class RelationEvaluation:
    relation_id: str
    passed: bool
    failure: str = ""


@dataclass(frozen=True)
class EvaluationScorecard:
    suite_id: str
    case_count: int
    passed_cases: int
    pass_rate: float
    adversarial_pass_rate: float
    evidence_coverage: float
    critical_failures: tuple[str, ...]
    case_results: tuple[CaseEvaluation, ...]
    relation_results: tuple[RelationEvaluation, ...]
    scorecard_hash: str


@dataclass(frozen=True)
class PromotionGate:
    minimum_pass_rate: float = 1.0
    minimum_adversarial_pass_rate: float = 1.0
    minimum_evidence_coverage: float = 1.0
    require_integrated_workflow: bool = True
    require_valid_ledger: bool = True
    require_deterministic_replay: bool = True

    def __post_init__(self) -> None:
        for value in (
            self.minimum_pass_rate,
            self.minimum_adversarial_pass_rate,
            self.minimum_evidence_coverage,
        ):
            if not 0 <= value <= 1:
                raise ValueError("promotion thresholds must be between 0 and 1")


@dataclass(frozen=True)
class PromotionDecision:
    eligible: bool
    target_maturity: str
    reasons: tuple[str, ...]
    evidence_hash: str
    limitations: tuple[str, ...] = (
        "A2 is synthetic integrated benchmark evidence, not controlled client use.",
        "A3 and A4 require independent external evidence and maintained outcomes.",
    )


Runner = Callable[[BenchmarkCase], Any]


def evaluate_suite(
    suite_id: str,
    cases: Iterable[BenchmarkCase],
    runner: Runner,
    *,
    relations: Iterable[MetamorphicRelation] = (),
) -> EvaluationScorecard:
    items = list(cases)
    if not suite_id or not items:
        raise ValueError("suite_id and at least one benchmark case are required")
    ids = [item.case_id for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("benchmark case ids must be unique")
    results: list[CaseEvaluation] = []
    for case in items:
        try:
            output = runner(case)
            failures = tuple(
                failure
                for assertion in case.assertions
                for passed, failure in (assertion.evaluate(output),)
                if not passed
            )
        except Exception as exc:  # the benchmark records, rather than hides, runner failures
            output = {"error_type": type(exc).__name__, "error": str(exc)}
            failures = (f"runner_error:{type(exc).__name__}:{exc}",)
        results.append(CaseEvaluation(
            case.case_id,
            not failures,
            case.category,
            case.severity,
            case.weight,
            failures,
            output,
            sha256_payload(output),
            case.evidence_ids,
        ))

    by_id = {item.case_id: item for item in results}
    relation_results = tuple(
        _evaluate_relation(relation, by_id)
        for relation in relations
    )
    total_weight = sum(item.weight for item in results)
    passed_weight = sum(item.weight for item in results if item.passed)
    adversarial = [item for item in results if item.category == "adversarial"]
    adversarial_pass = (
        sum(item.passed for item in adversarial) / len(adversarial)
        if adversarial else 1.0
    )
    evidence_coverage = sum(bool(item.evidence_ids) for item in results) / len(results)
    critical_failures = tuple(sorted(
        item.case_id for item in results if item.severity == 4 and not item.passed
    ))
    critical_failures += tuple(sorted(
        item.relation_id for item in relation_results if not item.passed
    ))
    body = {
        "suite_id": suite_id,
        "case_results": [
            {
                "case_id": item.case_id,
                "passed": item.passed,
                "failures": item.failures,
                "output_hash": item.output_hash,
            }
            for item in results
        ],
        "relation_results": relation_results,
    }
    return EvaluationScorecard(
        suite_id=suite_id,
        case_count=len(results),
        passed_cases=sum(item.passed for item in results),
        pass_rate=passed_weight / total_weight,
        adversarial_pass_rate=adversarial_pass,
        evidence_coverage=evidence_coverage,
        critical_failures=critical_failures,
        case_results=tuple(results),
        relation_results=relation_results,
        scorecard_hash=sha256_payload(body),
    )


def _evaluate_relation(
    relation: MetamorphicRelation,
    results: Mapping[str, CaseEvaluation],
) -> RelationEvaluation:
    if relation.base_case_id not in results or relation.variant_case_id not in results:
        return RelationEvaluation(relation.relation_id, False, "unknown_relation_case")
    base_result = results[relation.base_case_id]
    variant_result = results[relation.variant_case_id]
    if not base_result.passed or not variant_result.passed:
        return RelationEvaluation(relation.relation_id, False, "related_case_failed")
    base_exists, base = _path_value(base_result.output, relation.path)
    variant_exists, variant = _path_value(variant_result.output, relation.path)
    if not base_exists or not variant_exists:
        return RelationEvaluation(relation.relation_id, False, f"missing_path:{relation.path}")
    if relation.operator is RelationOperator.EQUAL:
        passed = base == variant
    elif relation.operator is RelationOperator.NONDECREASING:
        passed = variant + relation.tolerance >= base
    elif relation.operator is RelationOperator.NONINCREASING:
        passed = variant <= base + relation.tolerance
    elif relation.operator is RelationOperator.INCREASES:
        passed = variant > base + relation.tolerance
    elif relation.operator is RelationOperator.DECREASES:
        passed = variant + relation.tolerance < base
    else:  # pragma: no cover
        raise ValueError(f"unsupported relation operator: {relation.operator}")
    failure = "" if passed else f"relation_failed:{relation.path}:{relation.operator.value}"
    return RelationEvaluation(relation.relation_id, passed, failure)


def assess_a2_promotion(
    scorecard: EvaluationScorecard,
    gate: PromotionGate = PromotionGate(),
    *,
    integrated_workflow: bool,
    ledger_valid: bool,
    deterministic_replay: bool,
) -> PromotionDecision:
    reasons: list[str] = []
    if scorecard.pass_rate < gate.minimum_pass_rate:
        reasons.append("benchmark_pass_rate_below_gate")
    if scorecard.adversarial_pass_rate < gate.minimum_adversarial_pass_rate:
        reasons.append("adversarial_pass_rate_below_gate")
    if scorecard.evidence_coverage < gate.minimum_evidence_coverage:
        reasons.append("evidence_coverage_below_gate")
    if scorecard.critical_failures:
        reasons.append("critical_failures_present")
    if gate.require_integrated_workflow and not integrated_workflow:
        reasons.append("integrated_workflow_required")
    if gate.require_valid_ledger and not ledger_valid:
        reasons.append("valid_evidence_ledger_required")
    if gate.require_deterministic_replay and not deterministic_replay:
        reasons.append("deterministic_replay_required")
    evidence = {
        "scorecard_hash": scorecard.scorecard_hash,
        "integrated_workflow": integrated_workflow,
        "ledger_valid": ledger_valid,
        "deterministic_replay": deterministic_replay,
        "reasons": reasons,
    }
    return PromotionDecision(not reasons, "A2", tuple(reasons), sha256_payload(evidence))
