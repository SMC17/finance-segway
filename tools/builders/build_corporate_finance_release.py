"""Release-grade Corporate Finance workbook."""
from __future__ import annotations

import argparse
from pathlib import Path

try:
    from tools.builders.legacy_frontier_release import build_model
except ModuleNotFoundError:
    from legacy_frontier_release import build_model


def build(output: Path) -> None:
    build_model("02", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("BASE_template.xlsx"))
    args = parser.parse_args()
    build(args.output)
    print(f"saved {args.output}")
