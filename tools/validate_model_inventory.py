"""Validate the finance-segway model inventory and maturity claims.

The inventory is deliberately conservative: it distinguishes a correct skeleton
from a decision model, institutional underwriting model, and maintained
production system. CI should fail when the repository claims a maturity level
without the evidence required for that level.

Usage:
    python tools/validate_model_inventory.py
    python tools/validate_model_inventory.py --report /tmp/model-report.json
    python tools/validate_model_inventory.py --strict
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = ROOT / "standards" / "model_inventory.json"
ALLOWED_MATURITY = {"M0", "M1", "M2", "M3", "M4"}
ALLOWED_HORIZONS = {
    "trading_intraday",
    "trading_daily",
    "short_term_1y",
    "corporate_5y",
    "corporate_10y",
    "long_term_10y",
    "long_term_30y",
    "long_term_40y",
    "perpetual",
}
ERROR_TOKENS = {"#REF!", "#NAME?", "#VALUE!", "#DIV/0!", "#N/A", "#NULL!", "#NUM!"}


@dataclass
class ModelResult:
    model_id: str
    domain: str
    maturity: str
    workbook: str
    formula_count: int = 0
    sheet_count: int = 0
    instance_count: int = 0
    errors: list[str] | None = None
    warnings: list[str] | None = None

    def __post_init__(self) -> None:
        self.errors = [] if self.errors is None else self.errors
        self.warnings = [] if self.warnings is None else self.warnings


def load_inventory(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data.get("models"), list):
        raise ValueError("inventory must contain a models list")
    return data


def count_instances(folder: Path) -> int:
    if not folder.exists():
        return 0
    count = 0
    for path in folder.rglob("*.xlsx"):
        if path.name.startswith("_template") or path.name.startswith("~$"):
            continue
        count += 1
    return count


def inspect_workbook(path: Path, result: ModelResult) -> set[str]:
    try:
        workbook = openpyxl.load_workbook(path, data_only=False, read_only=False)
    except Exception as exc:  # noqa: BLE001
        result.errors.append(f"workbook cannot be opened: {exc}")
        return set()

    sheetnames = set(workbook.sheetnames)
    result.sheet_count = len(workbook.sheetnames)
    if "Cover" not in sheetnames:
        result.errors.append("missing Cover sheet")
    if "RefreshLog" not in sheetnames:
        result.errors.append("missing RefreshLog sheet")
    if getattr(workbook, "_external_links", []):
        result.errors.append("contains external workbook links")

    literal_errors: list[str] = []
    formula_count = 0
    for sheet in workbook.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                value = cell.value
                if isinstance(value, str) and value.startswith("="):
                    formula_count += 1
                elif isinstance(value, str) and value.strip() in ERROR_TOKENS:
                    literal_errors.append(f"{sheet.title}!{cell.coordinate}={value}")
    result.formula_count = formula_count
    if literal_errors:
        result.errors.append(f"literal Excel errors: {literal_errors[:5]}")
    return sheetnames


def validate_model(model: dict[str, Any]) -> ModelResult:
    model_id = str(model.get("id", ""))
    domain = str(model.get("domain", ""))
    maturity = str(model.get("declared_maturity", ""))
    workbook_rel = str(model.get("workbook", ""))
    result = ModelResult(model_id, domain, maturity, workbook_rel)

    required_strings = ("id", "domain", "folder", "archetype", "workbook", "builder", "horizon")
    for field in required_strings:
        if not isinstance(model.get(field), str) or not model[field].strip():
            result.errors.append(f"missing or invalid {field}")

    if maturity not in ALLOWED_MATURITY:
        result.errors.append(f"invalid maturity {maturity!r}")
    if model.get("target_maturity") not in ALLOWED_MATURITY:
        result.errors.append(f"invalid target maturity {model.get('target_maturity')!r}")
    if model.get("horizon") not in ALLOWED_HORIZONS:
        result.errors.append(f"invalid horizon {model.get('horizon')!r}")

    engines = model.get("required_engines")
    perspectives = model.get("required_perspectives")
    reference_checks = model.get("reference_checks")
    if not isinstance(engines, list) or not engines:
        result.errors.append("required_engines must be a non-empty list")
    if not isinstance(perspectives, list) or not perspectives:
        result.errors.append("required_perspectives must be a non-empty list")
    if not isinstance(reference_checks, list):
        result.errors.append("reference_checks must be a list")

    folder = ROOT / str(model.get("folder", ""))
    workbook = ROOT / workbook_rel
    builder = ROOT / str(model.get("builder", ""))
    if not folder.is_dir():
        result.errors.append(f"domain folder missing: {folder.relative_to(ROOT)}")
    sheetnames: set[str] = set()
    if not workbook.is_file():
        result.errors.append(f"workbook missing: {workbook_rel}")
    else:
        sheetnames = inspect_workbook(workbook, result)
    if not builder.is_file():
        result.errors.append(f"builder missing: {builder.relative_to(ROOT)}")

    result.instance_count = count_instances(folder)

    if maturity in {"M1", "M2", "M3", "M4"}:
        if result.formula_count == 0:
            result.errors.append("M1+ requires at least one formula")
        if result.sheet_count < 2:
            result.errors.append("M1+ requires multiple worksheets")

    if maturity in {"M2", "M3", "M4"}:
        if not reference_checks:
            result.errors.append("M2+ requires at least one independent reference check")
        if result.formula_count < 20:
            result.errors.append("M2+ requires at least 20 formula cells")
        if len(engines or []) < 3:
            result.errors.append("M2+ requires at least three documented domain engines")

    if maturity in {"M3", "M4"}:
        if len(perspectives or []) < 3:
            result.errors.append("M3+ requires at least three stakeholder perspectives")
        if "Sources" not in sheetnames:
            result.errors.append("M3+ requires a Sources sheet")
        if "Checks" not in sheetnames:
            result.errors.append("M3+ requires a Checks sheet")

    if maturity == "M4":
        minimum_instances = int(model.get("minimum_instances_for_M4", 2))
        if result.instance_count < minimum_instances:
            result.errors.append(
                f"M4 requires at least {minimum_instances} populated instances; found {result.instance_count}"
            )

    if model.get("target_maturity") == maturity:
        result.warnings.append("declared maturity already equals target; confirm next promotion target")

    return result


def validate_inventory(data: dict[str, Any]) -> tuple[list[ModelResult], list[str]]:
    models = data["models"]
    inventory_errors: list[str] = []
    if len(models) != 24:
        inventory_errors.append(f"expected 24 core model domains; found {len(models)}")

    ids = [str(model.get("id", "")) for model in models]
    folders = [str(model.get("folder", "")) for model in models]
    workbooks = [str(model.get("workbook", "")) for model in models]
    for label, values in (("id", ids), ("folder", folders), ("workbook", workbooks)):
        duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
        if duplicates:
            inventory_errors.append(f"duplicate {label} values: {duplicates}")

    return [validate_model(model) for model in models], inventory_errors


def print_summary(results: list[ModelResult], inventory_errors: list[str]) -> None:
    print("Finance-Segway Model Inventory")
    print("=" * 88)
    print(f"{'ID':<4} {'Domain':<36} {'Mat':<4} {'Sheets':>6} {'Formulas':>9} {'Inst':>5} Status")
    print("-" * 88)
    for result in results:
        status = "FAIL" if result.errors else ("WARN" if result.warnings else "PASS")
        print(
            f"{result.model_id:<4} {result.domain[:36]:<36} {result.maturity:<4} "
            f"{result.sheet_count:>6} {result.formula_count:>9} {result.instance_count:>5} {status}"
        )
        for error in result.errors:
            print(f"     ERROR: {error}")
        for warning in result.warnings:
            print(f"     WARN:  {warning}")
    for error in inventory_errors:
        print(f"INVENTORY ERROR: {error}")

    maturity_counts = Counter(result.maturity for result in results)
    print("-" * 88)
    print("Maturity distribution:", ", ".join(f"{k}={maturity_counts[k]}" for k in sorted(maturity_counts)))


def write_report(path: Path, results: list[ModelResult], inventory_errors: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "inventory_errors": inventory_errors,
        "models": [asdict(result) for result in results],
        "summary": {
            "models": len(results),
            "failed": sum(bool(result.errors) for result in results),
            "warnings": sum(bool(result.warnings) for result in results),
            "maturity_distribution": dict(Counter(result.maturity for result in results)),
        },
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--report", type=Path)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as failures. Useful for release promotion, not routine PR checks.",
    )
    args = parser.parse_args()

    try:
        data = load_inventory(args.inventory)
        results, inventory_errors = validate_inventory(data)
    except Exception as exc:  # noqa: BLE001
        print(f"inventory validation could not start: {exc}", file=sys.stderr)
        return 2

    print_summary(results, inventory_errors)
    if args.report:
        write_report(args.report, results, inventory_errors)

    failed = bool(inventory_errors) or any(result.errors for result in results)
    if args.strict:
        failed = failed or any(result.warnings for result in results)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
