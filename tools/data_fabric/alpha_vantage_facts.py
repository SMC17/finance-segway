"""L2 data fabric: record Alpha Vantage MCP fundamentals as structured facts + provenance.

Alpha Vantage's fundamentals endpoints (COMPANY_OVERVIEW, INCOME_STATEMENT,
BALANCE_SHEET, CASH_FLOW, EARNINGS) are reachable only as MCP tool calls in
this repo's working environment -- this session's sandbox egress policy
blocks the raw SEC/EDGAR HTTP path that edgar_company_facts.py uses (a
proxy-level 403, confirmed via
`curl http://127.0.0.1:46715/__agentproxy/status`), but MCP connector calls
route through separate, already-authenticated infrastructure and are not
subject to that policy.

Because of that, this module cannot fetch data itself the way
edgar_company_facts.py does (no outbound HTTP call would reach Alpha
Vantage's API from inside a plain script here). It is a *recorder*, the same
shape as hvpe_public_facts.py and fca_open_data.py: an agent or maintainer
calls an Alpha Vantage MCP tool directly, then passes the already-fetched
rows to record_company_facts() here, which writes the same
structured-facts-JSON + source_register-CSV shape edgar_company_facts.py
produces, so downstream tooling doesn't need to care which of the two
fetched a given fact.

Field-name mapping: Alpha Vantage normalizes GAAP/IFRS statement line items
under its own names (e.g. "totalAssets", "totalShareholderEquity"), distinct
from SEC XBRL's raw us-gaap concept tags (e.g. "Assets",
"StockholdersEquity"). AV_TO_EDGAR_CONCEPT maps the common ones so a fact
recorded here carries the same concept name edgar_company_facts.py would use
for the same line item -- verified by a live cross-check against Ares
Capital's FY2025 10-K (Assets/Liabilities/StockholdersEquity/NetIncomeLoss
all matched to the dollar between the two sources).

That cross-check also surfaced a real discrepancy worth flagging rather than
silently reconciling: for ARCC FY2025, Alpha Vantage's "operatingCashflow"
was +$1,142M while SEC EDGAR's NetCashProvidedByUsedInOperatingActivities
concept was -$54M -- a business-development company's portfolio
purchases/sales can be classified as operating or investing activity
differently across data vendors. Cash-flow-statement facts for BDC/fund
entities are recorded with their AV field name preserved (not silently
mapped to the EDGAR concept) so this class of vendor disagreement stays
visible instead of being papered over.

Usage (from an agent session with Alpha Vantage MCP tools available):
    result = <call mcp__Alpha_Vantage_MCP_Server__BALANCE_SHEET symbol="ARCC">
    rows = extract_annual(result, "BALANCE_SHEET", fiscal_year="2025-12-31")
    record_company_facts("ARCC", "1287750", rows, statement="BALANCE_SHEET")
"""
from __future__ import annotations

import csv
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "tools" / "data_fabric" / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Balance-sheet and income-statement line items: safe to map 1:1 onto the
# same us-gaap concept name edgar_company_facts.py's DEFAULT_CONCEPTS uses,
# verified against a live ARCC cross-check (see module docstring).
AV_TO_EDGAR_CONCEPT: dict[str, str] = {
    "totalAssets": "Assets",
    "totalCurrentAssets": "AssetsCurrent",
    "totalLiabilities": "Liabilities",
    "totalCurrentLiabilities": "LiabilitiesCurrent",
    "totalShareholderEquity": "StockholdersEquity",
    "cashAndCashEquivalentsAtCarryingValue": "CashAndCashEquivalentsAtCarryingValue",
    "commonStockSharesOutstanding": "CommonStockSharesOutstanding",
    "totalRevenue": "Revenues",
    "netIncome": "NetIncomeLoss",
    "operatingIncome": "OperatingIncomeLoss",
    "grossProfit": "GrossProfit",
    "interestExpense": "InterestExpense",
    "incomeTaxExpense": "IncomeTaxExpenseBenefit",
    "ebitda": "EBITDA",  # not a us-gaap tag; AV-derived, kept distinct
}

# Cash-flow-statement fields are NOT mapped onto EDGAR concept names -- see
# the module docstring's ARCC discrepancy. Recorded with their AV field name
# so a reviewer can see which vendor's classification a figure came from.
CASH_FLOW_FIELDS = {
    "operatingCashflow",
    "cashflowFromInvestment",
    "cashflowFromFinancing",
    "capitalExpenditures",
    "dividendPayout",
    "depreciationDepletionAndAmortization",
}


