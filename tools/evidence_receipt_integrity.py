"""Refresh and validate public-evidence workbook receipt integrity."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "standards" / "public_cases" / "index.json"
DEFAULT_REPORT = ROOT / "evidence-receipt-integrity-report.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _receipt_m4_value(receipt: dict[str, Any]) -> Any:
    if "counts_toward_M4" in receipt:
        return receipt["counts_toward_M4"]
    return receipt.get("counts_toward_m4")


def refresh() -> dict[str, Any]:
    index = _load(INDEX)
    errors: list[str] = []
    changed_receipts: list[str] = []
    cases = index.get("cases", [])
    for item in cases:
        case_id = item["case_id"]
        output = ROOT / item["output"]
        receipt_path = output.with_suffix(".receipt.json")
        if not output.exists():
            errors.append(f"{case_id}: missing workbook {item['output']}")
            continue
        if not receipt_path.exists():
            errors.append(f"{case_id}: missing receipt {receipt_path.relative_to(ROOT)}")
            continue
        digest = _sha256(output)
        receipt = _load(receipt_path)
        changed = False
        if receipt.get("workbook_sha256") != digest:
            receipt["workbook_sha256"] = digest
            receipt["hash_refreshed_on"] = date.today().isoformat()
            receipt["hash_refresh_reason"] = (
                "Bind the public-evidence receipt to the exact committed workbook bytes"
            )
            changed = True
        if _receipt_m4_value(receipt) is not False or "counts_toward_M4" not in receipt:
            receipt["counts_toward_M4"] = False
            changed = True
        if changed:
            _write(receipt_path, receipt)
            changed_receipts.append(str(receipt_path.relative_to(ROOT)))
        item["receipt"] = receipt
    index["case_count"] = len(cases)
    index["evidence_models"] = len({item["model_id"] for item in cases})
    _write(INDEX, index)
    return {
        "status": "PASS" if not errors else "FAIL",
        "cases": len(cases),
        "evidence_models": index["evidence_models"],
        "changed_receipts": changed_receipts,
        "errors": errors,
    }


def check() -> dict[str, Any]:
    index = _load(INDEX)
    errors: list[str] = []
    case_ids: list[str] = []
    models: set[str] = set()
    for item in index.get("cases", []):
        case_id = item["case_id"]
        case_ids.append(case_id)
        models.add(item["model_id"])
        output = ROOT / item["output"]
        receipt_path = output.with_suffix(".receipt.json")
        if not output.exists():
            errors.append(f"{case_id}: missing workbook")
            continue
        if not receipt_path.exists():
            errors.append(f"{case_id}: missing receipt")
            continue
        receipt = _load(receipt_path)
        digest = _sha256(output)
        receipt_digest = receipt.get("workbook_sha256")
        index_digest = (item.get("receipt") or {}).get("workbook_sha256")
        if receipt_digest != digest:
            errors.append(f"{case_id}: receipt hash does not match workbook")
        if index_digest != digest:
            errors.append(f"{case_id}: index receipt hash does not match workbook")
        if receipt.get("instance_id") != case_id:
            errors.append(f"{case_id}: receipt instance id mismatch")
        if _receipt_m4_value(receipt) is not False:
            errors.append(f"{case_id}: receipt may not count toward M4")
        if item.get("counts_toward_m4") is not False:
            errors.append(f"{case_id}: index case may not count toward M4")
    if len(case_ids) != len(set(case_ids)):
        errors.append("public evidence case identifiers must be globally unique")
    if index.get("case_count") != len(case_ids):
        errors.append("public evidence index case_count is stale")
    if index.get("evidence_models") != len(models):
        errors.append("public evidence index evidence_models is stale")
    return {
        "status": "PASS" if not errors else "FAIL",
        "cases": len(case_ids),
        "evidence_models": len(models),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    if not (args.refresh or args.check):
        args.check = True
    refresh_report = refresh() if args.refresh else None
    check_report = check() if args.check or args.refresh else None
    errors = [
        *([] if refresh_report is None else refresh_report["errors"]),
        *([] if check_report is None else check_report["errors"]),
    ]
    report = {
        "schema_version": "1.1",
        "status": "PASS" if not errors else "FAIL",
        "refresh": refresh_report,
        "check": check_report,
        "errors": errors,
    }
    report_path = args.report if args.report.is_absolute() else ROOT / args.report
    _write(report_path, report)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
