import unittest

from openpyxl import Workbook

from tools.builders.formula_compatibility import normalize_workbook_formulas, portable_formula


class FormulaCompatibilityTests(unittest.TestCase):
    def test_normal_distribution_rewrites(self):
        self.assertEqual(
            portable_formula("=NORM.S.DIST(A1,TRUE)"),
            "=NORMSDIST(A1)",
        )
        self.assertEqual(
            portable_formula("=NORM.S.DIST((A1+B1)/C1,FALSE)"),
            "=(EXP(-(((A1+B1)/C1)^2)/2)/SQRT(2*PI()))",
        )
        self.assertEqual(
            portable_formula("=-NORM.S.INV(1-C5)"),
            "=-NORMSINV(1-C5)",
        )

    def test_legacy_statistical_names(self):
        self.assertEqual(
            portable_formula("=STDEV.P(A1:A5)+PERCENTILE.INC(A1:A5,0.05)"),
            "=STDEVP(A1:A5)+PERCENTILE(A1:A5,0.05)",
        )

    def test_nested_norm_calls(self):
        formula = "=NORM.S.DIST(A1,TRUE)-NORM.S.DIST(-A1,TRUE)"
        self.assertEqual(
            portable_formula(formula),
            "=NORMSDIST(A1)-NORMSDIST(-A1)",
        )

    def test_workbook_normalization(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet["A1"] = "=NORM.S.DIST(B1,TRUE)"
        sheet["A2"] = "=NORM.S.INV(B2)"
        sheet["A3"] = "=STDEV.P(B1:B5)"
        self.assertEqual(normalize_workbook_formulas(workbook), 3)
        self.assertEqual(sheet["A1"].value, "=NORMSDIST(B1)")
        self.assertEqual(sheet["A2"].value, "=NORMSINV(B2)")
        self.assertEqual(sheet["A3"].value, "=STDEVP(B1:B5)")


if __name__ == "__main__":
    unittest.main()
