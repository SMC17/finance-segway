from __future__ import annotations

import unittest

from tools.validate_reconciled_models import validate_sheet_contract


class ReconciledSheetContractTests(unittest.TestCase):
    def test_governed_extension_sheets_are_permitted(self) -> None:
        required = ("Cover", "Assumptions", "Checks", "Sources", "RefreshLog")
        actual = [
            "Cover",
            "Institutional Surface",
            "Challenge Log",
            "Lineage Map",
            "Assumptions",
            "Checks",
            "Sources",
            "RefreshLog",
        ]
        self.assertEqual(validate_sheet_contract(actual, required), [])

    def test_missing_required_sheet_is_rejected(self) -> None:
        errors = validate_sheet_contract(["Cover", "Checks"], ("Cover", "Sources", "Checks"))
        self.assertEqual(errors, ["missing required sheet(s): ['Sources']"])

    def test_required_sheet_reordering_is_rejected(self) -> None:
        errors = validate_sheet_contract(
            ["Cover", "Checks", "Sources"], ("Cover", "Sources", "Checks")
        )
        self.assertTrue(errors[0].startswith("required sheet order mismatch:"))


if __name__ == "__main__":
    unittest.main()
