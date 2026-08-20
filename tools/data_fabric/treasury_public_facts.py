"""L2 data fabric: pull U.S. Treasury daily par yield / bill / real (TIPS)
curves and emit structured facts + provenance.

Uses the same public CSV export home.treasury.gov's own "Daily Treasury Par
Yield Curve Rates" chart page serves (no API key, no auth) -- this repo's
existing Fixed Income domain (21) cases (rates-treasury-2025-12-01,
rates-treasury-2022-shock) already cite this exact page as their source but
captured it by hand. This script makes that fetch reproducible.

Treasury's REST API at api.fiscaldata.treasury.gov does not carry this
dataset (checked: no `daily_treasury_*` table exists under its `accounting/od`
group as of this writing); the CSV export under home.treasury.gov is the
correct, official, machine-readable form of the same published chart.

Rules (repo policy):
- Public data only.
- Every fact lands with as-of, retrieval date, transformation, and snapshot pointer.
- Domain builders remain the calculation engine; this layer only supplies inputs.

Examples:
  python tools/data_fabric/treasury_public_facts.py --year 2026
  python tools/data_fabric/treasury_public_facts.py --year 2026 --type daily_treasury_bill_rates
  python tools/data_fabric/treasury_public_facts.py --year 2026 --as-of 2026-08-17
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "tools" / "data_fabric" / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv"

# Treasury's own dataset identifiers, one CSV schema each. Column headers are
# read from the CSV itself (not hardcoded) so this script tracks whatever
# tenors Treasury is currently publishing without needing an update.
DATASET_LABELS = {
    "daily_treasury_yield_curve": "Daily Treasury Par Yield Curve Rates",
    "daily_treasury_bill_rates": "Daily Treasury Bill Rates",
    "daily_treasury_long_term_rate": "Daily Treasury Long-Term Rates",
    "daily_treasury_real_yield_curve": "Daily Treasury Par Real Yield Curve Rates (TIPS)",
    "daily_treasury_real_long_term": "Daily Treasury Real Long-Term Rates (TIPS)",
}

CHART_PAGE_URL = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type={type}&field_tdr_date_value={year}"


def fetch_csv(year: int, dataset_type: str) -> str:
    """Fetch the raw CSV. Uses curl, not `requests`: this repo's existing
    tools/resolve_from_fred.py already documented that FRED's edge rejects
    Python's HTTP stack at the TLS layer while curl passes; home.treasury.gov
    is served by the same class of edge (Akamai) and the same workaround
    applies, plus curl ships everywhere this repo's CI runs."""
    url = f"{BASE_URL}/{year}/all?type={dataset_type}&field_tdr_date_value={year}&page&_format=csv"
    fetched = subprocess.run(
        ["curl", "-sSg", "-m", "30", url],
        capture_output=True, text=True, check=True,
    )
    if not fetched.stdout.strip():
        raise SystemExit(f"empty response fetching {dataset_type} for {year} from {url}")
    return fetched.stdout


def parse_curve(csv_text: str) -> list[dict[str, Any]]:
    """One row per published date; tenor columns as filed, MM/DD/YYYY -> ISO."""
    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames is None:
        raise SystemExit("no header row in Treasury CSV response")
    tenor_cols = [c for c in reader.fieldnames if c != "Date"]
    rows: list[dict[str, Any]] = []
    for raw in reader:
        raw_date = raw.get("Date", "").strip()
        if not raw_date:
            continue
        month, day, year_s = raw_date.split("/")
        iso_date = f"{year_s}-{int(month):02d}-{int(day):02d}"
        tenors: dict[str, float | None] = {}
        for col in tenor_cols:
            v = (raw.get(col) or "").strip()
            tenors[col] = float(v) if v not in ("", "N/A") else None
        rows.append({"date": iso_date, "tenors": tenors})
    rows.sort(key=lambda r: r["date"])
    return rows


def write_outputs(
    dataset_type: str,
    year: int,
    rows: list[dict[str, Any]],
    as_of: str | None,
) -> tuple[Path, Path]:
    today = date.today().isoformat()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    label = DATASET_LABELS.get(dataset_type, dataset_type)
    slug = f"treasury_{dataset_type}_{year}"

    if as_of:
        selected = next((r for r in rows if r["date"] == as_of), None)
        if selected is None:
            available = ", ".join(r["date"] for r in rows[-5:])
            raise SystemExit(f"no {label} row for {as_of}; most recent available: {available}")
        payload_rows = [selected]
    else:
        payload_rows = rows

    payload = {
        "dataset": dataset_type,
        "dataset_label": label,
        "year": year,
        "retrieved_utc": stamp,
        "rows": payload_rows,
        "row_count": len(payload_rows),
    }

    facts_path = OUT_DIR / f"{slug}.json"
    (OUT_DIR / f"{slug}_{stamp}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    facts_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    reg_path = OUT_DIR / f"{slug}_source_register.csv"
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
        for row in payload_rows:
            w.writerow(
                {
                    "source_name": "U.S. Department of the Treasury, Daily Treasury Rates",
                    "document_or_dataset": label,
                    "publication_date": row["date"],
                    "as_of_date": row["date"],
                    "retrieval_date": today,
                    "unit_currency": "percent (annualized, par yield or discount basis per Treasury convention)",
                    "transformation": "as-published CSV export, no interpolation or adjustment",
                    "workbook_destination": "Fixed Income / Rates; discount curves in Options, Project Finance",
                    "license_or_restriction": "U.S. government public data; no restriction",
                    "checksum_or_snapshot": str(facts_path.relative_to(ROOT)),
                }
            )

    print(f"Wrote {facts_path}")
    print(f"Wrote {reg_path}")
    print(f"Rows: {len(payload_rows)}")
    print(f"Chart page: {CHART_PAGE_URL.format(type=dataset_type, year=year)}")
    return facts_path, reg_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--year", type=int, default=date.today().year)
    parser.add_argument("--type", dest="dataset_type", default="daily_treasury_yield_curve",
                        choices=sorted(DATASET_LABELS))
    parser.add_argument("--as-of", default=None, help="ISO date (YYYY-MM-DD); default emits the full year")
    args = parser.parse_args()

    csv_text = fetch_csv(args.year, args.dataset_type)
    rows = parse_curve(csv_text)
    if not rows:
        raise SystemExit(f"parsed zero rows for {args.dataset_type} {args.year}")
    write_outputs(args.dataset_type, args.year, rows, args.as_of)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
