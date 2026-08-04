"""Canonical release wrapper for the institutional options builder."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_options_institutional import build as build_layout  # noqa: E402
from formula_compatibility import normalize_workbook_formulas  # noqa: E402
from institutional_helpers import finalize  # noqa: E402


def build(output: Path) -> None:
    build_layout(output)
    workbook = load_workbook(output)
    normalize_workbook_formulas(workbook)
    finalize(workbook, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("OPTIONS_template.xlsx"))
    arguments = parser.parse_args()
    build(arguments.output)
    print(f"saved {arguments.output}")
