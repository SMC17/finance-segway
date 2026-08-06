"""Tests for the machine-checkable M3 readiness gate.

These deliberately assert the gate's *failure* behaviour as hard as its
success behaviour. A maturity gate that can be talked past is worse than
no gate, so the properties under test are mostly "this cannot be
satisfied by writing a document."
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from verify_m3_readiness import (  # noqa: E402
    CRITERIA,
    check_a_engine_set,
    check_b_stakeholder_lenses,
    check_c_source_register,
    check_e_decision_usefulness,
    check_f_reference_agreement,
    check_g_effective_challenge,
)


class M3GateFailClosedTests(unittest.TestCase):
    def test_undeclared_engine_surfaces_fail(self) -> None:
        # A domain listing twelve required engines without saying where any
        # of them live has written a list, not built twelve engines.
        model = {
            "id": "99",
            "domain": "Test",
            "workbook": "03_Private_Equity/_template_LBO.xlsx",
            "required_engines": ["operating_model", "cash_sweep"],
        }
        result = check_a_engine_set(model)
        self.assertEqual("FAIL", result["status"])
        self.assertIn("no declared workbook surface", result["evidence"])

    def test_engine_pointing_at_absent_sheet_fails(self) -> None:
        model = {
            "id": "99",
            "domain": "Test",
            "workbook": "03_Private_Equity/_template_LBO.xlsx",
            "required_engines": ["operating_model"],
            "engine_surfaces": {"operating_model": "No Such Sheet"},
        }
        result = check_a_engine_set(model)
        self.assertEqual("FAIL", result["status"])
        self.assertIn("declared sheet absent", result["evidence"])

    def test_engine_pointing_at_formula_free_sheet_fails(self) -> None:
        # Pointing an engine at a sheet with no formulas is a declaration
        # without an implementation.
        model = {
            "id": "99",
            "domain": "Test",
            "workbook": "03_Private_Equity/_template_LBO.xlsx",
            "required_engines": ["operating_model"],
            "engine_surfaces": {"operating_model": "Sources"},
        }
        result = check_a_engine_set(model)
        self.assertEqual("FAIL", result["status"])
        self.assertIn("no formulas", result["evidence"])

    def test_engine_set_passes_only_with_real_declared_surfaces(self) -> None:
        model = {
            "id": "99",
            "domain": "Test",
            "workbook": "03_Private_Equity/_template_LBO.xlsx",
            "required_engines": ["operating_model", "cash_sweep"],
            "engine_surfaces": {
                "operating_model": "Operating Model",
                "cash_sweep": "Debt Schedule",
            },
        }
        self.assertEqual("PASS", check_a_engine_set(model)["status"])

    def test_fewer_than_three_perspectives_fails(self) -> None:
        model = {
            "id": "99",
            "domain": "Test",
            "workbook": "03_Private_Equity/_template_LBO.xlsx",
            "required_perspectives": ["sponsor", "lender"],
        }
        result = check_b_stakeholder_lenses(model)
        self.assertEqual("FAIL", result["status"])

    def test_all_perspectives_on_one_sheet_fails(self) -> None:
        # Three lenses pointing at one sheet is one number relabelled.
        model = {
            "id": "99",
            "domain": "Test",
            "workbook": "03_Private_Equity/_template_LBO.xlsx",
            "required_perspectives": ["sponsor", "lender", "management"],
            "perspective_surfaces": {
                "sponsor": "Returns Waterfall",
                "lender": "Returns Waterfall",
                "management": "Returns Waterfall",
            },
        }
        result = check_b_stakeholder_lenses(model)
        self.assertEqual("FAIL", result["status"])
        self.assertIn("distinct outputs", result["evidence"])

    def test_thin_real_data_coverage_fails_source_register(self) -> None:
        model = {"id": "03", "folder": "03_Private_Equity"}
        result = check_c_source_register(model, {"03": 0.035})
        self.assertEqual("FAIL", result["status"])
        self.assertIn("3.5%", result["evidence"])

    def test_undifferentiated_cases_fail_decision_usefulness(self) -> None:
        # If the stress case lands on the same status as the base case, the
        # model does not distinguish them -- that is the exact "thin case"
        # signature the evidence board already tracks.
        model = {"id": "03"}
        status = {
            "03": [
                {"case_type": "conventional", "status": "PASS"},
                {"case_type": "adversarial", "status": "PASS"},
            ]
        }
        result = check_e_decision_usefulness(model, status)
        self.assertEqual("FAIL", result["status"])
        self.assertIn("does not move the decision", result["evidence"])

    def test_single_case_fails_decision_usefulness(self) -> None:
        model = {"id": "30"}
        result = check_e_decision_usefulness(model, {"30": [{"case_type": "conventional", "status": "PASS"}]})
        self.assertEqual("FAIL", result["status"])

    def test_unbound_reference_check_fails(self) -> None:
        model = {"id": "99"}
        result = check_f_reference_agreement(model, set())
        self.assertEqual("FAIL", result["status"])

    def test_human_signoff_gate_cannot_be_satisfied_by_agent_work(self) -> None:
        # Every flagship domain must currently FAIL criterion G. If this
        # ever passes without a real human approval landing in signoff.json,
        # the gate has been compromised.
        for folder, model_id in (
            ("01_Investment_Banking", "01"),
            ("03_Private_Equity", "03"),
            ("05_Private_Credit", "05"),
            ("14_Options_Derivatives", "14"),
        ):
            result = check_g_effective_challenge({"id": model_id, "folder": folder})
            self.assertEqual("FAIL", result["status"], msg=folder)
            self.assertIn("human-only gate", result["evidence"])

    def test_criteria_set_is_complete(self) -> None:
        self.assertEqual(("A", "B", "C", "D", "E", "F", "G", "H"), CRITERIA)


if __name__ == "__main__":
    unittest.main()
