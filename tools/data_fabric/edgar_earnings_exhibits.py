"""Freeze earnings-release exhibits: the disclosure-only source class.

The software templates' highest-value drivers (ARR mechanics, NRR, guidance)
live in earnings materials - 8-K exhibits under Item 2.02 (Results of
Operations) - not in XBRL. This tool freezes those documents per ticker:
RAW and UNINTERPRETED, no extracted numbers, no parsing - zero fabrication
surface. Reading ARR out of a frozen exhibit is the modeling agent's job,
and its citation is the committed file plus its recorded SHA-256.

Per ticker: scan recent 8-K filings whose Item list contains 2.02, take the
latest N (default 2 - typically the newest quarter and the one before),
download every EX-99 exhibit document, and write:

  tools/data_fabric/exhibits/{TICKER}/{accession}/{original filename}
  tools/data_fabric/exhibits/{TICKER}/index.json   (accessions, dates,
      items, per-file sha256 and byte size - the citation surface)

Sector sweeps mirror the facts harvests: --sector / --all-sectors /
--skip-existing, with CIKs resolved offline from the SIC snapshot.

    python tools/data_fabric/edgar_earnings_exhibits.py --ticker DDOG
    python tools/data_fabric/edgar_earnings_exhibits.py --sector information_technology --skip-existing
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

from edgar_company_facts import UA, resolve_cik, sector_members

ROOT = Path(__file__).resolve().parents[2]
EXHIBITS_DIR = ROOT / "tools" / "data_fabric" / "exhibits"

RESULTS_ITEM = "2.02"
DOC_TYPE = re.compile(r"<TYPE>\s*(EX-99[^\s<]*)", re.IGNORECASE)
DOC_FILENAME = re.compile(r"<FILENAME>\s*([^\s<]+)", re.IGNORECASE)


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept": "*/*"})
    return session


def exhibit_documents(header_text: str) -> list[tuple[str, str]]:
    """(exhibit_type, filename) pairs from the filing's SGML header.

    Filenames are issuer-arbitrary (ADSK ships 'q127pressrelease.htm',
    CoreWeave 'coreweave1q26earningspress.htm'); the header's <TYPE> tag is
    the authoritative statement of which document is an EX-99 exhibit.
    """
    pairs = []
    # The -index-headers.html page HTML-escapes the underlying SGML
    # (&lt;TYPE&gt;), so unescape before matching tags.
    header_text = html.unescape(header_text)
    blocks = header_text.split("<DOCUMENT>")
    for block in blocks[1:]:
        type_match = DOC_TYPE.search(block)
        name_match = DOC_FILENAME.search(block)
        if type_match and name_match:
            pairs.append((type_match.group(1).upper(), name_match.group(1)))
    return pairs


def results_8ks(submissions: dict, limit: int) -> list[dict]:
    """Latest 8-K filings whose Item list includes 2.02, newest first."""
    recent = submissions["filings"]["recent"]
    out = []
    for form, accession, filed, items, report in zip(
        recent["form"], recent["accessionNumber"], recent["filingDate"],
        recent.get("items", [""] * len(recent["form"])),
        recent.get("reportDate", [""] * len(recent["form"])),
    ):
        if form != "8-K" or RESULTS_ITEM not in (items or ""):
            continue
        out.append(
            {"accession": accession, "filed": filed, "items": items,
             "report_date": report or None}
        )
        if len(out) >= limit:
            break
    return out


def harvest_ticker(ticker: str, cik: str | None, *, limit: int = 2,
                   session: requests.Session | None = None) -> dict:
    sess = session or _session()
    if not cik:
        cik = resolve_cik(ticker, sess)
    cik_padded = str(cik).zfill(10)
    subs = sess.get(
        f"https://data.sec.gov/submissions/CIK{cik_padded}.json", timeout=60
    )
    subs.raise_for_status()
    filings = results_8ks(subs.json(), limit)
    ticker_dir = EXHIBITS_DIR / ticker.upper()
    entries = []
    for filing in filings:
        acc = filing["accession"].replace("-", "")
        base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}"
        header = sess.get(f"{base}/{filing['accession']}-index-headers.html",
                          timeout=60)
        header.raise_for_status()
        documents = exhibit_documents(header.text)
        files = []
        for exhibit_type, name in documents:
            raw = sess.get(f"{base}/{name}", timeout=120)
            raw.raise_for_status()
            dest = ticker_dir / acc / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw.content)
            files.append(
                {
                    "name": name,
                    "exhibit_type": exhibit_type,
                    "url": f"{base}/{name}",
                    "sha256": hashlib.sha256(raw.content).hexdigest(),
                    "bytes": len(raw.content),
                }
            )
        if files:
            entries.append({**filing, "files": files})
    payload = {
        "ticker": ticker.upper(),
        "cik": cik_padded,
        "source": "SEC EDGAR 8-K filings, Item 2.02 (Results of Operations), EX-99 exhibits",
        "retrieved_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "note": (
            "Raw, uninterpreted earnings-release documents. No numbers are "
            "extracted here by design - a modeling agent reads the frozen "
            "file and cites it by path + sha256."
        ),
        "filings": entries,
    }
    ticker_dir.mkdir(parents=True, exist_ok=True)
    (ticker_dir / "index.json").write_text(
        json.dumps(payload, indent=1) + "\n", encoding="utf-8"
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticker")
    parser.add_argument("--cik")
    parser.add_argument("--sector")
    parser.add_argument("--all-sectors", action="store_true")
    parser.add_argument("--limit", type=int, default=2,
                        help="results-8-Ks to freeze per ticker (default 2)")
    parser.add_argument("--skip-existing", action="store_true",
                        help="resume: skip tickers whose exhibits index exists")
    args = parser.parse_args()
    if not (args.ticker or args.sector or args.all_sectors):
        parser.error("one of --ticker, --sector, or --all-sectors is required")
    sess = _session()
    if args.sector or args.all_sectors:
        failures = []
        for ticker, cik in sector_members(None if args.all_sectors else args.sector):
            if args.skip_existing and (EXHIBITS_DIR / ticker / "index.json").exists():
                continue
            try:
                payload = harvest_ticker(ticker, cik, limit=args.limit, session=sess)
                total = sum(len(f["files"]) for f in payload["filings"])
                print(f"{ticker}: {len(payload['filings'])} filings, {total} exhibits")
            except Exception as exc:  # noqa: BLE001 - one bad issuer must not kill the sweep
                failures.append(f"{ticker}: {exc}")
                print(f"FAILED {ticker}: {exc}")
        if failures:
            print(f"{len(failures)} failures: {failures}")
            return 1
        return 0
    payload = harvest_ticker(args.ticker, args.cik, limit=args.limit, session=sess)
    total = sum(len(f["files"]) for f in payload["filings"])
    print(f"{args.ticker.upper()}: {len(payload['filings'])} filings, {total} exhibits frozen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
