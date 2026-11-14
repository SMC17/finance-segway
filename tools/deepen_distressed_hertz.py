"""Deepen the Hertz 2021 Chapter 11 case from filings public on or before 2021-06-30.

The case shipped with one sourced cell out of 98 template inputs: New Money!C5
= 7,500, read off Hertz's FY2021 Form 10-K. That figure is the cash Hertz
*received* on the Effective Date, and the 10-K that reports it was filed on
2022-02-24 -- eight months after the case's as-of date. It was hindsight. This
script replaces it and sources every other input from documents that were on
EDGAR by 2021-06-30.

WHAT THE CASE IS
----------------
The as-of date is 2021-06-30, the Plan's Effective Date. The decision point is
the Bankruptcy Court's confirmation of the Plan on 2021-06-10 (8-K filed
2021-06-16). The newest financial statements public at that point are the
Q1 2021 Form 10-Q (filed 2021-05-07). So:

  * Recovery Waterfall -- Allowed claim amounts per Article III.B of the
    confirmed Plan (Exhibit 2.1 to the 2021-06-16 8-K), the DIP balance from
    the Q1 10-Q, and the equity distribution from the Plan terms reported in
    the 2021-05-14 8-K/A. Every creditor class is paid in full in cash; the
    only Impaired class is Class 11, existing equity.
  * New Money -- the DIP Credit Agreement, the template's own subject
    ("DIP / Rescue Financing"): $1.65bn superpriority delayed-draw term loan,
    LIBOR + 7.25% with a 1.00% floor, matures 2021-12-31.
  * 13-Week Liquidity -- the most recent 13 weeks with disclosed cash flows
    before the case date: Q1 2021 (2021-01-01 to 2021-03-31). Quarterly totals
    from the 10-Q are phased evenly across the 13 weeks; operating
    disbursements are the balancing residual that ties week-13 ending cash to
    the disclosed 2021-03-31 unrestricted cash of $1,087mm.
  * Liquidation vs Reorg -- both columns measured as value available to the
    waterfall classes. The Debtors' own liquidation analysis and valuation
    sit in the Disclosure Statement on the claims agent's site, which returns
    HTTP 403 to automated clients, so the liquidation haircut, Chapter 7 fees,
    disposal time and discount rate are declared drivers, each grounded in a
    named disclosure or statute.

NOTHING HERE IS HAND-TYPED ARITHMETIC
-------------------------------------
Every derived value is computed below from the captured figures in
`FACTS`, and the arithmetic is written into that input's notes.

Usage:
    python tools/deepen_distressed_hertz.py
    python tools/deepen_distressed_hertz.py --print-only
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

try:
    from tools.public_case_index import report_sync
except ModuleNotFoundError:
    from public_case_index import report_sync

ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "distressed-public-hertz-2021-reorganization"
FOLDER = "24_Distressed_Restructuring"
MANIFEST_PATH = ROOT / "standards" / "public_cases" / f"{CASE_ID}.json"
SNAPSHOT_PATH = ROOT / FOLDER / "sources" / "snapshots" / f"{CASE_ID}.json"
REGISTER_PATH = ROOT / FOLDER / "sources" / "source_register.csv"
EMITTED_BY = "tools/deepen_distressed_hertz.py"

AS_OF = "2021-06-30"
SNAPSHOT_REPO_URL = f"repo://{FOLDER}/sources/snapshots/{CASE_ID}.json"

# ---------------------------------------------------------------- sources
# Every source used for an input, with the date it became public. The
# assertion in assert_no_hindsight() refuses any input source filed after
# AS_OF.
SOURCES: dict[str, dict[str, str]] = {
    "q1_10q": {
        "name": "Hertz Global Holdings Q1 2021 Form 10-Q",
        "url": "https://www.sec.gov/Archives/edgar/data/1657853/000165785321000013/htz-20210331.htm",
        "period": "2021-03-31",
        "filed": "2021-05-07",
        "publisher": "U.S. SEC / Hertz Global Holdings, Inc. (CIK 0001657853)",
    },
    "fy20_10k": {
        "name": "Hertz Global Holdings 2020 Form 10-K",
        "url": "https://www.sec.gov/Archives/edgar/data/1657853/000165785321000006/htz-20201231.htm",
        "period": "2020-12-31",
        "filed": "2021-02-26",
        "publisher": "U.S. SEC / Hertz Global Holdings, Inc. (CIK 0001657853)",
    },
    "dip_8k": {
        "name": "Hertz Form 8-K: DIP Credit Agreement (Item 1.01)",
        "url": "https://www.sec.gov/Archives/edgar/data/1657853/000165785320000106/htz-20201030.htm",
        "period": "2020-10-30",
        "filed": "2020-11-03",
        "publisher": "U.S. SEC / Hertz Global Holdings, Inc. (CIK 0001657853)",
    },
    "plan_8ka": {
        "name": "Hertz Form 8-K/A: Plan Sponsor selection and Proposed Plan terms",
        "url": "https://www.sec.gov/Archives/edgar/data/1657853/000110465921066944/tm2116104d2_8k.htm",
        "period": "2021-05-11",
        "filed": "2021-05-14",
        "publisher": "U.S. SEC / Hertz Global Holdings, Inc. (CIK 0001657853)",
    },
    "confirmation_8k": {
        "name": "Hertz Form 8-K: Plan confirmation (Item 1.03)",
        "url": "https://www.sec.gov/Archives/edgar/data/1657853/000110465921081986/tm2119738d1_8k.htm",
        "period": "2021-06-10",
        "filed": "2021-06-16",
        "publisher": "U.S. SEC / Hertz Global Holdings, Inc. (CIK 0001657853)",
    },
    "plan": {
        "name": "Second Modified Third Amended Joint Chapter 11 Plan of Reorganization (Exhibit 2.1 to the 2021-06-16 Form 8-K)",
        "url": "https://www.sec.gov/Archives/edgar/data/1657853/000110465921081986/tm2119738d1_ex2-1.htm",
        "period": "2021-06-10",
        "filed": "2021-06-16",
        "publisher": "U.S. SEC / Hertz Global Holdings, Inc. (CIK 0001657853)",
    },
    "usc_326": {
        "name": "11 U.S.C. 326(a), limitation on compensation of a Chapter 7 trustee",
        "url": "https://www.law.cornell.edu/uscode/text/11/326",
        "period": "2021-06-10",
        "filed": "1994-10-22",
        "publisher": "U.S. Code (Legal Information Institute)",
    },
}

# Outcome-only source. Read for the realized outcome; never used for an input.
OUTCOME_SOURCE = {
    "name": "Hertz 2021 Form 10-K",
    "url": "https://www.sec.gov/Archives/edgar/data/1657853/000165785322000012/htz-20211231.htm",
    "filed": "2022-02-24",
}

# ------------------------------------------------------------------ facts
# Figures as printed in the filings, in USD millions unless the key says
# otherwise. Each carries the source key and the place in the filing.
FACTS: dict[str, tuple[Any, str, str]] = {
    # Recovery Waterfall
    "dip_outstanding_usd_mm": (750.0, "q1_10q", "Note 6 debt table, DIP Credit Agreement, 2021-03-31"),
    "first_lien_allowed_usd": (1_271_932_486.00, "plan", "Art. III.B.3(b), Class 3 First Lien Claims allowed amount"),
    "second_lien_allowed_usd": (362_750_694.00, "plan", "Art. III.B.4(b), Class 4 Second Lien Note Claims allowed amount"),
    "notes_5500_allowed_usd": (804_522_222.00, "plan", "Art. III.B.5(b)(i), 5.500% Unsecured Note Claims"),
    "notes_6000_allowed_usd": (926_700_000.00, "plan", "Art. III.B.5(b)(i), 6.000% Unsecured Note Claims"),
    "notes_6250_allowed_usd": (503_211_806.00, "plan", "Art. III.B.5(b)(i), 6.250% Unsecured Note Claims"),
    "notes_7125_allowed_usd": (511_083_333.00, "plan", "Art. III.B.5(b)(i), 7.125% Unsecured Note Claims"),
    "equity_cash_per_share_usd": (1.53, "plan", "Art. III.B.11(b)(i), Class 11: Cash in an amount equal to $1.53 per share of Existing Hertz Parent Interests"),
    "equity_new_common_share": (0.03, "plan_8ka", "Proposed Plan: common stock representing 3% of the reorganized Company"),
    "plan_equity_value_usd_mm": (4700.0, "plan_8ka", "Rights Offering and sponsor price based on an equity value of approximately $4.7 billion"),
    # New Money (DIP Credit Agreement)
    "dip_commitment_usd_mm": (1650.0, "dip_8k", "delayed-draw term loans in an aggregate amount of up to $1.65 billion"),
    "dip_rate": (0.0825, "q1_10q", "Note 6, DIP weighted-average interest rate 8.25% at 2021-03-31 (LIBOR + 7.25%, 1.00% floor per the 2020-11-03 8-K)"),
    "dip_closing_date": ("2020-10-30", "dip_8k", "DIP Credit Agreement entered into on October 30, 2020"),
    "dip_maturity_date": ("2021-12-31", "dip_8k", "The DIP Facility matures on December 31, 2021"),
    "non_vehicle_unamortized_costs_usd_mm": (26.0, "q1_10q", "Note 6, unamortized debt issuance costs on non-vehicle debt not subject to compromise, 2021-03-31"),
    # 13-Week Liquidity (Q1 2021)
    "unrestricted_cash_2020_12_31_usd_mm": (1096.0, "q1_10q", "Balance sheet, cash and cash equivalents, 2020-12-31"),
    "unrestricted_cash_2021_03_31_usd_mm": (1087.0, "q1_10q", "Balance sheet, cash and cash equivalents, 2021-03-31"),
    "dip_min_liquidity_usd_mm": (275.0, "q1_10q", "Note 6, DIP liquidity maintenance test of $275 million"),
    "q1_2021_total_revenues_usd_mm": (1289.0, "q1_10q", "Statement of operations, total revenues, three months ended 2021-03-31"),
    "q1_2021_interest_paid_vehicle_usd_mm": (69.0, "q1_10q", "Cash flow supplemental, interest paid, vehicle"),
    "q1_2021_interest_paid_non_vehicle_usd_mm": (30.0, "q1_10q", "Cash flow supplemental, interest paid, non-vehicle"),
    "q1_2021_reorganization_items_paid_usd_mm": (58.0, "q1_10q", "Note 16, cash payments for reorganization items, three months ended 2021-03-31"),
    "dip_outstanding_2020_12_31_usd_mm": (250.0, "q1_10q", "Note 6 debt table, DIP Credit Agreement, 2020-12-31"),
    "dip_draw_2021_02_16_usd_mm": (250.0, "fy20_10k", "On February 16, 2021, Hertz borrowed an additional $250 million"),
    # Liquidation vs Reorg
    "total_assets_usd_mm": (16610.0, "q1_10q", "Balance sheet, total assets, 2021-03-31"),
    "liabilities_not_subject_to_compromise_usd_mm": (11342.0, "q1_10q", "Balance sheet, total liabilities not subject to compromise, 2021-03-31"),
    "non_vehicle_debt_not_subject_to_compromise_usd_mm": (740.0, "q1_10q", "Note 6, total non-vehicle debt not subject to compromise (DIP 750 + other 16 - costs 26), 2021-03-31"),
    "goodwill_usd_mm": (1045.0, "q1_10q", "Balance sheet, goodwill, 2021-03-31"),
    "intangibles_usd_mm": (2969.0, "q1_10q", "Balance sheet, intangible assets, net, 2021-03-31"),
    "prof_fees_accrued_usd_mm": (57.0, "q1_10q", "Note 16, reorganization charges recorded in accrued liabilities at 2021-03-31"),
    "prof_fees_payable_usd_mm": (7.0, "q1_10q", "Note 16, reorganization charges recorded in accounts payable at 2021-03-31"),
    "revenue_earning_vehicles_net_usd_mm": (6360.0, "q1_10q", "Balance sheet, total revenue earning vehicles, net, 2021-03-31"),
    "fy2020_vehicle_disposal_proceeds_usd_mm": (10098.0, "fy20_10k", "Cash flow statement, proceeds from disposal of revenue earning vehicles, 2020"),
    # Cover and timing
    "petition_date": ("2020-05-22", "confirmation_8k", "On May 22, 2020 (the Petition Date)"),
    "confirmation_date": ("2021-06-10", "confirmation_8k", "On June 10, 2021, the Bankruptcy Court entered the Confirmation Order"),
    "targeted_effective_date": ("2021-06-30", "confirmation_8k", "targeting occurrence of the Effective Date by the end of June 2021"),
    "shares_outstanding": (156_206_478, "confirmation_8k", "156,206,478 shares of existing common stock outstanding as of June 10, 2021"),
}

WEEKS = 13
# Week k of Q1 2021 covers calendar days 7(k-1)+1 .. 7k counted from 2021-01-01;
# 2021-02-16 is day 47, so the disclosed draw falls in week 7.
DISCLOSED_DRAW_WEEK = 7
UNDATED_DRAW_WEEK = 13


def f(key: str) -> Any:
    return FACTS[key][0]


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def assert_no_hindsight() -> None:
    for key, src in SOURCES.items():
        if src["filed"] > AS_OF:
            raise AssertionError(f"source {key} filed {src['filed']} after as-of {AS_OF}")
    for key, (_, src_key, _) in FACTS.items():
        if src_key not in SOURCES:
            raise AssertionError(f"fact {key} cites unknown source {src_key}")


def _source(src_key: str, notes: str) -> dict[str, str]:
    src = SOURCES[src_key]
    return {
        "name": src["name"],
        "url": src["url"],
        "as_of": src["period"],
        "notes": f"Filed {src['filed']}. {notes}",
    }


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    assert_no_hindsight()
    existing = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    inputs: list[dict[str, Any]] = []
    drivers: list[dict[str, Any]] = []

    def emit(sheet: str, cell: str, value: Any, kind: str, src_key: str, note: str) -> None:
        if kind not in {"observed", "derived", "modeler_assumption"}:
            raise ValueError(kind)
        inputs.append({
            "sheet": sheet, "cell": cell, "value": value, "input_kind": kind,
            "source": _source(src_key, note), "emitted_by": EMITTED_BY,
        })

    def driver(sheet: str, cell: str, value: Any, driver_type: str, src_key: str,
               rationale: str, basis_note: str) -> None:
        src = SOURCES[src_key]
        emit(sheet, cell, value, "modeler_assumption", src_key, f"Declared driver. {rationale} Basis: {basis_note}")
        drivers.append({
            "sheet": sheet, "cell": cell, "driver_type": driver_type,
            "rationale": rationale,
            "basis": {"source_name": src["name"], "source_url": src["url"],
                      "as_of": src["period"], "note": basis_note},
            "emitted_by": EMITTED_BY,
        })

    # ------------------------------------------------ Recovery Waterfall
    dip = f("dip_outstanding_usd_mm")
    first_lien = round(f("first_lien_allowed_usd") / 1e6, 6)
    second_lien = round(f("second_lien_allowed_usd") / 1e6, 6)
    notes_keys = ["notes_5500_allowed_usd", "notes_6000_allowed_usd", "notes_6250_allowed_usd", "notes_7125_allowed_usd"]
    unsecured = round(sum(f(k) for k in notes_keys) / 1e6, 6)
    equity_stock = f("equity_new_common_share") * f("plan_equity_value_usd_mm")
    equity_cash = round(f("equity_cash_per_share_usd") * f("shares_outstanding") / 1e6, 6)
    equity = round(equity_cash + equity_stock, 6)
    distributable = round(dip + first_lien + second_lien + unsecured + 0.0 + equity, 6)

    rw = "Recovery Waterfall"
    emit(rw, "C5", dip, "observed", "q1_10q",
         "DIP / super-priority face claim: Senior Secured Superpriority Debtor-in-Possession Credit Agreement "
         "principal outstanding at 2021-03-31, $750mm (latest balance public before the as-of date). USD millions.")
    emit(rw, "C6", first_lien, "observed", "plan",
         "Class 3 First Lien Claims (Senior Term Loan and Senior RCF) Allowed in the amount of $1,271,932,486.00 "
         "per Plan Art. III.B.3(b), before the Donlen paydown, post-petition LC draws, hedge claims and accrued "
         "interest the Plan adds to render the class Unimpaired. USD millions.")
    emit(rw, "C7", second_lien, "observed", "plan",
         "Class 4 Second Lien Note Claims (7.625% Senior Second Priority Secured Notes) Allowed in the amount of "
         "$362,750,694.00 per Plan Art. III.B.4(b), before post-petition interest. USD millions.")
    emit(rw, "C8", unsecured, "derived", "plan",
         "Class 5 Unsecured Note Claims, sum of the four Allowed amounts in Plan Art. III.B.5(b)(i): "
         "804,522,222 (5.500%) + 926,700,000 (6.000%) + 503,211,806 (6.250%) + 511,083,333 (7.125%) = "
         f"{sum(f(k) for k in notes_keys):,.0f} USD = {unsecured} USD millions. Excludes the ALOC Facility claims in the same "
         "class, which the Plan leaves to the Court to fix (drawn $142mm at 2021-03-31 per the Q1 10-Q), the "
         "$790.1mm HHN Notes guarantee claims (Class 6, paid by the issuer), and the $28.3mm 7.000% Unsecured "
         "Promissory Notes (Class 7 general unsecured).")
    emit(rw, "C9", 0.0, "observed", "plan",
         "Subordinated debt: the Plan's classification table (Art. III.A) has no subordinated debt class; the Q1 "
         "2021 10-Q debt table lists no subordinated instrument. USD millions.")
    emit(rw, "C10", equity, "derived", "plan",
         f"Class 11 Existing Hertz Parent Interests, the Plan's only Impaired class. Distribution value = cash of "
         f"$1.53 per share (confirmed Plan Art. III.B.11(b)(i)) x 156,206,478 shares outstanding at 2021-06-10 "
         f"(2021-06-16 8-K) = {equity_cash} USD millions, + 3% of reorganized common (Plan Art. III.B.11(b)(ii)) "
         f"at the equity value of approximately $4,700mm on which the Rights Offering is priced (2021-05-14 8-K/A; "
         f"0.03 x 4,700 = {equity_stock:.0f}) = {equity} USD millions. The 30-year warrants (18% at a $6.5bn strike) or the "
         "alternative Rights Offering participation carry option value that is not disclosed and is excluded.")
    emit(rw, "C12", distributable, "derived", "plan",
         f"Plan distributable value to the six modeled classes = {dip} + {first_lien} + {second_lien} + {unsecured} + 0 + "
         f"{equity} = {distributable} USD millions. Every creditor class is paid in full in cash under Plan Art. "
         "III.B, so the value distributed equals the sum of the modeled claims plus equity's distribution. This is "
         "the Plan's distribution, not an independent enterprise valuation: the Debtors' valuation analysis sits in "
         "the Disclosure Statement on the claims agent site, which returns HTTP 403 to automated clients.")
    for cell, rank, what in [("D5", 1, "DIP Claims are superpriority administrative claims (Plan Art. II.B; DIP Credit Agreement, 2020-11-03 8-K)"),
                             ("D6", 2, "Class 3 First Lien Claims"),
                             ("D7", 3, "Class 4 Second Lien Note Claims"),
                             ("D8", 4, "Class 5 Unsecured Funded Debt Claims"),
                             ("D10", 6, "Class 11 Existing Hertz Parent Interests, junior to every Claim")]:
        emit(rw, cell, rank, "observed", "plan",
             f"Seniority rank {rank}: {what}. Order follows the Plan's classification and the absolute priority of "
             "secured, unsecured and equity interests.")
    driver(rw, "D9", 5, "presentation_convention", "plan",
           "Seniority rank of the subordinated debt row. Hertz has no subordinated debt class, so the rank is the "
           "template's positional slot between unsecured claims and equity, not a fact about Hertz.",
           "Plan Art. III.A classification table: no subordinated debt class exists; the row carries a zero claim.")

    # ------------------------------------------------------- New Money
    nm = "New Money"
    emit(nm, "C5", f("dip_commitment_usd_mm"), "observed", "dip_8k",
         "DIP Credit Agreement commitment: superpriority secured delayed-draw term loans of up to $1.65 billion "
         "($1.0bn for interim fleet financing equity, $800mm for working capital). USD millions. Replaces the "
         "earlier 7,500 read off the FY2021 10-K (filed 2022-02-24), which was hindsight for a 2021-06-30 case.")
    upfront = round(f("non_vehicle_unamortized_costs_usd_mm") / f("dip_outstanding_usd_mm"), 6)
    driver(nm, "C7", upfront, "undisclosed_term_driver", "q1_10q",
           "Upfront fee as a share of drawn amount. The DIP fee letter is not on EDGAR; the credit agreement is on "
           "the claims agent site (HTTP 403). The value is the unamortized issuance cost on non-vehicle debt not "
           "subject to compromise divided by DIP principal drawn, both at 2021-03-31: 26 / 750.",
           "Q1 2021 10-Q Note 6: unamortized debt issuance costs (26) against DIP principal 750; attributing the "
           "whole 26 to the DIP is the assumption.")
    emit(nm, "C8", f("dip_rate"), "observed", "q1_10q",
         "DIP cash interest rate: 8.25% weighted-average rate at 2021-03-31 per Note 6, equal to the contractual "
         "LIBOR + 7.25% with a 1.00% LIBOR floor disclosed in the 2020-11-03 8-K.")
    days = (date.fromisoformat(f("dip_maturity_date")) - date.fromisoformat(f("dip_closing_date"))).days
    tenor = round(days / 365.0, 6)
    emit(nm, "C9", tenor, "derived", "dip_8k",
         f"DIP tenor in years: closing 2020-10-30 to maturity 2021-12-31 = {days} days / 365 = {tenor}.")
    driver(nm, "C10", 0.0, "undisclosed_term_driver", "dip_8k",
           "Exit fee. The 8-K summary of DIP economics discloses rate, floor, step-down, maturity and draw size and "
           "names no exit fee; the credit agreement that would confirm it is not reachable. Held at zero.",
           "2020-11-03 8-K Item 1.01 summary of DIP Credit Agreement terms lists no exit or prepayment fee.")
    emit(nm, "C11", 1.0, "observed", "dip_8k",
         "Super-priority multiple 1.0x: the DIP is a superpriority secured facility with first priority liens on "
         "substantially all Debtor assets, consensual priming of the first-lien debt, and no roll-up.")

    # ------------------------------------------------ 13-Week Liquidity
    lq = "13-Week Liquidity"
    emit(lq, "C3", f("unrestricted_cash_2020_12_31_usd_mm"), "observed", "q1_10q",
         "Initial unrestricted liquidity: Hertz Global consolidated cash and cash equivalents (unrestricted) at "
         "2020-12-31, the opening of the 13-week window Q1 2021. Excludes $411mm restricted cash and DIP "
         "availability. USD millions.")
    emit(lq, "C4", f("dip_min_liquidity_usd_mm"), "observed", "q1_10q",
         "Minimum operating liquidity: the DIP Credit Agreement's $275mm month-end liquidity maintenance test. "
         "USD millions.")
    receipts = round(f("q1_2021_total_revenues_usd_mm") / WEEKS, 6)
    interest_total = f("q1_2021_interest_paid_vehicle_usd_mm") + f("q1_2021_interest_paid_non_vehicle_usd_mm")
    interest = round(interest_total / WEEKS, 6)
    fees = round(f("q1_2021_reorganization_items_paid_usd_mm") / WEEKS, 6)
    q1_draws = f("dip_outstanding_usd_mm") - f("dip_outstanding_2020_12_31_usd_mm")
    undated_draw = q1_draws - f("dip_draw_2021_02_16_usd_mm")
    change = f("unrestricted_cash_2021_03_31_usd_mm") - f("unrestricted_cash_2020_12_31_usd_mm")
    disb_total = f("q1_2021_total_revenues_usd_mm") - interest_total - f("q1_2021_reorganization_items_paid_usd_mm") + q1_draws - change
    disb = round(disb_total / WEEKS, 6)
    for week in range(1, WEEKS + 1):
        row = 6 + week
        emit(lq, f"D{row}", receipts, "derived", "q1_10q",
             f"Week {week} receipts: Q1 2021 total revenues 1,289 / 13 = {receipts}. Revenue stands in for cash "
             "receipts; weekly phasing is not disclosed and is spread evenly. USD millions.")
        emit(lq, f"E{row}", disb, "derived", "q1_10q",
             f"Week {week} operating disbursements, the balancing residual that ties week-13 ending cash to the "
             f"disclosed 2021-03-31 unrestricted cash: (revenues 1,289 - interest paid 99 - reorganization items "
             f"paid 58 + DIP draws {q1_draws:.0f} - change in unrestricted cash ({change:.0f})) / 13 = "
             f"{disb_total:.0f} / 13 = {disb}. Includes every other use of unrestricted cash in the quarter, "
             "fleet equity funding and transfers to restricted cash among them. USD millions.")
        emit(lq, f"F{row}", interest, "derived", "q1_10q",
             f"Week {week} interest: Q1 2021 cash interest paid, vehicle 69 + non-vehicle 30 = 99, / 13 = {interest}. "
             "USD millions.")
        emit(lq, f"G{row}", fees, "derived", "q1_10q",
             f"Week {week} professional fees: Q1 2021 cash paid for reorganization items, primarily professional "
             f"fees, 58 / 13 = {fees}. USD millions.")
        if week == DISCLOSED_DRAW_WEEK:
            emit(lq, f"H{row}", f("dip_draw_2021_02_16_usd_mm"), "observed", "fy20_10k",
                 "Week 7 (2021-02-12 to 2021-02-18) new money: the $250mm DIP draw made on 2021-02-16. USD millions.")
        elif week == UNDATED_DRAW_WEEK:
            driver(lq, f"H{row}", undated_draw, "undisclosed_metric_driver", "q1_10q",
                   f"Week 13 new money: the second Q1 DIP draw. DIP principal rose from 250 to 750 in Q1 2021, so "
                   f"draws totaled 500; 250 is dated 2021-02-16, leaving {undated_draw:.0f} whose date is not "
                   "disclosed. Placed in the last week, the latest date consistent with the 2021-03-31 balance, "
                   "which gives the lowest interim cash path.",
                   "Q1 2021 10-Q Note 6: DIP principal 250 at 2020-12-31 and 750 at 2021-03-31; 2020 10-K: $250mm drawn 2021-02-16.")
        else:
            driver(lq, f"H{row}", 0.0, "undisclosed_metric_driver", "q1_10q",
                   f"Week {week} new money held at zero. Q1 DIP draws total 500: 250 dated 2021-02-16 (week 7) and "
                   "250 undated, placed in week 13.",
                   "Q1 2021 10-Q Note 6: DIP principal 250 at 2020-12-31 and 750 at 2021-03-31.")

    # --------------------------------------------- Liquidation vs Reorg
    lr = "Liquidation vs Reorg"
    book_available = f("total_assets_usd_mm") - (f("liabilities_not_subject_to_compromise_usd_mm") - f("non_vehicle_debt_not_subject_to_compromise_usd_mm"))
    emit(lr, "C5", book_available, "derived", "q1_10q",
         f"Liquidation gross asset value: book assets available to the waterfall classes at 2021-03-31 = total "
         f"assets 16,610 - (liabilities not subject to compromise 11,342 - non-vehicle debt not subject to "
         f"compromise 740, which is the DIP, a waterfall class) = {book_available:.0f}. Vehicle ABS debt, "
         "operating leases and other non-compromised liabilities are netted first because their collateral or "
         "claims rank outside the modeled classes. USD millions.")
    emit(lr, "D5", distributable, "derived", "plan",
         f"Reorganization value to the same classes: the Plan distributable value from Recovery Waterfall!C12, "
         f"{distributable} USD millions.")
    haircut = f("goodwill_usd_mm") + f("intangibles_usd_mm")
    driver(lr, "C6", haircut, "undisclosed_metric_driver", "q1_10q",
           f"Liquidation discount: goodwill 1,045 + intangible assets 2,969 = {haircut:.0f}, assumed to realize "
           "nothing in a Chapter 7 while tangible assets realize book. The Debtors' own liquidation analysis is in "
           "the Disclosure Statement, which is not reachable (HTTP 403).",
           "Q1 2021 10-Q balance sheet at 2021-03-31: goodwill 1,045 and intangible assets, net 2,969.")
    net_before_fees = book_available - haircut
    trustee = (0.25 * 5_000 + 0.10 * 45_000 + 0.05 * 950_000 + 0.03 * (net_before_fees * 1e6 - 1_000_000)) / 1e6
    trustee = round(trustee, 6)
    driver(lr, "C7", trustee, "undisclosed_metric_driver", "usc_326",
           f"Chapter 7 administrative fees: the statutory maximum trustee compensation under 11 U.S.C. 326(a) "
           f"(25% of the first $5,000, 10% of the next $45,000, 5% of the next $950,000, 3% above $1,000,000) on "
           f"distributions of {net_before_fees:.0f} USD millions = {trustee}. Trustee professionals' fees would add "
           "to this and are not estimated, so the figure is a floor.",
           "11 U.S.C. 326(a) fee schedule applied to C5 - C6.")
    emit(lr, "D7", f("prof_fees_accrued_usd_mm") + f("prof_fees_payable_usd_mm"), "derived", "q1_10q",
         "Reorganization professional fees still to be paid: reorganization charges unpaid at 2021-03-31, 57 in "
         "accrued liabilities + 7 in accounts payable = 64. Fees incurred after 2021-03-31 are not yet disclosed "
         "at the as-of date. USD millions.")
    months = round(f("revenue_earning_vehicles_net_usd_mm") / (f("fy2020_vehicle_disposal_proceeds_usd_mm") / 12.0), 6)
    driver(lr, "C8", months, "undisclosed_metric_driver", "fy20_10k",
           f"Chapter 7 time to distribution: the months needed to sell the 2021-03-31 fleet (net book 6,360) at "
           f"Hertz's own 2020 disposal pace (proceeds 10,098 / 12 = 841.5 a month) = {months}. 2020 was the year "
           "the Interim Lease Order forced fleet disposals, so it is Hertz's observed stress-sale pace.",
           "2020 Form 10-K cash flow statement (disposal proceeds 10,098) and Q1 2021 10-Q balance sheet (fleet 6,360).")
    eff_days = (date.fromisoformat(f("targeted_effective_date")) - date.fromisoformat(f("confirmation_date"))).days
    reorg_months = round(eff_days / (365.0 / 12.0), 6)
    emit(lr, "D8", reorg_months, "derived", "confirmation_8k",
         f"Reorganization time to distribution: Plan distributions are made on the Effective Date; confirmation "
         f"2021-06-10 to the targeted Effective Date at the end of June 2021 = {eff_days} days / (365/12) = "
         f"{reorg_months} months.")
    driver(lr, "C9", f("dip_rate"), "undisclosed_term_driver", "q1_10q",
           "Discount rate for delayed recovery: the DIP all-in rate of 8.25%, Hertz's own marginal cost of senior "
           "secured financing at 2021-03-31. A creditor's required return on a delayed distribution is not a "
           "disclosure. FRED's ICE BofA high-yield yield series now publish only the trailing three years and "
           "cannot supply a 2021 value.",
           "Q1 2021 10-Q Note 6: DIP weighted-average interest rate 8.25% at 2021-03-31.")

    # ----------------------------------------------------------- Cover
    cover = {
        "Title:": "Hertz Global Holdings, Inc. — Distressed / Restructuring Model",
        "Situation type:": (
            "Chapter 11, In re The Hertz Corporation, et al., Case No. 20-11218 (MFW), Bankr. D. Del.; "
            "Plan confirmed 2021-06-10, emergence financing and recoveries"
        ),
        "Petition/filing date:": f("petition_date"),
        "Refresh cadence:": (
            "None scheduled: closed historical case, refreshed only on source revision or builder change"
        ),
    }
    drivers.append({
        "sheet": "Cover", "cell": "C6", "driver_type": "generated_metadata",
        "rationale": "Last refreshed: written from the manifest as_of (2021-06-30), the Plan's targeted Effective Date.",
        "basis": {"source_name": SOURCES["confirmation_8k"]["name"],
                  "source_url": SOURCES["confirmation_8k"]["url"],
                  "as_of": AS_OF,
                  "note": "The as-of date is the Effective Date the Debtors targeted in the confirmation 8-K."},
        "emitted_by": EMITTED_BY,
    })

    # -------------------------------------------------------- snapshot
    snapshot_existing = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    snapshot = {
        **snapshot_existing,
        "capture_method": "curated_public_observation_from_edgar_filings_public_by_as_of",
        "sources": [
            {
                "name": src["name"], "url": src["url"], "publisher": src["publisher"],
                "period": src["period"], "filed": src["filed"],
                "captured_values": {
                    key: {"value": value, "where": where}
                    for key, (value, src_key, where) in FACTS.items() if src_key == skey
                },
            }
            for skey, src in SOURCES.items()
        ],
        "input_overrides": [
            {"sheet": i["sheet"], "cell": i["cell"], "value": i["value"], "kind": i["input_kind"],
             "source": i["source"]["name"]}
            for i in inputs
        ],
        "hindsight_policy": (
            f"Every input source was filed on or before {AS_OF}. The FY2021 Form 10-K (filed "
            f"{OUTCOME_SOURCE['filed']}) is used only for the realized outcome."
        ),
        "unreachable_sources": {
            "note": "Primary documents that would source the declared drivers but refused automated retrieval.",
            "items": [
                "Disclosure Statement (valuation analysis and liquidation analysis) -- restructuring.primeclerk.com/hertz, HTTP 403",
                "DIP Credit Agreement and fee letter -- restructuring.primeclerk.com/hertz, HTTP 403",
                "Monthly operating reports (weekly cash detail) -- restructuring.primeclerk.com/hertz, HTTP 403",
                "CourtListener RECAP docket 20-11218 -- HTTP 403",
            ],
        },
    }
    snapshot.pop("snapshot_sha256", None)
    snapshot["snapshot_sha256"] = hashlib.sha256(canonical_bytes(snapshot)).hexdigest()

    manifest_sources = [
        {"name": src["name"], "url": src["url"], "as_of": src["period"],
         "notes": f"Filed {src['filed']}. {src['publisher']}."}
        for src in SOURCES.values()
    ]
    manifest_sources.append({
        "name": OUTCOME_SOURCE["name"], "url": OUTCOME_SOURCE["url"], "as_of": "2021-12-31",
        "notes": f"Filed {OUTCOME_SOURCE['filed']}. Realized outcome only (emergence completed); no input is read from it.",
    })
    manifest_sources.append({
        "name": "Frozen source snapshot", "url": SNAPSHOT_REPO_URL, "as_of": AS_OF,
        "notes": "Immutable curated observation package with SHA-256 digest",
    })

    manifest = {
        **existing,
        "cover": cover,
        "inputs": inputs,
        "sources": manifest_sources,
        "refresh": {
            "date": date.today().isoformat(),
            "trigger": "Depth pass: source every template input from filings public by the as-of date",
            "source_snapshot": SNAPSHOT_REPO_URL,
            "what_changed": (
                "Sourced the capital structure from the Allowed claim amounts in the confirmed Plan, the DIP terms "
                "from the 2020-11-03 8-K and the Q1 2021 10-Q, the 13-week cash schedule from Q1 2021 actuals, and "
                "the liquidation comparison from the Q1 2021 balance sheet. Replaced New Money!C5 = 7,500, which was "
                "read off the FY2021 10-K filed 2022-02-24 and was hindsight for a 2021-06-30 case, with the "
                "$1,650mm DIP commitment. Filled every Cover field."
            ),
            "reviewer_notes": (
                "External historical case; human stakeholder approval remains pending. The waterfall's distributable "
                "value is the Plan's distribution, not an independent valuation, so recoveries are 100% by "
                "construction. Twenty cells are declared drivers grounded in named filings or statute because the "
                "Disclosure Statement, DIP fee letter and monthly operating reports are on a site that refuses "
                "automated retrieval."
            ),
            "next_check": "On source revision, builder change, or annual review",
        },
        "driver_declarations": drivers,
    }
    return manifest, snapshot


def write_source_register(snapshot: dict[str, Any]) -> None:
    rows = [
        (CASE_ID, src["name"], src["publisher"], src["url"], src["period"],
         str(SNAPSHOT_PATH.relative_to(ROOT)), snapshot["snapshot_sha256"], "frozen")
        for src in SOURCES.values()
    ]
    header = "case_id,source_name,publisher,url,as_of,snapshot,snapshot_sha256,status"
    lines = [header]
    if REGISTER_PATH.exists():
        existing = REGISTER_PATH.read_text(encoding="utf-8").splitlines()
        lines = [line for line in (existing or lines) if not line.startswith(f"{CASE_ID},")]
    for row in rows:
        lines.append(",".join(f'"{x}"' if "," in str(x) else str(x) for x in row))
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
    print(report_sync(CASE_ID, snapshot["snapshot_sha256"]))
    print(f"inputs={len(manifest['inputs'])} drivers={len(manifest['driver_declarations'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
