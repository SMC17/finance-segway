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

    # NOTE: this used to also overwrite Checks!C5 ("Paid triangle
    # cumulative") with a hand-rolled scalar-difference MIN(...) formula --
    # motivated by a real LibreOffice constraint (it evaluates range
    # subtraction inside MIN as an array and returns #VALUE, unlike Excel),
    # but built over the *full* rectangular D5:L14/C5:K14 block regardless
    # of each accident year's actual observed development periods. A loss
    # triangle is deliberately ragged -- most rows have blank cells beyond
    # their observed periods, and Excel/LibreOffice both treat a blank as 0
    # in subtraction, so "blank(=0) minus a real value" is large and
    # negative for nearly every row. That silently failed this check for
    # every real instance in the domain regardless of the underlying data.
    # build_insurance_institutional.build_layout() now generates the same
    # scalar-difference form directly (already LibreOffice-safe), but only
    # over adjacent *observed* period pairs per row -- so this override is
    # both redundant and wrong; removed rather than duplicating the fix here.

    finalize(workbook, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("INSURANCE_template.xlsx"))
    arguments = parser.parse_args()
    build(arguments.output)
    print(f"saved {arguments.output}")
