"""Daily SEC EDGAR ingest: record one day's filings and refresh what they touch.

Each run does three things, all from public SEC data:

  1. Pulls the EDGAR daily master index for one business day and writes a
     filing log to ``tools/data_fabric/out/edgar_daily/<year>/<date>.json``:
     counts by form, every filing by a tracked company, and every filing of a
     form that changes corporate lineage (Form 15, Form 25, Form 425, merger
     proxies, tender offers, Form 10).
  2. Re-pulls XBRL company facts for each tracked company that filed a
     periodic report (10-K, 10-Q, 20-F, 40-F, or an amendment) that day,
     through ``edgar_company_facts.py`` with the same flags the reviewed
     refresh driver uses. "Tracked" means a company already in the corpus
     under ``tools/data_fabric/out/``.
  3. Lists the public cases whose subject company filed that day.

It never rewrites a case. Every public case is pinned to a historical as-of
date, and feeding it a later filing would be hindsight. The case list tells a
reviewer which cases a new filing bears on; promoting a case is a reviewed
change, per tools/quarterly_refresh.py.

Usage:
    python tools/sec_daily_ingest.py                    # previous business day
    python tools/sec_daily_ingest.py --date 2026-11-13
    python tools/sec_daily_ingest.py --date 2026-11-13 --no-facts
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tools" / "data_fabric" / "out"
DAILY = CORPUS / "edgar_daily"
CASE_INDEX = ROOT / "standards" / "public_cases" / "index.json"

PERIODIC = {"10-K", "10-Q", "20-F", "40-F", "10-K/A", "10-Q/A", "20-F/A", "40-F/A", "10-KT"}
LINEAGE_FORMS = {
    "15-12B", "15-12G", "15-15D", "25", "25-NSE", "425", "DEFM14A", "PREM14A",
    "DEFM14C", "SC TO-T", "SC 14D9", "10-12B", "10-12G",
}
# The flags tools/refresh_data_layer.py passes for its facts step.
FACTS_FLAGS = ["--prefer-annual", "--annual-series"]


def previous_business_day(today: date) -> date:
    day = today - timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


def daily_index_url(day: date) -> str:
    qtr = (day.month - 1) // 3 + 1
    return f"https://www.sec.gov/Archives/edgar/daily-index/{day.year}/QTR{qtr}/master.{day:%Y%m%d}.idx"


def fetch_daily_index(day: date, user_agent: str) -> list[dict[str, str]] | None:
    """Rows of the day's master index, or None when SEC published none (a holiday)."""
    url = daily_index_url(day)
    for attempt in range(1, 5):
        resp = requests.get(url, headers={"User-Agent": user_agent}, timeout=60)
        if resp.status_code in (403, 404):
            return None
        if resp.ok:
            break
        time.sleep(2 ** attempt)
    else:
        resp.raise_for_status()
    rows = []
    for line in resp.content.decode("latin-1").splitlines():
        parts = line.split("|")
        if len(parts) != 5 or not parts[0].isdigit():
            continue
        cik, name, form, filed, path = parts
        rows.append({
            "cik": cik.zfill(10),
            "name": name.strip(),
            "form": form.strip(),
            "filed": f"{filed[:4]}-{filed[4:6]}-{filed[6:8]}" if len(filed) == 8 else filed,
            "accession": path.rsplit("/", 1)[-1].removesuffix(".txt"),
        })
    return rows


