"""Generate the domain -> sector -> company taxonomy from recorded real data.

This is the schema a swarm fills. It exists so that "model every company in
the index" is a structured, checkable backlog rather than a pile of ad-hoc
case files, and so that every company in it traces to a real, dated
disclosure rather than to someone's memory of what is in the index.

Two rules make it trustworthy:

  1. Every constituent comes from a recorded source snapshot under
     tools/data_fabric/out/, never from a hand-typed list. If the source
     file is missing the build fails rather than emitting a plausible
     guess.
  2. A company's sector is left null unless a real classification source
     is attached. Sector assignment feels obvious ("NVDA is tech") and is
     exactly the kind of thing that gets fabricated by autofill. The
     issuer-disclosed sector *weights* are real and recorded; the
     per-company mapping is a separate fact that needs its own source, so
     it starts empty and the validator refuses to accept one without a
     citation.

Usage:
    python tools/build_universe_taxonomy.py
    python tools/build_universe_taxonomy.py --output standards/universe/taxonomy.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "standards" / "universe" / "taxonomy.json"

QQQ_PROFILE = ROOT / "tools" / "data_fabric" / "out" / "QQQ_alphavantage_etf_profile.json"

# Holdings that are not modelable operating companies. Kept in the taxonomy
# (they are real disclosed positions and dropping them would silently break
# the weight reconciliation) but flagged so the swarm never tries to build a
# three-statement model for a futures contract.
NON_OPERATING_PATTERNS = (
    (re.compile(r"^CASH$", re.I), "cash_position"),
    (re.compile(r"FUTURE", re.I), "derivative_position"),
)


SIC_SNAPSHOT = ROOT / "tools" / "data_fabric" / "out" / "QQQ_sec_sic_classifications.json"
SIC_CROSSWALK = ROOT / "standards" / "universe" / "sic_crosswalk.json"


def _load_classification() -> tuple[dict, dict]:
    """Per-symbol SEC SIC facts + the committed SIC->bucket judgment layer.

    Classification is optional by design: if either artifact is absent the
    taxonomy builds with sector_id null exactly as before - companies are
    never assigned a sector without both the SEC-filed fact and the
    reviewable crosswalk to cite.
    """
    if not (SIC_SNAPSHOT.exists() and SIC_CROSSWALK.exists()):
        return {}, {}
    snapshot = json.loads(SIC_SNAPSHOT.read_text(encoding="utf-8"))
    crosswalk = json.loads(SIC_CROSSWALK.read_text(encoding="utf-8"))
    return snapshot.get("companies", {}), crosswalk


def _slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.strip().lower()).strip("_")


def _classify_non_operating(description: str) -> str | None:
    for pattern, kind in NON_OPERATING_PATTERNS:
        if pattern.search(description or ""):
            return kind
    return None


def build_qqq_universe() -> dict[str, Any]:
    if not QQQ_PROFILE.exists():
        raise FileNotFoundError(
            f"missing recorded source {QQQ_PROFILE.relative_to(ROOT)} -- "
            "the taxonomy is only ever built from recorded real data"
        )
    payload = json.loads(QQQ_PROFILE.read_text(encoding="utf-8"))
    source = {
        "name": "Invesco QQQ Trust ETF profile (issuer-disclosed holdings and sector weights)",
        "url": "https://www.alphavantage.co/documentation/#etf-profile",
        "as_of": payload.get("retrieved_at", "2026-08-06"),
        "snapshot": str(QQQ_PROFILE.relative_to(ROOT)),
    }

    sic_facts, crosswalk = _load_classification()

    sectors = []
    for entry in payload["sectors"]:
        label = entry["sector"]
        sectors.append(
            {
                "id": _slug(label),
                "label": label,
                "universe": "qqq",
                "disclosed_weight": float(entry["weight"]),
                "source": source,
            }
        )

    companies = []
    for entry in payload["holdings"]:
        symbol = (entry.get("symbol") or "").strip()
        description = (entry.get("description") or "").strip()
        non_operating = _classify_non_operating(description)
        # Alpha Vantage returns "n/a" for positions it cannot resolve to a
        # listed symbol. Those are real disclosed positions but cannot be
        # keyed on a ticker, so they are recorded and flagged rather than
        # dropped or assigned an invented symbol.
        unresolved_symbol = symbol in {"", "n/a", "N/A"}
        sector_id = sector_source = None
        sic_code = sic_description = None
        sic_meta = sic_facts.get(symbol) if not unresolved_symbol else None
        if sic_meta:
            sic_code = sic_meta.get("sic")
            sic_description = sic_meta.get("sic_description")
            override = (crosswalk.get("ambiguous_sic_overrides") or {}).get(symbol)
            if override:
                sector_id = override["bucket"]
                sector_source = (
                    f"SEC EDGAR SIC {sic_code} ({sic_description}) per "
                    f"{SIC_SNAPSHOT.relative_to(ROOT)}, bucket via per-company "
                    f"override in {SIC_CROSSWALK.relative_to(ROOT)}: "
                    f"{override['rationale']}"
                )
            elif sic_code in (crosswalk.get("sic_to_bucket") or {}):
                sector_id = crosswalk["sic_to_bucket"][sic_code]
                sector_source = (
                    f"SEC EDGAR SIC {sic_code} ({sic_description}) per "
                    f"{SIC_SNAPSHOT.relative_to(ROOT)}, mapped by "
                    f"{SIC_CROSSWALK.relative_to(ROOT)}"
                )
        companies.append(
            {
                "symbol": None if unresolved_symbol else symbol,
                "name": None if description in {"", "n/a", "N/A"} else description,
                "name_sec": (sic_meta or {}).get("name"),
                "cik": (sic_meta or {}).get("cik"),
                "memberships": [{"universe": "qqq", "weight": float(entry["weight"])}],
                "sector_id": sector_id,
                "sector_source": sector_source,
                "sic": sic_code,
                "sic_description": sic_description,
                "modelable": not (non_operating or unresolved_symbol),
                "not_modelable_reason": non_operating
                or ("unresolved_symbol" if unresolved_symbol else None),
            }
        )

    universe = {
        "id": "qqq",
        "name": "Invesco QQQ Trust, Series 1",
        "ticker": "QQQ",
        "benchmark": "NASDAQ-100 Index",
        "source": source,
        "disclosed_constituent_count": len(companies),
        "sector_scheme": "issuer-disclosed sector buckets (not a licensed GICS mapping)",
        "linked_public_case": "etf-public-qqq-2026",
    }
    return {"universe": universe, "sectors": sectors, "companies": companies}


def build() -> dict[str, Any]:
    qqq = build_qqq_universe()

    return {
        "schema_version": "1.0",
        "as_of": "2026-08-06",
        "generated_by": "tools/build_universe_taxonomy.py",
        "purpose": (
            "Structured domain -> sector -> company backlog. Every company traces "
            "to a recorded, dated disclosure. Sector assignment per company is "
            "deliberately empty until a real classification source is attached."
        ),
        "universes": [qqq["universe"]],
        "sectors": qqq["sectors"],
        "companies": sorted(
            qqq["companies"], key=lambda item: (item["symbol"] is None, item["symbol"] or "")
        ),
        # Which model archetypes are in scope for which sectors. This is a
        # coverage *decision* we are making, not a claim about the world, so
        # it is labelled as such and starts empty -- populating it is a
        # deliberate scoping act, not something to autofill.
        "domain_sector_scope": [],
        "scope_note": (
            "domain_sector_scope records which domains we intend to cover for "
            "which sectors. It is a modeling-scope decision, not a sourced fact, "
            "and every entry must carry a rationale."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    taxonomy = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(taxonomy, indent=2) + "\n", encoding="utf-8")

    modelable = [item for item in taxonomy["companies"] if item["modelable"]]
    print(f"saved {args.output.relative_to(ROOT)}")
    print(
        f"universes={len(taxonomy['universes'])} "
        f"sectors={len(taxonomy['sectors'])} "
        f"companies={len(taxonomy['companies'])} "
        f"modelable={len(modelable)} "
        f"sector-mapped={sum(1 for item in taxonomy['companies'] if item['sector_id'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
