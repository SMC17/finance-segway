"""Recalculate every real public-case workbook and read its genuine,
computed decision status back -- the check neither
tools/evidence_receipt_integrity.py (hashes only) nor
tools/final_public_evidence.py (schema and input-count only) performs.

Both of those existing gates can pass while a workbook is financially
broken: a receipt hash matches whatever bytes are committed regardless of
whether those bytes reflect a correct recalculation, and a manifest can
satisfy "at least two observed/derived inputs" while leaving every
valuation-driving assumption on template defaults. This script is what
actually opens each of the 48 real instances, recalculates it for real via
LibreOffice, and reads back the Overall/Decision status row -- the same
manual process that found:

  - a false-negative in Insurance's "Paid triangle cumulative" check that
    failed unconditionally regardless of the underlying data (fixed);
  - roughly a dozen domains where the "conventional" reference case and
    the "adversarial" stress case land on the identical overall status,
    because their manifests only source-address a couple of deal-specific
    cells and leave the assumptions that actually drive the decision
    (WACC, terminal growth, EPS-accretion inputs, ...) on template
    defaults -- not yet fixed, tracked below.

Two tiers of enforcement:

1. Hard failures (always block): workbook missing, recalculation doesn't
   succeed cleanly, or no genuine Overall/Decision status can be found at
   all. These indicate the model is structurally broken, not just
   thin -- exactly the Insurance bug's signature.

2. Tracked failures (block only if not explicitly allowlisted below): a
   conventional case landing on the same concerning status (FAIL/BREACH)
   as its adversarial sibling. This is evidence the manifest is thin
   rather than a compile-time defect, so it's tracked in
   KNOWN_THIN_CASES rather than failing every PR immediately -- but an
   *unlisted* case matching this pattern fails CI. As each domain's
   manifest is sourced with real valuation assumptions (see
   docs/EVIDENCE_STATUS_BOARD.md), remove it from the allowlist so the
   gate ratchets tighter over time instead of silently staying lenient.

Usage:
  python tools/verify_public_case_status.py
  python tools/verify_public_case_status.py --report report.json
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "standards" / "public_cases" / "index.json"

sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))
from recalc import recalc  # noqa: E402

CHECKS_SHEET_NAMES = ("Checks", "Decision & Checks")
CONCERNING_STATUSES = {"FAIL", "BREACH"}

# (model_id, domain) pairs where the conventional and adversarial public
# cases are known to land on the identical concerning status because the
# manifest only source-addresses a handful of deal-specific cells, leaving
# the assumptions that actually drive the decision (WACC, terminal growth,
# EPS-accretion inputs, ...) on template defaults. Remove an entry here
# only once real valuation assumptions have been sourced for both of that
# domain's public cases and verified to produce a differentiated result.
KNOWN_THIN_CASES: frozenset[str] = frozenset({
    "ib-public-hp-autonomy-2012-stress", "ib-public-microsoft-linkedin-2016",
    "corporate-public-intel-2024-stress", "corporate-public-microsoft-2024",
    "am-public-blackrock-2022-stress", "am-public-blackrock-2023",
    "microfinance-public-asa-zambia-stress", "microfinance-public-asa-2025",
    "equity-public-amc-2020-dilution", "equity-public-tesla-2020-offering",
    "vc-public-instacart-2023-down-round", "vc-public-snowflake-2020",
    "commodities-public-wti-april-2020", "commodities-public-wti-2023",
    "crypto-public-coinbase-2022-stress", "crypto-public-coinbase-2023",
    "real-estate-public-wework-2022-stress", "real-estate-public-realty-income-2023",
    "fintech-public-fis-worldpay-2023-stress", "fintech-public-visa-2023",
})


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_overall_status(workbook_path: Path) -> tuple[str | None, str | None]:
    """Search every sheet for a row whose label contains "overall"
    (case-insensitive substring, covers both "Overall" and "Overall model
    status" -- the two conventions in use across domains) and return
    (sheet_name, status). Not restricted to CHECKS_SHEET_NAMES: a renamed
    or missing checks sheet should surface as "not found", not a KeyError."""
    workbook = openpyxl.load_workbook(workbook_path, data_only=True)
    for sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
        for row in range(1, min(sheet.max_row, 60) + 1):
            for col in range(1, 6):
                label = sheet.cell(row, col).value
                if label and "overall" in str(label).strip().lower():
                    for status_col in range(col + 1, col + 4):
                        status = sheet.cell(row, status_col).value
                        if status is not None:
                            return sheet_name, str(status)
    return None, None


def verify(*, keep_scratch: bool = False) -> dict[str, Any]:
    index = _load(INDEX)
    cases = index["cases"]
    results: list[dict[str, Any]] = []
    errors: list[str] = []

    with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
        tmp_dir = Path(tmp)
        for case in cases:
            case_id = case["case_id"]
            src = ROOT / case["output"]
            if not src.exists():
                errors.append(f"{case_id}: missing workbook {case['output']}")
                results.append({"case_id": case_id, "status": "MISSING_WORKBOOK"})
                continue

            scratch = tmp_dir / src.name
            shutil.copyfile(src, scratch)
            recalc_result = recalc(str(scratch), timeout=90)
            recalc_ok = (
                recalc_result.get("status") == "success"
                and not recalc_result.get("total_errors", 1)
            )
            if not recalc_ok:
                errors.append(f"{case_id}: recalculation did not succeed cleanly: {recalc_result}")
                results.append({"case_id": case_id, "status": "RECALC_FAILED", "recalc": recalc_result})
                continue

            sheet_name, status = _find_overall_status(scratch)
            if status is None:
                errors.append(f"{case_id}: no Overall/Decision status found in any sheet")
                results.append({"case_id": case_id, "status": "NO_STATUS_FOUND"})
                continue

            results.append({
                "case_id": case_id,
                "model_id": case["model_id"],
                "case_type": case["case_type"],
                "sheet": sheet_name,
                "status": status,
            })

        if keep_scratch:
            shutil.copytree(tmp_dir, ROOT / ".verify-public-case-scratch", dirs_exist_ok=True)

    by_model: dict[str, dict[str, dict[str, Any]]] = {}
    for r in results:
        if "model_id" not in r:
            continue
        by_model.setdefault(r["model_id"], {})[r["case_type"]] = r

    thin_matches: list[str] = []
    unexpected_thin: list[str] = []
    for model_id, by_type in by_model.items():
        conventional = by_type.get("conventional")
        adversarial = by_type.get("adversarial")
        if not conventional or not adversarial:
            continue
        if (
            conventional["status"] == adversarial["status"]
            and conventional["status"] in CONCERNING_STATUSES
        ):
            thin_matches.append(conventional["case_id"])
            thin_matches.append(adversarial["case_id"])
            if conventional["case_id"] not in KNOWN_THIN_CASES:
                unexpected_thin.append(conventional["case_id"])
                errors.append(
                    f"{conventional['case_id']}: conventional case matches its adversarial "
                    f"sibling's {conventional['status']} status and is not in KNOWN_THIN_CASES -- "
                    "either this domain regressed to a thin manifest, or a real fix landed and "
                    "the case should be removed from KNOWN_THIN_CASES instead of left unlisted"
                )

    stale_allowlist = sorted(KNOWN_THIN_CASES - set(thin_matches))
    if stale_allowlist:
        errors.append(
            "KNOWN_THIN_CASES lists cases that no longer match the thin-manifest pattern -- "
            f"remove them from the allowlist now that they're fixed: {stale_allowlist}"
        )

    return {
        "status": "PASS" if not errors else "FAIL",
        "cases_checked": len(results),
        "known_thin_cases": sorted(KNOWN_THIN_CASES),
        "unexpected_thin_cases": unexpected_thin,
        "stale_allowlist_entries": stale_allowlist,
        "results": results,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument(
        "--keep-scratch", action="store_true",
        help="preserve recalculated copies under .verify-public-case-scratch/ for inspection",
    )
    args = parser.parse_args()

    report = verify(keep_scratch=args.keep_scratch)
    payload = json.dumps(report, indent=2)
    if args.report:
        args.report.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
