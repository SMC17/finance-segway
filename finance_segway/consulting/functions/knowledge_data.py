"""Scoped local knowledge retrieval, meeting records, and semantic metrics."""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import re
from typing import Any, Iterable, Mapping, Sequence


TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-]*")
ACTION = re.compile(r"^\[ACTION(?:\s+owner=([^\s\]]+))?(?:\s+due=([^\s\]]+))?\]\s*(.*)$", re.IGNORECASE)


def tokenize(text: str) -> tuple[str, ...]:
    return tuple(match.group(0).lower() for match in TOKEN.finditer(text))


@dataclass(frozen=True)
class KnowledgeDocument:
    document_id: str
    title: str
    text: str
    citation: str
    as_of: str
    allowed_roles: frozenset[str] = frozenset()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchResult:
    document_id: str
    title: str
    score: float
    snippet: str
    citation: str
    as_of: str


class KnowledgeBase:
    """Small-corpus BM25 retrieval with explicit source citations and ACLs."""

    def __init__(self, documents: Iterable[KnowledgeDocument] = ()) -> None:
        items = list(documents)
        self._documents = {item.document_id: item for item in items}
        if len(self._documents) != len(items):
            raise ValueError("document ids must be unique")

    def add(self, document: KnowledgeDocument) -> None:
        if document.document_id in self._documents:
            raise ValueError(f"duplicate document: {document.document_id}")
        self._documents[document.document_id] = document

    def search(
        self,
        query: str,
        *,
        roles: Iterable[str] = (),
        top_k: int = 5,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> tuple[SearchResult, ...]:
        if top_k <= 0 or k1 <= 0 or not 0 <= b <= 1:
            raise ValueError("invalid BM25 parameters")
        query_tokens = tokenize(query)
        if not query_tokens:
            return ()
        granted = set(roles)
        visible = [
            document for document in self._documents.values()
            if not document.allowed_roles or document.allowed_roles.intersection(granted)
        ]
        if not visible:
            return ()
        bodies = {
            document.document_id: tokenize(f"{document.title} {document.text}")
            for document in visible
        }
        average_length = sum(len(tokens) for tokens in bodies.values()) / len(bodies)
        document_frequency = {
            token: sum(token in set(tokens) for tokens in bodies.values())
            for token in set(query_tokens)
        }
        results: list[SearchResult] = []
        for document in visible:
            tokens = bodies[document.document_id]
            frequencies = {token: tokens.count(token) for token in set(query_tokens)}
            score = 0.0
            for token in query_tokens:
                frequency = frequencies[token]
                if not frequency:
                    continue
                df = document_frequency[token]
                idf = math.log(1 + (len(visible) - df + 0.5) / (df + 0.5))
                denominator = frequency + k1 * (1 - b + b * len(tokens) / max(average_length, 1))
                score += idf * frequency * (k1 + 1) / denominator
            if score <= 0:
                continue
            lowered = document.text.lower()
            positions = [lowered.find(token) for token in set(query_tokens) if lowered.find(token) >= 0]
            start = max(min(positions, default=0) - 80, 0)
            snippet = document.text[start:start + 240].strip()
            results.append(SearchResult(
                document.document_id,
                document.title,
                score,
                snippet,
                document.citation,
                document.as_of,
            ))
        return tuple(sorted(results, key=lambda item: (-item.score, item.document_id))[:top_k])


@dataclass(frozen=True)
class MeetingAction:
    text: str
    owner: str = ""
    due: str = ""


@dataclass(frozen=True)
class MeetingRecord:
    decisions: tuple[str, ...]
    actions: tuple[MeetingAction, ...]
    risks: tuple[str, ...]
    notes: tuple[str, ...]


def parse_tagged_minutes(text: str) -> MeetingRecord:
    """Parse human- or model-tagged minutes without pretending to transcribe.

    Supported line prefixes are [DECISION], [ACTION owner=X due=YYYY-MM-DD],
    [RISK], and [NOTE]. Untagged lines are retained as notes.
    """
    decisions: list[str] = []
    actions: list[MeetingAction] = []
    risks: list[str] = []
    notes: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        if lowered.startswith("[decision]"):
            decisions.append(line[len("[decision]"):].strip())
            continue
        action_match = ACTION.match(line)
        if action_match:
            owner, due, body = action_match.groups()
            actions.append(MeetingAction(body.strip(), owner or "", due or ""))
            continue
        if lowered.startswith("[risk]"):
            risks.append(line[len("[risk]"):].strip())
            continue
        if lowered.startswith("[note]"):
            notes.append(line[len("[note]"):].strip())
            continue
        notes.append(line)
    return MeetingRecord(tuple(decisions), tuple(actions), tuple(risks), tuple(notes))


@dataclass(frozen=True)
class SemanticMetric:
    metric_id: str
    name: str
    aggregation: str
    value_field: str = ""
    denominator_field: str = ""
    owner: str = ""
    source_fields: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()


class MetricCatalog:
    ALLOWED_AGGREGATIONS = {"sum", "average", "count", "count_distinct", "ratio"}

    def __init__(self) -> None:
        self._metrics: dict[str, SemanticMetric] = {}
        self._aliases: dict[str, str] = {}

    def register(self, metric: SemanticMetric) -> None:
        if metric.metric_id in self._metrics:
            raise ValueError(f"duplicate metric: {metric.metric_id}")
        if metric.aggregation not in self.ALLOWED_AGGREGATIONS:
            raise ValueError("unsupported aggregation")
        if metric.aggregation != "count" and not metric.value_field:
            raise ValueError("value_field is required")
        if metric.aggregation == "ratio" and not metric.denominator_field:
            raise ValueError("ratio metrics require denominator_field")
        self._metrics[metric.metric_id] = metric
        for alias in (metric.metric_id, metric.name, *metric.aliases):
            key = alias.strip().lower()
            if key in self._aliases and self._aliases[key] != metric.metric_id:
                raise ValueError(f"duplicate metric alias: {alias}")
            self._aliases[key] = metric.metric_id

    def resolve(self, name: str) -> SemanticMetric:
        metric_id = self._aliases.get(name.strip().lower())
        if metric_id is None:
            raise KeyError(f"unknown metric: {name}")
        return self._metrics[metric_id]

    def evaluate(self, name: str, rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
        metric = self.resolve(name)
        if metric.aggregation == "count":
            value = float(len(rows))
        elif metric.aggregation == "count_distinct":
            value = float(len({row.get(metric.value_field) for row in rows}))
        elif metric.aggregation == "sum":
            value = sum(float(row.get(metric.value_field, 0) or 0) for row in rows)
        elif metric.aggregation == "average":
            values = [float(row[metric.value_field]) for row in rows if row.get(metric.value_field) is not None]
            value = sum(values) / len(values) if values else 0.0
        else:
            numerator = sum(float(row.get(metric.value_field, 0) or 0) for row in rows)
            denominator = sum(float(row.get(metric.denominator_field, 0) or 0) for row in rows)
            value = numerator / denominator if denominator else 0.0
        return {
            "metric_id": metric.metric_id,
            "name": metric.name,
            "value": value,
            "owner": metric.owner,
            "row_count": len(rows),
            "lineage": metric.source_fields or tuple(
                field for field in (metric.value_field, metric.denominator_field) if field
            ),
        }
