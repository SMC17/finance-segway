"""Canonical release wrapper for the institutional insurance builder."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_insurance_institutional import build as build_layout  # noqa: E402
from institutional_helpers import finalize  # noqa: E402


def build(output: Path) -> None:
    build_layout(output)
    workbook = load_workbook(output)
    chain = workbook["Chain Ladder"]
    # At ultimate development the cumulative development factor must be one.
    chain["L6"] = 1.0
    chain["L6"].number_format = "0.0000x"
    finalize(workbook, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("INSURANCE_template.xlsx"))
    arguments = parser.parse_args()
    build(arguments.output)
    print(f"saved {arguments.output}")
