from __future__ import annotations

import json
import unittest

from tools import cross_domain_oracles
from tools import validate_frontier_program


class FrontierProgramTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads(
            validate_frontier_program.REGISTRY.read_text(encoding="utf-8")
        )
        cls.engines = cls.registry["cross_domain"]["engines"]

    def test_program_validator_passes(self):
        report = validate_frontier_program.validate()
        self.assertEqual(report["status"], "PASS", msg=report["errors"])
        self.assertEqual(report["inventory_models"], 24)
        self.assertEqual(report["existing_m3_evidence_models"], 9)
        self.assertEqual(report["evidence_expansion_models"], 15)
        self.assertEqual(report["legacy_engine_hardening_models"], 6)
        self.assertEqual(report["cross_domain_engines"], 7)
        self.assertEqual(report["cross_domain_cases"], 14)

    def test_exact_evidence_partition(self):
        cohorts = self.registry["cohorts"]
        existing = set(cohorts["existing_m3_evidence"])
        expansion = set(cohorts["evidence_expansion"])
        self.assertEqual(len(existing), 9)
        self.assertEqual(len(expansion), 15)
        self.assertFalse(existing & expansion)
        self.assertEqual(existing | expansion, {f"{value:02d}" for value in range(1, 25)})

    def test_exact_legacy_engine_backlog(self):
        self.assertEqual(
            set(self.registry["cohorts"]["legacy_engine_hardening"]),
            validate_frontier_program.EXPECTED_LEGACY_IDS,
        )

    def test_exact_cross_domain_oracle_set(self):
        registry_ids = {engine["id"] for engine in self.engines}
        self.assertEqual(registry_ids, validate_frontier_program.EXPECTED_ENGINE_IDS)
        self.assertEqual(registry_ids, set(cross_domain_oracles.ORACLES))

    def test_every_engine_has_conventional_and_adversarial_case(self):
        for engine in self.engines:
            self.assertEqual(len(engine["cases"]), 2, msg=engine["id"])
            self.assertEqual(
                {case["type"] for case in engine["cases"]},
                {"conventional", "adversarial"},
                msg=engine["id"],
            )

    def test_all_financial_identities_pass(self):
        for engine in self.engines:
            for case in engine["cases"]:
                result = cross_domain_oracles.validate_case(
                    engine["id"], case["inputs"]
                )
                self.assertEqual(
                    result["identity_status"],
                    "PASS",
                    msg=f"{engine['id']} {case['id']} {result['identity_checks']}",
                )

    def test_conventional_cases_are_unflagged(self):
        for engine in self.engines:
            case = next(item for item in engine["cases"] if item["type"] == "conventional")
            result = cross_domain_oracles.validate_case(engine["id"], case["inputs"])
            self.assertEqual(
                result["active_risk_flags"], [], msg=f"{engine['id']} {case['id']}"
            )

    def test_adversarial_cases_trigger_failure_states(self):
        for engine in self.engines:
            case = next(item for item in engine["cases"] if item["type"] == "adversarial")
            result = cross_domain_oracles.validate_case(engine["id"], case["inputs"])
            self.assertTrue(
                result["active_risk_flags"], msg=f"{engine['id']} {case['id']}"
            )

    def test_capital_allocator_solves_the_two_constraint_global_optimum(self):
        case = next(
            case
            for engine in self.engines
            if engine["id"] == "capital_allocation"
            for case in engine["cases"]
            if case["type"] == "adversarial"
        )
        result = cross_domain_oracles.capital_allocation(case["inputs"])
        self.assertAlmostEqual(result["allocations"]["liquidity_efficient"], 10.0)
        self.assertAlmostEqual(result["allocations"]["liquidity_hog"], 0.0)
        self.assertAlmostEqual(result["metrics"]["risk_adjusted_value_created"], 90.0)

    def test_contagion_flag_tracks_membership_not_shock_cardinality(self):
        case = next(
            case
            for engine in self.engines
            if engine["id"] == "liquidity_contagion"
            for case in engine["cases"]
            if case["type"] == "adversarial"
        )
        result = cross_domain_oracles.liquidity_contagion(case["inputs"])
        self.assertEqual(result["initially_defaulted_entities"], ["Originator"])
        self.assertEqual(result["propagated_defaulted_entities"], ["Lender"])
        self.assertEqual(result["defaulted_entities"], ["Lender", "Originator"])
        self.assertIn("contagion_propagated", result["active_risk_flags"])

    def test_engineering_vectors_never_count_toward_m4(self):
        claim = self.registry["claim_boundary"]
        self.assertIs(claim["engineering_test_vectors_count_toward_m4"], False)
        self.assertEqual(claim["m3_promoted"], 0)
        self.assertEqual(claim["m4_promoted"], 0)


if __name__ == "__main__":
    unittest.main()
