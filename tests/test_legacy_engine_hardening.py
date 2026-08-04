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

    def test_validator_passes_for_current_release_phase(self):
        report = validate_legacy_engine_hardening.validate()
        self.assertEqual(report["status"], "PASS", msg=report["errors"])
        self.assertEqual(report["models"], 6)
        self.assertEqual(report["cases"], 12)
        self.assertEqual(report["release_status"], self.registry.get("status", "planned"))
        expected_count = (
            2
            if report["release_status"]
            == validate_legacy_engine_hardening.RELEASE_APPLIED
            else 0
        )
        self.assertEqual(set(report["benchmark_counts"].values()), {expected_count})

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

    def test_inventory_builder_matches_release_phase(self):
        inventory = json.loads(
            validate_legacy_engine_hardening.INVENTORY.read_text(encoding="utf-8")
        )
        inventory_by_id = {item["id"]: item for item in inventory["models"]}
        status = self.registry.get("status", "planned")
        candidate_active = status in {
            validate_legacy_engine_hardening.RELEASE_STAGED,
            validate_legacy_engine_hardening.RELEASE_APPLIED,
        }
        for model in self.models:
            expected = (
                model["candidate_builder"]
                if candidate_active
                else model["current_builder"]
            )
            self.assertEqual(inventory_by_id[model["model_id"]]["builder"], expected)

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
