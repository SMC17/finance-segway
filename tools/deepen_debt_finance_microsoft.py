"""Deepen the Microsoft FY2024 debt-finance case from recorded SEC XBRL facts.

The case shipped with four sourced cells out of 102 candidates -- 4.9% real,
the thinnest case in the repository. Everything else in the workbook was a
generic template default sized for a leveraged mid-cap: a 5.5x maximum
leverage covenant, a 5.5% senior-notes coupon, a $300mm term loan. None of
that is Microsoft, and a reader opening the workbook would see those numbers
sitting in blue input cells with no indication they were placeholders.

This script rebuilds the case from the committed XBRL snapshot
(tools/data_fabric/out/MSFT_facts_annual_series.json) plus the four values
already frozen in the case's own source snapshot. Nothing is typed by hand.

WHAT IS AND IS NOT SOURCEABLE HERE
----------------------------------
Microsoft's XBRL facts carry the debt *balances* (LongTermDebt, its
current/non-current split, commercial paper) and interest expense, but not
the instrument-level detail a debt model wants: no per-tranche coupons, no
maturity ladder by year beyond the current portion, no revolver commitment
size, and no covenant thresholds -- Microsoft is investment grade and has no
maintenance covenants to disclose. Those live in the 10-K debt note as
tabular HTML, not as tagged facts.

So the same discipline as the Adobe case applies: where a component is
undisclosed but an aggregate of it is disclosed, the component stays a
declared driver and the aggregate is pinned by solving one cell for it.
Three aggregates are pinned here:

  - The capital structure sums EXACTLY to the disclosed ending debt of
    $67,127mm. Commercial paper and long-term debt are read off XBRL; "other
    debt" (finance leases and similar, which Microsoft does not tag in this
    fact set) is the residual that makes the total tie.
  - Cash interest ties to the disclosed InterestExpense of $2,935mm. The
    senior-notes coupon is solved for, so the model's interest burden is the
    real one rather than a coupon someone picked.
  - The weighted cost of debt on the refinancing sheet ties to the same
    interest expense over average debt. The second tranche's rate carries
    that constraint.

TWO CAVEATS STATED RATHER THAN BURIED
-------------------------------------
1. EBITDA. Microsoft tags no DepreciationDepletionAndAmortization concept in
   this fact set, so EBITDA cannot be derived. The model uses EBIT
   (OperatingIncomeLoss) instead. This is deliberately the conservative
   direction: EBIT understates EBITDA, which understates interest coverage
   and overstates leverage. The case therefore makes Microsoft's credit look
   worse than it is, never better.

2. Debt definition. The disclosed ending debt of $67,127mm is broader than
   the XBRL LongTermDebt tag ($44,937mm) because it includes finance leases
   and other borrowings Microsoft reports outside that concept. Both numbers
   are real and they measure different things; the case uses the broader
   disclosed total for the capital structure and says so on every affected
   cell rather than quietly reconciling them.

Usage:
    python tools/deepen_debt_finance_microsoft.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / "tools" / "data_fabric" / "out" / "MSFT_facts_annual_series.json"
CASE_ID = "debt-public-microsoft-2024"
MODEL_ID = "06"
FOLDER = "06_Debt_Finance"
MANIFEST_PATH = ROOT / "standards" / "public_cases" / f"{CASE_ID}.json"
SNAPSHOT_PATH = ROOT / FOLDER / "sources" / "snapshots" / f"{CASE_ID}.json"
REGISTER_PATH = ROOT / FOLDER / "sources" / "source_register.csv"

FY = "2024-06-30"
# Three-year window. The adversarial column is the least favourable of these
# rather than an invented stress: Microsoft's own worst recent year.
WINDOW = ["2024-06-30", "2023-06-30", "2022-06-30"]

TEN_K_URL = (
    "https://www.sec.gov/Archives/edgar/data/789019/000095017024087843/msft-20240630.htm"
)
TEN_K_NAME = "Microsoft 2024 Form 10-K"
XBRL_NAME = "Microsoft FY2024 XBRL company facts (CIK 0000789019)"
XBRL_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json"
AS_OF = "2024-06-30"

# Values already frozen in this case's own committed snapshot, read off the
# FY2024 10-K's cash-flow and liquidity disclosures. Re-read from disk rather
# than retyped so the two artifacts cannot drift apart.
FROZEN_KEYS = (
    "ending_debt_usd_mm",
    "derived_opening_debt_usd_mm",
    "debt_issued_usd_mm",
    "debt_repaid_usd_mm",
    "cash_and_short_term_investments_usd_mm",
    "operating_cash_flow_usd_mm",
    "capital_expenditures_usd_mm",
)

# Terms with no disclosure anywhere in the XBRL fact set. Held in one place so
# the split between "sourced" and "chosen" is a readable list.
UNGROUNDED = {
    "base_rate": 0.0533,          # feeds term-loan pricing only; MSFT has none
    "revolver_spread": 0.0500,    # commercial-paper all-in cost
    "term_loan_spread": 0.0150,
    "new_issue_spread": 0.0090,
    "oid_fees": 0.0035,
    "minimum_cash": 10000.0,
    "max_leverage": 3.00,
    "min_interest_coverage": 8.00,
    "recovery_multiple": 12.00,
    "ev_haircut": 0.35,
    "committed_lines": 15000.0,
    "max_maturity_concentration": 0.40,
    "max_weighted_cost": 0.0600,
    "tranche1_rate": 0.0350,
}


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def load_xbrl() -> dict[str, dict[str, float]]:
    if not FACTS.exists():
        raise FileNotFoundError(
            f"missing recorded snapshot {FACTS.relative_to(ROOT)} -- this case is "
            "only ever built from committed real data"
        )
    payload = json.loads(FACTS.read_text(encoding="utf-8"))
    return {
        series["concept"]: {
            observation["end"]: observation["value"] / 1e6
            for observation in series["observations"]
        }
        for series in payload["concepts"]
    }


def load_frozen() -> dict[str, float]:
    """The 10-K values this case already had, read back from its snapshot."""
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    captured = snapshot["sources"][0]["captured_values"]
    missing = [key for key in FROZEN_KEYS if key not in captured]
    if missing:
        raise KeyError(f"existing snapshot lost frozen values: {missing}")
    return {key: float(captured[key]) for key in FROZEN_KEYS}


def fact(xbrl: dict[str, dict[str, float]], concept: str, end: str) -> float:
    try:
        return xbrl[concept][end]
    except KeyError as error:
        raise KeyError(f"{concept} not disclosed for {end}") from error


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    xbrl = load_xbrl()
    frozen = load_frozen()

    ending_debt = frozen["ending_debt_usd_mm"]
    opening_debt = frozen["derived_opening_debt_usd_mm"]
    liquidity = frozen["cash_and_short_term_investments_usd_mm"]

    long_term = fact(xbrl, "LongTermDebt", FY)
    long_term_current = fact(xbrl, "LongTermDebtCurrent", FY)
    commercial_paper = fact(xbrl, "CommercialPaper", FY)
    cash = fact(xbrl, "CashAndCashEquivalentsAtCarryingValue", FY)
    ebit = fact(xbrl, "OperatingIncomeLoss", FY)
    interest_expense = fact(xbrl, "InterestExpense", FY)

    # Sanity: the XBRL split must reconcile before anything is derived from it.
    noncurrent = fact(xbrl, "LongTermDebtNoncurrent", FY)
    if abs((noncurrent + long_term_current) - long_term) > 0.5:
        raise ValueError(
            f"XBRL long-term debt split does not reconcile: {noncurrent} + "
            f"{long_term_current} != {long_term}"
        )

    # The residual that ties the capital structure to disclosed total debt.
    other_debt = ending_debt - long_term - commercial_paper
    if other_debt < 0:
        raise ValueError("other-debt residual is negative; debt definitions disagree")

    # Year-1 contractual maturities that are actually disclosed: the current
    # portion of long-term debt plus commercial paper, which by definition
    # matures inside twelve months.
    year1_maturities = long_term_current + commercial_paper

    average_debt = (opening_debt + ending_debt) / 2
    effective_rate = interest_expense / average_debt

    # Solve the senior-notes coupon so Capital Structure cash interest equals
    # the disclosed interest expense. Capital Structure charges the revolver
    # line at the revolver spread and BOTH the notes and other-debt lines at
    # the senior-notes coupon, so:
    #   revolver * revolver_spread + (notes + other) * coupon = interest_expense
    notes_and_other = long_term + other_debt
    coupon = (
        interest_expense - commercial_paper * UNGROUNDED["revolver_spread"]
    ) / notes_and_other
    if not 0 < coupon < 0.20:
        raise ValueError(f"solved coupon {coupon} is implausible; check the pin")

    # Solve tranche 2's rate so the refinancing sheet's weighted cost equals
    # the same disclosed effective rate.
    tranche1 = long_term
    tranche2 = ending_debt - long_term
    tranche2_rate = (
        effective_rate * (tranche1 + tranche2) - tranche1 * UNGROUNDED["tranche1_rate"]
    ) / tranche2
    if not 0 < tranche2_rate < 0.30:
        raise ValueError(f"solved tranche-2 rate {tranche2_rate} is implausible")

    # Adversarial column: Microsoft's own least favourable year in the window.
    worst_ebit = min(fact(xbrl, "OperatingIncomeLoss", end) for end in WINDOW)
    worst_cash = min(
        fact(xbrl, "CashAndCashEquivalentsAtCarryingValue", end) for end in WINDOW
    )
    worst_long_term = max(fact(xbrl, "LongTermDebt", end) for end in WINDOW)
    worst_rate = max(
        fact(xbrl, "InterestExpense", end) / fact(xbrl, "LongTermDebt", end)
        for end in WINDOW
    )

    window_label = ", ".join(f"FY{end[:4]}" for end in WINDOW)
    ebit_caveat = (
        "EBIT (us-gaap:OperatingIncomeLoss), NOT EBITDA. Microsoft tags no "
        "DepreciationDepletionAndAmortization concept in this fact set, so EBITDA "
        "cannot be derived from it. EBIT is used as a conservative lower bound: it "
        "understates EBITDA, which understates interest coverage and overstates "
        "leverage, so the case errs toward making Microsoft's credit look worse "
        "than it is, never better."
    )
    debt_caveat = (
        f"Disclosed total debt of {ending_debt:,.0f} $mm is BROADER than the XBRL "
        f"LongTermDebt tag ({long_term:,.0f} $mm): it includes finance leases and "
        "other borrowings Microsoft reports outside that concept. Both figures are "
        "real and measure different things; the capital structure uses the broader "
        "disclosed total so gross debt ties to the filing."
    )

    def observed(text: str) -> tuple[str, str]:
        return ("observed", text)

    def derived(text: str) -> tuple[str, str]:
        return ("derived", text)

    def driver(text: str) -> tuple[str, str]:
        return ("driver", text)

    # (sheet, row, base, adverse, kind, note)
    rows: list[tuple[str, int, float, float, str, str]] = [
        # --- Assumptions -------------------------------------------------
        ("Assumptions", 5, ebit, worst_ebit, *derived(
            f"{ebit_caveat} FY2024 OperatingIncomeLoss = {ebit:,.0f} $mm. Downside is "
            f"the lowest of {window_label} ({worst_ebit:,.0f} $mm)."
        )),
        ("Assumptions", 6, cash, worst_cash, *observed(
            f"us-gaap:CashAndCashEquivalentsAtCarryingValue at {FY} = {cash:,.0f} $mm. "
            "Strict cash and equivalents -- narrower than the liquidity figure on the "
            f"refinancing sheet ({liquidity:,.0f} $mm), which is cash AND short-term "
            f"investments per the 10-K. Downside is the lowest of {window_label}."
        )),
        ("Assumptions", 7, commercial_paper, commercial_paper, *derived(
            f"us-gaap:CommercialPaper at {FY} = {commercial_paper:,.0f} $mm. Mapped to "
            "the template's 'revolver drawn' line because commercial paper is the "
            "short-term borrowing Microsoft actually had outstanding and is the balance "
            "that must be rolled within twelve months; Microsoft's revolving credit "
            "facility itself was undrawn. Labelled here so the line is not misread as "
            "revolver borrowings."
        )),
        ("Assumptions", 8, 0.0, 0.0, *derived(
            "Zero. Microsoft's XBRL debt facts disclose no term-loan instrument -- the "
            "entire long-term balance is tagged under LongTermDebt / "
            "LongTermDebtNoncurrent, consistent with a notes-and-leases capital "
            "structure. The template's $300mm term-loan default is a generic "
            "mid-cap placeholder and is removed."
        )),
        ("Assumptions", 9, long_term, worst_long_term, *derived(
            f"us-gaap:LongTermDebt at {FY} = {long_term:,.0f} $mm, carried on the "
            "senior-notes line because Microsoft's long-term debt is senior unsecured "
            f"notes. Downside is the highest of {window_label} "
            f"({worst_long_term:,.0f} $mm) -- more debt is the adverse direction."
        )),
        ("Assumptions", 10, other_debt, other_debt, *derived(
            f"Residual: disclosed total debt {ending_debt:,.0f} - LongTermDebt "
            f"{long_term:,.0f} - CommercialPaper {commercial_paper:,.0f} = "
            f"{other_debt:,.0f} $mm. Finance leases and other borrowings Microsoft "
            "does not tag separately in this fact set. Carrying it as the residual is "
            "what makes gross debt on the Capital Structure sheet tie EXACTLY to the "
            f"disclosed total. {debt_caveat}"
        )),
        ("Assumptions", 11, UNGROUNDED["base_rate"], UNGROUNDED["base_rate"], *driver(
            "Floating base rate. Not company data; it would come from a rates source "
            "(FRED), which is not reachable in this environment. It feeds only the "
            "term-loan line, which is zero for Microsoft, so it is inert here."
        )),
        ("Assumptions", 12, UNGROUNDED["revolver_spread"], UNGROUNDED["revolver_spread"],
         *driver(
            "All-in cost of the commercial-paper balance. Microsoft does not tag a "
            "commercial-paper rate. Held as a driver -- and note the AGGREGATE it "
            "feeds is pinned: the senior-notes coupon is solved so total cash interest "
            f"equals the disclosed InterestExpense of {interest_expense:,.0f} $mm "
            "regardless of how this splits."
        )),
        ("Assumptions", 13, UNGROUNDED["term_loan_spread"], UNGROUNDED["term_loan_spread"],
         *driver("Term-loan spread. Inert: Microsoft has no term loan.")),
        ("Assumptions", 14, coupon, coupon, *derived(
            f"Solved so Capital Structure cash interest equals the disclosed "
            f"us-gaap:InterestExpense of {interest_expense:,.0f} $mm for FY2024. The "
            "template charges both the senior-notes and other-debt lines at this rate, "
            f"so coupon = (InterestExpense - CommercialPaper x revolver spread) / "
            f"(LongTermDebt + other debt) = {coupon:.6f}. Per-instrument coupons are "
            "in the 10-K debt note as tabular HTML, not as tagged facts; the weighted "
            "burden is what is disclosed, and it is what is pinned."
        )),
        ("Assumptions", 15, UNGROUNDED["new_issue_spread"], UNGROUNDED["new_issue_spread"],
         *driver(
            "New-issue spread for hypothetical refinancing. Forward pricing is not a "
            "disclosed fact about any issuer."
        )),
        ("Assumptions", 16, UNGROUNDED["oid_fees"], UNGROUNDED["oid_fees"], *driver(
            "Original issue discount and fees on hypothetical new issuance. Not "
            "disclosed."
        )),
        ("Assumptions", 17, UNGROUNDED["minimum_cash"], UNGROUNDED["minimum_cash"],
         *driver(
            "Minimum operating cash. A modeler-set policy floor, not a Microsoft "
            "disclosure."
        )),
        ("Assumptions", 18, UNGROUNDED["max_leverage"], UNGROUNDED["max_leverage"],
         *driver(
            "Maximum leverage screen. Microsoft is investment grade and its credit "
            "agreement carries no maintenance leverage covenant, so there is no "
            "disclosed threshold to source. This is an analyst screen, not a covenant, "
            "and the template's 5.5x leveraged-mid-cap default is removed."
        )),
        ("Assumptions", 19, UNGROUNDED["min_interest_coverage"],
         UNGROUNDED["min_interest_coverage"], *driver(
            "Minimum interest-coverage screen. Same reasoning as the leverage screen: "
            "no maintenance covenant exists to disclose."
        )),
        ("Assumptions", 20, UNGROUNDED["recovery_multiple"], UNGROUNDED["recovery_multiple"],
         *driver("Recovery/EV multiple for the recovery analysis. Not a disclosed fact.")),
        ("Assumptions", 21, UNGROUNDED["ev_haircut"], UNGROUNDED["ev_haircut"], *driver(
            "Distress haircut to enterprise value. A modeler-chosen severity, not a "
            "disclosure."
        )),
        # --- Refinancing & Rates -----------------------------------------
        ("Refinancing & Rates", 5, opening_debt, opening_debt, *derived(
            f"Opening total debt {opening_debt:,.0f} $mm, derived from the FY2024 10-K "
            f"as ending debt {ending_debt:,.0f} + repayments {frozen['debt_repaid_usd_mm']:,.0f} "
            f"- issuance {frozen['debt_issued_usd_mm']:,.0f}. Retained from the case's "
            "existing frozen snapshot."
        )),
        ("Refinancing & Rates", 6, frozen["debt_issued_usd_mm"],
         frozen["debt_issued_usd_mm"], *observed(
            "Debt issued during FY2024 per the 10-K financing-activities section. "
            "Retained from the case's existing frozen snapshot."
        )),
        ("Refinancing & Rates", 7, frozen["debt_repaid_usd_mm"],
         frozen["debt_repaid_usd_mm"], *observed(
            "Debt repaid during FY2024 per the 10-K financing-activities section. "
            "Retained from the case's existing frozen snapshot."
        )),
        ("Refinancing & Rates", 8, year1_maturities, year1_maturities, *derived(
            f"Contractual maturities inside twelve months: LongTermDebtCurrent "
            f"{long_term_current:,.0f} + CommercialPaper {commercial_paper:,.0f} = "
            f"{year1_maturities:,.0f} $mm. This is the one rung of the maturity ladder "
            "that IS tagged in XBRL; years 2-5 are disclosed only in the 10-K debt "
            "note's maturity table, which is untagged HTML."
        )),
        ("Refinancing & Rates", 13, liquidity, liquidity, *observed(
            f"Cash and short-term investments {liquidity:,.0f} $mm per the FY2024 10-K. "
            "Retained from the case's existing frozen snapshot."
        )),
        ("Refinancing & Rates", 14, UNGROUNDED["committed_lines"],
         UNGROUNDED["committed_lines"], *driver(
            "Committed revolving-credit capacity. Disclosed in the 10-K debt note as "
            "narrative text rather than a tagged fact."
        )),
        ("Refinancing & Rates", 15, tranche1, tranche1, *derived(
            f"Tranche 1 = us-gaap:LongTermDebt at {FY} = {tranche1:,.0f} $mm."
        )),
        ("Refinancing & Rates", 16, UNGROUNDED["tranche1_rate"], UNGROUNDED["tranche1_rate"],
         *driver(
            "Tranche-1 rate. Per-instrument coupons are untagged. Held as a driver; "
            "the weighted cost this feeds IS pinned to disclosure via tranche 2."
        )),
        ("Refinancing & Rates", 17, tranche2, tranche2, *derived(
            f"Tranche 2 = disclosed total debt {ending_debt:,.0f} - LongTermDebt "
            f"{tranche1:,.0f} = {tranche2:,.0f} $mm (commercial paper, finance leases, "
            "and other borrowings)."
        )),
        ("Refinancing & Rates", 18, tranche2_rate, tranche2_rate, *derived(
            f"Solved so the sheet's weighted cost equals Microsoft's disclosed "
            f"effective rate: InterestExpense {interest_expense:,.0f} / average debt "
            f"{average_debt:,.0f} = {effective_rate:.6f}. Gross bookings of rate detail "
            "are not disclosed per instrument; the blended cost is, so the blended "
            "cost is what the model reproduces."
        )),
        ("Refinancing & Rates", 19, ebit, worst_ebit, *derived(
            f"{ebit_caveat} Downside is the lowest of {window_label}."
        )),
        ("Refinancing & Rates", 20, UNGROUNDED["max_maturity_concentration"],
         UNGROUNDED["max_maturity_concentration"], *driver(
            "Maximum tolerated share of debt maturing in any single year. An analyst "
            "screen, not a disclosed covenant."
        )),
        ("Refinancing & Rates", 21, UNGROUNDED["min_interest_coverage"],
         UNGROUNDED["min_interest_coverage"], *driver(
            "Minimum interest coverage screen. No maintenance covenant exists to source."
        )),
        ("Refinancing & Rates", 22, UNGROUNDED["max_weighted_cost"],
         UNGROUNDED["max_weighted_cost"], *driver(
            "Maximum tolerated weighted cost of debt. An analyst screen."
        )),
    ]

    # Years 2-5 of the maturity ladder. Individually undisclosed, but their
    # SUM is pinned: everything not maturing in year 1 must still be there.
    remaining = ending_debt - year1_maturities
    shape = [0.22, 0.24, 0.20, 0.34]  # driver: the ladder's shape, not its total
    ladder = [round(remaining * share, 1) for share in shape[:-1]]
    ladder.append(round(remaining - sum(ladder), 1))
    ladder_note = (
        f"Years 2-5 of the maturity ladder. The SHAPE is a driver -- Microsoft's "
        "year-by-year maturity table is in the 10-K debt note as untagged HTML -- but "
        f"the TOTAL is pinned: these four rungs sum to {remaining:,.1f} $mm, which is "
        f"disclosed total debt {ending_debt:,.0f} less the {year1_maturities:,.0f} $mm "
        "of tagged year-1 maturities, so no debt is created or lost by the ladder."
    )
    for offset, amount in enumerate(ladder):
        row = 9 + offset
        kind = "derived" if row == 12 else "driver"
        note = ladder_note + (
            " This rung is the balancing residual and therefore carries the constraint."
            if row == 12 else ""
        )
        rows.append(("Refinancing & Rates", row, amount, amount, kind, note))

    inputs: list[dict[str, Any]] = []
    drivers: list[dict[str, Any]] = []
    for sheet, row, base_value, adverse_value, kind, text in rows:
        for column, value in (("C", base_value), ("D", adverse_value)):
            cell = f"{column}{row}"
            # Rates keep eight digits, dollar levels one. A solved rate is the
            # answer to an equation whose right-hand side is disclosed, so
            # truncating it loosens the tie to the filing for no benefit.
            quantize = round(value, 8) if abs(value) < 100 else round(value, 1)
            if kind == "driver":
                drivers.append({
                    "sheet": sheet,
                    "cell": cell,
                    "driver_type": "undisclosed_term_driver",
                    "rationale": text,
                    "basis": {},
                })
                inputs.append({
                    "sheet": sheet,
                    "cell": cell,
                    "value": quantize,
                    "input_kind": "modeler_assumption",
                    "source": {
                        "name": "Case driver (no tagged disclosure exists)",
                        "url": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
                        "as_of": AS_OF,
                        "notes": text,
                    },
                })
                continue
            inputs.append({
                "sheet": sheet,
                "cell": cell,
                "value": quantize,
                "input_kind": kind,
                "source": {
                    "name": TEN_K_NAME,
                    "url": TEN_K_URL,
                    "as_of": AS_OF,
                    "notes": text,
                },
            })

    # --- Maturity Ladder sheet -------------------------------------------
    # Six columns (Year 1..5, Beyond) x four instrument rows. Three of the
    # twenty-four cells are disclosed outright; the rest are shape drivers
    # whose ROW TOTALS are pinned to tagged balances, so the grid sums to
    # disclosed gross debt and the workbook's "maturities reconcile" check
    # becomes a real test instead of a standing REVIEW.
    ladder_columns = ["C", "D", "E", "F", "G", "H"]

    def spread(total: float, shares: list[float]) -> list[float]:
        parts = [round(total * s, 1) for s in shares[:-1]]
        parts.append(round(total - sum(parts), 1))
        return parts

    notes_later = spread(long_term - long_term_current, [0.20, 0.16, 0.14, 0.12, 0.38])
    other_spread = spread(other_debt, [0.30, 0.22, 0.16, 0.12, 0.10, 0.10])
    ladder_rows = {
        5: (
            [commercial_paper, 0.0, 0.0, 0.0, 0.0, 0.0],
            ["derived"] + ["derived"] * 5,
            f"Commercial paper {commercial_paper:,.0f} $mm matures inside twelve "
            "months by definition, so it sits entirely in Year 1 and the later "
            "columns are zero. Microsoft's revolving facility itself was undrawn.",
        ),
        6: (
            [0.0] * 6,
            ["derived"] * 6,
            "Zero across every year: Microsoft's XBRL debt facts disclose no "
            "term-loan instrument.",
        ),
        7: (
            [long_term_current] + notes_later,
            ["derived"] + ["driver"] * 5,
            f"Year 1 is us-gaap:LongTermDebtCurrent = {long_term_current:,.0f} $mm, a "
            f"tagged fact. The remaining {long_term - long_term_current:,.0f} $mm of "
            "long-term notes is spread across later years by a SHAPE driver -- "
            "Microsoft's year-by-year maturity table is untagged HTML in the debt "
            "note -- but the row total is pinned to tagged us-gaap:LongTermDebt.",
        ),
        8: (
            other_spread,
            ["driver"] * 6,
            f"Finance leases and other borrowings, {other_debt:,.0f} $mm in total. "
            "Neither the balance nor its maturity profile is tagged separately; the "
            "balance is the residual against disclosed total debt and the profile is "
            "a shape driver. The row total is pinned.",
        ),
    }
    for row, (amounts, kinds, note) in ladder_rows.items():
        for column, amount, kind in zip(ladder_columns, amounts, kinds):
            cell = f"{column}{row}"
            value = round(amount, 1)
            if kind == "driver":
                drivers.append({
                    "sheet": "Maturity Ladder",
                    "cell": cell,
                    "driver_type": "undisclosed_term_driver",
                    "rationale": note,
                    "basis": {},
                })
                inputs.append({
                    "sheet": "Maturity Ladder",
                    "cell": cell,
                    "value": value,
                    "input_kind": "modeler_assumption",
                    "source": {
                        "name": "Case driver (no tagged disclosure exists)",
                        "url": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
                        "as_of": AS_OF,
                        "notes": note,
                    },
                })
                continue
            inputs.append({
                "sheet": "Maturity Ladder",
                "cell": cell,
                "value": value,
                "input_kind": "derived",
                "source": {
                    "name": TEN_K_NAME,
                    "url": TEN_K_URL,
                    "as_of": AS_OF,
                    "notes": note,
                },
            })

    # C16 is the one remaining cell there with a disclosed value.
    inputs.append({
        "sheet": "Maturity Ladder",
        "cell": "C16",
        "value": liquidity,
        "input_kind": "observed",
        "source": {
            "name": TEN_K_NAME,
            "url": TEN_K_URL,
            "as_of": AS_OF,
            "notes": (
                f"Cash and short-term investments {liquidity:,.0f} $mm per the FY2024 "
                "10-K, the same disclosed liquidity used on the refinancing sheet."
            ),
        },
    })

    cover = {
        "Issuer:": "Microsoft Corporation (NASDAQ: MSFT), CIK 0000789019",
        "Transaction:": (
            "FY2024 debt, liquidity, and refinancing profile -- general corporate, "
            "no transaction pending"
        ),
        "Next maturity / launch:": (
            f"FY2025 (within twelve months of {FY}): {year1_maturities:,.0f} $mm of "
            f"tagged near-term maturities (LongTermDebtCurrent {long_term_current:,.0f} "
            f"+ commercial paper {commercial_paper:,.0f})"
        ),
        "Refresh cadence:": "Annual, on Microsoft's Form 10-K (fiscal year ends 30 June)",
    }
    cover_drivers = [
        {
            "sheet": "Cover",
            "cell": "C6",
            "driver_type": "generated_metadata",
            "rationale": "Populated from the manifest as_of date; release metadata.",
            "basis": {},
        },
        {
            "sheet": "Cover",
            "cell": "C9",
            "driver_type": "generated_metadata",
            "rationale": "Populated from the manifest scenario selection.",
            "basis": {},
        },
        {
            "sheet": "Cover",
            "cell": "C10",
            "driver_type": "presentation_convention",
            "rationale": "Presentation convention ($ in millions), not a fact.",
            "basis": {},
        },
    ]

    snapshot = {
        "schema_version": "1.0",
        "model_id": MODEL_ID,
        "domain": "Debt Finance",
        "case_id": CASE_ID,
        "case_type": "conventional",
        "as_of": AS_OF,
        "capture_method": "sec_xbrl_company_facts_plus_curated_10k_observation",
        "sources": [
            {
                "name": TEN_K_NAME,
                "url": TEN_K_URL,
                "publisher": "U.S. SEC / Microsoft",
                "captured_values": {
                    key: frozen[key] for key in FROZEN_KEYS
                },
            },
            {
                "name": XBRL_NAME,
                "url": XBRL_URL,
                "publisher": "U.S. Securities and Exchange Commission (EDGAR company facts)",
                "captured_values": {
                    "cik": "0000789019",
                    "fiscal_year_ends": WINDOW,
                    "long_term_debt_usd_mm": {
                        end: fact(xbrl, "LongTermDebt", end) for end in WINDOW
                    },
                    "long_term_debt_current_usd_mm": {
                        end: fact(xbrl, "LongTermDebtCurrent", end) for end in WINDOW
                    },
                    "long_term_debt_noncurrent_usd_mm": {
                        end: fact(xbrl, "LongTermDebtNoncurrent", end) for end in WINDOW
                    },
                    "commercial_paper_usd_mm": {FY: commercial_paper},
                    "cash_and_equivalents_usd_mm": {
                        end: fact(xbrl, "CashAndCashEquivalentsAtCarryingValue", end)
                        for end in WINDOW
                    },
                    "operating_income_usd_mm": {
                        end: fact(xbrl, "OperatingIncomeLoss", end) for end in WINDOW
                    },
                    "interest_expense_usd_mm": {
                        end: fact(xbrl, "InterestExpense", end) for end in WINDOW
                    },
                },
            },
        ],
        "input_overrides": [],
        "reconciliation_to_disclosure": {
            "exact": {
                "gross_debt_usd_mm": round(
                    commercial_paper + 0.0 + long_term + other_debt, 1
                ),
                "disclosed_ending_debt_usd_mm": ending_debt,
                "cash_interest_usd_mm": round(
                    commercial_paper * UNGROUNDED["revolver_spread"]
                    + notes_and_other * coupon,
                    1,
                ),
                "disclosed_interest_expense_usd_mm": interest_expense,
                "weighted_cost_of_debt": round(effective_rate, 6),
                "note": (
                    "Gross debt ties to the disclosed total because other debt is "
                    "carried as the residual; cash interest and weighted cost tie "
                    "because the senior-notes coupon and tranche-2 rate are solved "
                    "for, not chosen."
                ),
            },
            "conservative_bias": {
                "ebitda_proxy": "EBIT (OperatingIncomeLoss)",
                "value_usd_mm": ebit,
                "direction": (
                    "EBIT understates EBITDA, so modelled interest coverage is "
                    "understated and modelled leverage overstated. The case cannot "
                    "flatter Microsoft's credit; it can only understate it."
                ),
            },
        },
        "undisclosed_terms": {
            "note": (
                "Debt-model terms Microsoft does not tag in XBRL. Recorded so the gap "
                "is auditable rather than implicit."
            ),
            "items": [
                "per-instrument coupons and spreads",
                "year-by-year maturity ladder beyond the current portion",
                "revolving credit facility commitment size",
                "maintenance covenant thresholds (investment grade; none exist)",
                "depreciation and amortization (so EBITDA is not derivable)",
                "finance lease balances as a separate tagged concept",
            ],
        },
        "outcome": {
            "metric": "ending_debt_usd_mm",
            "forecast": 70000.0,
            "realized": ending_debt,
            "realized_source": TEN_K_NAME,
            "status": "recorded",
        },
        "counts_toward_m4": False,
    }
    snapshot["snapshot_sha256"] = hashlib.sha256(canonical_bytes(snapshot)).hexdigest()

    existing = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest = {
        **existing,
        "cover": cover,
        "inputs": sorted(
            inputs, key=lambda item: (item["sheet"], item["cell"][0], int(item["cell"][1:]))
        ),
        "sources": [
            {
                "name": TEN_K_NAME,
                "url": TEN_K_URL,
                "as_of": AS_OF,
                "notes": (
                    "Cash-flow and liquidity disclosures frozen in the case snapshot: "
                    "debt issued, debt repaid, ending debt, cash and short-term "
                    "investments, operating cash flow, capex."
                ),
            },
            {
                "name": XBRL_NAME,
                "url": XBRL_URL,
                "as_of": AS_OF,
                "notes": (
                    "SEC XBRL company facts for CIK 0000789019, recorded at "
                    f"{FACTS.relative_to(ROOT)}. Supplies the debt balances, "
                    "current/non-current split, commercial paper, cash, operating "
                    f"income, and interest expense for {window_label}."
                ),
            },
            {
                "name": "Frozen source snapshot",
                "url": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
                "as_of": AS_OF,
                "notes": "Immutable curated observation package with SHA-256 digest",
            },
        ],
        "refresh": {
            "date": date.today().isoformat(),
            "trigger": "Depth pass: full input accounting against recorded XBRL facts",
            "source_snapshot": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
            "what_changed": (
                "Rebuilt the case from Microsoft's recorded SEC XBRL facts. It "
                "previously carried four sourced cells out of 102 candidates (4.9%) "
                "with every other input left at a generic leveraged-mid-cap template "
                "default -- a $300mm term loan Microsoft does not have, a 5.5x leverage "
                "covenant it is not subject to, a 5.5% coupon. Capital structure now "
                "ties exactly to disclosed total debt, cash interest and weighted cost "
                "are solved to disclosed interest expense, and every remaining cell is "
                "a declared driver with a stated reason."
            ),
            "reviewer_notes": (
                "External historical case; human stakeholder approval remains pending. "
                "EBITDA is proxied by EBIT because Microsoft tags no D&A concept; the "
                "bias is conservative (understates coverage, overstates leverage)."
            ),
            "next_check": "On Microsoft's next Form 10-K, builder change, or annual review",
        },
        "driver_declarations": sorted(
            drivers + cover_drivers,
            key=lambda item: (item["sheet"], item["cell"][0], int(item["cell"][1:])),
        ),
    }
    return manifest, snapshot


def write_source_register(snapshot: dict[str, Any]) -> None:
    rows = [
        (
            CASE_ID, TEN_K_NAME, "U.S. SEC / Microsoft", TEN_K_URL, AS_OF,
            str(SNAPSHOT_PATH.relative_to(ROOT)), snapshot["snapshot_sha256"], "frozen",
        ),
        (
            CASE_ID, XBRL_NAME,
            "SEC EDGAR via tools/data_fabric/edgar_company_facts.py", XBRL_URL, AS_OF,
            str(FACTS.relative_to(ROOT)),
            hashlib.sha256(FACTS.read_bytes()).hexdigest(), "active",
        ),
    ]
    header = "case_id,source_name,publisher,url,as_of,snapshot,snapshot_sha256,status"
    lines = [header]
    if REGISTER_PATH.exists():
        existing = REGISTER_PATH.read_text(encoding="utf-8").splitlines()
        lines = [line for line in (existing or lines) if not line.startswith(f"{CASE_ID},")]
    for row in rows:
        lines.append(",".join(f'"{f}"' if "," in f else f for f in row))
    REGISTER_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-only", action="store_true")
    args = parser.parse_args()

    manifest, snapshot = build()
    if args.print_only:
        print(json.dumps(manifest, indent=2))
        return 0

    SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_source_register(snapshot)
    print(f"saved {MANIFEST_PATH.relative_to(ROOT)}")
    print(f"saved {SNAPSHOT_PATH.relative_to(ROOT)}  sha256={snapshot['snapshot_sha256'][:16]}...")
    print(f"saved {REGISTER_PATH.relative_to(ROOT)}")
    print(
        f"inputs={len(manifest['inputs'])} "
        f"drivers={len(manifest['driver_declarations'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
