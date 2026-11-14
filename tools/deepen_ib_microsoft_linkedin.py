"""Source every input of the Microsoft / LinkedIn 2016 investment-banking case.

The case shipped with 16 sourced cells out of 172 candidates. The forward
driver grid, the LinkedIn income-statement history, the DCF bridge, the
comparable-companies table, the policy screens and the Cover were template
defaults. Several of the cells that were sourced were approximations: buyer
earnings of 16,800 and diluted shares of 8,000 where the 10-K says 16,798 and
8,013, and a target diluted-share count solved as 26,200 / 196 rather than
counted.

THE INFORMATION SET
-------------------
The case is dated 2016-12-08, the day the merger completed. The transaction
analysis is the one a banker would show at signing: it uses only what was
public on or before the unaffected date, 2016-06-10 (the last trading day
before the 2016-06-13 announcement), plus three documents filed between
signing and closing that describe the deal itself:

  - LinkedIn's definitive merger proxy (DEFM14A, filed 2016-07-22): the
    management Forecasts for 2016E-2020E, Qatalyst Partners' discount-rate
    range, its peer set and its DCF value range.
  - Microsoft's FY2016 Form 10-K (filed 2016-07-28): buyer earnings,
    diluted shares and effective tax rate.
  - Microsoft's 2016-08-01 pricing term sheet (FWP) for the $19.75bn notes
    whose prospectus names the LinkedIn acquisition as a use of proceeds.

Every one of those was filed before the case date. Nothing filed after
2016-12-08 is used; `assert_no_hindsight()` checks every recorded as_of.

WHAT IS A DRIVER AND WHY
------------------------
Four kinds of cell have no disclosure and stay declared drivers, each with the
named data that grounds its value:

  - gross margin (cost of revenue is not in the Forecasts): held at the FY2015
    actual; opex intensity is then the balancing residual that makes EBIT tie
    exactly to the Forecasts' implied operating income;
  - forward share count: the proxy's ~12% dilution over the projection period;
  - terminal growth: the 30-year Treasury par yield on 2016-06-10 (Base) and
    the FOMC's 2% longer-run inflation goal (Adversarial);
  - policy screens (premium warning, valuation-dispersion warning, minimum
    accretion, Adversarial synergies): each pinned to a disclosed benchmark.

Usage:
    python tools/deepen_ib_microsoft_linkedin.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "ib-public-microsoft-linkedin-2016"
FOLDER = "01_Investment_Banking"
MANIFEST_PATH = ROOT / "standards" / "public_cases" / f"{CASE_ID}.json"
SNAPSHOT_PATH = ROOT / FOLDER / "sources" / "snapshots" / f"{CASE_ID}.json"
REGISTER_PATH = ROOT / FOLDER / "sources" / "source_register.csv"
OWNER = "tools/deepen_ib_microsoft_linkedin.py"

AS_OF = "2016-12-08"
UNAFFECTED = "2016-06-10"

# --------------------------------------------------------------------------
# Sources. Every value below is transcribed from the document named, and the
# snapshot records which one. Filing dates, not period ends, decide hindsight.
# --------------------------------------------------------------------------
S = {
    "proxy": {
        "name": "LinkedIn definitive merger proxy statement (DEFM14A), filed 2016-07-22",
        "url": "https://www.sec.gov/Archives/edgar/data/1271024/000104746916014430/a2229104zdefm14a.htm",
        "as_of": "2016-07-22",
        "publisher": "U.S. SEC / LinkedIn",
    },
    "lnkd_10k": {
        "name": "LinkedIn Form 10-K for fiscal year 2015, filed 2016-02-12",
        "url": "https://www.sec.gov/Archives/edgar/data/1271024/000127102416000035/a20151231-10xkdocument.htm",
        "as_of": "2016-02-12",
        "publisher": "U.S. SEC / LinkedIn",
    },
    "lnkd_10q": {
        "name": "LinkedIn Form 10-Q for the quarter ended 2016-03-31, filed 2016-04-29",
        "url": "https://www.sec.gov/Archives/edgar/data/1271024/000127102416000043/a20160331-10qdocument.htm",
        "as_of": "2016-04-29",
        "publisher": "U.S. SEC / LinkedIn",
    },
    "msft_deck": {
        "name": "Microsoft Form 8-K Exhibit 99.1, Microsoft-LinkedIn investor presentation, filed 2016-06-13",
        "url": "https://www.sec.gov/Archives/edgar/data/789019/000119312516619689/d116815dex991.htm",
        "as_of": "2016-06-13",
        "publisher": "U.S. SEC / Microsoft",
    },
    "msft_10k": {
        "name": "Microsoft Form 10-K for fiscal year 2016, filed 2016-07-28",
        "url": "https://www.sec.gov/Archives/edgar/data/789019/000119312516662209/d187868d10k.htm",
        "as_of": "2016-07-28",
        "publisher": "U.S. SEC / Microsoft",
    },
    "msft_fwp": {
        "name": "Microsoft pricing term sheet (FWP) for $19.75bn of senior notes, filed 2016-08-02",
        "url": "https://www.sec.gov/Archives/edgar/data/789019/000119312516667093/d234953dfwp.htm",
        "as_of": "2016-08-02",
        "publisher": "U.S. SEC / Microsoft",
    },
    "msft_424b2": {
        "name": "Microsoft prospectus supplement (424B2) for the August 2016 notes, use of proceeds",
        "url": "https://www.sec.gov/Archives/edgar/data/789019/000119312516668371/d200218d424b2.htm",
        "as_of": "2016-08-02",
        "publisher": "U.S. SEC / Microsoft",
    },
    "close_8k": {
        "name": "LinkedIn merger completion Form 8-K",
        "url": "https://www.sec.gov/Archives/edgar/data/1271024/000110465916161289/a16-22816_18k.htm",
        "as_of": "2016-12-08",
        "publisher": "U.S. SEC / LinkedIn",
    },
    "q3_10q": {
        "name": "LinkedIn September 2016 Form 10-Q merger disclosure",
        "url": "https://www.sec.gov/Archives/edgar/data/1271024/000127102416000059/a20160930-10qdocument.htm",
        "as_of": "2016-10-27",
        "publisher": "U.S. SEC / LinkedIn",
    },
    "av_weekly": {
        "name": "Alpha Vantage TIME_SERIES_WEEKLY (unadjusted weekly close), week ending 2016-06-10",
        "url": "https://www.alphavantage.co/documentation/#weekly",
        "as_of": UNAFFECTED,
        "publisher": "Alpha Vantage",
    },
    "yahoo": {
        "name": "Yahoo Finance chart API daily close for 2016-06-10 (split-adjusted; unadjusted by disclosed split ratios)",
        "url": "https://query1.finance.yahoo.com/v8/finance/chart/CRM?period1=1465516800&period2=1465603200&interval=1d",
        "as_of": UNAFFECTED,
        "publisher": "Yahoo Finance",
    },
    "treasury": {
        "name": "U.S. Treasury daily par yield curve rates, 2016",
        "url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2016/all?type=daily_treasury_yield_curve&field_tdr_date_value=2016&page&_format=csv",
        "as_of": UNAFFECTED,
        "publisher": "U.S. Department of the Treasury",
    },
    "fomc": {
        "name": "FOMC Statement on Longer-Run Goals and Monetary Policy Strategy, as amended effective 2016-01-26",
        "url": "https://www.federalreserve.gov/monetarypolicy/files/FOMC_LongerRunGoals_20160126.pdf",
        "as_of": "2016-01-26",
        "publisher": "Board of Governors of the Federal Reserve System",
    },
    "yahoo_goog": {
        "name": "Yahoo Finance chart API daily close for GOOG (Alphabet Class C) on 2016-06-10 (split-adjusted)",
        "url": "https://query1.finance.yahoo.com/v8/finance/chart/GOOG?period1=1465430400&period2=1465689600&interval=1d",
        "as_of": UNAFFECTED,
        "publisher": "Yahoo Finance",
    },
    "dwre_14d9": {
        "name": "Demandware Schedule 14D-9 (Goldman Sachs selected historical premia analysis), filed 2016-06-10",
        "url": "https://www.sec.gov/Archives/edgar/data/1301031/000119312516618542/d207591dsc14d9.htm",
        "as_of": "2016-06-10",
        "publisher": "U.S. SEC / Demandware",
    },
}

PEER_SOURCES = {
    "GOOGL": ("Alphabet Form 10-Q, quarter ended 2016-03-31",
              "https://www.sec.gov/Archives/edgar/data/1652044/000165204416000021/goog10-qq12016.htm", "2016-05-03"),
    "AMZN": ("Amazon.com Form 10-Q, quarter ended 2016-03-31",
             "https://www.sec.gov/Archives/edgar/data/1018724/000101872416000227/amzn-20160331x10q.htm", "2016-04-29"),
    "FB": ("Facebook Form 10-Q, quarter ended 2016-03-31",
           "https://www.sec.gov/Archives/edgar/data/1326801/000132680116000067/fb-3312016x10q.htm", "2016-04-28"),
    "TWTR": ("Twitter Form 10-Q, quarter ended 2016-03-31",
             "https://www.sec.gov/Archives/edgar/data/1418091/000156459016017462/twtr-10q_20160331.htm", "2016-05-03"),
    "CRM": ("Salesforce.com Form 10-Q, quarter ended 2016-04-30",
            "https://www.sec.gov/Archives/edgar/data/1108524/000110852416000066/crmq1fy1710-q.htm", "2016-05-20"),
    "WDAY": ("Workday Form 10-Q, quarter ended 2016-04-30",
             "https://www.sec.gov/Archives/edgar/data/1327811/000132781116000041/wday-04302016x10q.htm", "2016-06-01"),
    "NOW": ("ServiceNow Form 10-Q, quarter ended 2016-03-31",
            "https://www.sec.gov/Archives/edgar/data/1373715/000137371516000364/now-2016331x10q.htm", "2016-05-06"),
}

# --------------------------------------------------------------------------
# Observed figures ($mm unless stated).
# --------------------------------------------------------------------------
# LinkedIn FY2013-FY2015 consolidated statements of operations (10-K FY2015).
LNKD_HIST = {
    "FY2013": {"revenue": 1528.545, "cost_of_revenue": 202.908, "sales_marketing": 522.100,
               "product_development": 395.643, "general_admin": 225.566, "da": 134.516,
               "interest_expense": 0.0, "tax": 22.459, "diluted_shares_mm": 118.944,
               "operating_income": 47.812},
    "FY2014": {"revenue": 2218.767, "cost_of_revenue": 293.797, "sales_marketing": 774.411,
               "product_development": 536.184, "general_admin": 341.294, "da": 236.946,
               "interest_expense": 6.797, "tax": 46.525, "diluted_shares_mm": 122.800,
               "operating_income": 36.135},
    "FY2015": {"revenue": 2990.911, "cost_of_revenue": 418.858, "sales_marketing": 1048.129,
               "product_development": 775.660, "general_admin": 478.734, "da": 420.472,
               "interest_expense": 50.882, "tax": -49.969, "diluted_shares_mm": 129.024,
               "operating_income": -150.942, "net_loss": -164.761,
               "net_loss_attributable": -166.144, "federal_statutory_rate": 0.35},
}

# LinkedIn management Forecasts, proxy pages 58-60 (in millions, rounded).
FORECAST_YEARS = ["2016E", "2017E", "2018E", "2019E", "2020E"]
FC = {
    "revenue":           [3738, 4615, 5529, 6421, 7365],
    "adjusted_ebitda":   [1031, 1391, 1824, 2236, 2666],
    "modified_ebitda":   [954, 1301, 1728, 2136, 2571],
    "net_income":        [-275, 44, 303, 565, 831],
    "tax":               [97, 24, 163, 304, 447],
    "other_expense":     [58, 63, 68, 65, 25],
    "da":                [570, 626, 621, 615, 630],
    "sbc":               [581, 634, 669, 687, 733],
    "capitalized_software": [-77, -90, -96, -100, -95],
    "cfo":               [1264, 1494, 1975, 2333, 2696],
    "capex":             [806, 600, 608, 642, 589],
    "levered_fcf":       [458, 894, 1367, 1691, 2107],
}

# Qatalyst Partners' analyses (proxy pages 52-55).
QATALYST = {
    "dcf_discount_rate_low": 0.10, "dcf_discount_rate_high": 0.13,
    "dcf_value_per_share_low_usd": 156.43, "dcf_value_per_share_high_usd": 238.39,
    "projected_dilution_from_equity_grants": 0.12,
    "consumer_internet_peers": ["Alphabet, Inc.", "Amazon.com, Inc.", "Facebook, Inc.", "Twitter Inc."],
    "saas_peers": ["Cornerstone OnDemand Inc.", "NetSuite Inc.", "Salesforce.com, Inc.",
                   "ServiceNow, Inc.", "Ultimate Software Group, Inc.", "Workday, Inc."],
    "announced_premium_to_unaffected": 0.495,
}

# LinkedIn capital structure, Form 10-Q for 2016-03-31.
LNKD_Q1 = {
    "class_a_shares_2016_04_21": 117984839, "class_b_shares_2016_04_21": 15559383,
    "rsus_unvested_2016_03_31": 7766829,
    "options_outstanding_2016_03_31": 2534824, "options_weighted_avg_exercise_usd": 104.19,
    "cash_and_equivalents": 759.451, "marketable_securities": 2400.187,
    "convertible_notes_principal": 1322.5, "convertible_notes_coupon": 0.005,
    "convertible_notes_maturity": "2019-11-01",
    "redeemable_noncontrolling_interest": 27.321,
}
LNKD_UNAFFECTED_CLOSE = 131.08   # Alpha Vantage weekly close, week ending 2016-06-10
OFFER_PRICE = 196.00             # merger agreement, per share in cash
MSFT_DEAL_EV = 26200.0           # Microsoft deck slide 23: "$26.2 billion enterprise value"
MSFT_COST_SYNERGIES_PRETAX = 150.0  # deck slide 23: "$150 million of cost synergies annually by 2018"

# Microsoft FY2016 (10-K, income statement).
MSFT = {"net_income": 16798.0, "diluted_shares_mm": 8013.0,
        "income_before_tax": 19751.0, "provision_for_tax": 2953.0}

# August 2016 notes (FWP): principal $mm, coupon.
NOTES = [(2500, 0.0110), (2750, 0.0155), (1500, 0.0200), (4000, 0.0240),
         (2250, 0.0345), (4500, 0.0370), (2250, 0.0395)]

UST_30Y_2016_06_10 = 0.0244
FOMC_INFLATION_GOAL = 0.02
# Goldman Sachs premia analysis in the Demandware 14D-9.
PREMIA = {"saas_median": 0.31, "saas_average": 0.40, "tech_500m_plus_median_2009_2016": 0.37,
          "tech_500m_plus_average_2016_ytd": 0.41,
          # Goldman's table of AVERAGE premia by year; its "Median 37%" is the
          # median of these eight yearly averages, not of the deals.
          "tech_500m_plus_annual_average_premia": {"2009": 0.39, "2010": 0.41, "2011": 0.35, "2012": 0.35,
                                                   "2013": 0.34, "2014": 0.36, "2015": 0.38,
                                                   "2016_through_2016_05_27": 0.41}}
_avgs = sorted(PREMIA["tech_500m_plus_annual_average_premia"].values())
assert round((_avgs[3] + _avgs[4]) / 2, 4) == PREMIA["tech_500m_plus_median_2009_2016"]

# Comparable companies. Shares are the cover-page counts of each 10-Q (all
# classes); balance sheet and LTM figures are SEC XBRL company facts filed on
# or before 2016-06-10. LTM = latest fiscal year + latest quarter - prior-year
# quarter. Debt is financial debt at carrying value excluding capital leases;
# cash is cash and equivalents plus current marketable securities.
PEERS = [
    # ticker, close, price source, split note, shares_mm, cash, debt, ltm_rev, ltm_opinc, ltm_da, ltm_ni
    {"ticker": "GOOGL", "close": 733.19, "price_src": "yahoo",
     "price_note": "Yahoo split-adjusted close 36.6595 x 20 (Alphabet 20-for-1 split, 2022; StockholdersEquityNoteStockSplitConversionRatio1 = 20 in Alphabet's 2022 10-Q)",
     "shares_mm": 293.675151 + 49.440407 + 343.439675,
     # Class C (GOOG) trades separately and closed below Class A; Class B is
     # unlisted and converts 1:1 into Class A, so it is valued at the Class A close.
     "class_c_shares_mm": 343.439675, "class_c_close": 719.41,
     "class_c_note": "GOOG close 35.9705 x 20 = 719.41 (Yahoo split-adjusted, same 20-for-1 split)",
     "cash": 75264.0, "debt": 3221.0 + 1987.0,
     "ltm_rev": 77988.0, "ltm_opinc": 20255.0, "ltm_da": (4132 + 931) + (1155 + 216) - (938 + 239),
     "ltm_ni": 17040.0},
    {"ticker": "AMZN", "close": 717.91, "price_src": "yahoo",
     "price_note": "Yahoo split-adjusted close 35.8955 x 20 (Amazon 20-for-1 split effective 2022-06-06 per Alpha Vantage SPLITS)",
     "shares_mm": 471.827960, "cash": 12470.0 + 3389.0, "debt": 8405.0,
     "ltm_rev": 113417.0, "ltm_opinc": 3049.0, "ltm_da": 6682.0, "ltm_ni": 1166.0},
    {"ticker": "FB", "yahoo_symbol": "META", "close": 116.62, "price_src": "yahoo", "price_note": "Yahoo close (ticker META today); no split since 2016",
     "shares_mm": 2311.865096 + 548.439425, "cash": 6456.0 + 14165.0, "debt": 0.0,
     "ltm_rev": 19767.0, "ltm_opinc": 7301.0, "ltm_da": 2040.0, "ltm_ni": 4686.0},
    {"ticker": "TWTR", "close": 14.02, "price_src": "av_weekly", "price_note": "Alpha Vantage weekly close",
     "shares_mm": 701.897432, "cash": 1027.661 + 2548.749, "debt": 1475.513,
     "ltm_rev": 2376.614, "ltm_opinc": -362.536, "ltm_da": 333.580, "ltm_ni": -438.320},
    {"ticker": "CRM", "close": 81.83, "price_src": "yahoo", "price_note": "Yahoo close; no split since 2016",
     "shares_mm": 677.5, "cash": 1799.083 + 232.109, "debt": 1095.104 + 198.066,
     "ltm_rev": 7072.652, "ltm_opinc": 135.804, "ltm_da": 530.595, "ltm_ni": -12.759},
    {"ticker": "WDAY", "close": 77.63, "price_src": "yahoo", "price_note": "Yahoo close; Alpha Vantage SPLITS lists no split",
     "shares_mm": 197.0, "shares_src": "10-Q cover, 'approximately 197 million' Class A and Class B shares; the cover gives no exact count", "cash": 404.604 + 1675.486, "debt": 514.075,
     "ltm_rev": 1256.819, "ltm_opinc": -284.904, "ltm_da": 93.494, "ltm_ni": None},
    {"ticker": "NOW", "close": 74.03, "price_src": "yahoo",
     "price_note": "Yahoo split-adjusted close 14.806 x 5 (ServiceNow 5-for-1 split effective 2025-12-18, per Yahoo Finance split events)",
     "shares_mm": 162.848163, "shares_src": "shares outstanding at 2016-03-31, 10-Q stockholders' equity note; the cover rounds to ~162.8mm", "cash": 453.450 + 447.423, "debt": 482.643,
     "ltm_rev": 1099.395, "ltm_opinc": -436.285, "ltm_da": 63.984, "ltm_ni": -473.665},
]
# SaaS peers ranked by LTM revenue ($mm) to choose the three that fit the
# template's seven rows alongside all four consumer-internet peers.
SAAS_LTM_REVENUE = {"CRM": 7072.652, "WDAY": 1256.819, "NOW": 1099.395,
                    "N": 792.910, "ULTI": 660.418, "CSOD": 365.020}


def r6(x: float) -> float:
    return round(x, 6)


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def assert_no_hindsight(sources: list[dict[str, Any]]) -> None:
    for source in sources:
        if source.get("as_of", "") > AS_OF:
            raise AssertionError(f"hindsight: {source['name']} as_of {source['as_of']} > {AS_OF}")


def src(key: str, notes: str) -> dict[str, Any]:
    s = S[key]
    return {"name": s["name"], "url": s["url"], "as_of": s["as_of"], "notes": notes}


def fd_shares(price: float) -> float:
    """Fully diluted shares (mm): basic + unvested RSUs + options by treasury-stock method."""
    q = LNKD_Q1
    basic = (q["class_a_shares_2016_04_21"] + q["class_b_shares_2016_04_21"]) / 1e6
    rsus = q["rsus_unvested_2016_03_31"] / 1e6
    options = q["options_outstanding_2016_03_31"] / 1e6
    strike = q["options_weighted_avg_exercise_usd"]
    tsm = options * max(0.0, 1 - strike / price)
    return basic + rsus + tsm


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    existing = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    inputs: list[dict[str, Any]] = []
    drivers: list[dict[str, Any]] = []

    def emit(sheet: str, cell: str, value: Any, kind: str, key: str, note: str) -> None:
        inputs.append({"sheet": sheet, "cell": cell,
                       "value": r6(value) if isinstance(value, float) else value,
                       "input_kind": kind, "source": src(key, note), "emitted_by": OWNER})

    def declare(sheet: str, cell: str, driver_type: str, rationale: str, key: str, basis_note: str) -> None:
        s = S[key]
        drivers.append({"sheet": sheet, "cell": cell, "driver_type": driver_type,
                        "rationale": rationale,
                        "basis": {"source_name": s["name"], "source_url": s["url"],
                                  "as_of": s["as_of"], "note": basis_note},
                        "emitted_by": OWNER})

    h = LNKD_HIST
    years = ["FY2013", "FY2014", "FY2015"]
    cols = ["C", "D", "E"]

    # ---------------- IS history: LinkedIn FY2013-FY2015 ----------------
    for col, fy in zip(cols, years):
        y = h[fy]
        tag = f"LinkedIn {fy[2:]} consolidated statement of operations"
        emit("IS", f"{col}5", y["revenue"], "observed", "lnkd_10k", f"{tag}: net revenue, $mm.")
        emit("IS", f"{col}7", y["cost_of_revenue"], "observed", "lnkd_10k",
             f"{tag}: cost of revenue (exclusive of depreciation and amortization), $mm.")
        opex = y["sales_marketing"] + y["product_development"] + y["general_admin"] + y["da"]
        emit("IS", f"{col}10", opex, "derived", "lnkd_10k",
             f"{tag}: sales and marketing {y['sales_marketing']} + product development "
             f"{y['product_development']} + general and administrative {y['general_admin']} + "
             f"depreciation and amortization {y['da']} = {opex:.3f} $mm. The template computes "
             f"EBIT = revenue - COGS - opex and EBITDA = EBIT + D&A, so opex must include D&A; "
             f"EBIT then equals reported income (loss) from operations of {y['operating_income']} $mm.")
        emit("IS", f"{col}13", y["da"], "observed", "lnkd_10k", f"{tag}: depreciation and amortization, $mm.")
        emit("IS", f"{col}15", y["interest_expense"], "observed", "lnkd_10k",
             f"{tag}: interest expense, $mm ('—' in FY2013, recorded as 0)." if fy == "FY2013"
             else f"{tag}: interest expense, $mm.")
        emit("IS", f"{col}17", y["tax"], "observed", "lnkd_10k",
             f"{tag}: provision (benefit) for income taxes, $mm.")
        emit("IS", f"{col}19", y["diluted_shares_mm"], "observed", "lnkd_10k",
             f"{tag}: weighted-average diluted shares, millions.")

    # ---------------- Assumptions: forward grid from the Forecasts ----------------
    fwd_cols = ["C", "D", "E", "F", "G"]
    base_rev = h["FY2015"]["revenue"]
    gm_2015 = (base_rev - h["FY2015"]["cost_of_revenue"]) / base_rev
    gm_hist = {fy: (h[fy]["revenue"] - h[fy]["cost_of_revenue"]) / h[fy]["revenue"] for fy in years}
    revs = [base_rev] + FC["revenue"]
    fd196 = fd_shares(OFFER_PRICE)
    wacc_mid = (QATALYST["dcf_discount_rate_low"] + QATALYST["dcf_discount_rate_high"]) / 2
    for i, col in enumerate(fwd_cols):
        yr = FORECAST_YEARS[i]
        g = FC["revenue"][i] / revs[i] - 1
        emit("Assumptions", f"{col}5", g, "derived", "proxy",
             f"Revenue growth {yr} = {FC['revenue'][i]} / {revs[i]} - 1, from LinkedIn management "
             "Forecasts (total revenue). FY2015 base is the 10-K actual 2,990.911 $mm.")
        emit("Assumptions", f"{col}6", gm_2015, "modeler_assumption", "lnkd_10k",
             f"Gross margin held at the FY2015 actual (2,990.911 - 418.858) / 2,990.911 = {gm_2015:.6f}. "
             "The Forecasts do not disclose cost of revenue. FY2013-FY2015 actuals: "
             + ", ".join(f"{fy} {v:.4f}" for fy, v in gm_hist.items()) + ".")
        declare("Assumptions", f"{col}6", "undisclosed_metric_driver",
                "Gross margin. The management Forecasts give revenue and operating-income components "
                "but not cost of revenue, so the split between COGS and opex is not disclosed.",
                "lnkd_10k", f"Held at FY2015 actual {gm_2015:.6f}; FY2013-FY2015 range "
                f"{min(gm_hist.values()):.4f}-{max(gm_hist.values()):.4f}.")
        ebit = FC["net_income"][i] + FC["tax"][i] + FC["other_expense"][i]
        opex_pct = gm_2015 - ebit / FC["revenue"][i]
        emit("Assumptions", f"{col}7", opex_pct, "modeler_assumption", "proxy",
             f"Opex % of revenue = gross margin driver {gm_2015:.6f} - EBIT margin. {yr} EBIT = net income "
             f"{FC['net_income'][i]} + tax {FC['tax'][i]} + other expense {FC['other_expense'][i]} = {ebit} $mm "
             f"(equivalently adjusted EBITDA {FC['adjusted_ebitda'][i]} - D&A {FC['da'][i]} - SBC {FC['sbc'][i]}), "
             f"revenue {FC['revenue'][i]}. This pins the template's EBIT to the Forecasts exactly.")
        declare("Assumptions", f"{col}7", "balancing_residual",
                "Opex intensity is the residual that makes revenue x (gross margin - opex %) equal the "
                "operating income implied by the management Forecasts.", "proxy",
                f"{yr} implied EBIT {ebit} $mm on revenue {FC['revenue'][i]} $mm.")
        pretax = FC["net_income"][i] + FC["tax"][i]
        emit("Assumptions", f"{col}8", FC["tax"][i] / pretax, "derived", "proxy",
             f"Effective tax rate {yr} = provision {FC['tax'][i]} / pre-tax income ({FC['net_income'][i]} + "
             f"{FC['tax'][i]} = {pretax}) from the Forecasts' net-income reconciliation."
             + (" Negative because the Forecasts show a tax provision on a pre-tax loss." if pretax < 0 else ""))
        emit("Assumptions", f"{col}9", FC["da"][i] / FC["capex"][i], "derived", "proxy",
             f"D&A % of capex {yr} = D&A {FC['da'][i]} / purchases of property and equipment {FC['capex'][i]} "
             "(Forecasts reconciliations); with row 10 this reproduces forecast D&A exactly.")
        emit("Assumptions", f"{col}10", FC["capex"][i] / FC["revenue"][i], "derived", "proxy",
             f"Capex % of revenue {yr} = {FC['capex'][i]} / {FC['revenue'][i]}.")
        wc = FC["cfo"][i] - FC["net_income"][i] - FC["da"][i] - FC["sbc"][i]
        d_rev = FC["revenue"][i] - revs[i]
        emit("Assumptions", f"{col}11", -wc / d_rev, "derived", "proxy",
             f"Change in NWC per dollar of revenue change {yr} = -(CFO {FC['cfo'][i]} - net income "
             f"{FC['net_income'][i]} - D&A {FC['da'][i]} - SBC {FC['sbc'][i]}) / revenue change {d_rev:.3f}. "
             "Negative = working capital releases cash (deferred revenue). CAVEAT: the residual also holds "
             "other non-cash items (deferred tax, debt-discount accretion) that the Forecasts do not separate.")
        shares = fd196 * (1 + QATALYST["projected_dilution_from_equity_grants"]) ** ((i + 1) / 5)
        emit("Assumptions", f"{col}12", shares, "modeler_assumption", "proxy",
             f"Diluted shares {yr} = fully diluted {fd196:.3f}mm (Transaction Analysis!C8) x 1.12^({i + 1}/5): "
             "the proxy's ~12% management-projected dilution from future equity grants over the projection "
             "period, spread geometrically. Year-by-year counts are not disclosed.")
        declare("Assumptions", f"{col}12", "undisclosed_metric_driver",
                "Forward diluted share count; only the cumulative ~12% dilution is disclosed.", "proxy",
                "Qatalyst DCF: 'dilution factor of approximately 12%, as projected by LinkedIn management'.")
        emit("Assumptions", f"{col}13", wacc_mid, "derived", "proxy",
             "WACC = midpoint of Qatalyst Partners' 10.0%-13.0% discount-rate range, 'based on an estimated "
             "weighted average cost of capital for LinkedIn'.")
        emit("Assumptions", f"{col}14", UST_30Y_2016_06_10, "modeler_assumption", "treasury",
             "Terminal growth = 30-year Treasury par yield on 2016-06-10 (2.44%), the long-run nominal "
             "risk-free rate as a ceiling for perpetual growth. Qatalyst used exit multiples, not a growth rate.")
        declare("Assumptions", f"{col}14", "undisclosed_metric_driver",
                "Perpetual growth is a modeling judgment; no filing discloses one for LinkedIn.", "treasury",
                "30-year par yield 2.44% on 2016-06-10; FOMC longer-run inflation goal 2% is the Adversarial floor.")

    # ---------------- DCF sheet ----------------
    q = LNKD_Q1
    cash = q["cash_and_equivalents"] + q["marketable_securities"]
    debt = q["convertible_notes_principal"]
    emit("DCF", "I5", wacc_mid, "derived", "proxy", "Midpoint of Qatalyst's 10.0%-13.0% WACC range.")
    emit("DCF", "I6", UST_30Y_2016_06_10, "modeler_assumption", "treasury",
         "Terminal growth = 30-year Treasury par yield on 2016-06-10.")
    declare("DCF", "I6", "undisclosed_metric_driver", "Perpetual growth rate; modeling judgment.", "treasury",
            "30-year par yield 2.44% on 2016-06-10.")
    emit("DCF", "I11", debt - cash, "derived", "lnkd_10q",
         f"Net debt = 0.50% convertible notes principal {debt} - (cash and equivalents "
         f"{q['cash_and_equivalents']} + marketable securities {q['marketable_securities']}) = {debt - cash:.3f} $mm "
         "at 2016-03-31 (negative = net cash). Redeemable noncontrolling interest of 27.321 $mm is excluded.")
    emit("DCF", "I13", fd196, "derived", "lnkd_10q", fd_note(OFFER_PRICE))

    # ---------------- Transaction Analysis ----------------
    fd131 = fd_shares(LNKD_UNAFFECTED_CLOSE)
    unaffected_ev = LNKD_UNAFFECTED_CLOSE * fd131 - cash + debt
    emit("Transaction Analysis", "C5", MSFT_DEAL_EV, "observed", "msft_deck",
         "Microsoft investor presentation slide 23: '$196 per share, $26.2 billion enterprise value'; slide 5: "
         "'valued at approximately $26.2 billion (inclusive of LinkedIn's net cash)'. Base column = the deal "
         f"as priced. Cross-check: 196 x {fd196:.3f}mm fully diluted - net cash {cash - debt:.3f} = "
         f"{OFFER_PRICE * fd196 - cash + debt:.1f} $mm, within 0.5% of the headline.")
    emit("Transaction Analysis", "D5", unaffected_ev, "derived", "av_weekly",
         f"Unaffected enterprise value = 131.08 (LNKD close 2016-06-10) x {fd131:.6f}mm fully diluted at that "
         f"price - cash {cash:.3f} + convertible notes {debt} = {unaffected_ev:.3f} $mm. Adversarial column = "
         "the market's pre-announcement value, so the offer premium row reproduces the disclosed ~49.5%.")
    for col in ("C", "D"):
        emit("Transaction Analysis", f"{col}6", debt, "observed", "lnkd_10q",
             "0.50% convertible senior notes due 2019-11-01, aggregate principal $1,322.5mm (10-Q Note 9); "
             "LinkedIn's only borrowed money. Out of the money at both prices (initial conversion price ~$294).")
        emit("Transaction Analysis", f"{col}7", cash, "derived", "lnkd_10q",
             f"Cash and cash equivalents {q['cash_and_equivalents']} + marketable securities "
             f"{q['marketable_securities']} = {cash:.3f} $mm at 2016-03-31.")
    emit("Transaction Analysis", "C8", fd196, "derived", "lnkd_10q", fd_note(OFFER_PRICE))
    emit("Transaction Analysis", "D8", fd131, "derived", "lnkd_10q", fd_note(LNKD_UNAFFECTED_CLOSE))
    for col in ("C", "D"):
        emit("Transaction Analysis", f"{col}9", OFFER_PRICE, "observed", "proxy",
             "Per share merger consideration $196.00 in cash (merger agreement dated 2016-06-11).")
    emit("Transaction Analysis", "C10", wacc_mid, "derived", "proxy",
         "Midpoint of Qatalyst's 10.0%-13.0% discount-rate range (estimated WACC for LinkedIn).")
    emit("Transaction Analysis", "D10", QATALYST["dcf_discount_rate_high"], "observed", "proxy",
         "Top of Qatalyst's 10.0%-13.0% discount-rate range: the Adversarial (lowest-value) end.")
    emit("Transaction Analysis", "C11", UST_30Y_2016_06_10, "modeler_assumption", "treasury",
         "Terminal growth = 30-year Treasury par yield 2.44% on 2016-06-10.")
    declare("Transaction Analysis", "C11", "undisclosed_metric_driver", "Perpetual growth; modeling judgment.",
            "treasury", "30-year par yield 2.44% on 2016-06-10.")
    emit("Transaction Analysis", "D11", FOMC_INFLATION_GOAL, "modeler_assumption", "fomc",
         "Adversarial terminal growth = the FOMC's 2% longer-run inflation goal, i.e. zero real growth.")
    declare("Transaction Analysis", "D11", "scenario_lever",
            "Adversarial perpetual growth set at zero real growth.", "fomc",
            "'inflation at the rate of 2 percent ... is most consistent over the longer run with the "
            "Federal Reserve's statutory mandate'.")
    coupon = q["convertible_notes_principal"] * q["convertible_notes_coupon"]
    after_tax_coupon = coupon * (1 - h["FY2015"]["federal_statutory_rate"])
    for i, row in enumerate(range(12, 17)):
        yr = FORECAST_YEARS[i]
        add_back = after_tax_coupon if i < 4 else 0.0
        ufcf = FC["levered_fcf"][i] + add_back
        note = (f"Unlevered FCF {yr} = management levered free cash flow {FC['levered_fcf'][i]} "
                f"(CFO {FC['cfo'][i]} - capex {FC['capex'][i]}) + after-tax cash coupon on the 0.50% notes "
                f"({q['convertible_notes_principal']} x 0.50% x (1 - 35% federal statutory rate) = {add_back:.4f}).")
        if i == 4:
            note = (f"Unlevered FCF {yr} = management levered free cash flow {FC['levered_fcf'][i]}; the notes "
                    "mature 2019-11-01, so no coupon is paid in 2020 and levered equals unlevered.")
        emit("Transaction Analysis", f"C{row}", ufcf, "derived", "proxy", note)
        emit("Transaction Analysis", f"D{row}", ufcf, "derived", "proxy",
             note + " Same in Adversarial: the Analyst Projections Qatalyst also used are not disclosed "
             "numerically, so the Adversarial stress sits in the discount rate and terminal growth instead.")
    emit("Transaction Analysis", "C17", PREMIA["tech_500m_plus_median_2009_2016"], "modeler_assumption", "dwre_14d9",
         "Offer-premium warning = 37%: Goldman Sachs' 'Median' of the eight annual AVERAGE one-day premia of "
         "all-cash U.S. technology acquisitions above $500mm enterprise value, 2009 to 2016-05-27 (39%, 41%, "
         "35%, 35%, 34%, 36%, 38%, 41%; median of the eight = (36% + 38%) / 2 = 37%). It is a median of yearly "
         "averages, not the median deal premium (Demandware 14D-9, Selected Historical Premia Analysis).")
    declare("Transaction Analysis", "C17", "scenario_lever",
            "Premium escalation threshold: a policy screen, set at the precedent median.", "dwre_14d9",
            "$500M+ tech all-cash premia: median of the 2009-2016 annual averages 37%; 2016 YTD average 41%.")
    emit("Transaction Analysis", "D17", PREMIA["saas_median"], "modeler_assumption", "dwre_14d9",
         "Adversarial offer-premium warning = 31%, the median premium of the SaaS transactions in the same "
         "Goldman Sachs analysis (high 120%, average 40%, low 18%).")
    declare("Transaction Analysis", "D17", "scenario_lever",
            "Stricter Adversarial premium screen at the SaaS precedent median.", "dwre_14d9",
            "SaaS transaction premia: median 31%, average 40%.")
    half_width = ((QATALYST["dcf_value_per_share_high_usd"] - QATALYST["dcf_value_per_share_low_usd"])
                  / (QATALYST["dcf_value_per_share_high_usd"] + QATALYST["dcf_value_per_share_low_usd"]))
    for col in ("C", "D"):
        emit("Transaction Analysis", f"{col}18", half_width, "modeler_assumption", "proxy",
             f"Valuation-dispersion warning = half-width of Qatalyst's own DCF range relative to its midpoint: "
             f"(238.39 - 156.43) / (238.39 + 156.43) = {half_width:.6f}. A DCF/bridge gap wider than the "
             "advisor's own DCF uncertainty band is escalated.")
        declare("Transaction Analysis", f"{col}18", "scenario_lever",
                "Dispersion tolerance: a policy screen.", "proxy",
                "Qatalyst illustrative DCF range $156.43-$238.39 per share.")

    # ---------------- Accretion / Dilution (Microsoft) ----------------
    etr = MSFT["provision_for_tax"] / MSFT["income_before_tax"]
    for col in ("C", "D"):
        emit("Accretion Dilution", f"{col}5", MSFT["net_income"], "observed", "msft_10k",
             "Microsoft FY2016 (year ended 2016-06-30) net income $16,798mm, income statement.")
        emit("Accretion Dilution", f"{col}6", MSFT["diluted_shares_mm"], "observed", "msft_10k",
             "Microsoft FY2016 weighted-average diluted shares 8,013mm, income statement.")
        emit("Accretion Dilution", f"{col}10", 0.0, "observed", "proxy",
             "All-cash consideration of $196.00 per share; Microsoft issues no shares.")
        emit("Accretion Dilution", f"{col}11", -0.01, "modeler_assumption", "msft_deck",
             "Minimum accretion = -1%: Microsoft's own approval boundary, 'minimally (~1%) dilutive to non-GAAP "
             "EPS in FY17 and FY18'. CAVEAT: that guidance is non-GAAP and excludes purchase accounting; this "
             "sheet uses GAAP earnings without purchase accounting, so the two are not like for like.")
        declare("Accretion Dilution", f"{col}11", "scenario_lever",
                "Dilution tolerance taken from the buyer's disclosed expectation.", "msft_deck",
                "Slide 23: '~1% dilutive to non-GAAP EPS in FY17 and FY18 ... accretive ... in FY19'.")
    emit("Accretion Dilution", "C7", h["FY2015"]["net_loss"], "observed", "lnkd_10k",
         "LinkedIn FY2015 net loss (164.761) $mm, the last full year before signing.")
    emit("Accretion Dilution", "D7", float(FC["net_income"][0]), "observed", "proxy",
         "Adversarial target earnings = LinkedIn management's 2016E net loss (275) $mm from the Forecasts' "
         "reconciliation: the first year Microsoft owns LinkedIn, and worse than FY2015.")
    emit("Accretion Dilution", "C8", MSFT_COST_SYNERGIES_PRETAX * (1 - etr), "derived", "msft_deck",
         f"After-tax synergies = $150mm annual cost synergies 'by 2018' (slide 23) x (1 - Microsoft FY2016 "
         f"effective tax rate {etr:.6f} = 2,953 / 19,751, 10-K).")
    emit("Accretion Dilution", "D8", 0.0, "modeler_assumption", "msft_deck",
         "Adversarial synergies = 0: the $150mm is guided as a run rate 'by 2018', so none is assured in the "
         "first year after closing.")
    declare("Accretion Dilution", "D8", "scenario_lever", "Synergies not yet realized in year one.",
            "msft_deck", "'$150 million of cost synergies annually by 2018'.")
    principal = sum(p for p, _ in NOTES)
    coupon_total = sum(p * c for p, c in NOTES)
    wavg = coupon_total / principal
    emit("Accretion Dilution", "C9", coupon_total * (1 - etr), "derived", "msft_fwp",
         f"After-tax interest on the August 2016 notes: coupons {', '.join(f'{p}x{c:.3%}' for p, c in NOTES)} "
         f"= {coupon_total:.3f} $mm pre-tax on {principal} $mm, x (1 - {etr:.6f}). The 424B2 names the "
         "LinkedIn acquisition as a use of proceeds.")
    emit("Accretion Dilution", "D9", MSFT_DEAL_EV * wavg * (1 - etr), "derived", "msft_fwp",
         f"Adversarial: the whole $26,200mm financed at the notes' weighted coupon {wavg:.6f} "
         f"(Microsoft: 'financed primarily with new debt'), after tax at {etr:.6f}.")

    # ---------------- Comps ----------------
    rows = range(5, 12)
    comps_snapshot = []
    for row, p in zip(rows, PEERS):
        name, url, filed = PEER_SOURCES[p["ticker"]]
        if "class_c_shares_mm" in p:
            ab_shares = p["shares_mm"] - p["class_c_shares_mm"]
            mcap = p["close"] * ab_shares + p["class_c_close"] * p["class_c_shares_mm"]
            mcap_note = (f"Market cap = Class A + Class B {ab_shares:.6f}mm x GOOGL close {p['close']} + Class C "
                         f"{p['class_c_shares_mm']:.6f}mm x GOOG close {p['class_c_close']} = {mcap:.1f} $mm "
                         "(10-Q cover share counts at 2016-04-21). Class B is unlisted and converts 1:1 into "
                         f"Class A, so it takes the Class A price. {p['class_c_note']}; "
                         f"source {S['yahoo_goog']['url']}.")
        else:
            mcap = p["close"] * p["shares_mm"]
            mcap_note = (f"Market cap = {p['close']} x {p['shares_mm']:.6f}mm shares outstanding "
                         f"({p.get('shares_src', '10-Q cover, all classes')}) = {mcap:.1f} $mm.")
        ev = mcap + p["debt"] - p["cash"]
        ebitda = p["ltm_opinc"] + p["ltm_da"]
        price_key = p["price_src"]
        if price_key == "yahoo":
            # One source per ticker: each close is cited to its own chart, not a shared one.
            price_key = f"yahoo_{p['ticker']}"
            S.setdefault(price_key, {**S["yahoo"], "name": f"{S['yahoo']['name']}, {p['ticker']}",
                                     "url": S["yahoo"]["url"].replace("/chart/CRM?", f"/chart/{p.get('yahoo_symbol', p['ticker'])}?")})

        def pe(sheet_cell: str, value: Any, kind: str, note: str, key: str = "") -> None:
            inputs.append({"sheet": "Comps", "cell": sheet_cell,
                           "value": r6(value) if isinstance(value, float) else value,
                           "input_kind": kind,
                           "source": ({"name": name, "url": url, "as_of": filed, "notes": note} if not key
                                      else src(key, note)),
                           "emitted_by": OWNER})
        pe(f"B{row}", p["ticker"], "observed",
           f"Qatalyst selected company ({'consumer internet' if row < 9 else 'SaaS'}); proxy page 53.")
        pe(f"C{row}", p["close"], "observed" if p["ticker"] in ("TWTR", "CRM", "WDAY", "FB") else "derived",
           f"Close on 2016-06-10, the date Qatalyst used. {p['price_note']}.", key=price_key)
        pe(f"D{row}", mcap, "derived", mcap_note)
        pe(f"E{row}", ev, "derived",
           f"EV = market cap {mcap:.1f} + debt {p['debt']:.3f} - cash and current marketable securities "
           f"{p['cash']:.3f} = {ev:.1f} $mm (latest balance sheet filed before 2016-06-10; capital leases excluded).")
        pe(f"F{row}", ev / p["ltm_rev"], "derived",
           f"EV / LTM revenue {p['ltm_rev']:.3f} $mm (latest fiscal year + latest quarter - prior-year quarter, "
           "SEC XBRL company facts). Qatalyst used CY17E consensus, which is not public.")
        if ebitda > 0:
            pe(f"G{row}", ev / ebitda, "derived",
               f"EV / LTM EBITDA, EBITDA = operating income {p['ltm_opinc']:.3f} + D&A {p['ltm_da']:.3f} "
               f"= {ebitda:.3f} $mm (GAAP, stock compensation not added back).")
        else:
            pe(f"G{row}", "NM", "derived",
               f"Not meaningful: LTM EBITDA = operating income {p['ltm_opinc']:.3f} + D&A {p['ltm_da']:.3f} "
               f"= {ebitda:.3f} $mm is negative. MEDIAN ignores the text.")
        if p["ltm_ni"] is not None and p["ltm_ni"] > 0:
            pe(f"H{row}", mcap / p["ltm_ni"], "derived",
               f"P/E = market cap {mcap:.1f} / LTM net income {p['ltm_ni']:.3f} $mm.")
        else:
            ni = "a net loss in every period of the window (basic-and-diluted EPS LTM -1.61)" \
                if p["ltm_ni"] is None else f"LTM net income {p['ltm_ni']:.3f} $mm"
            pe(f"H{row}", "NM", "derived", f"Not meaningful: {ni}.")
        comps_snapshot.append({"ticker": p["ticker"], "close_usd_2016_06_10": p["close"],
                               "shares_outstanding_mm": r6(p["shares_mm"]), "market_cap_usd_mm": round(mcap, 3),
                               "debt_usd_mm": round(p["debt"], 3), "cash_usd_mm": round(p["cash"], 3),
                               "enterprise_value_usd_mm": round(ev, 3), "ltm_revenue_usd_mm": p["ltm_rev"],
                               "ltm_operating_income_usd_mm": p["ltm_opinc"], "ltm_da_usd_mm": p["ltm_da"],
                               "ltm_net_income_usd_mm": p["ltm_ni"], "filing": url, "filed": filed,
                               "price_source": S[price_key]["name"], "price_note": p["price_note"],
                               **({"class_c_shares_mm": p["class_c_shares_mm"],
                                   "class_c_close_usd_2016_06_10": p["class_c_close"],
                                   "class_c_price_source": S["yahoo_goog"]["name"]}
                                  if "class_c_shares_mm" in p else {})})

    # ---------------- Cover ----------------
    cover = {
        "Title:": "LNKD — LinkedIn Corporation: Microsoft acquisition of LinkedIn",
        "Sector:": "Internet professional network -- SEC SIC 7370 (Services-Computer Programming, "
                   "Data Processing, Etc.), as filed by the registrant",
        "Coverage started:": "2016-06-13",
        "Next earnings date:": "None -- the merger completed on 2016-12-08 and LinkedIn became a wholly "
                               "owned subsidiary of Microsoft (Form 8-K, 2016-12-08)",
    }
    thesis = (
        "Microsoft paid $196.00 a share in cash for LinkedIn, a 49.5% premium to the 2016-06-10 close of "
        "$131.08 and a $26.2bn enterprise value, financed primarily with new debt; the merger closed on "
        "2016-12-08. The price rests on management's Forecasts, which grow revenue from $2,991mm in 2015 "
        "to $7,365mm in 2020 and levered free cash flow from $458mm to $2,107mm: at Qatalyst's 10.0%-13.0% "
        "discount rates, the case is whether those cash flows arrive, not the bridge."
    )
    emit("Cover", "B11", thesis, "derived", "proxy",
         "Thesis stated in terms of the disclosed figures it rests on: offer price and premium (proxy), "
         "unaffected close (Alpha Vantage), enterprise value and financing (Microsoft deck), revenue and FCF "
         "(10-K and Forecasts), discount-rate range (Qatalyst).")
    drivers.append({"sheet": "Cover", "cell": "C5", "driver_type": "presentation_convention",
                    "rationale": "Coverage start = the public announcement of the merger agreement, the date "
                                 "the transaction analysis begins.",
                    "basis": {"source_name": S["msft_deck"]["name"], "source_url": S["msft_deck"]["url"],
                              "as_of": "2016-06-13"}, "emitted_by": OWNER})
    drivers.append({"sheet": "Cover", "cell": "C6", "driver_type": "generated_metadata",
                    "rationale": "Populated automatically from the manifest as_of date, the merger-completion "
                                 "date and the case's information cutoff.",
                    "basis": {"source_name": S["close_8k"]["name"], "source_url": S["close_8k"]["url"],
                              "as_of": AS_OF}, "emitted_by": OWNER})
    drivers.append({"sheet": "Cover", "cell": "B17", "driver_type": "presentation_convention",
                    "rationale": "Colour-legend row, a presentation convention rather than an input. The "
                                 "coverage scanner's legend exclusion matches only 'Blue text / yellow fill'; "
                                 "this template writes 'Blue text', so the row is declared here instead.",
                    "basis": {"source_name": "Template colour legend written by "
                                             "tools/builders/build_investment_banking_release.py",
                              "source_url": "repo://01_Investment_Banking/_template_BASE.xlsx"},
                    "emitted_by": OWNER})

    # ---------------- Presentation fills ----------------
    # The template ships bracketed placeholders outside the input surface: a
    # "Source: [10-K/10-Q cite or user estimate]" note on every Assumptions row
    # and "[data table — Excel What-If Analysis]" in the Sensitivity grid. They
    # are replaced here, through the manifest, never by editing the workbook.
    fills: list[dict[str, Any]] = []

    def fill(sheet: str, cell: str, value: Any, purpose: str, key: str, note: str) -> None:
        fills.append({"sheet": sheet, "cell": cell, "value": value, "purpose": purpose,
                      "source": src(key, note), "emitted_by": OWNER})

    proxy_cite = "LinkedIn DEFM14A filed 2016-07-22, management Forecasts pp. 58-60"
    row_notes = {
        5: ("proxy", f"Source: {proxy_cite}: revenue 2016E-2020E over the prior year; FY2015 base 2,990.911 $mm "
                     "from the FY2015 10-K. Derived."),
        6: ("lnkd_10k", f"Driver: held at the FY2015 actual {gm_2015:.4%} (FY2015 10-K, filed 2016-02-12). The "
                        "Forecasts do not disclose cost of revenue. Declared modeler_assumption."),
        7: ("proxy", f"Driver (balancing residual): gross margin less the EBIT margin implied by the Forecasts "
                     f"(net income + tax + other expense; {proxy_cite}). EBIT ties to the Forecasts exactly."),
        8: ("proxy", f"Source: {proxy_cite}: tax provision / pre-tax income. 2016E is negative because the "
                     "Forecasts carry a tax provision on a pre-tax loss. Derived."),
        9: ("proxy", f"Source: {proxy_cite}: D&A / purchases of property and equipment. Derived."),
        10: ("proxy", f"Source: {proxy_cite}: purchases of property and equipment / revenue. Derived."),
        11: ("proxy", f"Source: {proxy_cite}: -(CFO - net income - D&A - SBC) / revenue change. The residual "
                      "also holds non-cash items the Forecasts do not separate. Derived."),
        12: ("proxy", f"Driver: fully diluted {fd196:.3f}mm at $196 (10-Q for 2016-03-31) grown geometrically to "
                      "the proxy's ~12% management-projected dilution over five years. Declared modeler_assumption."),
        13: ("proxy", "Source: midpoint of Qatalyst Partners' 10.0%-13.0% discount-rate range (DEFM14A filed "
                      "2016-07-22). Derived."),
        14: ("treasury", "Driver: 30-year Treasury par yield 2.44% on 2016-06-10 (U.S. Treasury daily par yield "
                         "curve). Declared modeler_assumption."),
    }
    for row, (key, text) in row_notes.items():
        fill("Assumptions", f"H{row}", text, "source_note", key,
             f"Row-level source note for Assumptions row {row}; each cell's full derivation is in its own "
             "manifest input.")
    for r in range(5, 10):
        for c in "CDEFG":
            formula = (f'=IF(OR(IS!$E$5="",IS!$E$5=0),"n/a - no forecast base",'
                       f"(NPV($B{r},DCF!$C$5:$G$5)+DCF!$G$5*(1+{c}$4)/($B{r}-{c}$4)/(1+$B{r})^5"
                       f"-DCF!$I$11)/DCF!$I$13)")
            fill("Sensitivity", f"{c}{r}", formula, "formula_grid", "proxy",
                 "Implied value per share at WACC in column B and terminal growth in row 4: the DCF sheet's "
                 "own arithmetic (end-of-year discounting of DCF!C5:G5, Gordon terminal value on DCF!G5, less "
                 "net debt DCF!I11, over diluted shares DCF!I13) with the two rates replaced. At the Base "
                 "11.5% / 2.44% it reproduces DCF!I14. The axis values are the template's grid.")
    comps_note = (
        "Peer set: Qatalyst Partners selected 10 companies (DEFM14A p. 53): consumer internet Alphabet, Amazon, "
        "Facebook, Twitter; SaaS Cornerstone OnDemand, NetSuite, Salesforce, ServiceNow, Ultimate Software, "
        "Workday. The template has 7 rows, so the 3 smallest SaaS peers by LTM revenue (NetSuite "
        f"{SAAS_LTM_REVENUE['N']:,.1f}, Ultimate Software {SAAS_LTM_REVENUE['ULTI']:,.1f}, Cornerstone OnDemand "
        f"{SAAS_LTM_REVENUE['CSOD']:,.1f} $mm) are omitted. Template limitation, not a selection judgment. "
        "Multiples are LTM; Qatalyst used CY2017E consensus, which is not public."
    )
    fill("Comps", "B15", comps_note, "source_note", "proxy",
         "Discloses that the comps table carries 7 of Qatalyst's 10 selected companies.")

    # A modeler_assumption already declared above must not ALSO be counted as an
    # undeclared driver; the scanner keys both forms on (sheet, cell).
    sources_used = sorted({i["source"]["url"] for i in inputs})
    source_entries = []
    for key, s in S.items():
        if key == "yahoo":
            continue  # template for the per-ticker entries; each close cites its own ticker's chart
        if s["url"] in sources_used or key in ("close_8k", "msft_424b2", "q3_10q", "yahoo_goog"):
            source_entries.append({"name": s["name"], "url": s["url"], "as_of": s["as_of"],
                                   "notes": f"{s['publisher']}."})
    for ticker, (name, url, filed) in PEER_SOURCES.items():
        source_entries.append({"name": name, "url": url, "as_of": filed,
                               "notes": "Cover share count; balance sheet and LTM figures via SEC XBRL company facts."})
    source_entries.append({"name": "SEC XBRL company facts (peers and LinkedIn), facts filed on or before 2016-06-10",
                           "url": "https://data.sec.gov/api/xbrl/companyfacts/CIK0001271024.json",
                           "as_of": UNAFFECTED,
                           "notes": "Same API for each peer CIK: 1652044, 1018724, 1326801, 1418091, 1108524, "
                                    "1327811, 1373715; and 1117106, 1016125, 1401680 for the SaaS revenue ranking."})
    source_entries.append({"name": "Frozen source snapshot",
                           "url": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}", "as_of": AS_OF,
                           "notes": "Immutable curated observation package with SHA-256 digest"})
    assert_no_hindsight(source_entries + [i["source"] for i in inputs])

    snapshot_existing = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    snapshot = {
        **snapshot_existing,
        "capture_method": "curated_public_observation_from_primary_filings",
        "sources": [
            {"name": S["q3_10q"]["name"], "url": S["q3_10q"]["url"], "publisher": S["q3_10q"]["publisher"],
             "captured_values": snapshot_existing["sources"][0]["captured_values"]},
            {"name": S["close_8k"]["name"], "url": S["close_8k"]["url"], "publisher": S["close_8k"]["publisher"],
             "captured_values": {"merger_completed": 1}},
            {"name": S["proxy"]["name"], "url": S["proxy"]["url"], "publisher": S["proxy"]["publisher"],
             "captured_values": {"forecast_years": FORECAST_YEARS,
                                 **{f"forecast_{k}_usd_mm": v for k, v in FC.items()},
                                 "qatalyst_dcf_discount_rate_low": QATALYST["dcf_discount_rate_low"],
                                 "qatalyst_dcf_discount_rate_high": QATALYST["dcf_discount_rate_high"],
                                 "qatalyst_dcf_value_per_share_low_usd": QATALYST["dcf_value_per_share_low_usd"],
                                 "qatalyst_dcf_value_per_share_high_usd": QATALYST["dcf_value_per_share_high_usd"],
                                 "projected_dilution_from_equity_grants": 0.12,
                                 "consumer_internet_peers": QATALYST["consumer_internet_peers"],
                                 "saas_peers": QATALYST["saas_peers"],
                                 "premium_to_unaffected_close": 0.495,
                                 "offer_price_usd": OFFER_PRICE,
                                 "record_date_class_a_shares": 119167595,
                                 "record_date_class_b_shares": 15559383}},
            {"name": S["lnkd_10k"]["name"], "url": S["lnkd_10k"]["url"], "publisher": S["lnkd_10k"]["publisher"],
             "captured_values": {fy: {f"{k}_usd_mm" if k not in ("diluted_shares_mm", "federal_statutory_rate") else k: v
                                      for k, v in vals.items()} for fy, vals in LNKD_HIST.items()}},
            {"name": S["lnkd_10q"]["name"], "url": S["lnkd_10q"]["url"], "publisher": S["lnkd_10q"]["publisher"],
             "captured_values": {k if not isinstance(v, float) or k.endswith(("_usd", "coupon")) else f"{k}_usd_mm": v
                                 for k, v in LNKD_Q1.items()}},
            {"name": S["av_weekly"]["name"], "url": S["av_weekly"]["url"], "publisher": S["av_weekly"]["publisher"],
             "captured_values": {"LNKD_close_usd_2016_06_10": LNKD_UNAFFECTED_CLOSE,
                                 "TWTR_close_usd_2016_06_10": 14.02,
                                 "check_offer_premium": round(OFFER_PRICE / LNKD_UNAFFECTED_CLOSE - 1, 6)}},
            {"name": S["msft_deck"]["name"], "url": S["msft_deck"]["url"], "publisher": S["msft_deck"]["publisher"],
             "captured_values": {"enterprise_value_usd_mm": MSFT_DEAL_EV,
                                 "cost_synergies_annual_by_2018_usd_mm": MSFT_COST_SYNERGIES_PRETAX,
                                 "eps_guidance": "~1% dilutive to non-GAAP EPS in FY17 and FY18; accretive in FY19",
                                 "financing": "primarily new debt"}},
            {"name": S["msft_10k"]["name"], "url": S["msft_10k"]["url"], "publisher": S["msft_10k"]["publisher"],
             "captured_values": {f"{k}_usd_mm" if k != "diluted_shares_mm" else k: v for k, v in MSFT.items()}},
            {"name": S["msft_fwp"]["name"], "url": S["msft_fwp"]["url"], "publisher": S["msft_fwp"]["publisher"],
             "captured_values": {"tranches": [{"principal_usd_mm": p, "coupon": c} for p, c in NOTES],
                                 "total_principal_usd_mm": principal,
                                 "annual_coupon_usd_mm": round(coupon_total, 3)}},
            {"name": S["treasury"]["name"], "url": S["treasury"]["url"], "publisher": S["treasury"]["publisher"],
             "captured_values": {"date": UNAFFECTED, "par_yield_30y": UST_30Y_2016_06_10, "par_yield_10y": 0.0164}},
            {"name": S["fomc"]["name"], "url": S["fomc"]["url"], "publisher": S["fomc"]["publisher"],
             "captured_values": {"longer_run_inflation_goal_pce": FOMC_INFLATION_GOAL}},
            {"name": S["dwre_14d9"]["name"], "url": S["dwre_14d9"]["url"], "publisher": S["dwre_14d9"]["publisher"],
             "captured_values": PREMIA},
            {"name": "Comparable companies at 2016-06-10", "url": "https://data.sec.gov/api/xbrl/companyfacts/",
             "publisher": "U.S. SEC (XBRL company facts and 10-Q cover pages); prices per row",
             "captured_values": {"rows": comps_snapshot,
                                 "saas_selection_rule": "three largest SaaS peers by LTM revenue",
                                 "saas_ltm_revenue_usd_mm": SAAS_LTM_REVENUE}},
        ],
        "input_overrides": [
            {"sheet": i["sheet"], "cell": i["cell"], "value": i["value"], "kind": i["input_kind"],
             "source": i["source"]["name"]} for i in inputs
        ],
    }
    snapshot.pop("snapshot_sha256", None)
    snapshot["snapshot_sha256"] = hashlib.sha256(canonical_bytes(snapshot)).hexdigest()

    def key(item: dict[str, Any]) -> tuple[str, int, str]:
        cell = item["cell"]
        letters = "".join(c for c in cell if c.isalpha())
        return (item["sheet"], int(cell[len(letters):]), letters)

    manifest = {
        **existing,
        "cover": cover,
        "inputs": sorted(inputs, key=key),
        "sources": source_entries,
        "refresh": {
            "date": date.today().isoformat(),
            "trigger": "Depth pass: every template input accounted for from primary filings",
            "source_snapshot": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
            "what_changed": (
                "Sourced the LinkedIn FY2013-FY2015 income statement, the forward driver grid from "
                "management's Forecasts in the merger proxy, the DCF and transaction bridge from the "
                "2016-03-31 10-Q, Qatalyst's discount-rate range and peer set, the Microsoft accretion "
                "inputs from its FY2016 10-K, investor deck and August 2016 note pricing, and the Cover. "
                "Corrected approximations: buyer earnings 16,800 -> 16,798, buyer diluted shares "
                "8,000 -> 8,013, and target diluted shares 133.67 (solved as 26,200 / 196) -> 142.50 "
                "counted fully diluted. The Adversarial column now carries the unaffected market bridge "
                "and the top of the discount-rate range instead of a copy of Base."
            ),
            "reviewer_notes": (
                "External historical case; human stakeholder approval remains pending. Drivers without "
                "a disclosure are declared with the named data that grounds them."
            ),
            "next_check": "On source revision, builder change, monitoring breach, or annual review",
        },
        "driver_declarations": sorted(drivers, key=key),
        "presentation_fills": sorted(fills, key=key),
    }
    return manifest, snapshot


def fd_note(price: float) -> str:
    q = LNKD_Q1
    basic = (q["class_a_shares_2016_04_21"] + q["class_b_shares_2016_04_21"]) / 1e6
    tsm = q["options_outstanding_2016_03_31"] / 1e6 * max(0.0, 1 - q["options_weighted_avg_exercise_usd"] / price)
    return (f"Fully diluted shares at ${price:.2f} = Class A 117,984,839 + Class B 15,559,383 (cover, 2016-04-21) "
            f"= {basic:.6f}mm + unvested RSUs 7.766829mm + options 2.534824mm x (1 - 104.19 / {price:.2f}) "
            f"= {tsm:.6f}mm by the treasury-stock method on the weighted-average strike = "
            f"{fd_shares(price):.6f}mm. The convertible notes are out of the money and excluded.")


def write_source_register(snapshot: dict[str, Any], manifest: dict[str, Any]) -> None:
    header = "case_id,source_name,publisher,url,as_of,snapshot,snapshot_sha256,status"
    lines = [header]
    if REGISTER_PATH.exists():
        existing = REGISTER_PATH.read_text(encoding="utf-8").splitlines()
        lines = [line for line in (existing or lines) if not line.startswith(f"{CASE_ID},")]
    snap = str(SNAPSHOT_PATH.relative_to(ROOT))
    for s in manifest["sources"]:
        if s["url"].startswith("repo://"):
            continue
        publisher = next((v["publisher"] for v in S.values() if v["url"] == s["url"]), "U.S. SEC")
        row = (CASE_ID, s["name"], publisher, s["url"], s["as_of"], snap, snapshot["snapshot_sha256"], "frozen")
        lines.append(",".join(f'"{f}"' if "," in str(f) else str(f) for f in row))
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
    write_source_register(snapshot, manifest)
    from public_case_index import report_sync  # keep the ledger hash in step with the snapshot
    print(report_sync(CASE_ID, snapshot["snapshot_sha256"]))
    print(f"inputs={len(manifest['inputs'])} drivers={len(manifest['driver_declarations'])} "
          f"snapshot_sha256={snapshot['snapshot_sha256'][:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
