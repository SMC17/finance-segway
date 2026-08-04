"""Validate the six-model legacy engine hardening and release state."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from tools.legacy_engine_oracles import ORACLES, validate_case
except ModuleNotFoundError:
    from legacy_engine_oracles import ORACLES, validate_case

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "standards" / "frontier" / "legacy_engine_registry.json"
INVENTORY = ROOT / "standards" / "model_inventory.json"
BENCHMARK_INDEX = ROOT / "standards" / "benchmark_cases" / "index.json"
EXPECTED_IDS = {"01", "02", "05", "06", "07", "13"}
RELEASE_STAGED = "release_staged"
RELEASE_APPLIED = "applied_release_validated"
EXPECTED_IDENTITIES = {
    "01": {"enterprise_to_equity_bridge", "per_share_identity", "deal_eps_identity"},
    "02": {"cash_rollforward", "debt_rollforward", "net_debt_identity"},
    "05": {"debt_rollforward", "recovery_lgd_identity", "recovery_claim_bound"},
    "06": {"debt_rollforward", "weighted_cost_identity", "refinancing_gap_identity"},
    "07": {
        "debt_ratio_identity",
        "stabilizing_primary_balance_identity",
        "coverage_nonnegative",
    },
    "13": {"post_money_identity", "ownership_conservation", "exit_proceeds_identity"},
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _model_id_from_template(path: str) -> str:
    return path.split("/", 1)[0].split("_", 1)[0]


def validate() -> dict[str, Any]:
    registry = _load(REGISTRY)
    inventory = _load(INVENTORY)
    benchmark_index = _load(BENCHMARK_INDEX)
    inventory_by_id = {item["id"]: item for item in inventory["models"]}
    status = registry.get("status", "planned")
    candidate_active = status in {RELEASE_STAGED, RELEASE_APPLIED}
    expected_benchmark_count = 2 if status == RELEASE_APPLIED else 0
    errors: list[str] = []
    warnings: list[str] = []
    results: list[dict[str, Any]] = []

    models = registry.get("models", [])
    registry_ids = {item.get("model_id") for item in models}
    if registry_ids != EXPECTED_IDS:
        errors.append(
            f"registry ids {sorted(registry_ids)} do not match legacy cohort {sorted(EXPECTED_IDS)}"
        )
    if set(ORACLES) != EXPECTED_IDS:
        errors.append("oracle dispatch does not exactly cover the six legacy models")
    if status not in {"planned", RELEASE_STAGED, RELEASE_APPLIED}:
        errors.append(f"unsupported legacy-engine release status {status}")

    benchmark_counts = {model_id: 0 for model_id in EXPECTED_IDS}
    for item in benchmark_index.get("instances", []):
        model_id = item.get("model_id") or _model_id_from_template(item["template"])
        if model_id in benchmark_counts:
            benchmark_counts[model_id] += 1
    for model_id, count in benchmark_counts.items():
        if count != expected_benchmark_count:
            errors.append(
                f"{model_id}: release status {status} requires {expected_benchmark_count} "
                f"benchmark instances, found {count}"
            )
    if status == RELEASE_STAGED:
        warnings.append(
            "Release is staged in a workflow tree; benchmark index finalization is still pending."
        )

    case_ids: list[str] = []
    for item in models:
        model_id = item["model_id"]
        inventory_model = inventory_by_id.get(model_id)
        if inventory_model is None:
            errors.append(f"{model_id}: missing from model inventory")
            continue
        if inventory_model.get("declared_maturity") != "M2":
            errors.append(f"{model_id}: release must preserve conservative M2 maturity")
        expected_builder = (
            item.get("candidate_builder") if candidate_active else item.get("current_builder")
        )
        if inventory_model.get("builder") != expected_builder:
            errors.append(
                f"{model_id}: status {status} requires builder {expected_builder}, "
                f"found {inventory_model.get('builder')}"
            )
        if candidate_active and inventory_model.get("reference_checks") != item.get(
            "reference_checks"
        ):
            errors.append(f"{model_id}: released reference checks do not match registry")
        candidate_builder = item.get("candidate_builder", "")
        if not candidate_builder.startswith("tools/builders/build_") or not candidate_builder.endswith("_release.py"):
            errors.append(f"{model_id}: invalid candidate release-builder path")
        if candidate_builder == item.get("current_builder"):
            errors.append(f"{model_id}: candidate builder must replace the legacy builder")
        if not item.get("required_new_sheets"):
            errors.append(f"{model_id}: no required release sheets declared")
        if not item.get("reference_checks"):
            errors.append(f"{model_id}: no reference checks declared")
        references = item.get("references", [])
        if len(references) < 2:
            errors.append(f"{model_id}: fewer than two authoritative references")
        for reference in references:
            if not reference.get("url", "").startswith("https://"):
                errors.append(f"{model_id}: reference URL must use HTTPS")
            if not all(reference.get(key) for key in ("authority", "title", "use")):
                errors.append(f"{model_id}: incomplete reference metadata")

        cases = item.get("cases", [])
        if len(cases) != 2 or {case.get("type") for case in cases} != {
            "conventional",
            "adversarial",
        }:
            errors.append(
                f"{model_id}: requires exactly one conventional and one adversarial case"
            )
        model_result = {
            "model_id": model_id,
            "domain": item["domain"],
            "release_status": status,
            "expected_builder": expected_builder,
            "benchmark_instances": benchmark_counts[model_id],
            "cases": [],
        }
        for case in cases:
            case_ids.append(case["id"])
            try:
                result = validate_case(model_id, case["inputs"])
            except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
                errors.append(f"{model_id}/{case['id']}: oracle execution failed: {exc}")
                continue
            if set(result["identity_checks"]) != EXPECTED_IDENTITIES[model_id]:
                errors.append(
                    f"{model_id}/{case['id']}: identity set {sorted(result['identity_checks'])} "
                    f"does not match expected {sorted(EXPECTED_IDENTITIES[model_id])}"
                )
            if result["identity_status"] != "PASS":
                errors.append(f"{model_id}/{case['id']}: financial identities failed")
            if case["type"] == "conventional" and result["active_risk_flags"]:
                errors.append(
                    f"{model_id}/{case['id']}: conventional case unexpectedly flagged "
                    f"{result['active_risk_flags']}"
                )
            if case["type"] == "adversarial" and not result["active_risk_flags"]:
                errors.append(
                    f"{model_id}/{case['id']}: adversarial case triggered no failure state"
                )
            model_result["cases"].append(
                {
                    "id": case["id"],
                    "type": case["type"],
                    "identity_status": result["identity_status"],
                    "active_risk_flags": result["active_risk_flags"],
                    "metrics": result["metrics"],
                }
            )
        results.append(model_result)

    if len(case_ids) != len(set(case_ids)):
        errors.append("legacy hardening case identifiers must be globally unique")
    claim = registry.get("claim_boundary", {})
    if claim.get("declared_maturity") != "M2":
        errors.append("legacy engine program may not pre-claim M3")
    if claim.get("m3_promoted") != 0 or claim.get("m4_promoted") != 0:
        errors.append("legacy engine program may not manufacture M3 or M4 promotions")
    if claim.get("synthetic_cases_count_toward_m4") is not False:
        errors.append("synthetic benchmark cases must never count toward M4")

    return {
        "schema_version": "1.1",
        "status": "PASS" if not errors else "FAIL",
        "release_status": status,
        "models": len(models),
        "cases": len(case_ids),
        "benchmark_counts": benchmark_counts,
        "results": results,
        "errors": errors,
        "warnings": warnings,
        "statement": claim.get("statement"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report", type=Path, default=ROOT / "legacy-engine-hardening-report.json"
    )
    args = parser.parse_args()
    report = validate()
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "status",
                    "release_status",
                    "models",
                    "cases",
                    "benchmark_counts",
                    "errors",
                    "warnings",
                )
            },
            indent=2,
        )
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
