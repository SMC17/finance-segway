"""Generate the KWEB public case: the adversarial pair to etf-public-qqq-2026.

The ETF template's Assumptions sheet carries a Base and a Downside column
(Cover!C9 selects which one is "Active"). etf-public-qqq-2026 populated only
Base, leaving Downside at illustrative template defaults -- the honest thing
for a "conventional" reference case. This case is the mirror image: it
populates only Downside with a real fund's real numbers, and leaves Base at
template defaults, because this case's entire point is to be the adversarial
half of the pair the model card already flags as a "thin-coverage gap"
(model_card.md: "a second (adversarial/stress) case is future work").

Every number here comes from two independently-sourced, recorded artifacts:
  - tools/data_fabric/out/KWEB_alphavantage_etf_profile.json /
    KWEB_alphavantage_global_quote.json (Alpha Vantage MCP, same source class
    the QQQ case already uses)
  - tools/data_fabric/out/KWEB_sec_ncsr_annual_report.json (the fund's own
    SEC-filed N-CSR annual shareholder report, accession 0001829126-26-006162)

The two sources cross-validate each other: holdings count (32 real equity
positions) and top-position weights agree closely between them (see the
N-CSR file's "notes" field for the exact comparison). Sector weights are NOT
available from the Alpha Vantage ETF_PROFILE call for this fund (unlike
QQQ) -- they are sourced from the N-CSR instead, which discloses them
directly.

The realized adversarial outcome is the fund's own disclosed 5-year average
annual total return (-15.07% net, through 2026-03-31): a real, filed,
audited number, not a peak-to-trough price computation. The free Alpha
Vantage tier's TIME_SERIES_DAILY only serves ~100 days of history (full
history is a paid-tier feature this repo does not use), so a price-based
drawdown was not available; the fund's own SEC-filed total-return figure is
if anything a more decision-relevant metric than a raw price drawdown, since
it is what the fund itself is required to disclose to a holding investor.

Usage:
    python tools/build_etf_kweb_case.py
    python tools/build_etf_kweb_case.py --print-only
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

try:
    from tools.public_case_index import report_sync
except ModuleNotFoundError:  # invoked with tools/ directly on sys.path
    from public_case_index import report_sync
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "tools" / "data_fabric" / "out"
DOMAIN_DIR = ROOT / "30_ETF_Construction_Management"
MANIFEST_PATH = ROOT / "standards" / "public_cases" / "etf-public-kweb-2026-stress.json"
SNAPSHOT_PATH = DOMAIN_DIR / "sources" / "snapshots" / "etf-public-kweb-2026-stress.json"
REGISTER_PATH = DOMAIN_DIR / "sources" / "source_register.csv"

CASE_ID = "etf-public-kweb-2026-stress"
AS_OF = "2026-08-17"

PROFILE = json.loads((OUT_DIR / "KWEB_alphavantage_etf_profile.json").read_text(encoding="utf-8"))
QUOTE = json.loads((OUT_DIR / "KWEB_alphavantage_global_quote.json").read_text(encoding="utf-8"))
NCSR = json.loads((OUT_DIR / "KWEB_sec_ncsr_annual_report.json").read_text(encoding="utf-8"))

AV_SOURCE = {
    "name": "KraneShares CSI China Internet ETF Profile (Alpha Vantage, fund-disclosed holdings/AUM/expense ratio)",
    "url": "https://www.alphavantage.co/documentation/#etf-profile",
    "as_of": PROFILE["retrieved_at"],
    "notes": (
        "Fund net assets, net expense ratio, and trailing dividend yield, retrieved via "
        "Alpha Vantage ETF_PROFILE (symbol=KWEB). Sourced from the fund's own disclosed "
        "holdings/profile data. This endpoint returned no sector breakdown for this fund "
        "(unlike QQQ) -- sector weights below are sourced from the fund's SEC N-CSR instead."
    ),
}
QUOTE_SOURCE = {
    "name": f"KWEB market close price (Alpha Vantage GLOBAL_QUOTE, {QUOTE['latestDay']})",
    "url": "https://www.alphavantage.co/documentation/#quote-endpoint",
    "as_of": QUOTE["latestDay"],
    "notes": f"Last daily close ${QUOTE['price']}, retrieved via Alpha Vantage GLOBAL_QUOTE (symbol=KWEB).",
}
NCSR_SOURCE = {
    "name": "KraneShares CSI China Internet ETF Annual Shareholder Report (SEC Form N-CSR)",
    "url": NCSR["url"],
    "as_of": "2026-03-31",
    "notes": (
        f"Filed {NCSR['filed_at']}, accession {NCSR['accession_number']}, CIK {NCSR['cik']}. "
        "Source of sector weightings, total net assets, holdings count, and the realized "
        "5-year average annual total return used as this case's adversarial outcome."
    ),
}


def _holdings() -> list[dict[str, Any]]:
    """Top 30 named rows (5-34) -- row 35 is the template's own formula-computed
    'All other constituents' remainder (=MAX(0,1-SUM(D5:D34))), same convention
    etf-public-qqq-2026 uses. Do not write into row 35."""
    real = [h for h in PROFILE["holdings"] if h["description"] not in ("CASH", "HONG KONG DOLLAR")]
    real.sort(key=lambda h: float(h["weight"]), reverse=True)
    return real[:30]


def _sectors() -> list[tuple[str, float]]:
    """Disclosed sector weights plus the fund's own balancing line.

    An N-CSR's sector weightings are percent-of-net-assets applied to
    *investments*, so they do not sum to 100% on their own -- KWEB's sum to
    102.6% because the fund carries 2.6% of net liabilities. The Schedule of
    Investments discloses both halves on adjacent lines:

        TOTAL INVESTMENTS - 102.6%
        OTHER ASSETS LESS LIABILITIES - (2.6)%
        NET ASSETS - 100%

    Carrying only the first half leaves the grid summing to 102.6%, which
    resolves the Checks sheet to REVIEW and reads to any fund-reporting
    audience as either an arithmetic error or unexplained leverage. Carrying
    both is not smoothing -- it adds a second disclosed figure from the same
    filing, and the grid then reconciles to exactly 100%.
    """
    items = sorted(
        NCSR["captured_values"]["sector_weightings_pct_of_net_assets"].items(),
        key=lambda kv: kv[1],
        reverse=True,
    )
    items = items[:10]
    items.append(
        (
            "Other assets less liabilities",
            NCSR["captured_values"]["other_assets_less_liabilities_pct_of_net_assets"],
        )
    )
    return items


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    holdings = _holdings()
    sectors = _sectors()
    net_assets_mm = NCSR["captured_values"]["total_net_assets_usd"] / 1_000_000
    net_expense_ratio = float(PROFILE["net_expense_ratio"])
    dividend_yield = float(PROFILE["dividend_yield"])
    price = QUOTE["price"]

    inputs: list[dict[str, Any]] = [
        {"sheet": "Cover", "cell": "C9", "value": "Downside", "input_kind": "modeler", "source": {
            "name": "Case design decision",
            "url": "repo://tools/build_etf_kweb_case.py",
            "as_of": AS_OF,
            "notes": "This case is the adversarial half of the pair; only the Downside column is populated with real data.",
        }},
        {"sheet": "Assumptions", "cell": "D5", "value": round(net_assets_mm, 1), "input_kind": "observed", "source": NCSR_SOURCE},
        {"sheet": "Assumptions", "cell": "D6", "value": net_expense_ratio, "input_kind": "observed", "source": AV_SOURCE},
        {"sheet": "Assumptions", "cell": "D7", "value": dividend_yield, "input_kind": "observed", "source": AV_SOURCE},
        {"sheet": "Assumptions", "cell": "D8", "value": price, "input_kind": "observed", "source": QUOTE_SOURCE},
    ]

    for i, h in enumerate(holdings):
        row = 5 + i
        # "n/a" here is the fund's own disclosed reality, not a gap in this case's
        # sourcing: most of KWEB's constituents are Hong Kong-primary listings with
        # no US ticker, only an ADR for the minority that cross-list. Fabricating a
        # pseudo-symbol (e.g. truncating the description) would misrepresent that.
        symbol = h["symbol"]
        inputs.append({"sheet": "Portfolio Construction", "cell": f"B{row}", "value": symbol, "input_kind": "observed", "source": AV_SOURCE})
        inputs.append({"sheet": "Portfolio Construction", "cell": f"C{row}", "value": h["description"], "input_kind": "observed", "source": AV_SOURCE})
        inputs.append({"sheet": "Portfolio Construction", "cell": f"D{row}", "value": round(float(h["weight"]), 4), "input_kind": "observed", "source": AV_SOURCE})

    for i, (sector, weight) in enumerate(sectors):
        row = 40 + i
        inputs.append({"sheet": "Portfolio Construction", "cell": f"B{row}", "value": sector.upper(), "input_kind": "observed", "source": NCSR_SOURCE})
        inputs.append({"sheet": "Portfolio Construction", "cell": f"C{row}", "value": weight, "input_kind": "observed", "source": NCSR_SOURCE})

    outcome = {
        "metric": "five_year_average_annual_total_return",
        "forecast": 0.0,
        "realized": NCSR["captured_values"]["average_annual_total_returns_as_of_2026_03_31"]["fund_net_return"]["5_years"],
        "realized_source": "KraneShares CSI China Internet ETF N-CSR annual shareholder report, period ended 2026-03-31 (fund's own disclosed Average Annual Total Returns table)",
        "status": "recorded",
    }

    manifest = {
        "schema_version": "1.0",
        "id": CASE_ID,
        "classification": "external_historical_case",
        "counts_toward_M4": False,
        "template": "30_ETF_Construction_Management/_template_ETF.xlsx",
        "output": "30_ETF_Construction_Management/instances/public_kweb_2026_stress.xlsx",
        "as_of": AS_OF,
        "scenario": "Downside",
        "cover": {
            "ETF / share class:": "KraneShares CSI China Internet ETF (NYSE Arca: KWEB)",
            "Benchmark index:": "CSI Overseas China Internet Index",
        },
        "inputs": inputs,
        "sources": [AV_SOURCE, QUOTE_SOURCE, NCSR_SOURCE],
        "refresh": {
            "date": AS_OF,
            "trigger": "Adversarial-pair sourcing for the ETF Construction & Management domain (model_card.md thin-coverage gap)",
            "source_snapshot": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
            "what_changed": f"Generated public case {CASE_ID} from canonical release template",
            "reviewer_notes": "External historical case; human stakeholder approval remains pending",
            "next_check": "On source revision, builder change, monitoring breach, or quarterly review",
        },
        "outcome": outcome,
        "lineage": {
            "source_snapshot": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
            "synthetic_benchmark_inputs_allowed": False,
        },
    }

    snapshot = {
        "schema_version": "1.0",
        "model_id": "30",
        "domain": "ETF Construction & Management",
        "case_id": CASE_ID,
        "case_type": "adversarial",
        "as_of": AS_OF,
        "capture_method": "curated_public_observation",
        "sources": [
            {
                "name": AV_SOURCE["name"],
                "url": AV_SOURCE["url"],
                "publisher": "KraneShares (via Alpha Vantage)",
                "captured_values": {
                    "net_expense_ratio": net_expense_ratio,
                    "dividend_yield": dividend_yield,
                    "inception_date": PROFILE["inception_date"],
                    "market_price_usd": price,
                    "holdings_count_disclosed": len(PROFILE["holdings"]),
                },
            },
            {
                "name": NCSR_SOURCE["name"],
                "url": NCSR_SOURCE["url"],
                "publisher": "Krane Shares Trust (SEC EDGAR)",
                "captured_values": NCSR["captured_values"],
            },
        ],
    }
    snapshot["snapshot_sha256"] = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return manifest, snapshot


def write_source_register(snapshot: dict[str, Any]) -> None:
    rows = [
        (
            CASE_ID,
            "KraneShares CSI China Internet ETF Profile (Alpha Vantage, fund-disclosed holdings/AUM/expense ratio)",
            "Alpha Vantage MCP (fund-disclosed holdings/profile data)",
            "https://www.alphavantage.co/documentation/#etf-profile",
            PROFILE["retrieved_at"],
            str(SNAPSHOT_PATH.relative_to(ROOT)),
            snapshot["snapshot_sha256"],
            "frozen",
        ),
        (
            CASE_ID,
            f"KWEB market close price (Alpha Vantage GLOBAL_QUOTE)",
            "Alpha Vantage MCP",
            "https://www.alphavantage.co/documentation/#quote-endpoint",
            QUOTE["latestDay"],
            str((OUT_DIR / "KWEB_alphavantage_global_quote.json").relative_to(ROOT)),
            hashlib.sha256((OUT_DIR / "KWEB_alphavantage_global_quote.json").read_bytes()).hexdigest(),
            "active",
        ),
        (
            CASE_ID,
            NCSR_SOURCE["name"],
            "U.S. Securities and Exchange Commission (EDGAR, Form N-CSR)",
            NCSR["url"],
            "2026-03-31",
            str((OUT_DIR / "KWEB_sec_ncsr_annual_report.json").relative_to(ROOT)),
            hashlib.sha256((OUT_DIR / "KWEB_sec_ncsr_annual_report.json").read_bytes()).hexdigest(),
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
    print(report_sync(CASE_ID, snapshot["snapshot_sha256"]))
    print(f"inputs={len(manifest['inputs'])} sourced cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
