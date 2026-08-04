"""Validate the all-domain evidence, engine-hardening and network-risk program."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from tools.cross_domain_oracles import ORACLES, validate_case
except ModuleNotFoundError:
    from cross_domain_oracles import ORACLES, validate_case

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "standards" / "frontier" / "frontier_registry.json"
LEGACY_REGISTRY = ROOT / "standards" / "frontier" / "legacy_engine_registry.json"
INVENTORY = ROOT / "standards" / "model_inventory.json"
FLAGSHIPS = ROOT / "standards" / "m3_evidence" / "flagship_registry.json"
BENCHMARK_INDEX = ROOT / "standards" / "benchmark_cases" / "index.json"
PUBLIC_INDEX = ROOT / "standards" / "public_cases" / "index.json"
EXPECTED_ENGINE_IDS = {
    "capital_allocation",
    "liquidity_contagion",
    "counterparty_network",
    "collateral_margin",
    "tax_leakage",
    "legal_entity_waterfall",
    "regime_scenario",
}
EXPECTED_LEGACY_IDS = {"01", "02", "05", "06", "07", "13"}
LEGACY_RELEASE_APPLIED = "applied_release_validated"
LEGACY_RELEASE_STAGED = "release_staged"


def _model_id_from_path(path: str) -> str:
    prefix = str(path).split("/", 1)[0]
    return prefix.split("_", 1)[0]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _expected_mismatches(actual: Any, expected: Any, path: str = "result") -> list[str]:
    """Compare a declared regression subset without freezing unrelated output fields."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected mapping, found {type(actual).__name__}"]
        errors = []
        for key, value in expected.items():
            if key not in actual:
                errors.append(f"{path}.{key}: missing")
            else:
                errors.extend(_expected_mismatches(actual[key], value, f"{path}.{key}"))
        return errors
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return [] if abs(float(actual) - float(expected)) <= 1e-7 else [
            f"{path}: expected {expected}, found {actual}"
        ]
    return [] if actual == expected else [f"{path}: expected {expected!r}, found {actual!r}"]


