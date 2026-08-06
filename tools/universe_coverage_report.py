"""The swarm's dispatch manifest: what data exists per universe company.

Joins the classified taxonomy (standards/universe/taxonomy.json) against the
data fabric's committed EDGAR artifacts and reports, per company: which
snapshots exist, how many concepts and fiscal years of history, the reported
currency, and named gaps. Read-only inventory - it declares no policy and
assigns no work; it exists so a backfill swarm (or a human) can query "what
is ready to model, and what is missing" instead of discovering coverage by
trial and error.

    python tools/universe_coverage_report.py                # full report (JSON)
    python tools/universe_coverage_report.py --sector X     # one sector
    python tools/universe_coverage_report.py --gaps-only    # just the holes
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAXONOMY = ROOT / "standards" / "universe" / "taxonomy.json"
OUT_DIR = ROOT / "tools" / "data_fabric" / "out"

CORE_CONCEPTS = ("Revenues", "NetIncomeLoss", "Assets")


def _series_summary(ticker: str) -> dict | None:
    path = OUT_DIR / f"{ticker}_facts_annual_series.json"
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    concepts = {c["concept"]: c for c in payload.get("concepts", [])}
    # An issuer can carry several revenue tags across eras (AAPL's legacy
    # us-gaap:Revenues died in 2017); coverage means the BEST series, so
    # take the variant with the most annual observations.
    revenue_variants = [
        concepts[key] for key in (
            "Revenues",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "RevenueFromContractWithCustomerIncludingAssessedTax",
        ) if key in concepts
    ]
    revenue = max(
        revenue_variants, key=lambda c: len(c["observations"]), default=None
    )
    units = sorted({c.get("unit") for c in concepts.values() if c.get("unit")})
    latest_end = max(
        (c["observations"][-1]["end"] for c in concepts.values() if c["observations"]),
        default=None,
    )
    return {
        "concepts": len(concepts),
        "revenue_years": len(revenue["observations"]) if revenue else 0,
        "latest_fiscal_end": latest_end,
        "units": units,
        "missing_core": [
            key for key in CORE_CONCEPTS
            if key not in concepts
            and not (key == "Revenues" and revenue is not None)
        ],
    }


def build_report(sector: str | None = None) -> dict:
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    companies = []
    gaps = []
    for company in taxonomy["companies"]:
        if not company.get("modelable"):
            continue
        if sector and company.get("sector_id") != sector:
            continue
        summary = _series_summary(company["symbol"])
        row = {
            "symbol": company["symbol"],
            "cik": company.get("cik"),
            "sector_id": company.get("sector_id"),
            "sic": company.get("sic"),
            "weight_qqq": company["memberships"][0]["weight"],
            "series": summary,
        }
        problems = []
        if summary is None:
            problems.append("no committed annual series - harvest this ticker")
        else:
            if summary["revenue_years"] == 0:
                problems.append(
                    "no annual revenue history (new filer with no annual "
                    "report yet, or an unmapped taxonomy tag)"
                )
            elif summary["revenue_years"] < 5:
                problems.append(f"thin history: {summary['revenue_years']} fiscal years")
            if summary["units"] and summary["units"] != ["USD"] and "USD" not in summary["units"]:
                problems.append(f"reports in {summary['units']} - do not mix with USD peers unconverted")
        row["gaps"] = problems
        companies.append(row)
        if problems:
            gaps.append({"symbol": company["symbol"], "gaps": problems})
    ready = [c for c in companies if not c["gaps"]]
    return {
        "as_of_taxonomy": taxonomy.get("as_of"),
        "scope": sector or "all-sectors",
        "companies_total": len(companies),
        "companies_ready": len(ready),
        "companies_with_gaps": len(gaps),
        "gaps": gaps,
        "companies": companies,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sector", help="restrict to one sector_id")
    parser.add_argument("--gaps-only", action="store_true",
                        help="print only the gap list")
    parser.add_argument("--report", type=Path, help="also write JSON here")
    args = parser.parse_args()
    report = build_report(args.sector)
    printable = report if not args.gaps_only else {
        key: report[key] for key in
        ("as_of_taxonomy", "scope", "companies_total", "companies_ready",
         "companies_with_gaps", "gaps")
    }
    print(json.dumps(printable, indent=2))
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
