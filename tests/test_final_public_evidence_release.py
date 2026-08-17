"""Regression tests for the final-evidence release path's ledger handling.

The release path rewrites `standards/public_cases/index.json` in place. It owns
the twenty-four models in EXPECTED_ALL_IDS and nothing else, so a public case
belonging to a later domain must survive the round trip untouched.

Before these tests the shape was frozen as literals (36 baseline cases over 18
models, 48 over 24 combined). Those literals were the only thing standing
between a twenty-fifth domain and silent deletion from the committed ledger:
raising the numbers to match a grown corpus -- the obvious reading of the
stale-count error -- would have let the rewrite proceed with the new domains
absent from `expected_models`, dropping their cases on the floor.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from tools import final_public_evidence, final_public_evidence_release


def case(model_id: str, index: int) -> dict:
    return {
        "model_id": model_id,
        "case_id": f"case-{model_id}-{index}",
        "case_type": "conventional" if index == 0 else "adversarial",
    }


def ledger(*, foreign: tuple[str, ...] = ()) -> dict:
    """A committed ledger: 18 baseline models, the final six, plus extras."""
    baseline_models = sorted(
        final_public_evidence.EXPECTED_ORIGINAL_IDS
        | final_public_evidence.EXPECTED_FRONTIER_IDS
    )
    cases = [case(m, n) for m in baseline_models for n in range(2)]
    cases += [
        case(m, n) for m in sorted(final_public_evidence.EXPECTED_FINAL_IDS) for n in range(2)
    ]
    cases += [case(m, 0) for m in foreign]
    return {
        "schema_version": "2.0",
        "as_of": "2026-08-17",
        "classification": "external_historical_cases",
        "counts_toward_m4": False,
        "case_count": len(cases),
        "evidence_models": len({item["model_id"] for item in cases}),
        "cases": cases,
    }


class ReleaseBaselineTests(unittest.TestCase):
    def restore(self, payload: dict) -> dict:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with patch.object(final_public_evidence, "PUBLIC_INDEX", path):
                final_public_evidence_release.restore_verified_baseline()
            return json.loads(path.read_text(encoding="utf-8"))

    def test_drops_the_final_cohort_it_regenerates(self) -> None:
        result = self.restore(ledger())
        models = {item["model_id"] for item in result["cases"]}
        self.assertFalse(models & final_public_evidence.EXPECTED_FINAL_IDS)
        self.assertEqual(36, len(result["cases"]))

    def test_a_later_domains_case_survives_the_rewrite(self) -> None:
        # The truncation this whole module exists to prevent.
        result = self.restore(ledger(foreign=("30", "31")))
        survivors = {
            item["case_id"]
            for item in result["cases"]
            if item["model_id"] in {"30", "31"}
        }
        self.assertEqual({"case-30-0", "case-31-0"}, survivors)

    def test_emitted_counts_are_derived_from_the_surviving_list(self) -> None:
        result = self.restore(ledger(foreign=("30", "31")))
        self.assertEqual(38, result["case_count"])
        self.assertEqual(20, result["evidence_models"])
        self.assertEqual(result["case_count"], len(result["cases"]))
        self.assertEqual(
            result["evidence_models"],
            len({item["model_id"] for item in result["cases"]}),
        )

    def test_a_missing_baseline_case_still_fails_closed(self) -> None:
        payload = ledger()
        payload["cases"] = [
            item for item in payload["cases"] if item["case_id"] != "case-03-1"
        ]
        with self.assertRaises(ValueError) as raised:
            self.restore(payload)
        self.assertIn("36 verified baseline cases", str(raised.exception))

    def test_a_missing_baseline_model_still_fails_closed(self) -> None:
        payload = ledger()
        payload["cases"] = [
            item for item in payload["cases"] if item["model_id"] != "03"
        ]
        with self.assertRaises(ValueError) as raised:
            self.restore(payload)
        self.assertIn("do not match expected", str(raised.exception))

    def test_partition_routes_every_model_to_exactly_one_bucket(self) -> None:
        cases = ledger(foreign=("30", "31"))["cases"]
        baseline, final_cohort, passthrough = final_public_evidence_release.partition_cases(
            cases
        )
        self.assertEqual(len(cases), len(baseline) + len(final_cohort) + len(passthrough))
        self.assertEqual(
            final_public_evidence.EXPECTED_ORIGINAL_IDS
            | final_public_evidence.EXPECTED_FRONTIER_IDS,
            {item["model_id"] for item in baseline},
        )
        self.assertEqual(
            final_public_evidence.EXPECTED_FINAL_IDS,
            {item["model_id"] for item in final_cohort},
        )
        self.assertEqual({"30", "31"}, {item["model_id"] for item in passthrough})


class SanitizeBaselineTests(unittest.TestCase):
    def test_a_later_domains_case_is_not_sanitized_against_the_registries(self) -> None:
        # `_sanitize_baseline` rewrites each case's manifest from the evidence
        # registries. A domain those registries were never meant to describe
        # must be skipped, not rejected and not rewritten.
        payload = {"cases": [case("31", 0)]}
        result = final_public_evidence._sanitize_baseline(payload, False)
        self.assertEqual(payload["cases"], result["cases"])

    def test_a_release_cohort_case_absent_from_the_registries_still_raises(self) -> None:
        payload = {"cases": [case("03", 0)]}
        with self.assertRaises(ValueError) as raised:
            final_public_evidence._sanitize_baseline(payload, False)
        self.assertIn("absent from evidence registries", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
