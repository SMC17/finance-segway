"""L2 data fabric skeleton: HarbourVest Global Private Equity (HVPE) public facts.

HVPE (LSE: HVPE / HVPD) is a listed private-equity fund-of-funds. Public
disclosures (monthly estimated NAV factsheets, annual reports, RNS) supply
usable inputs for PE, Merchant Banking, Fund-of-Funds, Asset Management and
look-through private-credit work without requiring LP statements.

This module is intentionally a *skeleton + provenance recorder*:
- It does not scrape paywalled or interactive content.
- It records structured public metrics (NAV, performance, portfolio composition
  when disclosed) with full source_register provenance.
- Callers or maintainers supply values obtained from the official public PDFs /
  RNS announcements (hvpe.com and LSE RNS).

Public entry points (as of 2026):
  https://www.hvpe.com/
  Monthly estimated NAV factsheets (typically released ~20 calendar days after month-end)
  Annual Report & Accounts
  LSE RNS for NAV, share transactions, etc.

Example workflow:
  1. Download latest monthly factsheet from hvpe.com
  2. Extract headline numbers (NAV/share, portfolio value, cash flow, etc.)
  3. Record via this helper so the domain source_register stays governed.
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

# Canonical public identifiers
HVPE_TICKER = "HVPE"
HVPE_NAME = "HarbourVest Global Private Equity Limited"
HVPE_HOME = "https://www.hvpe.com/"
HVPE_FAQ = "https://www.hvpe.com/company-info/hvpe-frequently-asked-questions/"


def record_public_snapshot(
    as_of: str,
    metrics: dict[str, Any],
    document_title: str,
    publication_date: str | None = None,
    source_url: str | None = None,
    notes: str | None = None,
) -> tuple[Path, Path]:
    """
    Write a governed snapshot + source_register fragment for an HVPE public disclosure.

    metrics example:
      {
        "nav_per_share_usd": 59.40,
        "nav_total_usd_m": 4200,
        "share_price_gbp": 34.50,
        "discount_to_nav_pct": 27.4,
        "portfolio_value_usd_m": 4356,
        "net_cash_flow_usd_m": 54,
        "commitments_outstanding_usd_m": ...,
        "buyout_pct": 62,
        "venture_growth_pct": 30,
        "private_credit_infra_pct": 8,
        ...
      }
    """
    today = date.today().isoformat()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_asof = as_of.replace("-", "")
    facts_path = OUT_DIR / f"HVPE_{safe_asof}_public_facts.json"
    reg_path = OUT_DIR / f"HVPE_{safe_asof}_source_register.csv"

    payload = {
        "entity": HVPE_NAME,
        "ticker": HVPE_TICKER,
        "as_of": as_of,
        "retrieved_utc": stamp,
        "document_title": document_title,
        "publication_date": publication_date or as_of,
        "source_url": source_url or HVPE_HOME,
        "notes": notes,
        "metrics": metrics,
        "license_note": "Public company disclosures; subject to HVPE / LSE terms of use",
    }

    # Timestamped archive + stable latest for this as-of
    (OUT_DIR / f"HVPE_{safe_asof}_{stamp}_public_facts.json").write_text(
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
        for key, val in metrics.items():
            w.writerow(
                {
                    "source_name": "HVPE public disclosure (LSE / hvpe.com)",
                    "document_or_dataset": f"{document_title} — {key}",
                    "publication_date": publication_date or as_of,
                    "as_of_date": as_of,
                    "retrieval_date": today,
                    "unit_currency": "USD" if "usd" in key.lower() or "nav" in key.lower() else "mixed",
                    "transformation": "Manual extraction from public PDF/RNS; no model adjustment",
                    "workbook_destination": "PE / Merchant Banking / FoF / AM Assumptions & look-through",
                    "license_or_restriction": "Public listed-company disclosure; see HVPE website and LSE terms",
                    "checksum_or_snapshot": str(facts_path.relative_to(ROOT)),
                }
            )

    print(f"Wrote {facts_path}")
    print(f"Wrote {reg_path}")
    print(f"Recorded {len(metrics)} metrics for HVPE as-of {as_of}")
    return facts_path, reg_path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--demo",
        action="store_true",
        help="Write a small illustrative provenance example (not live data)",
    )
    args = ap.parse_args()

    if args.demo:
        # Illustrative structure only — replace with real extracted numbers from
        # the latest public factsheet before attaching to any model instance.
        record_public_snapshot(
            as_of="2026-01-31",
            metrics={
                "nav_per_share_usd": None,  # fill from public factsheet
                "nav_total_usd_bn": None,
                "share_price_gbp": None,
                "discount_to_nav_pct": None,
                "net_portfolio_cash_flow_usd_m": None,
                "buyout_allocation_pct": None,
                "venture_growth_allocation_pct": None,
            },
            document_title="HVPE Monthly Estimated NAV / Annual Report (placeholder)",
            publication_date="2026-02-20",
            source_url=HVPE_HOME,
            notes="DEMO ONLY — replace None values with figures taken from the official public PDF/RNS before use in any workbook.",
        )
        print("Demo provenance written. Do not use placeholder metrics in live models.")
        return 0

    print(__doc__)
    print("\nUsage pattern:")
    print("  from tools.data_fabric.hvpe_public_facts import record_public_snapshot")
    print("  record_public_snapshot(as_of=..., metrics={...}, document_title=...)")
    print("\nOr run with --demo to emit a template file under tools/data_fabric/out/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
