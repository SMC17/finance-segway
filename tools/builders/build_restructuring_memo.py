"""Build a governed, data-grounded restructuring memo deck for a real
public Distressed & Restructuring instance.

Seventh domain on the IC-memo/pptx system, reusing
tools/builders/pptx_helpers.py unchanged. Every number on a slide is read
from the instance workbook after a real LibreOffice recalculation
(tools.recalc), or from the case's own governed manifest
(standards/public_cases/<case_id>.json). Nothing on any slide is invented
here -- this script only reads and renders.

The deck states how many inputs are observed or derived and how many are
declared drivers, straight from the manifest, and labels the waterfall's
distributable value as the Plan's distribution rather than an independent
valuation. For the default case
(distressed-public-hertz-2021-reorganization) every input comes from a
filing public on or before 2021-06-30; see tools/deepen_distressed_hertz.py.

Usage:
    python tools/builders/build_restructuring_memo.py --case-id distressed-public-hertz-2021-reorganization
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import pptx_helpers as ph  # noqa: E402
from recalc import recalc  # noqa: E402

import openpyxl  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "standards" / "public_cases" / "index.json"


def _load_case(case_id: str) -> dict[str, Any]:
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    for item in index["cases"]:
        if item["case_id"] == case_id:
            return item
    raise KeyError(f"unknown case_id {case_id!r}")


def _recalculated_workbook(output_rel: str) -> openpyxl.Workbook:
    src = ROOT / output_rel
    with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
        scratch = Path(tmp) / src.name
        shutil.copyfile(src, scratch)
        result = recalc(str(scratch), timeout=90)
        if result.get("status") != "success" or result.get("total_errors", 1):
            raise RuntimeError(f"recalculation did not succeed cleanly: {result}")
        return openpyxl.load_workbook(scratch, data_only=True)


def _manifest(case_id: str) -> dict[str, Any]:
    return json.loads((ROOT / "standards" / "public_cases" / f"{case_id}.json").read_text(encoding="utf-8"))


def _fmt_usd_mm(value: float) -> str:
    return f"${value:,.1f}mm"


def build_restructuring_memo(case_id: str, output: Path) -> None:
    case = _load_case(case_id)
    manifest = _manifest(case_id)
    outcome = manifest["outcome"]
    kinds = [item.get("input_kind") for item in manifest["inputs"]]
    n_real = sum(1 for k in kinds if k in {"observed", "derived"})
    n_drivers = len(manifest.get("driver_declarations", []))
    situation = manifest["cover"]["Situation type:"]
    subject = manifest["cover"].get("Title:", situation).split(" — ")[0]

    wb = _recalculated_workbook(case["output"])
    waterfall = wb["Recovery Waterfall"]
    liquidity = wb["13-Week Liquidity"]
    new_money = wb["New Money"]
    lvr = wb["Liquidation vs Reorg"]
    checks = wb["Decision & Checks"]

    as_of = manifest["as_of"]
    commitment = new_money["C5"].value
    rate = new_money["C8"].value
    commitment_status = new_money["C19"].value
    min_cash = liquidity["C22"].value
    peak_need = liquidity["C23"].value
    min_liquidity = liquidity["C4"].value
    distributable = waterfall["C12"].value
    liq_npv = lvr["C12"].value
    reorg_npv = lvr["D12"].value
    overall_status = checks["C14"].value

    prs = ph.new_presentation()

    # 1. Title
    ph.add_title_slide(
        prs,
        f"{subject} — Restructuring Memo",
        situation,
        f"As of {as_of}  ·  Prepared from a governed, recalculated model instance",
    )

    # 2. Provenance
    slide = ph.add_content_slide(prs, "Reading this deck", kicker="Provenance")
    ph.add_bullets(
        slide, ph.MARGIN, ph.Inches(1.5), ph.SLIDE_W - 2 * ph.MARGIN, ph.Inches(3.2),
        [
            f"{n_real} inputs are observed or derived from filings public on or before {as_of}; "
            f"{n_drivers} are declared drivers, each grounded in a named filing or statute.",
            "Capital structure: Allowed claim amounts from the confirmed Plan. DIP terms: the DIP Credit "
            "Agreement as disclosed in Form 8-K and Form 10-Q.",
            "13-week schedule: Q1 2021 actual cash flows phased evenly by week; ending cash ties to the "
            "disclosed 2021-03-31 balance.",
            "Distributable value is the Plan's distribution to the modeled classes, not an independent "
            "enterprise valuation, so creditor recoveries are 100% by construction.",
        ],
        size=15,
    )
    ph.add_footer(slide, f"Model checks: Overall {overall_status}  ·  standards/public_cases/{case_id}.json")

    # 3. Capital structure and recoveries
    slide = ph.add_content_slide(prs, "Claims and Plan recoveries", kicker="Recovery Waterfall")
    rows = []
    for r in range(5, 11):
        face = waterfall.cell(r, 3).value or 0
        recovery = waterfall.cell(r, 6).value
        rows.append([
            waterfall.cell(r, 2).value,
            _fmt_usd_mm(face),
            f"{recovery:.0%}" if isinstance(recovery, (int, float)) else str(recovery),
        ])
    ph.add_table(
        slide, ph.MARGIN, ph.Inches(1.5), ph.SLIDE_W - 2 * ph.MARGIN, ph.Inches(3.4),
        ["Tranche", "Claim", "Recovery"], rows, col_widths=[4, 2, 2],
    )
    ph.add_disclosure_note(
        slide,
        f"Distributable value {_fmt_usd_mm(distributable)} is the Plan's distribution to these classes. "
        "Equity's row is its cash and 3% stock distribution; warrant and rights value is excluded.",
    )

    # 4. Liquidity and DIP
    slide = ph.add_content_slide(prs, "Liquidity and DIP financing", kicker="13-Week Liquidity and New Money")
    ph.add_stat_row(
        slide, ph.Inches(1.6),
        [
            ph.Stat(_fmt_usd_mm(commitment), "DIP commitment", tag="Form 8-K", color=ph.NAVY),
            ph.Stat(f"{rate:.2%}", "DIP cash rate", tag="Form 10-Q", color=ph.NAVY),
            ph.Stat(_fmt_usd_mm(min_cash), "Minimum 13-week cash", tag="Q1 2021", color=ph.POSITIVE),
            ph.Stat(_fmt_usd_mm(peak_need), "Peak funding need", tag="Q1 2021", color=ph.POSITIVE),
        ],
    )
    ph.add_text(
        slide, ph.MARGIN, ph.Inches(3.6), ph.SLIDE_W - 2 * ph.MARGIN, ph.Inches(1.4),
        f"On the modeled Q1 2021 weekly path, unrestricted cash stays at or above {_fmt_usd_mm(min_cash)} against "
        f"the {_fmt_usd_mm(min_liquidity)} DIP minimum liquidity test. Commitment sufficiency: {commitment_status}.",
        size=15, color=ph.CHARCOAL,
    )
    ph.add_footer(slide, "Weekly phasing is an even spread of disclosed quarterly totals.")

    # 5. Decision
    slide = ph.add_content_slide(prs, "Liquidation versus reorganization", kicker="Decision")
    ph.add_table(
        slide, ph.MARGIN, ph.Inches(1.6), ph.SLIDE_W - 2 * ph.MARGIN, ph.Inches(1.8),
        ["Path", "NPV of proceeds"],
        [["Chapter 7 liquidation", _fmt_usd_mm(liq_npv)], ["Chapter 11 Plan", _fmt_usd_mm(reorg_npv)]],
        col_widths=[4, 2],
    )
    ph.add_text(
        slide, ph.MARGIN, ph.Inches(3.7), ph.SLIDE_W - 2 * ph.MARGIN, ph.Inches(1.2),
        ("Chapter 11 emergence: Completed" if outcome["realized"] == 1.0 else "Chapter 11 emergence: Not completed")
        + f"  ·  Overall checks: {overall_status}",
        size=17, bold=True, color=ph.NAVY,
    )
    ph.add_disclosure_note(
        slide,
        "Liquidation haircut, Chapter 7 fees, disposal time and discount rate are declared drivers: the "
        "Debtors' own liquidation analysis was not retrievable.",
    )
    ph.add_footer(
        slide,
        f"Outcome source: {outcome['realized_source']}  ·  Instance: {case['output']}",
    )

    ph.save(prs, output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", default="distressed-public-hertz-2021-reorganization")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    output = args.output or ROOT / "24_Distressed_Restructuring" / "presentations" / f"{args.case_id}-memo.pptx"
    build_restructuring_memo(args.case_id, output)
    print(f"saved {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
