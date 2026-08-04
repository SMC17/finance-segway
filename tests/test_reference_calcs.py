from __future__ import annotations

import unittest
from unittest.mock import patch

from openpyxl import Workbook

from tools import verify_reference_calcs


class VentureCapitalReferenceCalcTests(unittest.TestCase):
    def test_vc_oracle_targets_the_institutional_workbook_contract(self):
        def recalculate(_path, populate):
            workbook = Workbook()
            workbook.remove(workbook.active)
            ownership = workbook.create_sheet("Ownership & Dilution")
            waterfall = workbook.create_sheet("Exit Waterfall")
            populate(workbook)

            pre_money = ownership["C5"].value
            investment = ownership["C6"].value
            existing = ownership["C7"].value
            new = ownership["C8"].value
            option_pool = ownership["C9"].value
            total_shares = existing + new + option_pool
            investor_ownership = new / total_shares
            founder_ownership = existing / total_shares
            pool_ownership = option_pool / total_shares

            ownership["C15"] = pre_money + investment
            ownership["C16"] = total_shares
            ownership["C17"] = investor_ownership
            ownership["C18"] = founder_ownership
            ownership["C19"] = pool_ownership
            ownership["C20"] = investment / new
            waterfall["C11"] = investor_ownership
            waterfall["C12"] = waterfall["C5"].value * investor_ownership
            waterfall["C13"] = waterfall["C12"].value / waterfall["C6"].value
            return workbook

        with patch.object(
            verify_reference_calcs, "with_recalc", side_effect=recalculate
        ):
            name, passed, details = (
                verify_reference_calcs.check_vc_waterfall_conservation()
            )

        self.assertEqual(
            name, "VC: ownership, pricing, and exit-proceeds identities"
        )
        self.assertTrue(passed, details)
        self.assertIn("ownership_sum=1.0", details)


if __name__ == "__main__":
    unittest.main()
