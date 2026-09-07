"""Tests for the verdict-closure gate.

Two of these pin mistakes that were made while building it:

  * `test_a_quoted_sheet_name_is_matched` -- a cross-check written during the
    investigation reported that `'Treasury & Liquidity'!` appeared in zero
    formulas, because its pattern handled only the bare form. Sheet names with a
    space or an ampersand are ALWAYS quoted, and check sheets are exactly the
    ones with those names, so a pattern missing that alternative finds nothing
    for the sheets that matter and reports it as absence.

  * `test_a_case_record_missing_its_output_is_not_skipped_as_a_non_case` -- the
    non-case filter must not become a way for a broken case to disappear.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from tools import verify_verdict_closure as gate  # noqa: E402


def workbook(tmp: Path, name: str = "w.xlsx", *, verdicts: int = 3,
             chain: bool = True, extra_sheet: str | None = None) -> Path:
    """A miniature workbook: a verdict sheet reading a bridge sheet reading a model."""
    book = openpyxl.Workbook()
    model = book.active
    model.title = "Model"
    model["C5"] = 100
    bridge = book.create_sheet("Treasury & Liquidity")
    if chain:
        bridge["C5"] = "=Model!C5"
    checks = book.create_sheet("Decision & Checks")
    checks["C5"] = "='Treasury & Liquidity'!C5"
    for index in range(verdicts):
        checks.cell(row=6 + index, column=4).value = f'=IF(C5>{index},"PASS","BREACH")'
    if extra_sheet:
        sheet = book.create_sheet(extra_sheet)
        sheet["C5"] = "=Model!C5*2"
    cover = book.create_sheet("Cover")
    cover["B2"] = "A title, sourced, computing nothing"
    path = tmp / name
    book.save(path)
    return path


def record(path: Path, inputs: list[tuple[str, str]]) -> dict:
    """A case record. A sheet is required only where a NUMBER was sourced, so the
    Cover entry carries prose exactly as the real records do."""
    return {
        "id": "synthetic-case",
        "template": "synthetic/_template.xlsx",
        "output": str(path),
        "inputs": [
            {"sheet": sheet, "cell": cell,
             "value": "A sourced title, not a model input" if sheet == "Cover" else 100.0}
            for sheet, cell in inputs
        ],
    }


class ReferenceMatchingTests(unittest.TestCase):
    def test_a_quoted_sheet_name_is_matched(self):
        found = {(q or b).strip()
                 for q, b in gate.SHEET_REF.findall("='Treasury & Liquidity'!D22-Model!C5")}
        self.assertIn("Treasury & Liquidity", found)
        self.assertIn("Model", found)

    def test_the_pattern_has_not_been_collapsed_to_one_alternative(self):
        """A matcher missing an alternative is invisible while nothing matches it."""
        bare_only = {(q or b).strip()
                     for q, b in gate.SHEET_REF.findall("='Capital Allocation'!D14")}
        self.assertEqual(bare_only, {"Capital Allocation"})


class ClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="closure_test_"))
        self.original_root = gate.ROOT
        gate.ROOT = self.tmp
        self.addCleanup(setattr, gate, "ROOT", self.original_root)

    def test_a_verdict_sheet_is_found_by_what_it_does_not_by_its_name(self):
        book = openpyxl.load_workbook(workbook(self.tmp))
        scanned = gate.scan(book)
        self.assertEqual(gate.verdict_sheets(scanned), ["Decision & Checks"])

    def test_a_sheet_with_too_few_verdicts_does_not_count_as_deciding(self):
        book = openpyxl.load_workbook(workbook(self.tmp, "few.xlsx", verdicts=2))
        self.assertEqual(gate.verdict_sheets(gate.scan(book)), [])

    def test_a_workbook_that_grades_nothing_fails_rather_than_passes(self):
        path = workbook(self.tmp, "novote.xlsx", verdicts=0)
        result = gate.check_case(record(path, [("Model", "C5")]))
        self.assertEqual(result["outcome"], "no_verdict_sheet")
        self.assertNotEqual(result["outcome"], "reachable")

    def test_a_sourced_sheet_reached_transitively_is_inside(self):
        """Decision & Checks -> Treasury & Liquidity -> Model is two hops."""
        path = workbook(self.tmp)
        result = gate.check_case(record(path, [("Model", "C5")]))
        self.assertEqual(result["outcome"], "reachable", result)
        self.assertIn("Model", result["closure"])

    def test_breaking_the_chain_strands_the_sourced_sheet(self):
        """The control for the test above: sever one edge and it must notice.

        This fixture is what exposed the first version's fail-open. Requiring a
        sheet that "computes or is referenced" meant severing the reference
        removed the sheet from the required set, so the defect exempted itself
        and this returned no_sourced_inputs. The requirement now keys on what
        the CASE sourced, which no defect in the workbook can alter.
        """
        path = workbook(self.tmp, "broken.xlsx", chain=False)
        result = gate.check_case(record(path, [("Model", "C5")]))
        self.assertEqual(result["outcome"], "stranded", result)
        self.assertEqual(result["stranded_sheets"], ["Model"])
        self.assertEqual(result["stranded_inputs"], 1)

    def test_a_sheet_sourced_only_with_prose_is_not_required(self):
        """Sourcing a title into a cover page is not a claim about the model."""
        path = workbook(self.tmp)
        result = gate.check_case(record(path, [("Model", "C5"), ("Cover", "B2")]))
        self.assertEqual(result["outcome"], "reachable", result)
        self.assertNotIn("Cover", result["required_sheets"])

    def test_a_case_that_sources_nothing_is_not_counted_as_a_pass(self):
        path = workbook(self.tmp)
        result = gate.check_case(record(path, []))
        self.assertEqual(result["outcome"], "no_sourced_inputs")
        self.assertNotEqual(result["outcome"], "reachable")

    def test_an_unrequired_unreached_sheet_is_reported_but_not_failed_on(self):
        """A sensitivity table nobody sourced into is outside by design."""
        path = workbook(self.tmp, "sens.xlsx", extra_sheet="Sensitivity")
        result = gate.check_case(record(path, [("Model", "C5")]))
        self.assertEqual(result["outcome"], "reachable")
        self.assertIn("Sensitivity", result["unreached_computing_sheets"])


class RecordSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="closure_records_"))
        self.original = gate.CASE_DIR
        gate.CASE_DIR = self.tmp
        self.addCleanup(setattr, gate, "CASE_DIR", self.original)

    def write(self, name: str, payload) -> None:
        (self.tmp / name).write_text(json.dumps(payload), encoding="utf-8")

    def test_an_index_file_is_skipped_rather_than_reported_as_a_broken_case(self):
        self.write("index.json", {"schema_version": "1.0", "cases": ["a", "b"]})
        records, skipped = gate.case_records()
        self.assertEqual(records, [])
        self.assertEqual(skipped, ["index.json"])

    def test_a_case_record_missing_its_output_is_not_skipped_as_a_non_case(self):
        """The non-case filter must not become a hiding place for a broken case."""
        self.write("case.json", {"id": "c", "template": "t.xlsx"})
        records, skipped = gate.case_records()
        self.assertEqual(skipped, [])
        self.assertEqual(len(records), 1)
        self.assertEqual(gate.check_case(records[0])["outcome"], "unreadable")

    def test_unparseable_json_is_reported_not_skipped(self):
        (self.tmp / "bad.json").write_text("{not json", encoding="utf-8")
        records, skipped = gate.case_records()
        self.assertEqual(skipped, [])
        self.assertEqual(gate.check_case(records[0])["outcome"], "unreadable")


class UnknownSheetTests(unittest.TestCase):
    """A requirement must not be able to delete itself.

    No case in the repository sources into a sheet its workbook lacks, which is
    precisely the situation in which a silent filter gets written and never
    revisited. If a sheet is later renamed, dropping the name would mean the
    record still claims the model needs that sheet while the gate quietly stops
    asking -- a fail-open with no symptom.
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="closure_unknown_"))
        self.original = gate.ROOT
        gate.ROOT = self.tmp
        self.addCleanup(setattr, gate, "ROOT", self.original)

    def test_sourcing_into_a_sheet_the_workbook_lacks_fails(self):
        path = workbook(self.tmp)
        result = gate.check_case(record(path, [("Model", "C5"), ("Renamed Model", "C5")]))
        self.assertEqual(result["outcome"], "unreadable")
        self.assertIn("Renamed Model", result["detail"])

    def test_a_prose_only_input_on_an_unknown_sheet_does_not_fail(self):
        """Only a sourced NUMBER is a claim about the model."""
        path = workbook(self.tmp)
        result = gate.check_case(record(path, [("Model", "C5"), ("Cover", "B2")]))
        self.assertEqual(result["outcome"], "reachable", result)
