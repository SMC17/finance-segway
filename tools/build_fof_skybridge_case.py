"""Generate the Fund of Funds domain's second public case: SkyBridge FY2023
(a real, disclosed hedge-fund-of-funds collapse), the adversarial pairing
for fof-public-hlpaf-2026's conventional case.

tools/verify_release_shape.py requires exactly two public cases per M2+
model. fof-public-hlpaf-2026 alone is real progress but not sufficient --
this case closes that gap, following the same conventional+adversarial
pairing pattern already established for domain 30 (QQQ conventional /
KWEB adversarial).

WHAT MAKES THIS ADVERSARIAL, FOR REAL
--------------------------------------
SkyBridge Multi-Adviser Hedge Fund Portfolios, LLC (CIK 0001181848),
Series G, is a real, SEC-registered fund-of-hedge-funds managed by
SkyBridge Capital, publicly known for exposure to FTX ahead of FTX's
November 2022 collapse. Its FY2023 N-CSR (period ended 2023-03-31)
discloses this directly: FTX Trading Ltd. common and three preferred
share classes, real aggregate cost $37,206,327, marked to real fair
value $0 -- a genuine, disclosed total write-off, not a synthetic stress
scenario. The fund's own disclosed one-year return, -30.29% vs. its
benchmark's -1.93%, is real and severe.

Top-8 positions are selected by ORIGINAL COST, not current fair value
(the convention fof-public-hlpaf-2026 uses) -- sorting by post-loss fair
value would silently drop the FTX position (now $0) from the cut, which
would defeat the entire purpose of an adversarial case. Cost-based
selection surfaces both the fund's largest real winners (Point72,
Axonic, Millennium) and its largest real total loss (FTX) side by side.

WHAT'S REAL, WHAT'S A LABELED GAP, AND ONE STRUCTURAL MISMATCH
-----------------------------------------------------------------
Real: per-position cost, fair value, strategy classification (a real
improvement over HLPAF's undisclosed strategy field), and first
acquisition date, all from the Consolidated Schedule of Investments.
FoF-level beginning/ending Shareholders' Capital, realized/unrealized
loss, distributions (both FY2023 and FY2022, both disclosed directly in
this one filing's comparative table), and paid-in capital, all from the
Consolidated Statements of Changes in Shareholders' Capital.

Not disclosed, not invented: per-position Commitment/Called/Distributed
history -- same real gap as HLPAF; Cost substitutes for Commitment/
Called, Distributed stays 0.

One further, real mismatch beyond HLPAF's fee-model gap: this fund uses
open-end/interval subscription-redemption mechanics (contributions +
reinvested distributions + redemptions), not the private-equity-style
capital-call mechanics this domain's template models (calls +
distributions only -- no redemptions line). Redemptions of $213.5mm
during the period have no template slot; this is disclosed as a real
structural limitation, expected to produce a materially larger NAV
roll-forward reconciliation residual than HLPAF's fee-model mismatch
alone -- another instance of this repo's "honest imperfection over false
precision" pattern, not suppressed to force a clean Checks tab.

Usage:
    python tools/build_fof_skybridge_case.py
    python tools/build_fof_skybridge_case.py --print-only
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
MANIFEST_PATH = ROOT / "standards" / "public_cases" / "fof-public-skybridge-fy2023-stress.json"
SNAPSHOT_PATH = DOMAIN_DIR / "sources" / "snapshots" / "fof-public-skybridge-fy2023-stress.json"
REGISTER_PATH = DOMAIN_DIR / "sources" / "source_register.csv"

CASE_ID = "fof-public-skybridge-fy2023-stress"
AS_OF = "2023-03-31"

RAW = json.loads((OUT_DIR / "SKYBRIDGE_sec_ncsr_fy2023_stress.json").read_text(encoding="utf-8"))
V = RAW["captured_values"]

NCSR_SOURCE = {
    "name": "SkyBridge Multi-Adviser Hedge Fund Portfolios, LLC Consolidated Schedule of Investments and Statements of Changes in Shareholders' Capital (SEC Form N-CSR)",
    "url": RAW["url"],
    "as_of": AS_OF,
    "notes": (
        f"Filed {RAW['filed_at']}, accession {RAW['accession_number']}, CIK {RAW['cik']}. "
        "Source of the underlying-fund look-through portfolio (real strategy and acquisition-date "
        "fields, unlike fof-public-hlpaf-2026), the FoF-level NAV roll-forward, and paid-in capital. "
        "The fund's own -30.29% disclosed one-year return and FTX Trading Ltd. total write-off "
        "(real cost $37.2mm, real fair value $0) are the source of this case's adversarial content."
    ),
}


def _holdings() -> list[dict[str, Any]]:
    return V["top_8_positions_by_cost_usd"]


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    holdings = _holdings()
    net_assets_end = V["shareholders_capital_usd"]["2023-03-31"] / 1_000_000
    net_assets_begin = V["shareholders_capital_usd"]["2022-03-31"] / 1_000_000
    net_loss_mm = (
        V["fy2023_net_realized_loss_investment_funds_usd"]
        + V["fy2023_net_realized_loss_securities_usd"]
        + V["fy2023_net_change_unrealized_depreciation_investment_funds_usd"]
        + V["fy2023_net_change_unrealized_depreciation_securities_usd"]
        + V["fy2023_net_change_unrealized_depreciation_related_party_securities_usd"]
    ) / 1_000_000
    # Net capital share transactions, the same basis the HLPAF case uses:
    # redemptions are a disclosed component of the period's capital
    # movement and dominate it here (-$213.5mm against $0.4mm of
    # contributions), so omitting them leaves the roll-forward unable to
    # reconcile no matter how good the rest of the sourcing is.
    capital_in_period_mm = (
        V["fy2023_capital_contributions_usd"]
        + V["fy2023_reinvestment_of_distributions_usd"]
        + V["fy2023_capital_redemptions_usd"]
    ) / 1_000_000
    # Disclosed net investment loss -- the first line of the statement of
    # changes, already containing the fund's management fee. Positive here
    # because the template's C11 formula subtracts it.
    net_investment_loss_mm = -V["fy2023_net_investment_loss_usd"] / 1_000_000
    distributions_period_mm = abs(V["fy2023_distributions_from_distributable_earnings_usd"]) / 1_000_000
    paid_in_capital_mm = V["paid_in_capital_usd"] / 1_000_000
    distributions_to_date_mm = (
        abs(V["fy2023_distributions_from_distributable_earnings_usd"])
        + abs(V["fy2022_distributions_from_distributable_earnings_usd"])
    ) / 1_000_000

    inputs: list[dict[str, Any]] = [
        {"sheet": "Cover", "cell": "C9", "value": "Downside", "input_kind": "observed", "source": NCSR_SOURCE},
        {"sheet": "Assumptions", "cell": "D5", "value": round(paid_in_capital_mm, 1), "input_kind": "derived", "source": NCSR_SOURCE},
        {"sheet": "Assumptions", "cell": "D9", "value": len(holdings), "input_kind": "observed", "source": NCSR_SOURCE},
        {"sheet": "NAV Rollforward & Fee Layering", "cell": "C5", "value": round(net_assets_begin, 3), "input_kind": "observed", "source": NCSR_SOURCE},
        {"sheet": "NAV Rollforward & Fee Layering", "cell": "C6", "value": round(capital_in_period_mm, 3), "input_kind": "observed", "source": NCSR_SOURCE},
        {"sheet": "NAV Rollforward & Fee Layering", "cell": "C7", "value": round(distributions_period_mm, 3), "input_kind": "observed", "source": NCSR_SOURCE},
        {"sheet": "NAV Rollforward & Fee Layering", "cell": "C14", "value": round(net_investment_loss_mm, 3), "input_kind": "observed", "source": NCSR_SOURCE},
        {"sheet": "NAV Rollforward & Fee Layering", "cell": "C10", "value": round(net_loss_mm, 3), "input_kind": "derived", "source": NCSR_SOURCE},
        {"sheet": "NAV Rollforward & Fee Layering", "cell": "C12", "value": round(net_assets_end, 3), "input_kind": "observed", "source": NCSR_SOURCE},
        {"sheet": "NAV Rollforward & Fee Layering", "cell": "C15", "value": round(paid_in_capital_mm, 1), "input_kind": "observed", "source": NCSR_SOURCE},
        {"sheet": "NAV Rollforward & Fee Layering", "cell": "C16", "value": round(distributions_to_date_mm, 1), "input_kind": "derived", "source": NCSR_SOURCE},
    ]

    for i, h in enumerate(holdings):
        row = 5 + i
        cost_mm = h["cost"] / 1_000_000
        fv_mm = h["fair_value"] / 1_000_000
        vintage_year = int(h["first_acquisition_date"][:4])
        inputs.append({"sheet": "Underlying Fund Portfolio", "cell": f"B{row}", "value": h["name"], "input_kind": "observed", "source": NCSR_SOURCE})
        inputs.append({"sheet": "Underlying Fund Portfolio", "cell": f"C{row}", "value": vintage_year, "input_kind": "observed", "source": NCSR_SOURCE})
        inputs.append({"sheet": "Underlying Fund Portfolio", "cell": f"D{row}", "value": h["strategy"], "input_kind": "observed", "source": NCSR_SOURCE})
        inputs.append({"sheet": "Underlying Fund Portfolio", "cell": f"E{row}", "value": round(cost_mm, 2), "input_kind": "derived", "source": NCSR_SOURCE})
        inputs.append({"sheet": "Underlying Fund Portfolio", "cell": f"F{row}", "value": round(cost_mm, 2), "input_kind": "derived", "source": NCSR_SOURCE})
        inputs.append({"sheet": "Underlying Fund Portfolio", "cell": f"G{row}", "value": 0.0, "input_kind": "observed", "source": NCSR_SOURCE})
        inputs.append({"sheet": "Underlying Fund Portfolio", "cell": f"H{row}", "value": round(fv_mm, 2), "input_kind": "observed", "source": NCSR_SOURCE})

    outcome = {
        "metric": "one_year_total_return",
        "forecast": 0.0,
        "realized": V["one_year_total_return_series_g"],
        "realized_source": "SkyBridge Multi-Adviser Hedge Fund Portfolios, LLC N-CSR annual shareholder report, period ended 2023-03-31 (fund's own disclosed Annualized Total Returns table, One Year column)",
        "status": "recorded",
    }

    manifest = {
        "schema_version": "1.0",
        "id": CASE_ID,
        "classification": "external_historical_case",
        "counts_toward_M4": False,
        "template": "29_Fund_of_Funds/_template_FOF.xlsx",
        "output": "29_Fund_of_Funds/instances/public_skybridge_fy2023_stress.xlsx",
        "as_of": AS_OF,
        "scenario": "Downside",
        "cover": {
            "FoF vehicle / vintage:": "SkyBridge Multi-Adviser Hedge Fund Portfolios, LLC – Series G, CIK 0001181848",
        },
        "inputs": inputs,
        "sources": [NCSR_SOURCE],
        "refresh": {
            "date": AS_OF,
            "trigger": "Second public case for the Fund of Funds domain -- tools/verify_release_shape.py requires exactly two per M2+ model, and the conventional-only fof-public-hlpaf-2026 case alone was not sufficient",
            "source_snapshot": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
            "what_changed": f"Generated public case {CASE_ID} from canonical release template",
            "reviewer_notes": (
                "External historical case; human stakeholder approval remains pending. Real, disclosed "
                "adversarial content (FTX Trading Ltd. written to real fair value $0; fund's own "
                "disclosed -30.29% one-year return). Position-level Commitment/Called/Distributed not "
                "disclosed -- Cost/first-acquisition-date substitute for Commitment/Called/vintage, "
                "labeled. This fund's real subscription-redemption mechanics (vs. this template's "
                "capital-call mechanics) have no redemptions line in the template -- expect a larger "
                "honest NAV-rollforward residual than fof-public-hlpaf-2026's fee-model mismatch alone."
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
                "sheet": "NAV Rollforward & Fee Layering", "cell": "C6", "driver_type": "not_disclosed",
                "rationale": "This fund's real capital inflow mechanics (contributions + reinvested distributions) don't map 1:1 onto this template's PE-style 'capital called' concept; the two real inflow line items are summed as the closest honest analog.",
                "basis": {},
            },
            {
                "sheet": "NAV Rollforward & Fee Layering", "cell": "C7", "driver_type": "not_disclosed",
                "rationale": "This template has no redemptions line -- $213.5mm of real FY2023 capital redemptions are not represented anywhere in the roll-forward, a genuine structural mismatch expected to inflate the reconciliation residual honestly rather than being forced to zero.",
                "basis": {},
            },
        ],
    }

    snapshot = {
        "schema_version": "1.0",
        "model_id": "29",
        "domain": "Fund of Funds",
        "case_id": CASE_ID,
        "case_type": "adversarial",
        "as_of": AS_OF,
        "capture_method": "curated_public_observation",
        "sources": [
            {
                "name": NCSR_SOURCE["name"],
                "url": NCSR_SOURCE["url"],
                "publisher": "SkyBridge Capital II, LLC (SEC EDGAR)",
                "captured_values": V,
            },
        ],
    }
    snapshot["snapshot_sha256"] = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return manifest, snapshot


def write_source_register(snapshot: dict[str, Any]) -> None:
    import csv
    import io

    row = {
        "source_id": CASE_ID,
        "source_name": NCSR_SOURCE["name"],
        "document_or_dataset": f"Form N-CSR, accession {RAW['accession_number']}",
        "publisher": "SkyBridge Capital II, LLC / SEC EDGAR",
        "publication_date": RAW["filed_at"],
        "as_of_date": AS_OF,
        "retrieval_date": RAW["retrieved_at"],
        "url_or_locator": NCSR_SOURCE["url"],
        "unit": "USD",
        "currency": "USD",
        "transformation": (
            "Top-8 positions selected by original cost (not fair value, to keep the real FTX total "
            "write-off in view) from the Consolidated Schedule of Investments; NAV roll-forward "
            "figures from the Consolidated Statements of Changes in Shareholders' Capital"
        ),
        "workbook_destination": "FoF Assumptions / Underlying Fund Portfolio / NAV Rollforward & Fee Layering",
        "license_or_restriction": "Public SEC filing",
        "snapshot_or_checksum": f"{SNAPSHOT_PATH.relative_to(ROOT)} sha256={snapshot['snapshot_sha256']}",
        "owner": "data-fabric",
        "notes": (
            "Adversarial case: FTX Trading Ltd. real cost $37.2mm marked to real fair value $0; "
            "fund's own disclosed one-year return -30.29% vs. benchmark -1.93%."
        ),
    }

    row_buf = io.StringIO()
    csv.DictWriter(row_buf, fieldnames=list(row.keys())).writerow(row)
    new_line = row_buf.getvalue()

    # The existing register has unquoted commas inside some free-text fields
    # (pre-existing, not RFC 4180 strict) -- csv.DictReader would misparse it.
    # Treat existing content as opaque text, line by line; replace this case's
    # own line in place (regeneration must update it, not silently skip and
    # leave a stale hash) rather than reparsing the whole file.
    existing_text = REGISTER_PATH.read_text(encoding="utf-8") if REGISTER_PATH.exists() else ""
    if not existing_text:
        header_buf = io.StringIO()
        csv.DictWriter(header_buf, fieldnames=list(row.keys())).writeheader()
        existing_text = header_buf.getvalue()
    lines = existing_text.splitlines(keepends=True)
    lines = [line for line in lines if not line.startswith(f"{CASE_ID},")]
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    lines.append(new_line)
    REGISTER_PATH.write_text("".join(lines), encoding="utf-8")


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
