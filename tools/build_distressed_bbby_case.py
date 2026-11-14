"""Generate the Bed Bath & Beyond 2022 liquidity case: the adversarial Distressed & Restructuring case.

As-of point: 2022-09-30, the day Bed Bath & Beyond filed its Form 10-Q for the
fiscal quarter ended 2022-08-27 (accession 0000886158-22-000150). Every input
uses only information that was public on or before that date. The case was
previously dated 2022-08-27, the balance-sheet date, while citing the 10-Q;
that 10-Q was not public until 2022-09-30, so the case date now follows the
filing date rather than the period end. The Chapter 11 petition of 2023-04-23
appears only in the outcome block, as the realized value.

What each sheet represents
--------------------------
13-Week Liquidity
    The 13 weeks after the balance-sheet date, 2022-08-28 to 2022-11-26
    (fiscal Q3 2022, which is exactly 13 weeks). The opening balance is the
    disclosed unrestricted cash. No weekly cash forecast was ever published,
    so the weekly flows are declared drivers. They are pinned to disclosed
    aggregates: receipts plus operating disbursements reproduce the fiscal
    Q2 2022 operating cash flow exactly, and the post-quarter financing is
    the disclosed amount.
New Money
    The undrawn borrowing capacity Bed Bath & Beyond reported at the end of
    fiscal September 2022 ($690.0mm). After the $375.0mm FILO term loan was
    funded on or before 2022-09-02, the remaining capacity is the ABL
    revolver, so the economics are the ABL's.
Recovery Waterfall
    The capital structure on the balance-sheet date, 2022-08-27, valued at
    the market prices the 10-Q itself discloses: the senior notes' Level 1
    fair value ($254.3mm against $1,184.4mm principal) and the ABL at
    carrying value, which the 10-Q says approximates fair value.
Liquidation vs Reorg
    Book assets that a liquidation could monetize, against the same
    creditor-implied going-concern value used in the waterfall.

Usage:
    python tools/build_distressed_bbby_case.py
    python tools/build_distressed_bbby_case.py --print-only
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

try:
    from tools.m3_evidence import canonical_bytes, sha256_bytes
    from tools.public_case_index import report_sync
except ModuleNotFoundError:  # invoked with tools/ directly on sys.path
    from m3_evidence import canonical_bytes, sha256_bytes
    from public_case_index import report_sync

ROOT = Path(__file__).resolve().parents[1]
DOMAIN_DIR = ROOT / "24_Distressed_Restructuring"
CASE_ID = "distressed-public-bbby-2022-liquidity"
MANIFEST_PATH = ROOT / "standards" / "public_cases" / f"{CASE_ID}.json"
SNAPSHOT_PATH = DOMAIN_DIR / "sources" / "snapshots" / f"{CASE_ID}.json"
REGISTER_PATH = DOMAIN_DIR / "sources" / "source_register.csv"

AS_OF = "2022-09-30"
BALANCE_SHEET_DATE = "2022-08-27"
WORK_DATE = "2026-11-13"
EMITTED_BY = "tools/build_distressed_bbby_case.py"

# ---------------------------------------------------------------------------
# Sources. Every value below was read from the filing named, fetched from
# sec.gov / fred.stlouisfed.org / the cited page; nothing is from memory.
# ---------------------------------------------------------------------------
TENQ = {
    "name": "Bed Bath & Beyond Inc. Form 10-Q for the quarter ended 2022-08-27 (SEC EDGAR, CIK 0000886158)",
    "url": "https://www.sec.gov/Archives/edgar/data/886158/000088615822000150/bbby-20220827.htm",
    "as_of": AS_OF,
    "notes": (
        "Filed 2022-09-30, accession 0000886158-22-000150. Balance sheet, statements of operations "
        "and cash flows as of and for the periods ended 2022-08-27; Note 2 (liquidity), Note 5 (fair "
        "value of the senior notes), Note 6 (cash), Note 13 (long-term debt, including post-quarter "
        "borrowings) and Note 14 (ATM program)."
    ),
}
Q1_TENQ = {
    "name": "Bed Bath & Beyond Inc. Form 10-Q for the quarter ended 2022-05-28 (SEC EDGAR, CIK 0000886158)",
    "url": "https://www.sec.gov/Archives/edgar/data/886158/000088615822000081/bbby-20220528.htm",
    "as_of": "2022-06-29",
    "notes": (
        "Filed 2022-06-29, accession 0000886158-22-000081. First-quarter operating cash flow "
        "(-$383.551mm) and interest paid ($1.3mm, XBRL InterestPaidNet), subtracted from the "
        "six-month figures to isolate fiscal Q2 2022."
    ),
}
XBRL = {
    "name": "Bed Bath & Beyond XBRL company facts (SEC EDGAR, CIK 0000886158)",
    "url": "https://data.sec.gov/api/xbrl/companyfacts/CIK0000886158.json",
    "as_of": AS_OF,
    "notes": (
        "InterestPaidNet: $1.3mm for 2022-02-27 to 2022-05-28 (10-Q filed 2022-06-29) and $33.5mm "
        "for 2022-02-27 to 2022-08-27 (10-Q filed 2022-09-30). Only facts filed on or before "
        "2022-09-30 are used."
    ),
}
FILO_8K = {
    "name": "Bed Bath & Beyond Inc. Form 8-K, Items 1.01 and 2.03, ABL amendment and FILO facility (event 2022-08-31)",
    "url": "https://www.sec.gov/Archives/edgar/data/886158/000119312522235718/d399971d8k.htm",
    "as_of": "2022-09-01",
    "notes": (
        "Filed 2022-09-01, accession 0001193125-22-235718. ABL commitments raised by $130.0mm to "
        "$1,130.0mm (matures 2026-08-09); new $375.0mm FILO term loan drawn on or before 2022-09-02 "
        "(matures 2027-08-31); FILO margin SOFR + 7.75% (SOFR floor 1.00%); ABL SOFR margin 1.25% to "
        "1.75%; ABL repayable at any time without premium or penalty; first-priority liens on "
        "substantially all assets; ABL borrowing base 90% of eligible card receivables and inventory."
    ),
}
UPDATE_8K = {
    "name": "Bed Bath & Beyond Inc. Form 8-K, Items 2.02/7.01/8.01, strategic and financial update (2022-08-31)",
    "url": "https://www.sec.gov/Archives/edgar/data/886158/000119312522234603/d279013d8k.htm",
    "as_of": "2022-08-31",
    "notes": (
        "Filed 2022-08-31, accession 0001193125-22-234603. Fiscal 2022 capital expenditures now "
        "planned at approximately $250mm (previously $400mm)."
    ),
}
TENK_FY21 = {
    "name": "Bed Bath & Beyond Inc. Form 10-K for the fiscal year ended 2022-02-26 (SEC EDGAR, CIK 0000886158)",
    "url": "https://www.sec.gov/Archives/edgar/data/886158/000088615822000047/bbby-20220226.htm",
    "as_of": "2022-04-21",
    "notes": (
        "Filed 2022-04-21, accession 0000886158-22-000047. Senior notes outstanding principal: "
        "approximately $284.4mm of 3.749% notes due 2024 (Contractual Obligations); fiscal 2020 "
        "purchases of $75.0mm of the 4.915% 2034 notes (issued $300.0mm) and approximately $225.0mm "
        "of the 5.165% 2044 notes (issued $900.0mm) (Note 7)."
    ),
}
CREDIT_AGREEMENT = {
    "name": "Bed Bath & Beyond Inc. Amended and Restated Credit Agreement dated 2021-08-09 (Form 8-K Exhibit 10.1)",
    "url": "https://www.sec.gov/Archives/edgar/data/886158/000088615821000033/bbbyamendedandrestatedablc.htm",
    "as_of": "2021-08-10",
    "notes": (
        "Filed 2021-08-10, accession 0000886158-21-000033. Section 6.14: the fixed charge coverage "
        "covenant springs when Availability is less than the greater of 10% of the Line Cap and "
        "$95,000,000. Applicable Rate grid: Eurodollar/term spread 1.75% when Average Quarterly "
        "Availability is below 33% of the Aggregate Revolving Commitment. Commitment fee 0.20%-0.25% "
        "on unused commitments; no fee is charged per draw. The 2022-08-31 amendment itself was filed "
        "only as scanned page images (10-Q Exhibit 4.1) and was not machine-read, so these 2021 terms "
        "are cited as the last text-readable version."
    ),
}
FRED_SOFR = {
    "name": "Secured Overnight Financing Rate (SOFR), FRED series SOFR, Federal Reserve Bank of St. Louis",
    "url": "https://fred.stlouisfed.org/series/SOFR",
    "as_of": "2022-09-29",
    "notes": (
        "SOFR for 2022-09-29 = 2.96%, the latest rate published on or before the 2022-09-30 case "
        "date (the New York Fed publishes each day's SOFR the next business day)."
    ),
}
FITCH_DURATION = {
    "name": "Fitch Ratings bankruptcy case-study findings as reported by CFO.com, 'Companies Spending Less Time in Bankruptcy: Fitch' (2018-08-08)",
    "url": "https://cfo.com/news/companies-spending-less-time-in-bankruptcy-fitch/658759/",
    "as_of": "2018-08-08",
    "notes": (
        "Median petition-to-confirmation time: 11 months for conventional (non-prepackaged) cases "
        "confirmed in 2017; 7 months across 304 cases confirmed 2003 to early 2017; under 10 months "
        "for filers with $2bn-$4bn of assets."
    ),
}
TRU_PETITION = {
    "name": "Toys \"R\" Us, Inc. Form 8-K, Item 7.01, Chapter 11 petition (2017-09-18)",
    "url": "https://www.sec.gov/Archives/edgar/data/1005414/000119312517287834/d451484d8k.htm",
    "as_of": "2017-09-19",
    "notes": "Toys \"R\" Us and subsidiaries filed Chapter 11 petitions on 2017-09-18 (E.D. Va.).",
}
TRU_WINDDOWN = {
    "name": "Toys \"R\" Us, Inc. Form 8-K, Item 8.01, U.S. wind-down and liquidation (2018-03-15)",
    "url": "https://www.sec.gov/Archives/edgar/data/1005414/000119312518083225/d552404d8k.htm",
    "as_of": "2018-03-15",
    "notes": (
        "On 2018-03-15 Toys \"R\" Us announced it would close all 744 remaining U.S. stores and wind "
        "down Toys Delaware, 178 days (5.9 months) after its petition: the closest large U.S. retail "
        "Chapter 11 that turned into a liquidation and filed with the SEC."
    ),
}
LOPUCKI_FEES = {
    "name": "LoPucki-Doherty Professional Fees Calculator (University of Florida Levin College of Law), worked example",
    "url": "https://lopucki.law.ufl.edu/fee_calculator_prediction.php",
    "as_of": "2011-01-01",
    "notes": (
        "Model from LoPucki & Doherty, Professional Fees in Corporate Bankruptcies (Oxford 2011), "
        "table 3.1. The page's worked example: assets $4,200,000,000, revenues $4,196,600,000, filed "
        "2001, not prepackaged, not prenegotiated; predicted court-awarded fees and expenses from "
        "filing through confirmation $61,355,784, 85% interval $52,994,569 to $71,036,188. The live "
        "calculator's back end no longer responds, so Bed Bath & Beyond's own inputs could not be run."
    ),
}
OUTCOME_SOURCE = {
    "name": "Bed Bath & Beyond Inc. Form 10-K for fiscal 2022 and Chapter 11 disclosure",
    "url": "https://www.sec.gov/Archives/edgar/data/886158/000088615823000059/bbby-20230225.htm",
    "as_of": "2023-04-23",
    "notes": (
        "Filed after the case date. Used only for the realized outcome (Chapter 11 petition "
        "2023-04-23), never for an input."
    ),
}
SNAPSHOT_SOURCE = {
    "name": "Frozen source snapshot",
    "url": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
    "as_of": AS_OF,
    "notes": "Immutable curated observation package with SHA-256 digest",
}

# Disclosed figures, USD millions unless the key says otherwise.
V: dict[str, Any] = {
    "tenq": {
        "cash_and_cash_equivalents_usd_mm": 135.270,
        "restricted_cash_long_term_usd_mm": 31.4,
        "cash_including_restricted_usd_mm": 166.716,
        "merchandise_inventories_usd_mm": 1576.270,
        "prepaid_and_other_current_assets_usd_mm": 192.615,
        "long_term_investment_securities_usd_mm": 20.228,
        "property_and_equipment_net_usd_mm": 1121.203,
        "operating_lease_assets_usd_mm": 1469.076,
        "other_assets_usd_mm": 151.977,
        "total_assets_usd_mm": 4666.639,
        "long_term_debt_carrying_usd_mm": 1729.964,
        "total_shareholders_deficit_usd_mm": -577.654,
        "abl_borrowings_2022_08_27_usd_mm": 550.0,
        "abl_weighted_average_interest_rate": 0.0372,
        "letters_of_credit_outstanding_usd_mm": 136.4,
        "senior_notes_fair_value_level1_usd_mm": 254.3,
        "senior_notes_carrying_value_usd_mm": 1184.0,
        "senior_notes_unamortized_financing_costs_usd_mm": 4.4,
        "abl_availability_2022_08_27_usd_mm": 315.0,
        "available_borrowing_capacity_end_fiscal_september_2022_usd_mm": 690.0,
        "post_quarter_additional_borrowings_usd_mm": 175.0,
        "post_quarter_total_credit_facility_borrowings_usd_mm": 725.0,
        "filo_commitment_usd_mm": 375.0,
        "atm_post_quarter_proceeds_usd_mm": 30.0,
        "atm_post_quarter_shares_sold_millions": 3.0,
        "net_sales_q2_fy2022_usd_mm": 1437.018,
        "net_cash_used_in_operating_activities_6m_usd_mm": -582.425,
        "interest_paid_6m_usd_mm": 33.5,
        "capital_expenditures_6m_usd_mm": 226.5,
        "common_shares_outstanding_2022_08_27": 80362695,
    },
    "q1_tenq": {
        "net_cash_used_in_operating_activities_q1_usd_mm": -383.551,
        "interest_paid_q1_usd_mm": 1.3,
    },
    "filo_8k": {
        "abl_commitments_before_amendment_usd_mm": 1000.0,
        "abl_commitments_after_amendment_usd_mm": 1130.0,
        "filo_commitment_usd_mm": 375.0,
        "filo_funding_date": "2022-09-02",
        "abl_maturity_date": "2026-08-09",
        "filo_maturity_date": "2027-08-31",
        "filo_sofr_margin": 0.0775,
        "abl_sofr_margin_low": 0.0125,
        "abl_sofr_margin_high": 0.0175,
        "abl_advance_rate_inventory_and_card_receivables": 0.90,
    },
    "update_8k": {"fiscal_2022_planned_capex_usd_mm": 250.0},
    "tenk_fy21": {
        "notes_2024_principal_usd_mm": 284.4,
        "notes_2034_issued_usd_mm": 300.0,
        "notes_2034_purchased_fy2020_usd_mm": 75.0,
        "notes_2044_issued_usd_mm": 900.0,
        "notes_2044_purchased_fy2020_usd_mm": 225.0,
    },
    "credit_agreement": {
        "fccr_trigger_line_cap_share": 0.10,
        "fccr_trigger_floor_usd_mm": 95.0,
        "commitment_fee_low": 0.0020,
        "commitment_fee_high": 0.0025,
    },
    "fred": {"sofr_2022_09_29": 0.0296},
    "fitch": {"median_months_conventional_2017": 11, "median_months_all_2003_2017": 7},
    "tru": {"petition_date": "2017-09-18", "wind_down_announcement_date": "2018-03-15"},
    "lopucki": {
        "example_assets_usd": 4200000000,
        "example_revenues_usd": 4196600000,
        "example_predicted_fees_usd": 61355784,
        "example_fees_lower_85_usd": 52994569,
        "example_fees_upper_85_usd": 71036188,
    },
}


def _derive() -> dict[str, float]:
    t, q1, f, k = V["tenq"], V["q1_tenq"], V["filo_8k"], V["tenk_fy21"]
    d: dict[str, float] = {}
    d["q2_ocf"] = t["net_cash_used_in_operating_activities_6m_usd_mm"] - q1["net_cash_used_in_operating_activities_q1_usd_mm"]
    d["q2_interest_paid"] = t["interest_paid_6m_usd_mm"] - q1["interest_paid_q1_usd_mm"]
    d["weekly_receipts"] = t["net_sales_q2_fy2022_usd_mm"] / 13
    d["h2_capex"] = V["update_8k"]["fiscal_2022_planned_capex_usd_mm"] - t["capital_expenditures_6m_usd_mm"]
    d["weekly_operating_disbursements"] = (
        (t["net_sales_q2_fy2022_usd_mm"] - d["q2_ocf"] - d["q2_interest_paid"]) / 13 + d["h2_capex"] / 26
    )
    d["abl_drawn_post_quarter"] = t["post_quarter_total_credit_facility_borrowings_usd_mm"] - f["filo_commitment_usd_mm"]
    d["abl_rate"] = V["fred"]["sofr_2022_09_29"] + f["abl_sofr_margin_high"]
    d["filo_rate"] = V["fred"]["sofr_2022_09_29"] + f["filo_sofr_margin"]
    d["weekly_interest"] = (d["abl_drawn_post_quarter"] * d["abl_rate"] + f["filo_commitment_usd_mm"] * d["filo_rate"]) / 52
    d["new_money_week1"] = t["post_quarter_additional_borrowings_usd_mm"] + t["atm_post_quarter_proceeds_usd_mm"]
    d["min_liquidity"] = max(
        V["credit_agreement"]["fccr_trigger_line_cap_share"] * f["abl_commitments_after_amendment_usd_mm"],
        V["credit_agreement"]["fccr_trigger_floor_usd_mm"],
    )
    d["notes_face"] = (
        k["notes_2024_principal_usd_mm"]
        + (k["notes_2034_issued_usd_mm"] - k["notes_2034_purchased_fy2020_usd_mm"])
        + (k["notes_2044_issued_usd_mm"] - k["notes_2044_purchased_fy2020_usd_mm"])
    )
    d["creditor_implied_value"] = t["abl_borrowings_2022_08_27_usd_mm"] + t["senior_notes_fair_value_level1_usd_mm"]
    d["liquidation_gross"] = t["total_assets_usd_mm"] - t["operating_lease_assets_usd_mm"]
    d["liquidation_recovery"] = (
        t["cash_and_cash_equivalents_usd_mm"]
        + f["abl_advance_rate_inventory_and_card_receivables"] * t["merchandise_inventories_usd_mm"]
        + t["long_term_investment_securities_usd_mm"]
    )
    d["liquidation_discount"] = d["liquidation_gross"] - d["liquidation_recovery"]
    d["abl_tenor_years"] = (date.fromisoformat(f["abl_maturity_date"]) - date.fromisoformat(AS_OF)).days / 365.25
    d["professional_fees"] = V["lopucki"]["example_predicted_fees_usd"] / 1_000_000
    d["tru_months"] = (
        date.fromisoformat(V["tru"]["wind_down_announcement_date"]) - date.fromisoformat(V["tru"]["petition_date"])
    ).days / (365.25 / 12)
    # Tie-outs asserted in code so a transcription error cannot pass silently.
    assert abs(d["notes_face"] - 1184.4) < 1e-9
    assert abs((t["abl_borrowings_2022_08_27_usd_mm"] + d["notes_face"] - t["senior_notes_unamortized_financing_costs_usd_mm"]) - t["long_term_debt_carrying_usd_mm"]) < 0.05
    assert abs(t["cash_and_cash_equivalents_usd_mm"] + t["restricted_cash_long_term_usd_mm"] - t["cash_including_restricted_usd_mm"]) < 0.05
    assert abs(13 * (d["weekly_receipts"] - d["weekly_operating_disbursements"] + d["h2_capex"] / 26) - d["q2_interest_paid"] - d["q2_ocf"]) < 1e-6
    return d


def _src(base: dict[str, Any], note: str) -> dict[str, Any]:
    return {**base, "notes": f"{note} Source: {base['notes']}"}


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    d = _derive()
    t = V["tenq"]
    inputs: list[dict[str, Any]] = []
    drivers: list[dict[str, Any]] = []

    def add(sheet: str, cell: str, value: Any, kind: str, source: dict[str, Any], note: str) -> None:
        inputs.append({"sheet": sheet, "cell": cell, "value": value, "input_kind": kind,
                       "source": _src(source, note), "emitted_by": EMITTED_BY})

    def driver(sheet: str, cell: str, driver_type: str, rationale: str, basis_sources: list[dict[str, Any]], basis_range: str) -> None:
        drivers.append({
            "sheet": sheet, "cell": cell, "driver_type": driver_type, "rationale": rationale,
            "basis": {
                "source_name": "; ".join(s["name"] for s in basis_sources),
                "source_url": basis_sources[0]["url"],
                "additional_source_urls": [s["url"] for s in basis_sources[1:]],
                "range": basis_range,
            },
            "emitted_by": EMITTED_BY,
        })

    # ---- 13-Week Liquidity ------------------------------------------------
    ws = "13-Week Liquidity"
    add(ws, "C3", t["cash_and_cash_equivalents_usd_mm"], "observed", TENQ,
        "Unrestricted cash and cash equivalents at 2022-08-27, $135.270mm (balance sheet). The earlier "
        "value 166.7 was cash INCLUDING $31.4mm of long-term restricted cash held in other assets, which "
        "is not unrestricted liquidity.")
    c4 = round(d["min_liquidity"], 1)
    add(ws, "C4", c4, "modeler_assumption", CREDIT_AGREEMENT,
        "Minimum operating liquidity = max(10% x $1,130.0mm ABL commitments, $95.0mm) = $113.0mm, the "
        "availability level below which the springing fixed-charge covenant applies (Section 6.14). "
        "Bed Bath & Beyond's FCCR was negative, so falling below it is a default trigger.")
    driver(ws, "C4", "undisclosed_term_driver",
           "No cash floor is disclosed. The tightest disclosed liquidity trigger is the ABL's springing "
           "FCCR threshold on Availability; it is applied here to cash as the operating floor.",
           [CREDIT_AGREEMENT, FILO_8K],
           "$95.0mm (fixed floor) to $113.0mm (10% of the amended $1,130.0mm commitments); the cash-dominion trigger, max(12.5% of Line Cap, $120mm), would be $141.25mm.")
    rec = round(d["weekly_receipts"], 4)
    dis = round(d["weekly_operating_disbursements"], 4)
    intr = round(d["weekly_interest"], 4)
    for i, row in enumerate(range(7, 20), start=1):
        add(ws, f"D{row}", rec, "modeler_assumption", TENQ,
            f"Week {i} receipts = fiscal Q2 2022 net sales $1,437.018mm / 13 weeks = ${rec}mm. Run-rate: "
            "Q2 is the latest disclosed quarter and is itself 13 weeks.")
        add(ws, f"E{row}", dis, "modeler_assumption", TENQ,
            f"Week {i} disbursements = (Q2 net sales 1,437.018 - Q2 operating cash flow (-198.874) - Q2 "
            "interest paid 32.2) / 13 + remaining fiscal 2022 capex (250.0 planned - 226.5 spent) / 26 "
            f"= ${dis}mm. Includes capital expenditure because the template has no separate capex row.")
        add(ws, f"F{row}", intr, "modeler_assumption", FRED_SOFR,
            f"Week {i} interest = (ABL $350.0mm x (SOFR 2.96% + 1.75%) + FILO $375.0mm x (SOFR 2.96% + "
            f"7.75%)) / 52 = ${intr}mm. No senior-note coupon falls in the window (coupons are paid 1 Feb "
            "and 1 Aug).")
        add(ws, f"G{row}", 0, "modeler_assumption", TENQ,
            f"Week {i} professional fees = 0. Bed Bath & Beyond had disclosed no restructuring-adviser "
            "retention or fee amount by 2022-09-30; any adviser cost is inside the operating "
            "disbursements, which are pinned to Q2 operating cash flow.")
        h = round(d["new_money_week1"], 1) if row == 7 else 0
        add(ws, f"H{row}", h, "modeler_assumption", TENQ,
            ("Week 1 new money = $175.0mm net additional Credit Facility borrowings after quarter end "
             "(Note 13) + $30.0mm ATM equity proceeds after quarter end (Note 14) = $205.0mm. Placed in "
             "week 1 (2022-08-28 to 2022-09-03), which contains the FILO funding date (on or before "
             "2022-09-02) and the ATM program start (2022-08-31); the 10-Q gives amounts, not dates.")
            if row == 7 else
            (f"Week {i} new money = 0: no further committed financing was disclosed by 2022-09-30. "
             "Undrawn ABL capacity is carried on the New Money sheet, not as a scheduled draw."))
        driver(ws, f"D{row}", "undisclosed_metric_driver",
               "Weekly receipts were never disclosed; held at the fiscal Q2 2022 weekly run-rate.",
               [TENQ], "Q2 FY2022 net sales $1,437.018mm over 13 weeks; Q1 FY2022 was $1,463.418mm (six-month $2,900.436mm less Q2).")
        driver(ws, f"E{row}", "balancing_residual",
               "Operating disbursements are the residual that makes 13 weeks of receipts less disbursements "
               "less interest reproduce the disclosed fiscal Q2 2022 operating cash flow of -$198.874mm "
               "exactly, plus the disclosed remaining fiscal 2022 capex plan.",
               [TENQ, Q1_TENQ, XBRL, UPDATE_8K], "Pinned: Q2 operating cash flow -582.425 - (-383.551) = -198.874; capex 250.0 - 226.5 = 23.5 over 26 weeks.")
        driver(ws, f"F{row}", "undisclosed_term_driver",
               "Weekly interest is computed from disclosed balances and margins at the case-date SOFR; the "
               "rate path after 2022-09-30 and the ABL margin tier are assumptions.",
               [FRED_SOFR, FILO_8K, TENQ], "ABL margin 1.25%-1.75% (tier 1.75% used, availability 31.5% < 33% of commitments at 2022-08-27); FILO SOFR + 7.75%.")
        driver(ws, f"G{row}", "undisclosed_metric_driver",
               "No professional-fee disclosure existed by the case date.",
               [TENQ], "0 by disclosure; fees, if any, are inside disbursements pinned to Q2 operating cash flow.")
        driver(ws, f"H{row}", "undisclosed_term_driver",
               "Amounts are disclosed; the week in which they landed is not.",
               [TENQ, FILO_8K], "Total $205.0mm across weeks 1-5 (2022-08-28 to 2022-09-30); placed in week 1.")

    # ---- New Money --------------------------------------------------------
    ws = "New Money"
    add(ws, "C5", t["available_borrowing_capacity_end_fiscal_september_2022_usd_mm"], "observed", TENQ,
        "Available borrowing capacity at the end of fiscal September 2022, after the ABL upsizing to "
        "$1,130.0mm and the $375.0mm FILO (Note 2 and MD&A Liquidity).")
    add(ws, "C7", 0, "modeler_assumption", CREDIT_AGREEMENT,
        "Upfront fee per draw = 0: the ABL charges commitment fees on unused commitments "
        "(0.20%-0.25%) and letter-of-credit fees, not a fee on each revolver draw. Any fee on the "
        "2022-08-31 amendment was not disclosed.")
    driver(ws, "C7", "undisclosed_term_driver",
           "The amendment's fee letter was not filed; the 2021 agreement's fee structure has no per-draw fee.",
           [CREDIT_AGREEMENT], "0 per draw; 0.20%-0.25% per year on unused commitments, not modeled by the template.")
    add(ws, "C8", round(d["abl_rate"], 4), "modeler_assumption", FRED_SOFR,
        "ABL revolver cash rate = SOFR 2.96% (2022-09-29) + 1.75% top-tier margin = 4.71%. The remaining "
        "$690.0mm capacity is the ABL revolver, because the FILO term loan was fully drawn by 2022-09-02.")
    driver(ws, "C8", "undisclosed_term_driver",
           "The disclosed margin grid is a range; the tier and the SOFR path after the case date are assumptions.",
           [FRED_SOFR, FILO_8K, CREDIT_AGREEMENT],
           "4.21% (SOFR 2.96% + 1.25%) to 4.71% (+ 1.75%); 2022-08-27 weighted average actually paid 3.72%.")
    add(ws, "C9", round(d["abl_tenor_years"], 4), "derived", FILO_8K,
        "Tenor = days from the 2022-09-30 case date to the 2026-08-09 ABL maturity (1,409) / 365.25 = 3.8576 years.")
    add(ws, "C10", 0, "observed", FILO_8K,
        "Exit fee = 0: the 8-K states ABL borrowings may be repaid at any time without premium or penalty.")
    add(ws, "C11", 1, "derived", FILO_8K,
        "Priority multiplier 1.0x: the Credit Facilities hold first-priority liens on substantially all "
        "assets, senior to the unsecured notes.")

    # ---- Recovery Waterfall -----------------------------------------------
    ws = "Recovery Waterfall"
    add(ws, "C5", 0, "observed", TENQ,
        "DIP claim = 0: no Chapter 11 case and no DIP facility existed at 2022-08-27 or 2022-09-30.")
    add(ws, "C6", t["abl_borrowings_2022_08_27_usd_mm"], "observed", TENQ,
        "First-lien claim = $550.0mm ABL borrowings at 2022-08-27 (Note 13). Excludes $136.4mm of undrawn "
        "letters of credit. Post-quarter the first-lien total rose to $725.0mm, but the waterfall is valued "
        "at the 2022-08-27 market marks, so it uses the 2022-08-27 balance.")
    add(ws, "C7", 0, "observed", TENQ, "Second-lien claim = 0: Note 13 discloses no second-lien debt.")
    add(ws, "C8", round(d["notes_face"], 1), "derived", TENK_FY21,
        "Senior unsecured notes principal = 284.4 (3.749% 2024) + (300.0 - 75.0) (4.915% 2034) + "
        "(900.0 - 225.0) (5.165% 2044) = $1,184.4mm. Ties to the 10-Q: long-term debt 1,729.964 = ABL "
        "550.0 + 1,184.4 - unamortized costs 4.4 (difference 0.036, rounding).")
    add(ws, "C9", 0, "observed", TENQ, "Subordinated debt = 0: Note 13 discloses none.")
    add(ws, "C10", 0, "derived", TENQ,
        "Equity face claim = 0: book shareholders' equity at 2022-08-27 was a deficit of $(577.654)mm, so "
        "equity carries no positive claim.")
    add(ws, "C12", round(d["creditor_implied_value"], 1), "derived", TENQ,
        "Value available for distribution = ABL 550.0 at carrying value (the 10-Q states it approximates "
        "fair value) + senior notes at Level 1 fair value 254.3 = $804.3mm at 2022-08-27. This is the "
        "creditor-implied value; it excludes the equity's ~80.4mm-share market value, which the bond "
        "market did not underwrite.")
    for rank, row in enumerate(range(5, 11), start=1):
        add(ws, f"D{row}", rank, "derived", TENQ,
            f"Seniority rank {rank} under absolute priority, from the disclosed lien status: DIP, first "
            "lien (ABL/FILO, first-priority liens), second lien, senior unsecured notes, subordinated, equity.")

    # ---- Liquidation vs Reorg ---------------------------------------------
    ws = "Liquidation vs Reorg"
    add(ws, "C5", round(d["liquidation_gross"], 3), "derived", TENQ,
        "Liquidation gross asset value = total assets 4,666.639 - operating lease right-of-use assets "
        "1,469.076 = $3,197.563mm at 2022-08-27 (lease assets are not saleable in a liquidation).")
    add(ws, "C6", round(d["liquidation_discount"], 3), "modeler_assumption", FILO_8K,
        "Liquidation discount = 3,197.563 - (cash 135.270 + 90% x inventory 1,576.270 + investment "
        "securities 20.228) = $1,623.422mm. Inventory recovers at the ABL's 90% advance rate; prepaid "
        "assets, property and equipment and other assets recover nothing.")
    driver(ws, "C6", "undisclosed_metric_driver",
           "No liquidation analysis was published before 2022-09-30. The lenders' own advance rate is the "
           "only disclosed measure of what the collateral fetches in a forced sale.",
           [FILO_8K, TENQ],
           "Inventory recovery 90% (ABL advance rate) to 105% (ABL 90% + FILO 15% stacked advance rate); other non-cash assets 0%.")
    add(ws, "C7", round(d["professional_fees"], 3), "modeler_assumption", LOPUCKI_FEES,
        "Liquidation administrative and professional fees = $61.356mm, the LoPucki-Doherty predicted award "
        "for a $4.2bn-asset, non-prepackaged case (Bed Bath & Beyond's total assets were $4.667bn).")
    driver(ws, "C7", "undisclosed_metric_driver",
           "No Chapter 11 case existed at the case date, so no fee application could exist.",
           [LOPUCKI_FEES], "$52.995mm to $71.036mm (85% interval of the calculator's worked example, 2001 dollars, no post-2010 inflation adjustment).")
    add(ws, "C8", 6, "modeler_assumption", TRU_WINDDOWN,
        "Time to distribution in a liquidation = 6 months: Toys \"R\" Us took 178 days (5.9 months) from "
        "its 2017-09-18 petition to its 2018-03-15 U.S. liquidation decision.")
    driver(ws, "C8", "undisclosed_metric_driver",
           "A liquidation timeline for Bed Bath & Beyond did not exist at the case date; grounded in the "
           "closest large U.S. retail Chapter 11 that converted to a liquidation.",
           [TRU_WINDDOWN, TRU_PETITION], "5.9 months (petition to liquidation decision); distributions follow store-closing sales, so this is a lower bound.")
    add(ws, "C9", round(d["filo_rate"], 4), "modeler_assumption", FRED_SOFR,
        "Discount rate = SOFR 2.96% (2022-09-29) + FILO margin 7.75% = 10.71%, the contracted cash cost of "
        "Bed Bath & Beyond's newest secured debt on the case date.")
    driver(ws, "C9", "undisclosed_term_driver",
           "No discount rate for delayed creditor recoveries is disclosed; the choice of the FILO's contracted "
           "rate as the rate creditors demand for waiting is a modeling judgment, so it is declared rather than "
           "claimed as derived.",
           [FRED_SOFR, FILO_8K],
           "4.71% (SOFR 2.96% + ABL top-tier margin 1.75%) to 10.71% (SOFR 2.96% + FILO margin 7.75%); 10.71% used.")
    add(ws, "D5", round(d["creditor_implied_value"], 1), "derived", TENQ,
        "Going-concern value = the $804.3mm creditor-implied value at 2022-08-27 used in the Recovery "
        "Waterfall (ABL 550.0 + senior notes Level 1 fair value 254.3).")
    add(ws, "D7", round(d["professional_fees"], 3), "modeler_assumption", LOPUCKI_FEES,
        "Reorganization administrative and professional fees = $61.356mm, the LoPucki-Doherty predicted "
        "award (filing through confirmation) for a $4.2bn-asset, non-prepackaged case.")
    driver(ws, "D7", "undisclosed_metric_driver",
           "No Chapter 11 case existed at the case date, so no fee application could exist.",
           [LOPUCKI_FEES], "$52.995mm to $71.036mm (85% interval of the calculator's worked example).")
    add(ws, "D8", 11, "modeler_assumption", FITCH_DURATION,
        "Time to distribution in a reorganization = 11 months, Fitch's median petition-to-confirmation "
        "time for conventional (non-prepackaged) cases confirmed in 2017.")
    driver(ws, "D8", "undisclosed_metric_driver",
           "No plan or restructuring support agreement existed at the case date.",
           [FITCH_DURATION], "7 months (median of 304 cases, 2003-early 2017) to 11 months (conventional cases, 2017); under 10 months for $2bn-$4bn filers.")

    # ---- Cover ------------------------------------------------------------
    drivers.append({
        "sheet": "Cover", "cell": "C6", "driver_type": "generated_metadata",
        "rationale": "Populated from the manifest as_of date, 2022-09-30, which is the EDGAR filing date of the Form 10-Q that supplies this case's latest data.",
        "basis": {"source_name": TENQ["name"], "source_url": TENQ["url"], "range": "Fixed: filing date 2022-09-30 (accession 0000886158-22-000150)."},
        "emitted_by": EMITTED_BY,
    })

    manifest = {
        "schema_version": "1.0",
        "id": CASE_ID,
        "classification": "external_historical_case",
        "counts_toward_M4": False,
        "template": "24_Distressed_Restructuring/_template_RESTRUCTURING.xlsx",
        "output": "24_Distressed_Restructuring/instances/public_bbby_2022_liquidity.xlsx",
        "as_of": AS_OF,
        "scenario": "Downside",
        "cover": {
            "Title:": "Bed Bath & Beyond Inc. (Nasdaq: BBBY) — Distressed / Restructuring Model",
            "Situation type:": "Out-of-court liquidity stress: Bed Bath & Beyond Inc. (Nasdaq: BBBY, CIK 0000886158), fiscal Q2 2022 ended 2022-08-27",
            "Petition/filing date:": "None as of 2022-09-30: no bankruptcy petition had been filed",
            "Refresh cadence:": "Quarterly, on each Form 10-Q / 10-K; this case is frozen at the Q2 FY2022 Form 10-Q filed 2022-09-30",
        },
        "inputs": inputs,
        "sources": [TENQ, Q1_TENQ, XBRL, FILO_8K, UPDATE_8K, TENK_FY21, CREDIT_AGREEMENT, FRED_SOFR,
                    FITCH_DURATION, TRU_PETITION, TRU_WINDDOWN, LOPUCKI_FEES, OUTCOME_SOURCE, SNAPSHOT_SOURCE],
        "refresh": {
            "date": WORK_DATE,
            "trigger": "Source every template input from public disclosures available on or before 2022-09-30",
            "source_snapshot": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
            "what_changed": (
                "Case date moved from 2022-08-27 (period end) to 2022-09-30 (10-Q filing date). Every input "
                "cell sourced as observed, derived, or a declared driver with a named basis. 13-Week "
                "Liquidity C3 corrected from 166.7 (cash including restricted cash) to 135.27 (unrestricted)."
            ),
            "reviewer_notes": (
                "External historical case; human stakeholder approval remains pending. The weekly cash flows "
                "are run-rate drivers pinned to fiscal Q2 2022 operating cash flow, not a company forecast. "
                "The waterfall uses the 2022-08-27 bond-market value of creditor claims; general unsecured "
                "claims (accounts payable $783.681mm, lease rejection claims) have no row in this template "
                "and are not modeled."
            ),
            "next_check": "On source revision, builder change, monitoring breach, or annual review",
        },
        "outcome": {
            "metric": "chapter_11_filing_within_12_months",
            "forecast": 1.0,
            "realized": 1.0,
            "realized_source": "Bed Bath & Beyond Chapter 11 filing, April 23, 2023",
            "status": "recorded",
        },
        "lineage": {
            "source_snapshot": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
            "synthetic_benchmark_inputs_allowed": False,
        },
        "driver_declarations": drivers,
    }

    snapshot: dict[str, Any] = {
        "schema_version": "1.0",
        "model_id": "24",
        "domain": "Distressed & Restructuring",
        "case_id": CASE_ID,
        "case_type": "adversarial",
        "as_of": AS_OF,
        "capture_method": "curated_public_observation",
        "sources": [
            {"name": TENQ["name"], "url": TENQ["url"], "publisher": "U.S. SEC / Bed Bath & Beyond", "filed": "2022-09-30", "captured_values": V["tenq"]},
            {"name": Q1_TENQ["name"], "url": Q1_TENQ["url"], "publisher": "U.S. SEC / Bed Bath & Beyond", "filed": "2022-06-29", "captured_values": V["q1_tenq"]},
            {"name": FILO_8K["name"], "url": FILO_8K["url"], "publisher": "U.S. SEC / Bed Bath & Beyond", "filed": "2022-09-01", "captured_values": V["filo_8k"]},
            {"name": UPDATE_8K["name"], "url": UPDATE_8K["url"], "publisher": "U.S. SEC / Bed Bath & Beyond", "filed": "2022-08-31", "captured_values": V["update_8k"]},
            {"name": TENK_FY21["name"], "url": TENK_FY21["url"], "publisher": "U.S. SEC / Bed Bath & Beyond", "filed": "2022-04-21", "captured_values": V["tenk_fy21"]},
            {"name": CREDIT_AGREEMENT["name"], "url": CREDIT_AGREEMENT["url"], "publisher": "U.S. SEC / Bed Bath & Beyond", "filed": "2021-08-10", "captured_values": V["credit_agreement"]},
            {"name": FRED_SOFR["name"], "url": FRED_SOFR["url"], "publisher": "Federal Reserve Bank of St. Louis / Federal Reserve Bank of New York", "captured_values": V["fred"]},
            {"name": FITCH_DURATION["name"], "url": FITCH_DURATION["url"], "publisher": "CFO.com (reporting Fitch Ratings)", "captured_values": V["fitch"]},
            {"name": TRU_WINDDOWN["name"], "url": TRU_WINDDOWN["url"], "publisher": "U.S. SEC / Toys \"R\" Us", "captured_values": V["tru"]},
            {"name": LOPUCKI_FEES["name"], "url": LOPUCKI_FEES["url"], "publisher": "University of Florida Levin College of Law", "captured_values": V["lopucki"]},
            {"name": OUTCOME_SOURCE["name"], "url": OUTCOME_SOURCE["url"], "publisher": "U.S. SEC / Bed Bath & Beyond", "captured_values": {"chapter_11_filing_date": "2023-04-23"}},
        ],
        "input_overrides": [
            {"sheet": i["sheet"], "cell": i["cell"], "value": i["value"], "kind": i["input_kind"], "source": i["source"]["name"]}
            for i in inputs
        ],
        "series": None,
        "outcome": manifest["outcome"],
        "counts_toward_m4": False,
    }
    snapshot["snapshot_sha256"] = sha256_bytes(canonical_bytes(snapshot))
    return manifest, snapshot


def write_source_register(snapshot: dict[str, Any]) -> None:
    rel = str(SNAPSHOT_PATH.relative_to(ROOT))
    digest = snapshot["snapshot_sha256"]
    rows = [
        (CASE_ID, s["name"], s["publisher"], s["url"], AS_OF, rel, digest, "frozen")
        for s in snapshot["sources"]
    ]
    header = "case_id,source_name,publisher,url,as_of,snapshot,snapshot_sha256,status"
    lines = REGISTER_PATH.read_text(encoding="utf-8").splitlines() if REGISTER_PATH.exists() else [header]
    lines = [line for line in (lines or [header]) if not line.startswith(f"{CASE_ID},")]

    def esc(field: str) -> str:
        return '"' + field.replace('"', '""') + '"' if ("," in field or '"' in field) else field

    for row in rows:
        lines.append(",".join(esc(field) for field in row))
    REGISTER_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-only", action="store_true")
    args = parser.parse_args()
    manifest, snapshot = build()
    if args.print_only:
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        return 0
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_source_register(snapshot)
    print(f"saved {MANIFEST_PATH.relative_to(ROOT)}")
    print(f"saved {REGISTER_PATH.relative_to(ROOT)}")
    print(f"saved {SNAPSHOT_PATH.relative_to(ROOT)}  sha256={snapshot['snapshot_sha256'][:16]}...")
    print(report_sync(CASE_ID, snapshot["snapshot_sha256"]))
    print(f"inputs={len(manifest['inputs'])}, drivers={len(manifest['driver_declarations'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
