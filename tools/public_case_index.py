"""Keep the public ledger's recorded snapshot hash equal to the snapshot's own.

`final_public_evidence._validate_combined_index` asserts

    index_entry["snapshot_sha256"] == snapshot_json["snapshot_sha256"]

and fails with `source snapshot hash mismatch` when they diverge. A case
builder writes its snapshot -- and with it a fresh `snapshot_sha256` -- but
nothing wrote the ledger entry, so *every* regeneration of *any* case left
the two out of step. The mismatch then surfaced in CI, one step removed
from the edit that caused it, with a message that names the symptom rather
than the cause.

It has been hit three times: on the Fund of Funds case (#99, fixed by hand),
and again on both the ETF and Fund of Funds regenerations. Each time the
remedy was to copy one hex string between two files. This module makes the
builder do it, so the ledger cannot drift from the artifact it indexes.

Deliberately narrow: it updates the recorded hash for a case that is already
in the ledger and nothing else. Adding a case to the ledger, changing its
paths, or removing it stays a human edit -- those are decisions, whereas a
hash following its own file is bookkeeping.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_INDEX = ROOT / "standards" / "public_cases" / "index.json"

UPDATED = "updated"
UNCHANGED = "unchanged"
ABSENT = "absent"


def sync_snapshot_hash(
    case_id: str, snapshot_sha256: str, *, index_path: Path | None = None
) -> str:
    """Point the ledger entry for `case_id` at `snapshot_sha256`.

    Returns UPDATED if the ledger was rewritten, UNCHANGED if it already
    agreed, or ABSENT if this case has no ledger entry yet (a brand-new case
    whose entry a human still has to add -- not an error).
    """
    path = index_path or PUBLIC_INDEX
    index = json.loads(path.read_text(encoding="utf-8"))
    for entry in index.get("cases", []):
        if entry.get("case_id") != case_id:
            continue
        if entry.get("snapshot_sha256") == snapshot_sha256:
            return UNCHANGED
        entry["snapshot_sha256"] = snapshot_sha256
        path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
        return UPDATED
    return ABSENT


def report_sync(
    case_id: str, snapshot_sha256: str, *, index_path: Path | None = None
) -> str:
    """sync_snapshot_hash plus the one-line message a builder should print."""
    result = sync_snapshot_hash(case_id, snapshot_sha256, index_path=index_path)
    if result == UPDATED:
        return f"ledger snapshot_sha256 updated for {case_id}"
    if result == UNCHANGED:
        return f"ledger snapshot_sha256 already current for {case_id}"
    return (
        f"{case_id} is not in standards/public_cases/index.json yet -- "
        "add its ledger entry before this case can validate"
    )