def tracked_companies() -> dict[str, str]:
    """CIK -> ticker for every company with an annual series in the corpus."""
    tracked: dict[str, str] = {}
    for path in sorted(CORPUS.glob("*_facts_annual_series.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        cik, ticker = str(payload.get("cik", "")).zfill(10), payload.get("ticker")
        if cik.strip("0") and ticker:
            tracked.setdefault(cik, ticker)
    return tracked


def case_subjects() -> dict[str, list[dict[str, str]]]:
    """CIK -> public cases whose manifest cites that CIK."""
    index = json.loads(CASE_INDEX.read_text(encoding="utf-8"))
    pattern = re.compile(r"CIK[ =:#]*0*(\d{3,10})|edgar/data/0*(\d+)/")
    subjects: dict[str, list[dict[str, str]]] = {}
    for case in index.get("cases", []):
        text = (ROOT / case["manifest"]).read_text(encoding="utf-8")
        manifest = json.loads(text)
        as_of = manifest.get("as_of") or manifest.get("case", {}).get("as_of") or ""
        for match in pattern.findall(text):
            cik = next(x for x in match if x).zfill(10)
            entry = {"case_id": case["case_id"], "as_of": as_of}
            if entry not in subjects.setdefault(cik, []):
                subjects[cik].append(entry)
    return subjects


def refresh_facts(ticker: str, cik: str) -> dict[str, Any]:
    cmd = [sys.executable, "tools/data_fabric/edgar_company_facts.py", "--ticker", ticker, "--cik", cik.lstrip("0"), *FACTS_FLAGS]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {"ticker": ticker, "cik": cik, "ok": proc.returncode == 0, "detail": (proc.stderr or proc.stdout).strip()[-400:]}


def ingest(day: date, refresh: bool, user_agent: str) -> dict[str, Any]:
    rows = fetch_daily_index(day, user_agent)
    if rows is None:
        return {"date": day.isoformat(), "published": False}
    tracked = tracked_companies()
    subjects = case_subjects()

    tracked_rows = [dict(r, ticker=tracked[r["cik"]]) for r in rows if r["cik"] in tracked]
    lineage_rows = [r for r in rows if r["form"] in LINEAGE_FORMS]
    periodic = sorted({(r["ticker"], r["cik"]) for r in tracked_rows if r["form"] in PERIODIC})
    refreshed = [refresh_facts(t, c) for t, c in periodic] if refresh else []

    # A case is flagged only for filings that can change a model input:
    # periodic reports, 8-Ks, and lineage forms. Ownership filings (Forms 3,
    # 4, 144, 13G) index under the issuer too, but carry nothing a model reads.
    material = PERIODIC | LINEAGE_FORMS | {"8-K", "8-K/A", "6-K"}
    by_case: dict[str, dict[str, Any]] = {}
    for r in rows:
        if r["form"] not in material or r["cik"] not in subjects:
            continue
        for case in subjects[r["cik"]]:
            entry = by_case.setdefault(case["case_id"], {**case, "ciks": set(), "forms": set()})
            entry["ciks"].add(r["cik"])
            entry["forms"].add(r["form"])
    cases = [
        {**entry, "ciks": sorted(entry["ciks"]), "forms": sorted(entry["forms"]),
         "action": "none: the case is pinned to its as-of date, so a later filing is hindsight for it"}
        for _, entry in sorted(by_case.items())
    ]

    log = {
        "schema_version": "1.0",
        "generated_by": "tools/sec_daily_ingest.py",
        "date": day.isoformat(),
        "published": True,
        "source": daily_index_url(day),
        "filing_count": len(rows),
        "entity_count": len({r["cik"] for r in rows}),
        "form_counts": dict(Counter(r["form"] for r in rows).most_common()),
        "tracked_filings": tracked_rows,
        "lineage_filings": lineage_rows,
        "facts_refreshed": refreshed,
        "cases_with_new_filings": cases,
    }
    dest = DAILY / str(day.year) / f"{day.isoformat()}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(log, indent=1) + "\n", encoding="utf-8")
    log["path"] = str(dest.relative_to(ROOT))
    return log


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--date", type=date.fromisoformat, default=None)
    parser.add_argument("--no-facts", action="store_true", help="log filings only; do not re-pull company facts")
    args = parser.parse_args()
    user_agent = os.environ.get("SEC_USER_AGENT", "").strip()
    if not user_agent:
        raise SystemExit('SEC_USER_AGENT is not set; SEC requires "Name contact@example.org".')
    day = args.date or previous_business_day(date.today())
    log = ingest(day, not args.no_facts, user_agent)
    if not log["published"]:
        print(f"{day}: SEC published no daily index (weekend or federal holiday).")
        return 0
    failed = [r for r in log["facts_refreshed"] if not r["ok"]]
    print(f"{day}: {log['filing_count']:,} filings by {log['entity_count']:,} entities -> {log['path']}")
    print(f"  tracked-company filings: {len(log['tracked_filings'])}; lineage filings: {len(log['lineage_filings'])}")
    print(f"  facts refreshed: {len(log['facts_refreshed']) - len(failed)} ok, {len(failed)} failed")
    for case in log["cases_with_new_filings"]:
        print(f"  case {case['case_id']} (as of {case['as_of']}): subject appears on {', '.join(case['forms'])}")
    for r in failed:
        print(f"  FAILED {r['ticker']}: {r['detail']}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
