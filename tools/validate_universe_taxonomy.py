"""Validate the universe taxonomy, failing closed on unsourced claims.

The taxonomy is the backlog a swarm works through, which makes it exactly
the artifact most likely to accumulate quiet fabrication: a sector guessed
because it is obvious, a constituent added from memory, a weight nudged so
the total reconciles. Each of those is individually harmless-looking and
collectively fatal to the claim that everything here traces to disclosure.

So the rules are mechanical:

  - Every universe names a source with a URL and a recorded snapshot that
    exists on disk.
  - Every sector weight comes from a source, and the disclosed weights
    reconcile to the universe's own disclosed total within tolerance.
  - No company carries a sector_id without a sector_source. This is the
    load-bearing one: sector assignment is the single easiest thing to
    autofill and the hardest to notice once wrong.
  - Every modelable company has a resolvable symbol; every non-modelable
    one states why.
  - domain_sector_scope entries reference real model ids and real sector
    ids, and each carries a rationale (it is a scope decision, so it must
    be argued, not asserted).

Usage:
    python tools/validate_universe_taxonomy.py
    python tools/validate_universe_taxonomy.py --report universe-report.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TAXONOMY = ROOT / "standards" / "universe" / "taxonomy.json"
INVENTORY = ROOT / "standards" / "model_inventory.json"

# Disclosed sector weights need not sum to exactly 1: cash, futures, and
# unclassified positions are excluded from an issuer's sector table but
# included in its holdings. QQQ's own disclosure sums to 0.967.
SECTOR_WEIGHT_FLOOR = 0.90
SECTOR_WEIGHT_CEILING = 1.01
HOLDINGS_WEIGHT_CEILING = 1.02


def validate(path: Path = TAXONOMY) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not path.exists():
        return {"status": "FAIL", "errors": [f"missing taxonomy: {path}"], "warnings": []}

    taxonomy = json.loads(path.read_text(encoding="utf-8"))
    universes = {item["id"]: item for item in taxonomy.get("universes", [])}
    sectors = {item["id"]: item for item in taxonomy.get("sectors", [])}
    companies = taxonomy.get("companies", [])

    if not universes:
        errors.append("taxonomy declares no universes")

    for universe_id, universe in universes.items():
        source = universe.get("source") or {}
        if not str(source.get("url", "")).strip():
            errors.append(f"{universe_id}: universe source has no url")
        snapshot = str(source.get("snapshot", "")).strip()
        if not snapshot:
            errors.append(f"{universe_id}: universe source names no recorded snapshot")
        elif not (ROOT / snapshot).exists():
            errors.append(f"{universe_id}: recorded snapshot missing on disk: {snapshot}")
        if not str(source.get("as_of", "")).strip():
            errors.append(f"{universe_id}: universe source has no as_of date")

    sector_total = sum(float(item.get("disclosed_weight", 0.0)) for item in sectors.values())
    if sectors and not (SECTOR_WEIGHT_FLOOR <= sector_total <= SECTOR_WEIGHT_CEILING):
        errors.append(
            f"disclosed sector weights sum to {sector_total:.4f}, outside the plausible "
            f"band [{SECTOR_WEIGHT_FLOOR}, {SECTOR_WEIGHT_CEILING}]"
        )
    for sector_id, sector in sectors.items():
        if not (sector.get("source") or {}).get("url"):
            errors.append(f"sector {sector_id}: no source url")

    seen_symbols: set[str] = set()
    membership_totals: dict[str, float] = {}
    for company in companies:
        symbol = company.get("symbol")
        label = symbol or company.get("name") or "<unnamed>"

        # The load-bearing rule.
        if company.get("sector_id") and not company.get("sector_source"):
            errors.append(
                f"{label}: sector_id {company['sector_id']!r} asserted with no "
                "sector_source -- sector assignment requires a citation"
            )
        if company.get("sector_id") and company["sector_id"] not in sectors:
            errors.append(f"{label}: sector_id {company['sector_id']!r} is not a declared sector")

        if company.get("modelable"):
            if not symbol:
                errors.append(f"{label}: marked modelable but has no resolvable symbol")
            if symbol and symbol in seen_symbols:
                errors.append(f"{symbol}: duplicate company entry")
            if symbol:
                seen_symbols.add(symbol)
        elif not company.get("not_modelable_reason"):
            errors.append(f"{label}: marked not modelable without a stated reason")

        memberships = company.get("memberships") or []
        if not memberships:
            errors.append(f"{label}: belongs to no universe")
        for membership in memberships:
            universe_id = membership.get("universe")
            if universe_id not in universes:
                errors.append(f"{label}: membership in unknown universe {universe_id!r}")
                continue
            weight = float(membership.get("weight", 0.0))
            if weight < 0:
                errors.append(f"{label}: negative weight in {universe_id}")
            membership_totals[universe_id] = membership_totals.get(universe_id, 0.0) + weight

    for universe_id, total in membership_totals.items():
        if total > HOLDINGS_WEIGHT_CEILING:
            errors.append(
                f"{universe_id}: constituent weights sum to {total:.4f}, above "
                f"{HOLDINGS_WEIGHT_CEILING} -- constituents may be duplicated"
            )
        declared = universes[universe_id].get("disclosed_constituent_count")
        actual = sum(
            1
            for company in companies
            if any(m.get("universe") == universe_id for m in company.get("memberships", []))
        )
        if declared is not None and declared != actual:
            errors.append(
                f"{universe_id}: declares {declared} constituents but taxonomy holds {actual}"
            )

    inventory_ids = {item["id"] for item in json.loads(INVENTORY.read_text())["models"]}
    for entry in taxonomy.get("domain_sector_scope", []):
        model_id = entry.get("model_id")
        if model_id not in inventory_ids:
            errors.append(f"scope entry references unknown model_id {model_id!r}")
        if not str(entry.get("rationale", "")).strip():
            errors.append(f"scope entry for {model_id!r} has no rationale")
        for sector_id in entry.get("sectors", []):
            if sector_id not in sectors:
                errors.append(f"scope entry {model_id!r} references unknown sector {sector_id!r}")

    unmapped = [item for item in companies if not item.get("sector_id")]
    if unmapped:
        warnings.append(
            f"{len(unmapped)}/{len(companies)} companies have no sourced sector mapping yet "
            "(expected: mapping requires its own classification source)"
        )
    if not taxonomy.get("domain_sector_scope"):
        warnings.append("domain_sector_scope is empty -- no domain coverage declared yet")

    modelable = [item for item in companies if item.get("modelable")]
    return {
        "status": "PASS" if not errors else "FAIL",
        "universes": len(universes),
        "sectors": len(sectors),
        "companies": len(companies),
        "modelable_companies": len(modelable),
        "sector_mapped_companies": len(companies) - len(unmapped),
        "declared_scope_entries": len(taxonomy.get("domain_sector_scope", [])),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    report = validate()
    print(json.dumps(report, indent=2))
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
