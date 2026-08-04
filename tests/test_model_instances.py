from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from openpyxl import Workbook, load_workbook

from tools.model_instances import apply_manifest


class ModelInstanceTests(unittest.TestCase):
    def create_template(self, root: Path) -> None:
        workbook = Workbook()
        cover = workbook.active
        cover.title = "Cover"
        cover["B4"] = "Last refreshed:"
        cover["C4"] = "[date]"
        cover["B9"] = "Active scenario:"
        cover["C9"] = "Base"
        assumptions = workbook.create_sheet("Assumptions")
        assumptions["C5"] = 100
        assumptions["D5"] = "=C5*2"
        sources = workbook.create_sheet("Sources")
        sources.append([None, "Input", "URL", "As-of", "Notes"])
        refresh = workbook.create_sheet("RefreshLog")
        refresh.append([None, "Date", "Trigger", "What changed", "Reviewer notes", "Next check"])
        workbook.save(root / "template.xlsx")

    def write_manifest(self, root: Path, *, cell: str = "C5") -> Path:
        manifest = {
            "schema_version": "1.0",
            "id": "test-instance",
            "template": "template.xlsx",
            "output": "instances/test.xlsx",
            "as_of": "2026-08-03",
            "scenario": "Downside",
            "inputs": [{
                "sheet": "Assumptions",
                "cell": cell,
                "value": 125,
                "source": {
                    "name": "Test source",
                    "url": "https://example.com/source",
                    "as_of": "2026-08-03",
                    "notes": "Unit-test fixture",
                },
            }],
        }
        path = root / "manifest.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    def test_generate_instance_and_receipt(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_template(root)
            manifest = self.write_manifest(root)
            receipt = apply_manifest(manifest, root)
            output = root / "instances/test.xlsx"
            self.assertTrue(output.exists())
            self.assertEqual(len(receipt["workbook_sha256"]), 64)
            workbook = load_workbook(output, data_only=False)
            self.assertEqual(workbook["Assumptions"]["C5"].value, 125)
            self.assertEqual(workbook["Cover"]["C4"].value, "2026-08-03")
            self.assertEqual(workbook["Cover"]["C9"].value, "Downside")
            self.assertEqual(workbook["Sources"]["C5"].value, "https://example.com/source")
            self.assertTrue(output.with_suffix(".receipt.json").exists())

    def test_formula_override_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_template(root)
            manifest = self.write_manifest(root, cell="D5")
            with self.assertRaisesRegex(ValueError, "refusing to overwrite formula"):
                apply_manifest(manifest, root)

    def test_validate_only_does_not_write(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_template(root)
            manifest = self.write_manifest(root)
            result = apply_manifest(manifest, root, validate_only=True)
            self.assertTrue(result["valid"])
            self.assertFalse((root / "instances/test.xlsx").exists())


if __name__ == "__main__":
    unittest.main()
