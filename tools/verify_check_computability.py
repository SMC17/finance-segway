"""A decision check may not report PASS on a metric it could not compute.

Excel compares text as greater than every number, and IFERROR swallows a
division by zero into whatever fallback it was given. Put those together
with a threshold test and an uncomputable metric does not merely pass -- it
reads as best-in-class:

    Visa, "LTV / CAC"
        metric  ='Unit Economics'!C19  ->  '-'      (=IFERROR(C18/C8,"-"))
        status  =IF(C8>=3,"PASS",IF(C8>=1,"REVIEW","BREACH"))  ->  PASS

    WeWork, "Loan-to-value"
        metric  =IFERROR(debt/price,0)  ->  0       (0/0, coerced)
        status  =IF(C9<=0.75,"PASS",...)            ->  PASS

The first says "low unit economics require remediation" in its own action
column, and awards the top band to a ratio that does not exist. The second
awards the safest leverage band to a property with no price.

This repository already has the right pattern and applies it in several
places -- `=IF(ISNUMBER(C9),IF(C9>=0,"PASS","REVIEW"),"REVIEW")`. In one
workbook (Coinbase FY2023) the guarded and unguarded forms sat four rows
apart. So this gate exists to keep the convention applied, not to introduce
one.

The marker is unambiguous. `-` here is a VALUE written by a formula
(`IFERROR(..., "-")`), not a number format: a plain 0 in a currency-
formatted cell still reads back as 0 through openpyxl, never as "-".

Text metrics that are not the marker are left alone. "SUPPORTED", "NONE"
and "PASS" are deliberate text-valued checks and several of them correctly
report FAIL, so the rule is specifically about the uncomputable marker.

Usage:
    python tools/verify_check_computability.py
    python tools/verify_check_computability.py --report check-computability.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_CASE_INDEX = ROOT / "standards" / "public_cases" / "index.json"
CHECK_SHEETS = ("Decision & Checks", "Checks")
STATUSES = ("PASS", "FAIL", "BREACH", "REVIEW")
UNCOMPUTABLE = "-"


def _status_column(sheet, values) -> int | None:
    """The column whose cells hold verdicts. Located rather than assumed:
    the two check-sheet archetypes put it in different places (D for
    "Decision & Checks", C for "Checks")."""
    for column in range(2, 9):
        hits = sum(
            1
            for row in range(1, sheet.max_row + 1)
            if values.cell(row=row, column=column).value in STATUSES
        )
        if hits >= 3:
            return column
    return None


def _label(path: Path) -> str:
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def inspect(path: Path) -> dict[str, Any]:
    formulas = load_workbook(path, data_only=False)
    values = load_workbook(path, data_only=True)
    sheet_name = next((s for s in formulas.sheetnames if s in CHECK_SHEETS), None)
    if sheet_name is None:
        return {"path": _label(path), "state": "no_check_sheet", "rows": []}

    sheet, vsheet = formulas[sheet_name], values[sheet_name]
    status_column = _status_column(sheet, vsheet)
    if status_column is None:
        return {"path": _label(path), "sheet": sheet_name,
                "state": "no_status_column", "rows": []}

    # The metric sits immediately left of the status in the archetype that
    # has one. Where status is column C there is no metric column at all,
    # and that is reported rather than treated as clean.
    metric_column = status_column - 1 if status_column - 1 > 2 else None

    rows = []
    for row in range(1, sheet.max_row + 1):
        label = sheet.cell(row=row, column=2).value
        status = vsheet.cell(row=row, column=status_column).value
        if not isinstance(label, str) or status not in STATUSES:
            continue
        if label.strip().lower().startswith("overall"):
            continue
        if metric_column is None:
            rows.append({"label": label, "status": status, "metric": None,
                         "state": "no_metric_shown"})
            continue
        metric = vsheet.cell(row=row, column=metric_column).value
        uncomputable = isinstance(metric, str) and metric.strip() == UNCOMPUTABLE
        rows.append({
            "label": label,
            "status": status,
            "metric": metric if isinstance(metric, (int, float, str)) else None,
            "state": ("passes_on_uncomputable" if uncomputable and status == "PASS"
                      else "uncomputable_reported" if uncomputable
                      else "ok"),
        })
    return {"path": _label(path), "sheet": sheet_name,
            "state": "inspected", "rows": rows}


def assess() -> dict[str, Any]:
    index = json.loads(PUBLIC_CASE_INDEX.read_text(encoding="utf-8"))
    cases = index["cases"] if isinstance(index, dict) else index
    seen: set[Path] = set()
    results = []
    for case in cases:
        output = case.get("output")
        if not output:
            continue
        path = (ROOT / output).resolve()
        if path in seen or not path.exists():
            continue
        seen.add(path)
        results.append(inspect(path))

    violations = [
        {"path": r["path"], "label": row["label"], "metric": row["metric"]}
        for r in results for row in r["rows"]
        if row["state"] == "passes_on_uncomputable"
    ]
    counts = {
        "workbooks": len(results),
        "workbooks_not_inspectable": sum(1 for r in results if r["state"] != "inspected"),
        "checks_inspected": sum(1 for r in results for row in r["rows"] if row["state"] != "no_metric_shown"),
        "checks_without_a_metric_column": sum(1 for r in results for row in r["rows"] if row["state"] == "no_metric_shown"),
        "uncomputable_reported_honestly": sum(1 for r in results for row in r["rows"] if row["state"] == "uncomputable_reported"),
        "passes_on_uncomputable": len(violations),
    }
    return {"status": "PASS" if not violations else "FAIL",
            "counts": counts, "violations": violations, "results": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = assess()
    c = report["counts"]

    print(f"Inspected {c['workbooks']} public-case workbooks.")
    print(f"  checks with a metric to inspect      : {c['checks_inspected']}")
    print(f"  metric is '-' and status is NOT PASS : {c['uncomputable_reported_honestly']}  (the convention working)")
    print(f"  metric is '-' and status IS PASS     : {c['passes_on_uncomputable']}")
    print()
    print("AND HERE IS WHAT THIS DID NOT CHECK: "
          f"{c['checks_without_a_metric_column']} checks live on a sheet that shows no metric "
          "column at all,\nso whether their verdict rests on a computable quantity cannot be "
          "read off the workbook. That is not\na pass; it is a question this gate cannot ask.")
    if c["workbooks_not_inspectable"]:
        print(f"  Also {c['workbooks_not_inspectable']} workbook(s) had no check sheet, or fewer "
              "than three verdicts on it, so the status\n  column could not be located. Counted "
              "here rather than skipped silently.")

    if report["violations"]:
        print("\nFAIL — a verdict of PASS over a metric that does not exist:")
        for v in report["violations"]:
            print(f"  {v['path']}\n      {v['label']}  (metric {v['metric']!r})")
        print("\nGuard the status with ISNUMBER, as several checks in this repository already do:")
        print('  =IF(ISNUMBER(C9),IF(C9>=0,"PASS","REVIEW"),"REVIEW")')

    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
