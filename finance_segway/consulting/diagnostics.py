"""Evidence-backed functional diagnostics and maturity scoring."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .schema import DiagnosticQuestion, Direction, MetricDefinition, MetricObservation


@dataclass(frozen=True)
class MetricScore:
    metric_id: str
    value: float | None
    target: float
    score: float
    evidence_complete: bool
    status: str


@dataclass(frozen=True)
class QuestionScore:
    question_id: str
    score: float
    metric_scores: tuple[MetricScore, ...]
    missing_evidence: tuple[str, ...]


class DiagnosticEngine:
    def __init__(
        self,
        metrics: Iterable[MetricDefinition],
        questions: Iterable[DiagnosticQuestion],
    ) -> None:
        metric_items = list(metrics)
        question_items = list(questions)
        self.metrics = {item.metric_id: item for item in metric_items}
        self.questions = {item.question_id: item for item in question_items}
        if len(self.metrics) != len(metric_items) or len(self.questions) != len(question_items):
            raise ValueError("metric and question ids must be unique")
        for question in question_items:
            missing = set(question.metric_ids) - set(self.metrics)
            if missing:
                raise ValueError(f"{question.question_id} references unknown metrics: {sorted(missing)}")

    @staticmethod
    def _score(definition: MetricDefinition, value: float) -> float:
        target = float(definition.target)
        if definition.direction is Direction.HIGHER:
            if target <= 0:
                return 100.0 if value >= target else 0.0
            return max(0.0, min(100.0, 100 * value / target))
        if definition.direction is Direction.LOWER:
            if value <= target:
                return 100.0
            scale = max(abs(target), 1.0)
            return max(0.0, 100 * (1 - (value - target) / scale))
        lower = float(definition.lower_bound)
        upper = float(definition.upper_bound)
        if lower <= value <= upper:
            return 100.0
        distance = lower - value if value < lower else value - upper
        width = max(upper - lower, 1.0)
        return max(0.0, 100 * (1 - distance / width))

    def score_question(
        self,
        question_id: str,
        observations: Iterable[MetricObservation],
        available_evidence: Iterable[str],
    ) -> QuestionScore:
        question = self.questions[question_id]
        latest: dict[str, MetricObservation] = {}
        for observation in observations:
            current = latest.get(observation.metric_id)
            if current is None or observation.as_of > current.as_of:
                latest[observation.metric_id] = observation
        evidence = set(available_evidence)
        missing_evidence = tuple(sorted(set(question.required_evidence) - evidence))
        scores: list[MetricScore] = []
        for metric_id in question.metric_ids:
            definition = self.metrics[metric_id]
            observation = latest.get(metric_id)
            if observation is None:
                scores.append(MetricScore(metric_id, None, definition.target, 0.0, False, "missing_observation"))
                continue
            evidence_complete = bool(observation.evidence_ids) and set(observation.evidence_ids).issubset(evidence)
            raw_score = self._score(definition, observation.value)
            score = raw_score if evidence_complete else raw_score * 0.5
            status = "on_target" if raw_score >= 99.999 else "gap"
            if not evidence_complete:
                status = "unverified"
            scores.append(MetricScore(metric_id, observation.value, definition.target, score, evidence_complete, status))
        question_score = sum(item.score for item in scores) / len(scores)
        if missing_evidence:
            question_score *= 0.5
        return QuestionScore(question_id, question_score, tuple(scores), missing_evidence)

    def score_all(
        self,
        observations: Iterable[MetricObservation],
        available_evidence: Iterable[str],
    ) -> Mapping[str, QuestionScore]:
        observation_items = tuple(observations)
        evidence_items = tuple(available_evidence)
        return {
            question_id: self.score_question(question_id, observation_items, evidence_items)
            for question_id in sorted(self.questions)
        }
