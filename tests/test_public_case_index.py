"""The ledger's recorded snapshot hash must follow the snapshot it indexes.

Regression for the `source snapshot hash mismatch` failure that surfaced
three times in one evening: a case builder rewrites its snapshot, nothing
rewrote the ledger entry, and CI reported the divergence one step removed
from the edit that caused it.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools import public_case_index as pci

ROOT = Path(__file__).resolve().parents[1]


def ledger(**hashes: str) -> dict:
    return {
        "schema_version": "2.0",
        "case_count": len(hashes),
        "evidence_models": len(hashes),
        "cases": [
            {"case_id": cid, "model_id": "29", "case_type": "conventional",
             "snapshot_sha256": sha}
            for cid, sha in hashes.items()
        ],
    }


class SyncSnapshotHashTests(unittest.TestCase):
    def run_sync(self, payload: dict, case_id: str, sha: str) -> tuple[str, dict]:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = pci.sync_snapshot_hash(case_id, sha, index_path=path)
            return result, json.loads(path.read_text(encoding="utf-8"))

    def test_a_drifted_hash_is_rewritten(self) -> None:
        result, after = self.run_sync(ledger(alpha="old"), "alpha", "new")
        self.assertEqual(pci.UPDATED, result)
        self.assertEqual("new", after["cases"][0]["snapshot_sha256"])

    def test_an_agreeing_hash_is_left_alone(self) -> None:
        result, after = self.run_sync(ledger(alpha="same"), "alpha", "same")
        self.assertEqual(pci.UNCHANGED, result)
        self.assertEqual("same", after["cases"][0]["snapshot_sha256"])

    def test_an_unlisted_case_is_reported_not_invented(self) -> None:
        # A brand-new case has no ledger entry yet. Adding one is a human
        # decision -- this helper must not fabricate it.
        result, after = self.run_sync(ledger(alpha="a"), "beta", "b")
        self.assertEqual(pci.ABSENT, result)
        self.assertEqual(1, len(after["cases"]))

    def test_only_the_named_case_is_touched(self) -> None:
        _, after = self.run_sync(ledger(alpha="a", beta="b"), "alpha", "z")
        by_id = {c["case_id"]: c["snapshot_sha256"] for c in after["cases"]}
        self.assertEqual({"alpha": "z", "beta": "b"}, by_id)

    def test_report_sync_names_the_case_in_every_outcome(self) -> None:
        # Against a temp ledger, never the committed one -- report_sync
        # writes, and a test that reaches for the default path would edit
        # the real evidence index (it did, once, before this argument
        # existed).
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.json"
            path.write_text(json.dumps(ledger(alpha="old")), encoding="utf-8")
            messages = [
                pci.report_sync("alpha", "new", index_path=path),
                pci.report_sync("alpha", "new", index_path=path),
                pci.report_sync("ghost", "new", index_path=path),
            ]
        self.assertIn("updated", messages[0])
        self.assertIn("already current", messages[1])
        self.assertIn("not in standards/public_cases/index.json", messages[2])
        for message, case_id in zip(messages, ["alpha", "alpha", "ghost"]):
            self.assertIn(case_id, message)


class CommittedLedgerTests(unittest.TestCase):
    def test_every_committed_case_hash_matches_its_snapshot(self) -> None:
        index = json.loads(
            (ROOT / "standards" / "public_cases" / "index.json").read_text(
                encoding="utf-8"
            )
        )
        drifted = []
        for entry in index["cases"]:
            snapshot = json.loads(
                (ROOT / entry["snapshot"]).read_text(encoding="utf-8")
            )
            if entry.get("snapshot_sha256") != snapshot.get("snapshot_sha256"):
                drifted.append(entry["case_id"])
        self.assertEqual([], drifted)


if __name__ == "__main__":
    unittest.main()
