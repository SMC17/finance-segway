from __future__ import annotations

import json
import unittest

from tools import release_legacy_engine_promotions


class LegacyEngineReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.specs = release_legacy_engine_promotions.case_specs()
        cls.registry = json.loads(
            release_legacy_engine_promotions.REGISTRY_PATH.read_text(encoding="utf-8")
        )
        cls.inventory = json.loads(
            release_legacy_engine_promotions.INVENTORY_PATH.read_text(encoding="utf-8")
        )

    def test_exact_twelve_case_coverage(self):
        self.assertEqual(len(self.specs), 12)
        by_model = {}
        for spec in self.specs:
            by_model.setdefault(spec["model_id"], []).append(spec)
        self.assertEqual(set(by_model), release_legacy_engine_promotions.EXPECTED_IDS)
        for model_id, cases in by_model.items():
            self.assertEqual(len(cases), 2, msg=model_id)
            self.assertEqual(
                {case["case_type"] for case in cases},
                {"conventional", "adversarial"},
                msg=model_id,
            )

    def test_case_ids_outputs_and_manifests_are_unique(self):
        ids = [spec["id"] for spec in self.specs]
        outputs = [spec["output"] for spec in self.specs]
        manifests = [
            str(release_legacy_engine_promotions.BENCHMARK_DIR / f"{spec['id']}.json")
            for spec in self.specs
        ]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(outputs), len(set(outputs)))
        self.assertEqual(len(manifests), len(set(manifests)))

    def test_every_case_has_source_addressed_non_formula_inputs(self):
        for spec in self.specs:
            self.assertTrue(spec["inputs"], msg=spec["id"])
            for item in spec["inputs"]:
                self.assertIn("sheet", item)
                self.assertIn("cell", item)
                self.assertIn("value", item)
                self.assertNotIn("allow_formula_override", item)
                source = item.get("source") or {}
                self.assertEqual(
                    source.get("url"),
                    "repo://standards/frontier/legacy_engine_registry.json",
                )
                self.assertIn(
                    "Synthetic engineering fixture", source.get("notes", "")
                )

    def test_canonical_paths_and_candidate_builders_align(self):
        inventory_by_id = {item["id"]: item for item in self.inventory["models"]}
        registry_by_id = {
            item["model_id"]: item for item in self.registry["models"]
        }
        self.assertEqual(
            set(registry_by_id), release_legacy_engine_promotions.EXPECTED_IDS
        )
        for model_id, candidate in registry_by_id.items():
            canonical = release_legacy_engine_promotions.CANONICAL_PATHS[model_id]
            self.assertEqual(inventory_by_id[model_id]["workbook"], canonical)
            self.assertEqual(inventory_by_id[model_id]["declared_maturity"], "M2")
            builder_path = (
                release_legacy_engine_promotions.ROOT
                / candidate["candidate_builder"]
            )
            self.assertTrue(builder_path.exists(), msg=str(builder_path))
            self.assertNotEqual(
                candidate["candidate_builder"], candidate["current_builder"]
            )
        for spec in self.specs:
            self.assertEqual(
                spec["template"],
                release_legacy_engine_promotions.CANONICAL_PATHS[spec["model_id"]],
            )

    def test_all_instances_are_synthetic_and_never_m4(self):
        for spec in self.specs:
            manifest = release_legacy_engine_promotions._manifest(spec)
            self.assertEqual(
                manifest["classification"], "synthetic_engineering_benchmark"
            )
            self.assertIs(manifest["counts_toward_M4"], False)
        claim = self.registry["claim_boundary"]
        self.assertEqual(claim["m3_promoted"], 0)
        self.assertEqual(claim["m4_promoted"], 0)
        self.assertIs(claim["synthetic_cases_count_toward_m4"], False)


if __name__ == "__main__":
    unittest.main()
