"""Guardrails for the committed-workbook recalculation-persistence gate.

Weighted toward negative cases on purpose. The failure this gate exists to
stop is a *silent* one -- a workbook that stores no results reads as clean
to every cached-value scanner in the repository -- so the tests that matter
are the ones proving the gate refuses what it exists to refuse, and that
"nothing to check" never renders as "checked and fine".

The empty-cache fixture is produced the same way the real defect is: by
round-tripping a genuinely recalculated workbook through openpyxl, which
does not evaluate formulas and therefore drops every stored result. That
needs no LibreOffice, so these tests run anywhere.
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook, load_workbook

from tools import verify_recalc_persistence as gate

ROOT = Path(__file__).resolve().parents[1]
CACHED_FIXTURE = ROOT / "15_Commodities" / "instances" / "public_wti_april_2020.xlsx"


class RecalcPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls._tmp.name)

        cls.cached = tmp / "cached.xlsx"
        shutil.copy(CACHED_FIXTURE, cls.cached)

        # The defect, reproduced: same formulas, results dropped.
        cls.stripped = tmp / "stripped.xlsx"
        shutil.copy(CACHED_FIXTURE, cls.stripped)
        load_workbook(cls.stripped, data_only=False).save(cls.stripped)

        cls.no_formulas = tmp / "no_formulas.xlsx"
        book = Workbook()
        book.active["A1"] = 42
        book.save(cls.no_formulas)

        cls.missing = tmp / "not_here.xlsx"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_the_cached_fixture_really_is_cached(self) -> None:
        """A control. Without this the whole suite could pass vacuously.

        If the committed fixture ever loses its stored results, the
        'passes' test below would still pass for the wrong reason -- so
        assert the property that makes this file a valid control, not
        merely that the file exists.
        """
        measured = gate.measure(self.cached)
        self.assertGreater(measured["formulas"], 0, "fixture offers no formulas")
        self.assertGreater(measured["cached"], 0, "fixture stores no results; it cannot serve as the positive control")

    def test_a_workbook_that_stores_results_passes(self) -> None:
        report = gate.assess([self.cached])
        self.assertEqual("PASS", report["status"])
        self.assertEqual(1, report["ok"])
        self.assertEqual(0, report["empty_cache"])

    def test_a_workbook_with_formulas_and_no_results_fails(self) -> None:
        report = gate.assess([self.stripped])
        self.assertEqual("FAIL", report["status"])
        self.assertEqual(1, report["empty_cache"])
        self.assertEqual("empty_cache", report["results"][0]["state"])

    def test_the_two_fixtures_differ_only_in_stored_results(self) -> None:
        """The point of the gate: identical formulas, opposite verdicts.

        This is what makes an empty cache a real finding rather than a
        cosmetic one -- the model is byte-identical and only the evidence
        that it ran is gone.
        """
        cached = gate.measure(self.cached)
        stripped = gate.measure(self.stripped)
        self.assertEqual(cached["formulas"], stripped["formulas"])
        self.assertEqual(0, stripped["cached"])
        self.assertNotEqual(cached["state"], stripped["state"])

    def test_a_workbook_with_no_formulas_is_not_counted_as_verified(self) -> None:
        """Empty subject, stated as such.

        'No errors in a workbook with nothing to evaluate' and 'no errors
        in 300 evaluated cells' must not reach a reader as one number.
        """
        report = gate.assess([self.no_formulas])
        self.assertEqual("no_formulas", report["results"][0]["state"])
        self.assertEqual(0, report["ok"])
        self.assertEqual(1, report["no_formulas"])

    def test_a_missing_workbook_fails_rather_than_being_skipped(self) -> None:
        report = gate.assess([self.missing])
        self.assertEqual("FAIL", report["status"])
        self.assertEqual(1, report["unreadable"])

    def test_the_committed_corpus_passes(self) -> None:
        report = gate.assess()
        self.assertEqual("PASS", report["status"], report["results"])
        self.assertEqual(0, report["empty_cache"])

    def test_the_gate_actually_reads_the_public_case_ledger(self) -> None:
        """Guard against the enumeration silently emptying.

        A gate over zero workbooks passes. Pin that the ledger resolves to
        a real, non-trivial population and that every entry exists.
        """
        workbooks = gate.committed_case_workbooks()
        self.assertGreaterEqual(len(workbooks), 50)
        self.assertTrue(all(path.exists() for path in workbooks))
        self.assertEqual(len(workbooks), len(set(workbooks)))


if __name__ == "__main__":
    unittest.main()
