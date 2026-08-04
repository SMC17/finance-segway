"""Validate the independent hardening and promotion state of the nine domains."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from tools.domain_hardening_oracles import ORACLES, validate_case
except ModuleNotFoundError:
    from domain_hardening_oracles import ORACLES, validate_case

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "standards" / "domain_hardening" / "m1_registry.json"
INVENTORY = ROOT / "standards" / "model_inventory.json"
CANDIDATES = (
    ROOT / "standards" / "domain_hardening" / "m2_promotion_candidates.json"
)
EXPECTED_M1_IDS = {"08", "10", "11", "12", "15", "16", "17", "23", "24"}
VALIDATED_PROMOTION_STATUS = "applied_release_validated"


def validate() -> dict[str, Any]:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    candidates = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    inventory_by_id = {item["id"]: item for item in inventory["models"]}
    candidate_by_id = {
        item["model_id"]: item for item in candidates.get("candidates", [])
    }
    promotion_validated = candidates.get("status") == VALIDATED_PROMOTION_STATUS
    expected_maturity = "M2" if promotion_validated else "M1"
    expected_integration = "validated" if promotion_validated else "pending"
    errors: list[str] = []
    warnings: list[str] = []
    results: list[dict[str, Any]] = []

    domains = registry.get("domains", [])
    registry_ids = {item.get("model_id") for item in domains}
    if registry_ids != EXPECTED_M1_IDS:
        errors.append(
            f"registry ids {sorted(registry_ids)} do not match hardening cohort "
            f"{sorted(EXPECTED_M1_IDS)}"
        )
    if set(ORACLES) != EXPECTED_M1_IDS:
        errors.append("oracle dispatch does not exactly cover the hardening cohort")
    if set(candidate_by_id) != EXPECTED_M1_IDS:
        errors.append("promotion candidate registry does not exactly cover the cohort")

    case_ids: list[str] = []
    for domain in domains:
        model_id = domain["model_id"]
        inventory_model = inventory_by_id.get(model_id)
        candidate = candidate_by_id.get(model_id)
        if not inventory_model:
            errors.append(f"{model_id}: missing from model inventory")
            continue
        if inventory_model["declared_maturity"] != expected_maturity:
            if promotion_validated:
                errors.append(
                    f"{model_id}: validated promotion requires committed M2 maturity"
                )
            else:
                errors.append(
                    f"{model_id}: hardening program may not silently change declared maturity"
                )
        if promotion_validated and candidate:
            if inventory_model.get("builder") != candidate.get("candidate_builder"):
                errors.append(f"{model_id}: validated promotion builder mismatch")
            if inventory_model.get("reference_checks") != candidate.get(
                "reference_checks"
            ):
                errors.append(
                    f"{model_id}: validated promotion reference-check mismatch"
                )
        if not domain.get("reference_checks"):
            errors.append(f"{model_id}: no independent reference checks declared")
        references = domain.get("references", [])
        if not references:
            errors.append(f"{model_id}: no authoritative references declared")
        for reference in references:
            if not reference.get("url", "").startswith("https://"):
                errors.append(f"{model_id}: reference URL must use HTTPS")
            if not all(reference.get(key) for key in ("authority", "title", "use")):
                errors.append(f"{model_id}: incomplete reference metadata")

        cases = domain.get("cases", [])
        case_types = {case.get("type") for case in cases}
        if case_types != {"conventional", "adversarial"} or len(cases) != 2:
            errors.append(
                f"{model_id}: requires exactly one conventional and one adversarial case"
            )

        domain_result = {
            "model_id": model_id,
            "domain": domain["domain"],
            "declared_maturity": inventory_model["declared_maturity"],
            "reference_checks": domain["reference_checks"],
            "references": len(references),
            "cases": [],
            "workbook_integration": expected_integration,
        }
        for case in cases:
            case_ids.append(case["id"])
            try:
                result = validate_case(model_id, case["inputs"])
            except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
                errors.append(
                    f"{model_id}/{case['id']}: oracle execution failed: {exc}"
                )
                continue
            if result["identity_status"] != "PASS":
                failed = [
                    name
                    for name, passed in result["identity_checks"].items()
                    if not passed
                ]
                errors.append(
                    f"{model_id}/{case['id']}: failed identities {failed}"
                )
            if case["type"] == "conventional" and result["active_risk_flags"]:
                warnings.append(
                    f"{model_id}/{case['id']}: conventional case has active flags "
                    f"{result['active_risk_flags']}"
                )
            if case["type"] == "adversarial" and not result["active_risk_flags"]:
                errors.append(
                    f"{model_id}/{case['id']}: adversarial case triggers no risk flag"
                )
            domain_result["cases"].append(
                {
                    "case_id": case["id"],
                    "type": case["type"],
                    "identity_status": result["identity_status"],
                    "active_risk_flags": result["active_risk_flags"],
                    "metrics": result["metrics"],
                }
            )
        results.append(domain_result)

    if len(case_ids) != len(set(case_ids)):
        errors.append("case identifiers must be globally unique")

    promotion_statement = (
        "The nine-domain promotion is committed and validated at M2; independent "
        "oracles, workbook contracts, benchmark receipts, and canonical builders "
        "remain mandatory. No M3 or M4 claim is made."
        if promotion_validated
        else (
            "Independent oracle coverage is necessary but no domain is promoted until "
            "workbook contracts and decision surfaces reconcile to these results."
        )
    )
    return {
        "schema_version": "1.1",
        "program": registry.get("program"),
        "promotion_status": candidates.get("status"),
        "expected_maturity": expected_maturity,
        "domains": len(domains),
        "cases": len(case_ids),
        "errors": errors,
        "warnings": warnings,
        "results": results,
        "status": "PASS" if not errors else "FAIL",
        "promotion_statement": promotion_statement,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report", type=Path, default=ROOT / "m1-domain-hardening-report.json"
    )
    args = parser.parse_args()
    report = validate()
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "promotion_status",
                    "expected_maturity",
                    "domains",
                    "cases",
                    "status",
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