def validate() -> dict[str, Any]:
    registry = _load(REGISTRY)
    legacy_registry = _load(LEGACY_REGISTRY)
    legacy_status = legacy_registry.get("status", "planned")
    inventory = _load(INVENTORY)
    flagships = _load(FLAGSHIPS)
    benchmark_index = _load(BENCHMARK_INDEX)
    public_index = _load(PUBLIC_INDEX)

    errors: list[str] = []
    warnings: list[str] = []
    results: list[dict[str, Any]] = []

    inventory_ids = {item["id"] for item in inventory["models"]}
    maturity = Counter(item["declared_maturity"] for item in inventory["models"])
    if inventory_ids != {f"{value:02d}" for value in range(1, 25)}:
        errors.append("model inventory must contain the exact governed 01-24 domain set")
    if maturity != Counter({"M2": 24}):
        errors.append(
            f"frontier program requires a conservative 24-model M2 base, found {dict(maturity)}"
        )

    flagship_ids = {item["model_id"] for item in flagships["flagships"]}
    cohorts = registry["cohorts"]
    declared_existing = set(cohorts["existing_m3_evidence"])
    declared_expansion = set(cohorts["evidence_expansion"])
    declared_legacy = set(cohorts["legacy_engine_hardening"])
    declared_recent = set(cohorts["recently_hardened_evidence"])

    if flagship_ids != declared_existing:
        errors.append("existing M3 evidence cohort must equal the flagship registry")
    if declared_existing | declared_expansion != inventory_ids:
        errors.append("existing and expansion cohorts must partition the 24-model inventory")
    if declared_existing & declared_expansion:
        errors.append("existing and expansion evidence cohorts must be disjoint")
    if len(declared_expansion) != 15:
        errors.append(
            f"evidence expansion must contain 15 domains, found {len(declared_expansion)}"
        )
    if declared_legacy != EXPECTED_LEGACY_IDS:
        errors.append(
            f"legacy hardening cohort {sorted(declared_legacy)} does not match "
            f"{sorted(EXPECTED_LEGACY_IDS)}"
        )
    if declared_legacy | declared_recent != declared_expansion:
        errors.append(
            "legacy and recently hardened cohorts must partition the 15-domain expansion"
        )

    benchmark_counts: Counter[str] = Counter()
    for item in benchmark_index.get("instances", []):
        model_id = item.get("model_id") or _model_id_from_path(item["template"])
        benchmark_counts[model_id] += 1
    for model_id in declared_recent:
        if benchmark_counts[model_id] != 2:
            errors.append(
                f"{model_id}: recently hardened model must retain two benchmark instances"
            )
    if legacy_status == "planned":
        inferred_legacy = {
            model_id
            for model_id in declared_expansion
            if benchmark_counts[model_id] == 0
        }
        if inferred_legacy != declared_legacy:
            errors.append(
                "planned legacy cohort must be derived from zero benchmark coverage: "
                f"inferred {sorted(inferred_legacy)}"
            )
    elif legacy_status == LEGACY_RELEASE_STAGED:
        invalid = {
            model_id: benchmark_counts[model_id]
            for model_id in declared_legacy
            if benchmark_counts[model_id] not in (0, 2)
        }
        if invalid:
            errors.append(f"staged legacy release has partial benchmark coverage {invalid}")
        warnings.append(
            "The six-engine release is staged in a workflow tree; final index application remains pending."
        )
    elif legacy_status == LEGACY_RELEASE_APPLIED:
        for model_id in declared_legacy:
            if benchmark_counts[model_id] != 2:
                errors.append(
                    f"{model_id}: applied legacy release requires two benchmark instances"
                )
    else:
        errors.append(f"unsupported legacy release status {legacy_status}")

    public_counts: Counter[str] = Counter(
        item["model_id"] for item in public_index.get("cases", [])
    )
    for model_id in declared_existing:
        if public_counts[model_id] != 2:
            errors.append(
                f"{model_id}: existing evidence model must retain two public cases"
            )
    for model_id in declared_expansion:
        if public_counts[model_id] not in (0, 2):
            errors.append(
                f"{model_id}: public evidence must be released atomically as a two-case pair"
            )

    claim = registry["claim_boundary"]
    if claim.get("declared_maturity") != "M2":
        errors.append("frontier program may not pre-claim M3")
    if claim.get("m3_promoted") != 0 or claim.get("m4_promoted") != 0:
        errors.append("frontier program may not manufacture M3 or M4 promotions")
    if claim.get("synthetic_cases_count_toward_m4") is not False:
        errors.append("synthetic engineering fixtures must never count toward M4")

    requested_taxonomy = {
        item["requested_domain"]: item for item in registry["taxonomy_decisions"]
    }
    if set(requested_taxonomy) != {"Commercial Banking", "FX"}:
        errors.append(
            "taxonomy decisions must explicitly resolve Commercial Banking and FX"
        )
    if requested_taxonomy.get("Commercial Banking", {}).get("current_mapping") != [
        "05",
        "06",
    ]:
        errors.append(
            "Commercial Banking must map to Private Credit and Debt Finance until separately engineered"
        )
    if requested_taxonomy.get("FX", {}).get("current_mapping") != [
        "09",
        "21",
        "22",
    ]:
        errors.append(
            "FX must map to Risk, Fixed Income & Rates, and Quantitative until separately engineered"
        )

    references = registry["cross_domain"].get("references", [])
    if len(references) < 6:
        errors.append(
            "cross-domain program requires a primary or authoritative reference atlas"
        )
    for reference in references:
        if not reference.get("url", "").startswith("https://"):
            errors.append(f"cross-domain reference must use HTTPS: {reference}")
        if not all(reference.get(key) for key in ("authority", "title", "use")):
            errors.append(f"incomplete cross-domain reference metadata: {reference}")

    engines = registry["cross_domain"].get("engines", [])
    engine_ids = {item["id"] for item in engines}
    if engine_ids != EXPECTED_ENGINE_IDS:
        errors.append(
            f"cross-domain engine ids {sorted(engine_ids)} do not match required set"
        )
    if set(ORACLES) != EXPECTED_ENGINE_IDS:
        errors.append("oracle dispatch does not exactly cover the cross-domain engine set")

    case_ids: list[str] = []
    for engine in engines:
        engine_id = engine["id"]
        cases = engine.get("cases", [])
        if len(cases) != 2 or {case.get("type") for case in cases} != {
            "conventional",
            "adversarial",
        }:
            errors.append(
                f"{engine_id}: requires exactly one conventional and one adversarial case"
            )
        engine_result = {"engine": engine_id, "cases": []}
        for case in cases:
            case_ids.append(case["id"])
            try:
                result = validate_case(engine_id, case["inputs"])
            except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
                errors.append(
                    f"{engine_id}/{case['id']}: oracle execution failed: {exc}"
                )
                continue
            expected_identities = set(engine.get("identities", []))
            if set(result["identity_checks"]) != expected_identities:
                errors.append(
                    f"{engine_id}/{case['id']}: identity set "
                    f"{sorted(result['identity_checks'])} does not match registry "
                    f"{sorted(expected_identities)}"
                )
            if result["identity_status"] != "PASS":
                errors.append(
                    f"{engine_id}/{case['id']}: financial identities failed"
                )
            if case["type"] == "conventional" and result["active_risk_flags"]:
                errors.append(
                    f"{engine_id}/{case['id']}: conventional case unexpectedly flagged "
                    f"{result['active_risk_flags']}"
                )
            if case["type"] == "adversarial" and not result["active_risk_flags"]:
                errors.append(
                    f"{engine_id}/{case['id']}: adversarial case triggered no failure state"
                )
            for mismatch in _expected_mismatches(result, case.get("expected", {})):
                errors.append(f"{engine_id}/{case['id']}: {mismatch}")
            engine_result["cases"].append(
                {
                    "id": case["id"],
                    "type": case["type"],
                    "identity_status": result["identity_status"],
                    "active_risk_flags": result["active_risk_flags"],
                    "metrics": result["metrics"],
                }
            )
        results.append(engine_result)
    if len(case_ids) != len(set(case_ids)):
        errors.append("cross-domain case identifiers must be globally unique")

    missing_public = [
        model_id for model_id in declared_expansion if public_counts[model_id] == 0
    ]
    if missing_public:
        warnings.append(
            f"Public evidence remains incomplete for {sorted(missing_public)}; these models "
            "remain M2 and do not count toward M4."
        )
    if legacy_status != LEGACY_RELEASE_APPLIED:
        warnings.append(
            "The six legacy engines still require an applied release with benchmark pairs."
        )
    elif any(public_counts[model_id] == 0 for model_id in declared_legacy):
        warnings.append(
            "The six released legacy engines require public historical evidence packs before the all-domain evidence ledger is complete."
        )

    return {
        "schema_version": "1.1",
        "status": "PASS" if not errors else "FAIL",
        "legacy_release_status": legacy_status,
        "inventory_models": len(inventory_ids),
        "maturity_distribution": dict(maturity),
        "existing_m3_evidence_models": len(declared_existing),
        "evidence_expansion_models": len(declared_expansion),
        "legacy_engine_hardening_models": len(declared_legacy),
        "cross_domain_engines": len(engine_ids),
        "cross_domain_cases": len(case_ids),
        "benchmark_counts": dict(sorted(benchmark_counts.items())),
        "public_case_counts": dict(sorted(public_counts.items())),
        "results": results,
        "errors": errors,
        "warnings": warnings,
        "statement": registry["claim_boundary"]["statement"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report", type=Path, default=ROOT / "frontier-program-report.json"
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
                    "legacy_release_status",
                    "inventory_models",
                    "existing_m3_evidence_models",
                    "evidence_expansion_models",
                    "legacy_engine_hardening_models",
                    "cross_domain_engines",
                    "cross_domain_cases",
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
