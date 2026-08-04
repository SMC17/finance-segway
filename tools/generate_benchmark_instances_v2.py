"""Generate the source-addressed benchmark instance release."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from generate_benchmark_instances import AS_OF, cases, source
from model_instance_release import apply_manifest


def generate(root: Path) -> dict:
    manifest_root = root / "standards" / "benchmark_cases"
    manifest_root.mkdir(parents=True, exist_ok=True)
    receipts = []
    for case in cases():
        manifest = {
            "schema_version": "1.1",
            "id": case["id"],
            "classification": "synthetic_engineering_benchmark",
            "counts_toward_M4": False,
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
                "source_snapshot": f"repo://standards/benchmark_cases/{case['id']}.json",
                "what_changed": f"Generated {case['id']} from canonical release template",
                "reviewer_notes": "Engineering fixture only; not public underwriting or M4 evidence",
                "next_check": "On builder, formula, or contract change",
            },
        }
        manifest_path = manifest_root / f"{case['id']}.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        receipts.append(apply_manifest(manifest_path, root))
    index = {
        "schema_version": "1.1",
        "as_of": AS_OF,
        "classification": "synthetic_engineering_benchmarks",
        "counts_toward_M4": False,
        "instance_count": len(receipts),
        "instances": receipts,
    }
    (manifest_root / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    return index


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    index = generate(args.root.resolve())
    print(json.dumps({
        "instances": index["instance_count"],
        "counts_toward_M4": index["counts_toward_M4"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
