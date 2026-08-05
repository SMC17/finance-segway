"""The inventory gate must see the forecast registry's forward evidence."""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import validate_model_inventory
from tools.forecast_registration import forward_evidence_by_model

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "standards" / "model_inventory.json"


def _models() -> list[dict]:
    return json.loads(INVENTORY.read_text(encoding="utf-8"))["models"]


class ForwardEvidenceTests(unittest.TestCase):
    def test_committed_registry_groups_by_model(self) -> None:
        evidence = forward_evidence_by_model()
        # Every model_id in the registry maps to a real inventory model.
        inventory_ids = {str(m["id"]) for m in _models()}
        self.assertTrue(set(evidence) <= inventory_ids, set(evidence) - inventory_ids)
        for entry in evidence.values():
            self.assertEqual(
                entry["registered"],
                entry["pending"] + entry["overdue"] + entry["resolved"],
            )

    def test_median_skill_computed_only_from_resolutions(self) -> None:
        evidence = forward_evidence_by_model()
        for entry in evidence.values():
            if entry["resolved"] == 0:
                self.assertIsNone(entry["median_skill_vs_baseline"])
                self.assertEqual(entry["skills"], [])

    def test_inventory_attaches_forward_evidence(self) -> None:
        results, _ = validate_model_inventory.validate_inventory({"models": _models()})
        by_id = {result.model_id: result for result in results}
        evidence = forward_evidence_by_model()
        for model_id, entry in evidence.items():
            self.assertEqual(by_id[model_id].forward_evidence, entry)

    def test_m4_claim_without_resolved_forecast_is_an_error(self) -> None:
        # M4 is defined as demonstrated forward accuracy: a model claiming it
        # with nothing resolved in the registry must fail the gate. Promote
        # model 03 (which has a pending registration but no resolution) and
        # assert the error fires.
        models = [dict(m) for m in _models()]
        for model in models:
            if str(model["id"]) == "03":
                model["declared_maturity"] = "M4"
                model["minimum_instances_for_M4"] = 0
        results, _ = validate_model_inventory.validate_inventory({"models": models})
        by_id = {result.model_id: result for result in results}
        self.assertTrue(
            any("no resolved out-of-sample forecast" in e for e in by_id["03"].errors),
            by_id["03"].errors,
        )

    def test_m4_with_resolved_forecast_passes_the_forward_floor(self) -> None:
        models = [dict(m) for m in _models()]
        for model in models:
            if str(model["id"]) == "03":
                model["declared_maturity"] = "M4"
                model["minimum_instances_for_M4"] = 0
        doctored = forward_evidence_by_model()
        doctored["03"] = dict(
            doctored["03"], resolved=1, pending=0,
            skills=[0.4], median_skill_vs_baseline=0.4,
        )
        with patch.object(
            validate_model_inventory.forecast_registration,
            "forward_evidence_by_model",
            return_value=doctored,
        ):
            results, _ = validate_model_inventory.validate_inventory({"models": models})
        by_id = {result.model_id: result for result in results}
        self.assertFalse(
            any("no resolved out-of-sample forecast" in e for e in by_id["03"].errors),
            by_id["03"].errors,
        )

    def test_overdue_forecasts_surface_as_model_warnings(self) -> None:
        models = _models()
        doctored = forward_evidence_by_model()
        doctored["05"] = dict(doctored["05"], overdue=1, pending=0)
        with patch.object(
            validate_model_inventory.forecast_registration,
            "forward_evidence_by_model",
            return_value=doctored,
        ):
            results, _ = validate_model_inventory.validate_inventory({"models": models})
        by_id = {result.model_id: result for result in results}
        self.assertTrue(
            any("past resolve_by" in w for w in by_id["05"].warnings),
            by_id["05"].warnings,
        )


if __name__ == "__main__":
    unittest.main()
