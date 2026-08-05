from __future__ import annotations

import unittest

from tools import frontier_evidence_registry

EXPECTED_EXPANSION_IDS = {"08", "10", "11", "12", "15", "16", "17", "23", "24"}


class FrontierEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = frontier_evidence_registry.registry()
        cls.models = cls.registry["flagships"]

    def test_exact_nine_model_cohort(self):
        self.assertEqual(len(self.models), 9)
        self.assertEqual(
            {model["model_id"] for model in self.models},
            EXPECTED_EXPANSION_IDS,
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

    def test_forecast_kind_is_valid_and_explicit(self):
        for model in self.models:
            for case in model["cases"]:
                self.assertIn(
                    case["outcome"]["forecast_kind"],
                    frontier_evidence_registry.FORECAST_KINDS,
                    msg=case["id"],
                )

    def test_each_model_has_genuine_forecast_evidence_or_is_tracked(self):
        # "recorded" alone isn't enough: a hindsight_restated_fact case is
        # "recorded" (both values are known) but demonstrates nothing about
        # prediction -- forecast was copied from the same source cited for
        # realized. This requires at least one point_forecast or
        # same_period_reproduction case per model, same intent as
        # test_each_model_has_recorded_outcome but closing the loophole that
        # let 6 hindsight-copied cases look like genuine outcome evidence.
        genuine = {"point_forecast", "same_period_reproduction"}
        for model in self.models:
            has_genuine = any(
                case["outcome"]["forecast_kind"] in genuine for case in model["cases"]
            )
            if model["model_id"] in frontier_evidence_registry.KNOWN_HINDSIGHT_ONLY_MODELS:
                self.assertFalse(
                    has_genuine,
                    msg=(
                        f"{model['model_id']} now has genuine forecast evidence -- "
                        "remove it from KNOWN_HINDSIGHT_ONLY_MODELS"
                    ),
                )
            else:
                self.assertTrue(has_genuine, msg=model["model_id"])

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

    def test_public_outputs_are_unique(self):
        cases = [case for model in self.models for case in model["cases"]]
        self.assertEqual(
            len({case["output"] for case in cases}), len(cases)
        )
        for case in cases:
            self.assertTrue(case["output"].endswith(".xlsx"))

    def test_claim_boundary_remains_conservative(self):
        policy = self.registry["promotion_policy"]
        self.assertIs(policy["engineering_test_vectors_count_toward_m4"], False)
        self.assertIn("stakeholder_signoff", policy["m3_requires"])
        self.assertIn("multi_release_outcome_history", policy["m4_requires"])


if __name__ == "__main__":
    unittest.main()
