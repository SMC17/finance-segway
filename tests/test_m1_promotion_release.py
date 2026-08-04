from __future__ import annotations

import json
import unittest

from tools import release_m1_domain_promotions


class M1PromotionReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.specs = release_m1_domain_promotions.case_specs()
        cls.inventory = json.loads(
            release_m1_domain_promotions.INVENTORY_PATH.read_text(encoding="utf-8")
        )
        cls.candidates = json.loads(
            release_m1_domain_promotions.CANDIDATE_PATH.read_text(encoding="utf-8")
        )

    def test_exact_case_coverage(self):
        self.assertEqual(len(self.specs), 18)
        by_model = {}
        for spec in self.specs:
            by_model.setdefault(spec["model_id"], []).append(spec)
        self.assertEqual(set(by_model), release_m1_domain_promotions.EXPECTED_IDS)
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
            str(release_m1_domain_promotions.BENCHMARK_DIR / f"{spec['id']}.json")
            for spec in self.specs
        ]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(outputs), len(set(outputs)))
        self.assertEqual(len(manifests), len(set(manifests)))

    def test_every_case_has_source_addressed_non_formula_inputs(self):
        for spec in self.specs:
            self.assertTrue(spec["inputs"], msg=spec["id"])
            for input_item in spec["inputs"]:
                self.assertIn("sheet", input_item)
                self.assertIn("cell", input_item)
                self.assertIn("value", input_item)
                self.assertNotIn("allow_formula_override", input_item)
                source = input_item.get("source") or {}
                self.assertEqual(
                    source.get("url"),
                    "repo://standards/domain_hardening/m1_registry.json",
                )
                self.assertIn("Synthetic engineering fixture", source.get("notes", ""))

    def test_candidate_builders_and_inventory_paths_align(self):
        inventory_by_id = {item["id"]: item for item in self.inventory["models"]}
        candidate_by_id = {
            item["model_id"]: item for item in self.candidates["candidates"]
        }
        self.assertEqual(set(candidate_by_id), release_m1_domain_promotions.EXPECTED_IDS)
        for spec in self.specs:
            model = inventory_by_id[spec["model_id"]]
            candidate = candidate_by_id[spec["model_id"]]
            self.assertEqual(spec["template"], model["workbook"])
            self.assertTrue(candidate["candidate_builder"].endswith("_release.py"))
            self.assertTrue(candidate["reference_checks"])

    def test_release_does_not_claim_m3_or_m4(self):
        self.assertEqual(self.candidates["target_maturity"], "M2")
        self.assertNotIn("M3", self.candidates["status"])
        for spec in self.specs:
            self.assertTrue(spec["output"].endswith(".xlsx"))


if __name__ == "__main__":
    unittest.main()
