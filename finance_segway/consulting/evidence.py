"""Append-only, hash-chained evidence and execution ledger."""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Iterable, Mapping


def _normalize(value: Any) -> Any:
    if is_dataclass(value):
        return _normalize(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _normalize(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple, set, frozenset)):
        items = [_normalize(item) for item in value]
        if isinstance(value, (set, frozenset)):
            return sorted(items, key=lambda item: json.dumps(item, sort_keys=True, default=str))
        return items
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def canonical_json(value: Any) -> str:
    return json.dumps(_normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_payload(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LedgerEntry:
    sequence: int
    timestamp: str
    actor: str
    event_type: str
    payload: Mapping[str, Any]
    previous_hash: str
    entry_hash: str


class EvidenceLedger:
    """In-memory ledger with deterministic export and tamper detection.

    Persistence is intentionally left to the caller. The core guarantee is that
    any mutation to an exported entry breaks the chain.
    """

    GENESIS_HASH = "0" * 64

    def __init__(self, entries: Iterable[LedgerEntry] = ()) -> None:
        self._entries = list(entries)
        if self._entries and not self.verify():
            raise ValueError("invalid evidence ledger")

    @property
    def entries(self) -> tuple[LedgerEntry, ...]:
        return tuple(self._entries)

    def append(
        self,
        event_type: str,
        payload: Mapping[str, Any],
        *,
        actor: str,
        timestamp: datetime | None = None,
    ) -> LedgerEntry:
        if not event_type or not actor:
            raise ValueError("event_type and actor are required")
        instant = timestamp or datetime.now(timezone.utc)
        if instant.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        normalized_payload = json.loads(canonical_json(payload))
        previous_hash = self._entries[-1].entry_hash if self._entries else self.GENESIS_HASH
        body = {
            "sequence": len(self._entries) + 1,
            "timestamp": instant.astimezone(timezone.utc).isoformat(),
            "actor": actor,
            "event_type": event_type,
            "payload": normalized_payload,
            "previous_hash": previous_hash,
        }
        entry = LedgerEntry(entry_hash=sha256_payload(body), **body)
        self._entries.append(entry)
        return entry

    def verify(self) -> bool:
        previous_hash = self.GENESIS_HASH
        for expected_sequence, entry in enumerate(self._entries, start=1):
            if entry.sequence != expected_sequence or entry.previous_hash != previous_hash:
                return False
            body = {
                "sequence": entry.sequence,
                "timestamp": entry.timestamp,
                "actor": entry.actor,
                "event_type": entry.event_type,
                "payload": entry.payload,
                "previous_hash": entry.previous_hash,
            }
            if sha256_payload(body) != entry.entry_hash:
                return False
            previous_hash = entry.entry_hash
        return True

    def export(self) -> list[dict[str, Any]]:
        return [asdict(entry) for entry in self._entries]

    @classmethod
    def from_export(cls, records: Iterable[Mapping[str, Any]]) -> "EvidenceLedger":
        return cls(LedgerEntry(**dict(record)) for record in records)
