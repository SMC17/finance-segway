from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools import validate_hardened_workbooks


class HardenedWorkbookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="finance-segway-hardened-")
        cls.directory = Path(cls.temp.name)
        validate_hardened_workbooks.build_all(cls.directory)
        cls.report = validate_hardened_workbooks.validate_directory(cls.directory)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_all_nine_workbooks_build(self):
        self.assertEqual(
            {path.name for path in self.directory.glob("*.xlsx")},
            {
                contract["filename"]
                for contract in validate_hardened_workbooks.CONTRACTS.values()
            },
        )
        self.assertEqual(len(validate_hardened_workbooks.CONTRACTS), 9)

    def test_all_contracts_pass(self):
        self.assertEqual(self.report["status"], "PASS", msg=self.report["errors"])
        self.assertEqual(self.report["models"], 9)

    def test_release_workbooks_have_nontrivial_formula_depth(self):
        for result in self.report["results"]:
            self.assertGreater(result["formulas"], 20, msg=result)

    def test_no_inventory_promotion_is_implicit(self):
        self.assertIn(
            "required before inventory maturity", self.report["promotion_statement"]
        )


if __name__ == "__main__":
    unittest.main()
