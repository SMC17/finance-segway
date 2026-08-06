"""Report model-library coverage against a bank's coverage-group structure.

Twenty-six domains sounds like a lot until you lay it against how a bank
actually organises. Product groups (M&A, LevFin, RX) map cleanly onto model
archetypes -- a restructuring model is a restructuring model regardless of
the client's industry. Sector groups do not: a biopharma DCF and a bank DCF
are different models, not the same model with different inputs, because the
value drivers are structurally different (risk-adjusted pipeline NPV versus
net interest margin and regulatory capital).

So this reports two very different kinds of gap:

  - A product group with no serving domain is a missing archetype.
  - A sector group with no serving domain is missing *sector depth*: the
    generic archetype may run, but nothing in the library reflects that
    sector's actual value drivers.

The second is the larger and less visible gap, and it is the one that
separates "we have 26 models" from "we cover what a coverage banker covers".

Usage:
    python tools/verify_coverage_groups.py
    python tools/verify_coverage_groups.py --report coverage-groups.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COVERAGE = ROOT / "standards" / "universe" / "coverage_groups.json"
SOURCE_STACK = ROOT / "standards" / "universe" / "source_stack.json"
INVENTORY = ROOT / "standards" / "model_inventory.json"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def assess() -> dict[str, Any]:
    coverage = _load(COVERAGE)
    inventory = _load(INVENTORY)
    domains = {item["id"]: item for item in inventory["models"]}

    errors: list[str] = []
    rows: list[dict[str, Any]] = []

    for kind in ("product_groups", "sector_groups"):
        for group in coverage[kind]:
            serving = group.get("serving_domains", [])
            unknown = [item for item in serving if item not in domains]
            if unknown:
                errors.append(
                    f"{group['id']}: serving_domains references unknown model ids {unknown}"
                )
            rows.append(
                {
                    "kind": kind,
                    "id": group["id"],
                    "label": group["label"],
                    "serving_domains": serving,
                    "serving_domain_names": [
                        domains[item]["domain"] for item in serving if item in domains
                    ],
                    "covered": bool(serving),
                    "subsector_count": len(group.get("subsectors", [])),
                    "distinct_modeling_needs": group.get("distinct_modeling_needs", []),
                }
            )

    products = [row for row in rows if row["kind"] == "product_groups"]
    sectors = [row for row in rows if row["kind"] == "sector_groups"]
    uncovered_products = [row for row in products if not row["covered"]]
    uncovered_sectors = [row for row in sectors if not row["covered"]]

    # Sector depth is the count of subsectors under a *covered* sector group.
    # A sector group served by one generic archetype still owes a model per
    # subsector before it reflects real coverage.
    total_subsectors = sum(row["subsector_count"] for row in sectors)

    source_stack = _load(SOURCE_STACK)
    grounding_sources = [
        item["id"]
        for item in source_stack["sources"]
        if "driver_range_grounding" in item.get("primary_for", [])
    ]

    return {
        "status": "PASS" if not errors else "FAIL",
        "product_groups": len(products),
        "product_groups_covered": len(products) - len(uncovered_products),
        "sector_groups": len(sectors),
        "sector_groups_covered": len(sectors) - len(uncovered_sectors),
        "total_subsectors_declared": total_subsectors,
        "uncovered_product_groups": [row["id"] for row in uncovered_products],
        "uncovered_sector_groups": [row["id"] for row in uncovered_sectors],
        "driver_grounding_sources": grounding_sources,
        "errors": errors,
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    report = assess()

    for kind, title in (("product_groups", "PRODUCT GROUPS"), ("sector_groups", "SECTOR GROUPS")):
        print(f"\n{title}")
        print("-" * 96)
        for row in [item for item in report["rows"] if item["kind"] == kind]:
            mark = "OK " if row["covered"] else "GAP"
            serving = ", ".join(row["serving_domain_names"]) or "(no serving domain)"
            subs = f"{row['subsector_count']} subsectors" if row["subsector_count"] else ""
            print(f"  [{mark}] {row['label']:<42} {serving:<40} {subs}")

    print("\n" + "=" * 96)
    print(
        f"Product groups covered: {report['product_groups_covered']}/{report['product_groups']}  "
        f"Sector groups covered: {report['sector_groups_covered']}/{report['sector_groups']}  "
        f"Subsectors declared: {report['total_subsectors_declared']}"
    )
    if report["uncovered_sector_groups"]:
        print(
            "\nUncovered sector groups (no domain reflects these value drivers):\n  "
            + ", ".join(report["uncovered_sector_groups"])
        )
    print(
        "\nNote: a covered sector group still owes a model per subsector before it "
        "matches real coverage.\nSector depth, not archetype count, is the binding "
        "constraint -- a biopharma DCF and a bank DCF are\ndifferent models, not one "
        "model with different inputs."
    )
    print(
        f"\nDriver ranges are grounded from: {', '.join(report['driver_grounding_sources'])} "
        "(see standards/universe/source_stack.json)"
    )

    if report["errors"]:
        print("\nErrors:")
        for error in report["errors"]:
            print(f"  {error}")

    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
