"""Validate the exact committed six-engine frontier release.

This validator is intentionally read-only. It checks the repository artifacts,
ledgers, receipts, institutional surfaces, workbook contracts, and conservative
maturity declarations produced by the atomic six-engine release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from tools.institutional_surface import profiles_by_id, validate_workbook_surface
    from tools.release_legacy_engine_promotions import (
        BENCHMARK_INDEX_PATH,
        CANONICAL_PATHS,
        EXPECTED_IDS,
        INVENTORY_PATH,
        REGISTRY_PATH,
        ROOT,
        case_specs,
    )
    from tools.validate_legacy_release_workbooks import validate_workbook
    from tools.workbook_engineering import audit_workbook
except ModuleNotFoundError:
    from institutional_surface import profiles_by_id, validate_workbook_surface
    from release_legacy_engine_promotions import (
        BENCHMARK_INDEX_PATH,
        CANONICAL_PATHS,
        EXPECTED_IDS,
        INVENTORY_PATH,
        REGISTRY_PATH,
        ROOT,
        case_specs,
    )
    from validate_legacy_release_workbooks import validate_workbook
    from workbook_engineering import audit_workbook

RELEASE_COMMIT_MESSAGE = "Release six legacy finance engines with benchmark evidence"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_entries() -> list[tuple[str, Path, str]]:
    entries = [
        (model_id, ROOT / CANONICAL_PATHS[model_id], f"canonical {model_id}")
        for model_id in sorted(EXPECTED_IDS)
    ]
    entries.extend(
        (
            spec["model_id"],
            ROOT / spec["output"],
            f"instance {spec['id']}",
        )
        for spec in case_specs()
    )
    return entries


def validate() -> dict[str, Any]:
    registry = _load(REGISTRY_PATH)
    inventory = _load(INVENTORY_PATH)
    benchmark_index = _load(BENCHMARK_INDEX_PATH)
    inventory_by_id = {item["id"]: item for item in inventory["models"]}
    registry_by_id = {item["model_id"]: item for item in registry["models"]}
    profiles = profiles_by_id(ROOT)
    errors: list[str] = []
    contracts: list[dict[str, Any]] = []
    surfaces: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []

    if registry.get("status") != "applied_release_validated":
        errors.append("legacy engine registry is not applied_release_validated")
    if set(registry_by_id) != EXPECTED_IDS:
        errors.append("legacy engine registry does not cover the exact six-model cohort")

    for model_id in sorted(EXPECTED_IDS):
        model = inventory_by_id.get(model_id)
        candidate = registry_by_id.get(model_id)
        if model is None or candidate is None:
            errors.append(f"{model_id}: missing inventory or registry entry")
            continue
        if model.get("declared_maturity") != "M2":
            errors.append(f"{model_id}: committed release may not exceed M2")
        if model.get("builder") != candidate.get("candidate_builder"):
            errors.append(f"{model_id}: committed builder does not match release registry")
        if model.get("reference_checks") != candidate.get("reference_checks"):
            errors.append(f"{model_id}: committed reference checks do not match registry")
        if model.get("workbook") != CANONICAL_PATHS[model_id]:
            errors.append(f"{model_id}: canonical workbook path mismatch")

    entries = artifact_entries()
    if len(entries) != 18 or len({str(path) for _, path, _ in entries}) != 18:
        errors.append("committed release must contain 18 unique workbooks")
    for model_id, path, label in entries:
        if not path.exists():
            errors.append(f"{label}: missing workbook {path.relative_to(ROOT)}")
            continue
        result = validate_workbook(model_id, path)
        contracts.append({"label": label, **result})
        errors.extend(f"{label}: {item}" for item in result["errors"])
        surface_errors = validate_workbook_surface(
            path, inventory_by_id[model_id], profiles[model_id]
        )
        surfaces.append(
            {
                "label": label,
                "path": str(path.relative_to(ROOT)),
                "errors": surface_errors,
            }
        )
        errors.extend(f"{label}: surface {item}" for item in surface_errors)
        summary, findings = audit_workbook(path)
        audit_errors = [
            finding.__dict__ for finding in findings if finding.severity == "error"
        ]
        audits.append(
            {
                "label": label,
                "path": str(path.relative_to(ROOT)),
                "summary": summary,
                "errors": audit_errors,
            }
        )
        errors.extend(f"{label}: engineering {item}" for item in audit_errors)

    index_instances = benchmark_index.get("instances", [])
    if benchmark_index.get("instance_count") != 48:
        errors.append(
            f"benchmark index expected 48 instances, found {benchmark_index.get('instance_count')}"
        )
    if benchmark_index.get("counts_toward_M4") is not False:
        errors.append("synthetic benchmark index may not count toward M4")
    by_instance = {item.get("instance_id"): item for item in index_instances}
    counts: Counter[str] = Counter()
    receipt_results: list[dict[str, Any]] = []
    for spec in case_specs():
        output = ROOT / spec["output"]
        receipt_path = output.with_suffix(".receipt.json")
        manifest_path = ROOT / "standards" / "benchmark_cases" / f"{spec['id']}.json"
        if not receipt_path.exists() or not manifest_path.exists():
            errors.append(f"{spec['id']}: missing receipt or manifest")
            continue
        receipt = _load(receipt_path)
        manifest = _load(manifest_path)
        digest = _sha256(output)
        index_item = by_instance.get(spec["id"], {})
        receipt_errors: list[str] = []
        if receipt.get("workbook_sha256") != digest:
            receipt_errors.append("receipt hash mismatch")
        if index_item.get("workbook_sha256") != digest:
            receipt_errors.append("index hash mismatch")
        if receipt.get("counts_toward_M4") is not False:
            receipt_errors.append("receipt may not count toward M4")
        if manifest.get("counts_toward_M4") is not False:
            receipt_errors.append("manifest may not count toward M4")
        if manifest.get("classification") != "synthetic_engineering_benchmark":
            receipt_errors.append("manifest classification mismatch")
        if receipt.get("model_id") != spec["model_id"]:
            receipt_errors.append("receipt model id mismatch")
        receipt_results.append(
            {
                "instance_id": spec["id"],
                "model_id": spec["model_id"],
                "output": spec["output"],
                "workbook_sha256": digest,
                "errors": receipt_errors,
            }
        )
        errors.extend(f"{spec['id']}: {item}" for item in receipt_errors)
        counts[spec["model_id"]] += 1
    for model_id in EXPECTED_IDS:
        if counts[model_id] != 2:
            errors.append(
                f"{model_id}: expected two committed benchmark instances, found {counts[model_id]}"
            )

    maturity = Counter(item.get("declared_maturity") for item in inventory["models"])
    if maturity != Counter({"M2": 24}):
        errors.append(f"committed maturity distribution must remain M2=24, found {dict(maturity)}")

    return {
        "schema_version": "1.0",
        "status": "PASS" if not errors else "FAIL",
        "release_status": registry.get("status"),
        "inventory_models": len(inventory.get("models", [])),
        "maturity_distribution": dict(maturity),
        "canonical_models": 6,
        "benchmark_instances": 12,
        "total_release_workbooks": len(entries),
        "benchmark_index_instances": benchmark_index.get("instance_count"),
        "benchmark_counts": dict(sorted(counts.items())),
        "contracts": contracts,
        "surfaces": surfaces,
        "audits": audits,
        "receipts": receipt_results,
        "errors": errors,
        "statement": (
            "The committed six-engine release is validated at M2. Synthetic benchmark "
            "instances do not count toward M4, and no M3 or M4 promotion is claimed."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report", type=Path, default=ROOT / "committed-frontier-release-report.json"
    )
    args = parser.parse_args()
    report = validate()
    report_path = args.report if args.report.is_absolute() else ROOT / args.report
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "status",
                    "release_status",
                    "inventory_models",
                    "maturity_distribution",
                    "canonical_models",
                    "benchmark_instances",
                    "total_release_workbooks",
                    "benchmark_index_instances",
                    "errors",
                )
            },
            indent=2,
        )
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
