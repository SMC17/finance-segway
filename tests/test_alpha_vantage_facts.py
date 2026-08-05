"""Verify the Alpha Vantage recorder maps fields correctly and writes the
same structured-facts/source_register shape edgar_company_facts.py uses.

Uses synthetic fixture payloads shaped like real Alpha Vantage MCP tool
responses (not a live call -- tests must be deterministic and offline) so a
regression in the field mapping or output shape is caught without needing
network access.
"""
from __future__ import annotations

import csv
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.data_fabric import alpha_vantage_facts as avf  # noqa: E402

# Shaped like a real ARCC BALANCE_SHEET response (values taken from a live
# call made this session; see the module docstring's cross-check note).
BALANCE_SHEET_FIXTURE = {
    "symbol": "ARCC",
    "annualReports": [
        {
            "fiscalDateEnding": "2025-12-31",
            "totalAssets": "31235000000",
            "totalLiabilities": "16917000000",
            "totalShareholderEquity": "14318000000",
            "cashAndCashEquivalentsAtCarryingValue": "638000000",
            "commonStockSharesOutstanding": "718000000",
            "intangibleAssets": "None",
        },
        {
            "fiscalDateEnding": "2024-12-31",
            "totalAssets": "28254000000",
            "totalLiabilities": "14899000000",
            "totalShareholderEquity": "13355000000",
            "cashAndCashEquivalentsAtCarryingValue": "635000000",
            "commonStockSharesOutstanding": "624000000",
        },
    ],
}

CASH_FLOW_FIXTURE = {
    "symbol": "ARCC",
    "annualReports": [
        {
            "fiscalDateEnding": "2025-12-31",
            "operatingCashflow": "1142000000",
            "cashflowFromInvestment": "-2859000000",
            "capitalExpenditures": "0",
        }
    ],
}


class ExtractAnnualTests(unittest.TestCase):
    def test_maps_balance_sheet_fields_to_edgar_concepts(self) -> None:
        rows = avf.extract_annual(BALANCE_SHEET_FIXTURE, "BALANCE_SHEET", fiscal_year="2025-12-31")
        by_field = {row["av_field"]: row for row in rows}
        self.assertEqual(by_field["totalAssets"]["concept"], "Assets")
        self.assertEqual(by_field["totalAssets"]["value"], 31235000000.0)
        self.assertEqual(by_field["totalLiabilities"]["concept"], "Liabilities")
        self.assertEqual(by_field["totalShareholderEquity"]["concept"], "StockholdersEquity")
        self.assertEqual(by_field["totalShareholderEquity"]["value"], 14318000000.0)

    def test_balance_sheet_identity_holds_on_extracted_values(self) -> None:
        # Independent re-derivation, not just trusting the fixture: assets
        # should equal liabilities plus equity for this fixture, the same
        # cross-check that verified the live Alpha Vantage call this session.
        rows = avf.extract_annual(BALANCE_SHEET_FIXTURE, "BALANCE_SHEET", fiscal_year="2025-12-31")
        by_concept = {row["concept"]: row["value"] for row in rows}
        self.assertAlmostEqual(
            by_concept["Assets"], by_concept["Liabilities"] + by_concept["StockholdersEquity"]
        )

    def test_none_values_are_skipped(self) -> None:
        rows = avf.extract_annual(BALANCE_SHEET_FIXTURE, "BALANCE_SHEET", fiscal_year="2025-12-31")
        fields = {row["av_field"] for row in rows}
        self.assertNotIn("intangibleAssets", fields)

    def test_defaults_to_most_recent_fiscal_year(self) -> None:
        rows = avf.extract_annual(BALANCE_SHEET_FIXTURE, "BALANCE_SHEET")
        by_field = {row["av_field"]: row for row in rows}
        self.assertEqual(by_field["totalAssets"]["end"], "2025-12-31")

    def test_unknown_fiscal_year_raises(self) -> None:
        with self.assertRaises(ValueError):
            avf.extract_annual(BALANCE_SHEET_FIXTURE, "BALANCE_SHEET", fiscal_year="1999-12-31")

    def test_cash_flow_fields_keep_their_alpha_vantage_name_as_concept(self) -> None:
        # These are deliberately NOT mapped onto an SEC concept name -- see
        # the module docstring's ARCC operating-cash-flow discrepancy.
        rows = avf.extract_annual(CASH_FLOW_FIXTURE, "CASH_FLOW", fiscal_year="2025-12-31")
        by_field = {row["av_field"]: row for row in rows}
        self.assertEqual(by_field["operatingCashflow"]["concept"], "operatingCashflow")
        self.assertNotIn(by_field["operatingCashflow"]["concept"], avf.AV_TO_EDGAR_CONCEPT.values())


class RecordCompanyFactsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_out_dir = avf.OUT_DIR
        self._tmp = Path(tempfile.mkdtemp())
        avf.OUT_DIR = self._tmp

    def tearDown(self) -> None:
        avf.OUT_DIR = self._orig_out_dir
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_writes_facts_json_and_source_register_csv(self) -> None:
        rows = avf.extract_annual(BALANCE_SHEET_FIXTURE, "BALANCE_SHEET", fiscal_year="2025-12-31")
        facts_path, reg_path = avf.record_company_facts(
            "ARCC", "1287750", rows, statement="BALANCE_SHEET"
        )
        self.assertTrue(facts_path.exists())
        self.assertTrue(reg_path.exists())

        payload = json.loads(facts_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["ticker"], "ARCC")
        self.assertEqual(payload["cik"], "0001287750")
        self.assertEqual(len(payload["facts"]), len(rows))

        with reg_path.open(encoding="utf-8") as f:
            csv_rows = list(csv.DictReader(f))
        self.assertEqual(len(csv_rows), len(rows))
        self.assertEqual(csv_rows[0]["source_name"], "Alpha Vantage MCP (normalized GAAP/IFRS fundamentals)")
        self.assertEqual(csv_rows[0]["as_of_date"], "2025-12-31")

    def test_cash_flow_rows_carry_the_non_mapped_transformation_note(self) -> None:
        rows = avf.extract_annual(CASH_FLOW_FIXTURE, "CASH_FLOW", fiscal_year="2025-12-31")
        _, reg_path = avf.record_company_facts("ARCC", "1287750", rows, statement="CASH_FLOW")
        with reg_path.open(encoding="utf-8") as f:
            csv_rows = list(csv.DictReader(f))
        for row in csv_rows:
            self.assertIn("not cross-mapped", row["transformation"])


if __name__ == "__main__":
    unittest.main()
