from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import final_public_evidence
from tools import final_public_evidence_release as release


class PreservesOutOfCohortCasesTests(unittest.TestCase):
    """Regression coverage for the bug where restore_verified_36_case_baseline()
    and materialize() -- both scoped to the original 01-24 domain cohort --
    silently dropped any case from a later domain (25, 29-31, ...) if this
    release tool were ever run for real. See tools/final_public_evidence_release.py's
    module docstring."""

    def test_cases_outside_known_cohort_finds_only_post_24_domains(self):
        index = {
            "cases": [
                {"case_id": "a", "model_id": "01"},
                {"case_id": "b", "model_id": "24"},
                {"case_id": "c", "model_id": "29"},
                {"case_id": "d", "model_id": "30"},
                {"case_id": "e", "model_id": "31"},
            ]
        }
        preserved = release._cases_outside_known_cohort(index)
        self.assertEqual({item["case_id"] for item in preserved}, {"c", "d", "e"})

    def test_restore_preserved_cases_adds_them_back_without_duplication(self):
        with tempfile.TemporaryDirectory() as tmp:
            index_path = Path(tmp) / "index.json"
            index_path.write_text(
                json.dumps(
                    {
                        "as_of": "2026-08-17",
                        "cases": [
                            {"case_id": "01-a", "model_id": "01", "case_type": "conventional"},
                            {"case_id": "01-b", "model_id": "01", "case_type": "adversarial"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            preserved = [
                {"case_id": "30-a", "model_id": "30", "case_type": "conventional"},
                {"case_id": "31-a", "model_id": "31", "case_type": "conventional"},
            ]
            with patch.object(final_public_evidence, "PUBLIC_INDEX", index_path):
                combined = release._restore_preserved_cases(preserved)

            self.assertEqual(combined["case_count"], 4)
            self.assertEqual(combined["evidence_models"], 3)
            self.assertEqual(
                {item["case_id"] for item in combined["cases"]},
                {"01-a", "01-b", "30-a", "31-a"},
            )
            on_disk = json.loads(index_path.read_text(encoding="utf-8"))
            self.assertEqual(on_disk["case_count"], 4)

    def test_restore_preserved_cases_does_not_overwrite_an_existing_case_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            index_path = Path(tmp) / "index.json"
            index_path.write_text(
                json.dumps(
                    {
                        "as_of": "2026-08-17",
                        "cases": [
                            {"case_id": "30-a", "model_id": "30", "case_type": "conventional", "already": "here"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            preserved = [
                {"case_id": "30-a", "model_id": "30", "case_type": "conventional", "already": "clobbered"},
            ]
            with patch.object(final_public_evidence, "PUBLIC_INDEX", index_path):
                combined = release._restore_preserved_cases(preserved)

            self.assertEqual(combined["case_count"], 1)
            self.assertEqual(
                [item["already"] for item in combined["cases"] if item["case_id"] == "30-a"],
                ["here"],
            )

    def test_restore_with_no_preserved_cases_is_a_pure_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            index_path = Path(tmp) / "index.json"
            original = {"as_of": "2026-08-17", "cases": [{"case_id": "01-a", "model_id": "01", "case_type": "conventional"}]}
            index_path.write_text(json.dumps(original), encoding="utf-8")
            mtime_before = index_path.stat().st_mtime_ns
            with patch.object(final_public_evidence, "PUBLIC_INDEX", index_path):
                combined = release._restore_preserved_cases([])
            self.assertEqual(combined["cases"], original["cases"])
            self.assertEqual(index_path.stat().st_mtime_ns, mtime_before)


if __name__ == "__main__":
    unittest.main()
