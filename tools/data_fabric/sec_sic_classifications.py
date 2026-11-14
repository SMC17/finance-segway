"""Harvest SEC SIC classifications for a universe's constituents.

Regenerates tools/data_fabric/out/QQQ_sec_sic_classifications.json - the
frozen snapshot the universe taxonomy's sector assignment cites. Reads the
committed QQQ ETF-profile snapshot for the constituent list, resolves each
ticker to a CIK via SEC's company_tickers.json (with explicit overrides for
issuers that file with the SEC but are absent from that map - AEP), then
pulls each issuer's SIC code and description from the submissions API.

Same repo rules as edgar_company_facts.py: public data only, every fact
lands dated, and the SEC fair-access User-Agent applies. data.sec.gov is
proxy-blocked in the agent sandbox, so this runs from an unrestricted
environment; the committed snapshot is the record either way.

Usage:
    python tools/data_fabric/sec_sic_classifications.py [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import json
import time
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "tools" / "data_fabric" / "out"
PROFILE = OUT_DIR / "QQQ_alphavantage_etf_profile.json"
SNAPSHOT = OUT_DIR / "QQQ_sec_sic_classifications.json"

# SEC requires a real contact: export SEC_USER_AGENT="Name/1.0 (you@example.org)"
UA = os.environ.get("SEC_USER_AGENT", "FinanceSegway/1.0 (research; set SEC_USER_AGENT)")

# SEC-registered issuers missing from company_tickers.json, keyed by ticker.
# Tickers SEC's company_tickers.json no longer carries. EA and WBD were QQQ
# constituents in the 2026-08-06 universe snapshot, then completed
# acquisitions and delisted: EA filed an 8-K (Item 2.01) and Form 25-NSE on
# 2026-08-04, WBD on 2026-10-06. Their CIKs still resolve on EDGAR.
CIK_OVERRIDES = {"AEP": "0000004904", "EA": "0000712515", "WBD": "0001437107"}


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept": "application/json"})
    return session


def harvest(dry_run: bool = False) -> dict:
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    symbols = sorted(
        {h["symbol"] for h in profile["holdings"]
         if h.get("symbol") and h["symbol"] not in {"n/a", "N/A"}}
    )
    session = _session()
    response = session.get(
        "https://www.sec.gov/files/company_tickers.json", timeout=60
    )
    response.raise_for_status()
    tickers = response.json()
    cik_by_ticker = {
        str(v["ticker"]).upper(): str(v["cik_str"]).zfill(10)
        for v in tickers.values()
    }
    cik_by_ticker.update(CIK_OVERRIDES)

    companies: dict[str, dict] = {}
    missing: list[str] = []
    for symbol in symbols:
        cik = cik_by_ticker.get(symbol) or cik_by_ticker.get(symbol.replace(".", "-"))
        if not cik:
            missing.append(symbol)
            continue
        response = session.get(
            f"https://data.sec.gov/submissions/CIK{cik}.json", timeout=60
        )
        response.raise_for_status()
        data = response.json()
        companies[symbol] = {
            "cik": cik,
            "name": data.get("name"),
            "sic": data.get("sic"),
            "sic_description": data.get("sicDescription"),
        }
        time.sleep(0.13)  # SEC fair-access pacing

    if missing:
        raise SystemExit(
            f"unresolvable tickers {sorted(missing)} - a truncated snapshot "
            "must never be written silently; add CIK_OVERRIDES entries or "
            "investigate before regenerating"
        )
    snapshot = {
        "source": "SEC EDGAR submissions API (data.sec.gov/submissions/CIK##########.json)",
        "retrieved_at": date.today().isoformat(),
        "retrieved_for": "standards/universe taxonomy sector classification",
        "note": (
            "Per-company SIC code and description as filed with the SEC. "
            "CIK overrides cover issuers absent from SEC's ticker map "
            f"({', '.join(sorted(CIK_OVERRIDES))}). The harvest refuses to "
            "write if any constituent is unresolvable."
        ),
        "companies": companies,
    }
    if not dry_run:
        SNAPSHOT.write_text(json.dumps(snapshot, indent=1) + "\n", encoding="utf-8")
        print(f"Wrote {SNAPSHOT} ({len(companies)} companies, {len(missing)} unresolved)")
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="fetch and report without writing the snapshot")
    args = parser.parse_args()
    harvest(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
