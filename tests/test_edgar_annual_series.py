"""The annual-series extraction: annual-only, deduped, restatements win."""
from __future__ import annotations

import unittest

from tools.data_fabric.edgar_company_facts import (
    extract_annual_series,
    sector_members,
)


def _facts() -> dict:
    return {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            # FY2022 as originally filed, then restated in the
                            # FY2023 10-K's comparatives: latest filed wins.
                            {"start": "2022-01-01", "end": "2022-12-31",
                             "val": 100, "form": "10-K", "filed": "2023-02-01",
                             "fy": 2022, "fp": "FY"},
                            {"start": "2022-01-01", "end": "2022-12-31",
                             "val": 105, "form": "10-K", "filed": "2024-02-01",
                             "fy": 2023, "fp": "FY"},
                            {"start": "2023-01-01", "end": "2023-12-31",
                             "val": 130, "form": "10-K", "filed": "2024-02-01",
                             "fy": 2023, "fp": "FY"},
                            # A quarterly row carried inside a 10-K filing:
                            # excluded because fp is not FY.
                            {"start": "2023-10-01", "end": "2023-12-31",
                             "val": 40, "form": "10-K", "filed": "2024-02-01",
                             "fy": 2023, "fp": "Q4"},
                            # A 10-Q observation: excluded by form.
                            {"start": "2024-01-01", "end": "2024-03-31",
                             "val": 35, "form": "10-Q", "filed": "2024-05-01",
                             "fy": 2024, "fp": "Q1"},
                        ]
                    }
                },
                "EmptyConcept": {"units": {}},
            }
        }
    }


def _facts_for(rows: list[dict]) -> dict:
    return {"facts": {"us-gaap": {"Revenues": {"units": {"USD": rows}}}}}


class AnnualSeriesTests(unittest.TestCase):
    def test_dedupes_by_year_with_latest_filed_winning(self) -> None:
        rows = extract_annual_series(_facts(), ["Revenues"])
        self.assertEqual(len(rows), 1)
        observations = rows[0]["observations"]
        self.assertEqual(
            [(o["end"], o["value"]) for o in observations],
            [("2022-12-31", 105), ("2023-12-31", 130)],
        )

    def test_quarterly_and_10q_rows_are_excluded(self) -> None:
        rows = extract_annual_series(_facts(), ["Revenues"])
        values = [o["value"] for o in rows[0]["observations"]]
        self.assertNotIn(40, values)
        self.assertNotIn(35, values)

    def test_missing_and_empty_concepts_are_skipped(self) -> None:
        rows = extract_annual_series(_facts(), ["Revenues", "EmptyConcept", "Nope"])
        self.assertEqual([r["concept"] for r in rows], ["Revenues"])


class AnnualSeriesRegressionTests(unittest.TestCase):
    """Each test is a real failure mode the first implementation had."""

    def test_fiscal_year_change_keeps_both_periods(self) -> None:
        # An issuer moving its fiscal year end files two DISTINCT annual
        # periods ending in the same calendar year; both must survive.
        rows = extract_annual_series(_facts_for([
            {"start": "2022-02-01", "end": "2023-01-31", "val": 500,
             "form": "10-K", "filed": "2023-03-15", "fy": 2023, "fp": "FY"},
            {"start": "2023-02-01", "end": "2023-12-31", "val": 460,
             "form": "10-K", "filed": "2024-02-20", "fy": 2023, "fp": "FY"},
        ]), ["Revenues"])
        self.assertEqual(
            [(o["end"], o["value"]) for o in rows[0]["observations"]],
            [("2023-01-31", 500), ("2023-12-31", 460)],
        )

    def test_short_stub_fiscal_year_survives(self) -> None:
        # A spin-off's first fiscal year can be a legitimate 8-month stub -
        # its only annual observation must not be filtered away.
        rows = extract_annual_series(_facts_for([
            {"start": "2022-05-01", "end": "2022-12-31", "val": 900,
             "form": "10-K", "filed": "2023-02-28", "fy": 2022, "fp": "FY"},
        ]), ["Revenues"])
        self.assertEqual(
            [(o["end"], o["value"]) for o in rows[0]["observations"]],
            [("2022-12-31", 900)],
        )

    def test_amended_10ka_restatement_wins(self) -> None:
        # Restatements frequently arrive as 10-K/A - the amendment's value
        # must beat the original, or the stated dedupe rule is a lie.
        rows = extract_annual_series(_facts_for([
            {"start": "2022-01-01", "end": "2022-12-31", "val": 100,
             "form": "10-K", "filed": "2023-02-01", "fy": 2022, "fp": "FY"},
            {"start": "2022-01-01", "end": "2022-12-31", "val": 999,
             "form": "10-K/A", "filed": "2023-06-01", "fy": 2022, "fp": "FY"},
        ]), ["Revenues"])
        self.assertEqual(rows[0]["observations"][0]["value"], 999)
        self.assertEqual(rows[0]["observations"][0]["form"], "10-K/A")

    def test_mistagged_q4_row_loses_to_full_year_sibling(self) -> None:
        # Some filers tag a Q4-duration row fp=FY on the FY end date; the
        # full-year row must win the shared end date by duration.
        rows = extract_annual_series(_facts_for([
            {"start": "2023-01-01", "end": "2023-12-31", "val": 130,
             "form": "10-K", "filed": "2024-02-01", "fy": 2023, "fp": "FY"},
            {"start": "2023-10-01", "end": "2023-12-31", "val": 40,
             "form": "10-K", "filed": "2024-03-01", "fy": 2023, "fp": "FY"},
        ]), ["Revenues"])
        self.assertEqual(rows[0]["observations"][0]["value"], 130)

    def test_instant_concepts_without_start_are_kept(self) -> None:
        facts = {"facts": {"us-gaap": {"Assets": {"units": {"USD": [
            {"end": "2023-12-31", "val": 5000, "form": "10-K",
             "filed": "2024-02-01", "fy": 2023, "fp": "FY"},
        ]}}}}}
        rows = extract_annual_series(facts, ["Assets"])
        self.assertEqual(rows[0]["observations"][0]["value"], 5000)


class SectorMembersTests(unittest.TestCase):
    def test_sector_enumeration_matches_taxonomy(self) -> None:
        import json
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        taxonomy = json.loads(
            (root / "standards" / "universe" / "taxonomy.json").read_text()
        )
        classified = {
            c["symbol"] for c in taxonomy["companies"]
            if c["modelable"] and c.get("sector_id")
        }
        everyone = sector_members()
        self.assertEqual({t for t, _ in everyone}, classified)
        union = set()
        for sector in {c["sector_id"] for c in taxonomy["companies"] if c.get("sector_id")}:
            union.update(t for t, _ in sector_members(sector))
        self.assertEqual(union, classified)
        for _, cik in everyone:
            if cik is not None:
                self.assertEqual(len(cik), 10)

    def test_unknown_sector_returns_empty(self) -> None:
        self.assertEqual(sector_members("no_such_sector"), [])


if __name__ == "__main__":
    unittest.main()
