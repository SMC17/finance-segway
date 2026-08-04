from __future__ import annotations

import unittest

from tools import frontier_evidence
from tools import frontier_evidence_registry


class FrontierEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = frontier_evidence_registry.registry()
        cls.models = cls.registry["flagships"]

    def test_exact_nine_model_cohort(self):
        self.assertEqual(len(self.models), 9)
        self.assertEqual(
            {model["model_id"] for model in self.models},
            frontier_evidence.EXPECTED_EXPANSION_IDS,
        )

    def test_exact_case_coverage(self):
        cases = [case for model in self.models for case in model["cases"]]
        self.assertEqual(len(cases), 18)
        self.assertEqual(len({case["id"] for case in cases}), 18)
        for model in self.models:
            self.assertEqual(len(model["cases"]), 2, msg=model["model_id"])
            self.assertEqual(
                {case["type"] for case in model["cases"]},
                {"conventional", "adversarial"},
                msg=model["model_id"],
            )

    def test_each_model_has_recorded_outcome(self):
        for model in self.models:
            self.assertTrue(
                any(case["outcome"]["status"] == "recorded" for case in model["cases"]),
                msg=model["model_id"],
            )

    def test_sources_are_external_and_source_addressed(self):
        valid_kinds = {"observed", "derived", "modeler_assumption"}
        for model in self.models:
            external_overrides = 0
            for case in model["cases"]:
                source_names = {source["name"] for source in case["sources"]}
                for source in case["sources"]:
                    self.assertTrue(source["url"].startswith("https://"))
                    self.assertTrue(source["publisher"])
                    self.assertTrue(source["captured_values"])
                for item in case["overrides"]:
                    self.assertIn(item["kind"], valid_kinds)
                    if item["kind"] in {"observed", "derived"}:
                        external_overrides += 1
                        self.assertIn(item["source"], source_names)
            self.assertGreaterEqual(external_overrides, 2, msg=model["model_id"])

    def test_base_manifests_and_outputs_are_unique(self):
        cases = [case for model in self.models for case in model["cases"]]
        self.assertEqual(
            len({case["output"] for case in cases}), len(cases)
        )
        for case in cases:
            self.assertTrue((frontier_evidence.ROOT / case["based_on"]).exists())
            self.assertTrue(case["output"].endswith(".xlsx"))

    def test_claim_boundary_remains_conservative(self):
        policy = self.registry["promotion_policy"]
        self.assertIs(policy["synthetic_cases_count_toward_m4"], False)
        self.assertIn("stakeholder_signoff", policy["m3_requires"])
        self.assertIn("multi_release_outcome_history", policy["m4_requires"])


if __name__ == "__main__":
    unittest.main()
