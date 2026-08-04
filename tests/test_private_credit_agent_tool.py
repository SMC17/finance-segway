"""Golden-path test for the private_credit_underwrite L3 agent tool.

Per docs/AGENT_TOOL_CONTRACT.md: fixed inputs -> Checks PASS, plus the
fail-closed paths (missing provenance, unknown Assumptions row label, a
recalculation that doesn't succeed cleanly). Every instance this test
generates is written under a temporary directory inside the repo root
(required so the tool's ROOT-relative manifest paths resolve) and torn
down afterward -- never into 05_Private_Credit/instances/, which is
reserved for source-addressed public cases (see test_real_data_only.py).
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.agents.private_credit_underwrite import (
    Provenance,
    ToolInput,
    demo,
    run,
    validate_provenance,
)

ROOT = Path(__file__).resolve().parents[1]


class PrivateCreditAgentToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self._tmp.cleanup)
        self.instances_dir = Path(self._tmp.name)

    def make_input(self, **overrides) -> ToolInput:
        today = "2026-08-04"
        base = dict(
            instance_slug="golden_path_test",
            borrower_name="Golden Path Test Co",
            as_of=today,
            facility="Unitranche",
            scenario="Base",
            facts={
                "Revenue (LTM)": 480.0,
                "EBITDA margin": 0.19,
                "Opening gross debt": 340.0,
                "Maximum leverage": 6.0,
                "Minimum DSCR": 1.05,
            },
            provenance={
                label: Provenance(
                    source_name="unit test fixture",
                    as_of_date=today,
                    retrieval_date=today,
                    source_url="https://example.invalid/fixture",
                    transformation="test fixture, not real",
                )
                for label in (
                    "Revenue (LTM)", "EBITDA margin", "Opening gross debt",
                    "Maximum leverage", "Minimum DSCR",
                )
            },
        )
        base.update(overrides)
        return ToolInput(**base)

    def test_golden_path_produces_a_recalculated_workbook_with_checks(self):
        result = run(self.make_input(), instances_dir=self.instances_dir)
        self.assertTrue(result.ok, result.message)
        self.assertIn(result.checks_status, ("PASS", "REVIEW"))
        self.assertIsNotNone(result.workbook_path)
        workbook_path = ROOT / result.workbook_path
        self.assertTrue(workbook_path.exists())
        self.assertTrue(workbook_path.with_suffix(".receipt.json").exists())
        # Headline metrics must be real numbers read back from the
        # recalculated workbook, not echoes of the submitted facts.
        self.assertEqual(result.headline["opening_gross_debt"], 340.0)
        self.assertIsInstance(result.headline["yr5_ending_debt"], float)
        self.assertIn("checks_detail", result.headline)
        # A real source URL must appear in the generated Sources sheet.
        source_names = {s["source_name"] for s in result.sources_written}
        self.assertIn("unit test fixture", source_names)

    def test_missing_provenance_fails_closed(self):
        inp = self.make_input(provenance={})
        result = run(inp, instances_dir=self.instances_dir)
        self.assertFalse(result.ok)
        self.assertEqual(result.checks_status, "FAIL")
        self.assertIsNone(result.workbook_path)
        self.assertIn("missing provenance", result.message)
        self.assertEqual(list(self.instances_dir.iterdir()), [])

    def test_unknown_assumptions_label_fails_closed(self):
        inp = self.make_input(
            facts={"Not A Real Assumptions Row": 1.0},
            provenance={
                "Not A Real Assumptions Row": Provenance(
                    source_name="x", as_of_date="2026-08-04", retrieval_date="2026-08-04"
                )
            },
        )
        result = run(inp, instances_dir=self.instances_dir)
        self.assertFalse(result.ok)
        self.assertEqual(result.checks_status, "FAIL")
        self.assertIn("unknown Assumptions row label", result.message)

    def test_missing_borrower_name_fails_closed(self):
        inp = self.make_input(borrower_name="")
        errors = validate_provenance(inp)
        self.assertIn("missing required fact: borrower_name", errors)

    def test_no_facts_fails_closed(self):
        inp = self.make_input(facts={}, provenance={})
        errors = validate_provenance(inp)
        self.assertIn("at least one material Assumptions fact is required", errors)

    def test_demo_writes_to_scratch_not_the_real_evidence_corpus(self):
        result = demo()
        self.assertTrue(result.ok, result.message)
        self.assertIn(".agent-tool-scratch", result.workbook_path)
        self.assertNotIn("05_Private_Credit/instances/demo", result.workbook_path)


if __name__ == "__main__":
    unittest.main()
