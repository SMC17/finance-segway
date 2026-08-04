from __future__ import annotations

import unittest

from tools import final_public_evidence
from tools import final_public_evidence_registry


class FinalPublicEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = final_public_evidence_registry.registry()
        cls.models = cls.registry["flagships"]
        cls.cases = [case for model in cls.models for case in model["cases"]]

    def test_exact_final_six_model_cohort(self):
        self.assertEqual(len(self.models), 6)
        self.assertEqual(
            {model["model_id"] for model in self.models},
            final_public_evidence.EXPECTED_FINAL_IDS,
        )

    def test_exact_twelve_case_coverage(self):
        self.assertEqual(len(self.cases), 12)
        self.assertEqual(len({case["id"] for case in self.cases}), 12)
        self.assertEqual(len({case["output"] for case in self.cases}), 12)
        for model in self.models:
            self.assertEqual(len(model["cases"]), 2, msg=model["model_id"])
            self.assertEqual(
                {case["type"] for case in model["cases"]},
                {"conventional", "adversarial"},
                msg=model["model_id"],
            )

    def test_each_model_has_recorded_outcomes(self):
        for model in self.models:
            recorded = [
                case
                for case in model["cases"]
                if case["outcome"]["status"] == "recorded"
            ]
            self.assertGreaterEqual(len(recorded), 1, msg=model["model_id"])

    def test_external_sources_and_typed_overrides(self):
        valid_kinds = {"observed", "derived", "modeler_assumption"}
        for model in self.models:
            external = 0
            for case in model["cases"]:
                names = {source["name"] for source in case["sources"]}
                for source in case["sources"]:
                    self.assertTrue(source["url"].startswith("https://"))
                    self.assertTrue(source["publisher"])
                    self.assertTrue(source["captured_values"])
                for item in case["overrides"]:
                    self.assertIn(item["kind"], valid_kinds)
                    if item["kind"] in {"observed", "derived"}:
                        external += 1
                        self.assertIn(item["source"], names)
            self.assertGreaterEqual(external, 2, msg=model["model_id"])

    def test_base_manifests_exist(self):
        for case in self.cases:
            self.assertTrue((final_public_evidence.ROOT / case["based_on"]).exists())
            self.assertTrue(case["output"].endswith(".xlsx"))

    def test_all_domain_partition_is_exact(self):
        self.assertEqual(
            final_public_evidence.EXPECTED_ORIGINAL_IDS
            | final_public_evidence.EXPECTED_FRONTIER_IDS
            | final_public_evidence.EXPECTED_FINAL_IDS,
            final_public_evidence.EXPECTED_ALL_IDS,
        )
        self.assertFalse(
            final_public_evidence.EXPECTED_ORIGINAL_IDS
            & final_public_evidence.EXPECTED_FRONTIER_IDS
        )
        self.assertFalse(
            final_public_evidence.EXPECTED_FINAL_IDS
            & (
                final_public_evidence.EXPECTED_ORIGINAL_IDS
                | final_public_evidence.EXPECTED_FRONTIER_IDS
            )
        )

    def test_claim_boundary_remains_conservative(self):
        policy = self.registry["promotion_policy"]
        self.assertIs(policy["synthetic_cases_count_toward_m4"], False)
        self.assertIn("stakeholder_signoff", policy["m3_requires"])
        self.assertIn("multi_release_outcome_history", policy["m4_requires"])


if __name__ == "__main__":
    unittest.main()
