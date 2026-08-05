"""L2 data fabric skeleton: FCA (UK Financial Conduct Authority) open / published data.

The FCA publishes a range of regulatory and market datasets useful for
Public Finance, Debt, Structured Finance, Microfinance, Fintech, Insurance,
and UK-listed credit / equity work:

- Product Sales Data (PSD) aggregates (mortgages, retail investments, pure protection)
- FIRDS – Financial Instruments Reference Data System
- FITRS – transparency calculations (equity focus under current regime)
- STS securitisation notifications
- Public Ratings Database (CRA)
- National Storage Mechanism (NSM) regulated disclosures
- Emerging daily UK equity market-activity summaries (from 2026)

This module is a skeleton + provenance helper:
- It does not claim live API access to every feed (many are file downloads or
  interactive tables).
- It records structured aggregates or reference rows with full source_register
  provenance once a maintainer has obtained the public files.
- Prefer official FCA publication pages over third-party mirrors.

Key public entry points (2026):
  https://www.fca.org.uk/data/product-sales-data
  https://www.fca.org.uk/markets/transaction-reporting/instrument-reference-data
  https://data.fca.org.uk/ (Publishing Hub)
  NSM investor guide and FIRDS/FITRS technical specs on fca.org.uk
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "tools" / "data_fabric" / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FCA_PSD_HOME = "https://www.fca.org.uk/data/product-sales-data"
FCA_FIRDS_HOME = "https://www.fca.org.uk/markets/transaction-reporting/instrument-reference-data"
FCA_DATA_HUB = "https://data.fca.org.uk/"


def record_dataset_snapshot(
    dataset_id: str,
    as_of: str,
    records: list[dict[str, Any]] | dict[str, Any],
    document_title: str,
    publication_date: str | None = None,
    source_url: str | None = None,
    unit_currency: str = "GBP",
    transformation: str = "Aggregated public FCA release; no model adjustment",
    workbook_destination: str = "Assumptions / sector benchmarks (Public Finance, Credit, Structured, Microfinance, Fintech)",
) -> tuple[Path, Path]:
    """
    Write a governed snapshot + source_register fragment for an FCA public dataset.

    dataset_id examples: "psd_mortgage_2024", "firds_delta_YYYYMMDD", "sts_notifications"
    records: either a list of row dicts or a summary metrics dict.
    """
    today = date.today().isoformat()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_id = dataset_id.replace(" ", "_").replace("/", "-")
    facts_path = OUT_DIR / f"FCA_{safe_id}_{as_of.replace('-', '')}_facts.json"
    reg_path = OUT_DIR / f"FCA_{safe_id}_{as_of.replace('-', '')}_source_register.csv"

    payload = {
        "publisher": "Financial Conduct Authority (UK)",
        "dataset_id": dataset_id,
        "as_of": as_of,
        "retrieved_utc": stamp,
        "document_title": document_title,
        "publication_date": publication_date or as_of,
        "source_url": source_url or FCA_DATA_HUB,
        "records_or_metrics": records,
        "license_note": "Public FCA data; see Open Government Licence / FCA terms where applicable",
    }

    (OUT_DIR / f"FCA_{safe_id}_{as_of.replace('-', '')}_{stamp}_facts.json").write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8"
    )
    facts_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    # Flatten for register: one row per top-level metric or a summary row
    if isinstance(records, dict):
        items = list(records.items())
    else:
        items = [(f"row_{i}", r) for i, r in enumerate(records[:20])]  # cap for register size

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
        if not items:
            w.writerow(
                {
                    "source_name": "FCA open / published data",
                    "document_or_dataset": document_title,
                    "publication_date": publication_date or as_of,
                    "as_of_date": as_of,
                    "retrieval_date": today,
                    "unit_currency": unit_currency,
                    "transformation": transformation,
                    "workbook_destination": workbook_destination,
                    "license_or_restriction": "Public FCA data; Open Government Licence / FCA terms",
                    "checksum_or_snapshot": str(facts_path.relative_to(ROOT)),
                }
            )
        else:
            for key, _val in items:
                w.writerow(
                    {
                        "source_name": "FCA open / published data",
                        "document_or_dataset": f"{document_title} — {key}",
                        "publication_date": publication_date or as_of,
                        "as_of_date": as_of,
                        "retrieval_date": today,
                        "unit_currency": unit_currency,
                        "transformation": transformation,
                        "workbook_destination": workbook_destination,
                        "license_or_restriction": "Public FCA data; Open Government Licence / FCA terms",
                        "checksum_or_snapshot": str(facts_path.relative_to(ROOT)),
                    }
                )

    print(f"Wrote {facts_path}")
    print(f"Wrote {reg_path}")
    return facts_path, reg_path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--demo",
        action="store_true",
        help="Emit an illustrative PSD-style provenance template (not live aggregates)",
    )
    args = ap.parse_args()

    if args.demo:
        record_dataset_snapshot(
            dataset_id="psd_mortgage_illustrative",
            as_of="2024-12-31",
            records={
                "reporting_firms": None,  # fill from published PSD tables
                "total_mortgage_sales_value_gbp_bn": None,
                "geographic_coverage_note": "UK nations + 9 English regions (ONSPD)",
            },
            document_title="FCA Product Sales Data – Mortgages (illustrative template)",
            publication_date="2025-09-30",
            source_url=FCA_PSD_HOME,
        )
        print("Demo FCA provenance written. Replace None / placeholders with published figures.")
        return 0

    print(__doc__)
    print("\nPrimary public pages:")
    print(f"  PSD:   {FCA_PSD_HOME}")
    print(f"  FIRDS: {FCA_FIRDS_HOME}")
    print(f"  Hub:   {FCA_DATA_HUB}")
    print("\nUsage:")
    print("  from tools.data_fabric.fca_open_data import record_dataset_snapshot")
    print("  record_dataset_snapshot(dataset_id=..., as_of=..., records=..., document_title=...)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
