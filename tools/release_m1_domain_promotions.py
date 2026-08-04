"""Prepare and finalize the atomic promotion of the nine hardened M1 domains.

The prepare phase builds canonical templates, validates their workbook contracts,
creates one conventional and one adversarial source-addressed benchmark manifest
per domain, generates the 18 workbook instances, and stages conservative M2
inventory declarations. The finalize phase is run only after LibreOffice and
engineering audits pass; it refreshes workbook hashes, rebuilds the benchmark
index, and marks the candidate transaction validated.

No artifact produced here counts toward M4. The cases are synthetic engineering
fixtures derived from the domain-hardening registry, not live underwriting.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import subprocess
from datetime import date
from pathlib import Path
from typing import Any

try:
    from tools.model_instance_release import apply_manifest
    from tools.validate_hardened_workbooks import validate_workbook
except ModuleNotFoundError:
    from model_instance_release import apply_manifest
    from validate_hardened_workbooks import validate_workbook

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "standards" / "model_inventory.json"
REGISTRY_PATH = ROOT / "standards" / "domain_hardening" / "m1_registry.json"
CANDIDATE_PATH = (
    ROOT / "standards" / "domain_hardening" / "m2_promotion_candidates.json"
)
BENCHMARK_DIR = ROOT / "standards" / "benchmark_cases"
BENCHMARK_INDEX_PATH = BENCHMARK_DIR / "index.json"
REPORT_PATH = ROOT / "m1-domain-promotion-report.json"
AS_OF = "2026-08-04"
EXPECTED_IDS = {"08", "10", "11", "12", "15", "16", "17", "23", "24"}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def source(case_id: str) -> dict[str, str]:
    return {
        "name": f"Finance-Segway domain-hardening fixture {case_id}",
        "url": "repo://standards/domain_hardening/m1_registry.json",
        "as_of": AS_OF,
        "notes": (
            "Synthetic engineering fixture derived from the authoritative-reference "
            "and adversarial-case registry; not investment evidence and not M4 evidence"
        ),
    }


def item(sheet: str, cell: str, value: Any, case_id: str) -> dict[str, Any]:
    return {
        "sheet": sheet,
        "cell": cell,
        "value": value,
        "source": source(case_id),
    }


def many(
    case_id: str,
    sheet: str,
    values: dict[str, Any],
) -> list[dict[str, Any]]:
    return [item(sheet, cell, value, case_id) for cell, value in values.items()]


def case_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []

    def add(
        model_id: str,
        domain: str,
        folder: str,
        template: str,
        case_id: str,
        case_type: str,
        output_name: str,
        inputs: list[dict[str, Any]],
        scenario: str = "Base",
        cover: dict[str, Any] | None = None,
    ) -> None:
        specs.append(
            {
                "model_id": model_id,
                "domain": domain,
                "folder": folder,
                "template": template,
                "id": case_id,
                "case_type": case_type,
                "output": f"{folder}/instances/{output_name}",
                "scenario": scenario,
                "cover": cover or {},
                "inputs": inputs,
            }
        )

    case_id = "am-reference-fund"
    inputs = []
    inputs += many(
        case_id,
        "Fund NAV",
        {
            "C5": 100.0,
            "C6": 20.0,
            "C7": 15.0,
            "C8": 2.0,
            "C9": 5.0,
            "D6": 10.0,
            "D7": 7.0,
            "D8": 2.0,
            "D9": 4.0,
            "E6": 5.0,
            "E7": 5.0,
            "E8": 2.0,
            "E9": 4.0,
            "F6": 0.0,
            "F7": 4.0,
            "F8": 2.0,
            "F9": 6.0,
        },
    )
    inputs += many(
        case_id,
        "Fee Waterfall",
        {
            "C5": 100.0,
            "C6": 80.0,
            "C7": 0.08,
            "C8": 0.20,
            "C9": 1.0,
            "C10": 100.0,
        },
    )
    inputs += many(case_id, "Return Measurement", {"C14": 0.08})
    inputs += many(
        case_id,
        "Exposure & Liquidity",
        {
            "C5": 150.0,
            "C6": 60.0,
            "C8": 35.0,
            "C9": 15.0,
            "C10": 12.0,
            "C11": 8.0,
            "C12": 30.0,
            "C13": 0.40,
            "C14": 0.25,
            "C15": 1.20,
        },
    )
    add(
        "08",
        "Asset Management",
        "08_Asset_Management",
        "08_Asset_Management/_template_AM.xlsx",
        case_id,
        "conventional",
        "benchmark_reference_fund.xlsx",
        inputs,
    )

    case_id = "am-adversarial-liquidity"
    inputs = []
    inputs += many(
        case_id,
        "Fund NAV",
        {
            "C5": 100.0,
            "C6": 0.0,
            "C7": -20.0,
            "C8": 3.0,
            "C9": 35.0,
            "D6": 0.0,
            "D7": -10.0,
            "D8": 3.0,
            "D9": 20.0,
            "E6": 0.0,
            "E7": -5.0,
            "E8": 2.0,
            "E9": 10.0,
            "F6": 0.0,
            "F7": 0.0,
            "F8": 2.0,
            "F9": 5.0,
        },
    )
    inputs += many(
        case_id,
        "Fee Waterfall",
        {
            "C5": 100.0,
            "C6": 80.0,
            "C7": 0.08,
            "C8": 0.20,
            "C9": 1.0,
            "C10": 5.0,
        },
    )
    inputs += many(case_id, "Return Measurement", {"C14": -0.05})
    inputs += many(
        case_id,
        "Exposure & Liquidity",
        {
            "D5": 180.0,
            "D6": 100.0,
            "D8": 55.0,
            "D9": 35.0,
            "D10": 40.0,
            "D11": 20.0,
            "D12": 15.0,
            "D13": 0.40,
            "D14": 0.25,
            "D15": 1.20,
        },
    )
    add(
        "08",
        "Asset Management",
        "08_Asset_Management",
        "08_Asset_Management/_template_AM.xlsx",
        case_id,
        "adversarial",
        "benchmark_adversarial_liquidity.xlsx",
        inputs,
        scenario="Downside",
    )

    case_id = "trade-reference-exporter"
    inputs = []
    inputs += many(
        case_id,
        "Working Capital Cycle",
        {"C5": 500.0, "C6": 350.0, "C7": 60.0, "C8": 50.0, "C9": 40.0},
    )
    inputs += many(
        case_id,
        "LC & Factoring Cost",
        {
            "C5": 100.0,
            "C6": 0.015,
            "C7": 0.010,
            "C8": 180.0,
            "C14": 100.0,
            "C15": 0.85,
            "C16": 0.020,
            "C17": 60.0,
        },
    )
    inputs += many(case_id, "Credit & Facility", {"C3": "Base"})
    inputs += many(
        case_id,
        "Documentary Controls",
        {"C5": 10.0, "C6": 0.0, "C7": 1.0, "C8": 1.0, "C9": 1.0, "C10": 1.0, "C11": 1.0, "C12": 1.0},
    )
    add(
        "10",
        "Trade Finance",
        "10_Trade_Finance",
        "10_Trade_Finance/_template_TRADE_FINANCE.xlsx",
        case_id,
        "conventional",
        "benchmark_reference_exporter.xlsx",
        inputs,
    )

    case_id = "trade-adversarial-country-shock"
    inputs = []
    inputs += many(
        case_id,
        "Working Capital Cycle",
        {"C5": 400.0, "C6": 320.0, "C7": 160.0, "C8": 120.0, "C9": 20.0},
    )
    inputs += many(
        case_id,
        "LC & Factoring Cost",
        {
            "C5": 100.0,
            "C6": 0.040,
            "C7": 0.030,
            "C8": 90.0,
            "C14": 100.0,
            "C15": 0.70,
            "C16": 0.180,
            "C17": 45.0,
        },
    )
    inputs += many(case_id, "Credit & Facility", {"C3": "Downside"})
    inputs += many(
        case_id,
        "Documentary Controls",
        {"C5": 30.0, "C6": 4.0, "C7": 0.0, "C8": 0.0, "C9": 0.0, "C10": 0.0, "C11": 0.0, "C12": 0.0},
    )
    add(
        "10",
        "Trade Finance",
        "10_Trade_Finance",
        "10_Trade_Finance/_template_TRADE_FINANCE.xlsx",
        case_id,
        "adversarial",
        "benchmark_adversarial_country_shock.xlsx",
        inputs,
        scenario="Downside",
    )

    case_id = "microfinance-reference-book"
    inputs = []
    inputs += many(
        case_id,
        "Loan Portfolio",
        {"C5": 103.0, "C6": 5000.0, "C7": 5.0, "C8": 2.0, "C9": 2.0, "C10": 0.0206},
    )
    inputs += many(
        case_id,
        "Sustainability",
        {"C5": 20.0, "C6": 4.0, "C7": 2.0, "C8": 10.0, "C9": 1.0},
    )
    inputs += many(
        case_id,
        "Provisioning",
        {"C5": 95.0, "C6": 5.0, "C7": 2.0, "C8": 1.0, "C12": 6.0},
    )
    inputs += many(case_id, "Portfolio Rollforward", {"C3": "Base"})
    add(
        "11",
        "Microfinance",
        "11_Microfinance",
        "11_Microfinance/_template_MICROFINANCE.xlsx",
        case_id,
        "conventional",
        "benchmark_reference_book.xlsx",
        inputs,
    )

    case_id = "microfinance-adversarial-moratorium"
    inputs = []
    inputs += many(
        case_id,
        "Loan Portfolio",
        {"C5": 82.0, "C6": 4200.0, "C7": 35.0, "C8": 20.0, "C9": 8.0, "C10": 0.0195},
    )
    inputs += many(
        case_id,
        "Sustainability",
        {"C5": 8.0, "C6": 5.0, "C7": 8.0, "C8": 10.0, "C9": 2.0},
    )
    inputs += many(
        case_id,
        "Provisioning",
        {"C5": 40.0, "C6": 20.0, "C7": 15.0, "C8": 7.0, "C12": 10.0},
    )
    inputs += many(case_id, "Portfolio Rollforward", {"C3": "Downside"})
    add(
        "11",
        "Microfinance",
        "11_Microfinance",
        "11_Microfinance/_template_MICROFINANCE.xlsx",
        case_id,
        "adversarial",
        "benchmark_adversarial_moratorium.xlsx",
        inputs,
        scenario="Downside",
    )

    case_id = "equity-reference-rights"
    inputs = many(case_id, "Cap Table & Dilution", {"C3": "Base"})
    inputs += many(
        case_id,
        "Rights Offering",
        {"C7": 12.0, "C8": 9.0, "C9": 0.90, "C10": 0.02},
    )
    inputs += many(
        case_id,
        "Convertible Securities",
        {"C7": 12.0, "C8": 0.04, "C9": 3.0, "C10": 0.05, "C11": 9.5},
    )
    add(
        "12",
        "Equity Finance",
        "12_Equity_Finance",
        "12_Equity_Finance/_template_BASE.xlsx",
        case_id,
        "conventional",
        "benchmark_reference_rights.xlsx",
        inputs,
    )

    case_id = "equity-adversarial-dilution"
    inputs = many(case_id, "Cap Table & Dilution", {"C3": "Adversarial"})
    inputs += many(
        case_id,
        "Rights Offering",
        {"D7": 10.0, "D8": 3.0, "D9": 0.45, "D10": 0.08},
    )
    inputs += many(
        case_id,
        "Convertible Securities",
        {"D7": 4.0, "D8": 0.08, "D9": 1.0, "D10": 0.15, "D11": 3.5},
    )
    add(
        "12",
        "Equity Finance",
        "12_Equity_Finance",
        "12_Equity_Finance/_template_BASE.xlsx",
        case_id,
        "adversarial",
        "benchmark_adversarial_dilution.xlsx",
        inputs,
        scenario="Adversarial",
    )

    case_id = "commodities-reference-hedge"
    inputs = []
    inputs += many(
        case_id,
        "Hedging",
        {"C5": 1000.0, "C6": 100.0, "C7": 80.0, "C8": 82.0, "C9": 0.0, "C10": 1.0},
    )
    inputs += many(
        case_id,
        "Physical Balance & Carry",
        {
            "C7": 0.04,
            "C8": 0.02,
            "C9": 0.03,
            "C10": 0.50,
            "C11": 100.0,
            "C12": 50.0,
            "C13": 20.0,
            "C14": 80.0,
            "C15": 30.0,
            "C16": 60.0,
            "C17": 10.0,
            "C18": 1.25,
        },
    )
    add(
        "15",
        "Commodities",
        "15_Commodities",
        "15_Commodities/_template_COMMODITIES.xlsx",
        case_id,
        "conventional",
        "benchmark_reference_hedge.xlsx",
        inputs,
    )

    case_id = "commodities-adversarial-storage-squeeze"
    inputs = []
    inputs += many(
        case_id,
        "Hedging",
        {"C5": 500.0, "C6": 100.0, "C7": 20.0, "C8": 40.0, "C9": 0.0, "C10": 2.0},
    )
    inputs += many(
        case_id,
        "Physical Balance & Carry",
        {
            "D7": 0.02,
            "D8": 0.30,
            "D9": 0.00,
            "D10": 0.25,
            "D11": 20.0,
            "D12": 0.0,
            "D13": 10.0,
            "D14": 25.0,
            "D15": 5.0,
            "D16": 0.0,
            "D17": 5.0,
            "D18": 1.10,
        },
    )
    add(
        "15",
        "Commodities",
        "15_Commodities",
        "15_Commodities/_template_COMMODITIES.xlsx",
        case_id,
        "adversarial",
        "benchmark_adversarial_storage_squeeze.xlsx",
        inputs,
        scenario="Downside",
    )

    case_id = "crypto-reference-network"
    inputs = []
    inputs += many(
        case_id,
        "Tokenomics",
        {"C5": 300.0, "C6": 200.0, "C7": 150.0, "C8": 150.0, "C9": 200.0, "C12": 700.0},
    )
    inputs += many(
        case_id,
        "Valuation",
        {"C5": 2.5, "C6": 800.0, "C7": 100.0, "C8": 25.0},
    )
    inputs += many(
        case_id,
        "Staking Yield",
        {"C5": 0.60, "C6": 20.0, "C7": 30.0, "C8": 2.5},
    )
    inputs += many(case_id, "Supply Rollforward & Unlocks", {"C3": "Base"})
    add(
        "16",
        "Crypto & Digital Assets",
        "16_Crypto_Digital_Assets",
        "16_Crypto_Digital_Assets/_template_CRYPTO.xlsx",
        case_id,
        "conventional",
        "benchmark_reference_network.xlsx",
        inputs,
    )

    case_id = "crypto-adversarial-unlock-run"
    inputs = []
    inputs += many(
        case_id,
        "Tokenomics",
        {"C5": 250.0, "C6": 250.0, "C7": 250.0, "C8": 100.0, "C9": 150.0, "C12": 350.0},
    )
    inputs += many(
        case_id,
        "Valuation",
        {"C5": 0.8, "C6": 150.0, "C7": 10.0, "C8": 2.0},
    )
    inputs += many(
        case_id,
        "Staking Yield",
        {"C5": 0.35, "C6": 50.0, "C7": 2.0, "C8": 0.8},
    )
    inputs += many(case_id, "Supply Rollforward & Unlocks", {"C3": "Downside"})
    add(
        "16",
        "Crypto & Digital Assets",
        "16_Crypto_Digital_Assets",
        "16_Crypto_Digital_Assets/_template_CRYPTO.xlsx",
        case_id,
        "adversarial",
        "benchmark_adversarial_unlock_run.xlsx",
        inputs,
        scenario="Downside",
    )

    case_id = "real-estate-reference-property"
    inputs = []
    inputs += many(
        case_id,
        "Property Pro Forma",
        {"C5": 20.0, "C6": 1.0, "C8": 1.0, "C10": 7.0, "C12": 1.0},
    )
    inputs += many(
        case_id,
        "Cap Rate & Valuation",
        {"C5": 0.06, "C8": 200.0, "C10": 120.0},
    )
    inputs += many(
        case_id,
        "REIT FFO-AFFO",
        {"C4": 6.0, "C5": 5.0, "C6": 0.0, "C9": 1.0, "C10": 0.5, "C13": 10.0},
    )
    inputs += many(case_id, "Debt Schedule", {"C3": 0.06, "C4": 25.0, "C5": 1.25})
    inputs += many(case_id, "5-Year Hold & IRR", {"C5": 0.02, "C6": 0.065, "C7": 0.02})
    add(
        "17",
        "Real Estate & REIT",
        "17_Real_Estate_REIT",
        "17_Real_Estate_REIT/_template_REAL_ESTATE.xlsx",
        case_id,
        "conventional",
        "benchmark_reference_property.xlsx",
        inputs,
    )

    case_id = "real-estate-adversarial-refinancing"
    inputs = []
    inputs += many(
        case_id,
        "Property Pro Forma",
        {"C5": 20.0, "C6": 6.0, "C8": 0.5, "C10": 9.0, "C12": 4.0},
    )
    inputs += many(
        case_id,
        "Cap Rate & Valuation",
        {"C5": 0.09, "C8": 100.0, "C10": 85.0},
    )
    inputs += many(
        case_id,
        "REIT FFO-AFFO",
        {"C4": -3.0, "C5": 2.0, "C6": 0.0, "C9": 4.0, "C10": 1.0, "C13": 10.0},
    )
    inputs += many(case_id, "Debt Schedule", {"C3": 0.10, "C4": 15.0, "C5": 1.25})
    inputs += many(case_id, "5-Year Hold & IRR", {"C5": -0.03, "C6": 0.10, "C7": 0.04})
    add(
        "17",
        "Real Estate & REIT",
        "17_Real_Estate_REIT",
        "17_Real_Estate_REIT/_template_REAL_ESTATE.xlsx",
        case_id,
        "adversarial",
        "benchmark_adversarial_refinancing.xlsx",
        inputs,
        scenario="Downside",
    )

    case_id = "fintech-reference-payments"
    inputs = []
    inputs += many(
        case_id,
        "Unit Economics",
        {"C5": 1000.0, "C6": 0.025, "C7": 0.008, "C8": 4.0, "C9": 2.0, "C10": 20.0, "C11": 30.0, "C12": 8.0, "C13": 0.60},
    )
    inputs += many(
        case_id,
        "Fraud & Risk",
        {"C5": 1000.0, "C6": 10.0, "C7": 5.0, "C8": 2.0, "C9": 1.0, "C10": 50.0},
    )
    inputs += many(case_id, "Network & Cohorts", {"C3": "Base"})
    add(
        "23",
        "Fintech & Payments",
        "23_Fintech_Payments",
        "23_Fintech_Payments/_template_FINTECH.xlsx",
        case_id,
        "conventional",
        "benchmark_reference_payments.xlsx",
        inputs,
    )

    case_id = "fintech-adversarial-fraud-run"
    inputs = []
    inputs += many(
        case_id,
        "Unit Economics",
        {"C5": 1000.0, "C6": 0.015, "C7": 0.010, "C8": 8.0, "C9": 6.0, "C10": 5.0, "C11": 20.0, "C12": 3.0, "C13": 0.20},
    )
    inputs += many(
        case_id,
        "Fraud & Risk",
        {"C5": 1000.0, "C6": 200.0, "C7": 100.0, "C8": 50.0, "C9": 8.0, "C10": 50.0},
    )
    inputs += many(case_id, "Network & Cohorts", {"C3": "Downside"})
    add(
        "23",
        "Fintech & Payments",
        "23_Fintech_Payments",
        "23_Fintech_Payments/_template_FINTECH.xlsx",
        case_id,
        "adversarial",
        "benchmark_adversarial_fraud_run.xlsx",
        inputs,
        scenario="Downside",
    )

    case_id = "distressed-reference-reorganization"
    inputs = []
    inputs += many(
        case_id,
        "Recovery Waterfall",
        {"C5": 10.0, "C6": 80.0, "C7": 20.0, "C8": 60.0, "C9": 20.0, "C10": 0.0, "C12": 200.0},
    )
    inputs += many(
        case_id,
        "Liquidation vs Reorg",
        {"C5": 180.0, "D5": 220.0, "C6": 30.0, "C7": 10.0, "D7": 15.0, "C8": 6.0, "D8": 18.0, "C9": 0.15},
    )
    inputs += many(case_id, "13-Week Liquidity", {"C3": 20.0, "C4": 5.0})
    inputs += many(case_id, "New Money", {"C5": 25.0, "C7": 0.02, "C8": 0.12, "C9": 1.0, "C10": 0.03, "C11": 1.0})
    add(
        "24",
        "Distressed & Restructuring",
        "24_Distressed_Restructuring",
        "24_Distressed_Restructuring/_template_RESTRUCTURING.xlsx",
        case_id,
        "conventional",
        "benchmark_reference_reorganization.xlsx",
        inputs,
    )

    case_id = "distressed-adversarial-cramdown"
    inputs = []
    inputs += many(
        case_id,
        "Recovery Waterfall",
        {"C5": 15.0, "C6": 80.0, "C7": 20.0, "C8": 50.0, "C9": 20.0, "C10": 0.0, "C12": 100.0},
    )
    inputs += many(
        case_id,
        "Liquidation vs Reorg",
        {"C5": 140.0, "D5": 110.0, "C6": 20.0, "C7": 10.0, "D7": 10.0, "C8": 6.0, "D8": 24.0, "C9": 0.20},
    )
    inputs += many(case_id, "13-Week Liquidity", {"C3": 5.0, "C4": 5.0})
    for row in range(7, 20):
        inputs += many(
            case_id,
            "13-Week Liquidity",
            {f"D{row}": 4.0, f"E{row}": 5.0, f"F{row}": 0.75, f"G{row}": 0.75, f"H{row}": 0.0},
        )
    inputs += many(case_id, "New Money", {"C5": 5.0, "C7": 0.05, "C8": 0.18, "C9": 1.0, "C10": 0.10, "C11": 1.0})
    add(
        "24",
        "Distressed & Restructuring",
        "24_Distressed_Restructuring",
        "24_Distressed_Restructuring/_template_RESTRUCTURING.xlsx",
        case_id,
        "adversarial",
        "benchmark_adversarial_cramdown.xlsx",
        inputs,
        scenario="Downside",
    )

    return specs


def load_state() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    inventory = read_json(INVENTORY_PATH)
    registry = read_json(REGISTRY_PATH)
    candidates = read_json(CANDIDATE_PATH)
    ids = {item["model_id"] for item in candidates["candidates"]}
    if ids != EXPECTED_IDS:
        raise ValueError(f"promotion candidate ids do not match expected cohort: {sorted(ids)}")
    return inventory, registry, candidates


def module_from_builder(builder_path: str):
    if not builder_path.endswith(".py"):
        raise ValueError(f"candidate builder must be a Python file: {builder_path}")
    return importlib.import_module(builder_path[:-3].replace("/", "."))


def build_canonical_templates(
    inventory: dict[str, Any], candidates: dict[str, Any]
) -> list[dict[str, Any]]:
    inventory_by_id = {item["id"]: item for item in inventory["models"]}
    results: list[dict[str, Any]] = []
    for candidate in candidates["candidates"]:
        model_id = candidate["model_id"]
        model = inventory_by_id[model_id]
        module = module_from_builder(candidate["candidate_builder"])
        output = ROOT / model["workbook"]
        module.build(output)
        validation = validate_workbook(model_id, output)
        if validation["status"] != "PASS":
            raise RuntimeError(f"canonical contract failure {model_id}: {validation['errors']}")
        results.append(validation)
    return results


def write_manifests_and_instances() -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    specs = case_specs()
    if len(specs) != 18:
        raise ValueError(f"expected 18 promotion cases, found {len(specs)}")
    if {spec["model_id"] for spec in specs} != EXPECTED_IDS:
        raise ValueError("promotion case coverage does not match expected cohort")
    for spec in specs:
        manifest = {
            "schema_version": "1.1",
            "id": spec["id"],
            "classification": "synthetic_engineering_benchmark",
            "counts_toward_M4": False,
            "domain": spec["domain"],
            "model_id": spec["model_id"],
            "case_type": spec["case_type"],
            "template": spec["template"],
            "output": spec["output"],
            "as_of": AS_OF,
            "scenario": spec["scenario"],
            "cover": spec["cover"],
            "inputs": spec["inputs"],
            "sources": [source(spec["id"])],
            "refresh": {
                "date": AS_OF,
                "trigger": "M1-to-M2 domain hardening benchmark",
                "source_snapshot": "repo://standards/domain_hardening/m1_registry.json",
                "what_changed": (
                    f"Generated {spec['case_type']} benchmark {spec['id']} from the "
                    "canonical hardened release template"
                ),
                "reviewer_notes": (
                    "Synthetic engineering fixture only; does not count toward M4 or live approval"
                ),
                "next_check": "On builder, reference-check, formula, or contract change",
            },
        }
        manifest_path = BENCHMARK_DIR / f"{spec['id']}.json"
        write_json(manifest_path, manifest)
        receipt = apply_manifest(manifest_path, ROOT)
        receipt["model_id"] = spec["model_id"]
        receipt["domain"] = spec["domain"]
        receipt["case_type"] = spec["case_type"]
        receipt["classification"] = manifest["classification"]
        receipt["counts_toward_M4"] = False
        receipts.append(receipt)
    return receipts


def stage_inventory(
    inventory: dict[str, Any], candidates: dict[str, Any]
) -> dict[str, Any]:
    candidate_by_id = {
        item["model_id"]: item for item in candidates["candidates"]
    }
    changed = []
    for model in inventory["models"]:
        candidate = candidate_by_id.get(model["id"])
        if candidate is None:
            continue
        model["builder"] = candidate["candidate_builder"]
        model["declared_maturity"] = "M2"
        model["reference_checks"] = list(candidate["reference_checks"])
        changed.append(model["id"])
    if set(changed) != EXPECTED_IDS:
        raise ValueError(f"inventory staging missed candidates: {sorted(changed)}")
    write_json(INVENTORY_PATH, inventory)
    return inventory


def prepare() -> dict[str, Any]:
    inventory, registry, candidates = load_state()
    canonical = build_canonical_templates(inventory, candidates)
    receipts = write_manifests_and_instances()
    stage_inventory(inventory, candidates)
    candidates["status"] = "applied_pending_release_validation"
    candidates["prepared_from_head"] = current_head()
    candidates["prepared_on"] = date.today().isoformat()
    write_json(CANDIDATE_PATH, candidates)
    report = {
        "schema_version": "1.0",
        "phase": "prepare",
        "status": "PASS",
        "source_head": current_head(),
        "canonical_models": len(canonical),
        "benchmark_instances": len(receipts),
        "canonical_results": canonical,
        "benchmark_outputs": [receipt["output"] for receipt in receipts],
        "inventory_staged_m2": sorted(EXPECTED_IDS),
        "statement": (
            "Inventory declarations are staged only in the workflow working tree. "
            "No promotion is committed until recalculation, post-contract, audit, and finalize pass."
        ),
    }
    write_json(REPORT_PATH, report)
    return report


def refresh_receipts() -> list[dict[str, Any]]:
    receipts = []
    for spec in case_specs():
        output = ROOT / spec["output"]
        receipt_path = output.with_suffix(".receipt.json")
        if not output.is_file() or not receipt_path.is_file():
            raise FileNotFoundError(f"missing promotion instance or receipt: {output}")
        receipt = read_json(receipt_path)
        receipt["workbook_sha256"] = sha256(output)
        receipt["generated_on"] = date.today().isoformat()
        receipt["refresh_schema"] = "source-addressed-v2"
        receipt["model_id"] = spec["model_id"]
        receipt["domain"] = spec["domain"]
        receipt["case_type"] = spec["case_type"]
        receipt["classification"] = "synthetic_engineering_benchmark"
        receipt["counts_toward_M4"] = False
        write_json(receipt_path, receipt)
        receipts.append(receipt)
    return receipts


def rebuild_benchmark_index(new_receipts: list[dict[str, Any]]) -> dict[str, Any]:
    existing = read_json(BENCHMARK_INDEX_PATH)
    new_ids = {receipt["instance_id"] for receipt in new_receipts}
    retained = [
        item
        for item in existing.get("instances", [])
        if item.get("instance_id") not in new_ids
    ]
    instances = retained + sorted(new_receipts, key=lambda item: item["instance_id"])
    index = {
        "schema_version": "1.2",
        "as_of": AS_OF,
        "classification": "synthetic_engineering_benchmarks",
        "counts_toward_M4": False,
        "instance_count": len(instances),
        "instances": instances,
    }
    if len(instances) != 36:
        raise ValueError(f"expected 36 total benchmark instances, found {len(instances)}")
    write_json(BENCHMARK_INDEX_PATH, index)
    return index


def validate_staged_inventory() -> dict[str, Any]:
    inventory = read_json(INVENTORY_PATH)
    models = {item["id"]: item for item in inventory["models"]}
    candidates = read_json(CANDIDATE_PATH)
    errors = []
    for candidate in candidates["candidates"]:
        model = models[candidate["model_id"]]
        if model["declared_maturity"] != "M2":
            errors.append(f"{model['id']}: maturity is not M2")
        if model["builder"] != candidate["candidate_builder"]:
            errors.append(f"{model['id']}: canonical builder mismatch")
        if model["reference_checks"] != candidate["reference_checks"]:
            errors.append(f"{model['id']}: reference-check mismatch")
        validation = validate_workbook(model["id"], ROOT / model["workbook"])
        if validation["status"] != "PASS":
            errors.append(f"{model['id']}: canonical workbook contract failed")
    return {
        "errors": errors,
        "status": "PASS" if not errors else "FAIL",
        "m2_models": sorted(EXPECTED_IDS),
    }


def finalize() -> dict[str, Any]:
    _, _, candidates = load_state()
    if candidates.get("status") != "applied_pending_release_validation":
        raise ValueError(
            "finalize requires applied_pending_release_validation candidate status"
        )
    receipts = refresh_receipts()
    index = rebuild_benchmark_index(receipts)
    inventory_result = validate_staged_inventory()
    if inventory_result["status"] != "PASS":
        raise RuntimeError(inventory_result["errors"])
    candidates["status"] = "applied_release_validated"
    candidates["validated_on"] = date.today().isoformat()
    candidates["validated_source_head"] = candidates.get("prepared_from_head")
    write_json(CANDIDATE_PATH, candidates)
    report = {
        "schema_version": "1.0",
        "phase": "finalize",
        "status": "PASS",
        "source_head": candidates.get("prepared_from_head"),
        "canonical_models": 9,
        "benchmark_instances_added": 18,
        "benchmark_instances_total": index["instance_count"],
        "m2_promoted": sorted(EXPECTED_IDS),
        "inventory_validation": inventory_result,
        "receipt_hashes_current": all(
            sha256(ROOT / receipt["output"]) == receipt["workbook_sha256"]
            for receipt in receipts
        ),
        "counts_toward_M4": False,
        "statement": (
            "The nine domains are promoted to M2 based on independent references, "
            "adversarial cases, canonical workbook contracts, spreadsheet execution, "
            "and source-addressed benchmark receipts. No M3 or M4 claim is made."
        ),
    }
    write_json(REPORT_PATH, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "finalize"))
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args()
    report = prepare() if args.phase == "prepare" else finalize()
    if args.report != REPORT_PATH:
        write_json(args.report, report)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
