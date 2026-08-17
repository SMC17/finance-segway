"""Golden-path test for the restructuring_screen L3 agent tool.

Per docs/AGENT_TOOL_CONTRACT.md: fixed inputs -> Decision & Checks status,
plus the fail-closed paths (missing provenance, unknown sheet/label, a
recalculation that doesn't succeed cleanly). Every instance this test
generates is written under a temporary directory inside the repo root
(required so the tool's ROOT-relative manifest paths resolve) and torn
down afterward -- never into 24_Distressed_Restructuring/instances/,
which is reserved for source-addressed public cases (see
test_real_data_only.py).
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.agents.restructuring_screen import (
    HERTZ_MANIFEST_PATH,
    INPUT_SHEETS,
    Provenance,
    ToolInput,
    demo,
    hertz_fixture,
    run,
    validate_provenance,
)

ROOT = Path(__file__).resolve().parents[1]


class RestructuringAgentToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self._tmp.cleanup)
        self.instances_dir = Path(self._tmp.name)

    def make_input(self, **overrides) -> ToolInput:
        today = "2026-08-17"
        base = dict(
            instance_slug="golden_path_test",
            situation_type="Golden Path Test Co. hypothetical Chapter 11",
            as_of=today,
            facts={
                "New Money": {"New-money commitment": 50.0},
                "13-Week Liquidity": {"Initial unrestricted liquidity": 30.0},
                "Recovery Waterfall": {
                    "Total enterprise value available for distribution ($)": 400.0
                },
            },
            provenance={
                "New Money": {
                    "New-money commitment": Provenance(
                        source_name="unit test fixture", as_of_date=today,
                        retrieval_date=today, source_url="https://example.invalid/fixture",
                        transformation="test fixture, not real",
                    )
                },
                "13-Week Liquidity": {
                    "Initial unrestricted liquidity": Provenance(
                        source_name="unit test fixture", as_of_date=today,
                        retrieval_date=today, source_url="https://example.invalid/fixture",
                        transformation="test fixture, not real",
                    )
                },
                "Recovery Waterfall": {
                    "Total enterprise value available for distribution ($)": Provenance(
                        source_name="unit test fixture", as_of_date=today,
                        retrieval_date=today, source_url="https://example.invalid/fixture",
                        transformation="test fixture, not real",
                    )
                },
            },
        )
        base.update(overrides)
        return ToolInput(**base)

    def test_golden_path_produces_a_recalculated_workbook_with_checks(self):
        result = run(self.make_input(), instances_dir=self.instances_dir)
        self.assertTrue(result.ok, result.message)
        self.assertIn(result.checks_status, ("PASS", "REVIEW", "BREACH"))
        self.assertIsNotNone(result.workbook_path)
        workbook_path = ROOT / result.workbook_path
        self.assertTrue(workbook_path.exists())
        self.assertTrue(workbook_path.with_suffix(".receipt.json").exists())
        self.assertEqual(result.headline["enterprise_value_available"], 400.0)
        self.assertIn("checks_detail", result.headline)
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

    def test_unknown_sheet_fails_closed(self):
        inp = self.make_input(
            facts={"Not A Real Sheet": {"x": 1.0}},
            provenance={
                "Not A Real Sheet": {
                    "x": Provenance(source_name="x", as_of_date="2026-08-17", retrieval_date="2026-08-17")
                }
            },
        )
        result = run(inp, instances_dir=self.instances_dir)
        self.assertFalse(result.ok)
        self.assertEqual(result.checks_status, "FAIL")
        self.assertIn("unknown input sheet", result.message)

    def test_unknown_label_fails_closed(self):
        inp = self.make_input(
            facts={"New Money": {"Not A Real Row": 1.0}},
            provenance={
                "New Money": {
                    "Not A Real Row": Provenance(source_name="x", as_of_date="2026-08-17", retrieval_date="2026-08-17")
                }
            },
        )
        result = run(inp, instances_dir=self.instances_dir)
        self.assertFalse(result.ok)
        self.assertIn("unknown row label", result.message)

    def test_missing_situation_type_fails_closed(self):
        inp = self.make_input(situation_type="")
        errors = validate_provenance(inp)
        self.assertIn("missing required fact: situation_type", errors)

    def test_no_facts_fails_closed(self):
        inp = self.make_input(facts={}, provenance={})
        errors = validate_provenance(inp)
        self.assertIn("at least one material fact on an input sheet is required", errors)

    def test_demo_writes_to_scratch_not_the_real_evidence_corpus(self):
        result = demo()
        self.assertTrue(result.ok, result.message)
        self.assertIn(".agent-tool-scratch", result.workbook_path)
        self.assertNotIn("24_Distressed_Restructuring/instances/demo", result.workbook_path)

    def test_hertz_fixture_only_submits_facts_with_real_provenance(self):
        # The fixture must never invent an unsourced capital-structure or
        # recovery-waterfall figure just to make the demonstration denser
        # than the real public case it's reused from.
        inp = hertz_fixture()
        self.assertEqual(inp.instance_slug, "public_hertz_restructuring_proxy")
        self.assertTrue(inp.facts)
        for sheet_name, sheet_facts in inp.facts.items():
            self.assertIn(sheet_name, INPUT_SHEETS)
            for label in sheet_facts:
                prov = inp.provenance[sheet_name][label]
                self.assertIsNotNone(prov.source_url)
                self.assertTrue(prov.transformation)
        self.assertEqual([], validate_provenance(inp))

    def test_hertz_fixture_reuses_the_committed_public_case(self):
        self.assertTrue(HERTZ_MANIFEST_PATH.exists())


if __name__ == "__main__":
    unittest.main()
