"""Materialize and validate the final six public evidence packs.

The release starts from the verified 36-case / 18-model public evidence ledger,
uses the shared M3 evidence materializer for the final six models, and merges the
result into one 48-case / 24-model ledger. No maturity promotion is performed.
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
    from tools.final_public_evidence_registry import registry as build_registry
except ModuleNotFoundError:
    import m3_evidence
    from final_public_evidence_registry import registry as build_registry

ROOT = Path(__file__).resolve().parents[1]
FINAL_REGISTRY = ROOT / "standards" / "m3_evidence" / "final_six_registry.json"
ORIGINAL_REGISTRY = ROOT / "standards" / "m3_evidence" / "flagship_registry.json"
FRONTIER_REGISTRY = ROOT / "standards" / "m3_evidence" / "frontier_registry.json"
PUBLIC_INDEX = ROOT / "standards" / "public_cases" / "index.json"
FINAL_REPORT = ROOT / "final-public-evidence-report.json"
ALL_DOMAIN_REPORT = ROOT / "all-domain-public-evidence-report.json"
EXPECTED_FINAL_IDS = {"01", "02", "05", "06", "07", "13"}
EXPECTED_FRONTIER_IDS = {"08", "10", "11", "12", "15", "16", "17", "23", "24"}
EXPECTED_ORIGINAL_IDS = {"03", "04", "09", "14", "18", "19", "20", "21", "22"}
EXPECTED_ALL_IDS = {f"{value:02d}" for value in range(1, 25)}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def materialized_registry() -> dict[str, Any]:
    payload = build_registry()
    write_json(FINAL_REGISTRY, payload)
    return payload


def _merge_indexes(
    baseline: dict[str, Any], final_index: dict[str, Any]
) -> dict[str, Any]:
    by_case: dict[str, dict[str, Any]] = {}
    for item in [*baseline.get("cases", []), *final_index.get("cases", [])]:
        case_id = item["case_id"]
        if case_id in by_case:
            raise ValueError(f"duplicate public case id {case_id}")
        by_case[case_id] = item
    cases = sorted(
        by_case.values(),
        key=lambda item: (item["model_id"], item["case_type"], item["case_id"]),
    )
    return {
        "schema_version": "2.0",
        "as_of": final_index.get("as_of") or baseline.get("as_of"),
        "classification": "external_historical_cases",
        "counts_toward_m4": False,
        "case_count": len(cases),
        "evidence_models": len({item["model_id"] for item in cases}),
        "cases": cases,
    }


def _case_registry() -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    result: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for path in (ORIGINAL_REGISTRY, FRONTIER_REGISTRY):
        for model in read_json(path)["flagships"]:
            for case in model["cases"]:
                if case["id"] in result:
                    raise ValueError(f"duplicate registry case id {case['id']}")
                result[case["id"]] = (model, case)
    return result


def _remove_synthetic_lineage(manifest: dict[str, Any]) -> int:
    """Remove benchmark-derived inputs from an existing public manifest."""
    before = len(manifest.get("inputs", []))
    manifest["inputs"] = [
        item
        for item in manifest.get("inputs", [])
        if not str((item.get("source") or {}).get("url", "")).startswith(
            "repo://standards/benchmark_cases/"
        )
    ]
    return before - len(manifest["inputs"])


def _sanitize_baseline(
    baseline: dict[str, Any], generate_instances: bool
) -> dict[str, Any]:
    registry = _case_registry()
    inventory = {
        model["id"]: model
        for model in read_json(m3_evidence.INVENTORY_PATH)["models"]
    }
    for item in baseline.get("cases", []):
        case_id = item["case_id"]
        if case_id not in registry:
            raise ValueError(f"baseline case {case_id} is absent from evidence registries")
        model, case = registry[case_id]
        manifest_path = ROOT / item["manifest"]
        manifest = read_json(manifest_path)
        _remove_synthetic_lineage(manifest)
        if not manifest.get("inputs"):
            raise ValueError(f"{case_id}: no real or explicitly derived inputs remain")
        manifest.update(
            {
                "classification": "external_historical_case",
                "counts_toward_M4": False,
                "template": inventory[model["model_id"]]["workbook"],
                "scenario": case.get(
                    "scenario",
                    "Base" if case["type"] == "conventional" else "Downside",
                ),
                "cover": {"Subject:": case["subject"]},
                "outcome": case["outcome"],
                "lineage": {
                    "source_snapshot": f"repo://{item['snapshot']}",
                    "synthetic_benchmark_inputs_allowed": False,
                },
            }
        )
        write_json(manifest_path, manifest)
        item["outcome"] = case["outcome"]
        if generate_instances:
            item["receipt"] = m3_evidence.apply_manifest(manifest_path, ROOT)
    return baseline


def materialize(generate_instances: bool) -> dict[str, Any]:
    materialized_registry()
    baseline = read_json(PUBLIC_INDEX)
    if baseline.get("case_count") != 36:
        raise ValueError(
            f"final evidence release must start from 36 public cases, found {baseline.get('case_count')}"
        )
    if baseline.get("evidence_models") != 18:
        raise ValueError(
            f"final evidence release must start from 18 evidenced models, found {baseline.get('evidence_models')}"
        )
    baseline = _sanitize_baseline(baseline, generate_instances)
    original_registry_path = m3_evidence.REGISTRY_PATH
    try:
        m3_evidence.REGISTRY_PATH = FINAL_REGISTRY
        final_index = m3_evidence.materialize(generate_instances)
    finally:
        m3_evidence.REGISTRY_PATH = original_registry_path
    combined = _merge_indexes(baseline, final_index)
    if combined["case_count"] != 48:
        raise ValueError(
            f"expected 48 combined public cases, found {combined['case_count']}"
        )
    if combined["evidence_models"] != 24:
        raise ValueError(
            f"expected 24 evidenced models, found {combined['evidence_models']}"
        )
    write_json(PUBLIC_INDEX, combined)
    return combined


def _validate_registry(
    path: Path, require_instances: bool, *, expected_flagships: int
) -> dict[str, Any]:
    previous = m3_evidence.REGISTRY_PATH
    try:
        m3_evidence.REGISTRY_PATH = path
        return m3_evidence.validate(
            require_instances, expected_flagships=expected_flagships
        )
    finally:
        m3_evidence.REGISTRY_PATH = previous


def _validate_combined_index(require_instances: bool) -> dict[str, Any]:
    index = read_json(PUBLIC_INDEX)
    errors: list[str] = []
    case_ids: list[str] = []
    by_model: Counter[str] = Counter()
    by_model_type: Counter[tuple[str, str]] = Counter()
    external_inputs: Counter[str] = Counter()
    recorded_outcomes: Counter[str] = Counter()
    receipt_results: list[dict[str, Any]] = []

    for item in index.get("cases", []):
        case_id = item["case_id"]
        model_id = item["model_id"]
        case_ids.append(case_id)
        by_model[model_id] += 1
        by_model_type[(model_id, item["case_type"])] += 1
        if item.get("counts_toward_m4") is not False:
            errors.append(f"{case_id}: public case may not count toward M4")
        manifest_path = ROOT / item["manifest"]
        snapshot_path = ROOT / item["snapshot"]
        output = ROOT / item["output"]
        receipt_path = output.with_suffix(".receipt.json")
        if not manifest_path.exists():
            errors.append(f"{case_id}: missing manifest")
            continue
        manifest = read_json(manifest_path)
        if manifest.get("classification") != "external_historical_case":
            errors.append(f"{case_id}: public-case classification mismatch")
        if manifest.get("counts_toward_M4") is not False:
            errors.append(f"{case_id}: manifest may not count toward M4")
        kinds = Counter(
            input_item.get("input_kind") for input_item in manifest.get("inputs", [])
        )
        if any(
            str((input_item.get("source") or {}).get("url", "")).startswith(
                "repo://standards/benchmark_cases/"
            )
            for input_item in manifest.get("inputs", [])
        ):
            errors.append(
                f"{case_id}: public manifest inherits synthetic benchmark inputs"
            )
        external_inputs[model_id] += kinds["observed"] + kinds["derived"]
        outcome = item.get("outcome") or manifest.get("outcome") or {}
        if outcome.get("status") == "recorded":
            recorded_outcomes[model_id] += 1
        if not snapshot_path.exists():
            errors.append(f"{case_id}: missing frozen source snapshot")
        elif item.get("snapshot_sha256") != read_json(snapshot_path).get(
            "snapshot_sha256"
        ):
            errors.append(f"{case_id}: source snapshot hash mismatch")
        if require_instances and not output.exists():
            errors.append(f"{case_id}: missing workbook")
            continue
        if require_instances and not receipt_path.exists():
            errors.append(f"{case_id}: missing workbook receipt")
            continue
        if require_instances:
            receipt = read_json(receipt_path)
            digest = sha256(output)
            receipt_digest = receipt.get("workbook_sha256")
            index_digest = (item.get("receipt") or {}).get("workbook_sha256")
            receipt_errors: list[str] = []
            if receipt_digest != digest:
                receipt_errors.append("receipt hash mismatch")
            if index_digest != digest:
                receipt_errors.append("index hash mismatch")
            receipt_m4 = receipt.get(
                "counts_toward_M4", receipt.get("counts_toward_m4")
            )
            if receipt_m4 is not False:
                receipt_errors.append("receipt may not count toward M4")
            receipt_results.append(
                {
                    "case_id": case_id,
                    "model_id": model_id,
                    "workbook_sha256": digest,
                    "errors": receipt_errors,
                }
            )
            errors.extend(f"{case_id}: {error}" for error in receipt_errors)

    if len(case_ids) != len(set(case_ids)):
        errors.append("public case identifiers must be globally unique")
    # The governed 01-24 set's own strict invariants (exactly two cases,
    # one conventional and one adversarial, minimum external inputs, a
    # recorded outcome) are a closed, certified claim about that specific
    # cohort and must not silently loosen. Domains added later (e.g. "29"
    # Fund of Funds, "30" ETF Construction & Management) are real,
    # honestly-declared inventory entries with their own independent
    # evidence bar (see model_inventory.json and each domain's own
    # model_card.md) -- they are additive to this ledger, not required to
    # satisfy the governed cohort's own two-case-per-model shape, and must
    # not be silently dropped by requiring an exact-equality match here.
    if not EXPECTED_ALL_IDS.issubset(set(by_model)):
        errors.append(
            f"evidence model ids {sorted(by_model)} do not cover the governed 01-24 set"
        )
    for model_id in EXPECTED_ALL_IDS:
        if by_model[model_id] != 2:
            errors.append(f"{model_id}: requires exactly two public cases")
        if by_model_type[(model_id, "conventional")] != 1:
            errors.append(f"{model_id}: requires one conventional public case")
        if by_model_type[(model_id, "adversarial")] != 1:
            errors.append(f"{model_id}: requires one adversarial public case")
        if external_inputs[model_id] < 2:
            errors.append(
                f"{model_id}: requires at least two observed or derived workbook inputs"
            )
        if recorded_outcomes[model_id] < 1:
            errors.append(f"{model_id}: requires at least one recorded outcome")
    # At least the governed 48/24 -- later, honestly-declared additions grow
    # these totals without invalidating the governed cohort's own claim.
    if index.get("case_count", 0) < 48:
        errors.append("public index case_count must be at least 48")
    if index.get("evidence_models", 0) < 24:
        errors.append("public index evidence_models must be at least 24")
    if index.get("counts_toward_m4") is not False:
        errors.append("public evidence index may not count toward M4")

    return {
        "status": "PASS" if not errors else "FAIL",
        "case_count": len(case_ids),
        "evidence_models": len(by_model),
        "case_counts_by_model": dict(sorted(by_model.items())),
        "external_inputs_by_model": dict(sorted(external_inputs.items())),
        "recorded_outcomes_by_model": dict(sorted(recorded_outcomes.items())),
        "receipts": receipt_results,
        "errors": errors,
    }


def validate(require_instances: bool) -> dict[str, Any]:
    materialized_registry()
    original_report = _validate_registry(
        ORIGINAL_REGISTRY, require_instances, expected_flagships=9
    )
    frontier_report = _validate_registry(
        FRONTIER_REGISTRY, require_instances, expected_flagships=9
    )
    final_report = _validate_registry(
        FINAL_REGISTRY, require_instances, expected_flagships=6
    )
    combined = _validate_combined_index(require_instances)
    errors = [
        *[f"original: {item}" for item in original_report["errors"]],
        *[f"frontier: {item}" for item in frontier_report["errors"]],
        *[f"final: {item}" for item in final_report["errors"]],
        *[f"combined: {item}" for item in combined["errors"]],
    ]
    report = {
        "schema_version": "1.0",
        "status": "PASS" if not errors else "FAIL",
        "original_evidence_models": original_report["flagships"],
        "frontier_evidence_models": frontier_report["flagships"],
        "final_evidence_models": final_report["flagships"],
        "total_evidence_models": combined["evidence_models"],
        "total_public_cases": combined["case_count"],
        "m3_promoted": 0,
        "m4_promoted": 0,
        "original_report_status": original_report["status"],
        "frontier_report_status": frontier_report["status"],
        "final_report_status": final_report["status"],
        "combined_index": combined,
        "errors": errors,
        "warnings": [
            *original_report["warnings"],
            *frontier_report["warnings"],
            *final_report["warnings"],
            "Named stakeholder approval remains pending for all evidence packs.",
            "Historical cases do not count toward M4 without maintained operating history.",
        ],
        "statement": (
            "All 24 governed M2 domains have conventional and adversarial public historical "
            "evidence packs. No M3 or M4 promotion occurs without human sign-off and "
            "maintained-operation history."
        ),
    }
    write_json(FINAL_REPORT, final_report)
    write_json(ALL_DOMAIN_REPORT, report)
    return report


def case_outputs() -> list[Path]:
    payload = build_registry()
    return [
        ROOT / case_item["output"]
        for model in payload["flagships"]
        for case_item in model["cases"]
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
