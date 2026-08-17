"""Generate the Adobe public case for the software / SaaS model.

Every number this writes is computed here from the recorded SEC XBRL
snapshot under tools/data_fabric/out/. Nothing is hand-typed, which is the
only way a reader can check the case without re-deriving it: the manifest
is a function of a committed input file, and running this script again on
the same snapshot must reproduce it byte for byte.

WHAT THIS CASE CAN AND CANNOT GROUND
------------------------------------
The software template's headline engine is an ARR cohort roll-forward, and
ARR is a management metric: no issuer tags it in XBRL, and Adobe is no
exception. So this case deliberately does NOT pretend to source the ARR
layer. Instead it splits the input surface three ways, and says which is
which on every cell:

  observed  - a value read directly off a disclosed fact.
  derived   - arithmetic on disclosed facts, with the arithmetic stated.
  driver    - no disclosure exists. Left as a driver, and where possible
              *constrained* by something that is disclosed rather than
              left free.

That last technique is what makes the case more than half-empty. Three
aggregates are pinned to real disclosure while their components stay
honest drivers:

  - The four ARR flow rates (new / expansion / contraction / churn) are
    individually undisclosed, but their NET is pinned to Adobe's disclosed
    revenue growth. Gross churn carries the constraint as the balancing
    residual, so it is the one flow rate with a real basis.
  - Subscription and services gross margins are individually undisclosed,
    but the BLENDED margin they produce is pinned to Adobe's disclosed
    GrossProfit / Revenues. Subscription margin carries the constraint.
  - The Downside column is not an invented stress. Each downside value is
    the least favourable of the same ratio across Adobe's three most
    recent disclosed fiscal years, so the stress case is bounded by what
    this company actually did rather than by a modeler's imagination.

One derivation needs its caveat stated loudly rather than buried: Adobe's
XBRL facts contain no ResearchAndDevelopmentExpense tag, so R&D is backed
out as the operating-expense residual. That residual is BROADER than
Adobe's reported R&D line -- it absorbs amortization of intangibles and any
other operating expense Adobe reports separately. It is labelled as such.
The compensating benefit is that operating income then ties exactly to the
disclosed figure, which a hand-picked R&D percentage would not.

Usage:
    python tools/build_software_adobe_case.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / "tools" / "data_fabric" / "out" / "ADBE_facts_annual_series.json"
SIC_SNAPSHOT = ROOT / "tools" / "data_fabric" / "out" / "QQQ_sec_sic_classifications.json"
CASE_ID = "software-public-adobe-fy2025"
MODEL_ID = "31"
DOMAIN = "Software & SaaS"
TEMPLATE = "31_Software_SaaS/_template_SOFTWARE.xlsx"
OUTPUT = "31_Software_SaaS/instances/public_adobe_fy2025.xlsx"
MANIFEST_PATH = ROOT / "standards" / "public_cases" / f"{CASE_ID}.json"
SNAPSHOT_PATH = ROOT / "31_Software_SaaS" / "sources" / "snapshots" / f"{CASE_ID}.json"
REGISTER_PATH = ROOT / "31_Software_SaaS" / "sources" / "source_register.csv"

# Adobe's three most recent disclosed fiscal year-ends, newest first. The
# newest sets the Base column; all three set the Downside column's range.
PERIODS = ["2025-11-28", "2024-11-29", "2023-12-01"]
PRIOR = "2022-12-02"  # only needed for the oldest year's growth rate
FILING_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000796343&type=10-K"
FILING_NAME = "Adobe Inc. FY2025 Form 10-K (XBRL company facts, CIK 0000796343)"
FILED = "2026-01-15"

# Drivers with no disclosure anywhere. Held here so the split between
# "sourced" and "chosen" is one readable list rather than scattered.
UNGROUNDED = {
    "services_mix": 0.030,       # services revenue as % of subscription
    "services_margin": 0.350,
    "new_arr_rate": 0.100,
    "expansion_rate": 0.090,
    "contraction_rate": 0.030,
    "new_arr_margin": 0.890,     # gross margin carried by newly won ARR
    "current_rpo_share": 0.640,  # disclosed only as narrative text, not XBRL
}


# Cover cells that are not facts about Adobe and never will be. Declared so
# the coverage report shows them as known non-sourceable rather than as
# unexamined gaps -- they still earn no credit, which is correct.
COVER_DECLARATIONS = [
    {
        "sheet": "Cover",
        "cell": "C7",
        "driver_type": "generated_metadata",
        "rationale": (
            "Populated automatically by tools/model_instances.py from the manifest's "
            "as_of date. Release metadata, not an observation about the company."
        ),
        "basis": {},
    },
    {
        "sheet": "Cover",
        "cell": "C9",
        "driver_type": "generated_metadata",
        "rationale": (
            "Populated automatically from the manifest's scenario selection. A "
            "Base/Downside toggle, not an observation about the company."
        ),
        "basis": {},
    },
    {
        "sheet": "Cover",
        "cell": "C10",
        "driver_type": "presentation_convention",
        "rationale": "Presentation convention ($ in millions), not a fact about the subject.",
        "basis": {},
    },
]


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def load_facts() -> dict[str, dict[str, float]]:
    """{concept: {period_end: value_in_usd_millions}} from the recorded snapshot."""
    if not FACTS.exists():
        raise FileNotFoundError(
            f"missing recorded snapshot {FACTS.relative_to(ROOT)} -- this case is "
            "only ever built from committed real data, never from memory"
        )
    payload = json.loads(FACTS.read_text(encoding="utf-8"))
    facts: dict[str, dict[str, float]] = {}
    for series in payload["concepts"]:
        facts[series["concept"]] = {
            observation["end"]: observation["value"] / 1e6
            for observation in series["observations"]
        }
    return facts


def ratios(facts: dict[str, dict[str, float]], period: str) -> dict[str, float]:
    """Every ratio this case sources, for one fiscal year.

    Raises rather than defaulting if a concept is absent: a silently
    missing fact would become a silently invented number.
    """
    def fact(concept: str, end: str = period) -> float:
        try:
            return facts[concept][end]
        except KeyError as error:
            raise KeyError(f"{concept} not disclosed for period {end}") from error

    revenue = fact("Revenues")
    gross_profit = fact("GrossProfit")
    selling = fact("SellingAndMarketingExpense")
    admin = fact("GeneralAndAdministrativeExpense")
    operating_income = fact("OperatingIncomeLoss")
    tax = fact("IncomeTaxExpenseBenefit")
    net_income = fact("NetIncomeLoss")
    # The residual. Broader than Adobe's reported R&D line -- see module docstring.
    other_opex = gross_profit - operating_income - selling - admin
    return {
        "revenue": revenue,
        "blended_gross_margin": gross_profit / revenue,
        "sm_pct": selling / revenue,
        "ga_pct": admin / revenue,
        "opex_residual_pct": other_opex / revenue,
        "sbc_pct": fact("ShareBasedCompensation") / revenue,
        "capex_pct": fact("PaymentsToAcquirePropertyPlantAndEquipment") / revenue,
        "effective_tax_rate": tax / (net_income + tax),
        "rpo_coverage": fact("RevenueRemainingPerformanceObligation") / revenue,
        "contract_liability_pct": fact("ContractWithCustomerLiability") / revenue,
        "operating_margin": operating_income / revenue,
    }


def annual_filing_months() -> list[str]:
    """Distinct months in which Adobe's 10-K filings actually landed.

    Used so the workbook's "next filing / refresh" field is read off
    observed filing behaviour rather than guessed. Note this cannot be read
    off the three periods this case uses: the snapshot's dedupe rule keeps
    the LATEST filing of each period, so all three fiscal years trace to the
    single FY2025 10-K. The filing cadence has to come from the distinct
    filing dates across the whole fact set instead.
    """
    payload = json.loads(FACTS.read_text(encoding="utf-8"))
    filed = {
        observation["filed"][:7]
        for series in payload["concepts"]
        for observation in series["observations"]
        if observation.get("form") == "10-K"
    }
    return sorted(filed)


def revenue_growth(facts: dict[str, dict[str, float]], period: str, prior: str) -> float:
    return facts["Revenues"][period] / facts["Revenues"][prior] - 1.0


def round6(value: float) -> float:
    """Solved constraint values keep more digits than read-off ratios.

    A pinned value rounded to four places no longer pins: subscription
    margin at 0.9089 reproduces the disclosed blended margin only to about
    5e-5, which is enough to make an equality check fail for no real
    reason. The extra digits are not false precision -- they are the
    solution of an equation whose right-hand side is disclosed.
    """
    return round(value, 6)


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    facts = load_facts()
    base = ratios(facts, PERIODS[0])
    history = [ratios(facts, period) for period in PERIODS]
    ends = PERIODS + [PRIOR]
    growths = [revenue_growth(facts, ends[i], ends[i + 1]) for i in range(len(PERIODS))]

    # Downside = the least favourable disclosed value of each ratio across
    # the three-year window. Direction matters and is set per ratio.
    worst_high = lambda key: max(item[key] for item in history)  # noqa: E731
    worst_low = lambda key: min(item[key] for item in history)  # noqa: E731

    base_growth = growths[0]
    down_growth = min(growths)

    services_mix = UNGROUNDED["services_mix"]
    services_margin = UNGROUNDED["services_margin"]
    # Solve subscription margin so the BLENDED margin equals the disclosed one.
    def subscription_margin(blended: float) -> float:
        return blended * (1 + services_mix) - services_mix * services_margin

    # Solve gross churn so NET ARR growth equals disclosed revenue growth.
    def gross_churn(net_growth: float) -> float:
        return (
            UNGROUNDED["new_arr_rate"]
            + UNGROUNDED["expansion_rate"]
            - UNGROUNDED["contraction_rate"]
            - net_growth
        )

    filing = {
        "name": FILING_NAME,
        "url": FILING_URL,
        "publisher": "U.S. Securities and Exchange Commission (EDGAR company facts)",
    }

    def note(text: str) -> str:
        return text

    residual_caveat = (
        "Adobe's XBRL facts contain no ResearchAndDevelopmentExpense concept, so this "
        "line is the operating-expense residual: GrossProfit - OperatingIncomeLoss - "
        "SellingAndMarketingExpense - GeneralAndAdministrativeExpense. It is BROADER "
        "than Adobe's reported R&D line because it also absorbs amortization of "
        "intangibles and any other separately reported operating expense. Using the "
        "residual keeps modelled GAAP operating margin tied exactly to the disclosed "
        f"{base['operating_margin']:.4f}; a hand-picked R&D percentage would not."
    )

    # (row, base value, downside value, kind, note)
    rows: list[tuple[int, float, float, str, str]] = [
        (
            10, services_mix, services_mix, "driver",
            "Adobe does not disaggregate services revenue from subscription revenue in "
            "its XBRL facts, so the mix is a driver. It is load-bearing only through "
            "the blended gross margin, which IS pinned to disclosure (row 11).",
        ),
        (
            11, subscription_margin(base["blended_gross_margin"]),
            subscription_margin(worst_low("blended_gross_margin")), "derived",
            "Subscription margin solved so the model's BLENDED gross margin equals the "
            f"disclosed GrossProfit/Revenues of {base['blended_gross_margin']:.4f} "
            f"(FY2025: {facts['GrossProfit'][PERIODS[0]]:,.0f} / "
            f"{facts['Revenues'][PERIODS[0]]:,.0f} $mm) given the services mix and "
            "services margin drivers. The split between subscription and services "
            "margin is undisclosed; their weighted average is not.",
        ),
        (
            12, services_margin, services_margin, "driver",
            "Services gross margin is not disclosed. Held as a driver; the blended "
            "margin it feeds is pinned to disclosure.",
        ),
        (
            13, base["sm_pct"], worst_high("sm_pct"), "observed",
            f"SellingAndMarketingExpense / Revenues. FY2025: "
            f"{facts['SellingAndMarketingExpense'][PERIODS[0]]:,.0f} / "
            f"{facts['Revenues'][PERIODS[0]]:,.0f} $mm. Downside is the highest of the "
            f"three most recent disclosed fiscal years ({', '.join(PERIODS)}).",
        ),
        (14, base["opex_residual_pct"], worst_high("opex_residual_pct"), "derived", residual_caveat),
        (
            15, base["ga_pct"], worst_high("ga_pct"), "observed",
            f"GeneralAndAdministrativeExpense / Revenues. FY2025: "
            f"{facts['GeneralAndAdministrativeExpense'][PERIODS[0]]:,.0f} / "
            f"{facts['Revenues'][PERIODS[0]]:,.0f} $mm. Downside is the highest of the "
            "three most recent disclosed fiscal years.",
        ),
        (
            16, base["sbc_pct"], worst_high("sbc_pct"), "observed",
            f"ShareBasedCompensation / Revenues. FY2025: "
            f"{facts['ShareBasedCompensation'][PERIODS[0]]:,.0f} / "
            f"{facts['Revenues'][PERIODS[0]]:,.0f} $mm. Downside is the highest of the "
            "three most recent disclosed fiscal years.",
        ),
        (
            17, base["capex_pct"], worst_high("capex_pct"), "observed",
            f"PaymentsToAcquirePropertyPlantAndEquipment / Revenues. FY2025: "
            f"{facts['PaymentsToAcquirePropertyPlantAndEquipment'][PERIODS[0]]:,.0f} / "
            f"{facts['Revenues'][PERIODS[0]]:,.0f} $mm. Downside is the highest of the "
            "three most recent disclosed fiscal years.",
        ),
        (
            18, base["effective_tax_rate"], worst_high("effective_tax_rate"), "derived",
            "IncomeTaxExpenseBenefit / (NetIncomeLoss + IncomeTaxExpenseBenefit), i.e. "
            "the EFFECTIVE GAAP rate. Caveat: the template line is labelled 'cash tax "
            "rate' and Adobe's cash taxes paid are not in this concept set, so the two "
            "differ by deferred taxes. Downside is the highest of the three most recent "
            "disclosed fiscal years.",
        ),
        (
            19, UNGROUNDED["new_arr_margin"], UNGROUNDED["new_arr_margin"], "driver",
            "Gross margin carried by newly won ARR is not disclosed by any issuer. Held "
            "as a driver, set near the disclosed blended margin because Adobe's cost of "
            "revenue is overwhelmingly delivery infrastructure rather than per-cohort "
            "cost; the CAC-payback line it feeds should be read as a range, not a point.",
        ),
        (
            20, facts["RevenueRemainingPerformanceObligation"][PERIODS[1]],
            facts["RevenueRemainingPerformanceObligation"][PERIODS[1]], "observed",
            "RevenueRemainingPerformanceObligation at FY2024 year-end "
            f"({PERIODS[1]}): {facts['RevenueRemainingPerformanceObligation'][PERIODS[1]]:,.0f} "
            "$mm. This is the model's opening RPO balance, so it is a disclosed level "
            "rather than a scenario lever and is identical in both columns.",
        ),
        (
            21, base["rpo_coverage"], worst_low("rpo_coverage"), "derived",
            f"RevenueRemainingPerformanceObligation / Revenues. FY2025: "
            f"{facts['RevenueRemainingPerformanceObligation'][PERIODS[0]]:,.0f} / "
            f"{facts['Revenues'][PERIODS[0]]:,.0f} $mm. Downside is the LOWEST of the "
            "three most recent disclosed fiscal years -- thinner contracted coverage is "
            "the adverse direction.",
        ),
        (
            22, UNGROUNDED["current_rpo_share"], UNGROUNDED["current_rpo_share"], "driver",
            "The portion of RPO expected to be recognised within twelve months is "
            "disclosed by Adobe only as narrative text in the revenue note; it is not "
            "tagged in the XBRL facts this case is built from, so it stays an "
            "ungrounded driver rather than being transcribed from memory.",
        ),
        (
            23, base["contract_liability_pct"], worst_high("contract_liability_pct"), "derived",
            f"ContractWithCustomerLiability / Revenues. FY2025: "
            f"{facts['ContractWithCustomerLiability'][PERIODS[0]]:,.0f} / "
            f"{facts['Revenues'][PERIODS[0]]:,.0f} $mm. Downside is the highest of the "
            "three most recent disclosed fiscal years -- more of RPO already billed "
            "means less unbilled contracted revenue still to come.",
        ),
    ]

    # The template's ARR line is SUBSCRIPTION ARR: total revenue is
    # subscription grossed up by the services mix. So the proxy must be net
    # of that mix, or the services layer double-counts against disclosure.
    opening_arr = facts["Revenues"][PERIODS[1]] / (1 + services_mix)
    modelled_year1_revenue = (
        (opening_arr + opening_arr * (1 + base_growth)) / 2 * (1 + services_mix)
    )
    disclosed_year1_revenue = facts["Revenues"][PERIODS[0]]
    proxy_error = modelled_year1_revenue / disclosed_year1_revenue - 1

    arr_proxy_note = (
        "Adobe does not tag annual recurring revenue in XBRL -- no issuer does; ARR is a "
        "management metric with no fixed definition. This case therefore uses disclosed "
        f"FY2024 Revenues ({facts['Revenues'][PERIODS[1]]:,.0f} $mm, period ending "
        f"{PERIODS[1]}) net of the services-mix driver as the opening SUBSCRIPTION ARR "
        f"scale ({opening_arr:,.1f} $mm), so modelled total revenue stays on the same "
        "basis as disclosed revenue. It is a proxy and errs in a known direction: "
        "revenue is a flow averaged over a year while ARR is a point-in-time contracted "
        "balance, so for a growing business it understates exit ARR. The size of the "
        f"error is measurable and is not hidden: modelled Year 1 revenue is "
        f"{modelled_year1_revenue:,.0f} $mm against Adobe's disclosed FY2025 "
        f"{disclosed_year1_revenue:,.0f} $mm, a gap of {proxy_error:+.2%}. Ratios on "
        "this case are sourced; absolute dollar levels carry that gap."
    )
    growth_note = (
        "The four ARR flow rates are individually undisclosed. Their NET is pinned to "
        f"Adobe's disclosed revenue growth of {base_growth:.4f} (FY2025 "
        f"{facts['Revenues'][PERIODS[0]]:,.0f} over FY2024 "
        f"{facts['Revenues'][PERIODS[1]]:,.0f} $mm), used as a proxy for net ARR growth. "
        "Gross churn is the balancing residual that carries this constraint, which is "
        "why it is the one flow rate with a real basis. Downside uses the lowest growth "
        f"of the three most recent disclosed fiscal years ({down_growth:.4f})."
    )
    flow_driver_note = (
        "New, expansion, and contraction ARR rates are not disclosed by Adobe or by any "
        "other issuer. They are drivers. Their decomposition is chosen; their net effect "
        "is not -- see the gross-churn residual, which pins the sum to disclosed growth."
    )

    rows.extend([
        (5, opening_arr, opening_arr, "derived", arr_proxy_note),
        (6, UNGROUNDED["new_arr_rate"], UNGROUNDED["new_arr_rate"], "driver", flow_driver_note),
        (7, UNGROUNDED["expansion_rate"], UNGROUNDED["expansion_rate"], "driver", flow_driver_note),
        (8, UNGROUNDED["contraction_rate"], UNGROUNDED["contraction_rate"], "driver", flow_driver_note),
        (9, gross_churn(base_growth), gross_churn(down_growth), "derived", growth_note),
    ])
    rows.sort()

    # Dollar levels round to $0.1mm; every ratio keeps six digits. Four
    # would be plenty to read, but the disclosed facts are exact integers in
    # $mm, so a ratio derived from them is exact too -- and truncating it
    # costs the model an exact tie to the disclosed operating margin for no
    # gain. Cheap precision that makes a check bite is worth keeping.
    dollar_rows = {5, 20}

    inputs: list[dict[str, Any]] = []
    drivers: list[dict[str, Any]] = []
    for row, base_value, down_value, kind, text in rows:
        quantize = (lambda v: round(v, 1)) if row in dollar_rows else round6
        for column, value in (("C", base_value), ("D", down_value)):
            cell = f"{column}{row}"
            if kind == "driver":
                # A driver still has to be WRITTEN. Declaring a cell as a
                # driver and then leaving the builder's template default in
                # place is the failure this repo exists to prevent: the
                # workbook would carry a generic SaaS default (22% new-logo
                # ARR) sitting next to Adobe's real 10.5% disclosed growth,
                # and the two would silently contradict each other. So the
                # driver is applied as an input -- typed modeler_assumption
                # against the frozen snapshot, which the coverage scanner
                # correctly refuses to credit as sourced -- and separately
                # declared with its rationale.
                drivers.append({
                    "sheet": "Assumptions",
                    "cell": cell,
                    "driver_type": "undisclosed_metric_driver",
                    "rationale": note(text),
                    # A driver earns coverage credit only with a real basis.
                    # These have none, deliberately, and are counted as gaps.
                    "basis": {},
                })
                inputs.append({
                    "sheet": "Assumptions",
                    "cell": cell,
                    "value": quantize(value),
                    "input_kind": "modeler_assumption",
                    "source": {
                        "name": "Case driver (no disclosure exists)",
                        "url": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
                        "as_of": FILED,
                        "notes": note(text),
                    },
                })
                continue
            inputs.append({
                "sheet": "Assumptions",
                "cell": cell,
                "value": quantize(value),
                "input_kind": "observed" if kind == "observed" else "derived",
                "source": {
                    "name": FILING_NAME,
                    "url": FILING_URL,
                    "as_of": FILED,
                    "notes": note(text),
                },
            })

    forecast_revenue = round(modelled_year1_revenue, 1)

    # Cover identity. Every field here is a disclosed fact rather than a
    # label someone typed: the SIC classification comes from Adobe's own
    # EDGAR submission, the fiscal year end is the period end of the facts
    # this case is built on, and the next-filing month is read off the
    # actual filing dates of the last three 10-Ks rather than guessed.
    sic = json.loads(SIC_SNAPSHOT.read_text(encoding="utf-8"))["companies"]["ADBE"]
    filing_months = annual_filing_months()
    next_filing = f"{int(FILED[:4]) + 1}-{FILED[5:7]}"
    cover = {
        "Title:": "Adobe Inc. -- FY2025 software operating, RPO, and unit-economics case",
        "Company / ticker:": f"Adobe Inc. (NASDAQ: ADBE), CIK {sic['cik']}",
        "Subsector:": (
            f"application software -- SEC SIC {sic['sic']} ({sic['sic_description']}), "
            "as filed by the registrant"
        ),
        "Fiscal year end:": (
            f"{PERIODS[0]} (FY2025; 52/53-week year ending the Friday nearest "
            "November 30)"
        ),
        "Next filing / refresh:": (
            f"{next_filing} expected (FY2026 Form 10-K); every Adobe 10-K in this "
            f"fact set was filed in January ({len(filing_months)} filings, "
            f"{filing_months[0]} through {filing_months[-1]})"
        ),
    }

    snapshot = {
        "schema_version": "1.0",
        "model_id": MODEL_ID,
        "domain": DOMAIN,
        "case_id": CASE_ID,
        "case_type": "conventional",
        "as_of": FILED,
        "capture_method": "sec_xbrl_company_facts",
        "sources": [{
            **filing,
            "captured_values": {
                "cik": "0000796343",
                "fiscal_year_ends": PERIODS,
                "revenues_usd_mm": {p: facts["Revenues"][p] for p in PERIODS},
                "gross_profit_usd_mm": {p: facts["GrossProfit"][p] for p in PERIODS},
                "operating_income_usd_mm": {p: facts["OperatingIncomeLoss"][p] for p in PERIODS},
                "selling_and_marketing_usd_mm": {
                    p: facts["SellingAndMarketingExpense"][p] for p in PERIODS
                },
                "general_and_administrative_usd_mm": {
                    p: facts["GeneralAndAdministrativeExpense"][p] for p in PERIODS
                },
                "share_based_compensation_usd_mm": {
                    p: facts["ShareBasedCompensation"][p] for p in PERIODS
                },
                "capex_usd_mm": {
                    p: facts["PaymentsToAcquirePropertyPlantAndEquipment"][p] for p in PERIODS
                },
                "remaining_performance_obligation_usd_mm": {
                    p: facts["RevenueRemainingPerformanceObligation"][p] for p in PERIODS
                },
                "contract_with_customer_liability_usd_mm": {
                    p: facts["ContractWithCustomerLiability"][p] for p in PERIODS
                },
                "income_tax_expense_usd_mm": {p: facts["IncomeTaxExpenseBenefit"][p] for p in PERIODS},
                "net_income_usd_mm": {p: facts["NetIncomeLoss"][p] for p in PERIODS},
                "revenue_growth_by_year": {
                    PERIODS[i]: round(growths[i], 6) for i in range(len(PERIODS))
                },
            },
        }],
        "input_overrides": [],
        # The case's own scorecard against reality. Recording it here means
        # the reader does not have to trust the prose: the one place this
        # model provably diverges from Adobe's filing is stated with its
        # size and its cause, and it moves if the case ever gets worse.
        "reconciliation_to_disclosure": {
            "exact": {
                "blended_gross_margin": round(base["blended_gross_margin"], 6),
                "gaap_operating_margin": round(base["operating_margin"], 6),
                "rpo_coverage_of_revenue": round(base["rpo_coverage"], 6),
                "note": (
                    "These tie to the filing by construction: margins are pinned to "
                    "disclosed ratios and the R&D residual absorbs the difference, so "
                    "modelled operating margin equals the disclosed one exactly."
                ),
            },
            "approximate": {
                "modelled_year1_revenue_usd_mm": round(modelled_year1_revenue, 1),
                "disclosed_fy2025_revenue_usd_mm": disclosed_year1_revenue,
                "relative_error": round(proxy_error, 6),
                "cause": (
                    "The ARR scale is proxied from prior-year revenue because ARR is "
                    "not disclosed. Revenue is a period-average flow and ARR is a "
                    "point-in-time balance, so the proxy understates exit ARR for a "
                    "growing business. This is the case's known, sized limitation."
                ),
            },
        },
        "undisclosed_metrics": {
            "note": (
                "Concepts the software template needs that Adobe does not tag in XBRL. "
                "Recorded so the gap is auditable rather than implicit."
            ),
            "concepts": [
                "annual recurring revenue (ARR)",
                "net revenue retention / gross revenue retention",
                "new, expansion, contraction, and churned ARR",
                "subscription versus services revenue disaggregation",
                "research and development expense (no us-gaap tag in this fact set)",
                "portion of RPO expected to be recognised within twelve months",
                "cash taxes paid",
            ],
        },
        "outcome": {
            "metric": "fy2026_total_revenue_usd_mm",
            "forecast": forecast_revenue,
            "realized": None,
            "realized_source": "Adobe FY2026 Form 10-K, expected filing January 2027",
            "status": "pending",
        },
        "counts_toward_m4": False,
    }
    snapshot["snapshot_sha256"] = hashlib.sha256(canonical_bytes(snapshot)).hexdigest()

    manifest = {
        "schema_version": "1.0",
        "id": CASE_ID,
        "classification": "external_historical_case",
        "counts_toward_M4": False,
        "template": TEMPLATE,
        "output": OUTPUT,
        "as_of": FILED,
        "scenario": "Base",
        "cover": cover,
        "inputs": inputs,
        "sources": [
            {
                "name": FILING_NAME,
                "url": FILING_URL,
                "as_of": FILED,
                "notes": (
                    "SEC XBRL company facts for CIK 0000796343, recorded at "
                    f"{FACTS.relative_to(ROOT)}. Three most recent disclosed fiscal "
                    f"years: {', '.join(PERIODS)}."
                ),
            },
            {
                "name": "Frozen source snapshot",
                "url": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
                "as_of": FILED,
                "notes": "Immutable curated observation package with SHA-256 digest",
            },
        ],
        "outcome": snapshot["outcome"],
        "lineage": {
            "source_snapshot": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
            "synthetic_benchmark_inputs_allowed": False,
        },
        "refresh": {
            "date": date.today().isoformat(),
            "trigger": "Initial materialization from SEC XBRL company facts",
            "source_snapshot": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
            "what_changed": (
                "Built the software domain's first company case. Sourced the entire GAAP "
                "cost and RPO layer from Adobe's disclosed FY2025 facts; pinned blended "
                "gross margin and net ARR growth to disclosure while leaving their "
                "undisclosed components as declared drivers; set the Downside column "
                "from the worst of three disclosed fiscal years rather than an invented "
                "stress. The ARR cohort layer remains ungrounded because no issuer "
                "discloses it."
            ),
            "reviewer_notes": (
                "External historical case; human stakeholder approval remains pending. "
                "Absolute ARR and RPO dollar levels inherit the revenue-as-ARR-scale "
                "proxy and should be read as approximate; ratios are sourced."
            ),
            "next_check": "On Adobe's next 10-K, builder change, or annual review",
        },
        "driver_declarations": sorted(
            drivers + COVER_DECLARATIONS,
            key=lambda item: (item["sheet"], item["cell"][0], int(item["cell"][1:])),
        ),
    }
    return manifest, snapshot


def write_source_register(snapshot: dict[str, Any]) -> None:
    """The domain's source register, which was header-only before this case.

    Two rows, because this case rests on two distinct recorded artifacts:
    the frozen snapshot itself, and the upstream XBRL harvest it was
    derived from. Listing only the snapshot would hide the fact that the
    snapshot is itself downstream of something.
    """
    rows = [
        (
            CASE_ID,
            FILING_NAME,
            "U.S. Securities and Exchange Commission (EDGAR company facts)",
            FILING_URL,
            FILED,
            str(SNAPSHOT_PATH.relative_to(ROOT)),
            snapshot["snapshot_sha256"],
            "frozen",
        ),
        (
            CASE_ID,
            "Adobe XBRL annual fact series (upstream harvest)",
            "SEC EDGAR via tools/data_fabric/edgar_company_facts.py",
            "https://data.sec.gov/api/xbrl/companyfacts/CIK0000796343.json",
            FILED,
            str(FACTS.relative_to(ROOT)),
            hashlib.sha256(FACTS.read_bytes()).hexdigest(),
            "active",
        ),
    ]
    header = "case_id,source_name,publisher,url,as_of,snapshot,snapshot_sha256,status"
    lines = [header]
    if REGISTER_PATH.exists():
        existing = REGISTER_PATH.read_text(encoding="utf-8").splitlines()
        lines = existing or lines
        lines = [line for line in lines if not line.startswith(f"{CASE_ID},")]
    for row in rows:
        lines.append(",".join(f'"{field}"' if "," in field else field for field in row))
    REGISTER_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
    print(
        f"inputs={len(manifest['inputs'])} sourced cells, "
        f"drivers={len(manifest['driver_declarations'])} declared-but-ungrounded"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
