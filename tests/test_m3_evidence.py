from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import m3_evidence


class M3EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry, cls.inventory = m3_evidence.load()
        cls.inventory_by_id = {model["id"]: model for model in cls.inventory["models"]}

    def test_nine_flagships_and_two_case_types(self):
        self.assertEqual(len(self.registry["flagships"]), 9)
        ids = {model["model_id"] for model in self.registry["flagships"]}
        self.assertEqual(ids, {"03", "04", "09", "14", "18", "19", "20", "21", "22"})
        for model in self.registry["flagships"]:
            self.assertEqual({case["type"] for case in model["cases"]}, {"conventional", "adversarial"})
            self.assertEqual(len(model["cases"]), 2)

    def test_registry_does_not_claim_m3_or_m4(self):
        for model in self.registry["flagships"]:
            inventory_model = self.inventory_by_id[model["model_id"]]
            self.assertEqual(inventory_model["declared_maturity"], "M2")
            self.assertTrue(model["approved_uses"])
            self.assertTrue(model["prohibited_uses"])
            self.assertTrue(model["limitations"])
            self.assertTrue(model["monitoring"])

    def test_case_ids_outputs_and_snapshots_are_unique(self):
        case_ids = []
        outputs = []
        for model in self.registry["flagships"]:
            for case in model["cases"]:
                case_ids.append(case["id"])
                outputs.append(case["output"])
                snapshot = m3_evidence.source_snapshot(model, case)
                expected = snapshot.pop("snapshot_sha256")
                self.assertEqual(expected, m3_evidence.sha256_bytes(m3_evidence.canonical_bytes(snapshot)))
        self.assertEqual(len(case_ids), len(set(case_ids)))
        self.assertEqual(len(outputs), len(set(outputs)))

    def test_all_overrides_have_explicit_provenance_type(self):
        allowed = {"observed", "derived", "modeler_assumption"}
        for model in self.registry["flagships"]:
            for case in model["cases"]:
                source_names = {source["name"] for source in case["sources"]}
                for override in case.get("overrides", []):
                    self.assertIn(override["kind"], allowed)
                    if override["kind"] != "modeler_assumption":
                        self.assertIn(override["source"], source_names)

    def test_public_manifest_reclassifies_synthetic_mapping(self):
        model = next(item for item in self.registry["flagships"] if item["model_id"] == "03")
        case = model["cases"][0]
        snapshot_path = Path(model["folder"]) / "sources" / "snapshots" / f"{case['id']}.json"
        manifest = m3_evidence.build_case_manifest(model, case, m3_evidence.ROOT / snapshot_path)
        self.assertEqual(manifest["classification"], "external_historical_case")
        self.assertFalse(manifest["counts_toward_M4"])
        kinds = {item["input_kind"] for item in manifest["inputs"]}
        self.assertIn("observed", kinds)
        self.assertIn("modeler_assumption", kinds)

    @patch("tools.m3_evidence.fetch_fred_monthly_returns", return_value=[0.01] * 60)
    def test_quant_series_adds_sixty_external_returns(self, mocked):
        model = next(item for item in self.registry["flagships"] if item["model_id"] == "22")
        case = model["cases"][0]
        snapshot_path = m3_evidence.ROOT / model["folder"] / "sources" / "snapshots" / f"{case['id']}.json"
        manifest = m3_evidence.build_case_manifest(model, case, snapshot_path)
        series_inputs = [
            item for item in manifest["inputs"]
            if item["sheet"] == "Backtest" and item["cell"].startswith("C")
        ]
        self.assertGreaterEqual(len(series_inputs), 60)
        self.assertTrue(mocked.called)


if __name__ == "__main__":
    unittest.main()
