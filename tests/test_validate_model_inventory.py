"""Regression tests for the M2+ real-verification wiring in validate_model_inventory.

Uses model 08's real inventory entry (a real workbook/builder/folder must exist
for validate_model's filesystem checks to stay quiet) so these tests isolate
the public_case_index behavior, not unrelated filesystem noise.
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from validate_model_inventory import load_inventory, validate_model  # noqa: E402


def _model_08() -> dict:
    data = load_inventory(ROOT / "standards" / "model_inventory.json")
    model = next(m for m in data["models"] if m["id"] == "08")
    return copy.deepcopy(model)


class PublicCaseWiringTests(unittest.TestCase):
    def test_skip_mode_ignores_public_cases(self) -> None:
        result = validate_model(_model_08(), public_case_index=None)
        self.assertFalse(
            [e for e in result.errors if "public case" in e],
            result.errors,
        )

    def test_no_cases_for_model_fails_m2(self) -> None:
        result = validate_model(_model_08(), public_case_index={})
        self.assertTrue(
            any("requires at least one real public case" in e for e in result.errors),
            result.errors,
        )

    def test_all_hard_failures_fails_m2(self) -> None:
        index = {"08": [{"status": "MISSING_WORKBOOK"}, {"status": "RECALC_FAILED"}]}
        result = validate_model(_model_08(), public_case_index=index)
        self.assertTrue(
            any("actually recalculates cleanly" in e for e in result.errors),
            result.errors,
        )

    def test_one_real_status_satisfies_m2(self) -> None:
        index = {"08": [{"status": "MISSING_WORKBOOK"}, {"status": "PASS"}]}
        result = validate_model(_model_08(), public_case_index=index)
        self.assertFalse(
            [e for e in result.errors if "public case" in e],
            result.errors,
        )

    def test_a_concerning_but_real_status_satisfies_m2(self) -> None:
        # BREACH/REVIEW/FAIL are genuine signal from a real recalculation, not
        # a verification-pipeline failure -- the gate cares whether the check
        # actually ran, not what it found.
        index = {"08": [{"status": "BREACH"}]}
        result = validate_model(_model_08(), public_case_index=index)
        self.assertFalse(
            [e for e in result.errors if "public case" in e],
            result.errors,
        )

    def test_other_models_cases_do_not_satisfy_this_model(self) -> None:
        index = {"01": [{"status": "PASS"}]}
        result = validate_model(_model_08(), public_case_index=index)
        self.assertTrue(
            any("requires at least one real public case" in e for e in result.errors),
            result.errors,
        )


class RealRegistryShapeTests(unittest.TestCase):
    """Sanity-check the actual repo data this gate depends on, so a future
    edit to standards/public_cases/index.json that silently drops a domain's
    only case is caught here, not just in a slow, LibreOffice-backed CI job.
    """

    def test_every_declared_m2_plus_model_has_a_public_case_entry(self) -> None:
        inventory = load_inventory(ROOT / "standards" / "model_inventory.json")
        index = json.loads(
            (ROOT / "standards" / "public_cases" / "index.json").read_text(encoding="utf-8")
        )
        case_model_ids = {item["model_id"] for item in index["cases"]}
        missing = [
            model["id"]
            for model in inventory["models"]
            if model["declared_maturity"] in {"M2", "M3", "M4"}
            and model["id"] not in case_model_ids
        ]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
