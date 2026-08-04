from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from openpyxl import Workbook

from tools.workbook_engineering import audit_workbook, compare_workbooks


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
            self.assertTrue(compare_workbooks(left, right)["parity"])

    def test_formula_drift(self):
        with TemporaryDirectory() as directory:
            left = Path(directory) / "left.xlsx"
            right = Path(directory) / "right.xlsx"
            self.create_book(left)
            self.create_book(right, "=B1-C1")
            result = compare_workbooks(left, right)
            self.assertFalse(result["parity"])
            self.assertIn("Model:cells", result["differences"])

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
