"""Tests for the template-exhaustion coverage scanner."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from verify_template_exhaustion import (  # noqa: E402
    _cover_real_cells,
    _rgb,
    find_candidate_cells,
    run,
)


class InputColourDetectionTests(unittest.TestCase):
    """The scanner must recognise input blue however openpyxl stored it."""

    class _Colour:
        def __init__(self, rgb: str) -> None:
            self.rgb = rgb

    def test_alpha_channel_does_not_change_the_detected_colour(self) -> None:
        # Regression: the scanner compared full 8-digit aRGB, so the same
        # blue written with a different alpha byte read as a different
        # colour. Domain 31's template stores "FF0000FF" and reported zero
        # candidate input cells -- a silent "nothing to source here" for a
        # whole domain.
        self.assertEqual(_rgb(self._Colour("000000FF")), _rgb(self._Colour("FF0000FF")))

    def test_non_blue_fonts_are_still_rejected(self) -> None:
        blue = _rgb(self._Colour("FF0000FF"))
        for other in ("FF111827", "00FFFFFF", "FF008000"):
            self.assertNotEqual(blue, _rgb(self._Colour(other)), msg=other)

    def test_theme_and_missing_colours_do_not_raise(self) -> None:
        class ThemeColour:
            @property
            def rgb(self):  # openpyxl raises for theme-indexed colours
                raise ValueError("Values must be of type <class 'str'>")

        self.assertIsNone(_rgb(None))
        self.assertIsNone(_rgb(ThemeColour()))

    def test_every_domain_template_exposes_some_input_surface(self) -> None:
        # A template with no detectable input cells is either a template
        # with no inputs (there are none) or a template the scanner cannot
        # read. Both are worth failing on.
        inventory = json.loads(
            (ROOT / "standards" / "model_inventory.json").read_text(encoding="utf-8")
        )
        blind = [
            model["workbook"]
            for model in inventory["models"]
            if not find_candidate_cells(ROOT / model["workbook"])
        ]
        self.assertEqual([], blind)


class TemplateExhaustionTests(unittest.TestCase):
    def test_every_real_manifest_input_is_recognized_as_a_candidate(self) -> None:
        # If the scanner's detection signal misses a styling convention a
        # builder actually uses, a real, sourced manifest input silently
        # doesn't count toward coverage -- this is the regression that
        # motivated dropping the fill-color check in favor of font color
        # alone. Assert it directly rather than just eyeballing the report.
        report = run()
        self.assertEqual([], report["anomalies"])

    def test_coverage_is_a_fraction_and_bounded(self) -> None:
        report = run()
        self.assertGreater(report["cases_measured"], 0)
        for item in report["results"]:
            self.assertGreaterEqual(item["coverage"], 0.0)
            self.assertLessEqual(item["coverage"], 1.0)
            if item["total_candidate_cells"] > 0:
                self.assertAlmostEqual(
                    item["coverage"],
                    item["real_cells"] / item["total_candidate_cells"],
                    places=4,
                )

    def test_single_case_lookup_matches_full_run(self) -> None:
        # --case-id is meant to be a cheap way to re-check one case after
        # deepening it; assert it agrees with the full sweep rather than
        # silently drifting into its own code path.
        full = run()
        home_depot_from_full = next(
            item for item in full["results"] if item["case_id"] == "pe-public-home-depot-2023"
        )
        single = run("pe-public-home-depot-2023")
        self.assertEqual(1, single["cases_measured"])
        self.assertEqual(home_depot_from_full["real_cells"], single["results"][0]["real_cells"])
        self.assertEqual(
            home_depot_from_full["total_candidate_cells"], single["results"][0]["total_candidate_cells"]
        )

    def test_candidate_scan_finds_no_false_positive_from_formula_cells(self) -> None:
        # Spot-check one template directly: no candidate cell should hold
        # a formula (formulas are never a real-data override target --
        # model_instances.py refuses to overwrite them).
        from openpyxl import load_workbook

        template_path = ROOT / "03_Private_Equity" / "_template_LBO.xlsx"
        candidates = find_candidate_cells(template_path)
        workbook = load_workbook(template_path, data_only=False)
        for sheet_name, cells in candidates.items():
            sheet = workbook[sheet_name]
            for coordinate in cells:
                value = sheet[coordinate].value
                self.assertFalse(
                    isinstance(value, str) and value.startswith("="),
                    f"{sheet_name}!{coordinate} is a formula, not a real input candidate",
                )

    def test_cover_sheet_overrides_count_as_real(self) -> None:
        # manifest["cover"] is applied through a different code path
        # (_set_cover, matched by row label) than manifest["inputs"], so
        # without explicit handling these real, case-specific facts (e.g.
        # the actual subject company name) are invisible to coverage.
        manifest = json.loads(
            (ROOT / "standards" / "public_cases" / "pe-public-home-depot-2023.json").read_text()
        )
        self.assertIn("Target / transaction:", manifest["cover"])
        template_path = ROOT / manifest["template"]
        cells = _cover_real_cells(manifest, template_path)
        self.assertIn(("Cover", "C4"), cells)

    def test_always_populated_cover_labels_are_excluded(self) -> None:
        template_path = ROOT / "03_Private_Equity" / "_template_LBO.xlsx"
        manifest = {
            "cover": {
                "Last refreshed:": "2026-01-01",
                "Active scenario:": "Base",
            }
        }
        self.assertEqual(set(), _cover_real_cells(manifest, template_path))

    def test_home_depot_case_counts_cover_field_as_real(self) -> None:
        report = run("pe-public-home-depot-2023")
        item = report["results"][0]
        self.assertEqual(item["by_sheet"]["Cover"]["real"], 1)

    def test_legend_cell_is_excluded(self) -> None:
        template_path = ROOT / "03_Private_Equity" / "_template_LBO.xlsx"
        candidates = find_candidate_cells(template_path)
        self.assertNotIn("B14", candidates.get("Cover", set()))


if __name__ == "__main__":
    unittest.main()
