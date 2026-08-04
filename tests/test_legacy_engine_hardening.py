from __future__ import annotations

import json
import unittest

from tools import legacy_engine_oracles
from tools import validate_legacy_engine_hardening


class LegacyEngineHardeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads(
            validate_legacy_engine_hardening.REGISTRY.read_text(encoding="utf-8")
        )
        cls.models = cls.registry["models"]

    def test_exact_six_model_cohort(self):
        ids = {item["model_id"] for item in self.models}
        self.assertEqual(ids, validate_legacy_engine_hardening.EXPECTED_IDS)
        self.assertEqual(ids, set(legacy_engine_oracles.ORACLES))

    def test_validator_passes_before_builder_release(self):
        report = validate_legacy_engine_hardening.validate()
        self.assertEqual(report["status"], "PASS", msg=report["errors"])
        self.assertEqual(report["models"], 6)
        self.assertEqual(report["cases"], 12)

    def test_each_model_has_conventional_and_adversarial_case(self):
        for model in self.models:
            self.assertEqual(len(model["cases"]), 2, msg=model["model_id"])
            self.assertEqual(
                {case["type"] for case in model["cases"]},
                {"conventional", "adversarial"},
                msg=model["model_id"],
            )

    def test_all_financial_identities_pass(self):
        for model in self.models:
            for case in model["cases"]:
                result = legacy_engine_oracles.validate_case(
                    model["model_id"], case["inputs"]
                )
                self.assertEqual(
                    result["identity_status"],
                    "PASS",
                    msg=(
                        f"{model['model_id']} {case['id']} "
                        f"{result['identity_checks']}"
                    ),
                )

    def test_conventional_cases_are_unflagged(self):
        for model in self.models:
            case = next(
                item for item in model["cases"] if item["type"] == "conventional"
            )
            result = legacy_engine_oracles.validate_case(
                model["model_id"], case["inputs"]
            )
            self.assertEqual(
                result["active_risk_flags"],
                [],
                msg=f"{model['model_id']} {case['id']}",
            )

    def test_adversarial_cases_trigger_failure_states(self):
        for model in self.models:
            case = next(
                item for item in model["cases"] if item["type"] == "adversarial"
            )
            result = legacy_engine_oracles.validate_case(
                model["model_id"], case["inputs"]
            )
            self.assertTrue(
                result["active_risk_flags"],
                msg=f"{model['model_id']} {case['id']}",
            )

    def test_release_builder_paths_are_distinct_and_unique(self):
        candidates = [item["candidate_builder"] for item in self.models]
        self.assertEqual(len(candidates), len(set(candidates)))
        for model in self.models:
            self.assertNotEqual(
                model["current_builder"], model["candidate_builder"]
            )
            self.assertTrue(model["required_new_sheets"])
            self.assertTrue(model["reference_checks"])

    def test_claim_boundary_remains_conservative(self):
        claim = self.registry["claim_boundary"]
        self.assertEqual(claim["declared_maturity"], "M2")
        self.assertEqual(claim["m3_promoted"], 0)
        self.assertEqual(claim["m4_promoted"], 0)
        self.assertIs(claim["synthetic_cases_count_toward_m4"], False)


if __name__ == "__main__":
    unittest.main()
