"""Atomic release transaction for the six legacy M2 finance engines."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

try:
    from tools.institutional_surface import (
        apply_surface,
        profiles_by_id,
        validate_workbook_surface,
    )
    from tools.model_instance_release import apply_manifest
    from tools.validate_legacy_release_workbooks import (
        SPECS,
        build_workbook,
        validate_workbook,
    )
except ModuleNotFoundError:
    from institutional_surface import apply_surface, profiles_by_id, validate_workbook_surface
    from model_instance_release import apply_manifest
    from validate_legacy_release_workbooks import SPECS, build_workbook, validate_workbook

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "standards" / "frontier" / "legacy_engine_registry.json"
INVENTORY_PATH = ROOT / "standards" / "model_inventory.json"
BENCHMARK_INDEX_PATH = ROOT / "standards" / "benchmark_cases" / "index.json"
BENCHMARK_DIR = ROOT / "standards" / "benchmark_cases"
EXPECTED_IDS = {"01", "02", "05", "06", "07", "13"}
RELEASE_STATUS = "applied_release_validated"

CANONICAL_PATHS = {
    "01": "01_Investment_Banking/_template_BASE.xlsx",
    "02": "02_Corporate_Finance/_template_BASE.xlsx",
    "05": "05_Private_Credit/_template_CREDIT.xlsx",
    "06": "06_Debt_Finance/_template_CREDIT.xlsx",
    "07": "07_Public_Finance/_template_PUBLIC_FINANCE.xlsx",
    "13": "13_Venture_Capital/_template_VC.xlsx",
}

CASE_NAMES = {
    "01": {
        "conventional": ("ib-reference-transaction", "benchmark_reference_transaction.xlsx"),
        "adversarial": ("ib-adversarial-overpay", "benchmark_adversarial_overpay.xlsx"),
    },
    "02": {
        "conventional": ("corp-reference-funded", "benchmark_reference_treasury.xlsx"),
        "adversarial": ("corp-adversarial-liquidity", "benchmark_adversarial_liquidity.xlsx"),
    },
    "05": {
        "conventional": ("credit-reference-deleveraging", "benchmark_reference_deleveraging.xlsx"),
        "adversarial": ("credit-adversarial-pik-trap", "benchmark_adversarial_pik_trap.xlsx"),
    },
    "06": {
        "conventional": ("debt-reference-refinancing", "benchmark_reference_refinancing.xlsx"),
        "adversarial": ("debt-adversarial-maturity-wall", "benchmark_adversarial_maturity_wall.xlsx"),
    },
    "07": {
        "conventional": ("public-reference-stable", "benchmark_reference_stable.xlsx"),
        "adversarial": ("public-adversarial-debt-distress", "benchmark_adversarial_debt_distress.xlsx"),
    },
    "13": {
        "conventional": ("vc-reference-up-round", "benchmark_reference_up_round.xlsx"),
        "adversarial": ("vc-adversarial-down-round", "benchmark_adversarial_down_round.xlsx"),
    },
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source(case_id: str) -> dict[str, Any]:
    return {
        "name": f"Finance-Segway six-engine fixture {case_id}",
        "url": "repo://standards/frontier/legacy_engine_registry.json",
        "as_of": "2026-08-04",
        "notes": (
            "Synthetic engineering fixture derived from the independent legacy-engine "
            "oracle registry; not investment evidence and not M4 evidence"
        ),
    }


def _both(sheet: str, row: int, value: Any, source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"sheet": sheet, "cell": f"C{row}", "value": value, "source": source},
        {"sheet": sheet, "cell": f"D{row}", "value": value, "source": source},
    ]


def _case_inputs(model_id: str, case_type: str, inputs: dict[str, Any], case_id: str) -> list[dict[str, Any]]:
    source = _source(case_id)
    items: list[dict[str, Any]] = []
    if model_id == "01":
        tx_rows = {
            "enterprise_value": 5,
            "debt": 6,
            "cash": 7,
            "shares": 8,
            "offer_price": 9,
            "discount_rate": 10,
            "terminal_growth": 11,
            "premium_warning": 17,
            "valuation_dispersion_warning": 18,
        }
        for key, row in tx_rows.items():
            items += _both("Transaction Analysis", row, inputs[key], source)
        for offset, value in enumerate(inputs["forecast_fcfs"], start=12):
            items += _both("Transaction Analysis", offset, value, source)
        acc_rows = {
            "buyer_earnings": 5,
            "buyer_shares": 6,
            "target_earnings": 7,
            "after_tax_synergies": 8,
            "incremental_financing_cost": 9,
            "shares_issued": 10,
            "minimum_accretion": 11,
        }
        for key, row in acc_rows.items():
            items += _both("Accretion Dilution", row, inputs[key], source)
    elif model_id == "02":
        rows = {
            "opening_cash": 5,
            "operating_cash_flow": 6,
            "capex": 7,
            "dividends": 8,
            "buybacks": 9,
            "debt_issuance": 10,
            "debt_repayment": 11,
            "opening_debt": 12,
            "ebitda": 13,
            "interest": 14,
            "minimum_cash": 15,
            "maximum_net_leverage": 16,
            "minimum_interest_coverage": 17,
        }
        for key, row in rows.items():
            items += _both("Treasury & Liquidity", row, inputs[key], source)
    elif model_id == "05":
        rows = {
            "opening_debt": 5,
            "mandatory_amortization": 6,
            "cash_sweep": 7,
            "pik_interest": 8,
            "cfads": 9,
            "cash_interest": 10,
            "ebitda": 11,
            "recovery_ev": 12,
            "senior_claims": 13,
            "lender_claim": 14,
            "minimum_dscr": 15,
            "maximum_leverage": 16,
            "minimum_recovery": 17,
        }
        for key, row in rows.items():
            items += _both("Amendment Economics", row, inputs[key], source)
        if case_type == "conventional":
            exposures = [35.0, 25.0, 20.0, 12.0, 8.0]
            leverages = [4.0, 4.5, 3.5, 3.0, 2.5]
        else:
            exposures = [45.0, 30.0, 15.0, 7.0, 3.0]
            leverages = [7.0, 6.5, 5.0, 4.0, 3.5]
        for row, (exposure, leverage) in enumerate(zip(exposures, leverages), start=5):
            for column in ("C", "D"):
                items.append({"sheet": "Portfolio & Concentration", "cell": f"{column}{row}", "value": exposure, "source": source})
            for column in ("E", "F"):
                items.append({"sheet": "Portfolio & Concentration", "cell": f"{column}{row}", "value": leverage, "source": source})
        items += _both("Portfolio & Concentration", 15, 0.40, source)
    elif model_id == "06":
        rows = {
            "opening_debt": 5,
            "issuance": 6,
            "repayments": 7,
            "liquidity": 13,
            "committed_lines": 14,
            "ebitda": 19,
            "maximum_maturity_concentration": 20,
            "minimum_interest_coverage": 21,
            "maximum_weighted_cost": 22,
        }
        for key, row in rows.items():
            items += _both("Refinancing & Rates", row, inputs[key], source)
        for row, value in enumerate(inputs["maturities"], start=8):
            items += _both("Refinancing & Rates", row, value, source)
        tranches = inputs["tranches"]
        items += _both("Refinancing & Rates", 15, tranches[0]["amount"], source)
        items += _both("Refinancing & Rates", 16, tranches[0]["rate"], source)
        items += _both("Refinancing & Rates", 17, tranches[1]["amount"], source)
        items += _both("Refinancing & Rates", 18, tranches[1]["rate"], source)
    elif model_id == "07":
        rows = {
            "opening_debt_ratio": 5,
            "nominal_interest_rate": 6,
            "nominal_growth_rate": 7,
            "primary_balance_ratio": 8,
            "pledged_revenue": 9,
            "debt_service": 10,
            "reserves": 11,
            "operating_expenditure": 12,
            "maximum_debt_ratio": 13,
            "minimum_dscr": 14,
            "minimum_reserve_coverage": 15,
        }
        for key, row in rows.items():
            items += _both("Revenue Stress", row, inputs[key], source)
    elif model_id == "13":
        ownership_rows = {
            "pre_money": 5,
            "investment": 6,
            "existing_shares": 7,
            "new_shares": 8,
            "pool_expansion": 9,
            "maximum_investor_ownership": 10,
            "maximum_pool_dilution": 11,
        }
        for key, row in ownership_rows.items():
            items += _both("Ownership & Dilution", row, inputs[key], source)
        reserve_rows = {"follow_on_required": 5, "reserves": 6}
        for key, row in reserve_rows.items():
            items += _both("Reserves & Follow-ons", row, inputs[key], source)
        items += _both("Exit Waterfall", 5, inputs["exit_value"], source)
        items += _both("Exit Waterfall", 6, inputs["investment"], source)
        items += _both("Exit Waterfall", 7, inputs["minimum_gross_moic"], source)
    else:
        raise KeyError(model_id)
    return items


def case_specs() -> list[dict[str, Any]]:
    registry = _load(REGISTRY_PATH)
    specs: list[dict[str, Any]] = []
    for model in registry["models"]:
        model_id = model["model_id"]
        folder = CANONICAL_PATHS[model_id].split("/", 1)[0]
        for case in model["cases"]:
            case_id, filename = CASE_NAMES[model_id][case["type"]]
            output = f"{folder}/instances/{filename}"
            specs.append(
                {
                    "id": case_id,
                    "model_id": model_id,
                    "domain": model["domain"],
                    "case_type": case["type"],
                    "template": CANONICAL_PATHS[model_id],
                    "output": output,
                    "inputs": _case_inputs(model_id, case["type"], case["inputs"], case_id),
                }
            )
    return specs


def _manifest(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.1",
        "id": spec["id"],
        "classification": "synthetic_engineering_benchmark",
        "counts_toward_M4": False,
        "domain": spec["domain"],
        "model_id": spec["model_id"],
        "case_type": spec["case_type"],
        "template": spec["template"],
        "output": spec["output"],
        "as_of": "2026-08-04",
        "scenario": "Base" if spec["case_type"] == "conventional" else "Adversarial",
        "cover": {},
        "inputs": spec["inputs"],
        "refresh": {
            "date": "2026-08-04",
            "trigger": "Six-engine frontier release",
            "source_snapshot": "repo://standards/frontier/legacy_engine_registry.json",
            "what_changed": f"Applied {spec['case_type']} fixture {spec['id']}",
            "reviewer_notes": "Synthetic engineering benchmark; not M4 evidence",
            "next_check": "On builder, source, contract, or threshold change",
        },
    }


def _update_inventory_and_registry() -> tuple[dict[str, Any], dict[str, Any]]:
    inventory = _load(INVENTORY_PATH)
    registry = _load(REGISTRY_PATH)
    model_by_id = {item["id"]: item for item in inventory["models"]}
    for candidate in registry["models"]:
        model_id = candidate["model_id"]
        model = model_by_id[model_id]
        model["builder"] = candidate["candidate_builder"]
        model["reference_checks"] = candidate["reference_checks"]
        model["declared_maturity"] = "M2"
    registry["status"] = "release_staged"
    _write(INVENTORY_PATH, inventory)
    _write(REGISTRY_PATH, registry)
    return inventory, registry


def prepare(report_path: Path) -> dict[str, Any]:
    inventory, registry = _update_inventory_and_registry()
    inventory_by_id = {item["id"]: item for item in inventory["models"]}
    profiles = profiles_by_id(ROOT)
    canonical_results = []
    errors: list[str] = []
    for model_id in sorted(EXPECTED_IDS):
        path = ROOT / CANONICAL_PATHS[model_id]
        build_workbook(model_id, path)
        apply_surface(path, inventory_by_id[model_id], profiles[model_id])
        surface_errors = validate_workbook_surface(path, inventory_by_id[model_id], profiles[model_id])
        result = validate_workbook(model_id, path)
        canonical_results.append(result)
        errors.extend(f"canonical {model_id}: {item}" for item in result["errors"])
        errors.extend(f"canonical {model_id}: surface {item}" for item in surface_errors)

    receipts = []
    for spec in case_specs():
        manifest_path = BENCHMARK_DIR / f"{spec['id']}.json"
        _write(manifest_path, _manifest(spec))
        receipt = apply_manifest(manifest_path, ROOT)
        path = ROOT / spec["output"]
        surface_errors = validate_workbook_surface(
            path, inventory_by_id[spec["model_id"]], profiles[spec["model_id"]]
        )
        result = validate_workbook(spec["model_id"], path)
        errors.extend(f"instance {spec['id']}: {item}" for item in result["errors"])
        errors.extend(f"instance {spec['id']}: surface {item}" for item in surface_errors)
        receipts.append(receipt)

    report = {
        "schema_version": "1.0",
        "phase": "prepare",
        "status": "PASS" if not errors else "FAIL",
        "canonical_models": len(canonical_results),
        "benchmark_instances": len(receipts),
        "canonical_results": canonical_results,
        "benchmark_outputs": [spec["output"] for spec in case_specs()],
        "inventory_staged_builders": sorted(EXPECTED_IDS),
        "errors": errors,
        "statement": (
            "Inventory and artifacts are staged in the workflow tree only. No release is "
            "committed before recalculation, post-contracts, parity, and finalization."
        ),
    }
    _write(report_path, report)
    if errors:
        raise ValueError(errors)
    return report


def finalize(report_path: Path) -> dict[str, Any]:
    inventory = _load(INVENTORY_PATH)
    inventory_by_id = {item["id"]: item for item in inventory["models"]}
    registry = _load(REGISTRY_PATH)
    index = _load(BENCHMARK_INDEX_PATH)
    retained = [
        item
        for item in index.get("instances", [])
        if item.get("instance_id") not in {spec["id"] for spec in case_specs()}
    ]
    new_receipts = []
    for spec in case_specs():
        output = ROOT / spec["output"]
        receipt_path = output.with_suffix(".receipt.json")
        receipt = _load(receipt_path)
        receipt["workbook_sha256"] = _sha256(output)
        receipt["recalculated_on"] = date.today().isoformat()
        receipt["recalculation_engine"] = "LibreOffice Calc"
        receipt["model_id"] = spec["model_id"]
        receipt["domain"] = spec["domain"]
        receipt["case_type"] = spec["case_type"]
        receipt["classification"] = "synthetic_engineering_benchmark"
        receipt["counts_toward_M4"] = False
        _write(receipt_path, receipt)
        new_receipts.append(receipt)
    instances = sorted(
        [*retained, *new_receipts],
        key=lambda item: (item.get("model_id", ""), item.get("instance_id", "")),
    )
    index.update(
        {
            "schema_version": "1.3",
            "as_of": date.today().isoformat(),
            "classification": "synthetic_engineering_benchmarks",
            "counts_toward_M4": False,
            "instance_count": len(instances),
            "instances": instances,
        }
    )
    _write(BENCHMARK_INDEX_PATH, index)
    registry["status"] = RELEASE_STATUS
    registry["released_on"] = date.today().isoformat()
    _write(REGISTRY_PATH, registry)

    errors: list[str] = []
    for model_id in EXPECTED_IDS:
        model = inventory_by_id[model_id]
        candidate = next(item for item in registry["models"] if item["model_id"] == model_id)
        if model["builder"] != candidate["candidate_builder"]:
            errors.append(f"{model_id}: inventory builder mismatch")
        if model.get("reference_checks") != candidate["reference_checks"]:
            errors.append(f"{model_id}: inventory reference-check mismatch")
        if model.get("declared_maturity") != "M2":
            errors.append(f"{model_id}: release may not change conservative M2 maturity")
    counts = {model_id: 0 for model_id in EXPECTED_IDS}
    for item in instances:
        model_id = item.get("model_id")
        if model_id in counts:
            counts[model_id] += 1
    for model_id, count in counts.items():
        if count != 2:
            errors.append(f"{model_id}: expected two benchmark instances, found {count}")
    report = {
        "schema_version": "1.0",
        "phase": "finalize",
        "status": "PASS" if not errors else "FAIL",
        "canonical_models": len(EXPECTED_IDS),
        "benchmark_instances_added": len(new_receipts),
        "benchmark_instances_total": len(instances),
        "released_models": sorted(EXPECTED_IDS),
        "benchmark_counts": counts,
        "m3_promoted": 0,
        "m4_promoted": 0,
        "errors": errors,
        "statement": (
            "The six legacy engines have release builders, independent oracle checks, and "
            "synthetic benchmark pairs. They remain M2; synthetic cases do not count toward M4."
        ),
    }
    _write(report_path, report)
    if errors:
        raise ValueError(errors)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "finalize"))
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report_path = args.report or ROOT / f"legacy-engine-release-{args.phase}-report.json"
    report = prepare(report_path) if args.phase == "prepare" else finalize(report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
