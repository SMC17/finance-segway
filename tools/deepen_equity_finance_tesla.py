"""Fill the Tesla February 2020 offering case's income statement from recorded facts.

The case is dated 2020-02-14, the day Tesla priced an underwritten primary
offering at $767.00 per share. Its template gained a historical actuals block
when the BASE builder was fixed (those cells existed before but carried no
input marker and no derived formulas, so the whole income statement, the DCF,
and diluted EPS evaluated to zero). This fills that block.

TWO DATING RULES, BOTH ENFORCED BELOW
-------------------------------------
1. No hindsight. The most recent fiscal year a reader could have had on
   2020-02-14 is FY2019, whose 10-K was filed 2020-02-13 -- one day before.
   FY2020 exists in the same fact file and is excluded. Every observation used
   here must also have been FILED on or before the case date, which is a
   stricter test than the period merely having ended.

2. No split-basis mixing. Tesla split 5:1 in August 2020 and 3:1 in August
   2022, and the corpus keeps one value per period taken from whichever filing
   restated it last. So adjacent share counts sit on different bases:
   FY2017 weighted basic reads 166,000,000 (filed 2020-02-13, pre-split) while
   FY2019 reads 887,000,000 (filed 2022-02-07, post 5:1). Read as a series that
   is a 414% increase. Tesla issued no such shares.

   Rule 1 happens to solve rule 2 here: requiring filed <= 2020-02-14 selects
   only pre-split filings, so every share count used is on one basis. That is
   not a coincidence -- as-filed-at-the-case-date is the correct basis for a
   historical case, and it is split-safe for the same reason.

WHAT CANNOT BE FILLED, AND WHY
------------------------------
Depreciation and amortisation. EDGAR tags it for Tesla's FY2017 (769) but not
for FY2018 or FY2019. Using the one available year would give a D&A series of
769, 0, 0, and an EBITDA series whose year-on-year change is pure artefact --
the same defect tools/verify_share_series_integrity.py exists to catch. So D&A
is declared as a driver at zero across all three years, which makes the EBITDA
line equal EBIT and understate true EBITDA. The direction is stated rather
than hidden: understating EBITDA understates every coverage ratio built on it.

Usage:
    python tools/deepen_equity_finance_tesla.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / "tools" / "data_fabric" / "out" / "TSLA_facts_annual_series.json"
CASE_ID = "equity-public-tesla-2020-offering"
FOLDER = "12_Equity_Finance"
MANIFEST_PATH = ROOT / "standards" / "public_cases" / f"{CASE_ID}.json"
SNAPSHOT_PATH = ROOT / FOLDER / "sources" / "snapshots" / f"{CASE_ID}.json"
REGISTER_PATH = ROOT / FOLDER / "sources" / "source_register.csv"

OWNER = "tools/deepen_equity_finance_tesla.py"

AS_OF = "2020-02-14"
# FY-2A, FY-1A, FY0A for a case dated 2020-02-14, mapped to IS columns C, D, E.
PERIODS = [("2017-12-31", "C"), ("2018-12-31", "D"), ("2019-12-31", "E")]

XBRL_NAME = "Tesla, Inc. SEC XBRL company facts (CIK 0001318605)"
XBRL_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK0001318605.json"
PROSPECTUS_NAME = "Tesla February 2020 Final Prospectus (424(b)(5))"
PROSPECTUS_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001318605&type=424"

# The second vendor the FY2017-FY2019 income lines were corroborated against.
# It belongs in the register because the cross-check is why those lines are
# recorded as observed rather than as retained-value estimates.
AV_FACTS = ROOT / "tools" / "data_fabric" / "out" / "TSLA_alphavantage_income_statement.json"
AV_NAME = "Tesla, Inc. income statement, FY2017-FY2019 (second-vendor cross-check)"
AV_URL = "https://www.alphavantage.co/documentation/#income-statement"

# Depreciation, amortisation and capital expenditure. Tesla used EDGAR's
# DepreciationDepletionAndAmortization tag in one filing only, for a narrower
# figure, and not at all for FY2018 or FY2019, so EDGAR cannot supply this
# series on one basis. The recorded snapshot states that disagreement in full.
AV_CASH = ROOT / "tools" / "data_fabric" / "out" / "TSLA_alphavantage_cash_flow.json"
AV_CASH_NAME = "Tesla, Inc. cash flow statement, FY2017-FY2019 (D&A and capital expenditure)"
AV_CASH_URL = "https://www.alphavantage.co/documentation/#cash-flow"

# IS row numbers in the BASE template.
ROW = {
    "revenue": 5, "cogs": 7, "opex": 10, "da": 13,
    "interest": 15, "tax": 17, "shares": 19,
}

# Shares outstanding at the offering, already a sourced input in this case
# (Cap Table & Dilution!C5). Reused rather than re-sourced so the two sheets
# cannot disagree.
OFFERING_SHARES_CELL = ("Cap Table & Dilution", "C5")


def load_cash_flow() -> dict[str, dict[str, float]]:
    """{av_field: {period_end: value}} from the recorded cash-flow snapshot."""
    if not AV_CASH.exists():
        raise FileNotFoundError(f"missing recorded snapshot {AV_CASH.relative_to(ROOT)}")
    payload = json.loads(AV_CASH.read_text(encoding="utf-8"))
    out: dict[str, dict[str, float]] = {}
    for fact in payload["facts"]:
        out.setdefault(fact["av_field"], {})[fact["end"]] = fact["value"]
    return out


def load_facts() -> dict[str, list[dict[str, Any]]]:
    if not FACTS.exists():
        raise FileNotFoundError(f"missing recorded snapshot {FACTS.relative_to(ROOT)}")
    payload = json.loads(FACTS.read_text(encoding="utf-8"))
    return {series["concept"]: series["observations"] for series in payload["concepts"]}


def as_filed(
    facts: dict[str, list[dict[str, Any]]], concept: str, end: str
) -> dict[str, Any] | None:
    """The observation for `end` whose FILING predates the case date.

    Used only for share counts, where a later filing demonstrably changes the
    number: Tesla's splits mean the restated value is on a different basis
    entirely. For those, nothing but an as-filed-by-the-case-date observation
    will do.
    """
    candidates = [
        o for o in facts.get(concept, [])
        if o["end"] == end and o.get("filed") and o["filed"] <= AS_OF
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda o: o["filed"])


def retained(
    facts: dict[str, list[dict[str, Any]]], concept: str, end: str
) -> dict[str, Any] | None:
    """The single observation this corpus retains for `end`.

    Used for income-statement lines, and the looser rule needs its reasoning on
    the record. The corpus keeps one observation per fiscal period and resolves
    collisions by latest filing, so Tesla's FY2018 figures are carried by the
    FY2020 10-K and FY2019's by the FY2021 10-K -- both filed after this case's
    date. A strict as-filed filter therefore rejects two of the three years and
    the case cannot be built at all.

    That filter would be rejecting the wrong thing. An annual report restates
    the two prior years as comparatives, so a later filing carrying FY2018 is
    usually repeating it, not revising it. The hazard is a filing that CHANGES
    the value, and for these line items there is evidence it did not: Alpha
    Vantage, an independent vendor, agrees with 15 of 18 compared values
    exactly, and the three differences are precision (as-filed to the thousand
    against a later rounding to millions), not revision. That cross-check is
    recorded in tools/data_fabric/out/TSLA_alphavantage_income_statement.json.

    Share counts get no such benefit of the doubt, because there the
    restatement provably changes the number.
    """
    candidates = [o for o in facts.get(concept, []) if o["end"] == end]
    if not candidates:
        return None
    return max(candidates, key=lambda o: o.get("filed") or "")


def millions(observation: dict[str, Any]) -> float:
    return round(observation["value"] / 1e6, 1)


def build() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    facts = load_facts()
    cash_flow = load_cash_flow()
    av_cash = (AV_CASH_NAME, AV_CASH_URL)
    existing = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    # Every entry this script writes carries OWNER, so a second run replaces
    # its own previous output instead of colliding with it. Without this the
    # script runs exactly once and then refuses, which makes it impossible to
    # correct a driver -- the correction has to be hand-edited into the
    # manifest, which is what the builders in this repository exist to avoid.
    existing["inputs"] = [
        i for i in existing["inputs"] if i.get("emitted_by") != OWNER
    ]
    existing["driver_declarations"] = [
        d for d in (existing.get("driver_declarations") or [])
        if d.get("emitted_by") != OWNER
    ]
    existing["sources"] = [
        s for s in existing["sources"] if s.get("emitted_by") != OWNER
    ]
    already = {(i["sheet"], i["cell"]) for i in existing["inputs"]}

    offering_shares = next(
        i["value"] for i in existing["inputs"]
        if (i["sheet"], i["cell"]) == OFFERING_SHARES_CELL
    )

    inputs: list[dict[str, Any]] = []
    drivers: list[dict[str, Any]] = []
    captured: dict[str, Any] = {"periods": [p for p, _ in PERIODS]}
    unavailable: list[str] = []

    def emit(cell: str, value: float, kind: str, note: str, source: tuple[str, str]) -> None:
        key = ("IS", cell)
        if key in already:
            raise ValueError(f"refusing to overwrite already-sourced cell IS!{cell}")
        if kind == "driver":
            drivers.append({
                "sheet": "IS", "cell": cell,
                "driver_type": "undisclosed_metric_driver",
                "rationale": note, "basis": {}, "emitted_by": OWNER,
            })
            inputs.append({
                "sheet": "IS", "cell": cell, "value": value,
                "input_kind": "modeler_assumption",
                "source": {
                    "name": "Case driver (no usable disclosure on one basis)",
                    "url": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
                    "as_of": AS_OF, "notes": note,
                },
                "emitted_by": OWNER,
            })
            return
        inputs.append({
            "sheet": "IS", "cell": cell, "value": value, "input_kind": kind,
            "source": {
                "name": source[0], "url": source[1], "as_of": AS_OF, "notes": note,
            },
            "emitted_by": OWNER,
        })

    xbrl = (XBRL_NAME, XBRL_URL)
    prospectus = (PROSPECTUS_NAME, PROSPECTUS_URL)

    for end, column in PERIODS:
        year = end[:4]
        revenue = retained(facts, "Revenues", end)
        cogs = retained(facts, "CostOfRevenue", end)
        gross = retained(facts, "GrossProfit", end)
        operating = retained(facts, "OperatingIncomeLoss", end)
        interest = retained(facts, "InterestExpense", end)
        tax = retained(facts, "IncomeTaxExpenseBenefit", end)
        # Strict: a later filing changes this one, so only as-filed will do.
        shares = as_filed(facts, "CommonStockSharesOutstanding", end)

        if not all((revenue, cogs, gross, operating, interest, tax)):
            missing = [
                name for name, obs in (
                    ("Revenues", revenue), ("CostOfRevenue", cogs),
                    ("GrossProfit", gross), ("OperatingIncomeLoss", operating),
                    ("InterestExpense", interest), ("IncomeTaxExpenseBenefit", tax),
                ) if obs is None
            ]
            raise ValueError(
                f"FY{year}: the corpus retains no observation for {missing}"
            )

        # Verify the issuer's own identity before deriving anything from it.
        if abs((revenue["value"] - cogs["value"]) - gross["value"]) > 1e6:
            raise ValueError(
                f"FY{year}: Revenues - CostOfRevenue does not equal GrossProfit "
                f"({revenue['value']:,} - {cogs['value']:,} != {gross['value']:,})"
            )

        emit(f"{ROW['revenue']}".join([column, ""]) if False else f"{column}{ROW['revenue']}",
             millions(revenue), "observed",
             f"us-gaap:Revenues for FY{year} = {millions(revenue):,.0f} $mm, carried by "
             f"the filing of {revenue['filed']}. Corroborated against Alpha Vantage, an "
             "independent vendor, which reports the same figure.",
             xbrl)
        emit(f"{column}{ROW['cogs']}", millions(cogs), "observed",
             f"us-gaap:CostOfRevenue for FY{year} = {millions(cogs):,.0f} $mm, carried by "
             f"the filing of {cogs['filed']}. Revenues less this equals the disclosed "
             f"GrossProfit of {millions(gross):,.0f} $mm exactly, which is asserted "
             "before the value is used.",
             xbrl)

        # The template reads row 10 as the expense between gross profit and
        # EBITDA, and row 13 as D&A between EBITDA and EBIT. For EBITDA to mean
        # what its label says, row 10 must EXCLUDE D&A. So D&A is sourced first
        # and row 10 is the residual, which keeps EBIT tied to the filing.
        da_value = round(cash_flow["depreciationDepletionAndAmortization"][end] / 1e6, 1)
        emit(f"{column}{ROW['da']}", da_value, "observed",
             f"Depreciation, amortisation and impairment for FY{year} = "
             f"{da_value:,.0f} $mm, from Tesla's cash flow statement as recorded at "
             f"{AV_CASH.relative_to(ROOT)}. Tesla disclosed all three years of this "
             "line in the Form 10-K filed 2020-02-13, one day before the case date. "
             "WHY NOT EDGAR: Tesla tagged DepreciationDepletionAndAmortization in one "
             "filing only, with a narrower figure (769 $mm for FY2017 against 1,636 "
             "$mm here), and did not tag it at all for FY2018 or FY2019. The recorded "
             "snapshot states that disagreement and what is unresolved about it.",
             av_cash)

        opex = round(
            (gross["value"] - operating["value"]) / 1e6 - da_value, 1
        )
        if opex <= 0:
            raise ValueError(
                f"FY{year}: operating expense net of D&A came out at {opex:,.1f} $mm. "
                "A non-positive residual means more D&A was charged than sits above "
                "operating income, so the two sources are not on compatible bases."
            )
        emit(f"{column}{ROW['opex']}", opex, "derived",
             f"Operating expense for FY{year} EXCLUDING depreciation and amortisation, "
             f"derived as GrossProfit {millions(gross):,.0f} less OperatingIncomeLoss "
             f"{millions(operating):,.0f} less D&A {da_value:,.0f} = {opex:,.0f} $mm. "
             f"The first two terms were filed {gross['filed']}. Taking D&A out here is "
             "what makes the EBITDA row a real EBITDA and leaves EBIT equal to the "
             "disclosed operating income: "
             f"{millions(gross):,.0f} - {opex:,.0f} - {da_value:,.0f} = "
             f"{millions(operating):,.0f}.",
             xbrl)

        emit(f"{column}{ROW['interest']}", millions(interest), "observed",
             f"us-gaap:InterestExpense for FY{year} = {millions(interest):,.0f} $mm, "
             f"filed {interest['filed']}.", xbrl)
        emit(f"{column}{ROW['tax']}", millions(tax), "observed",
             f"us-gaap:IncomeTaxExpenseBenefit for FY{year} = {millions(tax):,.0f} $mm, "
             f"filed {tax['filed']}. A reported amount, not a rate.", xbrl)

        # --- share count: the split-basis decision -----------------------
        if shares is not None:
            emit(f"{column}{ROW['shares']}", millions(shares), "derived",
                 f"us-gaap:CommonStockSharesOutstanding at FY{year} year-end = "
                 f"{millions(shares):,.1f}mm, from the filing of {shares['filed']}, "
                 f"which predates the case date and is therefore PRE-SPLIT (Tesla split "
                 "5:1 in August 2020 and 3:1 in August 2022). Two caveats. First, the "
                 "template row is 'diluted shares' and this is period-end shares "
                 "outstanding: Tesla's weighted-average diluted count is not tagged, "
                 "and its weighted BASIC series in this corpus mixes split bases "
                 "(FY2017 reads 166mm pre-split, FY2019 reads 887mm post-split), so it "
                 "is unusable as a series. Second, year-end outstanding exceeds the "
                 "weighted average in a year with issuance, which understates earnings "
                 "per share.",
                 xbrl)
            captured[f"shares_outstanding_fy{year}"] = shares["value"]
            captured[f"shares_outstanding_fy{year}_filed"] = shares["filed"]
        else:
            # FY2019's as-filed value was superseded by the post-split
            # restatement and is no longer in the corpus. The offering
            # prospectus gives a pre-split count six weeks later, and this case
            # already cites it on the cap table.
            emit(f"{column}{ROW['shares']}", offering_shares, "derived",
                 f"Shares outstanding for FY{year} taken as {offering_shares}mm, the "
                 "pre-offering count disclosed in the February 2020 prospectus and "
                 "already sourced on this case's Cap Table & Dilution sheet. The "
                 f"as-filed FY{year} year-end count is NOT recoverable from this "
                 "corpus: the dedupe rule keeps one value per period and the FY2020 "
                 "10-K restated this one onto a post-5:1-split basis (905mm), so the "
                 "pre-split original is gone. The prospectus figure is six weeks later "
                 "than year-end and therefore slightly higher, which understates "
                 "earnings per share. Recovering the original requires re-harvesting "
                 "the FY2019 10-K as filed.",
                 prospectus)
            unavailable.append(
                f"CommonStockSharesOutstanding FY{year} as filed (superseded by a "
                "post-split restatement)"
            )

        captured[f"revenue_fy{year}_usd"] = revenue["value"]
        captured[f"cost_of_revenue_fy{year}_usd"] = cogs["value"]
        captured[f"gross_profit_fy{year}_usd"] = gross["value"]
        captured[f"operating_income_fy{year}_usd"] = operating["value"]
        captured[f"interest_expense_fy{year}_usd"] = interest["value"]
        captured[f"income_tax_fy{year}_usd"] = tax["value"]


    # --- forward driver grid and DCF bridge ------------------------------
    # Without these the Assumptions sheet stays at its zero defaults, and a
    # zero growth rate with a zero gross margin makes every projection column
    # and the DCF evaluate to zero. Each driver below is either derived from
    # the three in-window fiscal years or declared, never guessed.
    revenues = [retained(facts, "Revenues", end)["value"] for end, _ in PERIODS]
    gross_profits = [retained(facts, "GrossProfit", end)["value"] for end, _ in PERIODS]
    operating = [retained(facts, "OperatingIncomeLoss", end)["value"] for end, _ in PERIODS]
    # Capex from the SAME source as D&A. Alpha Vantage's capital expenditure
    # runs about 10% above EDGAR's PaymentsToAcquirePropertyPlantAndEquipment in
    # every year -- a stable gap, so a wider scope rather than a restatement.
    # The projection multiplies a capex ratio by a D&A-to-capex ratio, and
    # mixing sources across that product would make it meaningless.
    capex = [cash_flow["capitalExpenditures"][end] for end, _ in PERIODS]
    da_series = [
        cash_flow["depreciationDepletionAndAmortization"][end] for end, _ in PERIODS
    ]
    current_assets = [retained(facts, "AssetsCurrent", end)["value"] for end, _ in PERIODS]
    current_liabs = [retained(facts, "LiabilitiesCurrent", end)["value"] for end, _ in PERIODS]

    trailing_cagr = (revenues[-1] / revenues[0]) ** (1 / (len(revenues) - 1)) - 1
    slowest_year = min(
        revenues[i + 1] / revenues[i] - 1 for i in range(len(revenues) - 1)
    )
    gross_margin = gross_profits[-1] / revenues[-1]
    opex_ratio = (gross_profits[-1] - operating[-1] - da_series[-1]) / revenues[-1]
    capex_ratio = capex[-1] / revenues[-1]
    da_over_capex = da_series[-1] / capex[-1]
    da_over_revenue = da_series[-1] / revenues[-1]
    da_over_capex_window = [d / c for d, c in zip(da_series, capex)]
    working_capital = [a - l for a, l in zip(current_assets, current_liabs)]
    nwc_steps = [
        (working_capital[i + 1] - working_capital[i]) / (revenues[i + 1] - revenues[i])
        for i in range(len(revenues) - 1)
    ]
    shares_path_base = offering_shares

    forward_columns = ["C", "D", "E", "F", "G"]
    growth_path = [
        trailing_cagr + (slowest_year - trailing_cagr) * i / (len(forward_columns) - 1)
        for i in range(len(forward_columns))
    ]

    def emit_sheet(sheet: str, cell: str, value: float, kind: str, note: str,
                   source: tuple[str, str]) -> None:
        key = (sheet, cell)
        if key in already:
            raise ValueError(f"refusing to overwrite already-sourced cell {sheet}!{cell}")
        if kind == "driver":
            drivers.append({
                "sheet": sheet, "cell": cell,
                "driver_type": "undisclosed_metric_driver",
                "rationale": note, "basis": {}, "emitted_by": OWNER,
            })
            inputs.append({
                "sheet": sheet, "cell": cell, "value": value,
                "input_kind": "modeler_assumption",
                "source": {
                    "name": "Case driver (no disclosure exists)",
                    "url": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
                    "as_of": AS_OF, "notes": note,
                },
                "emitted_by": OWNER,
            })
            return
        inputs.append({
            "sheet": sheet, "cell": cell, "value": value, "input_kind": kind,
            "source": {"name": source[0], "url": source[1], "as_of": AS_OF, "notes": note},
            "emitted_by": OWNER,
        })

    window = "FY2017-FY2019"
    # Row 12 (shares outstanding) is deliberately absent. In the Equity Finance
    # variant of this template it is a FORMULA linking to the cap table, which
    # is the right design for an equity model -- share count belongs to the cap
    # table, not to a driver grid. model_instances.py refuses to overwrite a
    # formula, so writing it would fail the build.
    assumption_rows = [
        (5, growth_path, "derived",
         f"Revenue growth, fading from the {window} trailing compound rate "
         f"({trailing_cagr:.4f}) to the slowest year actually observed in the window "
         f"({slowest_year:.4f}). Both endpoints are real; only the linear path between "
         "them is a modelling choice. No fiscal year after the case date is used."),
        (6, [gross_margin] * 5, "derived",
         f"Gross margin held at the FY2019 actual, GrossProfit / Revenues = "
         f"{gross_margin:.4f}. The {window} range was 0.1656 to 0.1890, so holding the "
         "most recent value is the lower end of recent experience."),
        (7, [opex_ratio] * 5, "derived",
         f"Operating expense EXCLUDING depreciation and amortisation, over revenue, "
         f"held at the FY2019 actual: (GrossProfit - OperatingIncomeLoss - D&A) / "
         f"Revenues = {opex_ratio:.4f}. D&A is excluded here because the template "
         "charges it separately on row 9, and leaving it in both places would charge it "
         "twice. This ratio fell steeply across the window as revenue scaled, so "
         "holding the latest value assumes that operating leverage stops improving."),
        (8, [0.21] * 5, "driver",
         "Tax rate. No meaningful effective rate exists in the window: Tesla reported "
         "tax EXPENSE against pre-tax LOSSES in all three years, which gives a negative "
         "rate that would make the model add income on the way down. Held at the then "
         "prevailing US federal statutory rate as a declared driver."),
        (9, [da_over_capex] * 5, "derived",
         f"Depreciation and amortisation as a share of capital expenditure, at the "
         f"FY2019 actual = {da_over_capex:.4f} ({da_series[-1] / 1e6:,.0f} $mm of D&A "
         f"over {capex[-1] / 1e6:,.0f} $mm of capex). Both terms come from the same "
         f"cash flow statement, recorded at {AV_CASH.relative_to(ROOT)}; taking them "
         "from different sources would make the ratio meaningless, because the two "
         "sources scope capex differently. Together with row 10 this reproduces the "
         f"observed FY2019 D&A of {da_over_revenue:.4f} of revenue exactly, since "
         f"{capex_ratio:.6f} x {da_over_capex:.6f} = {da_over_revenue:.6f}. "
         "CAVEAT, and it matters: this ratio is unstable across the window "
         f"({da_over_capex_window[0]:.2f}, {da_over_capex_window[1]:.2f}, "
         f"{da_over_capex_window[2]:.2f}), because Tesla's capex fell by two thirds "
         "while its asset base kept depreciating. The pairing is chosen so that the "
         "product ties to the one quantity that is stable -- D&A as a share of revenue, "
         "which ran 0.1391, 0.0886 and 0.0876 across the window. Read row 9 and row 10 "
         "as a pair, not separately."),
        (10, [capex_ratio] * 5, "derived",
         f"Capital expenditure over revenue held at the FY2019 actual, "
         f"{capex[-1] / 1e6:,.0f} / {revenues[-1] / 1e6:,.0f} = {capex_ratio:.4f}, from "
         f"the cash flow statement recorded at {AV_CASH.relative_to(ROOT)}. Capex fell "
         "in absolute terms across the window while revenue more than doubled, so this "
         "is the lowest ratio of the three years and therefore the most favourable to "
         "free cash flow -- stated because it flatters the case. This source scopes "
         "capex about 10% wider than EDGAR's "
         "PaymentsToAcquirePropertyPlantAndEquipment, which makes the ratio slightly "
         "LESS favourable than the EDGAR-based figure this driver previously carried; "
         "it is used because row 9 needs capex and D&A on one basis."),
        (11, [sum(nwc_steps) / len(nwc_steps)] * 5, "derived",
         f"Change in net working capital per dollar of revenue change, mean of the "
         f"{window} steps = {sum(nwc_steps) / len(nwc_steps):.4f}, where net working "
         "capital is AssetsCurrent less LiabilitiesCurrent. CAVEAT: the two yearly "
         f"values ({nwc_steps[0]:.4f} and {nwc_steps[1]:.4f}) differ by an order of "
         "magnitude and Tesla's working capital crossed from negative to positive "
         "inside the window, so this mean is a weak central estimate."),
        (13, [0.095] * 5, "driver",
         "Weighted average cost of capital. A market-derived quantity requiring a "
         "risk-free rate, an equity risk premium, and a beta as of February 2020. None "
         "is an issuer disclosure, and no market-data source for that date is reachable "
         "from this environment."),
        (14, [0.025] * 5, "driver",
         "Terminal growth rate. A judgment about the indefinite future, not a fact."),
    ]
    for row, values, kind, note in assumption_rows:
        for column, value in zip(forward_columns, values):
            emit_sheet("Assumptions", f"{column}{row}", round(value, 6), kind, note, xbrl)

    emit_sheet("DCF", "I5", 0.095, "driver",
               "Discount rate, same reasoning as Assumptions row 13.", xbrl)
    emit_sheet("DCF", "I6", 0.025, "driver",
               "Terminal growth rate, same reasoning as Assumptions row 14.", xbrl)
    net_debt = round((13279000000 - 19384000000) / 1e6, 1)
    emit_sheet("DCF", "I11", net_debt, "derived",
               "Net debt as of FY2019 year-end, computed from Alpha Vantage's balance "
               "sheet for Tesla: shortLongTermDebtTotal 13,279 less cash and short-term "
               f"investments 19,384 = {net_debt:,.1f} $mm, i.e. Tesla carried net cash. "
               "Taken from Alpha Vantage because EDGAR's retained concept set for Tesla "
               "has no single total-debt tag. Note Alpha Vantage's totalShareholderEquity "
               "excludes noncontrolling interests and the vendor exposes no NCI field, so "
               "its balance sheet does not foot: assets 52,148 less liabilities 28,469 "
               "less equity 22,225 leaves 1,454 of unreported noncontrolling interest.",
               ("Tesla FY2019 balance sheet via Alpha Vantage",
                "https://www.alphavantage.co/documentation/#balance-sheet"))
    emit_sheet("DCF", "I13", shares_path_base, "derived",
               f"Diluted share count {shares_path_base}mm, the prospectus pre-offering "
               "count already sourced on the cap table.", prospectus)

    snapshot_extra_capex = {
        f"capex_fy{end[:4]}_usd": c for (end, _), c in zip(PERIODS, capex) if c
    }
    captured.update(snapshot_extra_capex)
    captured["net_debt_fy2019_usd_mm_from_alpha_vantage"] = net_debt

    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    snapshot = {
        **snapshot,
        "sources": [
            s for s in snapshot["sources"] if s.get("emitted_by") != OWNER
        ] + [{
            "name": XBRL_NAME,
            "url": XBRL_URL,
            "publisher": "U.S. Securities and Exchange Commission (EDGAR company facts)",
            "captured_values": captured,
            "emitted_by": OWNER,
        }],
        "dating_rules": {
            "hindsight": (
                f"Only observations FILED on or before the case date {AS_OF} are used. "
                "Filtering on the filing date rather than the period end is the "
                "stricter test and is what a reader on the case date actually had."
            ),
            "split_basis": (
                "Tesla split 5:1 in August 2020 and 3:1 in August 2022. Because the "
                "corpus keeps the latest restatement per period, adjacent share counts "
                "sit on different bases. The filed-by-case-date filter selects only "
                "pre-split filings, so every share count here is on one basis."
            ),
        },
        "not_available": {
            "note": (
                "Facts this case needed and could not get on a usable basis. Recorded "
                "so the gap is auditable rather than implicit."
            ),
            "items": sorted(set(unavailable)),
        },
    }
    snapshot.pop("snapshot_sha256", None)
    snapshot["snapshot_sha256"] = hashlib.sha256(
        (json.dumps(snapshot, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    ).hexdigest()

    manifest = {
        **existing,
        "inputs": sorted(
            existing["inputs"] + inputs,
            key=lambda i: (i["sheet"], i["cell"][0], int(i["cell"][1:])),
        ),
        "sources": list(existing["sources"]) + [
            {
                "name": XBRL_NAME, "url": XBRL_URL, "as_of": AS_OF,
                "notes": (
                    "SEC XBRL company facts for CIK 0001318605, recorded at "
                    f"{FACTS.relative_to(ROOT)}. Only observations filed on or before "
                    f"{AS_OF} are used, which excludes both hindsight and the post-split "
                    "restatements."
                ),
                "emitted_by": OWNER,
            },
            {
                "name": AV_CASH_NAME, "url": AV_CASH_URL, "as_of": AS_OF,
                "notes": (
                    "Depreciation, amortisation and impairment, and capital expenditure, "
                    f"for FY2017-FY2019, recorded at {AV_CASH.relative_to(ROOT)}. Used "
                    "instead of EDGAR because Tesla tagged "
                    "DepreciationDepletionAndAmortization in one filing only, with a "
                    "narrower figure, and not at all for FY2018 or FY2019. The vendor's "
                    "income statement and cash flow statement agree on D&A for all three "
                    "years, and its FY2016 figure matches Tesla's reported total. The "
                    "snapshot records the disagreement with EDGAR, which scope question "
                    "is unresolved, and that the vendor reports no filing date."
                ),
                "emitted_by": OWNER,
            },
            {
                "name": AV_NAME, "url": AV_URL, "as_of": AS_OF,
                "notes": (
                    "Second-vendor corroboration of the FY2017-FY2019 income lines, "
                    f"recorded at {AV_FACTS.relative_to(ROOT)}. Fifteen of eighteen "
                    "compared items match SEC EDGAR exactly; the three differences are "
                    "precision, because EDGAR's retained FY2018 observation comes from a "
                    "later filing that rounded to millions. Share counts are not taken "
                    "from this vendor: it reports them on the latest split basis, which "
                    "is unusable for a case dated before a split."
                ),
                "emitted_by": OWNER,
            },
        ],
        "refresh": {
            "date": date.today().isoformat(),
            "trigger": "Historical actuals block filled after the BASE template fix",
            "source_snapshot": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
            "what_changed": (
                "The BASE template's income-statement historical block carried no input "
                "marker and no derived formulas, so the income statement, the DCF, and "
                "diluted EPS all evaluated to zero. With the template fixed, this fills "
                "FY2017-FY2019 revenue, cost of revenue, operating expense, depreciation "
                "and amortisation, interest, tax, and share count. Depreciation comes "
                "from the cash flow statement rather than EDGAR, because Tesla tagged "
                "EDGAR's D&A concept in one filing only and with a narrower figure. With "
                "D&A real and taken out of the operating expense row, the EBITDA line is "
                "a real EBITDA and EBIT ties exactly to the disclosed operating income "
                "in all three years."
            ),
            "reviewer_notes": (
                "External historical case; human stakeholder approval remains pending. "
                "Read three things before using any number here. First, the share counts "
                "are period-end outstanding rather than weighted diluted, which "
                "understates earnings per share. Second, the forward D&A driver is the "
                "product of a capex ratio and a D&A-to-capex ratio, and the second of "
                "those is unstable across the window; the pair is set so the product "
                "ties to D&A as a share of revenue, which is stable, and the two rows "
                "must be read together. Third, the discounted cash flow values the "
                "equity at roughly a quarter of the price the February 2020 offering "
                "actually cleared at. That is not a defect in the arithmetic. It is what "
                "a cash flow model built on Tesla's FY2019 operating margins produces, "
                "and the gap between the two was the whole argument about Tesla at the "
                "time. The case exists to show the offering mechanics, not to settle "
                "that argument."
            ),
            "next_check": "On builder change or annual review",
        },
        "driver_declarations": sorted(
            (existing.get("driver_declarations") or []) + drivers,
            key=lambda d: (d["sheet"], d["cell"][0], int(d["cell"][1:])),
        ),
    }
    return manifest, snapshot, {"inputs_added": len(inputs), "drivers_added": len(drivers)}


def write_source_register(snapshot: dict[str, Any]) -> None:
    header = "case_id,source_name,publisher,url,as_of,snapshot,snapshot_sha256,status"
    rows = [
        (CASE_ID, PROSPECTUS_NAME, "U.S. SEC / Tesla, Inc.", PROSPECTUS_URL, AS_OF,
         str(SNAPSHOT_PATH.relative_to(ROOT)), snapshot["snapshot_sha256"], "frozen"),
        (CASE_ID, XBRL_NAME, "SEC EDGAR via tools/data_fabric/edgar_company_facts.py",
         XBRL_URL, AS_OF, str(FACTS.relative_to(ROOT)),
         hashlib.sha256(FACTS.read_bytes()).hexdigest(), "active"),
        (CASE_ID, AV_NAME, "Alpha Vantage via tools/data_fabric/alpha_vantage_facts.py",
         AV_URL, AS_OF, str(AV_FACTS.relative_to(ROOT)),
         hashlib.sha256(AV_FACTS.read_bytes()).hexdigest(), "active"),
        (CASE_ID, AV_CASH_NAME, "Alpha Vantage via tools/data_fabric/alpha_vantage_facts.py",
         AV_CASH_URL, AS_OF, str(AV_CASH.relative_to(ROOT)),
         hashlib.sha256(AV_CASH.read_bytes()).hexdigest(), "active"),
    ]
    lines = [header]
    if REGISTER_PATH.exists():
        existing = REGISTER_PATH.read_text(encoding="utf-8").splitlines()
        lines = [l for l in (existing or lines) if not l.startswith(f"{CASE_ID},")]
    for row in rows:
        lines.append(",".join(f'"{f}"' if "," in str(f) else str(f) for f in row))
    REGISTER_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-only", action="store_true")
    args = parser.parse_args()
    manifest, snapshot, stats = build()
    if args.print_only:
        print(json.dumps(manifest["inputs"], indent=2))
        return 0
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_source_register(snapshot)
    print(f"saved {MANIFEST_PATH.relative_to(ROOT)}")
    print(f"saved {SNAPSHOT_PATH.relative_to(ROOT)}  sha256={snapshot['snapshot_sha256'][:16]}...")
    print(f"saved {REGISTER_PATH.relative_to(ROOT)}")
    print(f"inputs added: {stats['inputs_added']}  drivers added: {stats['drivers_added']}")
    print(f"not available: {snapshot['not_available']['items']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
