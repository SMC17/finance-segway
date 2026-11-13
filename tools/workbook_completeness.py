#!/usr/bin/env python3
"""Measure how complete every committed workbook is.

For each .xlsx/.xlsm tracked by git, count non-empty cells, formulas, formulas
with no cached (computed) value, cached error values, and placeholder text such
as "[ISSUER]" or "TBD". A workbook is *computed* when every formula carries a
cached value, which is what a reader opening the file actually sees.

    python tools/workbook_completeness.py            # table
    python tools/workbook_completeness.py --json     # machine-readable totals
    python tools/workbook_completeness.py --strict   # exit 1 unless all computed and no placeholders

Requires openpyxl.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

PLACEHOLDER = re.compile(r"^\s*\[[^\]]{2,60}\]\s*$|\bTBD\b|\bTODO\b|\bXXX\b|^\s*\?\s*$|placeholder|lorem", re.I)
ERROR = re.compile(r"^#(REF!|DIV/0!|VALUE!|NAME\?|N/A|NUM!|NULL!|SPILL!|CALC!)$")


def workbooks(root: Path) -> list[str]:
    out = subprocess.run(["git", "-C", str(root), "ls-files", "*.xlsx", "*.xlsm"], capture_output=True, text=True, check=True)
    return sorted(p for p in out.stdout.split() if p)


def measure(path: Path) -> dict:
    from openpyxl import load_workbook

    formulas_wb = load_workbook(path, data_only=False, read_only=True)
    values_wb = load_workbook(path, data_only=True, read_only=True)
    m = dict(sheets=0, cells=0, formulas=0, uncached=0, errors=0, placeholders=0, numbers=0)
    for ws in formulas_wb.worksheets:
        m["sheets"] += 1
        cached = {}
        for row in values_wb[ws.title].iter_rows():
            for c in row:
                if c.value is not None and hasattr(c, "coordinate"):
                    cached[c.coordinate] = c.value
        for row in ws.iter_rows():
            for c in row:
                v = c.value
                if v is None or not hasattr(c, "coordinate"):
                    continue
                m["cells"] += 1
                if isinstance(v, str) and v.startswith("="):
                    m["formulas"] += 1
                    cv = cached.get(c.coordinate)
                    if cv is None:
                        m["uncached"] += 1
                    elif isinstance(cv, str) and ERROR.match(cv):
                        m["errors"] += 1
                elif isinstance(v, str):
                    if PLACEHOLDER.search(v):
                        m["placeholders"] += 1
                    if ERROR.match(v):
                        m["errors"] += 1
                elif isinstance(v, (int, float)):
                    m["numbers"] += 1
    return m


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    root = Path(a.root)
    rows = [(p, measure(root / p)) for p in workbooks(root)]
    keys = ["sheets", "cells", "formulas", "uncached", "errors", "placeholders", "numbers"]
    tot = {k: sum(m[k] for _, m in rows) for k in keys}
    tot["workbooks"] = len(rows)
    tot["computed_workbooks"] = sum(1 for _, m in rows if m["uncached"] == 0)
    tot["never_computed_workbooks"] = sum(1 for _, m in rows if m["formulas"] and m["uncached"] == m["formulas"])
    tot["workbooks_with_placeholders"] = sum(1 for _, m in rows if m["placeholders"])
    tot["formula_computed_pct"] = round(100 * (1 - tot["uncached"] / tot["formulas"]), 2) if tot["formulas"] else 100.0
    if a.json:
        print(json.dumps({"totals": tot, "workbooks": {p: m for p, m in rows}}, indent=1))
    else:
        print(f"{'uncached':>8} {'formulas':>8} {'placeh.':>7} {'errors':>6}  workbook")
        for p, m in sorted(rows, key=lambda r: (-r[1]["uncached"], -r[1]["placeholders"], r[0])):
            print(f"{m['uncached']:8d} {m['formulas']:8d} {m['placeholders']:7d} {m['errors']:6d}  {p}")
        print(f"\n{tot['workbooks']} workbooks, {tot['formulas']} formulas, {tot['formula_computed_pct']}% computed; "
              f"{tot['never_computed_workbooks']} never computed; {tot['placeholders']} placeholder cells in "
              f"{tot['workbooks_with_placeholders']} workbooks; {tot['errors']} error values")
    if a.strict and (tot["uncached"] or tot["placeholders"] or tot["errors"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
