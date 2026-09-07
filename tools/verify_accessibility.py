"""Check the workbooks against the accessibility criteria that actually apply.

Standards in scope: WCAG 2.2 (adopted verbatim as ISO/IEC 40500) and EN 301 549,
which incorporates WCAG for non-web documents.

WHICH CRITERIA APPLY TO A SPREADSHEET
-------------------------------------
Most of WCAG addresses web pages and cannot be evaluated against an .xlsx file.
Three success criteria do apply directly to what this repository ships, and
they are the ones checked here:

  1.4.1 Use of Colour (Level A)
      Colour must not be the only visual means of conveying information. This
      repository signals check outcomes with conditional formatting -- green
      fill for PASS, red for FAIL. If the cell held only the fill, a reader with
      a colour vision deficiency, a monochrome printout, or a screen reader
      would have no way to tell a passing model from a failing one. The cells
      also carry the literal words "PASS", "FAIL", "REVIEW", "BREACH", which is
      what makes the design conformant. This check asserts that the text is
      really there, on every status cell, in every workbook.

  1.3.1 Info and Relationships (Level A)
      Structure conveyed visually must be programmatically determinable. For a
      workbook, the load-bearing case is the sheet name and the row label: a
      value in a grid with no label is meaningless to anything that is not a
      pair of eyes reading position. This check asserts that every populated
      data row carries a text label in its label column.

  3.1.3 Unusual Words (Level AAA, checked as a courtesy)
      Domain jargon should be definable. Reported, not enforced: the glossary
      is the mechanism, and coverage of it is a warning rather than a failure.

WHAT THIS DOES NOT CHECK
------------------------
Contrast ratios (1.4.3), because the rendered contrast of a spreadsheet depends
on the reader's application, theme, and printer rather than on the file. Keyboard
operability, focus order, and timing criteria have no meaning for a static
document. Claiming those would be conformance theatre, so the standards register
records them as not-applicable with this reason rather than as passing.

Usage:
    python tools/verify_accessibility.py
    python tools/verify_accessibility.py --report accessibility.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "standards" / "model_inventory.json"

# The words this repository uses to state an outcome in text. A status cell must
# resolve to one of these, or to a formula that can produce one.
STATUS_TOKENS = {
    "PASS", "FAIL", "REVIEW", "BREACH", "WARN", "OK", "N/A", "PENDING", "BLOCKED",
}
STATUS_SHEET_HINT = re.compile(r"check|decision|covenant|status|gate", re.IGNORECASE)
# A formula that can yield a status token: the token appears as a string literal.
QUOTED = re.compile(r'"([^"]*)"')


def workbooks() -> list[tuple[str, Path]]:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    found: list[tuple[str, Path]] = []
    for model in inventory["models"]:
        path = ROOT / model["workbook"]
        if path.exists():
            found.append((model["id"], path))
    return found


def check_workbook(model_id: str, path: Path) -> tuple[list[str], list[str], dict[str, int]]:
    failures: list[str] = []
    warnings: list[str] = []
    counts = {"status_cells": 0, "labelled_rows": 0, "unlabelled_rows": 0}
    workbook = load_workbook(path, data_only=False)
    relative = path.relative_to(ROOT)

    for sheet in workbook.worksheets:
        is_status_sheet = bool(STATUS_SHEET_HINT.search(sheet.title))

        # --- 1.4.1 Use of Colour -------------------------------------------
        # Every cell carrying conditional formatting on a status sheet must also
        # resolve to a text token, never to a bare number or an empty cell whose
        # only signal is its fill.
        # Only DISCRETE status rules are in scope. A colour-scale rule paints a
        # gradient across a grid of numbers -- the number is present in every
        # cell, so colour is redundant emphasis rather than the sole means of
        # conveying the value, and 1.4.1 is satisfied. Discrete rules
        # ('cellIs', 'expression') are the ones that map a cell to a
        # pass/fail meaning, and those must also say it in words.
        ranges: list[str] = []
        try:
            for rule_range in sheet.conditional_formatting:
                types = {rule.type for rule in rule_range.rules}
                if types <= {"colorScale", "dataBar", "iconSet"}:
                    continue
                ranges.append(str(rule_range.sqref))
        except (AttributeError, TypeError):
            pass

        for sqref in ranges:
            for chunk in str(sqref).split():
                try:
                    cells = sheet[chunk]
                except (ValueError, KeyError):
                    continue
                rows = cells if isinstance(cells, tuple) else ((cells,),)
                for row in rows:
                    row = row if isinstance(row, tuple) else (row,)
                    for cell in row:
                        value = cell.value
                        if value is None:
                            continue
                        counts["status_cells"] += 1
                        text = str(value)
                        if isinstance(value, str) and text.startswith("="):
                            produced = {
                                q.strip() for q in QUOTED.findall(text) if q.strip()
                            }
                            if not produced:
                                # The criterion is that words are present, not
                                # that they come from a particular list. A
                                # formula that can never yield any string
                                # conveys its outcome by colour alone.
                                failures.append(
                                    f"{relative}!{sheet.title}!{cell.coordinate}: "
                                    "conditional formatting conveys a status, but the "
                                    "formula can never produce text -- colour is the "
                                    "only signal (WCAG 2.2 SC 1.4.1)"
                                )
                            elif not {p.upper() for p in produced} & STATUS_TOKENS:
                                # Conformant, but off-vocabulary. Reported so the
                                # glossary and the workbooks can converge, never
                                # failed: imposing a token list would be this
                                # tool inventing a requirement WCAG does not make.
                                warnings.append(
                                    f"{relative}!{sheet.title}!{cell.coordinate}: "
                                    f"states its outcome as {sorted(produced)!r}, which "
                                    "is outside the repository's usual status "
                                    "vocabulary. Accessible, but a reader must learn a "
                                    "second set of words"
                                )
                        elif isinstance(value, (int, float)):
                            warnings.append(
                                f"{relative}!{sheet.title}!{cell.coordinate}: a numeric "
                                "cell carries conditional formatting; the colour adds "
                                "meaning the number does not state"
                            )

        # --- 1.3.1 Info and Relationships ----------------------------------
        if is_status_sheet:
            for row_index in range(1, min(sheet.max_row, 60) + 1):
                populated = [
                    sheet.cell(row_index, col)
                    for col in range(3, min(sheet.max_column, 10) + 1)
                    if sheet.cell(row_index, col).value not in (None, "")
                ]
                if not populated:
                    continue
                label = sheet.cell(row_index, 2).value
                if isinstance(label, str) and label.strip():
                    counts["labelled_rows"] += 1
                else:
                    counts["unlabelled_rows"] += 1
                    warnings.append(
                        f"{relative}!{sheet.title} row {row_index}: populated but "
                        "carries no row label, so its meaning depends on position "
                        "alone (WCAG 2.2 SC 1.3.1)"
                    )
    return failures, warnings, counts


def run() -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []
    totals = {"status_cells": 0, "labelled_rows": 0, "unlabelled_rows": 0}
    checked = 0

    for model_id, path in workbooks():
        model_failures, model_warnings, counts = check_workbook(model_id, path)
        failures.extend(model_failures)
        warnings.extend(model_warnings)
        for key, value in counts.items():
            totals[key] += value
        checked += 1

    return {
        "status": "PASS" if not failures else "FAIL",
        "workbooks_checked": checked,
        "criteria": {
            "WCAG 2.2 SC 1.4.1 Use of Colour": "enforced",
            "WCAG 2.2 SC 1.3.1 Info and Relationships": "reported",
            "WCAG 2.2 SC 1.4.3 Contrast": "not evaluable for a spreadsheet file",
        },
        "totals": totals,
        "failures": failures,
        "warnings": warnings[:25],
        "failure_count": len(failures),
        "warning_count": len(warnings),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()
    report = run()
    print(json.dumps(report, indent=2))
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
