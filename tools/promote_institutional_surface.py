"""Promote the institutional decision surface across all committed workbooks."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from institutional_surface import (
    apply_surface,
    load_inventory,
    profiles_by_id,
    validate_profiles,
    validate_workbook_surface,
)


def promote(root: Path) -> dict:
    errors = validate_profiles(root)
    inventory = load_inventory(root)
    profiles = profiles_by_id(root)
    results = []
    for model in inventory["models"]:
        workbook = root / model["workbook"]
        if not workbook.exists():
            errors.append(f"{model['id']}:missing_workbook:{model['workbook']}")
            continue
        receipt = apply_surface(workbook, model, profiles[model["id"]])
        errors.extend(validate_workbook_surface(workbook, model, profiles[model["id"]]))
        results.append(receipt)
    return {
        "inventory_version": inventory["version"],
        "models": len(inventory["models"]),
        "promoted": len(results),
        "errors": sorted(set(errors)),
        "results": results,
        "status": "PASS" if not errors else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--report", type=Path, default=Path("institutional-surface-report.json"))
    args = parser.parse_args()
    root = args.root.resolve()
    report = promote(root)
    output = args.report if args.report.is_absolute() else root / args.report
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "models": report["models"],
        "promoted": report["promoted"],
        "errors": len(report["errors"]),
        "status": report["status"],
    }, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
