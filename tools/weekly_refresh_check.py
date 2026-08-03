"""Weekly triage scanner for workbook freshness, structural drift, and errors.

Usage:
    python tools/weekly_refresh_check.py [repo-or-domain-path]

Template workbooks are checked for structure and cached errors but are not
flagged as stale. Populated instances are also checked against Cover!C6
(`Last refreshed`) and Cover!C7 (`Next material date`).
"""
from __future__ import annotations

import csv
import glob
import os
import sys
from datetime import date, datetime
from pathlib import Path

import openpyxl

ARCHETYPE_REQUIRED_TABS = {
    "corp_finance": {"Cover", "Assumptions", "IS", "BS", "CF", "DCF", "Comps", "Sensitivity", "RefreshLog"},
    "lbo": {"Cover", "Sources & Uses", "Debt Schedule", "Returns", "Sensitivity", "RefreshLog"},
    "credit": {
        "Cover", "Assumptions", "Operating Case", "Debt Schedule", "Covenants",
        "Yield & Spread", "Recovery", "Sensitivity", "Checks", "Sources", "RefreshLog",
    },
    "public_finance": {
        "Cover", "Assumptions", "Debt Sustainability", "Revenue & Expenditure",
        "Debt Service", "Coverage", "Scenarios", "Sensitivity", "Checks", "Sources", "RefreshLog",
    },
    "risk": {"Cover", "VaR", "Stress Scenarios", "RefreshLog"},
    "default": {"Cover", "RefreshLog"},
}

ERROR_TOKENS = {"#REF!", "#NAME?", "#VALUE!", "#DIV/0!", "#N/A", "#NULL!", "#NUM!"}
STALE_DAYS = 7
MATERIAL_DATE_WARNING_DAYS = 5


def detect_archetype(path: str, sheetnames: set[str]) -> str:
    lower = path.lower()
    lowered_sheets = {sheet.lower() for sheet in sheetnames}
    if "public_finance" in lower or {"debt sustainability", "coverage"}.issubset(lowered_sheets):
        return "public_finance"
    if "credit" in lower or {"covenants", "yield & spread", "recovery"}.issubset(lowered_sheets):
        return "credit"
    if "lbo" in lower or "sources & uses" in lowered_sheets:
        return "lbo"
    if "risk" in lower:
        return "risk"
    if {"IS", "BS", "CF", "DCF"}.issubset(sheetnames):
        return "corp_finance"
    return "default"


def parse_date_cell(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text or text.startswith("["):
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def is_template(path: str) -> bool:
    return Path(path).name.startswith("_template_")


def scan_workbook(path: str) -> dict:
    result = {
        "file": os.path.basename(path),
        "path": path,
        "archetype": "",
        "is_template": is_template(path),
        "missing_tabs": "",
        "last_refreshed": "",
        "days_since_refresh": "",
        "next_material_date": "",
        "days_to_material_date": "",
        "formula_errors_found": "",
        "flags": [],
    }
    try:
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    except Exception as exc:  # noqa: BLE001 - report malformed workbooks rather than aborting scan
        result["flags"].append(f"COULD NOT OPEN: {exc}")
        return result

    sheetnames = set(wb.sheetnames)
    archetype = detect_archetype(path, sheetnames)
    required = ARCHETYPE_REQUIRED_TABS[archetype]
    missing = required - sheetnames
    result["archetype"] = archetype
    if missing:
        result["missing_tabs"] = ", ".join(sorted(missing))
        result["flags"].append(f"STRUCTURAL DRIFT vs {archetype} (missing: {', '.join(sorted(missing))})")

    if "Cover" in sheetnames and not result["is_template"]:
        cover = wb["Cover"]
        today = date.today()
        last_refreshed = parse_date_cell(cover["C6"].value)
        next_material = parse_date_cell(cover["C7"].value)

        if last_refreshed:
            days_since = (today - last_refreshed).days
            result["last_refreshed"] = str(last_refreshed)
            result["days_since_refresh"] = days_since
            if days_since > STALE_DAYS:
                result["flags"].append(f"STALE ({days_since}d since refresh)")
        else:
            result["flags"].append("NO REFRESH DATE SET")

        if next_material:
            days_to = (next_material - today).days
            result["next_material_date"] = str(next_material)
            result["days_to_material_date"] = days_to
            if 0 <= days_to <= MATERIAL_DATE_WARNING_DAYS:
                result["flags"].append(f"MATERIAL DATE IN {days_to}d — refresh model")
            elif days_to < 0:
                result["flags"].append(f"MATERIAL DATE PASSED {abs(days_to)}d AGO — update next date")

    errors_found: list[str] = []
    for sheet in wb.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.strip() in ERROR_TOKENS:
                    errors_found.append(f"{sheet.title}!{cell.coordinate}={cell.value}")
    if errors_found:
        result["formula_errors_found"] = "; ".join(errors_found[:10])
        result["flags"].append(f"{len(errors_found)} CELL ERROR(S)")

    if not result["flags"]:
        result["flags"].append("OK")
    return result


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    files = sorted(glob.glob(os.path.join(root, "**", "*.xlsx"), recursive=True))
    files = [path for path in files if not os.path.basename(path).startswith("~$")]
    if not files:
        print(f"No .xlsx files found in {root}")
        return 0

    rows = [scan_workbook(path) for path in files]
    report_path = os.path.join(root, f"refresh_report_{date.today().isoformat()}.csv")
    fieldnames = [
        "file", "archetype", "is_template", "flags", "last_refreshed",
        "days_since_refresh", "next_material_date", "days_to_material_date",
        "missing_tabs", "formula_errors_found", "path",
    ]
    with open(report_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            row = dict(row)
            row["flags"] = "; ".join(row["flags"])
            writer.writerow(row)

    def urgency(row: dict) -> int:
        flags = "; ".join(row["flags"])
        if "COULD NOT OPEN" in flags or "MATERIAL DATE IN" in flags:
            return 0
        if "ERROR" in flags or "DRIFT" in flags:
            return 1
        if "STALE" in flags:
            return 2
        return 3

    print(f"\nScanned {len(rows)} workbooks in {root}\n" + "-" * 72)
    for row in sorted(rows, key=urgency):
        flags = "; ".join(row["flags"])
        if flags != "OK":
            print(f"{row['file']:42s} {flags}")
    clean = sum(1 for row in rows if row["flags"] == ["OK"])
    print("-" * 72)
    print(f"{clean}/{len(rows)} clean. Full report: {report_path}")

    hard_fail = any(
        any(token in "; ".join(row["flags"]) for token in ("COULD NOT OPEN", "CELL ERROR", "STRUCTURAL DRIFT"))
        for row in rows
    )
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
