"""Apply institutional surfaces to every artifact in the M1-to-M2 promotion.

The domain release builders intentionally own only the financial mechanics.
This pass applies the same profile-driven Institutional Surface, Challenge Log,
Lineage Map, and defined-name layer used by full-library builder parity. It is
run after the promotion prepare phase and before LibreOffice recalculation so
canonical templates and populated benchmark instances share one governed
artifact shape.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from tools.institutional_surface import (
        apply_surface,
        profiles_by_id,
        validate_profiles,
        validate_workbook_surface,
    )
    from tools.release_m1_domain_promotions import (
        EXPECTED_IDS,
        INVENTORY_PATH,
        case_specs,
    )
except ModuleNotFoundError:
    from institutional_surface import (
        apply_surface,
        profiles_by_id,
        validate_profiles,
        validate_workbook_surface,
    )
    from release_m1_domain_promotions import EXPECTED_IDS, INVENTORY_PATH, case_specs

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "m1-promotion-surface-report.json"


def load_inventory() -> dict[str, Any]:
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def promotion_targets() -> list[dict[str, str]]:
    inventory = load_inventory()
    models = {item["id"]: item for item in inventory["models"]}
    targets: list[dict[str, str]] = []
    for model_id in sorted(EXPECTED_IDS):
        model = models[model_id]
        targets.append(
            {
                "model_id": model_id,
                "kind": "canonical",
                "path": model["workbook"],
            }
        )
    for spec in case_specs():
        targets.append(
            {
                "model_id": spec["model_id"],
                "kind": spec["case_type"],
                "case_id": spec["id"],
                "path": spec["output"],
            }
        )
    return targets


def apply_all() -> dict[str, Any]:
    inventory = load_inventory()
    models = {item["id"]: item for item in inventory["models"]}
    profiles = profiles_by_id(ROOT)
    errors = list(validate_profiles(ROOT))
    results: list[dict[str, Any]] = []
    targets = promotion_targets()
    if len(targets) != 27:
        errors.append(f"expected 27 promotion artifacts, found {len(targets)}")

    for target in targets:
        model_id = target["model_id"]
        model = models.get(model_id)
        profile = profiles.get(model_id)
        path = ROOT / target["path"]
        target_errors: list[str] = []
        if model is None:
            target_errors.append("missing inventory model")
        if profile is None:
            target_errors.append("missing institutional profile")
        if not path.is_file():
            target_errors.append("missing workbook artifact")
        if not target_errors:
            try:
                apply_surface(path, model, profile)
                target_errors.extend(
                    validate_workbook_surface(path, model, profile)
                )
            except Exception as exc:  # retained in release evidence
                target_errors.append(f"surface application failed: {exc}")
        errors.extend(
            f"{target.get('case_id', target['model_id'])}: {error}"
            for error in target_errors
        )
        results.append(
            {
                **target,
                "errors": target_errors,
                "status": "PASS" if not target_errors else "FAIL",
            }
        )

    canonical = sum(1 for item in targets if item["kind"] == "canonical")
    instances = len(targets) - canonical
    return {
        "schema_version": "1.0",
        "artifacts": len(targets),
        "canonical_templates": canonical,
        "benchmark_instances": instances,
        "institutional_profiles": len(profiles),
        "errors": errors,
        "results": results,
        "status": "PASS" if not errors else "FAIL",
        "statement": (
            "All promotion artifacts use the same profile-driven institutional "
            "surface compiler as full-library builder parity."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = apply_all()
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "artifacts",
                    "canonical_templates",
                    "benchmark_instances",
                    "status",
                    "errors",
                )
            },
            indent=2,
        )
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
