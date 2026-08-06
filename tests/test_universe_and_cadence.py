"""Tests for the universe taxonomy and the quarterly refresh clock."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from build_universe_taxonomy import build as build_taxonomy  # noqa: E402
from quarterly_refresh import (  # noqa: E402
    assess,
    most_recent_reportable_quarter,
    quarter_end,
)
from validate_universe_taxonomy import validate as validate_taxonomy  # noqa: E402

TAXONOMY = ROOT / "standards" / "universe" / "taxonomy.json"


class UniverseTaxonomyTests(unittest.TestCase):
    def test_committed_taxonomy_validates(self) -> None:
        report = validate_taxonomy()
        self.assertEqual("PASS", report["status"], msg=report["errors"])

    def test_builder_is_deterministic(self) -> None:
        # The taxonomy is regenerated from recorded data, so two builds must
        # agree exactly -- otherwise committed output drifts for no reason.
        self.assertEqual(build_taxonomy(), build_taxonomy())

    def test_committed_taxonomy_matches_builder_output(self) -> None:
        self.assertEqual(
            json.loads(TAXONOMY.read_text(encoding="utf-8")),
            build_taxonomy(),
            msg="committed taxonomy is stale -- rerun tools/build_universe_taxonomy.py",
        )

    def test_no_company_carries_an_unsourced_sector(self) -> None:
        # The load-bearing rule: sector assignment is the easiest thing to
        # autofill from apparent obviousness and the hardest to catch once
        # wrong, so it must always carry a citation.
        taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
        for company in taxonomy["companies"]:
            if company.get("sector_id"):
                self.assertTrue(
                    company.get("sector_source"),
                    msg=f"{company.get('symbol')} has a sector with no source",
                )

    def test_validator_rejects_unsourced_sector_assignment(self) -> None:
        taxonomy = build_taxonomy()
        taxonomy["companies"][0]["sector_id"] = taxonomy["sectors"][0]["id"]
        taxonomy["companies"][0]["sector_source"] = None
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "taxonomy.json"
            path.write_text(json.dumps(taxonomy), encoding="utf-8")
            report = validate_taxonomy(path)
        self.assertEqual("FAIL", report["status"])
        self.assertTrue(any("sector_source" in error for error in report["errors"]))

    def test_validator_rejects_a_missing_source_snapshot(self) -> None:
        taxonomy = build_taxonomy()
        taxonomy["universes"][0]["source"]["snapshot"] = "tools/data_fabric/out/does_not_exist.json"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "taxonomy.json"
            path.write_text(json.dumps(taxonomy), encoding="utf-8")
            report = validate_taxonomy(path)
        self.assertEqual("FAIL", report["status"])

    def test_non_operating_positions_are_flagged_not_dropped(self) -> None:
        # Cash and futures are real disclosed positions; dropping them would
        # silently break weight reconciliation, but modeling them as
        # operating companies is nonsense.
        taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
        non_modelable = [c for c in taxonomy["companies"] if not c["modelable"]]
        self.assertTrue(non_modelable)
        for company in non_modelable:
            self.assertTrue(company["not_modelable_reason"])


class QuarterlyClockTests(unittest.TestCase):
    def test_quarter_end_dates(self) -> None:
        self.assertEqual(date(2026, 3, 31), quarter_end(2026, 1))
        self.assertEqual(date(2026, 12, 31), quarter_end(2026, 4))

    def test_filing_lag_prevents_flagging_a_just_ended_quarter(self) -> None:
        # One day after Q1 ends, Q1 filings do not exist yet, so the most
        # recent reportable quarter must still be Q4 of the prior year.
        self.assertEqual((2025, 4), most_recent_reportable_quarter(date(2026, 4, 1)))
        # Well past the lag, Q1 becomes reportable.
        self.assertEqual((2026, 1), most_recent_reportable_quarter(date(2026, 6, 30)))

    def test_pinned_historical_cases_are_not_reported_as_due(self) -> None:
        # Macy's FY2020 does not get "refreshed" to the current quarter.
        report = assess(date(2026, 8, 6))
        self.assertEqual(0, report["refresh_due"])
        self.assertGreater(report["pinned_historical_behind_quarter"], 0)

    def test_universe_becomes_due_once_a_quarter_passes(self) -> None:
        report = assess(date(2027, 3, 1))
        self.assertTrue(
            any(item["universe"] == "qqq" for item in report["universes_due"]),
            msg="QQQ constituents should be due for a re-pull well after capture",
        )

    def test_zero_live_tracking_cases_is_surfaced(self) -> None:
        # Structural finding, not a clean bill of health: a library made
        # entirely of pinned cases has nothing to put on a cadence.
        report = assess(date(2026, 8, 6))
        self.assertEqual(0, report["live_tracking_cases"])


if __name__ == "__main__":
    unittest.main()
