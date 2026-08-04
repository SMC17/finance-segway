"""Materialize and validate public evidence for the nine recently hardened domains.

The existing flagship evidence release remains authoritative and unchanged. This
wrapper generates a second nine-model evidence cohort with the shared M3 tooling,
merges the public-case indexes, validates both registries independently, and
retains the conservative M2 / no-M4 claim boundary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from tools import m3_evidence
    from tools.frontier_evidence_registry import registry as build_registry
except ModuleNotFoundError:
    import m3_evidence
    from frontier_evidence_registry import registry as build_registry

ROOT = Path(__file__).resolve().parents[1]
EXPANSION_REGISTRY = ROOT / "standards" / "m3_evidence" / "frontier_registry.json"
PUBLIC_INDEX = ROOT / "standards" / "public_cases" / "index.json"
EXPANSION_REPORT = ROOT / "frontier-evidence-report.json"
COMBINED_REPORT = ROOT / "all-domain-evidence-report.json"
ORIGINAL_REGISTRY = ROOT / "standards" / "m3_evidence" / "flagship_registry.json"
EXPECTED_EXPANSION_IDS = {"08", "10", "11", "12", "15", "16", "17", "23", "24"}
EXPECTED_EXISTING_IDS = {"03", "04", "09", "14", "18", "19", "20", "21", "22"}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def materialized_registry() -> dict[str, Any]:
    payload = build_registry()
    write_json(EXPANSION_REGISTRY, payload)
    return payload


def _normalize_empty_benchmark_covers(
    evidence_registry: dict[str, Any],
) -> dict[Path, bytes]:
    """Temporarily add a subject key for old empty-cover benchmark manifests."""

    backups: dict[Path, bytes] = {}
    for model in evidence_registry["flagships"]:
        for case in model["cases"]:
            path = ROOT / case["based_on"]
            raw = path.read_bytes()
            payload = json.loads(raw.decode("utf-8"))
            if payload.get("cover"):
                continue
            backups[path] = raw
            payload["cover"] = {"Subject:": ""}
            write_json(path, payload)
    return backups


def _restore(backups: dict[Path, bytes]) -> None:
    for path, raw in backups.items():
        path.write_bytes(raw)


def _merge_indexes(
    existing: dict[str, Any], expansion: dict[str, Any]
) -> dict[str, Any]:
    by_case: dict[str, dict[str, Any]] = {}
    for item in [*existing.get("cases", []), *expansion.get("cases", [])]:
        case_id = item["case_id"]
        if case_id in by_case:
            raise ValueError(f"duplicate public case id {case_id}")
        by_case[case_id] = item
    cases = sorted(
        by_case.values(),
        key=lambda item: (item["model_id"], item["case_type"], item["case_id"]),
    )
    return {
        "schema_version": "1.1",
        "as_of": expansion.get("as_of") or existing.get("as_of"),
        "classification": "external_historical_cases",
        "counts_toward_m4": False,
        "case_count": len(cases),
        "evidence_models": len({item["model_id"] for item in cases}),
        "cases": cases,
    }


def materialize(generate_instances: bool) -> dict[str, Any]:
    evidence_registry = materialized_registry()
    existing_index = read_json(PUBLIC_INDEX)
    if existing_index.get("case_count") != 18:
        raise ValueError(
            "frontier evidence must start from the verified 18-case flagship index"
        )
    backups = _normalize_empty_benchmark_covers(evidence_registry)
    original_registry_path = m3_evidence.REGISTRY_PATH
    try:
        m3_evidence.REGISTRY_PATH = EXPANSION_REGISTRY
        expansion_index = m3_evidence.materialize(generate_instances)
    finally:
        m3_evidence.REGISTRY_PATH = original_registry_path
        _restore(backups)
    combined = _merge_indexes(existing_index, expansion_index)
    if combined["case_count"] != 36:
        raise ValueError(f"expected 36 combined public cases, found {combined['case_count']}")
    write_json(PUBLIC_INDEX, combined)
    return combined


def _validate_combined_index(require_instances: bool) -> dict[str, Any]:
    index = read_json(PUBLIC_INDEX)
    errors: list[str] = []
    case_ids: list[str] = []
    by_model: Counter[str] = Counter()
    by_model_type: Counter[tuple[str, str]] = Counter()
    external_input_counts: Counter[str] = Counter()

    for item in index.get("cases", []):
        case_id = item["case_id"]
        case_ids.append(case_id)
        model_id = item["model_id"]
        by_model[model_id] += 1
        by_model_type[(model_id, item["case_type"])] += 1
        if item.get("counts_toward_m4") is not False:
            errors.append(f"{case_id}: public historical case may not count toward M4")
        manifest_path = ROOT / item["manifest"]
        snapshot_path = ROOT / item["snapshot"]
        if not manifest_path.exists():
            errors.append(f"{case_id}: missing manifest {item['manifest']}")
            continue
        manifest = read_json(manifest_path)
        if manifest.get("classification") != "external_historical_case":
            errors.append(f"{case_id}: incorrect public-case classification")
        if manifest.get("counts_toward_M4") is not False:
            errors.append(f"{case_id}: manifest may not count toward M4")
        kinds = Counter(input_item.get("input_kind") for input_item in manifest.get("inputs", []))
        external_input_counts[model_id] += kinds["observed"] + kinds["derived"]
        if not snapshot_path.exists():
            errors.append(f"{case_id}: missing frozen snapshot {item['snapshot']}")
        elif item.get("snapshot_sha256") != read_json(snapshot_path).get("snapshot_sha256"):
            errors.append(f"{case_id}: index and frozen snapshot hashes disagree")
        output = ROOT / item["output"]
        if require_instances and not output.exists():
            errors.append(f"{case_id}: missing workbook {item['output']}")
        receipt_path = output.with_suffix(".receipt.json")
        if require_instances and not receipt_path.exists():
            errors.append(f"{case_id}: missing workbook receipt")
        elif require_instances:
            receipt = read_json(receipt_path)
            if receipt.get("workbook_sha256") != sha256(output):
                errors.append(f"{case_id}: workbook receipt hash is stale")

    if len(case_ids) != len(set(case_ids)):
        errors.append("public case identifiers must be globally unique")
    expected_ids = EXPECTED_EXISTING_IDS | EXPECTED_EXPANSION_IDS
    if set(by_model) != expected_ids:
        errors.append(
            f"evidence model ids {sorted(by_model)} do not match expected {sorted(expected_ids)}"
        )
    for model_id in expected_ids:
        if by_model[model_id] != 2:
            errors.append(f"{model_id}: requires exactly two public cases")
        if by_model_type[(model_id, "conventional")] != 1:
            errors.append(f"{model_id}: requires one conventional public case")
        if by_model_type[(model_id, "adversarial")] != 1:
            errors.append(f"{model_id}: requires one adversarial public case")
    for model_id in EXPECTED_EXPANSION_IDS:
        if external_input_counts[model_id] < 2:
            errors.append(f"{model_id}: evidence release has insufficient observed/derived workbook inputs")

    return {
        "status": "PASS" if not errors else "FAIL",
        "case_count": len(case_ids),
        "evidence_models": len(by_model),
        "case_counts_by_model": dict(sorted(by_model.items())),
        "external_inputs_by_expansion_model": {
            model_id: external_input_counts[model_id]
            for model_id in sorted(EXPECTED_EXPANSION_IDS)
        },
        "errors": errors,
    }


def validate(require_instances: bool) -> dict[str, Any]:
    materialized_registry()
    original_registry_path = m3_evidence.REGISTRY_PATH
    try:
        m3_evidence.REGISTRY_PATH = EXPANSION_REGISTRY
        expansion_report = m3_evidence.validate(require_instances)
        write_json(EXPANSION_REPORT, expansion_report)
        m3_evidence.REGISTRY_PATH = ORIGINAL_REGISTRY
        existing_report = m3_evidence.validate(require_instances)
    finally:
        m3_evidence.REGISTRY_PATH = original_registry_path
    combined = _validate_combined_index(require_instances)
    errors = [
        *[f"expansion: {item}" for item in expansion_report["errors"]],
        *[f"existing: {item}" for item in existing_report["errors"]],
        *[f"combined: {item}" for item in combined["errors"]],
    ]
    report = {
        "schema_version": "1.0",
        "status": "PASS" if not errors else "FAIL",
        "existing_evidence_models": existing_report["flagships"],
        "expansion_evidence_models": expansion_report["flagships"],
        "total_evidence_models": combined["evidence_models"],
        "total_public_cases": combined["case_count"],
        "m3_promoted": 0,
        "m4_promoted": 0,
        "existing_report_status": existing_report["status"],
        "expansion_report_status": expansion_report["status"],
        "combined_index": combined,
        "errors": errors,
        "warnings": [
            *existing_report["warnings"],
            *expansion_report["warnings"],
            "Human stakeholder approval remains pending for all evidence packs.",
            "Historical public cases and synthetic engineering fixtures do not count toward M4.",
        ],
        "statement": (
            "Eighteen M2 domains have public historical evidence packs. No M3 or M4 "
            "promotion occurs without human sign-off and maintained-operation history."
        ),
    }
    write_json(COMBINED_REPORT, report)
    return report


def case_outputs() -> list[Path]:
    payload = build_registry()
    return [
        ROOT / case["output"]
        for model in payload["flagships"]
        for case in model["cases"]
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--materialize", action="store_true")
    parser.add_argument("--generate-instances", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--require-instances", action="store_true")
    args = parser.parse_args()
    if not (args.materialize or args.validate):
        args.materialize = True
        args.validate = True
    if args.materialize:
        index = materialize(args.generate_instances)
        print(
            json.dumps(
                {
                    "public_cases": index["case_count"],
                    "evidence_models": index["evidence_models"],
                },
                indent=2,
            )
        )
    if args.validate:
        report = validate(args.require_instances)
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "total_evidence_models": report["total_evidence_models"],
                    "total_public_cases": report["total_public_cases"],
                    "errors": report["errors"],
                    "warnings": len(report["warnings"]),
                },
                indent=2,
            )
        )
        return 0 if report["status"] == "PASS" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
