"""CSV parsing and output shape for the Treasury data-fabric connector.

No network calls: parse_curve/write_outputs are tested against a fixed CSV
fixture, not a live fetch. The live fetch itself is exercised manually
(see the script's module docstring) since a network-dependent test would be
flaky in CI and this repo's policy is public-data-only, not live-data-in-CI.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.data_fabric import treasury_public_facts as tp

FIXTURE_CSV = (
    'Date,"1 Mo","2 Mo","3 Mo","1 Yr","10 Yr","30 Yr"\n'
    "08/17/2026,3.79,3.82,3.87,4.00,4.72,5.31\n"
    "08/14/2026,3.79,3.81,3.86,3.98,4.68,5.25\n"
    "08/13/2026,3.79,3.81,3.87,3.97,4.63,5.21\n"
)

FIXTURE_CSV_WITH_GAP = (
    'Date,"1 Mo","2 Mo"\n'
    "08/17/2026,3.79,N/A\n"
    "08/14/2026,,3.81\n"
)


class ParseCurveTests(unittest.TestCase):
    def test_parses_every_row_and_tenor_column(self) -> None:
        rows = tp.parse_curve(FIXTURE_CSV)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["date"], "2026-08-13")  # sorted ascending
        self.assertEqual(rows[-1]["date"], "2026-08-17")
        self.assertEqual(rows[-1]["tenors"]["10 Yr"], 4.72)
        self.assertEqual(rows[-1]["tenors"]["30 Yr"], 5.31)

    def test_mm_dd_yyyy_converts_to_iso(self) -> None:
        rows = tp.parse_curve(FIXTURE_CSV)
        for row in rows:
            year, month, day = row["date"].split("-")
            self.assertEqual(len(year), 4)
            self.assertEqual(len(month), 2)
            self.assertEqual(len(day), 2)

    def test_blank_and_na_cells_become_none_not_dropped(self) -> None:
        rows = tp.parse_curve(FIXTURE_CSV_WITH_GAP)
        by_date = {r["date"]: r["tenors"] for r in rows}
        self.assertIsNone(by_date["2026-08-17"]["2 Mo"])
        self.assertIsNone(by_date["2026-08-14"]["1 Mo"])
        # The present values on those same rows are NOT dropped alongside
        # the gap -- a missing tenor must not take its row's other tenors
        # down with it.
        self.assertEqual(by_date["2026-08-17"]["1 Mo"], 3.79)
        self.assertEqual(by_date["2026-08-14"]["2 Mo"], 3.81)

    def test_no_header_row_raises_instead_of_returning_empty(self) -> None:
        with self.assertRaises(SystemExit):
            tp.parse_curve("")


class WriteOutputsTests(unittest.TestCase):
    def test_as_of_selects_exactly_one_row(self) -> None:
        rows = tp.parse_curve(FIXTURE_CSV)
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(tp, "ROOT", Path(tmp)), patch.object(tp, "OUT_DIR", Path(tmp)):
                facts_path, reg_path = tp.write_outputs(
                    "daily_treasury_yield_curve", 2026, rows, as_of="2026-08-14"
                )
                payload = json.loads(facts_path.read_text(encoding="utf-8"))
                self.assertEqual(payload["row_count"], 1)
                self.assertEqual(payload["rows"][0]["date"], "2026-08-14")

                reg_text = reg_path.read_text(encoding="utf-8")
                self.assertIn("U.S. Department of the Treasury", reg_text)
                self.assertIn("2026-08-14", reg_text)

    def test_as_of_missing_date_raises_with_available_dates_listed(self) -> None:
        rows = tp.parse_curve(FIXTURE_CSV)
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(tp, "ROOT", Path(tmp)), patch.object(tp, "OUT_DIR", Path(tmp)):
                with self.assertRaises(SystemExit) as ctx:
                    tp.write_outputs("daily_treasury_yield_curve", 2026, rows, as_of="2026-01-01")
                self.assertIn("2026-08-17", str(ctx.exception))

    def test_no_as_of_emits_every_row(self) -> None:
        rows = tp.parse_curve(FIXTURE_CSV)
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(tp, "ROOT", Path(tmp)), patch.object(tp, "OUT_DIR", Path(tmp)):
                facts_path, reg_path = tp.write_outputs(
                    "daily_treasury_yield_curve", 2026, rows, as_of=None
                )
                payload = json.loads(facts_path.read_text(encoding="utf-8"))
                self.assertEqual(payload["row_count"], 3)
                reg_rows = reg_path.read_text(encoding="utf-8").strip().splitlines()
                self.assertEqual(len(reg_rows), 4)  # header + 3 data rows


if __name__ == "__main__":
    unittest.main()
