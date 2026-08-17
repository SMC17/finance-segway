"""Generate the UiPath public case: the adversarial pair to software-public-adobe-fy2025.

As-of point: UiPath's fiscal year 2023 (ended 2023-01-31), the year its
dollar-based net retention rate first cratered (145% -> 123%) alongside a
well-documented leadership crisis (the co-CEO structure was unwound in
April 2023). The decline was not a one-off: the following year's 10-K
discloses retention fell further, to 119% -- that continuation is this
case's realized outcome.

Same three-way input labeling Adobe's case established:
  observed  - a value read directly off a disclosed fact.
  derived   - arithmetic on disclosed facts, with the arithmetic stated.
  modeler_assumption - no disclosure exists; a driver, constrained where
              possible by something that IS disclosed (see the ARR
              flow-rate split below).

WHAT THIS CASE CAN AND CANNOT GROUND
-------------------------------------
UiPath's ARR growth (30% for FY2023, real and disclosed) decomposes into a
new-customer component and a net-existing-customer-expansion component,
both DERIVABLE from two disclosed facts (total net-new ARR in dollars, and
the dollar-based net retention rate). Neither source discloses the further
split of the existing-customer effect into gross Expansion vs Contraction
vs Churn individually -- Contraction and Gross churn are declared
modeler_assumption drivers (informed by this repo's own template Base
defaults), and Expansion carries the balancing residual so the four rows
sum to exactly the disclosed net growth. This mirrors Adobe's case, which
used gross churn as its residual; here Expansion is the residual because
Contraction and Churn are the two components more commonly independently
estimated in SaaS unit-economics literature.

UiPath's revenue has three disclosed categories (Licenses, Subscription
services, Professional services), not the template's two (Subscription,
Services). ARR by UiPath's own definition explicitly excludes perpetual
licenses and professional services, so this case maps the template's
"Subscription revenue" to UiPath's own "Subscription services" line and
"Services revenue" to "Professional services and other" -- License
revenue ($497.8mm, 47% of FY2023 revenue) falls outside what this
ARR-driven template can represent and is not force-fit into it. That is a
real, stated gap, not a rounding choice.

Usage:
    python tools/build_software_uipath_case.py
    python tools/build_software_uipath_case.py --print-only
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "tools" / "data_fabric" / "out"
DOMAIN_DIR = ROOT / "31_Software_SaaS"
MANIFEST_PATH = ROOT / "standards" / "public_cases" / "software-public-uipath-fy2023-stress.json"
SNAPSHOT_PATH = DOMAIN_DIR / "sources" / "snapshots" / "software-public-uipath-fy2023-stress.json"
REGISTER_PATH = DOMAIN_DIR / "sources" / "source_register.csv"

CASE_ID = "software-public-uipath-fy2023-stress"
AS_OF = "2023-01-31"

TENK = json.loads((OUT_DIR / "PATH_sec_10k_fy2023_stress.json").read_text(encoding="utf-8"))
V = TENK["captured_values"]

TENK_SOURCE = {
    "name": "UiPath, Inc. FY2023 Form 10-K (SEC EDGAR, CIK 0001734722)",
    "url": TENK["url"],
    "as_of": "2023-01-31",
    "notes": (
        f"Filed {TENK['filed_at']}, accession {TENK['accession_number']}. Source of ARR, "
        "net retention rate, revenue mix, cost structure, RPO, and capex for FY2023."
    ),
}
FY24_SOURCE = {
    "name": "UiPath, Inc. FY2024 Form 10-K (SEC EDGAR, CIK 0001734722)",
    "url": "https://www.sec.gov/Archives/edgar/data/1734722/000173472224000011/path-20240131.htm",
    "as_of": "2024-01-31",
    "notes": "Filed 2024-03-27. Source of the realized outcome: FY2024 dollar-based net retention rate (119%), disclosed alongside the FY2023 comparative (123%).",
}
XBRL_SOURCE = {
    "name": "UiPath XBRL annual fact series (SEC EDGAR company facts, CIK 0001734722)",
    "url": "https://data.sec.gov/api/xbrl/companyfacts/CIK0001734722.json",
    "as_of": "2023-01-31",
    "notes": "Cross-check for revenue, gross profit, operating loss against the 10-K's own statement of operations (recorded at tools/data_fabric/out/PATH_facts_annual_series.json).",
}


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    beginning_arr_mm = V["arr_usd"]["2022-01-31"] / 1_000_000
    ending_arr_mm = V["arr_usd"]["2023-01-31"] / 1_000_000
    net_new_arr_mm = V["net_new_arr_usd_fy2023"] / 1_000_000
    net_retention = V["dollar_based_net_retention_rate"]["2023-01-31"]

    net_expansion_rate = net_retention - 1.0  # 0.23, derived from disclosed retention rate
    new_customer_arr_mm = net_new_arr_mm - net_expansion_rate * beginning_arr_mm
    new_arr_rate = new_customer_arr_mm / beginning_arr_mm  # derived

    contraction_rate = 0.05  # modeler_assumption, informed by template's own Base default order of magnitude
    churn_rate = 0.08  # modeler_assumption, matches template's own Base default exactly
    expansion_rate = net_expansion_rate + contraction_rate + churn_rate  # derived residual

    subscription_rev = V["revenue_usd"]["subscription_services"]
    services_rev = V["revenue_usd"]["professional_services_and_other"]
    services_pct_of_subscription = services_rev / subscription_rev  # derived
    subscription_cost = V["cost_of_revenue_usd"]["subscription_services"]
    subscription_margin = (subscription_rev - subscription_cost) / subscription_rev  # derived
    services_cost = V["cost_of_revenue_usd"]["professional_services_and_other"]
    services_margin = (services_rev - services_cost) / services_rev  # derived, negative

    total_rev = V["revenue_usd"]["total"]
    sm_pct = V["operating_expenses_usd"]["sales_and_marketing"] / total_rev
    rd_pct = V["operating_expenses_usd"]["research_and_development"] / total_rev
    ga_pct = V["operating_expenses_usd"]["general_and_administrative"] / total_rev
    capex_pct = V["capex_usd"] / total_rev
    rpo_coverage = V["remaining_performance_obligations_usd"] / total_rev  # derived, ending RPO / revenue

    inputs: list[dict[str, Any]] = [
        {"sheet": "Cover", "cell": "C9", "value": "Downside", "input_kind": "modeler_assumption", "source": {
            "name": "Case design decision", "url": "repo://tools/build_software_uipath_case.py", "as_of": AS_OF,
            "notes": "This case is the adversarial half of the pair; only the Downside column is populated with real data.",
        }},
        {"sheet": "Assumptions", "cell": "D5", "value": round(beginning_arr_mm, 1), "input_kind": "observed", "source": TENK_SOURCE},
        {"sheet": "Assumptions", "cell": "D6", "value": round(new_arr_rate, 4), "input_kind": "derived", "source": TENK_SOURCE},
        {"sheet": "Assumptions", "cell": "D7", "value": round(expansion_rate, 4), "input_kind": "derived", "source": TENK_SOURCE},
        {"sheet": "Assumptions", "cell": "D8", "value": contraction_rate, "input_kind": "modeler_assumption", "source": TENK_SOURCE},
        {"sheet": "Assumptions", "cell": "D9", "value": churn_rate, "input_kind": "modeler_assumption", "source": TENK_SOURCE},
        {"sheet": "Assumptions", "cell": "D10", "value": round(services_pct_of_subscription, 4), "input_kind": "derived", "source": TENK_SOURCE},
        {"sheet": "Assumptions", "cell": "D11", "value": round(subscription_margin, 4), "input_kind": "derived", "source": TENK_SOURCE},
        {"sheet": "Assumptions", "cell": "D12", "value": round(services_margin, 4), "input_kind": "derived", "source": TENK_SOURCE},
        {"sheet": "Assumptions", "cell": "D13", "value": round(sm_pct, 4), "input_kind": "derived", "source": TENK_SOURCE},
        {"sheet": "Assumptions", "cell": "D14", "value": round(rd_pct, 4), "input_kind": "derived", "source": TENK_SOURCE},
        {"sheet": "Assumptions", "cell": "D15", "value": round(ga_pct, 4), "input_kind": "derived", "source": TENK_SOURCE},
        {"sheet": "Assumptions", "cell": "D17", "value": round(capex_pct, 4), "input_kind": "derived", "source": TENK_SOURCE},
        {"sheet": "Assumptions", "cell": "D19", "value": round(subscription_margin, 4), "input_kind": "derived", "source": TENK_SOURCE},
        {"sheet": "Assumptions", "cell": "D21", "value": round(rpo_coverage, 4), "input_kind": "derived", "source": TENK_SOURCE},
    ]

    outcome = {
        "metric": "next_fiscal_year_dollar_based_net_retention_rate",
        "forecast": net_retention,
        "realized": V["dollar_based_net_retention_rate"]["2023-01-31"] - 0.04,
        "realized_source": "UiPath FY2024 Form 10-K: dollar-based net retention rate of 119% at 2024-01-31, vs 123% at 2023-01-31 (both disclosed in that filing)",
        "status": "recorded",
    }
    # keep the realized figure exact rather than float-subtracted
    outcome["realized"] = 1.19

    manifest = {
        "schema_version": "1.0",
        "id": CASE_ID,
        "classification": "external_historical_case",
        "counts_toward_M4": False,
        "template": "31_Software_SaaS/_template_SOFTWARE.xlsx",
        "output": "31_Software_SaaS/instances/public_uipath_fy2023_stress.xlsx",
        "as_of": AS_OF,
        "scenario": "Downside",
        "cover": {
            "Title:": "UiPath, Inc. -- FY2023 net-retention deceleration case",
            "Company / ticker:": "UiPath, Inc. (NYSE: PATH), CIK 0001734722",
            "Subsector:": "application software -- SEC SIC 7372 (Services-Prepackaged Software), as filed by the registrant",
            "Fiscal year end:": "2023-01-31 (FY2023)",
            "Next filing / refresh:": "FY2024 10-K, filed 2024-03-27, already used for this case's realized outcome",
        },
        "inputs": inputs,
        "sources": [TENK_SOURCE, FY24_SOURCE, XBRL_SOURCE],
        "refresh": {
            "date": AS_OF,
            "trigger": "Adversarial-pair sourcing for the Software & SaaS domain (model_card.md thin-coverage gap)",
            "source_snapshot": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
            "what_changed": f"Generated public case {CASE_ID} from canonical release template",
            "reviewer_notes": (
                "External historical case; human stakeholder approval remains pending. "
                "License revenue (47% of FY2023 revenue) falls outside this ARR-driven template's scope and is not represented. "
                "Unlike software-public-adobe-fy2025 (which uses revenue AS an ARR proxy, by construction near-consistent with "
                "itself), this case uses UiPath's own REAL disclosed ARR as the scale driver. UiPath's ARR (annualized invoiced "
                "amounts from subscription + maintenance/support) and its GAAP Subscription-services revenue line are genuinely "
                "different bases -- the template's avg-ARR-times-(1+services%) revenue formula, applied to real ARR, implies "
                "Year-1 total revenue of ~$1,173.1mm against UiPath's actual disclosed FY2023 revenue of $1,058.6mm, a +10.8% "
                "gap. This is not a modeling error: it is the real, measurable distance between an ARR-native metric and GAAP "
                "revenue recognition timing for this specific company, disclosed here rather than papered over."
            ),
            "next_check": "On source revision, builder change, monitoring breach, or quarterly review",
        },
        "outcome": outcome,
        "lineage": {
            "source_snapshot": f"repo://{SNAPSHOT_PATH.relative_to(ROOT)}",
            "synthetic_benchmark_inputs_allowed": False,
        },
        "driver_declarations": [
            {
                "sheet": "Assumptions", "cell": "D8", "driver_type": "undisclosed_metric_driver",
                "rationale": "UiPath discloses net retention (net of expansion/contraction/churn) but not gross contraction separately. Chosen at an order of magnitude typical for enterprise SaaS; does not affect the derived net-growth tie-out.",
                "basis": {},
            },
            {
                "sheet": "Assumptions", "cell": "D9", "driver_type": "undisclosed_metric_driver",
                "rationale": "UiPath discloses net retention but not gross churn separately. Set equal to this repo's own SOFTWARE template Base-scenario default (8%) as the most defensible anchor available.",
                "basis": {},
            },
            {
                "sheet": "Assumptions", "cell": "D7", "driver_type": "balancing_residual",
                "rationale": "Expansion ARR is the balancing residual: Expansion = (net_retention - 1) + Contraction + Churn, so the four flow rates sum to exactly UiPath's disclosed 30% FY2023 ARR growth rate. This mirrors software-public-adobe-fy2025's use of gross churn as its own residual.",
                "basis": {},
            },
        ],
    }

    snapshot = {
        "schema_version": "1.0",
        "model_id": "31",
        "domain": "Software & SaaS",
        "case_id": CASE_ID,
        "case_type": "adversarial",
        "as_of": AS_OF,
        "capture_method": "curated_public_observation",
        "sources": [
            {"name": TENK_SOURCE["name"], "url": TENK_SOURCE["url"], "publisher": "UiPath, Inc. (SEC EDGAR)", "captured_values": V},
            {"name": FY24_SOURCE["name"], "url": FY24_SOURCE["url"], "publisher": "UiPath, Inc. (SEC EDGAR)", "captured_values": {"dollar_based_net_retention_rate_fy2024": 1.19}},
        ],
    }
    snapshot["snapshot_sha256"] = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode("utf-8")).hexdigest()
    return manifest, snapshot


def write_source_register(snapshot: dict[str, Any]) -> None:
    rows = [
        (CASE_ID, TENK_SOURCE["name"], "U.S. Securities and Exchange Commission (EDGAR, Form 10-K)", TENK_SOURCE["url"], "2023-01-31",
         str(SNAPSHOT_PATH.relative_to(ROOT)), snapshot["snapshot_sha256"], "frozen"),
        (CASE_ID, FY24_SOURCE["name"], "U.S. Securities and Exchange Commission (EDGAR, Form 10-K)", FY24_SOURCE["url"], "2024-01-31",
         str((OUT_DIR / "PATH_sec_10k_fy2023_stress.json").relative_to(ROOT)), hashlib.sha256((OUT_DIR / "PATH_sec_10k_fy2023_stress.json").read_bytes()).hexdigest(), "active"),
        (CASE_ID, XBRL_SOURCE["name"], "U.S. Securities and Exchange Commission (EDGAR, XBRL company facts)", XBRL_SOURCE["url"], "2023-01-31",
         str((OUT_DIR / "PATH_facts_annual_series.json").relative_to(ROOT)), hashlib.sha256((OUT_DIR / "PATH_facts_annual_series.json").read_bytes()).hexdigest(), "active"),
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
    print(f"inputs={len(manifest['inputs'])} sourced cells, drivers={len(manifest['driver_declarations'])} declared")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
