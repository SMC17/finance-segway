\"\"\"L2 seed: pull SEC company facts (XBRL) and write provenance rows.

Uses the public SEC companyfacts API. Output is structured facts + a
source_register-compatible CSV fragment that IB / PE / Credit instances
can attach.

Example:
  python tools/data_fabric/edgar_company_facts.py --ticker AAPL --cik 0000320193

Note: SEC requires a descriptive User-Agent. Respect rate limits.
\"\"\"
from __future__ import annotations

import argparse
import csv
import json
from datetime import date, datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "tools" / "data_fabric" / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

UA = "Finance-Segway Research (github.com/SMC17/finance-segway; local-dev)"


def fetch_company_facts(cik: str) -> dict:
    cik_padded = cik.zfill(10)
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json"
    r = requests.get(url, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    return r.json()


def extract_selected(facts: dict) -> list[dict]:
    "\"\"Pull a small set of commonly needed US-GAAP facts (latest).\"\"\"
    usgaap = facts.get("facts", {}).get("us-gaap", {})
    wanted = [
        "Assets",
        "Liabilities",
        "StockholdersEquity",
        "Revenues",
        "NetIncomeLoss",
        "CashAndCashEquivalentsAtCarryingValue",
        "LongTermDebt",
        "LongTermDebtNoncurrent",
        "EarningsPerShareBasic",
    ]
    rows = []
    for concept in wanted:
        node = usgaap.get(concept)
        if not node:
            continue
        units = node.get("units", {})
        # prefer USD
        series = units.get("USD") or units.get("USD/shares") or next(iter(units.values()), [])
        if not series:
            continue
        # latest by end date
        latest = max(series, key=lambda x: x.get("end", ""))
        rows.append(
            {
                "concept": concept,
                "value": latest.get("val"),
                "end": latest.get("end"),
                "filed": latest.get("filed"),
                "form": latest.get("form"),
                "fy": latest.get("fy"),
                "fp": latest.get("fp"),
            }
        )
    return rows


def write_outputs(ticker: str, cik: str, facts: dict, rows: list[dict]) -> None:
    today = date.today().isoformat()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = OUT_DIR / f"{ticker.upper()}_{cik}_{stamp}"
    raw_path = Path(str(base) + "_companyfacts.json")
    facts_path = Path(str(base) + "_selected.json")
    reg_path = Path(str(base) + "_source_register.csv")

    raw_path.write_text(json.dumps(facts)[:2_000_000])  # cap size in stub
    facts_path.write_text(json.dumps(rows, indent=2))

    with reg_path.open("w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
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
            ],
        )
        w.writeheader()
        for row in rows:
            w.writerow(
                {
                    "source_name": "SEC EDGAR companyfacts API",
                    "document_or_dataset": f"{ticker} {row['concept']} ({row.get('form')})",
                    "publication_date": row.get("filed") or "",
                    "as_of_date": row.get("end") or "",
                    "retrieval_date": today,
                    "unit_currency": "USD",
                    "transformation": "latest USD fact by end date",
                    "workbook_destination": "Assumptions / historicals (IB, PE, Credit)",
                    "license_or_restriction": "Public SEC data; see SEC terms",
                    "checksum_or_snapshot": str(facts_path.relative_to(ROOT)),
                }
            )

    print(f"Wrote {facts_path}")
    print(f"Wrote {reg_path}")
    print(f"Selected concepts: {len(rows)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--cik", required=True, help="SEC CIK (number, leading zeros optional)")
    args = ap.parse_args()

    facts = fetch_company_facts(args.cik)
    rows = extract_selected(facts)
    write_outputs(args.ticker, args.cik, facts, rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
