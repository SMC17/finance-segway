"""Source every input of the HP / Autonomy 2012 stress case from public filings.

The case asks one question: on 31 October 2012, the last day of Hewlett-
Packard's fiscal 2012, could a reader holding only public information have
seen that the $11 billion paid for Autonomy Corporation plc was not supported?
Three weeks later, on 20 November 2012, HP announced an $8.8 billion
impairment of the Autonomy business.

THE SUBJECT OF EACH SHEET
-------------------------
  - IS, Assumptions, DCF, Comps: Autonomy, the target. Its own reported
    accounts (IFRS, presented in US dollars) for 2008-2010, the last three
    years it reported before HP bought it, valued at the case date.
  - Transaction Analysis: the offer. Base = the terms as underwritten on
    18 August 2011, with an as-reported growth path. Adversarial = the same
    terms tested on the case date under a no-growth stress.
  - Accretion Dilution: HP, the buyer. Base = HP's own non-GAAP framing (the
    basis on which HP said the deal would be accretive). Adversarial = GAAP.

NO HINDSIGHT
------------
Every input comes from a document published on or before 2012-10-31. The
fiscal 2012 Form 10-K (filed 2012-12-27) and the 20 November 2012 earnings
release are after the case date. They are kept only as the source of the
recorded outcome. This replaces three earlier inputs that cited the FY2012
10-K: the $11.1bn purchase price, a "one unit" share normalisation, and a
$2.3bn post-impairment residual that had been placed in an FCF row.

The Damodaran cost-of-capital files are named by the year their data
describes, not the year they were published: wacc11.xls carries a 1.87%
Treasury rate, the 10-year yield on 2011-12-30, so it is the January 2012
release. wacc12.xls (January 2013) is therefore excluded.

WHAT COULD NOT BE SOURCED, AND WHAT STANDS IN ITS PLACE
-------------------------------------------------------
Discount rates, terminal growth, the two policy screens, the synergy credit
and the minimum-accretion bar are not disclosed facts about Autonomy. Each
is a declared driver whose `basis` names the public data that sets it. They
earn coverage as grounded drivers, never as observations.

Usage:
    python tools/deepen_investment_banking_hp_autonomy.py            # write
    python tools/deepen_investment_banking_hp_autonomy.py --print-only
    python tools/deepen_investment_banking_hp_autonomy.py --verify-sources [--cache DIR]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

CASE_ID = "ib-public-hp-autonomy-2012-stress"
AS_OF = "2012-10-31"
MANIFEST_PATH = ROOT / "standards" / "public_cases" / f"{CASE_ID}.json"
SNAPSHOT_PATH = ROOT / "01_Investment_Banking" / "sources" / "snapshots" / f"{CASE_ID}.json"
REGISTER_PATH = ROOT / "01_Investment_Banking" / "sources" / "source_register.csv"
EMITTED_BY = "tools/deepen_investment_banking_hp_autonomy.py"

EDGAR = "https://www.sec.gov/Archives/edgar/data"

# --------------------------------------------------------------------------
# Sources. `published` is the date the document became public, which is the
# date the no-hindsight rule tests. Every input source is on or before AS_OF.
# --------------------------------------------------------------------------
SOURCES: dict[str, dict[str, Any]] = {
    "auto_fy2010": {
        "name": "Autonomy Corporation plc results for the year ended December 31, 2010 (PR Newswire release)",
        "url": "https://www.prnewswire.com/news-releases/autonomy-corporation-plc-announced-results-for-the-year-ended-december-31-2010-114992659.html",
        "publisher": "Autonomy Corporation plc via PR Newswire",
        "published": "2011-02-01",
        "kind": "html",
    },
    "auto_fy2009": {
        "name": "Autonomy Corporation plc results for the twelve months ended December 31, 2009 (PR Newswire release)",
        "url": "https://www.prnewswire.com/news-releases/autonomy-corporation-plc-announces-results-for-the-twelve-months-and-fourth-quarter-ended-december-31-2009-83419142.html",
        "publisher": "Autonomy Corporation plc via PR Newswire",
        "published": "2010-02-03",
        "kind": "html",
    },
    "hp_8k_20110819": {
        "name": "HP Form 8-K filed 2011-08-19, Item 1.01 (Autonomy Offer Agreement)",
        "url": f"{EDGAR}/47217/000110465911047805/a11-24706_18k.htm",
        "publisher": "U.S. SEC / Hewlett-Packard",
        "published": "2011-08-19",
        "kind": "html",
    },
    "rule_2_5": {
        "name": "Rule 2.5 Announcement of the recommended cash offer for Autonomy (HP Form 8-K Exhibit 99.1, filed 2011-08-19)",
        "url": f"{EDGAR}/47217/000110465911047805/a11-24706_1ex99d1.htm",
        "publisher": "U.S. SEC / Hewlett-Packard",
        "published": "2011-08-19",
        "kind": "html",
    },
    "hp_10k_fy2011": {
        "name": "Hewlett-Packard Form 10-K for fiscal year ended 2011-10-31",
        "url": f"{EDGAR}/47217/000104746911010094/a2206500z10-k.htm",
        "publisher": "U.S. SEC / Hewlett-Packard",
        "published": "2011-12-14",
        "kind": "html",
    },
    "hp_q4fy11_release": {
        "name": "HP fourth quarter and fiscal 2011 results release (Form 8-K Exhibit 99.1, filed 2011-11-21)",
        "url": f"{EDGAR}/47217/000004721711000050/q4exhibit99-1.htm",
        "publisher": "U.S. SEC / Hewlett-Packard",
        "published": "2011-11-21",
        "kind": "html",
    },
    "hp_10q_q3fy12": {
        "name": "Hewlett-Packard Form 10-Q for the quarter ended 2012-07-31",
        "url": f"{EDGAR}/47217/000104746912008732/a2210845z10-q.htm",
        "publisher": "U.S. SEC / Hewlett-Packard",
        "published": "2012-09-10",
        "kind": "html",
    },
    "damodaran_wacc_jan2011": {
        "name": "Damodaran Online, cost of capital by industry, January 2011 release (archives/wacc10.xls)",
        "url": "https://pages.stern.nyu.edu/~adamodar/pc/archives/wacc10.xls",
        "publisher": "Aswath Damodaran, NYU Stern",
        "published": "2011-01-05",
        "kind": "xls",
    },
    "damodaran_wacc_jan2012": {
        "name": "Damodaran Online, cost of capital by industry, January 2012 release (archives/wacc11.xls)",
        "url": "https://pages.stern.nyu.edu/~adamodar/pc/archives/wacc11.xls",
        "publisher": "Aswath Damodaran, NYU Stern",
        "published": "2012-01-05",
        "kind": "xls",
    },
    "ust_2010": {
        "name": "U.S. Treasury daily par yield curve rates, 2010",
        "url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2010/all?type=daily_treasury_yield_curve&field_tdr_date_value=2010&page&_format=csv",
        "publisher": "U.S. Department of the Treasury",
        "published": "2010-12-31",
        "kind": "csv",
    },
    "ust_2011": {
        "name": "U.S. Treasury daily par yield curve rates, 2011",
        "url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2011/all?type=daily_treasury_yield_curve&field_tdr_date_value=2011&page&_format=csv",
        "publisher": "U.S. Department of the Treasury",
        "published": "2011-12-30",
        "kind": "csv",
    },
    "ust_2012": {
        "name": "U.S. Treasury daily par yield curve rates, 2012",
        "url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2012/all?type=daily_treasury_yield_curve&field_tdr_date_value=2012&page&_format=csv",
        "publisher": "U.S. Department of the Treasury",
        "published": "2012-10-31",
        "kind": "csv",
    },
    "hp_10k_fy2012_outcome": {
        "name": "Hewlett-Packard 2012 Form 10-K Autonomy impairment",
        "url": f"{EDGAR}/47217/000104746912011417/a2211959z10-k.htm",
        "publisher": "U.S. SEC / Hewlett-Packard",
        "published": "2012-12-27",
        "kind": "html",
        "outcome_only": True,
    },
}

# Comparable companies. Autonomy's two markets as HP named them in the
# Rule 2.5 announcement are enterprise information management and business
# analytics. The peers are SEC 10-K filers in those markets whose 2012 share
# price is still recoverable: OpenText (EIM), Oracle, IBM and Microsoft (EIM
# and analytics suites), CommVault (information management and archiving),
# Teradata and MicroStrategy (analytics). Price: close on 2012-10-31.
# Shares: latest cover-page count filed on or before 2012-10-31. Debt and
# cash: latest balance sheet filed on or before 2012-10-31. Revenue, EBITDA
# and EPS: last fiscal year reported in a 10-K filed on or before 2012-10-31.
# EBITDA = operating income + the cash-flow statement's depreciation and
# amortisation line(s); IBM reports no operating income, so for IBM it is
# pre-tax income + interest expense + depreciation + intangible amortisation.
YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{t}?period1=1351468800&period2=1351814400&interval=1d&events=split"
XBRL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
PEERS: list[dict[str, Any]] = [
    {
        "ticker": "OTEX", "name": "Open Text Corporation", "cik": "0001002638",
        "yahoo_close": 13.487500190734863, "split_factor": 4.0,
        "split_note": "2:1 splits on 2014-01-24 and 2017-01-23 (Yahoo split events); close is restated to the 2012 share basis by x4",
        "shares": ("dei:EntityCommonStockSharesOutstanding", "0001002638-12-000011", "2012-08-03", 58405575),
        "debt": [("LongTermDebt", "0001002638-12-000011", "2012-06-30", 596374000)],
        "cash": [("CashAndCashEquivalentsAtCarryingValue", "0001002638-12-000011", "2012-06-30", 559747000)],
        "revenue": ("Revenues", "0001002638-12-000011", "2012-06-30", 1207473000),
        "ebit_parts": [("OperatingIncomeLoss", "0001002638-12-000011", "2012-06-30", 149360000)],
        "da_parts": [("DepreciationDepletionAndAmortization", "0001002638-12-000011", "2012-06-30", 159485000)],
        "eps": ("EarningsPerShareDiluted", "0001002638-12-000011", "2012-06-30", 2.13),
    },
    {
        "ticker": "ORCL", "name": "Oracle Corporation", "cik": "0001341439",
        "yahoo_close": 31.079999923706055, "split_factor": 1.0, "split_note": "no split since 2012",
        # The XBRL dei tag in this 10-Q is mis-scaled (4,819,056,000,000,000);
        # the filing's cover page text reads 4,819,056,000.
        "shares": ("cover page text", "0001193125-12-401697", "2012-09-17", 4819056000),
        "shares_url": f"{EDGAR}/1341439/000119312512401697/d397317d10q.htm",
        "shares_excerpt": "The number of shares of registrant’s common stock outstanding as of September 17, 2012 was: 4,819,056,000.",
        "debt": [("DebtCurrent", "0001193125-12-401697", "2012-08-31", 1250000000),
                 ("LongTermNotesPayable", "0001193125-12-401697", "2012-08-31", 13521000000)],
        "cash": [("CashAndCashEquivalentsAtCarryingValue", "0001193125-12-401697", "2012-08-31", 15667000000),
                 ("AvailableForSaleSecuritiesCurrent", "0001193125-12-401697", "2012-08-31", 15940000000)],
        "revenue": ("Revenues", "0001193125-12-284007", "2012-05-31", 37121000000),
        "ebit_parts": [("OperatingIncomeLoss", "0001193125-12-284007", "2012-05-31", 13706000000)],
        "da_parts": [("Depreciation", "0001193125-12-284007", "2012-05-31", 486000000),
                     ("AmortizationOfIntangibleAssets", "0001193125-12-284007", "2012-05-31", 2430000000)],
        "eps": ("EarningsPerShareDiluted", "0001193125-12-284007", "2012-05-31", 1.96),
    },
    {
        "ticker": "IBM", "name": "International Business Machines Corporation", "cik": "0000051143",
        "yahoo_close": 185.9751434326172, "split_factor": 1.046,
        "split_note": "Yahoo carries the 2021-11-04 Kyndryl spin-off as a 1046:1000 split; close is restated to the 2012 basis by x1.046",
        "shares": ("dei:EntityCommonStockSharesOutstanding", "0001104659-12-072210", "2012-09-30", 1129932457),
        "debt": [("DebtCurrent", "0001104659-12-072210", "2012-09-30", 9334000000),
                 ("LongTermDebtNoncurrent", "0001104659-12-072210", "2012-09-30", 24333000000)],
        "cash": [("CashAndCashEquivalentsAtCarryingValue", "0001104659-12-072210", "2012-09-30", 11909000000),
                 ("MarketableSecuritiesCurrent", "0001104659-12-072210", "2012-09-30", 345000000)],
        "revenue": ("Revenues", "0001047469-12-001742", "2011-12-31", 106916000000),
        "ebit_parts": [("IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest", "0001047469-12-001742", "2011-12-31", 21003000000),
                       ("InterestExpense", "0001047469-12-001742", "2011-12-31", 411000000)],
        "da_parts": [("Depreciation", "0001047469-12-001742", "2011-12-31", 3589000000),
                     ("AmortizationOfIntangibleAssets", "0001047469-12-001742", "2011-12-31", 1226000000)],
        "eps": ("EarningsPerShareDiluted", "0001047469-12-001742", "2011-12-31", 13.06),
    },
    {
        "ticker": "MSFT", "name": "Microsoft Corporation", "cik": "0000789019",
        "yahoo_close": 28.540000915527344, "split_factor": 1.0, "split_note": "no split since 2012",
        "shares": ("dei:EntityCommonStockSharesOutstanding", "0001193125-12-427209", "2012-10-15", 8416462491),
        "debt": [("LongTermDebt", "0001193125-12-427209", "2012-09-30", 12000000000)],
        "cash": [("CashAndCashEquivalentsAtCarryingValue", "0001193125-12-427209", "2012-09-30", 5036000000),
                 ("AvailableForSaleSecuritiesCurrent", "0001193125-12-427209", "2012-09-30", 61608000000)],
        "revenue": ("SalesRevenueNet", "0001193125-12-316848", "2012-06-30", 73723000000),
        "ebit_parts": [("OperatingIncomeLoss", "0001193125-12-316848", "2012-06-30", 21763000000)],
        # Microsoft's cash-flow line "Depreciation, amortization, and other"
        # carries no single XBRL tag in this filing; read from the 10-K text.
        "da_parts": [("10-K cash flow line 'Depreciation, amortization, and other'", "0001193125-12-316848", "2012-06-30", 2967000000)],
        "da_url": f"{EDGAR}/789019/000119312512316848/d347676d10k.htm",
        "da_excerpt": "Depreciation, amortization, and other 2,967",
        "eps": ("EarningsPerShareDiluted", "0001193125-12-316848", "2012-06-30", 2.0),
    },
    {
        "ticker": "CVLT", "name": "CommVault Systems, Inc.", "cik": "0001169561",
        "yahoo_close": 62.369998931884766, "split_factor": 1.0, "split_note": "no split since 2012",
        "shares": ("dei:EntityCommonStockSharesOutstanding", "0001193125-12-332000", "2012-07-25", 44949576),
        "debt": [],
        "cash": [("CashAndCashEquivalentsAtCarryingValue", "0001193125-12-332000", "2012-06-30", 318135000),
                 ("ShortTermInvestments", "0001193125-12-332000", "2012-06-30", 1948000)],
        "revenue": ("Revenues", "0001193125-12-234191", "2012-03-31", 406639000),
        "ebit_parts": [("OperatingIncomeLoss", "0001193125-12-234191", "2012-03-31", 49299000)],
        "da_parts": [("DepreciationDepletionAndAmortization", "0001193125-12-234191", "2012-03-31", 4484000)],
        "eps": ("EarningsPerShareDiluted", "0001193125-12-234191", "2012-03-31", 0.68),
    },
    {
        "ticker": "TDC", "name": "Teradata Corporation", "cik": "0000816761",
        "yahoo_close": 68.30999755859375, "split_factor": 1.0, "split_note": "no split since 2012",
        "shares": ("dei:EntityCommonStockSharesOutstanding", "0001193125-12-333968", "2012-07-27", 168600000),
        "debt": [("10-Q text: term loan principal outstanding", "0001193125-12-333968", "2012-06-30", 296000000)],
        "debt_url": f"{EDGAR}/816761/000119312512333968/d377038d10q.htm",
        "debt_excerpt": "As of June 30, 2012, the term loan principal outstanding was $296 million",
        "cash": [("CashAndCashEquivalentsAtCarryingValue", "0001193125-12-333968", "2012-06-30", 821000000)],
        "revenue": ("Revenues", "0001193125-12-087334", "2011-12-31", 2362000000),
        "ebit_parts": [("OperatingIncomeLoss", "0001193125-12-087334", "2011-12-31", 456000000)],
        "da_parts": [("DepreciationAndAmortization", "0001193125-12-087334", "2011-12-31", 102000000)],
        "eps": ("EarningsPerShareDiluted", "0001193125-12-087334", "2011-12-31", 2.05),
    },
    {
        "ticker": "MSTR", "name": "MicroStrategy Incorporated", "cik": "0001050446",
        "yahoo_close": 9.446999549865723, "split_factor": 10.0,
        "split_note": "10:1 split on 2024-08-08 (Yahoo split event); close is restated to the 2012 basis by x10",
        # Two share classes; the dei tag is absent, the 10-Q cover states both.
        "shares": ("cover page text (class A + class B)", "0001193125-12-335169", "2012-07-24", 8707145 + 2227327),
        "shares_url": f"{EDGAR}/1050446/000119312512335169/d371508d10q.htm",
        "shares_excerpt": "8,707,145 and 2,227,327, respectively.",
        "debt": [],
        "cash": [("CashAndCashEquivalentsAtCarryingValue", "0001193125-12-335169", "2012-06-30", 195540000)],
        "revenue": ("Revenues", "0001193125-12-067605", "2011-12-31", 562150000),
        "ebit_parts": [("OperatingIncomeLoss", "0001193125-12-067605", "2011-12-31", 15042000)],
        "da_parts": [("DepreciationAmortizationAndAccretionNet", "0001193125-12-067605", "2011-12-31", 18526000)],
        "eps": ("EarningsPerShareDiluted", "0001193125-12-067605", "2011-12-31", 1.62),
    },
]

# --------------------------------------------------------------------------
# Captured observations: value, and the verbatim text (whitespace-collapsed)
# that `--verify-sources` looks for in the fetched document.
# Autonomy amounts are reported in $'000 and are converted to $mm here.
# --------------------------------------------------------------------------
OBS: dict[str, tuple[str, float, str]] = {
    # Autonomy FY2010 release (FY2010 and FY2009 columns)
    "auto_rev_2010_usd_mm": ("auto_fy2010", 870.366, "Revenues (see note 3) 870,366 739,688"),
    "auto_rev_2009_usd_mm": ("auto_fy2010", 739.688, "Revenues (see note 3) 870,366 739,688"),
    "auto_cogs_2010_usd_mm": ("auto_fy2010", 168.793, "Total cost of revenues (168,793) (137,397)"),
    "auto_cogs_2009_usd_mm": ("auto_fy2010", 137.397, "Total cost of revenues (168,793) (137,397)"),
    "auto_opex_2010_usd_mm": ("auto_fy2010", 385.158, "Total operating expenses (385,158) (330,113)"),
    "auto_opex_2009_usd_mm": ("auto_fy2010", 330.113, "Total operating expenses (385,158) (330,113)"),
    "auto_ebit_2010_usd_mm": ("auto_fy2010", 316.415, "Profit from operations 316,415 272,178"),
    "auto_ebit_2009_usd_mm": ("auto_fy2010", 272.178, "Profit from operations 316,415 272,178"),
    "auto_pbt_2010_usd_mm": ("auto_fy2010", 282.194, "Profit before income taxes 282,194 266,066"),
    "auto_pbt_2009_usd_mm": ("auto_fy2010", 266.066, "Profit before income taxes 282,194 266,066"),
    "auto_tax_2010_usd_mm": ("auto_fy2010", 64.901, "Income taxes (see note 4) (64,901) (74,515)"),
    "auto_tax_2009_usd_mm": ("auto_fy2010", 74.515, "Income taxes (see note 4) (64,901) (74,515)"),
    "auto_net_profit_2010_usd_mm": ("auto_fy2010", 217.293, "Net profit 217,293 191,551"),
    "auto_adj_net_profit_2010_usd_mm": ("auto_fy2010", 292.216, "Net profit (adj.) 292,216 232,798"),
    "auto_da_2010_usd_mm": ("auto_fy2010", 99.610, "Depreciation and amortization 99,610 81,083"),
    "auto_da_2009_usd_mm": ("auto_fy2010", 81.083, "Depreciation and amortization 99,610 81,083"),
    "auto_diluted_shares_2010_mm": ("auto_fy2010", 244.473, "(IFRS) 244,473 240,555"),
    "auto_diluted_shares_2009_mm": ("auto_fy2010", 240.555, "(IFRS) 244,473 240,555"),
    "auto_fixed_asset_purchases_2010_usd_mm": ("auto_fy2010", 59.624, "Purchase of fixed assets (59,624) (34,429)"),
    "auto_product_development_2010_usd_mm": ("auto_fy2010", 38.542, "Expenditure on product (38,542) (24,722)"),
    "auto_receivables_movement_2010_usd_mm": ("auto_fy2010", -60.983, "Receivables (60,983) (78,396)"),
    "auto_inventories_movement_2010_usd_mm": ("auto_fy2010", 0.369, "Inventories 369 235"),
    "auto_payables_movement_2010_usd_mm": ("auto_fy2010", 7.718, "Payables 7,718 4,267"),
    "auto_bank_loan_current_2010_usd_mm": ("auto_fy2010", 78.745, "Bank loan (78,745) (52,375)"),
    "auto_bank_loan_noncurrent_2010_usd_mm": ("auto_fy2010", 66.407, "Bank loan (66,407) (145,152)"),
    "auto_convertible_notes_2010_usd_mm": ("auto_fy2010", 681.791, "Convertible loan notes (681,791)"),
    "auto_cash_2010_usd_mm": ("auto_fy2010", 1060.600, "Cash and cash equivalents 1,060,600 242,791"),
    "auto_tax_guidance_2011_low_pct": ("auto_fy2010", 0.27, "effective tax rate for 2011 will likely be in the range of 27-29%"),
    "auto_tax_guidance_2011_high_pct": ("auto_fy2010", 0.29, "effective tax rate for 2011 will likely be in the range of 27-29%"),
    # Autonomy FY2009 release (FY2008 column)
    "auto_rev_2008_usd_mm": ("auto_fy2009", 503.229, "Revenues (see note 3) 739,688 503,229"),
    "auto_cogs_2008_usd_mm": ("auto_fy2009", 64.527, "Total cost of revenues (137,397) (64,527)"),
    "auto_opex_2008_usd_mm": ("auto_fy2009", 252.209, "Total operating expenses (330,113) (252,209)"),
    "auto_ebit_2008_usd_mm": ("auto_fy2009", 186.493, "Profit from operations 272,178 186,493"),
    "auto_pbt_2008_usd_mm": ("auto_fy2009", 185.707, "Profit before income taxes 266,066 185,707"),
    "auto_tax_2008_usd_mm": ("auto_fy2009", 53.958, "Income taxes (see note 4) (74,515) (53,958)"),
    "auto_da_2008_usd_mm": ("auto_fy2009", 38.408, "Depreciation and amortization 81,083 38,408"),
    "auto_diluted_shares_2008_mm": ("auto_fy2009", 217.158, "of diluted earnings per share 240,555 217,158"),
    # Offer terms
    "offer_price_gbp": ("rule_2_5", 25.50, "Autonomy Shareholders will be entitled to receive £25.50 in cash per Autonomy Share"),
    "offer_price_usd": ("hp_8k_20110819", 42.11, "for £25.50 ($42.11) per share in cash"),
    "unaffected_close_gbp": ("rule_2_5", 15.58, "a premium of approximately 64 per cent to the Closing Price of £15.58 per Autonomy Share on 17 August 2011"),
    "disclosed_premium_pct": ("rule_2_5", 0.64, "a premium of approximately 64 per cent to the Closing Price of £15.58"),
    "premium_to_52_week_high_pct": ("rule_2_5", 0.36, "a premium of approximately 36 per cent to the fifty-two week high price of an Autonomy Share of £18.81"),
    "shares_in_issue_mm": ("rule_2_5", 243.469433, "based on there being 243,469,433 Autonomy Shares now in issue"),
    "fully_diluted_offer_value_gbp_mm": ("rule_2_5", 7091.0, "The Offer values Autonomy’s fully diluted share capital at approximately £7,091 million"),
    "eim_market_growth_pct": ("rule_2_5", 0.08, "$20 billion Enterprise Information Management space, which is growing at 8 per cent annually"),
    "cash_consideration_flag": ("rule_2_5", 0.0, "terms of a recommended cash offer for the entire issued and to be issued share capital of Autonomy"),
    "accretion_expectation_flag": ("rule_2_5", 0.0, "expect the acquisition to be accretive to Non-GAAP earnings per share for HP stockholders in the first full year following completion"),
    # HP FY2011 10-K
    "hp_net_earnings_fy2011_usd_mm": ("hp_q4fy11_release", 7074.0, "GAAP net earnings $ 7,074 $ 8,761"),
    "hp_nongaap_net_earnings_fy2011_usd_mm": ("hp_q4fy11_release", 10379.0, "Non-GAAP net earnings $ 10,379 $ 10,866"),
    "hp_diluted_shares_fy2011_mm": ("hp_q4fy11_release", 2128.0, "Weighted-average shares used to compute diluted EPS 2,128 2,372"),
    "hp_autonomy_consideration_usd_mm": ("hp_10k_fy2011", 11000.0, "The acquisition date fair value consideration of $11 billion consisted of cash"),
    "hp_weighted_average_interest_rate_fy2011_pct": ("hp_10k_fy2011", 0.024, "Weighted-average interest rate 2.4 %"),
    "hp_effective_tax_rate_fy2011_pct": ("hp_10k_fy2011", 0.212, "Our effective tax rates were 21.2%, 20.2% and 18.6% in fiscal 2011, 2010 and 2009"),
    "hp_sept2011_note_2015_usd_mm": ("hp_10k_fy2011", 750.0, "$750 issued at discount to par at a price of 99.977% in September 2011 at 2.35%, due March 2015"),
    "hp_sept2011_note_2016_usd_mm": ("hp_10k_fy2011", 1300.0, "$1,300 issued at discount to par at a price of 99.784% in September 2011 at 3.0% , due September 2016"),
    "hp_sept2011_note_2021_usd_mm": ("hp_10k_fy2011", 1000.0, "$1,000 issued at discount to par at a price of 99.816% in September 2011 at 4.375% due September 2021"),
    "hp_sept2011_note_2041_usd_mm": ("hp_10k_fy2011", 1200.0, "$1,200 issued at discount to par at a price of 99.863% in September 2011 at 6.0% due September 2041"),
    "hp_fiscal_year_end_flag": ("hp_10k_fy2011", 0.0, "For the fiscal year ended October 31, 2011"),
    # HP Q3 FY2012 10-Q
    "autonomy_goodwill_jul2012_usd_bn": ("hp_10q_q3fy12", 6.9, "$6.9 billion relates to the Autonomy acquisition"),
    "autonomy_headroom_at_acquisition_flag": ("hp_10q_q3fy12", 0.0, "At the time of the Autonomy acquisition in October 2011, the fair value of Autonomy approximated the carrying value"),
    "legacy_software_headroom_pct": ("hp_10q_q3fy12", 0.38, "the excess of fair value over carrying value of the legacy HP software business was 38% of the carrying value"),
    "software_license_growth_q3fy12_pct": ("hp_10q_q3fy12", 0.02, "net revenue from services, support and licenses increased by 65%, 16% and 2%"),
    # Damodaran (row label, column "Cost of Capital")
    "damodaran_software_wacc_jan2011_pct": ("damodaran_wacc_jan2011", 0.08137796024670886, "Computer Software/Svcs"),
    "damodaran_treasury_input_jan2011_pct": ("damodaran_wacc_jan2011", 0.0329, "Long Term Treasury bond rate ="),
    "damodaran_software_wacc_jan2012_pct": ("damodaran_wacc_jan2012", 0.07870902376552068, "Computer Software"),
    "damodaran_treasury_input_jan2012_pct": ("damodaran_wacc_jan2012", 0.0187, "Long Term Treasury bond rate ="),
    # Treasury 10-year par yields
    "ust10y_2010_12_31_pct": ("ust_2010", 0.0330, "12/31/2010,0.07,0.12,0.19,0.29,0.61,1.02,2.01,2.71,3.30"),
    "ust10y_2011_08_17_pct": ("ust_2011", 0.0217, "08/17/2011,0.01,0.01,0.06,0.12,0.19,0.33,0.92,1.48,2.17"),
    "ust10y_2011_12_30_pct": ("ust_2011", 0.0189, "12/30/2011,0.01,0.02,0.06,0.12,0.25,0.36,0.83,1.35,1.89"),
    "ust10y_2012_10_31_pct": ("ust_2012", 0.0172, "10/31/2012,0.09,0.11,0.16,0.18,0.30,0.38,0.72,1.14,1.72"),
}


def v(key: str) -> float:
    return OBS[key][1]


def src(key: str) -> dict[str, Any]:
    return SOURCES[key]


def r6(x: float) -> float:
    return round(x, 6)


# --------------------------------------------------------------------------
# Derivations. Every number written to the workbook is computed here from
# OBS, and the arithmetic is restated in the manifest note beside it.
# --------------------------------------------------------------------------
def derive() -> dict[str, float]:
    d: dict[str, float] = {}
    # Net non-operating charge = profit from operations - profit before tax.
    # The template's forward identity is pre-tax = EBIT - "interest expense",
    # so this row carries interest payable net of interest receivable, the
    # share of associate result and disposal gains, which makes pre-tax and
    # net income tie to the release exactly.
    for y in (2008, 2009, 2010):
        d[f"nonop_{y}"] = r6(v(f"auto_ebit_{y}_usd_mm") - v(f"auto_pbt_{y}_usd_mm"))
        assert abs(v(f"auto_rev_{y}_usd_mm") - v(f"auto_cogs_{y}_usd_mm") - v(f"auto_opex_{y}_usd_mm")
                   - v(f"auto_ebit_{y}_usd_mm")) < 0.0015, y
    rev10, rev09 = v("auto_rev_2010_usd_mm"), v("auto_rev_2009_usd_mm")
    d["growth_2010"] = rev10 / rev09 - 1
    d["gross_margin_2010"] = (rev10 - v("auto_cogs_2010_usd_mm")) / rev10
    d["opex_pct_2010"] = v("auto_opex_2010_usd_mm") / rev10
    d["tax_rate_2011_guidance"] = (v("auto_tax_guidance_2011_low_pct") + v("auto_tax_guidance_2011_high_pct")) / 2
    d["capex_2010"] = v("auto_fixed_asset_purchases_2010_usd_mm") + v("auto_product_development_2010_usd_mm")
    d["capex_pct_2010"] = d["capex_2010"] / rev10
    d["da_pct_capex_2010"] = v("auto_da_2010_usd_mm") / d["capex_2010"]
    d["nwc_increase_2010"] = -(v("auto_receivables_movement_2010_usd_mm") + v("auto_inventories_movement_2010_usd_mm")
                               + v("auto_payables_movement_2010_usd_mm"))
    d["nwc_pct_rev_chg_2010"] = d["nwc_increase_2010"] / (rev10 - rev09)
    d["growth_path"] = [d["growth_2010"] + (v("eim_market_growth_pct") - d["growth_2010"]) * i / 4 for i in range(5)]
    d["debt_2010"] = (v("auto_bank_loan_current_2010_usd_mm") + v("auto_bank_loan_noncurrent_2010_usd_mm")
                      + v("auto_convertible_notes_2010_usd_mm"))
    d["cash_2010"] = v("auto_cash_2010_usd_mm")
    d["net_debt_2010"] = d["debt_2010"] - d["cash_2010"]
    d["fx_usd_per_gbp"] = v("offer_price_usd") / v("offer_price_gbp")
    d["unaffected_price_usd"] = v("unaffected_close_gbp") * d["fx_usd_per_gbp"]
    d["unaffected_equity_usd_mm"] = d["unaffected_price_usd"] * v("shares_in_issue_mm")
    d["unaffected_ev_usd_mm"] = d["unaffected_equity_usd_mm"] + d["debt_2010"] - d["cash_2010"]
    # Forward unlevered FCF, the DCF sheet's own identity:
    #   UFCF = EBIT * (1 - tax) + D&A - capex,   D&A = revenue * capex% * D&A/capex
    rev = rev10
    path = []
    for g in d["growth_path"]:
        rev = rev * (1 + g)
        ebit = rev * d["gross_margin_2010"] - rev * d["opex_pct_2010"]
        da = rev * d["capex_pct_2010"] * d["da_pct_capex_2010"]
        path.append(ebit * (1 - d["tax_rate_2011_guidance"]) + da - rev * d["capex_pct_2010"])
    d["ufcf_base_path"] = path
    d["tax_rate_2010"] = v("auto_tax_2010_usd_mm") / v("auto_pbt_2010_usd_mm")
    d["ufcf_2010_actual"] = (v("auto_ebit_2010_usd_mm") * (1 - d["tax_rate_2010"])
                             + v("auto_da_2010_usd_mm") - d["capex_2010"])
    # Financing cost of the $11bn consideration, after tax at HP's FY2011 rate.
    t = v("hp_effective_tax_rate_fy2011_pct")
    d["fin_cost_avg_rate"] = v("hp_autonomy_consideration_usd_mm") * v("hp_weighted_average_interest_rate_fy2011_pct") * (1 - t)
    notes = [("hp_sept2011_note_2015_usd_mm", 0.0235), ("hp_sept2011_note_2016_usd_mm", 0.030),
             ("hp_sept2011_note_2021_usd_mm", 0.04375), ("hp_sept2011_note_2041_usd_mm", 0.060)]
    d["sept2011_fixed_coupon"] = sum(v(k) * c for k, c in notes) / sum(v(k) for k, _ in notes)
    d["fin_cost_marginal"] = v("hp_autonomy_consideration_usd_mm") * d["sept2011_fixed_coupon"] * (1 - t)
    return d


def peer_rows() -> list[dict[str, Any]]:
    rows = []
    for p in PEERS:
        price = p["yahoo_close"] * p["split_factor"]
        shares_mm = p["shares"][3] / 1e6
        mcap = price * shares_mm
        debt = sum(x[3] for x in p["debt"]) / 1e6
        cash = sum(x[3] for x in p["cash"]) / 1e6
        ev = mcap + debt - cash
        revenue = p["revenue"][3] / 1e6
        ebitda = (sum(x[3] for x in p["ebit_parts"]) + sum(x[3] for x in p["da_parts"])) / 1e6
        rows.append({
            "ticker": p["ticker"], "price": round(price, 4), "shares_mm": shares_mm,
            "mcap": round(mcap, 2), "debt": debt, "cash": cash, "ev": round(ev, 2),
            "revenue": revenue, "ebitda": ebitda,
            "ev_rev": round(ev / revenue, 4), "ev_ebitda": round(ev / ebitda, 4),
            "pe": round(price / p["eps"][3], 4),
        })
    return rows


# --------------------------------------------------------------------------
def source_ref(key: str, notes: str) -> dict[str, Any]:
    s = src(key)
    return {"name": s["name"], "url": s["url"], "as_of": s["published"], "notes": notes}


def inp(sheet: str, cell: str, value: Any, kind: str, key: str, notes: str) -> dict[str, Any]:
    return {"sheet": sheet, "cell": cell, "value": value, "input_kind": kind,
            "source": source_ref(key, notes), "emitted_by": EMITTED_BY}


def drv(sheet: str, cell: str, value: Any, driver_type: str, rationale: str,
        basis_key: str, basis_note: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """A driver: the input row writes the value, the declaration grounds it."""
    s = src(basis_key)
    item = {"sheet": sheet, "cell": cell, "value": value, "input_kind": "modeler_assumption",
            "source": source_ref(basis_key, rationale), "emitted_by": EMITTED_BY}
    decl = {"sheet": sheet, "cell": cell, "driver_type": driver_type, "rationale": rationale,
            "basis": {"source_name": s["name"], "source_url": s["url"], "as_of": s["published"],
                      "note": basis_note},
            "emitted_by": EMITTED_BY}
    return item, decl


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    for key, meta in SOURCES.items():
        if not meta.get("outcome_only"):
            assert meta["published"] <= AS_OF, f"hindsight: {key} published {meta['published']}"
    d = derive()
    peers = peer_rows()
    inputs: list[dict[str, Any]] = []
    decls: list[dict[str, Any]] = []
    fills: list[dict[str, Any]] = []

    def add(item: dict[str, Any]) -> None:
        inputs.append(item)

    def add_drv(pair: tuple[dict[str, Any], dict[str, Any]]) -> None:
        inputs.append(pair[0])
        decls.append(pair[1])

    A = "Autonomy (IFRS, reported in US dollars; $'000 converted to $mm)"
    # ---------------- IS: Autonomy FY2008 (C), FY2009 (D), FY2010 (E) ----
    for col, y, key in (("C", 2008, "auto_fy2009"), ("D", 2009, "auto_fy2010"), ("E", 2010, "auto_fy2010")):
        add(inp("IS", f"{col}5", v(f"auto_rev_{y}_usd_mm"), "observed", key, f"{A} FY{y} revenues."))
        add(inp("IS", f"{col}7", v(f"auto_cogs_{y}_usd_mm"), "observed", key,
                f"{A} FY{y} total cost of revenues, including amortization of purchased intangibles."))
        add(inp("IS", f"{col}10", v(f"auto_opex_{y}_usd_mm"), "observed", key,
                f"{A} FY{y} total operating expenses. Revenue - COGS - opex reproduces reported profit from operations of {v(f'auto_ebit_{y}_usd_mm'):.3f}."))
        add(inp("IS", f"{col}13", v(f"auto_da_{y}_usd_mm"), "observed", key,
                f"{A} FY{y} depreciation and amortization from the cash flow statement."))
        add(inp("IS", f"{col}15", d[f"nonop_{y}"], "derived", key,
                f"Net non-operating charge = profit from operations {v(f'auto_ebit_{y}_usd_mm'):.3f} - profit before income taxes "
                f"{v(f'auto_pbt_{y}_usd_mm'):.3f} = {d[f'nonop_{y}']:.3f}. It nets interest payable against interest receivable, "
                "the share of associate result and disposal gains, because the template has one row between EBIT and pre-tax income."))
        add(inp("IS", f"{col}17", v(f"auto_tax_{y}_usd_mm"), "observed", key, f"{A} FY{y} income taxes."))
        add(inp("IS", f"{col}19", v(f"auto_diluted_shares_{y}_mm"), "observed", key,
                f"FY{y} weighted average ordinary shares for diluted EPS (IFRS), millions."))

    # ---------------- Assumptions: FY1..FY5 = 2011..2015 -----------------
    cols = "CDEFG"
    g0, g5 = d["growth_2010"], v("eim_market_growth_pct")
    for i, c in enumerate(cols):
        add(inp("Assumptions", f"{c}5", r6(d["growth_path"][i]), "derived", "rule_2_5",
                f"Revenue growth fades linearly from Autonomy's FY2010 reported growth ({v('auto_rev_2010_usd_mm')}/{v('auto_rev_2009_usd_mm')} - 1 = {g0:.6f}, "
                f"FY2010 release) in FY1 to the 8% annual growth HP's Rule 2.5 announcement gives for the Enterprise Information Management market in FY5. "
                "Both endpoints are disclosed; only the straight-line shape between them is a modeling choice."))
        add(inp("Assumptions", f"{c}6", r6(d["gross_margin_2010"]), "derived", "auto_fy2010",
                f"Gross margin = (870.366 - 168.793) / 870.366 = {d['gross_margin_2010']:.6f}, FY2010, held flat."))
        add(inp("Assumptions", f"{c}7", r6(d["opex_pct_2010"]), "derived", "auto_fy2010",
                f"Opex / revenue = 385.158 / 870.366 = {d['opex_pct_2010']:.6f}, FY2010, held flat."))
        add(inp("Assumptions", f"{c}8", r6(d["tax_rate_2011_guidance"]), "derived", "auto_fy2010",
                "Tax rate = midpoint of Autonomy's disclosed 2011 effective tax rate guidance of 27-29% = 0.28. "
                "The FY2010 rate of 23% included a one-off use of tax losses the company said would not repeat."))
        add(inp("Assumptions", f"{c}9", r6(d["da_pct_capex_2010"]), "derived", "auto_fy2010",
                f"D&A / capex = 99.610 / (59.624 purchase of fixed assets + 38.542 expenditure on product development) = {d['da_pct_capex_2010']:.6f}, FY2010, held flat."))
        add(inp("Assumptions", f"{c}10", r6(d["capex_pct_2010"]), "derived", "auto_fy2010",
                f"Capex / revenue = 98.166 / 870.366 = {d['capex_pct_2010']:.6f}, FY2010, held flat. Capex counts capitalized product development as well as fixed assets."))
        add(inp("Assumptions", f"{c}11", r6(d["nwc_pct_rev_chg_2010"]), "derived", "auto_fy2010",
                f"Increase in operating working capital per dollar of revenue increase, FY2010: -(receivables -60.983 + inventories 0.369 + payables 7.718) "
                f"= 52.896 over revenue change 130.678 = {d['nwc_pct_rev_chg_2010']:.6f}. Positive means working capital grows with revenue."))
        add(inp("Assumptions", f"{c}12", v("auto_diluted_shares_2010_mm"), "observed", "auto_fy2010",
                "FY2010 IFRS diluted weighted average shares, 244.473mm, held flat."))
        add_drv(drv("Assumptions", f"{c}13", r6(v("damodaran_software_wacc_jan2012_pct")), "undisclosed_metric_driver",
                    "WACC. Autonomy's own cost of capital is not disclosed. Set to Damodaran's January 2012 cost of capital for the "
                    "Computer Software industry (191 US firms), 7.8709%, the latest release published before the case date.",
                    "damodaran_wacc_jan2012",
                    "wacc11.xls, row 'Computer Software', column 'Cost of Capital' = 0.078709. The file's Treasury input of 1.87% matches the "
                    "10-year par yield of 1.89% on 2011-12-30, which dates it to the January 2012 release."))
        add_drv(drv("Assumptions", f"{c}14", r6(v("ust10y_2012_10_31_pct")), "undisclosed_metric_driver",
                    "Terminal growth. Set to the 10-year Treasury par yield on the case date, 1.72%, under the convention that a perpetual "
                    "growth rate should not exceed the risk-free rate.",
                    "ust_2012", "10 Yr column, 10/31/2012 = 1.72."))

    # Column H of Assumptions is the template's "Source / notes" column. Its
    # default text is a bracketed placeholder; each row gets the citation for
    # the drivers written to that row above. Text only, no new number.
    notes_h = {
        5: "Source: Autonomy FY2010 results release (revenue growth FY2010 = 870.366/739.688 - 1) fading linearly to the 8% EIM market growth in HP's Rule 2.5 announcement, 2011-08-18.",
        6: "Source: Autonomy FY2010 results release, gross margin = (870.366 - 168.793)/870.366, held flat.",
        7: "Source: Autonomy FY2010 results release, total operating expenses 385.158 / revenue 870.366, held flat.",
        8: "Source: Autonomy FY2010 results release, 2011 effective tax rate guidance 27-29%, midpoint 28%.",
        9: "Source: Autonomy FY2010 results release, D&A 99.610 / (fixed assets 59.624 + product development 38.542), held flat.",
        10: "Source: Autonomy FY2010 results release, capex (fixed assets + capitalized product development) 98.166 / revenue 870.366, held flat.",
        11: "Source: Autonomy FY2010 results release, operating working capital increase 52.896 / revenue increase 130.678.",
        12: "Source: Autonomy FY2010 results release, IFRS diluted weighted average shares 244.473mm, held flat.",
        13: "Driver: Damodaran Online, January 2012 cost of capital, Computer Software (wacc11.xls) = 7.8709%. Autonomy's own WACC is not disclosed.",
        14: "Driver: U.S. Treasury 10-year par yield on 2012-10-31 = 1.72%, as a ceiling for perpetual growth.",
    }
    for row, text in notes_h.items():
        fills.append({"sheet": "Assumptions", "cell": f"H{row}", "value": text, "purpose": "source_note",
                      "source": source_ref("auto_fy2010" if row < 13 else ("damodaran_wacc_jan2012" if row == 13 else "ust_2012"),
                                           "Citation text for the drivers in this row; restates the source and arithmetic "
                                           "recorded on the row's inputs. No new number."),
                      "emitted_by": EMITTED_BY})

    # ---------------- DCF -------------------------------------------------
    add_drv(drv("DCF", "I5", r6(v("damodaran_software_wacc_jan2012_pct")), "undisclosed_metric_driver",
                "WACC. Damodaran January 2012 Computer Software cost of capital, 7.8709% (see Assumptions row 13).",
                "damodaran_wacc_jan2012", "wacc11.xls, row 'Computer Software', column 'Cost of Capital'."))
    add_drv(drv("DCF", "I6", r6(v("ust10y_2012_10_31_pct")), "undisclosed_metric_driver",
                "Terminal growth. 10-year Treasury par yield on 2012-10-31, 1.72% (see Assumptions row 14).",
                "ust_2012", "10 Yr column, 10/31/2012 = 1.72."))
    add(inp("DCF", "I11", r6(d["net_debt_2010"]), "derived", "auto_fy2010",
            f"Net debt at 2010-12-31 = bank loans 78.745 + 66.407 + convertible loan notes 681.791 - cash 1,060.600 = {d['net_debt_2010']:.3f} "
            "(net cash). Autonomy's last published balance sheet with a full debt breakdown before the offer."))
    add(inp("DCF", "I13", v("auto_diluted_shares_2010_mm"), "observed", "auto_fy2010",
            "FY2010 IFRS diluted weighted average shares, 244.473mm."))

    # ---------------- Sensitivity ---------------------------------------
    # The template leaves the WACC x terminal-growth grid as bracketed text
    # standing in for an Excel data table, which openpyxl and LibreOffice
    # cannot evaluate. Each cell becomes a live formula: the DCF sheet's own
    # arithmetic with the two rates replaced by the grid axes (the axis values
    # are the template's). These are presentation fills, not inputs: they
    # earn no coverage credit and recompute whenever the inputs change.
    for r in range(5, 10):
        for c in "CDEFG":
            formula = (f'=IF(OR(IS!$E$5="",IS!$E$5=0),"n/a - no forecast base",'
                       f"(NPV($B{r},DCF!$C$5:$G$5)+DCF!$G$5*(1+{c}$4)/($B{r}-{c}$4)/(1+$B{r})^5"
                       f"-DCF!$I$11)/DCF!$I$13)")
            fills.append({"sheet": "Sensitivity", "cell": f"{c}{r}", "value": formula, "purpose": "formula_grid",
                          "source": source_ref("auto_fy2010",
                              "Implied value per share at WACC in column B and terminal growth in row 4: the DCF "
                              "sheet's own arithmetic (end-of-year discounting of DCF!C5:G5, Gordon terminal value "
                              "on DCF!G5, less net debt DCF!I11, over diluted shares DCF!I13) with the two rates "
                              "replaced. At the case's base rates it reproduces DCF!I14."),
                          "emitted_by": EMITTED_BY})

    # ---------------- Comps ----------------------------------------------
    for row, (p, r) in enumerate(zip(PEERS, peers), start=5):
        filings = (f"Shares {p['shares'][0]} ({p['shares'][1]}, {p['shares'][2]}); debt "
                   + (" + ".join(f"{x[0]} {x[3]/1e6:,.1f}" for x in p["debt"]) or "none reported")
                   + f"; cash " + " + ".join(f"{x[0]} {x[3]/1e6:,.1f}" for x in p["cash"])
                   + f" (balance sheet {p['cash'][0][1]}, {p['cash'][0][2]}); revenue {p['revenue'][0]} {r['revenue']:,.1f}, "
                   + "EBITDA = " + " + ".join(f"{x[0]} {x[3]/1e6:,.1f}" for x in p["ebit_parts"] + p["da_parts"])
                   + f" = {r['ebitda']:,.1f}; diluted EPS {p['eps'][3]} (10-K {p['revenue'][1]}, fiscal year ended {p['revenue'][2]}).")
        xbrl_src = {"name": f"{p['name']} SEC XBRL company facts (CIK {p['cik']})",
                    "url": XBRL.format(cik=p["cik"]), "as_of": AS_OF}
        price_src = {"name": f"Yahoo Finance daily chart, {p['ticker']}, close on 2012-10-31",
                     "url": YAHOO.format(t=p["ticker"]), "as_of": AS_OF}

        def cinp(cell: str, value: Any, kind: str, s: dict[str, Any], note: str) -> None:
            inputs.append({"sheet": "Comps", "cell": cell, "value": value, "input_kind": kind,
                           "source": {**s, "notes": note}, "emitted_by": EMITTED_BY})

        cinp(f"B{row}", p["ticker"], "observed", xbrl_src,
             f"{p['name']}. Peer selected for Autonomy's two markets as named in HP's Rule 2.5 announcement (enterprise information management, business analytics).")
        cinp(f"C{row}", r["price"], "observed", price_src,
             f"Close on 2012-10-31 = {p['yahoo_close']:.4f} as served x {p['split_factor']} ({p['split_note']}) = {r['price']:.4f} USD.")
        cinp(f"D{row}", r["mcap"], "derived", xbrl_src,
             f"Market cap $mm = price {r['price']:.4f} x shares {r['shares_mm']:,.6f}mm = {r['mcap']:,.2f}. {filings}")
        cinp(f"E{row}", r["ev"], "derived", xbrl_src,
             f"EV $mm = market cap {r['mcap']:,.2f} + debt {r['debt']:,.1f} - cash and short-term investments {r['cash']:,.1f} = {r['ev']:,.2f}.")
        cinp(f"F{row}", r["ev_rev"], "derived", xbrl_src,
             f"EV / last-fiscal-year revenue = {r['ev']:,.2f} / {r['revenue']:,.1f} = {r['ev_rev']:.4f}x.")
        cinp(f"G{row}", r["ev_ebitda"], "derived", xbrl_src,
             f"EV / last-fiscal-year EBITDA = {r['ev']:,.2f} / {r['ebitda']:,.1f} = {r['ev_ebitda']:.4f}x.")
        cinp(f"H{row}", r["pe"], "derived", xbrl_src,
             f"P/E = price {r['price']:.4f} / last-fiscal-year diluted EPS {p['eps'][3]} = {r['pe']:.4f}x.")

    # ---------------- Transaction Analysis -------------------------------
    TA = "Transaction Analysis"
    bridge_note = ("Debt, cash and share basis are the same in both columns: the offer terms did not change between signing "
                   "and the case date; only the valuation view does.")
    for col in "CD":
        add(inp(TA, f"{col}5", r6(d["unaffected_ev_usd_mm"]), "derived", "rule_2_5",
                f"Unaffected enterprise value $mm = unaffected close £15.58 (17 Aug 2011) x {d['fx_usd_per_gbp']:.6f} USD/GBP x 243.469433mm shares "
                f"= {d['unaffected_equity_usd_mm']:.3f}, + debt {d['debt_2010']:.3f} - cash {d['cash_2010']:.3f} = {d['unaffected_ev_usd_mm']:.3f}. "
                "USD/GBP = $42.11 / £25.50, the rate implied by HP's own 8-K statement of the offer price. " + bridge_note))
        add(inp(TA, f"{col}6", r6(d["debt_2010"]), "derived", "auto_fy2010",
                "Debt at 2010-12-31 = bank loan current 78.745 + bank loan non-current 66.407 + convertible loan notes 681.791 = 826.943 $mm."))
        add(inp(TA, f"{col}7", d["cash_2010"], "observed", "auto_fy2010", "Cash and cash equivalents at 2010-12-31, 1,060.600 $mm."))
        add(inp(TA, f"{col}8", v("shares_in_issue_mm"), "observed", "rule_2_5",
                "Autonomy shares in issue at the offer, 243,469,433 (Rule 2.5 bases of calculation), millions."))
        add(inp(TA, f"{col}9", v("offer_price_usd"), "observed", "hp_8k_20110819",
                "Offer price £25.50 ($42.11) per share in cash, per HP's Form 8-K Item 1.01. Offer premium to the unaffected close "
                "computes to 63.7%, matching the 'approximately 64 per cent' in the Rule 2.5 announcement."))
    add_drv(drv(TA, "C10", r6(v("damodaran_software_wacc_jan2011_pct")), "undisclosed_metric_driver",
                "Discount rate at signing. Damodaran January 2011 cost of capital for Computer Software/Svcs, 8.1378%, the release "
                "current on 18 August 2011.",
                "damodaran_wacc_jan2011",
                "wacc10.xls, row 'Computer Software/Svcs', column 'Cost of Capital' = 0.081378. Treasury input 3.29% matches the "
                "10-year par yield of 3.30% on 2010-12-31."))
    add_drv(drv(TA, "D10", r6(v("damodaran_software_wacc_jan2012_pct")), "undisclosed_metric_driver",
                "Discount rate at the case date. Damodaran January 2012 Computer Software cost of capital, 7.8709%.",
                "damodaran_wacc_jan2012", "wacc11.xls, row 'Computer Software', column 'Cost of Capital' = 0.078709."))
    add_drv(drv(TA, "C11", r6(v("ust10y_2011_08_17_pct")), "undisclosed_metric_driver",
                "Terminal growth at signing = 10-year Treasury par yield on 2011-08-17, the last business day before the offer, 2.17%.",
                "ust_2011", "10 Yr column, 08/17/2011 = 2.17."))
    add_drv(drv(TA, "D11", 0.0, "scenario_lever",
                "No-growth stress. HP's 10-Q for the quarter to 2012-07-31 reports Software licence revenue up only 2% year on year "
                "although the current period includes Autonomy, acquired in October 2011, and the prior period does not. On the "
                "public record at the case date, the combined licence base was not growing, so the stress sets perpetual growth to zero.",
                "hp_10q_q3fy12", "'net revenue from services, support and licenses increased by 65%, 16% and 2%' (three months ended 2012-07-31)."))
    for i, c in enumerate(range(12, 17)):
        add(inp(TA, f"C{c}", r6(d["ufcf_base_path"][i]), "derived", "auto_fy2010",
                f"Unlevered FCF year {i + 1} ($mm) on Autonomy's as-reported path: revenue grown by Assumptions row 5 from FY2010's 870.366; "
                "EBIT = revenue x (gross margin 0.806067 - opex 0.442525); UFCF = EBIT x (1 - 0.28) + revenue x capex 0.112787 x D&A/capex 1.014710 "
                f"- revenue x 0.112787 = {d['ufcf_base_path'][i]:.3f}. Same identity as the DCF sheet."))
        add(inp(TA, f"D{c}", r6(d["ufcf_2010_actual"]), "derived", "auto_fy2010",
                f"No-growth stress: FY2010 reported unlevered FCF held flat. EBIT 316.415 x (1 - FY2010 tax rate 64.901/282.194 = {d['tax_rate_2010']:.6f}) "
                f"+ D&A 99.610 - capex 98.166 = {d['ufcf_2010_actual']:.3f} $mm."))
    for col in "CD":
        add_drv(drv(TA, f"{col}17", v("premium_to_52_week_high_pct"), "scenario_lever",
                    "Maximum offer-premium screen, set at the 36% premium the Rule 2.5 announcement reports over Autonomy's 52-week high "
                    "of £18.81. A premium to the unaffected price above that level pays more than any price the market set in the prior year "
                    "by a wider margin than the offer itself claimed.",
                    "rule_2_5", "'a premium of approximately 36 per cent to the fifty-two week high price of an Autonomy Share of £18.81'."))
        add_drv(drv(TA, f"{col}18", v("legacy_software_headroom_pct"), "scenario_lever",
                    "Maximum DCF-to-bridge dispersion screen, set at 38%, the thinnest impairment-test headroom HP disclosed for a software "
                    "reporting unit (legacy HP software, fair value over carrying value at the 2011-08-01 test). A gap wider than that "
                    "between intrinsic and bridge value is large enough to matter in HP's own impairment framework.",
                    "hp_10q_q3fy12", "'the excess of fair value over carrying value of the legacy HP software business was 38% of the carrying value'."))

    # ---------------- Accretion Dilution ---------------------------------
    AD = "Accretion Dilution"
    add(inp(AD, "C5", v("hp_nongaap_net_earnings_fy2011_usd_mm"), "observed", "hp_q4fy11_release",
            "HP fiscal 2011 non-GAAP net earnings, $10,379mm. Base is HP's own framing: the Rule 2.5 announcement promised accretion to non-GAAP EPS."))
    add(inp(AD, "D5", v("hp_net_earnings_fy2011_usd_mm"), "observed", "hp_q4fy11_release",
            "HP fiscal 2011 GAAP net earnings, $7,074mm (also in the FY2011 10-K). Adversarial uses GAAP."))
    for col in "CD":
        add(inp(AD, f"{col}6", v("hp_diluted_shares_fy2011_mm"), "observed", "hp_q4fy11_release",
                "HP fiscal 2011 weighted-average shares used to compute diluted EPS, 2,128mm. Replaces an earlier 2,131 back-solved from rounded EPS."))
    add(inp(AD, "C7", v("auto_adj_net_profit_2010_usd_mm"), "observed", "auto_fy2010",
            "Autonomy FY2010 net profit (adj.), $292.216mm: the company's non-IFRS measure, matched to HP's non-GAAP basis. Replaces adjusted "
            "profit before tax (379), which was a pre-tax figure in an after-tax row."))
    add(inp(AD, "D7", v("auto_net_profit_2010_usd_mm"), "observed", "auto_fy2010", "Autonomy FY2010 IFRS net profit, $217.293mm."))
    for col in "CD":
        add_drv(drv(AD, f"{col}8", 0.0, "undisclosed_metric_driver",
                    "After-tax synergies set to zero. The Rule 2.5 announcement describes the deal as synergistic but contains no quantified "
                    "financial benefits statement, and no later HP filing before the case date quantifies one.",
                    "rule_2_5", "Synergies are described qualitatively only; no figure is stated."))
    t = v("hp_effective_tax_rate_fy2011_pct")
    add(inp(AD, "C9", r6(d["fin_cost_avg_rate"]), "derived", "hp_10k_fy2011",
            f"After-tax financing cost $mm = consideration 11,000 x HP's FY2011 weighted-average interest rate 2.4% x (1 - FY2011 effective tax rate {t}) "
            f"= {d['fin_cost_avg_rate']:.3f}. HP said it funded the offer from existing cash and debt; the average rate prices the mix."))
    add(inp(AD, "D9", r6(d["fin_cost_marginal"]), "derived", "hp_10k_fy2011",
            f"After-tax financing cost at the marginal rate $mm = 11,000 x {d['sept2011_fixed_coupon']:.6f} x (1 - {t}) = {d['fin_cost_marginal']:.3f}. "
            "The rate is the face-weighted coupon of the four fixed-rate notes HP issued in September 2011, weeks before the offer settled "
            "(750 at 2.35%, 1,300 at 3.0%, 1,000 at 4.375%, 1,200 at 6.0%), before any swap."))
    for col in "CD":
        add(inp(AD, f"{col}10", 0.0, "observed", "rule_2_5",
                "All-cash offer: no HP shares issued. 'a recommended cash offer for the entire issued and to be issued share capital of Autonomy'."))
        add_drv(drv(AD, f"{col}11", 0.0, "scenario_lever",
                    "Minimum accretion = 0: HP's own stated test. The Rule 2.5 announcement says HP expects the acquisition to be accretive to "
                    "non-GAAP EPS in the first full year.",
                    "rule_2_5", "'expect the acquisition to be accretive to Non-GAAP earnings per share for HP stockholders in the first full year following completion'."))

    # ---------------- Cover ----------------------------------------------
    base_dcf, stress_dcf = ta_dcf(d)
    thesis = (
        f"HP paid $11.0bn in cash for Autonomy (£25.50 a share, a {v('offer_price_usd') / d['unaffected_price_usd'] - 1:.1%} premium to the unaffected "
        f"price) against FY2010 reported revenue of $870mm and IFRS net profit of $217mm. On Autonomy's own reported numbers, a DCF gives "
        f"${stress_dcf['per_share']:.2f} a share with no growth at the case-date cost of capital ({v('damodaran_software_wacc_jan2012_pct'):.2%}) "
        f"and ${base_dcf['per_share']:.2f} with FY2010 growth fading to the 8% market growth HP cited, at the signing-date cost of capital "
        f"({v('damodaran_software_wacc_jan2011_pct'):.2%}), against $42.11 paid; HP's 10-Q says Autonomy's fair value only approximated its "
        f"carrying value at acquisition."
    )
    add({"sheet": "Cover", "cell": "B11", "value": thesis, "input_kind": "derived",
         "source": source_ref("hp_10q_q3fy12",
                              "Thesis restates values computed in this workbook from the cited filings; no number in it is new. "
                              "Zero impairment headroom is from the 10-Q for the quarter ended 2012-07-31."),
         "emitted_by": EMITTED_BY})
    decls.append({"sheet": "Cover", "cell": "C6", "driver_type": "generated_metadata",
                  "rationale": "Last refreshed is written by tools/model_instances.py from the manifest's as_of, 2012-10-31: the last day of HP's fiscal 2012.",
                  "basis": {"source_name": src("hp_10k_fy2011")["name"], "source_url": src("hp_10k_fy2011")["url"],
                            "as_of": src("hp_10k_fy2011")["published"], "note": "HP's fiscal year ends October 31."},
                  "emitted_by": EMITTED_BY})
    decls.append({"sheet": "Cover", "cell": "B17", "driver_type": "presentation_convention",
                  "rationale": "Colour-legend label 'Blue text', styled as an input to demonstrate the convention it describes. Not a fact about the subject.",
                  "basis": {"source_name": "Repository input-cell styling convention",
                            "source_url": "repo://tools/builders/institutional_helpers.py",
                            "note": "input_cell() styles hardcoded inputs blue on yellow; the Cover legend displays that style."},
                  "emitted_by": EMITTED_BY})
    cover = {
        "Title:": "Hewlett-Packard Autonomy acquisition impairment",
        "Sector:": ("Enterprise infrastructure software. Target: Autonomy Corporation plc (LSE: AU.), acquired October 2011. "
                    "Acquirer: Hewlett-Packard Company (NYSE: HPQ), SEC SIC 3570 Computer & Office Equipment as recorded on EDGAR."),
        "Coverage started:": "2011-08-18, the date HP announced its recommended cash offer for Autonomy (Rule 2.5 announcement).",
        "Next earnings date:": ("HP fourth quarter fiscal 2012 results. No date had been announced in an SEC filing by 2012-10-31 "
                                "(HP's EDGAR filings between the 2012-09-10 Form 10-Q and the case date: one Form 8-K, 2012-10-03, "
                                "fiscal 2013 EPS outlook only); HP furnished its prior fourth-quarter results on Form 8-K on 2011-11-21."),
    }

    existing = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    used = sorted({k for k in SOURCES if not SOURCES[k].get("outcome_only")})
    sources = []
    for k in used:
        s = SOURCES[k]
        sources.append({"name": s["name"], "url": s["url"], "as_of": s["published"],
                        "notes": f"{s['publisher']}. Published {s['published']}, on or before the case date."})
    for p in PEERS:
        sources.append({"name": f"{p['name']} SEC XBRL company facts (CIK {p['cik']})", "url": XBRL.format(cik=p["cik"]),
                        "as_of": AS_OF, "notes": "Only facts from filings dated on or before 2012-10-31 are used; accession numbers are in the snapshot."})
    sources.append({"name": "Yahoo Finance daily chart API (closing prices on 2012-10-31, split events)",
                    "url": "https://query1.finance.yahoo.com/v8/finance/chart/", "as_of": AS_OF,
                    "notes": "Market data vendor; closes restated to the 2012 share basis with the split factors recorded in the snapshot."})
    s = SOURCES["hp_10k_fy2012_outcome"]
    sources.append({"name": s["name"], "url": s["url"], "as_of": "2012-10-31",
                    "notes": "Filed 2012-12-27, after the case date. Used only for the recorded outcome ($8.8bn impairment); no input cites it."})
    sources.append({"name": "Frozen source snapshot", "url": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}", "as_of": AS_OF,
                    "notes": "Immutable curated observation package with SHA-256 digest"})

    inputs.sort(key=lambda it: (it["sheet"], it["cell"][0], int(re.sub(r"\D", "", it["cell"]))))
    decls.sort(key=lambda it: (it["sheet"], it["cell"][0], int(re.sub(r"\D", "", it["cell"]))))
    fills.sort(key=lambda it: (it["sheet"], it["cell"][0], int(re.sub(r"\D", "", it["cell"]))))
    manifest = {
        **{k: existing[k] for k in ("schema_version", "id", "classification", "counts_toward_M4", "template", "output", "as_of", "scenario")},
        "cover": cover,
        "inputs": inputs,
        "driver_declarations": decls,
        "presentation_fills": fills,
        "outcome": existing["outcome"],
        "lineage": existing["lineage"],
        "sources": sources,
        "refresh": {
            "date": date.today().isoformat(),
            "trigger": "Depth pass: every template input sourced or declared against filings public on or before 2012-10-31",
            "source_snapshot": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
            "what_changed": (
                "Sourced Autonomy's FY2008-FY2010 income statement, a forward driver grid, the DCF bridge, a seven-company comps table, "
                "both columns of the transaction analysis and both columns of accretion/dilution. Removed three inputs that cited the FY2012 "
                "10-K, filed after the case date, including a post-impairment residual that sat in an FCF row. Policy screens, discount "
                "rates and terminal growth are declared drivers with named bases, not observations."
            ),
            "reviewer_notes": (
                "External historical case; human stakeholder approval remains pending. Autonomy's numbers are as reported before the "
                "acquisition and were later disputed by HP; using them is the point of the case. The accretion sheet has no row for "
                "amortization of the $4.6bn of acquired intangibles, so GAAP dilution is understated."
            ),
            "next_check": "On source revision, builder change, or annual review",
        },
        "base_year_reproduction": {
            "sheet": "IS",
            "exemptions": [
                {"row": 17, "line": "Tax", "reproduction_exemption": "forward_by_design",
                 "rationale": "The forward tax rate is Autonomy's disclosed 2011 guidance of 27-29% (midpoint 28%); FY2010's 23% included a one-off use of tax losses the company said would not repeat."},
                {"row": 18, "line": "Net income", "reproduction_exemption": "forward_by_design",
                 "rationale": "Net income is pre-tax less tax and inherits the guided tax rate on row 17."},
                {"row": 20, "line": "Diluted EPS", "reproduction_exemption": "forward_by_design",
                 "rationale": "EPS is net income over diluted shares and inherits the guided tax rate on row 17."},
            ],
        },
    }

    captured = {k: {"source": s_, "value": val, "excerpt": ex} for k, (s_, val, ex) in OBS.items()}
    snapshot = {
        "schema_version": "1.0",
        "model_id": "01",
        "domain": "Investment Banking",
        "case_id": CASE_ID,
        "case_type": "adversarial",
        "as_of": AS_OF,
        "capture_method": "curated_public_observation",
        "generated_by": EMITTED_BY,
        "sources": [
            {"id": k, "name": s_["name"], "url": s_["url"], "publisher": s_["publisher"], "published": s_["published"],
             "outcome_only": bool(s_.get("outcome_only"))}
            for k, s_ in SOURCES.items()
        ],
        "captured_values": captured,
        "outcome_source": {
            "name": SOURCES["hp_10k_fy2012_outcome"]["name"],
            "captured_values": {"autonomy_impairment_usd_mm": 8800.0},
            "note": "Filed 2012-12-27, after the case date; outcome only.",
        },
        "comparable_companies": [
            {**{k: p[k] for k in p if k not in ()}, "computed": r} for p, r in zip(PEERS, peers)
        ],
        "derivations": {k: (val if not isinstance(val, list) else [r6(x) for x in val]) for k, val in d.items()},
        "transaction_dcf_check": {"base": base_dcf, "stress": stress_dcf},
        "input_overrides": [
            {"sheet": it["sheet"], "cell": it["cell"], "value": it["value"], "kind": it["input_kind"],
             "source": it["source"]["name"]}
            for it in inputs
        ],
        "series": None,
        "outcome": existing["outcome"],
        "counts_toward_m4": False,
    }
    snapshot["snapshot_sha256"] = hashlib.sha256(canonical_bytes(snapshot)).hexdigest()
    return manifest, snapshot


def sens_flows(d: dict[str, float]) -> list[float]:
    """DCF sheet row 5, from the rounded Assumptions values the workbook holds."""
    gm, ox, t = r6(d["gross_margin_2010"]), r6(d["opex_pct_2010"]), r6(d["tax_rate_2011_guidance"])
    dac, cx = r6(d["da_pct_capex_2010"]), r6(d["capex_pct_2010"])
    growth = [r6(x) for x in d["growth_path"]]
    rev, flows = v("auto_rev_2010_usd_mm"), []
    for g in growth[:4]:
        rev = rev * (1 + g)
        ebit = rev - rev * (1 - gm) - rev * ox
        flows.append(ebit * (1 - t) + rev * cx * dac - rev * cx)
    flows.append(flows[-1] * (1 + growth[4]))
    return flows


def dcf_per_share(d: dict[str, float], wacc: float, g: float) -> float:
    flows = sens_flows(d)
    pv = sum(f / (1 + wacc) ** (i + 1) for i, f in enumerate(flows))
    tv = flows[-1] * (1 + g) / (wacc - g) / (1 + wacc) ** 5
    return (pv + tv - r6(d["net_debt_2010"])) / v("auto_diluted_shares_2010_mm")


def sensitivity_grid(d: dict[str, float]) -> dict[tuple[int, str], tuple[float, float, float]]:
    waccs = {5: 0.08, 6: 0.09, 7: 0.10, 8: 0.11, 9: 0.12}       # template Sensitivity!B5:B9
    growths = {"C": 0.015, "D": 0.02, "E": 0.025, "F": 0.03, "G": 0.035}  # template Sensitivity!C4:G4
    return {(r, c): (w, g, dcf_per_share(d, w, g)) for r, w in waccs.items() for c, g in growths.items()}


def ta_dcf(d: dict[str, float]) -> tuple[dict[str, float], dict[str, float]]:
    """Recompute the Transaction Analysis DCF per share for both columns (cross-check only)."""
    out = []
    for flows, r, g in ((d["ufcf_base_path"], v("damodaran_software_wacc_jan2011_pct"), v("ust10y_2011_08_17_pct")),
                        ([d["ufcf_2010_actual"]] * 5, v("damodaran_software_wacc_jan2012_pct"), 0.0)):
        pv = sum(f / (1 + r) ** (i + 1) for i, f in enumerate(flows))
        tv = flows[-1] * (1 + g) / (r - g)
        ev = pv + tv / (1 + r) ** 5
        eq = ev - d["debt_2010"] + d["cash_2010"]
        out.append({"enterprise_value_usd_mm": round(ev, 3), "equity_value_usd_mm": round(eq, 3),
                    "per_share": round(eq / v("shares_in_issue_mm"), 4)})
    return out[0], out[1]


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def write_source_register(snapshot: dict[str, Any]) -> None:
    rows = []
    for k, s in SOURCES.items():
        rows.append((CASE_ID, s["name"], s["publisher"], s["url"], s["published"],
                     str(SNAPSHOT_PATH.relative_to(ROOT)), snapshot["snapshot_sha256"],
                     "frozen" if not s.get("outcome_only") else "outcome_only"))
    for p in PEERS:
        rows.append((CASE_ID, f"{p['name']} SEC XBRL company facts (CIK {p['cik']})", "U.S. SEC EDGAR",
                     XBRL.format(cik=p["cik"]), AS_OF, str(SNAPSHOT_PATH.relative_to(ROOT)),
                     snapshot["snapshot_sha256"], "frozen"))
    header = "case_id,source_name,publisher,url,as_of,snapshot,snapshot_sha256,status"
    lines = REGISTER_PATH.read_text(encoding="utf-8").splitlines() if REGISTER_PATH.exists() else [header]
    lines = [line for line in lines if not line.startswith(f"{CASE_ID},")]
    for row in rows:
        lines.append(",".join(f'"{f}"' if ("," in str(f) or '"' in str(f)) else str(f) for f in row))
    REGISTER_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------
# Source verification: fetch each document and confirm every captured value.
# --------------------------------------------------------------------------
UA = "finance-segway research (set SEC_USER_AGENT)"


def _fetch(url: str, cache: Path | None) -> bytes:
    import os
    import urllib.request
    if cache is not None:
        name = hashlib.sha256(url.encode()).hexdigest()[:24]
        path = cache / name
        if path.exists():
            return path.read_bytes()
    headers = {"User-Agent": os.environ.get("SEC_USER_AGENT", UA) if "sec.gov" in url else "Mozilla/5.0"}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
        body = response.read()
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=True)
        (cache / name).write_bytes(body)
    return body


def _text(body: bytes) -> str:
    import html as html_lib
    text = re.sub(r"<[^>]+>", " ", body.decode("utf-8", "replace"))
    text = html_lib.unescape(text).replace("\xa0", " ").replace("|", " ")
    return re.sub(r"\s+", " ", text)


def verify_sources(cache: Path | None) -> int:
    failures = []
    texts: dict[str, str] = {}
    for key, (sid, value, excerpt) in OBS.items():
        s = SOURCES[sid]
        if s["kind"] == "xls":
            import xlrd
            body = _fetch(s["url"], cache)
            sheet = xlrd.open_workbook(file_contents=body).sheet_by_index(0)
            ok = False
            for r in range(sheet.nrows):
                row = sheet.row_values(r)
                if str(row[0]).strip() == excerpt:
                    cand = row[-1] if excerpt != "Long Term Treasury bond rate =" else row[3]
                    ok = abs(float(cand) - value) < 1e-9
                    break
            if not ok:
                failures.append(f"{key}: {excerpt!r} != {value} in {s['url']}")
            continue
        if sid not in texts:
            body = _fetch(s["url"], cache)
            texts[sid] = body.decode("utf-8", "replace") if s["kind"] == "csv" else _text(body)
        hay = texts[sid]
        if re.sub(r"\s+", " ", excerpt) not in hay:
            failures.append(f"{key}: excerpt not found in {s['url']}: {excerpt!r}")
    for p in PEERS:
        facts = json.loads(_fetch(XBRL.format(cik=p["cik"]), cache))
        pool = {**facts["facts"].get("us-gaap", {}), **{"dei:" + k: x for k, x in facts["facts"].get("dei", {}).items()}}
        checks = [p["shares"], p["revenue"], p["eps"], *p["debt"], *p["cash"], *p["ebit_parts"], *p["da_parts"]]
        for tag, accn, end, val in checks:
            if tag not in pool:
                url = p.get("shares_url") if "cover" in tag else p.get("da_url") if "cash flow" in tag else p.get("debt_url")
                excerpt = p.get("shares_excerpt") if "cover" in tag else p.get("da_excerpt") if "cash flow" in tag else p.get("debt_excerpt")
                if not url or excerpt not in _text(_fetch(url, cache)):
                    failures.append(f"{p['ticker']}: {tag} {val} not confirmed in filing text")
                continue
            hits = [x for u in pool[tag]["units"].values() for x in u
                    if x["accn"] == accn and x["end"] == end and abs(x["val"] - val) < 1e-6]
            if not hits:
                failures.append(f"{p['ticker']}: {tag} {accn} {end} {val} not in XBRL")
            elif any(x["filed"] > AS_OF for x in hits):
                failures.append(f"{p['ticker']}: {tag} {accn} filed after {AS_OF}")
        chart = json.loads(_fetch(YAHOO.format(t=p["ticker"]), cache))["chart"]["result"][0]
        closes = dict(zip(chart["timestamp"], chart["indicators"]["quote"][0]["close"]))
        oct31 = [c for t, c in closes.items() if date.fromtimestamp(t).isoformat() in ("2012-10-31",)]
        if not oct31 or abs(oct31[0] - p["yahoo_close"]) > 1e-6:
            failures.append(f"{p['ticker']}: 2012-10-31 close {oct31} != {p['yahoo_close']}")
    for line in failures:
        print("FAIL", line)
    print(f"checked {len(OBS)} captured values and {len(PEERS)} peers: {len(failures)} failure(s)")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--print-only", action="store_true")
    parser.add_argument("--verify-sources", action="store_true")
    parser.add_argument("--cache", type=Path, default=None)
    args = parser.parse_args()
    if args.verify_sources:
        return verify_sources(args.cache)
    manifest, snapshot = build()
    if args.print_only:
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        return 0
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_source_register(snapshot)
    from public_case_index import report_sync
    print(f"saved {MANIFEST_PATH.relative_to(ROOT)}")
    print(f"saved {SNAPSHOT_PATH.relative_to(ROOT)}  sha256={snapshot['snapshot_sha256'][:16]}...")
    print(f"saved {REGISTER_PATH.relative_to(ROOT)}")
    print(report_sync(CASE_ID, snapshot["snapshot_sha256"]))
    print(f"inputs={len(manifest['inputs'])} drivers={len(manifest['driver_declarations'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
