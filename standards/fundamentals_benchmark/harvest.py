"""Harvest annual fundamentals (Assets / Revenues / NetIncome) for a
diversified large-cap panel from SEC EDGAR companyfacts, and distill to a
compact frozen snapshot for the fundamentals benchmark.

Fiscal labeling: each observation is keyed by the CALENDAR YEAR its fiscal
year ends in (Home Depot's FY ending 2024-01-28 -> 2024). Per fiscal year we
keep the latest-filed value (restatements win); every rung sees the same
series, so ladder comparisons stay fair. Values in $bn.
"""
import json
import os
import time
import urllib.request
from pathlib import Path

S = Path(__file__).resolve().parent
CACHE = S / "edgar_cache"
CACHE.mkdir(exist_ok=True)
# SEC's fair-access policy requires a User-Agent identifying the requester.
UA = {"User-Agent": os.environ.get(
    "EDGAR_UA", "finance-segway fundamentals-benchmark (set EDGAR_UA to your contact)")}

TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "ORCL", "CRM", "ADBE",
    "INTC", "IBM", "CSCO", "QCOM", "TXN",
    "JPM", "BAC", "WFC", "GS", "MS", "C", "BLK", "SCHW", "AXP", "ARCC",
    "JNJ", "UNH", "PFE", "MRK", "ABBV", "LLY", "TMO", "ABT", "BMY", "AMGN",
    "PG", "KO", "PEP", "WMT", "COST", "MCD", "NKE", "SBUX", "TGT", "HD",
    "LOW", "DIS",
    "XOM", "CVX", "CAT", "BA", "GE", "HON", "UNP", "UPS", "LMT", "DE", "MMM",
    "T", "VZ", "NEE", "DUK", "SO", "SPG", "O", "PLD",
]

REVENUE_TAGS = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                "SalesRevenueNet", "RevenuesNetOfInterestExpense",
                "InterestAndDividendIncomeOperating",
                "GrossInvestmentIncomeOperating"]
CONCEPTS = {"assets": ["Assets"], "revenue": REVENUE_TAGS,
            "net_income": ["NetIncomeLoss"]}


def fetch(url: str, dest: Path) -> dict:
    if dest.exists():
        return json.loads(dest.read_text())
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    dest.write_bytes(data)
    time.sleep(0.15)
    return json.loads(data)


def annual_series(gaap: dict, tags: list) -> dict:
    """Among candidate tags, keep the series with the most observations in
    the benchmark window (2014+; ties -> earlier tag wins). First-match lets
    a short modern series shadow a longer one; longest-overall lets a long
    RETIRED tag (dead since 2017) shadow the current one. Window coverage is
    what the benchmark actually consumes."""
    best: dict = {}
    best_cov = -1
    for tag in tags:
        units = gaap.get(tag, {}).get("units", {}).get("USD")
        if not units:
            continue
        by_year = {}
        for row in units:
            if row.get("form") != "10-K" or row.get("fp") != "FY":
                continue
            end, filed, val = row.get("end"), row.get("filed", ""), row.get("val")
            if not end or val is None:
                continue
            # annual duration only (>300 days) for flow concepts
            start = row.get("start")
            if start:
                y0, y1 = int(start[:4]), int(end[:4])
                m0, m1 = int(start[5:7]), int(end[5:7])
                if (y1 - y0) * 12 + (m1 - m0) < 10:
                    continue
            year = int(end[:4])
            if year not in by_year or filed > by_year[year][0]:
                by_year[year] = (filed, val)
        cov = sum(1 for y in by_year if y >= 2014)
        if len(by_year) >= 8 and cov > best_cov:
            best_cov = cov
            best = {str(y): round(v / 1e9, 3) for y, (_, v) in sorted(by_year.items())}
    return best


def main():
    tick_map = json.loads((CACHE / "company_tickers.json").read_text())
    cik = {v["ticker"]: str(v["cik_str"]).zfill(10) for v in tick_map.values()}
    panel = {}
    for t in TICKERS:
        if t not in cik:
            print(f"{t}: no CIK"); continue
        try:
            facts = fetch(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik[t]}.json",
                          CACHE / f"{t}.json")
        except Exception as e:
            print(f"{t}: fetch failed {e}"); continue
        gaap = facts.get("facts", {}).get("us-gaap", {})
        row = {m: annual_series(gaap, tags) for m, tags in CONCEPTS.items()}
        kept = {m: s for m, s in row.items() if s}
        if kept:
            panel[t] = kept
        print(f"{t}: " + ", ".join(f"{m}:{len(s)}y" for m, s in kept.items()))
    out = S / "fundamentals_panel.json"
    out.write_text(json.dumps(panel, indent=1) + "\n")
    print(f"\npanel: {len(panel)} companies -> {out} ({out.stat().st_size//1024}KB)")


if __name__ == "__main__":
    main()
