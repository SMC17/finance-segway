"""Golden-path test for the lbo_underwrite L3 agent tool.

Per docs/AGENT_TOOL_CONTRACT.md: fixed inputs -> Checks PASS, plus the
fail-closed paths (missing provenance, unknown Assumptions row label, a
recalculation that doesn't succeed cleanly). Every instance this test
generates is written under a temporary directory inside the repo root
(required so the tool's ROOT-relative manifest paths resolve) and torn
down afterward -- never into 03_Private_Equity/instances/, which is
reserved for source-addressed public cases (see test_real_data_only.py).
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.agents.lbo_underwrite import (
    HOME_DEPOT_MANIFEST_PATH,
    Provenance,
    ToolInput,
    demo,
    home_depot_fixture,
    run,
    validate_provenance,
)

ROOT = Path(__file__).resolve().parents[1]


class LboAgentToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self._tmp.cleanup)
        self.instances_dir = Path(self._tmp.name)

    def make_input(self, **overrides) -> ToolInput:
        today = "2026-08-17"
        base = dict(
            instance_slug="golden_path_test",
            target_name="Golden Path Test Target",
            as_of=today,
            scenario="Base",
            facts={
                "LTM revenue": 1200.0,
                "LTM EBITDA margin": 0.22,
                "Entry EBITDA multiple": 9.5,
                "Exit EBITDA multiple": 9.5,
                "Exit year": 5,
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
                    "LTM revenue", "LTM EBITDA margin", "Entry EBITDA multiple",
                    "Exit EBITDA multiple", "Exit year",
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
        self.assertEqual(result.headline["entry_ebitda_multiple"], 9.5)
        self.assertIsInstance(result.headline["sponsor_moic"], float)
        self.assertIsInstance(result.headline["sponsor_irr"], float)
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

    def test_unknown_assumptions_label_fails_closed(self):
        inp = self.make_input(
            facts={"Not A Real Assumptions Row": 1.0},
            provenance={
                "Not A Real Assumptions Row": Provenance(
                    source_name="x", as_of_date="2026-08-17", retrieval_date="2026-08-17"
                )
            },
        )
        result = run(inp, instances_dir=self.instances_dir)
        self.assertFalse(result.ok)
        self.assertEqual(result.checks_status, "FAIL")
        self.assertIn("unknown Assumptions row label", result.message)

    def test_missing_target_name_fails_closed(self):
        inp = self.make_input(target_name="")
        errors = validate_provenance(inp)
        self.assertIn("missing required fact: target_name", errors)

    def test_no_facts_fails_closed(self):
        inp = self.make_input(facts={}, provenance={})
        errors = validate_provenance(inp)
        self.assertIn("at least one material Assumptions fact is required", errors)

    def test_demo_writes_to_scratch_not_the_real_evidence_corpus(self):
        result = demo()
        self.assertTrue(result.ok, result.message)
        self.assertIn(".agent-tool-scratch", result.workbook_path)
        self.assertNotIn("03_Private_Equity/instances/demo", result.workbook_path)

    def test_exit_year_out_of_range_fails_closed_at_validation(self):
        # An out-of-range exit year doesn't fail loudly in the workbook --
        # it produces #REF! errors in whatever formulas reference the
        # (nonexistent) selected year column, which recalc() then reports
        # as a generic failure far from the real cause. Must be rejected
        # here, before anything gets written.
        inp = self.make_input(facts={**self.make_input().facts, "Exit year": 99})
        inp.provenance["Exit year"] = Provenance(
            source_name="unit test fixture", as_of_date="2026-08-17", retrieval_date="2026-08-17"
        )
        errors = validate_provenance(inp)
        self.assertTrue(any("Exit year must be" in e for e in errors), errors)
        result = run(inp, instances_dir=self.instances_dir)
        self.assertFalse(result.ok)
        self.assertIsNone(result.workbook_path)

    def test_home_depot_fixture_only_submits_facts_with_real_provenance(self):
        # Every fact the fixture submits must carry a real SEC source URL
        # and a transformation note explaining it's a real operating
        # profile reused for a hypothetical LBO wrapper, not a real deal --
        # this fixture must never invent unsourced leverage/multiple/
        # covenant terms and present them as if Home Depot disclosed them.
        inp = home_depot_fixture()
        self.assertEqual(inp.instance_slug, "public_home_depot_lbo_proxy")
        self.assertTrue(inp.facts)
        for label, prov in inp.provenance.items():
            self.assertIn(label, inp.facts)
            self.assertIsNotNone(prov.source_url)
            self.assertIn("sec.gov", prov.source_url)
            self.assertTrue(prov.transformation)
        # Deal-structure terms must NOT be in the submitted facts -- Home
        # Depot's own 10-K cannot disclose an LBO entry multiple or
        # leverage level it never had.
        self.assertNotIn("Entry EBITDA multiple", inp.facts)
        self.assertNotIn("TLB opening leverage", inp.facts)
        self.assertEqual([], validate_provenance(inp))

    def test_home_depot_fixture_reuses_the_committed_public_case(self):
        self.assertTrue(HOME_DEPOT_MANIFEST_PATH.exists())


if __name__ == "__main__":
    unittest.main()
