"""Require a committed workbook to carry the values it was verified with.

CI recalculates workbooks in the runner and throws the result away. The
bytes that land on main are whatever the builder wrote, and openpyxl does
not evaluate formulas -- so a workbook rebuilt or round-tripped after its
recalculation is committed with every formula cell empty. Opened by a
reader, it shows blanks where the model's answers should be.

That is not only a presentation problem. tools/weekly_refresh_check.py --
the repository's only scanner for *cached* formula errors -- loads with
data_only=True and looks for #REF!/#DIV/0!/#VALUE! and friends. When no
formula carries a cached result there is nothing for it to look at, so it
reports the workbook clean. Demonstrated on a planted control: one file
with a deliberate `=1/0`, recalculated, reports 71 CELL ERROR(S); the same
file round-tripped through openpyxl, formulas byte-identical, reports
clean. The negative is not evidence.

So this is a PRESENCE check, and it fails closed. A workbook that offers
formulas and stores no results has not been shown to compute anything, and
"no cached errors in 0 cached cells" must never render as the same green
tick as "no cached errors in 198 cached cells".

Four outcomes are reported separately, because they are four different
facts and only one of them is a defect:

  ok            formulas present, results stored
  empty_cache   formulas present, NO results stored          <- the failure
  no_formulas   nothing to evaluate; states so rather than passing quietly
  unreadable    the file could not be opened at all

Partial caches are reported with their ratio and treated as ok: a formula
legitimately evaluates to blank in some models, so a missing individual
result is not by itself evidence of anything. A file where *nothing at
all* evaluated is a different claim, and it is the one worth gating.

Usage:
    python tools/verify_recalc_persistence.py
    python tools/verify_recalc_persistence.py --report recalc-persistence.json
    python tools/verify_recalc_persistence.py --paths 02_Corporate_Finance/instances/x.xlsx
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_CASE_INDEX = ROOT / "standards" / "public_cases" / "index.json"


def committed_case_workbooks() -> list[Path]:
    """Every public-case workbook the ledger claims as evidence.

    Driven off the ledger rather than a glob so a case that is dropped from
    the index stops being gated at the same moment it stops being evidence,
    and so an untracked scratch workbook in an instances/ directory never
    reddens the build.
    """
    index = json.loads(PUBLIC_CASE_INDEX.read_text(encoding="utf-8"))
    cases = index["cases"] if isinstance(index, dict) else index
    paths: list[Path] = []
    seen: set[Path] = set()
    for case in cases:
        output = case.get("output")
        if not output:
            continue
        path = (ROOT / output).resolve()
        if path not in seen:
            seen.add(path)
            paths.append(path)
    return sorted(paths)


def measure(path: Path) -> dict[str, Any]:
    """Count formula cells and how many of them carry a stored result."""
    try:
        formulas_wb = load_workbook(path, data_only=False)
        values_wb = load_workbook(path, data_only=True)
    except Exception as exc:  # noqa: BLE001 -- any open failure is the same fact here
        return {
            "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "state": "unreadable",
            "formulas": 0,
            "cached": 0,
            "detail": str(exc),
        }

    formulas = 0
    cached = 0
    for name in formulas_wb.sheetnames:
        formula_sheet = formulas_wb[name]
        value_sheet = values_wb[name]
        for row in formula_sheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    formulas += 1
                    if value_sheet[cell.coordinate].value is not None:
                        cached += 1

    if formulas == 0:
        state = "no_formulas"
    elif cached == 0:
        state = "empty_cache"
    else:
        state = "ok"

    return {
        "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "state": state,
        "formulas": formulas,
        "cached": cached,
    }


def assess(paths: list[Path] | None = None) -> dict[str, Any]:
    workbooks = paths if paths is not None else committed_case_workbooks()
    results = []
    for path in workbooks:
        if not path.exists():
            results.append(
                {
                    "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                    "state": "unreadable",
                    "formulas": 0,
                    "cached": 0,
                    "detail": "file does not exist",
                }
            )
            continue
        results.append(measure(path))

    by_state: dict[str, list[dict[str, Any]]] = {}
    for item in results:
        by_state.setdefault(item["state"], []).append(item)

    failures = by_state.get("empty_cache", []) + by_state.get("unreadable", [])
    return {
        "status": "PASS" if not failures else "FAIL",
        "checked": len(results),
        "ok": len(by_state.get("ok", [])),
        "empty_cache": len(by_state.get("empty_cache", [])),
        "no_formulas": len(by_state.get("no_formulas", [])),
        "unreadable": len(by_state.get("unreadable", [])),
        "total_formulas": sum(item["formulas"] for item in results),
        "total_cached": sum(item["cached"] for item in results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    parser.add_argument(
        "--paths",
        type=Path,
        nargs="*",
        help="check these workbooks instead of the public-case ledger",
    )
    args = parser.parse_args()

    report = assess([p.resolve() for p in args.paths] if args.paths else None)

    width = max([len(item["path"]) for item in report["results"]] + [8]) + 2
    rule = "-" * (width + 32)
    print(f"{'workbook':<{width}}{'state':<14}{'cached/formulas':>18}")
    print(rule)
    for item in sorted(report["results"], key=lambda r: (r["state"] != "empty_cache", r["path"])):
        ratio = f"{item['cached']}/{item['formulas']}"
        print(f"{item['path']:<{width}}{item['state']:<14}{ratio:>18}")

    print(rule)
    print(
        f"Checked {report['checked']} committed case workbooks: "
        f"{report['ok']} ok, {report['empty_cache']} with an empty cache, "
        f"{report['no_formulas']} with no formulas, {report['unreadable']} unreadable. "
        f"{report['total_cached']} of {report['total_formulas']} formula cells carry a stored result."
    )

    if report["no_formulas"]:
        print(
            "\nAND HERE IS WHAT THIS DID NOT CHECK: a workbook reported no_formulas was not "
            "verified to compute anything -- it was verified to have nothing to compute. That is\n"
            "a different fact from a pass, which is why it is counted separately."
        )

    if report["status"] == "FAIL":
        print(
            "\nFAIL. A workbook with formulas and no stored results has not been shown to compute "
            "anything, and the cached-error scanner cannot see errors in it.\n"
            "Recalculate it (tools/recalc.py), refresh its receipt "
            "(tools/evidence_receipt_integrity.py --refresh), and commit the recalculated bytes."
        )

    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
