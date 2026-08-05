from __future__ import annotations

import unittest
from unittest.mock import patch

from tools import final_public_evidence
from tools import final_public_evidence_registry
from tools import frontier_evidence_registry


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

    def test_forecast_kind_is_valid_and_explicit(self):
        # final_public_evidence_registry.case() is imported directly from
        # frontier_evidence_registry (not re-exported under a local name), so
        # FORECAST_KINDS lives there too.
        for case in self.cases:
            self.assertIn(
                case["outcome"]["forecast_kind"],
                frontier_evidence_registry.FORECAST_KINDS,
                msg=case["id"],
            )

    def test_each_model_has_genuine_forecast_evidence(self):
        # "recorded" alone isn't enough: a hindsight_restated_fact case (e.g.
        # microsoft-linkedin-2016's "transaction_completed", copied straight
        # from a Form 8-K confirming the merger closed) is "recorded" but
        # demonstrates nothing about prediction. Unlike
        # tools/frontier_evidence_registry.py, this registry has no tracked
        # hindsight-only gap -- every model here already has at least one
        # genuine point_forecast case alongside its hindsight-restated one.
        genuine = {"point_forecast", "same_period_reproduction"}
        for model in self.models:
            self.assertTrue(
                any(case["outcome"]["forecast_kind"] in genuine for case in model["cases"]),
                msg=model["model_id"],
            )

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

    def test_public_outputs_are_declared(self):
        for case in self.cases:
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
        self.assertIs(policy["engineering_test_vectors_count_toward_m4"], False)
        self.assertIn("stakeholder_signoff", policy["m3_requires"])
        self.assertIn("multi_release_outcome_history", policy["m4_requires"])

    def test_final_registry_uses_six_model_validation_contract(self):
        original_path = final_public_evidence.m3_evidence.REGISTRY_PATH
        with patch.object(
            final_public_evidence.m3_evidence,
            "validate",
            return_value={"status": "PASS"},
        ) as validator:
            final_public_evidence._validate_registry(
                final_public_evidence.FINAL_REGISTRY,
                False,
                expected_flagships=6,
            )
        validator.assert_called_once_with(False, expected_flagships=6)
        self.assertEqual(
            final_public_evidence.m3_evidence.REGISTRY_PATH, original_path
        )

    def test_synthetic_benchmark_lineage_is_removed_fail_closed(self):
        manifest = {
            "inputs": [
                {
                    "sheet": "Assumptions",
                    "cell": "C5",
                    "source": {
                        "url": "repo://standards/benchmark_cases/example.json"
                    },
                },
                {
                    "sheet": "Assumptions",
                    "cell": "C6",
                    "source": {"url": "https://www.sec.gov/example"},
                },
            ]
        }
        removed = final_public_evidence._remove_synthetic_lineage(manifest)
        self.assertEqual(removed, 1)
        self.assertEqual(len(manifest["inputs"]), 1)
        self.assertEqual(
            manifest["inputs"][0]["source"]["url"],
            "https://www.sec.gov/example",
        )


if __name__ == "__main__":
    unittest.main()
