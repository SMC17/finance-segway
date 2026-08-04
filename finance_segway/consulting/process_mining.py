"""Dependency-free process discovery, conformance, and bottleneck analysis.

The miner operates on normalized event records supplied by the caller.  It does
not connect to source systems and it does not infer meaning that is absent from
the log.  Its purpose is to turn observed work into reproducible consulting
evidence before a workflow is redesigned or automated.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from statistics import median
from typing import Any, Iterable, Mapping


def _percentile(values: Iterable[float], probability: float) -> float:
    items = sorted(float(value) for value in values)
    if not items:
        return 0.0
    if not 0 <= probability <= 1:
        raise ValueError("probability must be between 0 and 1")
    if len(items) == 1:
        return items[0]
    position = probability * (len(items) - 1)
    lower = int(position)
    upper = min(lower + 1, len(items) - 1)
    weight = position - lower
    return items[lower] * (1 - weight) + items[upper] * weight


@dataclass(frozen=True)
class ProcessEvent:
    case_id: str
    activity_id: str
    occurred_at: datetime
    actor: str = ""
    event_id: str = ""
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.case_id or not self.activity_id:
            raise ValueError("case_id and activity_id are required")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")


@dataclass(frozen=True)
class TransitionPerformance:
    source: str
    target: str
    count: int
    share: float
    actor_handoffs: int
    median_wait_hours: float
    p90_wait_hours: float
    total_wait_hours: float


@dataclass(frozen=True)
class ProcessVariant:
    activities: tuple[str, ...]
    case_count: int
    share: float
    median_cycle_hours: float


@dataclass(frozen=True)
class ConformanceViolation:
    case_id: str
    violation_type: str
    detail: str


@dataclass(frozen=True)
class ProcessAssessment:
    case_count: int
    event_count: int
    variant_count: int
    median_cycle_hours: float
    p90_cycle_hours: float
    rework_event_rate: float
    average_handoffs_per_case: float
    conformance_rate: float
    straight_through_rate: float
    variants: tuple[ProcessVariant, ...]
    transitions: tuple[TransitionPerformance, ...]
    violations: tuple[ConformanceViolation, ...]

    @property
    def bottlenecks(self) -> tuple[TransitionPerformance, ...]:
        """Transitions ranked by aggregate delay, then tail wait."""
        return tuple(sorted(
            self.transitions,
            key=lambda item: (-item.total_wait_hours, -item.p90_wait_hours, item.source, item.target),
        ))


class ProcessMiner:
    """Discovers traces and checks them against an explicitly supplied model."""

    def __init__(self, events: Iterable[ProcessEvent]) -> None:
        items = list(events)
        if not items:
            raise ValueError("at least one process event is required")
        event_ids = [item.event_id for item in items if item.event_id]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("event_id values must be unique when supplied")
        grouped: dict[str, list[ProcessEvent]] = defaultdict(list)
        for item in items:
            grouped[item.case_id].append(item)
        self._traces = {
            case_id: tuple(sorted(
                trace,
                key=lambda item: (item.occurred_at, item.event_id, item.activity_id),
            ))
            for case_id, trace in grouped.items()
        }

    @property
    def traces(self) -> Mapping[str, tuple[ProcessEvent, ...]]:
        return dict(self._traces)

    def assess(
        self,
        *,
        allowed_transitions: Iterable[tuple[str, str]],
        required_activities: Iterable[str] = (),
        allowed_starts: Iterable[str] = (),
        allowed_ends: Iterable[str] = (),
    ) -> ProcessAssessment:
        allowed = set(allowed_transitions)
        required = set(required_activities)
        starts = set(allowed_starts)
        ends = set(allowed_ends)
        if not allowed and any(len(trace) > 1 for trace in self._traces.values()):
            raise ValueError("allowed_transitions are required for multi-event traces")

        violations: list[ConformanceViolation] = []
        transition_waits: dict[tuple[str, str], list[float]] = defaultdict(list)
        transition_handoffs: Counter[tuple[str, str]] = Counter()
        variant_cycles: dict[tuple[str, ...], list[float]] = defaultdict(list)
        cycle_hours: list[float] = []
        total_events = 0
        rework_events = 0
        total_handoffs = 0
        conforming_cases = 0
        straight_through_cases = 0

        for case_id, trace in sorted(self._traces.items()):
            activities = tuple(item.activity_id for item in trace)
            total_events += len(trace)
            repeated = sum(count - 1 for count in Counter(activities).values() if count > 1)
            rework_events += repeated
            duration = (trace[-1].occurred_at - trace[0].occurred_at).total_seconds() / 3600
            if duration < 0:
                raise ValueError("trace ordering produced a negative duration")
            cycle_hours.append(duration)
            variant_cycles[activities].append(duration)
            case_violations = 0

            if starts and activities[0] not in starts:
                violations.append(ConformanceViolation(case_id, "invalid_start", activities[0]))
                case_violations += 1
            if ends and activities[-1] not in ends:
                violations.append(ConformanceViolation(case_id, "invalid_end", activities[-1]))
                case_violations += 1
            for missing in sorted(required - set(activities)):
                violations.append(ConformanceViolation(case_id, "missing_activity", missing))
                case_violations += 1
            for source, target in zip(trace, trace[1:]):
                edge = (source.activity_id, target.activity_id)
                wait = (target.occurred_at - source.occurred_at).total_seconds() / 3600
                transition_waits[edge].append(wait)
                if source.actor and target.actor and source.actor != target.actor:
                    transition_handoffs[edge] += 1
                    total_handoffs += 1
                if edge not in allowed:
                    detail = f"{edge[0]}->{edge[1]}"
                    violations.append(ConformanceViolation(case_id, "unexpected_transition", detail))
                    case_violations += 1
            if case_violations == 0:
                conforming_cases += 1
                if repeated == 0:
                    straight_through_cases += 1

        case_count = len(self._traces)
        transition_count = sum(len(values) for values in transition_waits.values())
        transitions = tuple(sorted((
            TransitionPerformance(
                source=edge[0],
                target=edge[1],
                count=len(waits),
                share=len(waits) / transition_count if transition_count else 0.0,
                actor_handoffs=transition_handoffs[edge],
                median_wait_hours=median(waits),
                p90_wait_hours=_percentile(waits, 0.9),
                total_wait_hours=sum(waits),
            )
            for edge, waits in transition_waits.items()
        ), key=lambda item: (item.source, item.target)))
        variants = tuple(sorted((
            ProcessVariant(
                activities=activities,
                case_count=len(durations),
                share=len(durations) / case_count,
                median_cycle_hours=median(durations),
            )
            for activities, durations in variant_cycles.items()
        ), key=lambda item: (-item.case_count, item.activities)))
        return ProcessAssessment(
            case_count=case_count,
            event_count=total_events,
            variant_count=len(variants),
            median_cycle_hours=median(cycle_hours),
            p90_cycle_hours=_percentile(cycle_hours, 0.9),
            rework_event_rate=rework_events / total_events if total_events else 0.0,
            average_handoffs_per_case=total_handoffs / case_count,
            conformance_rate=conforming_cases / case_count,
            straight_through_rate=straight_through_cases / case_count,
            variants=variants,
            transitions=transitions,
            violations=tuple(violations),
        )

    def cost_of_delay(
        self,
        assessment: ProcessAssessment,
        *,
        value_per_case_hour: float,
    ) -> Mapping[str, float]:
        if value_per_case_hour < 0:
            raise ValueError("value_per_case_hour must be nonnegative")
        return {
            f"{item.source}->{item.target}": item.total_wait_hours * value_per_case_hour
            for item in assessment.transitions
        }
