from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font

from tools.workbook_engineering import audit_workbook
from tools.workbook_parity import compare_workbooks, normalize_formula


class WorkbookEngineeringTests(unittest.TestCase):
    def create_book(self, path: Path, formula: str = "=B1+C1") -> None:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Model"
        sheet["B1"] = 1
        sheet["C1"] = 2
        sheet["D1"] = formula
        sheet.freeze_panes = "B2"
        workbook.save(path)

    def test_semantic_parity(self):
        with TemporaryDirectory() as directory:
            left = Path(directory) / "left.xlsx"
            right = Path(directory) / "right.xlsx"
            self.create_book(left)
            self.create_book(right)
            result = compare_workbooks(left, right)
            self.assertTrue(result["semantic_parity"])
            self.assertTrue(result["presentation_parity"])

    def test_formula_drift_has_cell_detail(self):
        with TemporaryDirectory() as directory:
            left = Path(directory) / "left.xlsx"
            right = Path(directory) / "right.xlsx"
            self.create_book(left)
            self.create_book(right, "=B1-C1")
            result = compare_workbooks(left, right)
            self.assertFalse(result["semantic_parity"])
            self.assertIn("Model:cells", result["semantic_differences"])
            self.assertEqual(result["semantic_cell_differences"][0]["cell"], "D1")

    def test_equivalent_formula_serialization(self):
        self.assertEqual(normalize_formula("='VaR'!C5*FALSE()*9E+099"), "=VaR!C5*FALSE*9E99")
        with TemporaryDirectory() as directory:
            left = Path(directory) / "left.xlsx"
            right = Path(directory) / "right.xlsx"
            self.create_book(left, "='VaR'!B1+9E99")
            self.create_book(right, "=VaR!B1+9E+099")
            self.assertTrue(compare_workbooks(left, right)["semantic_parity"])

    def test_presentation_drift_does_not_fail_semantics(self):
        with TemporaryDirectory() as directory:
            left = Path(directory) / "left.xlsx"
            right = Path(directory) / "right.xlsx"
            self.create_book(left)
            self.create_book(right)
            workbook = load_workbook(right)
            workbook["Model"]["D1"].font = Font(bold=True)
            workbook.save(right)
            result = compare_workbooks(left, right)
            self.assertTrue(result["semantic_parity"])
            self.assertFalse(result["presentation_parity"])

    def test_audit_external_and_volatile_formula(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "book.xlsx"
            self.create_book(path, "=OFFSET(B1,0,0)+[other.xlsx]Sheet1!A1")
            _, findings = audit_workbook(path)
            codes = {finding.code for finding in findings}
            self.assertIn("volatile_formula", codes)
            self.assertIn("external_formula_reference", codes)


if __name__ == "__main__":
    unittest.main()
