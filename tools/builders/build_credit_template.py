"""Compatibility entrypoint for the canonical private-credit builder."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_private_credit_template import build  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("CREDIT_template.xlsx"))
    args = parser.parse_args()
    build(args.output)
    print(f"saved {args.output}")
