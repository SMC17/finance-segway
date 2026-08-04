\"\"\"L2 seed: pull SEC company facts (XBRL) and write provenance rows.

Uses the public SEC companyfacts API. Output is structured facts + a
source_register-compatible CSV fragment that IB / PE / Credit instances
can attach.

Example:
  python tools/data_fabric/edgar_company_facts.py --ticker ARCC --cik 1287750
  python tools/data_fabric/edgar_company_facts.py --ticker HD --cik 354950

SEC requires a descriptive User-Agent with contact.
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

# SEC fair-access: identify application + contact email
UA = "FinanceSegway/1.0 (research; seancollins2027@u.northwestern.edu)"


def fetch_company_facts(cik: str) -> dict:
    cik_padded = str(cik).zfill(10)
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json"
    r = requests.get(
        url,
        headers={"User-Agent": UA, "Accept-Encoding": "gzip, deflate"},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def extract_selected(facts: dict) -> list[dict]:
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
        "InterestExpense",
        "EarningsPerShareBasic",
        "DebtCurrent",
    ]
    rows = []
    for concept in wanted:
        node = usgaap.get(concept)
        if not node:
            continue
        units = node.get("units", {})
        series = (
            units.get("USD")
            or units.get("USD/shares")
            or (next(iter(units.values())) if units else [])
        )
        if not series:
            continue
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


def write_outputs(ticker: str, cik: str, rows: list[dict]) -> tuple[Path, Path]:
    today = date.today().isoformat()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    facts_path = OUT_DIR / f"{ticker.upper()}_facts_selected.json"
    reg_path = OUT_DIR / f"{ticker.upper()}_source_register.csv"
    # also timestamped copy
    (OUT_DIR / f"{ticker.upper()}_{cik}_{stamp}_selected.json").write_text(
        json.dumps(rows, indent=2), encoding="utf-8"
    )

    facts_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    with reg_path.open("w", newline="", encoding="utf-8") as f:
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
                    "transformation": "latest USD (or USD/shares) fact by end date",
                    "workbook_destination": "Assumptions / historicals (IB, PE, Credit)",
                    "license_or_restriction": "Public SEC data; see SEC terms of use",
                    "checksum_or_snapshot": str(facts_path.relative_to(ROOT)),
                }
            )

    print(f"Wrote {facts_path}")
    print(f"Wrote {reg_path}")
    print(f"Selected concepts: {len(rows)}")
    return facts_path, reg_path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--cik", required=True, help="SEC CIK (leading zeros optional)")
    args = ap.parse_args()

    facts = fetch_company_facts(args.cik)
    rows = extract_selected(facts)
    write_outputs(args.ticker, args.cik, rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
