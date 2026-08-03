"""Validate integrated credit and public-finance builders and templates.

This gate deliberately compares stable workbook contracts rather than binary
hashes. XLSX ZIP metadata and producer details may differ, while sheet order,
scenario controls, formula anchors, source/check tabs, and minimum modeling
depth must remain stable.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
BUILDERS = ROOT / "tools" / "builders"
ERROR_TOKENS = {"#REF!", "#NAME?", "#VALUE!", "#DIV/0!", "#N/A", "#NULL!", "#NUM!"}


@dataclass(frozen=True)
class ModelCase:
    name: str
    builder: Path
    committed: tuple[Path, ...]
    required_tabs: tuple[str, ...]
    formula_anchors: frozenset[str]
    minimum_formula_cells: int


CASES = (
    ModelCase(
        name="credit",
        builder=BUILDERS / "build_credit_template.py",
        committed=(
            ROOT / "05_Private_Credit" / "_template_CREDIT.xlsx",
            ROOT / "06_Debt_Finance" / "_template_CREDIT.xlsx",
        ),
        required_tabs=(
            "Cover", "Assumptions", "Operating Case", "Debt Schedule", "Covenants",
            "Yield & Spread", "Recovery", "Sensitivity", "Checks", "Sources", "RefreshLog",
        ),
        formula_anchors=frozenset({
            "Assumptions!E5", "Operating Case!D5", "Operating Case!H14",
            "Debt Schedule!D15", "Debt Schedule!H18", "Covenants!C14",
            "Yield & Spread!C9", "Recovery!C12", "Sensitivity!G9", "Checks!C9",
        }),
        minimum_formula_cells=220,
    ),
    ModelCase(
        name="public_finance",
        builder=BUILDERS / "build_public_finance_template.py",
        committed=(ROOT / "07_Public_Finance" / "_template_PUBLIC_FINANCE.xlsx",),
        required_tabs=(
            "Cover", "Assumptions", "Debt Sustainability", "Revenue & Expenditure",
            "Debt Service", "Coverage", "Scenarios", "Sensitivity", "Checks", "Sources", "RefreshLog",
        ),
        formula_anchors=frozenset({
            "Assumptions!E5", "Debt Sustainability!C10", "Debt Sustainability!C12",
            "Revenue & Expenditure!D5", "Revenue & Expenditure!H14",
            "Debt Service!C11", "Debt Service!G15", "Coverage!C15",
            "Scenarios!C10", "Sensitivity!G9", "Checks!C10",
        }),
        minimum_formula_cells=220,
    ),
)


def workbook_signature(path: Path, case: ModelCase) -> dict:
    workbook = openpyxl.load_workbook(path, data_only=False, read_only=False)
    if tuple(workbook.sheetnames) != case.required_tabs:
        raise AssertionError(
            f"{path}: sheet order/contract differs; got {workbook.sheetnames}"
        )
    if workbook["Cover"]["C6"].value in (None, ""):
        raise AssertionError(f"{path}: Cover!C6 must hold Last refreshed")
    if workbook["Cover"]["C7"].value in (None, ""):
        raise AssertionError(f"{path}: Cover!C7 must hold Next material date")
    if workbook["Cover"]["C9"].value not in {"Base", "Downside"}:
        raise AssertionError(f"{path}: Cover!C9 must be Base or Downside")
    if getattr(workbook, "_external_links", []):
        raise AssertionError(f"{path}: external workbook links are not allowed")

    formulas: dict[str, str] = {}
    literal_errors: list[str] = []
    for sheet in workbook.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    formulas[f"{sheet.title}!{cell.coordinate}"] = cell.value
                elif isinstance(cell.value, str) and cell.value.strip() in ERROR_TOKENS:
                    literal_errors.append(f"{sheet.title}!{cell.coordinate}={cell.value}")
    if literal_errors:
        raise AssertionError(f"{path}: literal Excel errors found: {literal_errors[:10]}")
    if len(formulas) < case.minimum_formula_cells:
        raise AssertionError(
            f"{path}: only {len(formulas)} formulas; expected at least {case.minimum_formula_cells}"
        )
    missing_anchors = case.formula_anchors - formulas.keys()
    if missing_anchors:
        raise AssertionError(f"{path}: missing formula anchors {sorted(missing_anchors)}")
    return {"sheets": tuple(workbook.sheetnames), "formula_count": len(formulas)}


def build(builder: Path, output: Path) -> None:
    subprocess.run(
        [sys.executable, str(builder), "--output", str(output)],
        cwd=BUILDERS,
        check=True,
    )


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="finance-model-validation-") as temp_dir:
        temp = Path(temp_dir)
        for case in CASES:
            try:
                generated = temp / f"{case.name}.xlsx"
                build(case.builder, generated)
                generated_signature = workbook_signature(generated, case)
                for committed in case.committed:
                    committed_signature = workbook_signature(committed, case)
                    if generated_signature["sheets"] != committed_signature["sheets"]:
                        raise AssertionError(
                            f"{committed}: sheet contract differs from {case.builder.name} output"
                        )
                print(
                    f"PASS {case.name}: builder and committed templates satisfy the same "
                    f"contract ({generated_signature['formula_count']} generated formulas)"
                )
            except Exception as exc:  # noqa: BLE001 - aggregate all model failures
                failures.append(f"{case.name}: {exc}")

    if failures:
        print("\nIntegrated-model validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
