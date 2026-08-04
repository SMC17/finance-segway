from __future__ import annotations

import json
import unittest

from tools import domain_hardening_oracles
from tools import validate_domain_hardening


class DomainHardeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads(
            validate_domain_hardening.REGISTRY.read_text(encoding="utf-8")
        )
        cls.candidates = json.loads(
            validate_domain_hardening.CANDIDATES.read_text(encoding="utf-8")
        )

    def test_exact_hardening_cohort(self):
        ids = {item["model_id"] for item in self.registry["domains"]}
        self.assertEqual(ids, validate_domain_hardening.EXPECTED_M1_IDS)
        self.assertEqual(ids, set(domain_hardening_oracles.ORACLES))

    def test_each_domain_has_two_distinct_case_types(self):
        for domain in self.registry["domains"]:
            self.assertEqual(len(domain["cases"]), 2)
            self.assertEqual(
                {case["type"] for case in domain["cases"]},
                {"conventional", "adversarial"},
            )

    def test_all_case_identities_pass(self):
        for domain in self.registry["domains"]:
            for case in domain["cases"]:
                result = domain_hardening_oracles.validate_case(
                    domain["model_id"], case["inputs"]
                )
                self.assertEqual(
                    result["identity_status"],
                    "PASS",
                    msg=(
                        f"{domain['model_id']} {case['id']} "
                        f"{result['identity_checks']}"
                    ),
                )

    def test_adversarial_cases_trigger_risk(self):
        for domain in self.registry["domains"]:
            adversarial = next(
                case
                for case in domain["cases"]
                if case["type"] == "adversarial"
            )
            result = domain_hardening_oracles.validate_case(
                domain["model_id"], adversarial["inputs"]
            )
            self.assertTrue(
                result["active_risk_flags"], msg=adversarial["id"]
            )

    def test_conventional_cases_are_unflagged(self):
        for domain in self.registry["domains"]:
            conventional = next(
                case
                for case in domain["cases"]
                if case["type"] == "conventional"
            )
            result = domain_hardening_oracles.validate_case(
                domain["model_id"], conventional["inputs"]
            )
            self.assertEqual(
                result["active_risk_flags"], [], msg=conventional["id"]
            )

    def test_registry_validation_matches_release_phase(self):
        report = validate_domain_hardening.validate()
        self.assertEqual(report["status"], "PASS", msg=report["errors"])
        self.assertEqual(report["domains"], 9)
        self.assertEqual(report["cases"], 18)
        promotion_validated = (
            self.candidates["status"]
            == validate_domain_hardening.VALIDATED_PROMOTION_STATUS
        )
        expected_maturity = "M2" if promotion_validated else "M1"
        expected_integration = (
            "validated" if promotion_validated else "pending"
        )
        self.assertEqual(report["expected_maturity"], expected_maturity)
        self.assertTrue(
            all(
                result["declared_maturity"] == expected_maturity
                for result in report["results"]
            )
        )
        self.assertTrue(
            all(
                result["workbook_integration"] == expected_integration
                for result in report["results"]
            )
        )


if __name__ == "__main__":
    unittest.main()
