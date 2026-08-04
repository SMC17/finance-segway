"""Regenerate selected real public cases and update their receipt ledger entries."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from tools.model_instance_release import apply_manifest
except ModuleNotFoundError:
    from model_instance_release import apply_manifest


def refresh_public_cases(root: Path, case_ids: list[str]) -> dict[str, Any]:
    root = root.resolve()
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("public case ids must be unique")
    index_path = root / "standards/public_cases/index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    by_id = {item["case_id"]: item for item in index.get("cases", [])}
    missing = sorted(set(case_ids) - set(by_id))
    if missing:
        raise ValueError(f"unknown public case ids: {', '.join(missing)}")
    refreshed = []
    for case_id in case_ids:
        item = by_id[case_id]
        manifest_path = root / item["manifest"]
        receipt = apply_manifest(manifest_path, root)
        item["receipt"] = receipt
        refreshed.append(
            {
                "case_id": case_id,
                "output": item["output"],
                "workbook_sha256": receipt["workbook_sha256"],
            }
        )
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    return {"refreshed": refreshed, "case_count": index.get("case_count")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("case_id", nargs="+")
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    print(json.dumps(refresh_public_cases(args.root, args.case_id), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
