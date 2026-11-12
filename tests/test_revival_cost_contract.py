"""Regressions for reported-cost accounting and decision sensitivity."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import openpyxl

from tools.recalc import recalc
from tools.verify_template_exhaustion import _formula_override_cells

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / '02_Corporate_Finance/_template_BASE.xlsx'


class ReportedCostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        target = Path(cls.temp.name) / 'synthetic_cost_test.xlsx'
        book = openpyxl.load_workbook(TEMPLATE)
        # Synthetic test inputs, never part of a historical case or receipt.
        for col in 'CDE':
            for row, value in {5:1000, 7:400, 10:300, 13:100,
                               15:50, 17:25, 19:10}.items():
                book['IS'][f'{col}{row}'] = value
        for col in 'CDEF':
            for row, value in {5:0, 6:0.6, 7:0.3, 8:0.1, 9:1,
                               10:0.1, 11:0, 12:10, 13:0.1, 14:0.02}.items():
                book['Assumptions'][f'{col}{row}'] = value
        book.save(target)
        recalc(str(target), force=True)
        cls.values = openpyxl.load_workbook(target, data_only=True)

    def test_reported_costs_reproduce_operating_income_without_double_da(self):
        for col in 'EF':
            self.assertAlmostEqual(300, self.values['IS'][f'{col}14'].value)
            self.assertAlmostEqual(400, self.values['IS'][f'{col}11'].value)
            self.assertAlmostEqual(100, self.values['IS'][f'{col}13'].value)

    def test_bad_discount_growth_order_changes_the_overall_decision(self):
        for domain, filename in (
            ('02_Corporate_Finance', 'public_microsoft_2024.xlsx'),
            ('12_Equity_Finance', 'public_tesla_2020_offering.xlsx'),
        ):
            with self.subTest(domain=domain):
                target = Path(self.temp.name) / filename
                source = ROOT / domain / 'instances' / filename
                shutil.copyfile(source, target)
                book = openpyxl.load_workbook(target)
                book['DCF']['I5'] = 0.01
                book['DCF']['I6'] = 0.02
                book.save(target)
                recalc(str(target), force=True)
                sheet = openpyxl.load_workbook(target, data_only=True)['Decision & Checks']
                rows = {str(sheet.cell(r, 2).value).strip().lower(): r
                        for r in range(1, sheet.max_row + 1)}
                self.assertEqual('FAIL', sheet.cell(rows['discount less terminal growth'], 4).value)
                overall = [r for label, r in rows.items() if 'overall' in label]
                self.assertEqual(1, len(overall))
                self.assertEqual('BREACH', sheet.cell(overall[0], 3).value)



class HistoricalOverrideTests(unittest.TestCase):
    def test_disclosed_historical_override_is_visible_to_the_scanner(self):
        path = ROOT / 'standards/public_cases/corporate-public-microsoft-2024.json'
        manifest = json.loads(path.read_text())
        found = _formula_override_cells(manifest, TEMPLATE)
        self.assertIn(('IS', 'E14'), found)
        self.assertIn(('IS', 'E18'), found)
        self.assertTrue(all(sheet == 'IS' and cell[0] in 'CDE' for sheet, cell in found))

    def test_an_override_flag_cannot_hide_a_missing_sheet_or_an_unsourced_cell(self):
        inputs = [
            {'sheet':'Absent', 'cell':'E14', 'allow_formula_override':True,
             'input_kind':'observed', 'source':{'url':'https://example.org/fixture'}},
            {'sheet':'IS', 'cell':'E14', 'allow_formula_override':True,
             'input_kind':'observed', 'source':{}},
            {'sheet':'IS', 'cell':'E5', 'allow_formula_override':True,
             'input_kind':'observed', 'source':{'url':'https://example.org/fixture'}},
        ]
        self.assertEqual(set(), _formula_override_cells({'inputs':inputs}, TEMPLATE))