def extract_annual(
    payload: dict[str, Any],
    statement: str,
    *,
    fiscal_year: str | None = None,
    fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Pull one annualReports entry's fields into the same
    {concept, value, end, filed, form, ...}-shaped rows edgar_company_facts.py
    emits, so both sources write through the same recorder shape.

    `payload` is the parsed JSON an Alpha Vantage BALANCE_SHEET /
    INCOME_STATEMENT / CASH_FLOW tool call returned. `fiscal_year` selects
    the annualReports entry by its fiscalDateEnding (defaults to the most
    recent). `fields` restricts which line items to keep (defaults to every
    field this module knows how to name).
    """
    reports = payload.get("annualReports", [])
    if not reports:
        raise ValueError(f"no annualReports in {statement} payload for {payload.get('symbol')}")
    if fiscal_year:
        report = next((r for r in reports if r.get("fiscalDateEnding") == fiscal_year), None)
        if report is None:
            raise ValueError(f"no annualReports entry for fiscalDateEnding={fiscal_year!r}")
    else:
        report = reports[0]

    known_fields = set(AV_TO_EDGAR_CONCEPT) | CASH_FLOW_FIELDS
    wanted = fields or [f for f in report if f in known_fields]

    rows = []
    for field in wanted:
        value = report.get(field)
        if value in (None, "None"):
            continue
        concept = AV_TO_EDGAR_CONCEPT.get(field, field)
        rows.append(
            {
                "concept": concept,
                "av_field": field,
                "value": float(value),
                "end": report.get("fiscalDateEnding"),
                "filed": None,  # Alpha Vantage does not report a filing date
                "form": "10-K" if statement != "OVERVIEW" else None,
                "fy": None,
                "fp": "FY",
                "frame": None,
            }
        )
    return rows


def record_company_facts(
    ticker: str,
    cik: str | None,
    rows: list[dict[str, Any]],
    *,
    statement: str,
    extra_meta: dict[str, Any] | None = None,
) -> tuple[Path, Path]:
    """Write a governed snapshot + source_register fragment for Alpha
    Vantage-sourced company facts, in the same shape
    edgar_company_facts.write_outputs() produces."""
    today = date.today().isoformat()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    facts_path = OUT_DIR / f"{ticker.upper()}_alphavantage_{statement.lower()}.json"
    reg_path = OUT_DIR / f"{ticker.upper()}_alphavantage_{statement.lower()}_source_register.csv"

    payload = {
        "ticker": ticker.upper(),
        "cik": str(cik).zfill(10) if cik else None,
        "statement": statement,
        "retrieved_utc": stamp,
        "facts": rows,
    }
    if extra_meta:
        payload["meta"] = extra_meta

    (OUT_DIR / f"{ticker.upper()}_alphavantage_{statement.lower()}_{stamp}.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    facts_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    try:
        snapshot_ref = str(facts_path.relative_to(ROOT))
    except ValueError:
        snapshot_ref = str(facts_path)

    with reg_path.open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "source_name",
            "document_or_dataset",
            "publication_date",
            "as_of_date",
            "retrieval_date",
            "unit_currency",
            "transformation",
            "workbook_destination",
            "license_or_restriction",
            "checksum_or_snapshot",
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(
                {
                    "source_name": "Alpha Vantage MCP (normalized GAAP/IFRS fundamentals)",
                    "document_or_dataset": f"{ticker.upper()} {row['concept']} (AV field: {row['av_field']})",
                    "publication_date": "",
                    "as_of_date": row.get("end") or "",
                    "retrieval_date": today,
                    "unit_currency": "USD",
                    "transformation": (
                        "Alpha Vantage normalized cash-flow-statement classification, "
                        "not cross-mapped to an SEC XBRL concept -- see module docstring"
                        if row["av_field"] in CASH_FLOW_FIELDS
                        else "Alpha Vantage normalized annual fact, mapped to equivalent SEC us-gaap concept name"
                    ),
                    "workbook_destination": "Assumptions / historicals (any domain covering a public issuer)",
                    "license_or_restriction": "Alpha Vantage API terms of use; underlying data derived from public SEC filings",
                    "checksum_or_snapshot": snapshot_ref,
                }
            )

    print(f"Wrote {facts_path}")
    print(f"Wrote {reg_path}")
    print(f"Recorded {len(rows)} facts for {ticker.upper()} ({statement})")
    return facts_path, reg_path
