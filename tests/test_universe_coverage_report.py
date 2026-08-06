"""The dispatch manifest: inventory only, honest about every hole."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import universe_coverage_report as ucr  # noqa: E402


class CoverageReportTests(unittest.TestCase):
    def test_full_report_accounts_for_every_modelable_company(self) -> None:
        report = ucr.build_report()
        self.assertEqual(
            report["companies_total"],
            report["companies_ready"] + report["companies_with_gaps"],
        )
        self.assertGreaterEqual(report["companies_total"], 100)
        for company in report["companies"]:
            self.assertTrue(company["cik"], company["symbol"])
            self.assertTrue(company["sector_id"], company["symbol"])

    def test_known_gaps_are_reported_not_hidden(self) -> None:
        # HONA and SPCX have no annual filings yet; the manifest must say so
        # rather than presenting them as ready to model.
        report = ucr.build_report()
        gap_symbols = {g["symbol"] for g in report["gaps"]}
        self.assertIn("HONA", gap_symbols)
        self.assertIn("SPCX", gap_symbols)

    def test_non_usd_reporters_are_flagged(self) -> None:
        report = ucr.build_report()
        ccep = next(c for c in report["companies"] if c["symbol"] == "CCEP")
        self.assertTrue(
            any("EUR" in gap for gap in ccep["gaps"]),
            "an EUR reporter mixed unconverted into USD peers is a silent "
            f"modeling error; gaps were: {ccep['gaps']}",
        )

    def test_sector_scope_filters(self) -> None:
        full = ucr.build_report()
        sector = ucr.build_report("utilities")
        self.assertLess(sector["companies_total"], full["companies_total"])
        for company in sector["companies"]:
            self.assertEqual(company["sector_id"], "utilities")

    def test_ready_companies_have_real_depth(self) -> None:
        report = ucr.build_report()
        for company in report["companies"]:
            if company["gaps"]:
                continue
            self.assertGreaterEqual(
                company["series"]["revenue_years"], 5, company["symbol"]
            )


if __name__ == "__main__":
    unittest.main()
