"""Generate the Fund of Funds public case: Hamilton Lane Private Assets Fund.

Closes 29_Fund_of_Funds' declared M1-not-M2 gap. A prior session attempted
to source a real case from closed-end, London-listed vehicles (HarbourVest
Global Private Equity, Pantheon International) and hit HTTP 403 on both
the factsheet PDF and the UK FCA National Storage Mechanism -- documented
in model_card.md's "Why M1, not M2" rather than papered over.

This case instead uses Hamilton Lane Private Assets Fund (HLPAF, CIK
0001803491), a real, SEC-registered (1940 Act) non-traded interval fund
that invests across direct PE/credit positions and secondary fund-of-funds
stakes. Same filing types (N-CSR) this session already used successfully
for KWEB and UiPath -- SEC EDGAR, not the UK regime the prior attempt
couldn't reach.

WHAT THIS CASE CAN AND CANNOT GROUND
-------------------------------------
Real: the top 8 (of 159 disclosed) secondary-fund positions by fair
value, each with real cost and fair value from the Consolidated Schedule
of Investments (extracted programmatically via regex over the real filing
text, not hand-typed). Real: FoF-level beginning/ending NAV, this-year
realized and unrealized gains, this-year distributions, this-year net
capital-share transactions, and paid-in capital (used as "total called to
date"), all from the Consolidated Statements of Changes in Net Assets.

NOT disclosed, and not invented: per-position Commitment/Called/
Distributed history (a secondaries buyer reports only its own cost and
fair value, not the original LP's commitment schedule) -- Cost is used as
both Commitment and Called (defensible: cost is what HLPAF itself paid),
Distributed stays 0 per position, a real, stated gap. Per-position vintage
year and PE substrategy are not disclosed either; HLPAF's own acquisition
date substitutes for vintage, explicitly labeled as a proxy, not a claim
about the underlying fund's own vintage. Cumulative "distributions to
date" uses only the two most recently disclosed fiscal years, explicitly
not a full since-inception sum. FoF management fee, carried interest, and
hurdle stay at the template's own illustrative defaults -- HLPAF's real
fee structure (management fee + incentive fee + per-class distribution
fees) does not map cleanly onto this template's simplified two-line fee
model, and forcing a fit would misrepresent it.

Given that mismatch, expect the NAV roll-forward reconciliation check to
show a real, honest residual, not a clean tie-out -- the template's
simplified fee model applied to a real, complex multi-share-class fund's
real gross investment gains will not reproduce the real reported ending
NAV exactly. That is the correct, informative signal for this case, the
same "honest imperfection" pattern established elsewhere in this repo
(e.g. Private Credit's Yellow Corp REVIEW, ETF's KWEB sector-band REVIEW).

Usage:
    python tools/build_fof_hlpaf_case.py
    python tools/build_fof_hlpaf_case.py --print-only
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "tools" / "data_fabric" / "out"
DOMAIN_DIR = ROOT / "29_Fund_of_Funds"
MANIFEST_PATH = ROOT / "standards" / "public_cases" / "fof-public-hlpaf-2026.json"
SNAPSHOT_PATH = DOMAIN_DIR / "sources" / "snapshots" / "fof-public-hlpaf-2026.json"
REGISTER_PATH = DOMAIN_DIR / "sources" / "source_register.csv"

CASE_ID = "fof-public-hlpaf-2026"
AS_OF = "2026-03-31"

NCSR = json.loads((OUT_DIR / "HLPAF_sec_ncsr_annual_report.json").read_text(encoding="utf-8"))
V = NCSR["captured_values"]

NCSR_SOURCE = {
    "name": "Hamilton Lane Private Assets Fund Consolidated Schedule of Investments and Statements of Changes in Net Assets (SEC Form N-CSR)",
    "url": NCSR["url"],
    "as_of": AS_OF,
    "notes": (
        f"Filed {NCSR['filed_at']}, accession {NCSR['accession_number']}, CIK {NCSR['cik']}. "
        "Source of the underlying-fund look-through portfolio, FoF-level NAV roll-forward, "
        "and paid-in capital."
    ),
}


def _holdings() -> list[dict[str, Any]]:
    return V["top_8_secondary_fund_positions_usd"]


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    holdings = _holdings()
    net_assets_end = V["total_net_assets_usd"]["2026-03-31"] / 1_000_000
    net_assets_begin = V["total_net_assets_usd"]["2025-03-31"] / 1_000_000
    net_gain_mm = (
        V["fy2026_net_realized_gain_usd"]
        + V["fy2026_net_unrealized_appreciation_usd"]
        + V["fy2026_net_unrealized_fx_depreciation_usd"]
    ) / 1_000_000
    distributions_period_mm = V["fy2026_distributions_to_investors_usd"] / 1_000_000
    capital_called_period_mm = V["fy2026_net_capital_share_transactions_usd"] / 1_000_000
    # The fund's disclosed net investment loss -- the first line of its
    # Statement of Changes in Net Assets, and the one component of the
    # roll-forward the template otherwise models rather than sources.
    # Positive here because the template's C11 formula subtracts C8.
    net_investment_loss_mm = -V["fy2026_net_investment_loss_usd"] / 1_000_000
    paid_in_capital_mm = V["paid_in_capital_usd"] / 1_000_000
    distributions_to_date_mm = (
        V["fy2026_distributions_to_investors_usd"] + V["fy2025_distributions_to_investors_usd"]
    ) / 1_000_000

    inputs: list[dict[str, Any]] = [
        {"sheet": "Assumptions", "cell": "C5", "value": round(paid_in_capital_mm, 1), "input_kind": "derived", "source": NCSR_SOURCE},
        {"sheet": "Assumptions", "cell": "C9", "value": len(holdings), "input_kind": "observed", "source": NCSR_SOURCE},
        {"sheet": "NAV Rollforward & Fee Layering", "cell": "C5", "value": round(net_assets_begin, 3), "input_kind": "observed", "source": NCSR_SOURCE},
        {"sheet": "NAV Rollforward & Fee Layering", "cell": "C6", "value": round(capital_called_period_mm, 3), "input_kind": "observed", "source": NCSR_SOURCE},
        {"sheet": "NAV Rollforward & Fee Layering", "cell": "C7", "value": round(distributions_period_mm, 3), "input_kind": "observed", "source": NCSR_SOURCE},
        {"sheet": "NAV Rollforward & Fee Layering", "cell": "C14", "value": round(net_investment_loss_mm, 3), "input_kind": "observed", "source": NCSR_SOURCE},
        {"sheet": "NAV Rollforward & Fee Layering", "cell": "C10", "value": round(net_gain_mm, 3), "input_kind": "derived", "source": NCSR_SOURCE},
        {"sheet": "NAV Rollforward & Fee Layering", "cell": "C12", "value": round(net_assets_end, 3), "input_kind": "observed", "source": NCSR_SOURCE},
        {"sheet": "NAV Rollforward & Fee Layering", "cell": "C15", "value": round(paid_in_capital_mm, 1), "input_kind": "observed", "source": NCSR_SOURCE},
        {"sheet": "NAV Rollforward & Fee Layering", "cell": "C16", "value": round(distributions_to_date_mm, 1), "input_kind": "derived", "source": NCSR_SOURCE},
    ]

    for i, h in enumerate(holdings):
        row = 5 + i
        cost_mm = h["cost"] / 1_000_000
        fv_mm = h["fair_value"] / 1_000_000
        vintage_year = int(h["acquisition_date"][:4])
        inputs.append({"sheet": "Underlying Fund Portfolio", "cell": f"B{row}", "value": h["name"], "input_kind": "observed", "source": NCSR_SOURCE})
        inputs.append({"sheet": "Underlying Fund Portfolio", "cell": f"C{row}", "value": vintage_year, "input_kind": "derived", "source": NCSR_SOURCE})
        inputs.append({"sheet": "Underlying Fund Portfolio", "cell": f"D{row}", "value": "n/a (not disclosed at position level)", "input_kind": "observed", "source": NCSR_SOURCE})
        inputs.append({"sheet": "Underlying Fund Portfolio", "cell": f"E{row}", "value": round(cost_mm, 2), "input_kind": "derived", "source": NCSR_SOURCE})
        inputs.append({"sheet": "Underlying Fund Portfolio", "cell": f"F{row}", "value": round(cost_mm, 2), "input_kind": "derived", "source": NCSR_SOURCE})
        inputs.append({"sheet": "Underlying Fund Portfolio", "cell": f"G{row}", "value": 0.0, "input_kind": "observed", "source": NCSR_SOURCE})
        inputs.append({"sheet": "Underlying Fund Portfolio", "cell": f"H{row}", "value": round(fv_mm, 2), "input_kind": "observed", "source": NCSR_SOURCE})

    outcome = {
        "metric": "next_fiscal_year_total_net_assets_usd_mm",
        "forecast": round(net_assets_end, 1),
        "realized": None,
        "realized_source": "Pending next maintained evidence refresh",
        "status": "pending",
    }

    manifest = {
        "schema_version": "1.0",
        "id": CASE_ID,
        "classification": "external_historical_case",
        "counts_toward_M4": False,
        "template": "29_Fund_of_Funds/_template_FOF.xlsx",
        "output": "29_Fund_of_Funds/instances/public_hlpaf_2026.xlsx",
        "as_of": AS_OF,
        "scenario": "Base",
        "cover": {
            "FoF vehicle / vintage:": "Hamilton Lane Private Assets Fund (HLPAF), CIK 0001803491",
        },
        "inputs": inputs,
        "sources": [NCSR_SOURCE],
        "refresh": {
            "date": AS_OF,
            "trigger": "Initial real-instance sourcing for the Fund of Funds domain (model_card.md M1-not-M2 gap)",
            "source_snapshot": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
            "what_changed": f"Generated public case {CASE_ID} from canonical release template",
            "reviewer_notes": (
                "External historical case; human stakeholder approval remains pending. "
                "Per-position Commitment/Called/Distributed and vintage are not disclosed at the "
                "position level for a secondaries buyer's schedule of investments -- Cost/acquisition "
                "date substitute, explicitly labeled. FoF fee/carry/hurdle stay at template "
                "illustrative defaults; HLPAF's real multi-class fee structure does not map onto this "
                "template's simplified two-line fee model."
            ),
            "next_check": "On source revision, builder change, monitoring breach, or quarterly review",
        },
        "outcome": outcome,
        "lineage": {
            "source_snapshot": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
            "synthetic_benchmark_inputs_allowed": False,
        },
        "driver_declarations": [
            {
                "sheet": "Underlying Fund Portfolio", "cell": "D5", "driver_type": "not_disclosed",
                "rationale": "PE substrategy per underlying-fund position is not disclosed in the schedule of investments; labeled n/a rather than guessed.",
                "basis": {},
            },
            {
                "sheet": "Assumptions", "cell": "C6", "driver_type": "modeler_assumption",
                "rationale": "HLPAF's real fee structure (management fee + incentive fee + per-class distribution fees) does not decompose into this template's simplified management-fee/carry model from public disclosure alone; kept at template default.",
                "basis": {},
            },
        ],
    }

    snapshot = {
        "schema_version": "1.0",
        "model_id": "29",
        "domain": "Fund of Funds",
        "case_id": CASE_ID,
        "case_type": "conventional",
        "as_of": AS_OF,
        "capture_method": "curated_public_observation",
        "sources": [
            {
                "name": NCSR_SOURCE["name"],
                "url": NCSR_SOURCE["url"],
                "publisher": "Hamilton Lane Advisors, L.L.C. (SEC EDGAR)",
                "captured_values": V,
            },
        ],
    }
    snapshot["snapshot_sha256"] = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return manifest, snapshot


_REGISTER_FIELDS = [
    "source_id", "source_name", "document_or_dataset", "publisher", "publication_date",
    "as_of_date", "retrieval_date", "url_or_locator", "unit", "currency", "transformation",
    "workbook_destination", "license_or_restriction", "snapshot_or_checksum", "owner", "notes",
]


def write_source_register(snapshot: dict[str, Any]) -> None:
    import csv
    import io

    row = {
        "source_id": CASE_ID,
        "source_name": NCSR_SOURCE["name"],
        "document_or_dataset": f"Form N-CSR, accession {NCSR['accession_number']}",
        "publisher": "Hamilton Lane Advisors, L.L.C. / SEC EDGAR",
        "publication_date": NCSR["filed_at"],
        "as_of_date": AS_OF,
        "retrieval_date": NCSR["retrieved_at"],
        "url_or_locator": NCSR_SOURCE["url"],
        "unit": "USD",
        "currency": "USD",
        "transformation": (
            "Regex extraction of top-8 (of 159) secondary-fund positions by fair value from the "
            "Consolidated Schedule of Investments; NAV roll-forward figures from the Consolidated "
            "Statements of Changes in Net Assets"
        ),
        "workbook_destination": "FoF Assumptions / Underlying Fund Portfolio / NAV Rollforward & Fee Layering",
        "license_or_restriction": "Public SEC filing",
        "snapshot_or_checksum": f"{SNAPSHOT_PATH.relative_to(ROOT)} sha256={snapshot['snapshot_sha256']}",
        "owner": "data-fabric",
        "notes": (
            "Position-level Commitment/Called/Distributed not disclosed for secondary-market fund "
            "stakes; Cost used as Commitment/Called proxy, Distributed=0. Vintage not disclosed; "
            "acquisition date used as labeled proxy."
        ),
    }

    # The existing register has unquoted commas inside some free-text fields
    # (pre-existing, not RFC 4180 strict) -- csv.DictReader would misparse it.
    # Treat existing content as opaque text; append only the new row, itself
    # correctly quoted.
    existing_text = REGISTER_PATH.read_text(encoding="utf-8") if REGISTER_PATH.exists() else ""
    if f"\n{CASE_ID}," in ("\n" + existing_text):
        # Already registered from a prior run -- leave file untouched.
        return
    if not existing_text:
        header_buf = io.StringIO()
        csv.DictWriter(header_buf, fieldnames=_REGISTER_FIELDS).writeheader()
        existing_text = header_buf.getvalue()
    if not existing_text.endswith("\n"):
        existing_text += "\n"

    row_buf = io.StringIO()
    csv.DictWriter(row_buf, fieldnames=_REGISTER_FIELDS).writerow(row)
    REGISTER_PATH.write_text(existing_text + row_buf.getvalue(), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-only", action="store_true")
    args = parser.parse_args()

    manifest, snapshot = build()
    if args.print_only:
        print(json.dumps(manifest, indent=2))
        return 0

    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_source_register(snapshot)
    print(f"saved {MANIFEST_PATH.relative_to(ROOT)}")
    print(f"saved {REGISTER_PATH.relative_to(ROOT)}")
    print(f"saved {SNAPSHOT_PATH.relative_to(ROOT)}  sha256={snapshot['snapshot_sha256'][:16]}...")
    print(f"inputs={len(manifest['inputs'])} sourced cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
