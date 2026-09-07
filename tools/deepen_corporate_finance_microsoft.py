"""Deepen the Microsoft FY2024 corporate-finance case from recorded SEC XBRL.

The case shipped with 18 sourced cells out of 135 candidates -- 13.3% real,
all of them on one sheet. The DCF's forward driver grid, the comparable-
companies table, and the treasury policy screens were all left at template
defaults of literal zero, which is worse than a wrong number: a zero revenue
growth rate and a zero WACC look like data rather than like blanks.

THE DISCIPLINE THAT SHAPES THIS CASE
------------------------------------
The case is dated 2024-06-30. Its Assumptions sheet is a FORWARD driver grid
(FY1..FY5 = FY2025..FY2029), and the recorded fact set contains Microsoft's
actual FY2025 and FY2026 results. Using them would manufacture a forecast
that already knows the answer -- the exact hindsight defect this repository
previously went through and fixed.

So every forward driver here is derived ONLY from fiscal years ending on or
before the case's as-of date (FY2020..FY2024). The later years are
deliberately left on the table. `assert_no_hindsight()` enforces this
mechanically rather than trusting the author to remember.

WHAT IS AND IS NOT SOURCEABLE
-----------------------------
Operating drivers -- growth, margin, opex intensity, tax rate, capex
intensity, working-capital sensitivity, share count -- all fall out of tagged
facts. Three do not, and stay declared drivers:

  - D&A as a share of capex. Microsoft tags no
    DepreciationDepletionAndAmortization concept in this fact set.
  - WACC. A market-derived quantity, not an issuer disclosure.
  - Terminal growth. A modeler's judgment about the far future.

The comparable-companies table is the honest casualty. It wants price, market
cap, and enterprise value; XBRL carries none of them, and no market-data host
is reachable from this environment. So the PEER SET itself is sourced -- seven
issuers sharing Microsoft's SEC-filed SIC code, drawn from the recorded
corpus -- and every price-derived column stays a declared driver. A comps
sheet with real tickers and blank multiples is a truthful statement about
what we can and cannot see; one with invented multiples is not.

EXISTING SOURCED CELLS ARE NOT OVERWRITTEN
------------------------------------------
The eighteen values already sourced from the FY2024 10-K stay exactly as
they are, including two this script could have "corrected" from XBRL:
cash interest (10-K: 1,700; us-gaap:InterestExpense: 2,935) and EBITDA
(10-K: 109,400; us-gaap:OperatingIncomeLoss: 109,433). Those gaps are real
and probably reflect different line-item definitions, but this script cannot
read the filing to adjudicate them, and silently replacing a sourced number
with a differently-defined one is not an improvement. They are recorded as
open questions in the snapshot instead.

Usage:
    python tools/deepen_corporate_finance_microsoft.py
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
SIC_SNAPSHOT = ROOT / "tools" / "data_fabric" / "out" / "QQQ_sec_sic_classifications.json"
CASE_ID = "corporate-public-microsoft-2024"
MODEL_ID = "02"
FOLDER = "02_Corporate_Finance"
MANIFEST_PATH = ROOT / "standards" / "public_cases" / f"{CASE_ID}.json"
SNAPSHOT_PATH = ROOT / FOLDER / "sources" / "snapshots" / f"{CASE_ID}.json"
REGISTER_PATH = ROOT / FOLDER / "sources" / "source_register.csv"

AS_OF = "2024-06-30"
# Fiscal years usable by this case. Anything later is hindsight.
HISTORY = ["2020-06-30", "2021-06-30", "2022-06-30", "2023-06-30", "2024-06-30"]
FORWARD_COLUMNS = ["C", "D", "E", "F", "G"]  # FY2025..FY2029

REVENUE = "RevenueFromContractWithCustomerExcludingAssessedTax"
TEN_K_URL = (
    "https://www.sec.gov/Archives/edgar/data/789019/000095017024087843/msft-20240630.htm"
)
TEN_K_NAME = "Microsoft 2024 Form 10-K"
XBRL_NAME = "Microsoft FY2020-FY2024 XBRL company facts (CIK 0000789019)"
XBRL_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json"
SIC_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&SIC=7372"

# Undisclosed by any issuer, or unreachable from this environment.
UNGROUNDED = {
    "da_share_of_capex": 0.55,
    "wacc": 0.085,
    "terminal_growth": 0.025,
    "minimum_cash": 20000.0,
    "max_net_leverage": 2.00,
    "min_interest_coverage": 10.00,
}


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def load_xbrl() -> dict[str, dict[str, float]]:
    if not FACTS.exists():
        raise FileNotFoundError(f"missing recorded snapshot {FACTS.relative_to(ROOT)}")
    payload = json.loads(FACTS.read_text(encoding="utf-8"))
    return {
        series["concept"]: {
            observation["end"]: observation["value"] / 1e6
            for observation in series["observations"]
        }
        for series in payload["concepts"]
    }


def assert_no_hindsight() -> None:
    """Fail loudly if any period this case consumes postdates its as-of date.

    A forward driver grid built from data the modeler could not have had is
    not a forecast, and the defect is invisible once the numbers are in the
    workbook. Checking it here makes it impossible to reintroduce by editing
    HISTORY without noticing.
    """
    late = [end for end in HISTORY if end > AS_OF]
    if late:
        raise ValueError(
            f"hindsight: {late} postdate the case as_of {AS_OF}. A forward "
            "driver derived from data published after the case date is not a "
            "forecast; it is a lookup of the answer."
        )


def peer_set() -> list[tuple[str, str]]:
    """Issuers sharing Microsoft's SEC-filed SIC code, from recorded data.

    Peer SELECTION is the one part of a comps sheet that can be sourced
    without market data: the SIC code is a fact each registrant files. The
    multiples cannot be, so they stay drivers.
    """
    classifications = json.loads(SIC_SNAPSHOT.read_text(encoding="utf-8"))["companies"]
    microsoft_sic = classifications["MSFT"]["sic"]
    recorded = {
        path.name.split("_facts_")[0]
        for path in (ROOT / "tools" / "data_fabric" / "out").glob("*_facts_annual_series.json")
    }
    peers = sorted(
        (symbol, meta["name"])
        for symbol, meta in classifications.items()
        if meta.get("sic") == microsoft_sic and symbol != "MSFT" and symbol in recorded
    )
    if len(peers) < 7:
        raise ValueError(
            f"only {len(peers)} SIC-{microsoft_sic} peers are present in the recorded "
            "corpus; the comps table reserves seven rows and must not be padded"
        )
    return peers[:7]


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    assert_no_hindsight()
    xbrl = load_xbrl()

    def fact(concept: str, end: str) -> float:
        try:
            return xbrl[concept][end]
        except KeyError as error:
            raise KeyError(f"{concept} not disclosed for {end}") from error

    revenue = [fact(REVENUE, end) for end in HISTORY]
    growth = [revenue[i + 1] / revenue[i] - 1 for i in range(len(revenue) - 1)]
    latest = HISTORY[-1]

    gross_margin = fact("GrossProfit", latest) / revenue[-1]
    opex_ratio = (
        fact("GrossProfit", latest) - fact("OperatingIncomeLoss", latest)
    ) / revenue[-1]
    tax_rate = fact("IncomeTaxExpenseBenefit", latest) / (
        fact("NetIncomeLoss", latest) + fact("IncomeTaxExpenseBenefit", latest)
    )
    capex_ratio = fact("PaymentsToAcquirePropertyPlantAndEquipment", latest) / revenue[-1]

    working_capital = [
        fact("AssetsCurrent", end) - fact("LiabilitiesCurrent", end) for end in HISTORY
    ]
    nwc_sensitivity = sum(
        (working_capital[i + 1] - working_capital[i]) / (revenue[i + 1] - revenue[i])
        for i in range(len(revenue) - 1)
    ) / len(growth)

    shares_latest = fact("CommonStockSharesOutstanding", latest)
    shares_first = fact("CommonStockSharesOutstanding", HISTORY[0])
    share_cagr = (shares_latest / shares_first) ** (1 / len(growth)) - 1

    # Revenue growth fades from the trailing mean to the SLOWEST year actually
    # observed. Both endpoints are real observations; only the linear shape
    # between them is a modeling choice, and it is labelled as one.
    mean_growth = sum(growth) / len(growth)
    slowest_growth = min(growth)
    growth_path = [
        mean_growth + (slowest_growth - mean_growth) * index / (len(FORWARD_COLUMNS) - 1)
        for index in range(len(FORWARD_COLUMNS))
    ]
    share_path = [shares_latest * (1 + share_cagr) ** (index + 1) for index in range(5)]

    window = f"FY{HISTORY[0][:4]}-FY{HISTORY[-1][:4]}"
    capex_series = ", ".join(
        "{:.4f}".format(
            fact("PaymentsToAcquirePropertyPlantAndEquipment", end) / fact(REVENUE, end)
        )
        for end in HISTORY
    )
    nwc_series = ", ".join(
        "{:.4f}".format(
            (working_capital[i + 1] - working_capital[i]) / (revenue[i + 1] - revenue[i])
        )
        for i in range(len(growth))
    )
    growth_series = ", ".join("{:.4f}".format(value) for value in growth)
    first_capex_ratio = (
        fact("PaymentsToAcquirePropertyPlantAndEquipment", HISTORY[0]) / revenue[0]
    )
    growth_note = (
        f"Revenue growth. Fades linearly from the {len(growth)}-year trailing mean "
        f"({mean_growth:.4f}) in FY1 to the slowest year actually observed "
        f"({slowest_growth:.4f}) in FY5. Both endpoints are real: annual growth over "
        f"{window} was {growth_series}, computed from tagged "
        "RevenueFromContractWithCustomerExcludingAssessedTax. Only the linear shape "
        "between them is a modeling choice. No fiscal year after the case's "
        f"{AS_OF} as-of date is used."
    )
    flat_note = (
        "Held flat at the FY2024 actual across the forecast. Holding the most recent "
        "observed value is the assumption that requires the least invention; the "
        f"{window} range is recorded in the snapshot so the reader can see the "
        "variation this flat line suppresses."
    )

    rows: list[tuple[str, int, list[float], str, str]] = [
        ("Assumptions", 5, growth_path, "derived", growth_note),
        ("Assumptions", 6, [gross_margin] * 5, "derived",
         f"Gross margin = GrossProfit / revenue, FY2024 = {gross_margin:.4f}. {flat_note}"),
        ("Assumptions", 7, [opex_ratio] * 5, "derived",
         f"Operating expense / revenue = (GrossProfit - OperatingIncomeLoss) / revenue, "
         f"FY2024 = {opex_ratio:.4f}. {flat_note}"),
        ("Assumptions", 8, [tax_rate] * 5, "derived",
         f"Effective tax rate = IncomeTaxExpenseBenefit / (NetIncomeLoss + "
         f"IncomeTaxExpenseBenefit), FY2024 = {tax_rate:.4f}. This is the GAAP "
         f"effective rate, not cash taxes paid, which are not in this fact set. "
         f"{flat_note}"),
        ("Assumptions", 9, [UNGROUNDED["da_share_of_capex"]] * 5, "driver",
         "Depreciation and amortization as a share of capex. Microsoft tags no "
         "DepreciationDepletionAndAmortization concept in this fact set, so there is "
         "nothing to derive it from. Held as a driver."),
        ("Assumptions", 10, [capex_ratio] * 5, "derived",
         f"Capex / revenue = PaymentsToAcquirePropertyPlantAndEquipment / revenue, "
         f"FY2024 = {capex_ratio:.4f}. Note this ratio rose steeply over the window "
         f"({capex_series}), "
         "so holding the latest value flat is the higher-capex, lower-free-cash-flow "
         "choice rather than the flattering one."),
        ("Assumptions", 11, [nwc_sensitivity] * 5, "derived",
         f"Change in net working capital per dollar of revenue change, "
         f"{len(growth)}-year mean = {nwc_sensitivity:.4f}, where net working capital "
         "is tagged AssetsCurrent less LiabilitiesCurrent. CAVEAT: the yearly values "
         f"({nwc_series}) "
         "are highly unstable and change sign, so this mean is a weak central estimate "
         "and the line should be stress-tested rather than trusted as a point."),
        ("Assumptions", 12, share_path, "derived",
         f"Shares outstanding. FY2024 tagged CommonStockSharesOutstanding = "
         f"{shares_latest:,.0f}mm, carried forward at the observed {window} buyback "
         f"CAGR of {share_cagr:.5f} (from {shares_first:,.0f}mm). Both endpoints are "
         "tagged facts; the constant-rate extrapolation is the modeling choice."),
        ("Assumptions", 13, [UNGROUNDED["wacc"]] * 5, "driver",
         "Weighted average cost of capital. A market-derived quantity -- it needs a "
         "risk-free rate, an equity risk premium, and a beta, none of which is an "
         "issuer disclosure and none of whose sources (FRED, Damodaran) is reachable "
         "from this environment. Held as a driver."),
        ("Assumptions", 14, [UNGROUNDED["terminal_growth"]] * 5, "driver",
         "Terminal growth rate. A judgment about the indefinite future, not a fact "
         "about Microsoft."),
    ]

    inputs: list[dict[str, Any]] = []
    drivers: list[dict[str, Any]] = []

    def emit(sheet: str, cell: str, value: Any, kind: str, note: str) -> None:
        if kind == "driver":
            drivers.append({
                "sheet": sheet, "cell": cell,
                "driver_type": "undisclosed_term_driver",
                "rationale": note, "basis": {},
            })
            inputs.append({
                "sheet": sheet, "cell": cell, "value": value,
                "input_kind": "modeler_assumption",
                "source": {
                    "name": "Case driver (no tagged disclosure exists)",
                    "url": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
                    "as_of": AS_OF, "notes": note,
                },
            })
            return
        inputs.append({
            "sheet": sheet, "cell": cell, "value": value, "input_kind": kind,
            "source": {
                "name": TEN_K_NAME if kind == "observed" else XBRL_NAME,
                "url": TEN_K_URL if kind == "observed" else XBRL_URL,
                "as_of": AS_OF, "notes": note,
            },
        })

    for sheet, row, values, kind, note in rows:
        for column, value in zip(FORWARD_COLUMNS, values):
            emit(sheet, f"{column}{row}", round(value, 6) if abs(value) < 100 else round(value, 1), kind, note)

    # --- Treasury & Liquidity: only cells not already sourced ------------
    opening_cash = fact("CashAndCashEquivalentsAtCarryingValue", HISTORY[-2])
    worst_cash = min(fact("CashAndCashEquivalentsAtCarryingValue", e) for e in HISTORY)
    cash_identity_note = (
        f"Opening cash = tagged CashAndCashEquivalentsAtCarryingValue at FY2023 "
        f"({opening_cash:,.0f} $mm). CAVEAT: the sheet's ending-cash identity is "
        "opening + operating cash flow - capex - dividends - buybacks + issuance - "
        "repayment. It omits net purchases and maturities of short-term investments, "
        "acquisitions, and FX, so the resulting ending-cash line is NOT comparable to "
        "the 10-K's cash and short-term investments; the difference is those omitted "
        "flows. The case's recorded outcome metric is a historical record of what was "
        "forecast at the time and is deliberately left unchanged."
    )
    emit("Treasury & Liquidity", "C5", round(opening_cash, 1), "observed", cash_identity_note)
    emit("Treasury & Liquidity", "D5", round(worst_cash, 1), "observed",
         cash_identity_note + f" Adversarial column uses the lowest cash balance "
         f"observed over {window} ({worst_cash:,.0f} $mm).")
    for row, key, label in (
        (15, "minimum_cash", "Minimum operating cash balance"),
        (16, "max_net_leverage", "Maximum tolerated net leverage"),
        (17, "min_interest_coverage", "Minimum tolerated interest coverage"),
    ):
        note = (
            f"{label}. A treasury policy screen set by the analyst, not a Microsoft "
            "disclosure -- Microsoft is investment grade and discloses no maintenance "
            "covenant thresholds. Held as a driver."
        )
        for column in ("C", "D"):
            emit("Treasury & Liquidity", f"{column}{row}", UNGROUNDED[key], "driver", note)

    # --- DCF -------------------------------------------------------------
    net_debt = 67127.0 - 75543.0
    emit("DCF", "I5", UNGROUNDED["wacc"], "driver",
         "Discount rate (WACC). Same reasoning as Assumptions row 13: market-derived, "
         "no reachable source.")
    emit("DCF", "I6", UNGROUNDED["terminal_growth"], "driver",
         "Terminal growth rate. Same reasoning as Assumptions row 14.")
    emit("DCF", "I11", round(net_debt, 1), "derived",
         f"Net debt = disclosed FY2024 total debt 67,127 less cash and short-term "
         f"investments 75,543 = {net_debt:,.1f} $mm, i.e. Microsoft carried NET CASH "
         "at FY2024. Both components are 10-K values already frozen in this repository "
         "(the debt figure in the domain-06 Microsoft case snapshot, the liquidity "
         "figure in this one).")
    emit("DCF", "I13", round(shares_latest, 1), "observed",
         f"Diluted share count proxied by tagged CommonStockSharesOutstanding at "
         f"FY2024 ({shares_latest:,.0f}mm). Microsoft's diluted weighted-average count "
         "is not separately tagged in this fact set; the basic weighted average "
         f"({fact('WeightedAverageNumberOfSharesOutstandingBasic', latest):,.0f}mm) is, "
         "and the two differ by roughly the dilutive equity award overhang, so implied "
         "value per share is marginally overstated.")

    # --- Comps: real peer set, undisclosed multiples ----------------------
    peers = peer_set()
    sic = json.loads(SIC_SNAPSHOT.read_text(encoding="utf-8"))["companies"]["MSFT"]
    peer_note = (
        f"Peer selected by SEC-filed SIC code: Microsoft files SIC {sic['sic']} "
        f"({sic['sic_description']}), and this issuer files the same code per "
        f"{SIC_SNAPSHOT.relative_to(ROOT)}. Peer SELECTION is sourced; the peer's "
        "multiples are not (see the price columns)."
    )
    for offset, (symbol, name) in enumerate(peers):
        emit("Comps", f"B{5 + offset}", symbol, "derived", f"{name}. {peer_note}")
    multiple_note = (
        "Price, market capitalisation, enterprise value, and every multiple derived "
        "from them. XBRL carries no market data, and no market-data host is reachable "
        "from this environment, so these cannot be sourced. They are left as declared "
        "drivers at zero rather than filled with plausible-looking multiples: a comps "
        "table with real tickers and visibly empty multiples states honestly what is "
        "and is not known, whereas invented multiples would not."
    )
    for offset in range(len(peers)):
        for column in ("C", "D", "E", "F", "G", "H"):
            emit("Comps", f"{column}{5 + offset}", 0, "driver", multiple_note)

    # --- Cover ------------------------------------------------------------
    thesis = (
        f"Microsoft closed FY2024 with {revenue[-1]:,.0f}mm of revenue, a "
        f"{gross_margin:.1%} gross margin and net cash of {abs(net_debt):,.0f}mm. The "
        f"live question is capital intensity: capex rose from {first_capex_ratio:.1%} "
        f"of revenue in FY2020 to {capex_ratio:.1%} in FY2024, so free cash flow now "
        "turns on whether that build sustains the growth rate that justifies it."
    )
    cover = {
        "Sector:": (
            f"Software -- SEC SIC {sic['sic']} ({sic['sic_description']}), as filed by "
            "the registrant"
        ),
    }
    emit("Cover", "B11", thesis, "derived",
         "Thesis stated in terms of the disclosed FY2024 figures it rests on, so every "
         "number in it is traceable to a tagged fact.")
    for cell, note in (
        ("C5", "Coverage start date: a repository fact about when this case was "
               "created, not a disclosure about Microsoft."),
        ("C6", "Populated automatically from the manifest as_of date; release metadata."),
        ("C7", "Next earnings date. Microsoft's future reporting calendar is announced "
               "in a press release, not tagged in XBRL, and is not derivable from the "
               "fact set."),
        ("B17", "Colour-legend row, a presentation convention rather than an input. The "
                "coverage scanner's legend exclusion matches only the phrase 'Blue text "
                "/ yellow fill'; this template writes 'Blue text', so the row is "
                "declared here instead."),
    ):
        drivers.append({
            "sheet": "Cover", "cell": cell,
            "driver_type": "generated_metadata" if cell == "C6" else "presentation_convention",
            "rationale": note, "basis": {},
        })

    existing = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    preserved = existing["inputs"]
    already = {(item["sheet"], item["cell"]) for item in preserved}
    added = [item for item in inputs if (item["sheet"], item["cell"]) not in already]
    collisions = [item for item in inputs if (item["sheet"], item["cell"]) in already]
    if collisions:
        raise ValueError(
            "refusing to overwrite already-sourced cells: "
            f"{sorted((c['sheet'], c['cell']) for c in collisions)}"
        )

    snapshot_existing = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    snapshot = {
        **snapshot_existing,
        "capture_method": "sec_xbrl_company_facts_plus_curated_10k_observation",
        "sources": [
            snapshot_existing["sources"][0],
            {
                "name": XBRL_NAME,
                "url": XBRL_URL,
                "publisher": "U.S. Securities and Exchange Commission (EDGAR company facts)",
                "captured_values": {
                    "cik": "0000789019",
                    "fiscal_years_used": HISTORY,
                    "hindsight_policy": (
                        "Only fiscal years ending on or before the case as_of date are "
                        "used. FY2025 and FY2026 are present in the recorded fact set "
                        "and deliberately excluded."
                    ),
                    "revenue_usd_mm": {e: fact(REVENUE, e) for e in HISTORY},
                    "revenue_growth": {
                        HISTORY[i + 1]: round(growth[i], 6) for i in range(len(growth))
                    },
                    "gross_margin": {
                        e: round(fact("GrossProfit", e) / fact(REVENUE, e), 6) for e in HISTORY
                    },
                    "capex_over_revenue": {
                        e: round(
                            fact("PaymentsToAcquirePropertyPlantAndEquipment", e)
                            / fact(REVENUE, e), 6
                        ) for e in HISTORY
                    },
                    "effective_tax_rate": {
                        e: round(
                            fact("IncomeTaxExpenseBenefit", e)
                            / (fact("NetIncomeLoss", e) + fact("IncomeTaxExpenseBenefit", e)), 6
                        ) for e in HISTORY
                    },
                    "net_working_capital_usd_mm": {
                        e: fact("AssetsCurrent", e) - fact("LiabilitiesCurrent", e)
                        for e in HISTORY
                    },
                    "shares_outstanding_mm": {
                        e: fact("CommonStockSharesOutstanding", e) for e in HISTORY
                    },
                    "cash_and_equivalents_usd_mm": {
                        e: fact("CashAndCashEquivalentsAtCarryingValue", e) for e in HISTORY
                    },
                },
            },
            {
                "name": "SEC EDGAR SIC classifications (peer selection)",
                "url": SIC_URL,
                "publisher": "U.S. Securities and Exchange Commission",
                "captured_values": {
                    "microsoft_sic": sic["sic"],
                    "microsoft_sic_description": sic["sic_description"],
                    "peers_same_sic": [symbol for symbol, _ in peers],
                },
            },
        ],
        "open_questions": {
            "note": (
                "Differences between values already sourced from the 10-K and the "
                "corresponding XBRL tags. Recorded rather than silently reconciled: "
                "this script cannot read the filing to adjudicate which definition "
                "each 10-K figure used, and overwriting a sourced number with a "
                "differently-defined one is not an improvement."
            ),
            "items": [
                {
                    "cell": "Treasury & Liquidity!C14",
                    "existing_10k_value": 1700.0,
                    "xbrl_tag": "us-gaap:InterestExpense",
                    "xbrl_value": fact("InterestExpense", latest),
                    "left_as": "existing 10-K value",
                },
                {
                    "cell": "Treasury & Liquidity!C13",
                    "existing_10k_value": 109400.0,
                    "xbrl_tag": "us-gaap:OperatingIncomeLoss",
                    "xbrl_value": fact("OperatingIncomeLoss", latest),
                    "left_as": "existing 10-K value",
                },
            ],
        },
        "undisclosed_terms": {
            "note": "Model terms with no tagged disclosure, recorded so the gap is auditable.",
            "items": [
                "depreciation and amortization (no us-gaap tag in this fact set)",
                "weighted average cost of capital",
                "terminal growth rate",
                "share price, market capitalisation, enterprise value, and all derived multiples",
                "treasury policy thresholds (minimum cash, leverage and coverage screens)",
                "future earnings calendar",
            ],
        },
    }
    snapshot.pop("snapshot_sha256", None)
    snapshot["snapshot_sha256"] = hashlib.sha256(canonical_bytes(snapshot)).hexdigest()

    manifest = {
        **existing,
        "cover": {**existing.get("cover", {}), **cover},
        "inputs": sorted(
            preserved + added,
            key=lambda item: (item["sheet"], item["cell"][0], int(item["cell"][1:])),
        ),
        "sources": [
            existing["sources"][0],
            {
                "name": XBRL_NAME, "url": XBRL_URL, "as_of": AS_OF,
                "notes": (
                    "SEC XBRL company facts for CIK 0000789019, recorded at "
                    f"{FACTS.relative_to(ROOT)}. Only {window} is used; FY2025 and "
                    "FY2026 are present in the fact set and deliberately excluded as "
                    "hindsight relative to this case's as-of date."
                ),
            },
            {
                "name": "SEC EDGAR SIC classifications (peer selection)",
                "url": SIC_URL, "as_of": AS_OF,
                "notes": (
                    f"Comparable-company selection by SIC {sic['sic']} "
                    f"({sic['sic_description']}) per {SIC_SNAPSHOT.relative_to(ROOT)}."
                ),
            },
            {
                "name": "Frozen source snapshot",
                "url": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}", "as_of": AS_OF,
                "notes": "Immutable curated observation package with SHA-256 digest",
            },
        ],
        "refresh": {
            "date": date.today().isoformat(),
            "trigger": "Depth pass: full input accounting against recorded XBRL facts",
            "source_snapshot": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
            "what_changed": (
                "Filled the forward driver grid, the DCF bridge, the treasury policy "
                "screens, and the comparable-company peer set from Microsoft's "
                f"recorded XBRL facts for {window}. The grid previously held literal "
                "zeros -- a zero revenue growth rate and a zero WACC read as data "
                "rather than as blanks. Every forward driver is derived only from "
                "fiscal years ending on or before the case's as-of date; FY2025 and "
                "FY2026 actuals are present in the fact set and excluded by an "
                "explicit assertion in the generator. The eighteen values already "
                "sourced from the 10-K are untouched, and two places where the 10-K "
                "and the XBRL tag disagree are recorded as open questions rather than "
                "silently reconciled."
            ),
            "reviewer_notes": (
                "External historical case; human stakeholder approval remains pending. "
                "Comps multiples remain empty because no market-data source is "
                "reachable; the peer set itself is sourced by SIC code. The sheet's "
                "ending-cash identity omits non-capex investing flows and FX, so it is "
                "not comparable to the 10-K's cash and short-term investments."
            ),
            "next_check": "On Microsoft's next Form 10-K, builder change, or annual review",
        },
        "driver_declarations": sorted(
            drivers,
            key=lambda item: (item["sheet"], item["cell"][0], int(item["cell"][1:])),
        ),
    }
    return manifest, snapshot


def write_source_register(snapshot: dict[str, Any]) -> None:
    rows = [
        (CASE_ID, TEN_K_NAME, "U.S. SEC / Microsoft", TEN_K_URL, AS_OF,
         str(SNAPSHOT_PATH.relative_to(ROOT)), snapshot["snapshot_sha256"], "frozen"),
        (CASE_ID, XBRL_NAME, "SEC EDGAR via tools/data_fabric/edgar_company_facts.py",
         XBRL_URL, AS_OF, str(FACTS.relative_to(ROOT)),
         hashlib.sha256(FACTS.read_bytes()).hexdigest(), "active"),
        (CASE_ID, "SEC EDGAR SIC classifications (peer selection)",
         "U.S. Securities and Exchange Commission", SIC_URL, AS_OF,
         str(SIC_SNAPSHOT.relative_to(ROOT)),
         hashlib.sha256(SIC_SNAPSHOT.read_bytes()).hexdigest(), "active"),
    ]
    header = "case_id,source_name,publisher,url,as_of,snapshot,snapshot_sha256,status"
    lines = [header]
    if REGISTER_PATH.exists():
        existing = REGISTER_PATH.read_text(encoding="utf-8").splitlines()
        lines = [line for line in (existing or lines) if not line.startswith(f"{CASE_ID},")]
    for row in rows:
        lines.append(",".join(f'"{f}"' if "," in str(f) else str(f) for f in row))
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
        f"inputs={len(manifest['inputs'])} drivers={len(manifest['driver_declarations'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
