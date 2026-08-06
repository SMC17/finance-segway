"""L2 data fabric: pull SEC companyfacts (XBRL) and emit structured facts + provenance.

Uses the public SEC companyfacts API and optional company_tickers.json for
ticker→CIK resolution. Output is selected US-GAAP (and a few DEI) facts plus a
source_register-compatible CSV fragment that domain instances can attach.

Rules (repo policy):
- Public data only.
- Every fact lands with as-of, retrieval date, transformation, and snapshot pointer.
- Domain builders remain the calculation engine; this layer only supplies inputs.

Examples:
  python tools/data_fabric/edgar_company_facts.py --ticker AAPL
  python tools/data_fabric/edgar_company_facts.py --ticker ARCC --cik 1287750
  python tools/data_fabric/edgar_company_facts.py --ticker MSFT --prefer-annual
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "tools" / "data_fabric" / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# SEC fair-access: identify application + contact
UA = "FinanceSegway/1.0 (research; seancollins2027@u.northwestern.edu)"

# Expanded but still conservative concept list. Prefer items that appear
# consistently across large-cap and financial issuers. Domain-specific
# expansions can be passed via --extra-concepts.
DEFAULT_CONCEPTS = [
    # Balance sheet core
    "Assets",
    "AssetsCurrent",
    "Liabilities",
    "LiabilitiesCurrent",
    "StockholdersEquity",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    "LongTermDebt",
    "LongTermDebtNoncurrent",
    "LongTermDebtCurrent",
    "DebtCurrent",
    "ShortTermBorrowings",
    "CommercialPaper",
    # Income / performance
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "NetIncomeLoss",
    "OperatingIncomeLoss",
    "GrossProfit",
    "InterestExpense",
    "InterestExpenseDebt",
    "IncomeTaxExpenseBenefit",
    "EarningsPerShareBasic",
    "EarningsPerShareDiluted",
    # Cash flow / coverage relevant
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInInvestingActivities",
    "NetCashProvidedByUsedInFinancingActivities",
    "DepreciationDepletionAndAmortization",
    "PaymentsToAcquirePropertyPlantAndEquipment",
    # Capital structure / shares
    "CommonStockSharesOutstanding",
    "CommonStockSharesIssued",
    "WeightedAverageNumberOfSharesOutstandingBasic",
]


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json",
        }
    )
    return s


def resolve_cik(ticker: str, session: requests.Session | None = None) -> str:
    """Resolve ticker → zero-padded CIK via SEC company_tickers.json."""
    sess = session or _session()
    url = "https://www.sec.gov/files/company_tickers.json"
    r = sess.get(url, timeout=60)
    r.raise_for_status()
    data = r.json()
    t = ticker.upper().strip()
    for entry in data.values():
        if str(entry.get("ticker", "")).upper() == t:
            return str(entry["cik_str"]).zfill(10)
    raise ValueError(f"Ticker {ticker!r} not found in SEC company_tickers.json")


def fetch_company_facts(cik: str, session: requests.Session | None = None) -> dict:
    sess = session or _session()
    cik_padded = str(cik).zfill(10)
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json"
    r = sess.get(url, timeout=60)
    r.raise_for_status()
    return r.json()


def _pick_series(node: dict) -> list[dict]:
    units = node.get("units", {})
    # Prefer USD, then USD/shares, then any
    for key in ("USD", "USD/shares", "pure", "shares"):
        if key in units and units[key]:
            return units[key]
    if units:
        return next(iter(units.values()))
    return []


def extract_selected(
    facts: dict,
    concepts: list[str],
    prefer_annual: bool = False,
) -> list[dict]:
    """Extract latest (or preferred-form) values for each concept."""
    usgaap = facts.get("facts", {}).get("us-gaap", {})
    dei = facts.get("facts", {}).get("dei", {})
    rows: list[dict] = []

    for concept in concepts:
        node = usgaap.get(concept) or dei.get(concept)
        if not node:
            continue
        series = _pick_series(node)
        if not series:
            continue

        if prefer_annual:
            annual = [x for x in series if x.get("form") in ("10-K", "20-F", "40-F")]
            candidates = annual or series
        else:
            candidates = series

        # Prefer most recent end date; break ties by filed date
        latest = max(
            candidates,
            key=lambda x: (x.get("end") or "", x.get("filed") or ""),
        )
        rows.append(
            {
                "concept": concept,
                "value": latest.get("val"),
                "end": latest.get("end"),
                "filed": latest.get("filed"),
                "form": latest.get("form"),
                "fy": latest.get("fy"),
                "fp": latest.get("fp"),
                "frame": latest.get("frame"),
            }
        )
    return rows


def extract_annual_series(facts: dict, concepts: list[str]) -> list[dict]:
    """Full annual history per concept from annual filings (10-K/20-F/40-F,
    amendments included), deduped to one observation per fiscal PERIOD END,
    latest-filed value winning (restatements win, including 10-K/A).

    Discriminating annual facts is subtler than it looks; each rule below is
    the scar of a reproduced failure mode:
    - Form matches by PREFIX so amendment restatements are not dropped.
    - fp/fy fields describe the FILING, not the fact (every row in a 10-K
      carries fp=FY, including quarterly comparative frames), so they are
      useless as annual markers and deliberately unused.
    - A duration fact is annual when it spans >= 10 months. Dedupe keys on
      the full END DATE, never its calendar year: a fiscal-year-end change
      produces two distinct annual periods ending in the same calendar year
      and both must land. Same end date -> longer duration wins (a mistagged
      Q4 row loses to its full-year sibling), then latest filed.
    - Short periods are admitted only as TRANSITION STUBS: >= 5 months
      (quarterly frames are ~3) and not contained inside any kept annual
      period - a spin-off's 8-month first fiscal year survives while the
      quarterly comparatives inside every 10-K stay out.
    - Instant (balance-sheet) facts have no start; annual filings carry
      them at fiscal year ends, so they key by end date directly.
    """
    usgaap = facts.get("facts", {}).get("us-gaap", {})
    dei = facts.get("facts", {}).get("dei", {})
    annual_forms = ("10-K", "20-F", "40-F")

    def months(item: dict) -> int | None:
        start, end = item.get("start"), item.get("end")
        if not start or not end:
            return None
        return (int(end[:4]) - int(start[:4])) * 12 + (int(end[5:7]) - int(start[5:7]))

    def better(new: dict, kept: dict) -> bool:
        new_m, kept_m = months(new) or 0, months(kept) or 0
        if new_m != kept_m:
            return new_m > kept_m
        return (new.get("filed") or "") > (kept.get("filed") or "")

    rows: list[dict] = []
    for concept in concepts:
        node = usgaap.get(concept) or dei.get(concept)
        if not node:
            continue
        candidates = [
            item for item in _pick_series(node)
            if str(item.get("form") or "").startswith(annual_forms)
            and item.get("end") and item.get("val") is not None
        ]
        by_end: dict[str, dict] = {}
        shorts: list[dict] = []
        for item in candidates:
            duration = months(item)
            if duration is not None and duration < 10:
                shorts.append(item)
                continue
            kept = by_end.get(item["end"])
            if kept is None or better(item, kept):
                by_end[item["end"]] = item
        annual_spans = [
            (item.get("start"), item["end"])
            for item in by_end.values()
            if item.get("start")
        ]
        for item in shorts:
            duration = months(item) or 0
            if duration < 5:
                continue  # quarterly comparative frames
            contained = any(
                start <= item["start"] and item["end"] <= end
                for start, end in annual_spans
            )
            if contained or item["end"] in by_end:
                continue
            kept = by_end.get(item["end"])
            if kept is None or better(item, kept):
                by_end[item["end"]] = item
        if not by_end:
            continue
        rows.append(
            {
                "concept": concept,
                "observations": [
                    {
                        "end": item.get("end"),
                        "value": item.get("val"),
                        "filed": item.get("filed"),
                        "form": item.get("form"),
                        "fy": item.get("fy"),
                        "fp": item.get("fp"),
                    }
                    for _, item in sorted(by_end.items())
                ],
            }
        )
    return rows


def write_outputs(
    ticker: str,
    cik: str,
    rows: list[dict],
    extra_meta: dict[str, Any] | None = None,
) -> tuple[Path, Path]:
    today = date.today().isoformat()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    facts_path = OUT_DIR / f"{ticker.upper()}_facts_selected.json"
    reg_path = OUT_DIR / f"{ticker.upper()}_source_register.csv"

    payload = {
        "ticker": ticker.upper(),
        "cik": str(cik).zfill(10),
        "retrieved_utc": stamp,
        "concepts": rows,
    }
    if extra_meta:
        payload["meta"] = extra_meta

    # Timestamped archive + stable latest
    (OUT_DIR / f"{ticker.upper()}_{str(cik).zfill(10)}_{stamp}_selected.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    facts_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with reg_path.open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "source_name",
            "document_or_dataset",
            "publication_date",
            "as_of_date",
            "retrieval_date",
            "unit_currency",
            "transformation",
            "workbook_destination",
            "license_or_restriction",
            "checksum_or_snapshot",
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(
                {
                    "source_name": "SEC EDGAR companyfacts API",
                    "document_or_dataset": f"{ticker.upper()} {row['concept']} ({row.get('form') or 'n/a'})",
                    "publication_date": row.get("filed") or "",
                    "as_of_date": row.get("end") or "",
                    "retrieval_date": today,
                    "unit_currency": "USD",
                    "transformation": "latest USD (or USD/shares) fact by end date"
                    + (" (prefer 10-K/20-F)" if extra_meta and extra_meta.get("prefer_annual") else ""),
                    "workbook_destination": "Assumptions / historicals (IB, Corporate, PE, Credit, Equity, AM)",
                    "license_or_restriction": "Public SEC data; see SEC terms of use and fair-access policy",
                    "checksum_or_snapshot": str(facts_path.relative_to(ROOT)),
                }
            )

    print(f"Wrote {facts_path}")
    print(f"Wrote {reg_path}")
    print(f"Selected concepts: {len(rows)}")
    return facts_path, reg_path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker", required=True, help="Ticker symbol (e.g. AAPL, ARCC)")
    ap.add_argument(
        "--cik",
        default=None,
        help="SEC CIK (leading zeros optional). If omitted, resolved via company_tickers.json",
    )
    ap.add_argument(
        "--prefer-annual",
        action="store_true",
        help="Prefer 10-K / 20-F / 40-F facts when available",
    )
    ap.add_argument(
        "--extra-concepts",
        nargs="*",
        default=[],
        help="Additional us-gaap or dei concept names to extract",
    )
    ap.add_argument(
        "--annual-series",
        action="store_true",
        help="Also write {TICKER}_facts_annual_series.json: full annual "
             "history per concept, one value per fiscal end-year, latest "
             "filed wins",
    )
    args = ap.parse_args()

    sess = _session()
    cik = args.cik
    if not cik:
        cik = resolve_cik(args.ticker, sess)
        print(f"Resolved {args.ticker.upper()} → CIK {cik}")

    facts = fetch_company_facts(cik, sess)
    concepts = list(dict.fromkeys(DEFAULT_CONCEPTS + list(args.extra_concepts or [])))
    rows = extract_selected(facts, concepts, prefer_annual=args.prefer_annual)
    if args.annual_series:
        series_rows = extract_annual_series(facts, concepts)
        series_path = OUT_DIR / f"{args.ticker.upper()}_facts_annual_series.json"
        series_path.write_text(
            json.dumps(
                {
                    "ticker": args.ticker.upper(),
                    "cik": str(cik).zfill(10),
                    "retrieved_utc": datetime.now(timezone.utc).strftime(
                        "%Y%m%dT%H%M%SZ"
                    ),
                    "dedupe_rule": (
                        "annual filings (amendments included); one value per "
                        "fiscal period-end date; annual = >=10-month span, "
                        "transition stubs >=5 months admitted when not inside "
                        "an annual period; longer duration then latest filed "
                        "wins (restatements win)"
                    ),
                    "concepts": series_rows,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"Wrote {series_path} ({len(series_rows)} concepts with history)")
    write_outputs(
        args.ticker,
        cik,
        rows,
        extra_meta={"prefer_annual": args.prefer_annual, "concept_count_requested": len(concepts)},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
