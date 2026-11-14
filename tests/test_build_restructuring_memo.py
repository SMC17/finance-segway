"""Data-grounding verification for the Distressed & Restructuring memo
deck builder.

Same discipline as tests/test_build_credit_memo.py: every figure the deck
shows must equal the recalculated workbook, and the deck's statement of how
many inputs are real versus declared drivers must equal the manifest.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "builders"))

from pptx import Presentation  # noqa: E402

from recalc import recalc  # noqa: E402
import openpyxl  # noqa: E402

from build_restructuring_memo import build_restructuring_memo, _load_case, _manifest  # noqa: E402


def _slide_text(prs: Presentation) -> list[str]:
    texts = []
    for slide in prs.slides:
        parts = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                parts.append(shape.text_frame.text)
            if shape.has_table:
                for row in shape.table.rows:
                    parts.append(" ".join(cell.text for cell in row.cells))
        texts.append("\n".join(parts))
    return texts


class RestructuringMemoDataGroundingTests(unittest.TestCase):
    CASE_ID = "distressed-public-hertz-2021-reorganization"

    @classmethod
    def setUpClass(cls) -> None:
        cls.output = Path(tempfile.mkdtemp()) / "restructuring-memo-test.pptx"
        build_restructuring_memo(cls.CASE_ID, cls.output)
        cls.prs = Presentation(str(cls.output))
        cls.slide_text = _slide_text(cls.prs)
        cls.full_text = "\n".join(cls.slide_text)

        case = _load_case(cls.CASE_ID)
        src = ROOT / case["output"]
        scratch_dir = tempfile.mkdtemp()
        scratch = Path(scratch_dir) / src.name
        shutil.copyfile(src, scratch)
        result = recalc(str(scratch), timeout=90)
        assert result.get("status") == "success" and not result.get("total_errors", 1), result
        cls.wb = openpyxl.load_workbook(scratch, data_only=True)
        cls.manifest = _manifest(cls.CASE_ID)

    def test_deck_has_expected_slide_count(self) -> None:
        self.assertEqual(len(self.prs.slides), 5)

    def test_deck_states_real_and_driver_counts_from_manifest(self) -> None:
        real_inputs = [
            item for item in self.manifest["inputs"]
            if item.get("input_kind") in {"observed", "derived"}
        ]
        drivers = self.manifest.get("driver_declarations", [])
        self.assertIn(f"{len(real_inputs)} inputs are observed or derived", self.full_text)
        self.assertIn(f"{len(drivers)} are declared drivers", self.full_text)

    def test_every_modeler_assumption_is_a_declared_driver(self) -> None:
        declared = {(d["sheet"], d["cell"]) for d in self.manifest.get("driver_declarations", [])}
        for item in self.manifest["inputs"]:
            if item.get("input_kind") == "modeler_assumption":
                self.assertIn((item["sheet"], item["cell"]), declared)

    def test_dip_commitment_matches_workbook_exactly(self) -> None:
        commitment = self.wb["New Money"]["C5"].value
        self.assertEqual(commitment, 1650.0)
        self.assertIn(f"${commitment:,.1f}mm", self.slide_text[3])

    def test_waterfall_claims_match_workbook(self) -> None:
        waterfall = self.wb["Recovery Waterfall"]
        for row in range(5, 11):
            face = waterfall.cell(row, 3).value or 0
            self.assertIn(f"${face:,.1f}mm", self.slide_text[2])

    def test_realized_outcome_matches_manifest_exactly(self) -> None:
        self.assertEqual(self.manifest["outcome"]["realized"], 1.0)
        self.assertIn("Completed", self.slide_text[4])

    def test_deck_does_not_present_plan_value_as_independent_valuation(self) -> None:
        self.assertIn("not an independent", self.full_text)

    def test_overall_checks_status_matches_workbook(self) -> None:
        checks = self.wb["Decision & Checks"]
        overall = checks["C14"].value
        self.assertIn(f"Overall checks: {overall}", self.slide_text[4])

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.output.parent, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
