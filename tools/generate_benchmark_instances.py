"""Generate deterministic reference and adversarial benchmark instances.

These are synthetic engineering fixtures, not public-company underwriting and
not M4 evidence. They exercise scenario selection, source/refresh plumbing,
recalculation, and receipt generation across the engineered flagship models.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from model_instances import apply_manifest

AS_OF = "2026-08-03"


def source(case_id: str) -> dict[str, str]:
    return {
        "name": f"Finance-Segway benchmark fixture {case_id}",
        "url": f"repo://standards/benchmark_cases/{case_id}.json",
        "as_of": AS_OF,
        "notes": "Synthetic engineering fixture; not investment evidence",
    }


def item(sheet: str, cell: str, value: Any, case_id: str) -> dict[str, Any]:
    return {"sheet": sheet, "cell": cell, "value": value, "source": source(case_id)}


def cases() -> list[dict[str, Any]]:
    return [
        {
            "id": "pe-reference-buyout", "domain": "03_Private_Equity",
            "template": "03_Private_Equity/_template_LBO.xlsx",
            "output": "03_Private_Equity/instances/benchmark_reference_buyout.xlsx",
            "scenario": "Base",
            "cover": {"Target / transaction:": "Reference Middle-Market Buyout", "Sponsor / principal:": "Benchmark Sponsor"},
            "inputs": [
                item("Assumptions", "C5", 650.0, "pe-reference-buyout"),
                item("Assumptions", "C6", 0.22, "pe-reference-buyout"),
                item("Assumptions", "C7", 0.055, "pe-reference-buyout"),
                item("Assumptions", "C13", 10.5, "pe-reference-buyout"),
                item("Assumptions", "C19", 4.25, "pe-reference-buyout"),
                item("Assumptions", "C22", 1.25, "pe-reference-buyout"),
                item("Assumptions", "C28", 10.0, "pe-reference-buyout"),
            ],
        },
        {
            "id": "pe-adversarial-contraction", "domain": "03_Private_Equity",
            "template": "03_Private_Equity/_template_LBO.xlsx",
            "output": "03_Private_Equity/instances/benchmark_adversarial_contraction.xlsx",
            "scenario": "Downside",
            "cover": {"Target / transaction:": "Adversarial Cyclical Contraction", "Sponsor / principal:": "Benchmark Sponsor"},
            "inputs": [
                item("Assumptions", "D6", 0.145, "pe-adversarial-contraction"),
                item("Assumptions", "D7", -0.060, "pe-adversarial-contraction"),
                item("Assumptions", "D8", -0.008, "pe-adversarial-contraction"),
                item("Assumptions", "D24", 0.070, "pe-adversarial-contraction"),
                item("Assumptions", "D28", 7.0, "pe-adversarial-contraction"),
            ],
        },
        {
            "id": "merchant-reference-principal", "domain": "04_Merchant_Banking",
            "template": "04_Merchant_Banking/_template_LBO.xlsx",
            "output": "04_Merchant_Banking/instances/benchmark_reference_principal.xlsx",
            "scenario": "Base",
            "cover": {"Target / transaction:": "Reference Principal Investment", "Sponsor / principal:": "Benchmark Merchant Bank"},
            "inputs": [
                item("Assumptions", "C5", 900.0, "merchant-reference-principal"),
                item("Assumptions", "C6", 0.18, "merchant-reference-principal"),
                item("Assumptions", "C7", 0.045, "merchant-reference-principal"),
                item("Assumptions", "C19", 3.50, "merchant-reference-principal"),
                item("Assumptions", "C22", 0.75, "merchant-reference-principal"),
                item("Assumptions", "C29", 7, "merchant-reference-principal"),
            ],
        },
        {
            "id": "merchant-adversarial-holdco", "domain": "04_Merchant_Banking",
            "template": "04_Merchant_Banking/_template_LBO.xlsx",
            "output": "04_Merchant_Banking/instances/benchmark_adversarial_holdco.xlsx",
            "scenario": "Downside",
            "cover": {"Target / transaction:": "Adversarial Holdco Leverage", "Sponsor / principal:": "Benchmark Merchant Bank"},
            "inputs": [
                item("Assumptions", "D7", -0.030, "merchant-adversarial-holdco"),
                item("Assumptions", "D20", 0.145, "merchant-adversarial-holdco"),
                item("Assumptions", "D24", 0.080, "merchant-adversarial-holdco"),
                item("Assumptions", "D28", 6.5, "merchant-adversarial-holdco"),
            ],
        },
        {
            "id": "risk-reference-balanced", "domain": "09_Risk_Management",
            "template": "09_Risk_Management/_template_RISK.xlsx",
            "output": "09_Risk_Management/instances/benchmark_reference_balanced.xlsx",
            "scenario": "Base",
            "cover": {"Portfolio / desk:": "Reference Multi-Asset Book"},
            "inputs": [
                item("Assumptions", "C5", 0.99, "risk-reference-balanced"),
                item("Assumptions", "C12", 12.0, "risk-reference-balanced"),
                item("Assumptions", "C18", 300.0, "risk-reference-balanced"),
                item("Positions", "D5", 50.0, "risk-reference-balanced"),
                item("Positions", "E5", 140.0, "risk-reference-balanced"),
            ],
        },
        {
            "id": "risk-adversarial-crowding", "domain": "09_Risk_Management",
            "template": "09_Risk_Management/_template_RISK.xlsx",
            "output": "09_Risk_Management/instances/benchmark_adversarial_crowding.xlsx",
            "scenario": "Downside",
            "cover": {"Portfolio / desk:": "Adversarial Crowded Levered Book"},
            "inputs": [
                item("Assumptions", "D7", 0.45, "risk-adversarial-crowding"),
                item("Assumptions", "D12", 8.0, "risk-adversarial-crowding"),
                item("Assumptions", "D13", 22.0, "risk-adversarial-crowding"),
                item("Positions", "E6", 90.0, "risk-adversarial-crowding"),
                item("Positions", "M14", 35.0, "risk-adversarial-crowding"),
            ],
        },
        {
            "id": "options-reference-atm", "domain": "14_Options_Derivatives",
            "template": "14_Options_Derivatives/_template_OPTIONS.xlsx",
            "output": "14_Options_Derivatives/instances/benchmark_reference_atm.xlsx",
            "scenario": "Base",
            "cover": {"Underlying:": "Reference ATM Equity Option"},
            "inputs": [
                item("Assumptions", "C5", 100.0, "options-reference-atm"),
                item("Assumptions", "C6", 100.0, "options-reference-atm"),
                item("Assumptions", "C7", 0.50, "options-reference-atm"),
                item("Assumptions", "C10", 0.25, "options-reference-atm"),
                item("Assumptions", "C11", 8.25, "options-reference-atm"),
            ],
        },
        {
            "id": "options-adversarial-skew", "domain": "14_Options_Derivatives",
            "template": "14_Options_Derivatives/_template_OPTIONS.xlsx",
            "output": "14_Options_Derivatives/instances/benchmark_adversarial_skew.xlsx",
            "scenario": "Downside",
            "cover": {"Underlying:": "Adversarial Gap-and-Skew Option Book"},
            "inputs": [
                item("Assumptions", "D5", 72.0, "options-adversarial-skew"),
                item("Assumptions", "D10", 0.60, "options-adversarial-skew"),
                item("Assumptions", "D11", 30.0, "options-adversarial-skew"),
                item("Assumptions", "D14", -0.50, "options-adversarial-skew"),
            ],
        },
        {
            "id": "insurance-reference-book", "domain": "18_Insurance_Actuarial",
            "template": "18_Insurance_Actuarial/_template_INSURANCE.xlsx",
            "output": "18_Insurance_Actuarial/instances/benchmark_reference_book.xlsx",
            "scenario": "Base",
            "cover": {"Entity / line of business:": "Reference Commercial Lines Book"},
            "inputs": [
                item("Assumptions", "C5", 0.60, "insurance-reference-book"),
                item("Assumptions", "C6", 0.27, "insurance-reference-book"),
                item("Assumptions", "C11", 550.0, "insurance-reference-book"),
                item("Assumptions", "C14", 375.0, "insurance-reference-book"),
            ],
        },
        {
            "id": "insurance-adversarial-social-inflation", "domain": "18_Insurance_Actuarial",
            "template": "18_Insurance_Actuarial/_template_INSURANCE.xlsx",
            "output": "18_Insurance_Actuarial/instances/benchmark_adversarial_social_inflation.xlsx",
            "scenario": "Downside",
            "cover": {"Entity / line of business:": "Adversarial Social-Inflation Book"},
            "inputs": [
                item("Assumptions", "D5", 0.88, "insurance-adversarial-social-inflation"),
                item("Assumptions", "D8", 0.12, "insurance-adversarial-social-inflation"),
                item("Assumptions", "D10", 0.22, "insurance-adversarial-social-inflation"),
                item("Assumptions", "D17", 0.20, "insurance-adversarial-social-inflation"),
            ],
        },
        {
            "id": "securitization-reference-pool", "domain": "19_Structured_Finance_Securitization",
            "template": "19_Structured_Finance_Securitization/_template_SECURITIZATION.xlsx",
            "output": "19_Structured_Finance_Securitization/instances/benchmark_reference_pool.xlsx",
            "scenario": "Base",
            "cover": {"Transaction / collateral:": "Reference Amortizing Consumer Pool"},
            "inputs": [
                item("Assumptions", "C5", 1200.0, "securitization-reference-pool"),
                item("Assumptions", "C7", 0.14, "securitization-reference-pool"),
                item("Assumptions", "C8", 0.025, "securitization-reference-pool"),
                item("Assumptions", "C9", 0.50, "securitization-reference-pool"),
            ],
        },
        {
            "id": "securitization-adversarial-default", "domain": "19_Structured_Finance_Securitization",
            "template": "19_Structured_Finance_Securitization/_template_SECURITIZATION.xlsx",
            "output": "19_Structured_Finance_Securitization/instances/benchmark_adversarial_default.xlsx",
            "scenario": "Downside",
            "cover": {"Transaction / collateral:": "Adversarial High-Default Slow-Recovery Pool"},
            "inputs": [
                item("Assumptions", "D7", 0.03, "securitization-adversarial-default"),
                item("Assumptions", "D8", 0.15, "securitization-adversarial-default"),
                item("Assumptions", "D9", 0.15, "securitization-adversarial-default"),
                item("Assumptions", "D10", 9, "securitization-adversarial-default"),
            ],
        },
        {
            "id": "project-reference-contracted", "domain": "20_Project_Finance",
            "template": "20_Project_Finance/_template_PROJECT_FINANCE.xlsx",
            "output": "20_Project_Finance/instances/benchmark_reference_contracted.xlsx",
            "scenario": "Base",
            "cover": {"Project / concession:": "Reference Contracted Infrastructure Project"},
            "inputs": [
                item("Assumptions", "C5", 900.0, "project-reference-contracted"),
                item("Assumptions", "C11", 205.0, "project-reference-contracted"),
                item("Assumptions", "C16", 1.40, "project-reference-contracted"),
                item("Assumptions", "C23", 0.98, "project-reference-contracted"),
            ],
        },
        {
            "id": "project-adversarial-delay", "domain": "20_Project_Finance",
            "template": "20_Project_Finance/_template_PROJECT_FINANCE.xlsx",
            "output": "20_Project_Finance/instances/benchmark_adversarial_delay.xlsx",
            "scenario": "Downside",
            "cover": {"Project / concession:": "Adversarial Delay and Availability Case"},
            "inputs": [
                item("Assumptions", "D5", 1100.0, "project-adversarial-delay"),
                item("Assumptions", "D9", 10, "project-adversarial-delay"),
                item("Assumptions", "D11", 135.0, "project-adversarial-delay"),
                item("Assumptions", "D23", 0.72, "project-adversarial-delay"),
            ],
        },
        {
            "id": "rates-reference-curve", "domain": "21_Fixed_Income_Rates",
            "template": "21_Fixed_Income_Rates/_template_FIXED_INCOME.xlsx",
            "output": "21_Fixed_Income_Rates/instances/benchmark_reference_curve.xlsx",
            "scenario": "Base",
            "cover": {"Portfolio / security:": "Reference Rates and Credit Portfolio"},
            "inputs": [
                item("Assumptions", "C6", 0.050, "rates-reference-curve"),
                item("Assumptions", "C7", 0.055, "rates-reference-curve"),
                item("Assumptions", "C8", 10.0, "rates-reference-curve"),
                item("Assumptions", "C14", 75.0, "rates-reference-curve"),
            ],
        },
        {
            "id": "rates-adversarial-bear-steepener", "domain": "21_Fixed_Income_Rates",
            "template": "21_Fixed_Income_Rates/_template_FIXED_INCOME.xlsx",
            "output": "21_Fixed_Income_Rates/instances/benchmark_adversarial_bear_steepener.xlsx",
            "scenario": "Downside",
            "cover": {"Portfolio / security:": "Adversarial Bear-Steepener Portfolio"},
            "inputs": [
                item("Assumptions", "D7", 0.085, "rates-adversarial-bear-steepener"),
                item("Assumptions", "D10", 0.025, "rates-adversarial-bear-steepener"),
                item("Zero Curve", "D10", 0.080, "rates-adversarial-bear-steepener"),
                item("Zero Curve", "D14", 0.090, "rates-adversarial-bear-steepener"),
            ],
        },
        {
            "id": "quant-reference-costed", "domain": "22_Quantitative_Systematic",
            "template": "22_Quantitative_Systematic/_template_QUANT.xlsx",
            "output": "22_Quantitative_Systematic/instances/benchmark_reference_costed.xlsx",
            "scenario": "Base",
            "cover": {"Strategy / universe:": "Reference Costed Systematic Strategy"},
            "inputs": [
                item("Assumptions", "C7", 10.0, "quant-reference-costed"),
                item("Assumptions", "C8", 0.003, "quant-reference-costed"),
                item("Assumptions", "C9", 60.0, "quant-reference-costed"),
                item("Assumptions", "C18", 1, "quant-reference-costed"),
                item("Assumptions", "C19", 1, "quant-reference-costed"),
            ],
        },
        {
            "id": "quant-adversarial-capacity", "domain": "22_Quantitative_Systematic",
            "template": "22_Quantitative_Systematic/_template_QUANT.xlsx",
            "output": "22_Quantitative_Systematic/instances/benchmark_adversarial_capacity.xlsx",
            "scenario": "Downside",
            "cover": {"Strategy / universe:": "Adversarial Capacity and Cost Shock"},
            "inputs": [
                item("Assumptions", "D7", 25.0, "quant-adversarial-capacity"),
                item("Assumptions", "D8", 0.015, "quant-adversarial-capacity"),
                item("Assumptions", "D9", 300.0, "quant-adversarial-capacity"),
                item("Assumptions", "D10", 100.0, "quant-adversarial-capacity"),
            ],
        },
    ]


def generate(root: Path) -> dict[str, Any]:
    manifest_root = root / "standards" / "benchmark_cases"
    manifest_root.mkdir(parents=True, exist_ok=True)
    receipts = []
    for case in cases():
        manifest = {
            "schema_version": "1.0",
            "id": case["id"],
            "template": case["template"],
            "output": case["output"],
            "as_of": AS_OF,
            "scenario": case["scenario"],
            "cover": case.get("cover", {}),
            "inputs": case["inputs"],
            "sources": [source(case["id"])],
            "refresh": {
                "date": AS_OF,
                "trigger": "Synthetic benchmark generation",
                "what_changed": f"Generated {case['id']} from canonical template",
                "reviewer_notes": "Engineering fixture only; not M4/public-instance evidence",
                "next_check": "On builder or contract change",
            },
        }
        manifest_path = manifest_root / f"{case['id']}.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        receipts.append(apply_manifest(manifest_path, root))
    index = {
        "schema_version": "1.0",
        "as_of": AS_OF,
        "classification": "synthetic_engineering_benchmarks",
        "counts_toward_M4": False,
        "instances": receipts,
    }
    index_path = manifest_root / "index.json"
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    return index


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    index = generate(args.root.resolve())
    print(json.dumps({"instances": len(index["instances"]), "counts_toward_M4": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
