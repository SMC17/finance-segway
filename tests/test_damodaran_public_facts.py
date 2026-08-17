"""Grid parsing and output shape for the Damodaran data-fabric connector.

No network calls and no binary .xls/.xlsx fixtures needed: rows_from_grid is
a pure function over a list-of-lists, which is exactly what xlrd's
Sheet.cell_value grid and openpyxl's Worksheet.iter_rows both reduce to
(see parse_industry_xls / parse_country_premium_xlsx) -- so the parsing
logic is tested directly against that shape instead of a real workbook.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.data_fabric import damodaran_public_facts as dp

INDUSTRY_GRID = [
    ["Date updated:", 46027.0, ""],
    ["Created by:", "Aswath Damodaran", ""],
    ["", "", ""],
    ["Industry Name", "Number of Firms", "Beta", "Cost of Capital"],
    ["Advertising", 52.0, 1.21, 0.078],
    ["Aerospace/Defense", 79.0, 0.95, 0.076],
    ["", "", "", ""],  # spacer row before a trailing notes block
    ["Total Market", 8500.0, 1.0, 0.08],
]

COUNTRY_GRID = [
    ["Country Risk Premiums"],
    ["Date of update:", "2026-01-01"],
    [],
    ["Country", "Region", "Moody's rating", "Total Equity Risk Premium"],
    ["Abu Dhabi", "Middle East", "Aa2", 0.0487],
    ["Albania", "Eastern Europe & Russia", "Ba3", 0.0889],
    ["United States", "North America", "Aa1", 0.0446],
]


class RowsFromGridTests(unittest.TestCase):
    def test_finds_header_row_past_leading_metadata(self) -> None:
        rows = dp.rows_from_grid(INDUSTRY_GRID, "Industry Name")
        self.assertEqual(len(rows), 3)  # Advertising, Aerospace/Defense, Total Market
        self.assertEqual(rows[0]["Industry Name"], "Advertising")
        self.assertEqual(rows[0]["Beta"], 1.21)

    def test_skips_blank_first_cell_rows(self) -> None:
        rows = dp.rows_from_grid(INDUSTRY_GRID, "Industry Name")
        names = [r["Industry Name"] for r in rows]
        self.assertNotIn("", names)
        self.assertEqual(len(names), 3)

    def test_country_grid_uses_country_as_key(self) -> None:
        rows = dp.rows_from_grid(COUNTRY_GRID, "Country")
        self.assertEqual(len(rows), 3)
        by_country = {r["Country"]: r for r in rows}
        self.assertEqual(by_country["United States"]["Total Equity Risk Premium"], 0.0446)
        self.assertEqual(by_country["Albania"]["Moody's rating"], "Ba3")

    def test_missing_header_raises(self) -> None:
        with self.assertRaises(SystemExit):
            dp.rows_from_grid(INDUSTRY_GRID, "Nonexistent Column")

    def test_short_data_rows_do_not_index_error(self) -> None:
        # A row shorter than the header row (trailing sparse columns in the
        # real sheets) must not crash -- missing trailing cells are just
        # absent from that row's dict, not an IndexError.
        grid = [["Industry Name", "A", "B", "C"], ["Only one", 1]]
        rows = dp.rows_from_grid(grid, "Industry Name")
        self.assertEqual(rows, [{"Industry Name": "Only one", "A": 1}])


class WriteOutputsTests(unittest.TestCase):
    def test_filter_selects_exactly_one_row(self) -> None:
        rows = dp.rows_from_grid(INDUSTRY_GRID, "Industry Name")
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(dp, "ROOT", Path(tmp)), patch.object(dp, "OUT_DIR", Path(tmp)):
                facts_path, reg_path = dp.write_outputs(
                    "wacc", "Cost of capital by industry", "wacc.xls",
                    rows, key_field="Industry Name", filter_value="Advertising",
                )
                payload = json.loads(facts_path.read_text(encoding="utf-8"))
                self.assertEqual(payload["row_count"], 1)
                self.assertEqual(payload["rows"][0]["Industry Name"], "Advertising")
                reg_text = reg_path.read_text(encoding="utf-8")
                self.assertIn("Aswath Damodaran", reg_text)

    def test_filter_is_case_insensitive(self) -> None:
        rows = dp.rows_from_grid(INDUSTRY_GRID, "Industry Name")
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(dp, "ROOT", Path(tmp)), patch.object(dp, "OUT_DIR", Path(tmp)):
                facts_path, _ = dp.write_outputs(
                    "wacc", "Cost of capital by industry", "wacc.xls",
                    rows, key_field="Industry Name", filter_value="advertising",
                )
                payload = json.loads(facts_path.read_text(encoding="utf-8"))
                self.assertEqual(payload["rows"][0]["Industry Name"], "Advertising")

    def test_unmatched_filter_raises_with_examples(self) -> None:
        rows = dp.rows_from_grid(INDUSTRY_GRID, "Industry Name")
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(dp, "ROOT", Path(tmp)), patch.object(dp, "OUT_DIR", Path(tmp)):
                with self.assertRaises(SystemExit) as ctx:
                    dp.write_outputs(
                        "wacc", "Cost of capital by industry", "wacc.xls",
                        rows, key_field="Industry Name", filter_value="Nonexistent Sector",
                    )
                self.assertIn("Advertising", str(ctx.exception))

    def test_no_filter_emits_every_row(self) -> None:
        rows = dp.rows_from_grid(INDUSTRY_GRID, "Industry Name")
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(dp, "ROOT", Path(tmp)), patch.object(dp, "OUT_DIR", Path(tmp)):
                facts_path, reg_path = dp.write_outputs(
                    "wacc", "Cost of capital by industry", "wacc.xls",
                    rows, key_field="Industry Name", filter_value=None,
                )
                payload = json.loads(facts_path.read_text(encoding="utf-8"))
                self.assertEqual(payload["row_count"], 3)
                reg_rows = reg_path.read_text(encoding="utf-8").strip().splitlines()
                self.assertEqual(len(reg_rows), 4)  # header + 3 data rows


class RegionalVariantResolutionTests(unittest.TestCase):
    def test_known_stem_maps_directly(self) -> None:
        self.assertIn("wacc", dp.INDUSTRY_DATASETS)
        filename, _ = dp.INDUSTRY_DATASETS["wacc"]
        self.assertEqual(filename, "wacc.xls")


if __name__ == "__main__":
    unittest.main()
