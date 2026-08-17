"""Golden-path test for the dcf_comps L3 agent tool.

Per docs/AGENT_TOOL_CONTRACT.md: fixed inputs -> a structurally sound DCF
output, plus the fail-closed paths (missing provenance, unknown label,
out-of-range Comps row, a recalculation that doesn't succeed cleanly).
Every instance this test generates is written under a temporary directory
inside the repo root (required so the tool's ROOT-relative manifest paths
resolve) and torn down afterward -- never into
01_Investment_Banking/instances/, which is reserved for source-addressed
public cases (see test_real_data_only.py).
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.agents.dcf_comps import (
    ADBE_ANNUAL_SERIES,
    Provenance,
    ToolInput,
    adobe_dcf_fixture,
    demo,
    run,
    validate_provenance,
)

ROOT = Path(__file__).resolve().parents[1]


class DcfCompsAgentToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self._tmp.cleanup)
        self.instances_dir = Path(self._tmp.name)

    def make_input(self, **overrides) -> ToolInput:
        today = "2026-08-17"
        facts = {
            "Base revenue (FY0A, $mm)": 1000.0,
            "Revenue growth %": 0.10,
            "Gross margin %": 0.60,
            "Opex % of revenue": 0.35,
            "Tax rate %": 0.21,
            "Diluted shares (mm)": 100.0,
            "WACC %": 0.09,
            "Terminal growth %": 0.025,
        }
        base = dict(
            instance_slug="golden_path_test",
            company_name="Golden Path Test Co",
            as_of=today,
            assumptions_facts=facts,
            provenance={
                f"Assumptions::{label}": Provenance(
                    source_name="unit test fixture", as_of_date=today,
                    retrieval_date=today, source_url="https://example.invalid/fixture",
                    transformation="test fixture, not real",
                )
                for label in facts
            },
        )
        base.update(overrides)
        return ToolInput(**base)

    def test_golden_path_produces_a_recalculated_workbook(self):
        result = run(self.make_input(), instances_dir=self.instances_dir)
        self.assertTrue(result.ok, result.message)
        self.assertEqual(result.checks_status, "PASS")
        self.assertIsNotNone(result.workbook_path)
        workbook_path = ROOT / result.workbook_path
        self.assertTrue(workbook_path.exists())
        self.assertTrue(workbook_path.with_suffix(".receipt.json").exists())
        # DCF/Comps outputs must be real numbers read back from the
        # recalculated workbook, not echoes of the submitted facts.
        self.assertEqual(result.headline["wacc"], 0.09)
        self.assertEqual(result.headline["terminal_growth"], 0.025)
        # Regression coverage: omitting "Base revenue (FY0A, $mm)" left
        # IS!E5 at its 0 default, silently zeroing every projected revenue
        # year (0 * (1+growth) = 0 forever) and cascading to an implied
        # value/share of exactly 0 -- a float, technically, so isinstance
        # alone didn't catch it. Must be strictly positive on real inputs.
        self.assertGreater(result.headline["implied_value_per_share"], 0)
        self.assertGreater(result.headline["enterprise_value"], 0)
        source_names = {s["source_name"] for s in result.sources_written}
        self.assertIn("unit test fixture", source_names)

    def test_wacc_and_terminal_growth_route_to_dcf_not_assumptions(self):
        # Assumptions!C13/C14 exist as labeled rows but no formula in the
        # template reads them -- writing only there would be a silent
        # no-op on the actual discount factor / terminal value. Must land
        # on DCF!I5/I6, the cells the template's own formulas reference.
        import openpyxl

        result = run(self.make_input(), instances_dir=self.instances_dir)
        self.assertTrue(result.ok, result.message)
        wb = openpyxl.load_workbook(ROOT / result.workbook_path, data_only=False)
        self.assertEqual(wb["DCF"]["I5"].value, 0.09)
        self.assertEqual(wb["DCF"]["I6"].value, 0.025)

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
            assumptions_facts={"Not A Real Row": 1.0},
            provenance={
                "Assumptions::Not A Real Row": Provenance(
                    source_name="x", as_of_date="2026-08-17", retrieval_date="2026-08-17"
                )
            },
        )
        result = run(inp, instances_dir=self.instances_dir)
        self.assertFalse(result.ok)
        self.assertIn("unknown Assumptions row label", result.message)

    def test_comps_row_out_of_range_fails_closed(self):
        inp = self.make_input(
            assumptions_facts={},
            provenance={},
            comps_facts={99: {"ticker": "XXX"}},
        )
        inp.provenance["Comps[99]::ticker"] = Provenance(
            source_name="x", as_of_date="2026-08-17", retrieval_date="2026-08-17"
        )
        errors = validate_provenance(inp)
        self.assertTrue(any("out of range" in e for e in errors), errors)

    def test_missing_company_name_fails_closed(self):
        inp = self.make_input(company_name="")
        errors = validate_provenance(inp)
        self.assertIn("missing required fact: company_name", errors)

    def test_no_facts_fails_closed(self):
        inp = self.make_input(assumptions_facts={}, provenance={})
        errors = validate_provenance(inp)
        self.assertIn("at least one Assumptions or Comps fact is required", errors)

    def test_demo_writes_to_scratch_not_the_real_evidence_corpus(self):
        result = demo()
        self.assertTrue(result.ok, result.message)
        self.assertIn(".agent-tool-scratch", result.workbook_path)
        self.assertNotIn("01_Investment_Banking/instances/demo", result.workbook_path)

    def test_adobe_dcf_fixture_only_submits_facts_with_real_provenance(self):
        # Comps facts must be empty -- this fixture deliberately does not
        # attempt to source peer comps data. WACC/terminal growth must be
        # explicitly attributed to repo precedent, never presented as if
        # Adobe itself disclosed a discount rate (no issuer ever does).
        inp = adobe_dcf_fixture()
        self.assertEqual(inp.instance_slug, "public_adobe_dcf_proxy")
        self.assertEqual(inp.comps_facts, {})
        self.assertTrue(inp.assumptions_facts)
        for label, prov in {k.split("::", 1)[1]: v for k, v in inp.provenance.items()}.items():
            self.assertIn(label, inp.assumptions_facts)
            self.assertTrue(prov.transformation)
        wacc_prov = inp.provenance["Assumptions::WACC %"]
        self.assertIn("no issuer discloses", wacc_prov.transformation.lower())
        self.assertEqual([], validate_provenance(inp))

    def test_adobe_dcf_fixture_reuses_already_fetched_xbrl_data(self):
        self.assertTrue(ADBE_ANNUAL_SERIES.exists())


if __name__ == "__main__":
    unittest.main()
