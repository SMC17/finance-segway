"""Public historical evidence registry for nine recently hardened M2 domains.

Every case's forecast/realized pair was authored on AS_OF using fully public,
already-known historical facts -- there is no case in this registry where the
forecast was genuinely made before the outcome existed. That alone means none
of this is real predictive-track-record evidence in the sense M4's
"multi_release_outcome_history" requirement is written for; monitoring that
actually starts before an outcome resolves is a separate, not-yet-built
system. Given that shared limitation, outcome pairs still differ in what they
demonstrate, and FORECAST_KIND makes the difference explicit rather than
letting every case look like the same kind of evidence:

  - "point_forecast": an independently chosen number that could have differed
    from the realized value, and in most cases here genuinely does (e.g.
    Boeing's forecast 75000 vs realized 58158 -- a real, sourced miss). This
    is the closest thing to genuine model behavior on record, even though it
    was chosen in hindsight.
  - "same_period_reproduction": forecast and realized describe the exact same
    already-known fact, and the workbook's own formula reproduces it from its
    other inputs. Proves the model's arithmetic is right; proves nothing
    about prediction.
  - "hindsight_restated_fact": forecast is not independent at all -- it was
    copied from the same source cited for realized (sometimes literally the
    same captured_values field), so forecast == realized by construction with
    zero chance of ever differing. This is the defect class an earlier
    external review flagged ("some rows are literal identities... contribute
    zero real signal"): a binary "did the modeled stress scenario happen"
    confirmation, or a plainly-copied cross-period figure, dressed up with
    forecast/realized column headers that imply a comparison never actually
    happened. Still legitimate evidence that the case's stress scenario is
    grounded in a real, not hypothetical, event -- just not forecast evidence.
"""
from __future__ import annotations

from typing import Any

AS_OF = "2026-08-04"
FORECAST_KINDS = frozenset({"point_forecast", "same_period_reproduction", "hindsight_restated_fact"})


def source(
    name: str,
    url: str,
    publisher: str,
    captured_values: dict[str, Any],
) -> dict[str, Any]:
    return {
        "name": name,
        "url": url,
        "publisher": publisher,
        "captured_values": captured_values,
    }


def override(
    sheet: str,
    cell: str,
    value: Any,
    kind: str,
    source_name: str,
) -> dict[str, Any]:
    return {
        "sheet": sheet,
        "cell": cell,
        "value": value,
        "kind": kind,
        "source": source_name,
    }


def case(
    case_id: str,
    case_type: str,
    output: str,
    subject: str,
    as_of: str,
    sources: list[dict[str, Any]],
    overrides: list[dict[str, Any]],
    metric: str,
    forecast: float,
    realized: float | None,
    realized_source: str,
    forecast_kind: str,
) -> dict[str, Any]:
    if forecast_kind not in FORECAST_KINDS:
        raise ValueError(f"{case_id}: unknown forecast_kind {forecast_kind!r}, expected one of {sorted(FORECAST_KINDS)}")
    return {
        "id": case_id,
        "type": case_type,
        "output": output,
        "subject": subject,
        "as_of": as_of,
        "sources": sources,
        "overrides": overrides,
        "outcome": {
            "metric": metric,
            "forecast": forecast,
            "realized": realized,
            "realized_source": realized_source,
            "forecast_kind": forecast_kind,
            "status": "recorded" if realized is not None else "pending",
        },
    }


COMMON_PROHIBITED = [
    "Live capital, fiduciary, regulatory, legal, or tax use without named human approval",
    "Representing retained modeler assumptions as external observations",
    "Treating historical public cases as transaction-specific diligence",
]

# Models where every case is forecast_kind == "hindsight_restated_fact" --
# zero genuine (point_forecast / same_period_reproduction) outcome evidence.
# tests/test_frontier_evidence.py requires each model to have at least one
# genuine case unless listed here; an entry means the gap is real and known,
# not silently accepted. Fixing either domain needs a genuinely independent
# forecast -- e.g. a growth-rate extrapolation sourced from data other than
# the realized-value's own source -- which is real sourcing/modeling work,
# not a one-line change, so it's tracked rather than rushed.
KNOWN_HINDSIGHT_ONLY_MODELS: frozenset[str] = frozenset({"23", "24"})


MODEL_META: dict[str, dict[str, Any]] = {
    "08": {
        "domain": "Asset Management",
        "folder": "08_Asset_Management",
        "risk_tier": "Tier 1",
        "approved_uses": [
            "Fund and manager performance diagnostics",
            "NAV, fee-waterfall, exposure and liquidity review",
            "Historical public-manager stress comparison",
        ],
        "limitations": [
            "Public-manager AUM is a proxy for a fund-level NAV rollforward",
            "AUM flow disclosures do not provide transaction-level fee and carry terms",
            "Liquidity and unfunded-commitment cells remain sensitivity inputs unless explicitly sourced",
        ],
        "monitoring": [
            {"metric": "aum_rollforward_residual", "warning": 0.01, "breach": 0.05, "action": "Reconcile flows, markets, FX, acquisitions and distributions"},
            {"metric": "liquidity_coverage", "warning": 1.20, "breach": 1.00, "action": "Escalate redemption and unfunded-commitment funding plan"},
        ],
        "retirement_trigger": "Performance methodology, fee structure, or liquidity architecture is superseded",
    },
    "10": {
        "domain": "Trade Finance",
        "folder": "10_Trade_Finance",
        "risk_tier": "Tier 1",
        "approved_uses": [
            "Working-capital-cycle and borrowing-need diagnostics",
            "Documentary, country, facility and expected-loss stress",
            "Historical exporter and supply-chain comparison",
        ],
        "limitations": [
            "Public statements aggregate multiple products and jurisdictions",
            "LC, factoring and facility terms remain modeler assumptions without executed documents",
            "Inventory includes program and production effects beyond trade-finance mechanics",
        ],
        "monitoring": [
            {"metric": "cash_conversion_cycle_days", "warning": 120, "breach": 180, "action": "Re-underwrite inventory, receivables, payables and facility availability"},
            {"metric": "facility_utilization", "warning": 0.85, "breach": 1.00, "action": "Escalate borrowing base and liquidity remediation"},
        ],
        "retirement_trigger": "Documentary-credit, facility or working-capital architecture changes materially",
    },
    "11": {
        "domain": "Microfinance",
        "folder": "11_Microfinance",
        "risk_tier": "Tier 1",
        "approved_uses": [
            "Portfolio-quality and sustainability diagnostics",
            "PAR, provisioning, funding and client-conduct stress",
            "Historical MFI comparison",
        ],
        "limitations": [
            "Public regional disclosures may not provide complete reserve or funding schedules",
            "Average loan size is derived from rounded portfolio and client counts",
            "Affordability and conduct conclusions require borrower-level evidence",
        ],
        "monitoring": [
            {"metric": "par30", "warning": 0.05, "breach": 0.10, "action": "Escalate collections, provisioning and client-protection review"},
            {"metric": "operational_self_sufficiency", "warning": 1.05, "breach": 1.00, "action": "Re-underwrite pricing, cost base and subsidy dependence"},
        ],
        "retirement_trigger": "Portfolio definitions, lending methodology, funding or conduct standards change materially",
    },
    "12": {
        "domain": "Equity Finance",
        "folder": "12_Equity_Finance",
        "risk_tier": "Tier 1",
        "approved_uses": [
            "Primary issuance, rights, convert and dilution analysis",
            "Ownership and proceeds reconciliation",
            "Historical financing-structure comparison",
        ],
        "limitations": [
            "A public underwritten offering is used as a primary-issuance proxy rather than a literal rights offering",
            "Anti-dilution, registration and voting terms require executed documents",
            "Market impact and investor allocation are not observed from offering proceeds alone",
        ],
        "monitoring": [
            {"metric": "fully_diluted_ownership_change", "warning": 0.10, "breach": 0.25, "action": "Escalate dilution attribution and shareholder protections"},
            {"metric": "proceeds_reconciliation_residual", "warning": 0.01, "breach": 0.05, "action": "Reconcile gross proceeds, fees and balance-sheet receipt"},
        ],
        "retirement_trigger": "Capital structure, security terms, or ownership architecture is superseded",
    },
    "15": {
        "domain": "Commodities",
        "folder": "15_Commodities",
        "risk_tier": "Tier 1",
        "approved_uses": [
            "Physical balance, storage, basis and cost-of-carry analysis",
            "Hedge-ratio and contract-alignment stress",
            "Historical market-dislocation comparison",
        ],
        "limitations": [
            "Annual prices and weekly storage data are simplified into a static workbook snapshot",
            "Location, quality, timing and optionality basis require contract-level data",
            "Physical operations and margin calls require daily treasury evidence",
        ],
        "monitoring": [
            {"metric": "basis_move", "warning": 10.0, "breach": 25.0, "action": "Reconcile location, quality, timing and liquidity basis"},
            {"metric": "storage_utilization", "warning": 0.75, "breach": 0.90, "action": "Escalate logistics, financing and hedge-roll plan"},
        ],
        "retirement_trigger": "Contract specification, delivery point, storage or hedging program changes materially",
    },
    "16": {
        "domain": "Crypto & Digital Assets",
        "folder": "16_Crypto_Digital_Assets",
        "risk_tier": "Tier 1",
        "approved_uses": [
            "Supply, unlock, staking, treasury and liquidity diagnostics",
            "Custody, venue, bridge and counterparty stress",
            "Historical public-platform comparison",
        ],
        "limitations": [
            "Custodied customer assets are a platform-scale proxy rather than a native token supply schedule",
            "On-chain ownership, validator and unlock data require protocol-specific snapshots",
            "Custody controls require independent operating and security evidence",
        ],
        "monitoring": [
            {"metric": "unlock_to_liquidity_ratio", "warning": 0.25, "breach": 0.50, "action": "Escalate unlock concentration and market-depth plan"},
            {"metric": "custody_counterparty_concentration", "warning": 0.25, "breach": 0.50, "action": "Re-underwrite custody, venue and key-management concentration"},
        ],
        "retirement_trigger": "Protocol economics, custody architecture or market structure is superseded",
    },
    "17": {
        "domain": "Real Estate & REIT",
        "folder": "17_Real_Estate_REIT",
        "risk_tier": "Tier 1",
        "approved_uses": [
            "NOI, cap-rate, debt, lease-roll and REIT bridge analysis",
            "DSCR, LTV and refinancing stress",
            "Historical public-owner and flexible-office comparison",
        ],
        "limitations": [
            "Company-wide public filings are simplified into a property/REIT decision model",
            "The flexible-office adversarial case is an occupancy-economics proxy and not REIT accounting",
            "Lease-level rollover, tenant credit and property debt require asset-specific diligence",
        ],
        "monitoring": [
            {"metric": "minimum_dscr", "warning": 1.25, "breach": 1.00, "action": "Escalate refinance, reserves, capex and asset-sale plan"},
            {"metric": "economic_occupancy", "warning": 0.90, "breach": 0.80, "action": "Re-underwrite expirations, renewals, downtime and tenant concentration"},
        ],
        "retirement_trigger": "Portfolio, lease, debt or REIT reporting architecture is superseded",
    },
    "23": {
        "domain": "Fintech & Payments",
        "folder": "23_Fintech_Payments",
        "risk_tier": "Tier 1",
        "approved_uses": [
            "Payment-volume, network, unit-economics and cohort diagnostics",
            "Fraud, chargeback, capital and settlement-liquidity stress",
            "Historical payment-network and platform-disposal comparison",
        ],
        "limitations": [
            "Public network scale is annual and aggregated while the workbook labels monthly unit economics",
            "The Worldpay case uses sale proceeds and impairments as capital-stress proxies",
            "Product-level fraud, safeguarding and settlement data require operating records",
        ],
        "monitoring": [
            {"metric": "fraud_bps", "warning": 50, "breach": 100, "action": "Escalate fraud controls, pricing and merchant exposure"},
            {"metric": "liquidity_coverage", "warning": 1.10, "breach": 1.00, "action": "Escalate unrestricted liquidity and settlement obligations"},
        ],
        "retirement_trigger": "Payment network, safeguarding, capital or product architecture changes materially",
    },
    "24": {
        "domain": "Distressed & Restructuring",
        "folder": "24_Distressed_Restructuring",
        "risk_tier": "Tier 1",
        "approved_uses": [
            "13-week liquidity and rescue-financing analysis",
            "Claim waterfall, fulcrum and priority diagnostics",
            "Historical reorganization and failure-path comparison",
        ],
        "limitations": [
            "Public filings do not replace claim schedules, cash receipts and legal opinions",
            "New-money economics and priority require executed documents and court orders",
            "Historical outcomes cannot establish feasibility for a different debtor",
        ],
        "monitoring": [
            {"metric": "minimum_13_week_liquidity", "warning": 1.20, "breach": 1.00, "action": "Escalate funding, disbursement and filing plan"},
            {"metric": "waterfall_conservation_residual", "warning": 0.01, "breach": 0.05, "action": "Block release and reconcile claims, value and distributions"},
        ],
        "retirement_trigger": "Plan, capital structure, court status or operating case is superseded",
    },
}


def registry() -> dict[str, Any]:
    cases: dict[str, list[dict[str, Any]]] = {}

    blackrock_2023 = source(
        "BlackRock 2023 Form 10-K",
        "https://www.sec.gov/Archives/edgar/data/1364742/000095017024019271/blk-20231231.htm",
        "U.S. SEC / BlackRock",
        {
            "beginning_aum_usd_bn": 8594.485,
            "net_inflows_usd_bn": 288.695,
            "market_fx_acquisition_change_usd_bn": 1125.815,
            "ending_aum_usd_bn": 10008.995,
        },
    )
    blackrock_2022 = source(
        "BlackRock 2022 Form 10-K",
        "https://www.sec.gov/Archives/edgar/data/1364742/000095017023004343/blk-20221231.htm",
        "U.S. SEC / BlackRock",
        {
            "beginning_aum_usd_bn": 10010.143,
            "net_inflows_usd_bn": 306.570,
            "market_fx_change_usd_bn": -1722.228,
            "ending_aum_usd_bn": 8594.485,
        },
    )
    cases["08"] = [
        # Same-period reproduction check, not a forward forecast: the case's
        # own cited source (blackrock_2023) already reports ending_aum_usd_bn
        # for this exact as_of date, and the workbook's own formula (Fund
        # NAV!C10 = C5+C6+C7-C8-C9) reproduces it exactly from the overridden
        # inputs. forecast/realized are therefore both the cited 10008.995 —
        # this demonstrates the model's rollforward arithmetic matches a known
        # fact, previously mismarked with an unrelated, uncited 10500.0 and a
        # "pending" status for an outcome that was already on hand.
        case(
            "am-public-blackrock-2023",
            "conventional",
            "08_Asset_Management/instances/public_blackrock_2023.xlsx",
            "BlackRock 2023 AUM rollforward",
            "2023-12-31",
            [blackrock_2023],
            [
                override("Fund NAV", "C5", 8594.485, "observed", blackrock_2023["name"]),
                override("Fund NAV", "C6", 288.695, "observed", blackrock_2023["name"]),
                override("Fund NAV", "C7", 1125.815, "derived", blackrock_2023["name"]),
                override("Fund NAV", "C8", 0.0, "modeler_assumption", "AUM rollforward normalization"),
                override("Fund NAV", "C9", 0.0, "modeler_assumption", "AUM rollforward normalization"),
            ],
            "ending_aum_usd_bn",
            10008.995,
            10008.995,
            blackrock_2023["name"],
            "same_period_reproduction",
        ),
        case(
            "am-public-blackrock-2022-stress",
            "adversarial",
            "08_Asset_Management/instances/public_blackrock_2022_stress.xlsx",
            "BlackRock 2022 market and FX AUM contraction",
            "2022-12-31",
            [blackrock_2022, blackrock_2023],
            [
                override("Fund NAV", "C5", 10010.143, "observed", blackrock_2022["name"]),
                override("Fund NAV", "C6", 306.570, "observed", blackrock_2022["name"]),
                override("Fund NAV", "C7", -1722.228, "derived", blackrock_2022["name"]),
                override("Fund NAV", "C8", 0.0, "modeler_assumption", "AUM rollforward normalization"),
                override("Fund NAV", "C9", 0.0, "modeler_assumption", "AUM rollforward normalization"),
            ],
            "next_year_ending_aum_usd_bn",
            8500.0,
            10008.995,
            "BlackRock 2023 Form 10-K",
            "point_forecast",
        ),
    ]

    boeing_2020 = source(
        "Boeing 2020 Form 10-K",
        "https://www.sec.gov/Archives/edgar/data/12927/000001292721000011/ba-20201231.htm",
        "U.S. SEC / Boeing",
        {
            "revenue_2019_usd_mm": 76559.0,
            "costs_2019_usd_mm": 72093.0,
            "receivables_2019_usd_mm": 3266.0,
            "inventory_2019_usd_mm": 76622.0,
            "payables_2019_usd_mm": 15553.0,
            "revenue_2020_usd_mm": 58158.0,
            "costs_2020_usd_mm": 63843.0,
            "receivables_2020_usd_mm": 1955.0,
            "inventory_2020_usd_mm": 81715.0,
            "payables_2020_usd_mm": 12928.0,
        },
    )
    boeing_2021 = source(
        "Boeing 2021 Form 10-K",
        "https://www.sec.gov/Archives/edgar/data/12927/000001292722000010/ba-20211231.htm",
        "U.S. SEC / Boeing",
        {"revenue_2021_usd_mm": 62286.0},
    )
    cases["10"] = [
        case(
            "trade-public-boeing-2019",
            "conventional",
            "10_Trade_Finance/instances/public_boeing_2019.xlsx",
            "Boeing 2019 working-capital and inventory case",
            "2019-12-31",
            [boeing_2020],
            [
                override("Working Capital Cycle", "C5", 76559.0, "observed", boeing_2020["name"]),
                override("Working Capital Cycle", "C6", 72093.0, "observed", boeing_2020["name"]),
                override("Working Capital Cycle", "C7", 3266.0, "observed", boeing_2020["name"]),
                override("Working Capital Cycle", "C8", 76622.0, "observed", boeing_2020["name"]),
                override("Working Capital Cycle", "C9", 15553.0, "observed", boeing_2020["name"]),
            ],
            "next_year_revenue_usd_mm",
            75000.0,
            58158.0,
            "Boeing 2020 Form 10-K",
            "point_forecast",
        ),
        case(
            "trade-public-boeing-2020-stress",
            "adversarial",
            "10_Trade_Finance/instances/public_boeing_2020_stress.xlsx",
            "Boeing 2020 production and working-capital shock",
            "2020-12-31",
            [boeing_2020, boeing_2021],
            [
                override("Working Capital Cycle", "C5", 58158.0, "observed", boeing_2020["name"]),
                override("Working Capital Cycle", "C6", 63843.0, "observed", boeing_2020["name"]),
                override("Working Capital Cycle", "C7", 1955.0, "observed", boeing_2020["name"]),
                override("Working Capital Cycle", "C8", 81715.0, "observed", boeing_2020["name"]),
                override("Working Capital Cycle", "C9", 12928.0, "observed", boeing_2020["name"]),
            ],
            "next_year_revenue_usd_mm",
            55000.0,
            62286.0,
            "Boeing 2021 Form 10-K",
            "point_forecast",
        ),
    ]

    asa_2025 = source(
        "ASA International 2025 Annual Report",
        "https://www.asa-international.com/investors/annual-report-2025/",
        "ASA International",
        {"clients_m": 2.8, "gross_olp_usd_mm": 611.0, "par30": 0.018, "net_profit_usd_mm": 56.5},
    )
    asa_q1_2026 = source(
        "ASA International Q1 2026 Business Update",
        "https://www.asa-international.com/media/featured-news/2026-business-update/",
        "ASA International",
        {"clients_m": 2.7, "gross_olp_usd_mm": 583.2, "portfolio_quality": 0.020},
    )
    asa_zambia = source(
        "ASA Zambia operating disclosure",
        "https://zambia.asa-international.com/",
        "ASA International Zambia",
        {"clients_thousand": 35.0, "gross_olp_usd_mm": 7.5, "par30": 0.092},
    )
    cases["11"] = [
        case(
            "microfinance-public-asa-2025",
            "conventional",
            "11_Microfinance/instances/public_asa_2025.xlsx",
            "ASA International 2025 portfolio",
            "2025-12-31",
            [asa_2025, asa_q1_2026],
            [
                override("Loan Portfolio", "C5", 611.0, "observed", asa_2025["name"]),
                override("Loan Portfolio", "C6", 2800.0, "observed", asa_2025["name"]),
                override("Loan Portfolio", "C7", 10.998, "derived", asa_2025["name"]),
                override("Loan Portfolio", "C10", 0.218214, "derived", asa_2025["name"]),
            ],
            "next_quarter_gross_olp_usd_mm",
            625.0,
            583.2,
            "ASA International Q1 2026 Business Update",
            "point_forecast",
        ),
        case(
            "microfinance-public-asa-zambia-stress",
            "adversarial",
            "11_Microfinance/instances/public_asa_zambia_stress.xlsx",
            "ASA Zambia elevated PAR portfolio",
            "2025-12-31",
            [asa_zambia],
            [
                override("Loan Portfolio", "C5", 7.5, "observed", asa_zambia["name"]),
                override("Loan Portfolio", "C6", 35.0, "observed", asa_zambia["name"]),
                override("Loan Portfolio", "C7", 0.69, "derived", asa_zambia["name"]),
                override("Loan Portfolio", "C10", 0.214286, "derived", asa_zambia["name"]),
            ],
            "next_reporting_period_par30",
            0.08,
            None,
            "Pending next maintained evidence refresh",
            "point_forecast",
        ),
    ]

    tesla_offering = source(
        "Tesla February 2020 Final Prospectus",
        "https://www.sec.gov/Archives/edgar/data/1318605/000119312520036491/d861752d424b5.htm",
        "U.S. SEC / Tesla",
        {"shares": 2650000, "offering_price": 767.0, "gross_proceeds_usd_mm": 2032.55, "underwriting_discount_usd_mm": 23.90, "net_before_expenses_usd_mm": 2008.65},
    )
    amc_2020 = source(
        "AMC Entertainment 2020 Form 10-K",
        "https://www.sec.gov/Archives/edgar/data/1411579/000141157921000006/amc-20201231x10k.htm",
        "U.S. SEC / AMC Entertainment",
        {"backstop_shares": 5000000, "mudrick_shares": 21978022, "new_notes_usd_mm": 100.0, "debt_exchange_usd_mm": 104.5},
    )
    cases["12"] = [
        # This override list is a summary, not the governing manifest -- the
        # real one (standards/public_cases/equity-public-tesla-2020-offering.json)
        # also sets Cap Table & Dilution!C5/C7/C11/C12 with the real share
        # count, issue price, and existing-share count. C8=0.0 below is listed
        # explicitly because its absence was a real, verified defect: Tesla's
        # raise was a straight primary offering, not a rights offering, but
        # 'Rights Offering'!C6 reads Cap Table!C8, which was left at the
        # template default of 25 -- producing a fabricated ~$19.2bn "Expected
        # net rights proceeds" on the Decision & Checks dashboard (confirmed
        # via LibreOffice recalc) that no automated check caught, since the
        # dashboard's checks are internal identities, not magnitude bounds.
        case(
            "equity-public-tesla-2020-offering",
            "conventional",
            "12_Equity_Finance/instances/public_tesla_2020_offering.xlsx",
            "Tesla February 2020 underwritten primary offering",
            "2020-02-14",
            [tesla_offering],
            [
                override("Rights Offering", "C7", 767.0, "observed", tesla_offering["name"]),
                override("Rights Offering", "C8", 767.0, "observed", tesla_offering["name"]),
                override("Rights Offering", "C9", 1.0, "derived", tesla_offering["name"]),
                override("Rights Offering", "C10", 0.01176, "derived", tesla_offering["name"]),
                override("Cap Table & Dilution", "C8", 0.0, "observed", tesla_offering["name"]),
            ],
            "net_proceeds_before_expenses_usd_mm",
            2032.55,
            2008.65,
            "Tesla February 2020 Final Prospectus",
            "point_forecast",
        ),
        case(
            "equity-public-amc-2020-dilution",
            "adversarial",
            "12_Equity_Finance/instances/public_amc_2020_dilution.xlsx",
            "AMC 2020 emergency equity and debt financing",
            "2020-12-31",
            [amc_2020],
            [
                override("Rights Offering", "D9", 0.196, "derived", amc_2020["name"]),
            ],
            "emergency_financing_completed",
            1.0,
            1.0,
            "AMC Entertainment 2020 Form 10-K",
            # hindsight_restated_fact, not point_forecast: AMC's completion of
            # its 2020 emergency financing is a known, already-disclosed fact
            # in the same 10-K used as both "forecast" and "realized" -- there
            # was never an independent prediction to miss.
            "hindsight_restated_fact",
        ),
    ]

    eia_2023 = source(
        "EIA Cushing stocks and WTI annual prices",
        "https://www.eia.gov/dnav/pet/PET_PRI_SPT_S1_A.htm",
        "U.S. Energy Information Administration",
        {"wti_2023_average_usd_per_bbl": 77.58, "cushing_2023_year_end_stocks_mm_bbl": 34.454},
    )
    eia_2020 = source(
        "EIA April 2020 negative WTI and storage analysis",
        "https://www.eia.gov/todayinenergy/detail.php?id=43495",
        "U.S. Energy Information Administration",
        {"may_contract_settlement_usd_per_bbl": -37.63, "june_contract_price_usd_per_bbl": 20.43, "cushing_stocks_mm_bbl": 60.0, "storage_utilization": 0.76},
    )
    eia_recovery = source(
        "EIA July 2020 oil-price recovery",
        "https://www.eia.gov/todayinenergy/detail.php?id=46336",
        "U.S. Energy Information Administration",
        {"wti_price_2020_07_01_usd_per_bbl": 40.0},
    )
    cases["15"] = [
        case(
            "commodities-public-wti-2023",
            "conventional",
            "15_Commodities/instances/public_wti_2023.xlsx",
            "WTI 2023 price and Cushing inventory case",
            "2023-12-31",
            [eia_2023],
            [
                override("Hedging", "C7", 77.58, "observed", eia_2023["name"]),
                override("Physical Balance & Carry", "C14", 34.454, "observed", eia_2023["name"]),
            ],
            "next_year_wti_average_usd_per_bbl",
            75.0,
            None,
            "Pending maintained annual EIA evidence refresh",
            "point_forecast",
        ),
        case(
            "commodities-public-wti-april-2020",
            "adversarial",
            "15_Commodities/instances/public_wti_april_2020.xlsx",
            "April 2020 WTI expiry, demand and storage dislocation",
            "2020-04-20",
            [eia_2020, eia_recovery],
            [
                override("Hedging", "C7", -37.63, "observed", eia_2020["name"]),
                override("Hedging", "C8", 20.43, "observed", eia_2020["name"]),
                override("Physical Balance & Carry", "D14", 60.0, "observed", eia_2020["name"]),
                override("Physical Balance & Carry", "D18", 0.76, "observed", eia_2020["name"]),
            ],
            "wti_price_by_2020_07_01_usd_per_bbl",
            0.0,
            40.0,
            "EIA July 2020 oil-price recovery",
            "point_forecast",
        ),
    ]

    coinbase_2023 = source(
        "Coinbase 2023 Form 10-K",
        "https://www.sec.gov/Archives/edgar/data/1679788/000167978824000022/coin-20231231.htm",
        "U.S. SEC / Coinbase",
        {"total_customer_assets_usd_bn": 197.154, "customer_custodial_funds_usd_bn": 4.571, "consumer_and_institutional_staking_usd_bn": 16.8},
    )
    coinbase_q1_2024 = source(
        "Coinbase Q1 2024 Form 10-Q",
        "https://www.sec.gov/Archives/edgar/data/1679788/000167978824000089/coin-20240331.htm",
        "U.S. SEC / Coinbase",
        {"total_customer_assets_usd_bn": 334.708},
    )
    coinbase_2022 = source(
        "Coinbase 2023 Form 10-K comparative 2022 custody data",
        "https://www.sec.gov/Archives/edgar/data/1679788/000167978824000022/coin-20231231.htm",
        "U.S. SEC / Coinbase",
        {"total_customer_assets_usd_bn": 80.454, "customer_custodial_funds_usd_bn": 5.041, "safeguarded_crypto_usd_bn": 75.413},
    )
    cases["16"] = [
        case(
            "crypto-public-coinbase-2023",
            "conventional",
            "16_Crypto_Digital_Assets/instances/public_coinbase_2023.xlsx",
            "Coinbase 2023 custody and staking scale",
            "2023-12-31",
            [coinbase_2023, coinbase_q1_2024],
            [
                override("Valuation", "C6", 197.154, "observed", coinbase_2023["name"]),
                override("Valuation", "C7", 4.571, "observed", coinbase_2023["name"]),
                override("Valuation", "C8", 16.8, "derived", coinbase_2023["name"]),
                override("Staking Yield", "C6", 16.8, "derived", coinbase_2023["name"]),
            ],
            "next_quarter_total_customer_assets_usd_bn",
            220.0,
            334.708,
            "Coinbase Q1 2024 Form 10-Q",
            "point_forecast",
        ),
        case(
            "crypto-public-coinbase-2022-stress",
            "adversarial",
            "16_Crypto_Digital_Assets/instances/public_coinbase_2022_stress.xlsx",
            "Coinbase 2022 crypto-winter custody contraction",
            "2022-12-31",
            [coinbase_2022, coinbase_2023],
            [
                override("Valuation", "C6", 80.454, "observed", coinbase_2022["name"]),
                override("Valuation", "C7", 5.041, "observed", coinbase_2022["name"]),
                override("Valuation", "C8", 75.413, "observed", coinbase_2022["name"]),
            ],
            "next_year_total_customer_assets_usd_bn",
            100.0,
            197.154,
            "Coinbase 2023 Form 10-K",
            "point_forecast",
        ),
    ]

    realty_2023 = source(
        "Realty Income 2023 FFO reconciliation",
        "https://www.sec.gov/Archives/edgar/data/726728/000072672825000080/o-20250326.htm",
        "U.S. SEC / Realty Income",
        {"net_income_common_usd_mm": 872.309, "depreciation_amortization_usd_mm": 1895.177, "gain_on_sales_usd_mm": 25.667, "net_income_2024_usd_mm": 847.893},
    )
    wework_2022 = source(
        "WeWork 2022 Form 10-K",
        "https://www.sec.gov/Archives/edgar/data/1813756/000181375623000016/we-20221231.htm",
        "U.S. SEC / WeWork",
        {"revenue_usd_mm": 3245.0, "operating_margin_proxy": -0.65, "net_loss_usd_mm": 2034.0},
    )
    cases["17"] = [
        case(
            "real-estate-public-realty-income-2023",
            "conventional",
            "17_Real_Estate_REIT/instances/public_realty_income_2023.xlsx",
            "Realty Income 2023 simplified FFO bridge",
            "2023-12-31",
            [realty_2023],
            [
                override("REIT FFO-AFFO", "C4", 872.309, "observed", realty_2023["name"]),
                override("REIT FFO-AFFO", "C5", 1895.177, "observed", realty_2023["name"]),
                override("REIT FFO-AFFO", "C6", 25.667, "observed", realty_2023["name"]),
            ],
            "next_year_net_income_common_usd_mm",
            900.0,
            847.893,
            "Realty Income 2024 public reconciliation",
            "point_forecast",
        ),
        case(
            "real-estate-public-wework-2022-stress",
            "adversarial",
            "17_Real_Estate_REIT/instances/public_wework_2022_stress.xlsx",
            "WeWork 2022 occupancy-economics and refinancing stress proxy",
            "2022-12-31",
            [wework_2022],
            [
                override("Property Pro Forma", "C5", 3245.0, "observed", wework_2022["name"]),
                override("Property Pro Forma", "C10", 5354.25, "derived", wework_2022["name"]),
                override("REIT FFO-AFFO", "C4", -2034.0, "observed", wework_2022["name"]),
                override("REIT FFO-AFFO", "C5", 0.0, "modeler_assumption", "Flexible-office FFO proxy normalization"),
                override("REIT FFO-AFFO", "C6", 0.0, "modeler_assumption", "Flexible-office FFO proxy normalization"),
            ],
            "bankruptcy_within_12_months",
            1.0,
            1.0,
            "WeWork Chapter 11 filing, November 2023",
            # hindsight_restated_fact: WeWork's Chapter 11 filing is a known
            # historical fact restated as "forecast" -- no independent
            # prediction was made before it. Still legitimate evidence that
            # this adversarial case is grounded in a real distress event, not
            # a hypothetical one, but not forecast evidence.
            "hindsight_restated_fact",
        ),
    ]

    visa_2023 = source(
        "Visa 2023 Form 10-K",
        "https://www.sec.gov/Archives/edgar/data/1403161/000140316123000099/v-20230930.htm",
        "U.S. SEC / Visa",
        {"payments_and_cash_volume_usd_bn": 15000.0, "transactions_bn": 276.0, "credentials_bn": 4.3, "merchant_locations_m": 130.0},
    )
    visa_2024 = source(
        "Visa 2024 Form 10-K",
        "https://www.sec.gov/Archives/edgar/data/1403161/000140316124000058/v-20240930.htm",
        "U.S. SEC / Visa",
        {"payments_and_cash_volume_usd_bn": 16000.0, "transactions_bn": 303.0, "credentials_bn": 4.6, "merchant_locations_m": 150.0},
    )
    fis_2023 = source(
        "FIS 2023 Form 10-K and Worldpay disposal",
        "https://www.sec.gov/Archives/edgar/data/1136893/000113689324000015/fis-20231231.htm",
        "U.S. SEC / FIS",
        {"worldpay_goodwill_impairment_usd_bn": 6.8, "held_for_sale_allowance_usd_bn": 1.9, "expected_net_proceeds_usd_bn": 11.7, "transaction_value_up_to_usd_bn": 18.5},
    )
    cases["23"] = [
        case(
            "fintech-public-visa-2023",
            "conventional",
            "23_Fintech_Payments/instances/public_visa_2023.xlsx",
            "Visa 2023 global network scale",
            "2023-09-30",
            [visa_2023, visa_2024],
            [
                override("Unit Economics", "C5", 15000.0, "observed", visa_2023["name"]),
                override("Network & Cohorts", "C5", 4300.0, "observed", visa_2023["name"]),
                override("Network & Cohorts", "C8", 130.0, "observed", visa_2023["name"]),
                override("Network & Cohorts", "C11", 276000.0, "observed", visa_2023["name"]),
            ],
            "next_year_payments_and_cash_volume_usd_bn",
            16000.0,
            16000.0,
            "Visa 2024 Form 10-K",
            # hindsight_restated_fact: forecast (16000.0) was copied straight
            # from visa_2024["captured_values"]["payments_and_cash_volume_usd_bn"]
            # -- the exact same field cited for realized -- rather than derived
            # independently (e.g. from a trailing growth rate off visa_2023's
            # own 15000.0). Same defect class as the BlackRock 2023 case fixed
            # elsewhere in this registry, but here there's no clean workbook
            # formula to substitute a genuine derived forecast, so it's
            # labeled honestly instead.
            "hindsight_restated_fact",
        ),
        case(
            "fintech-public-fis-worldpay-2023-stress",
            "adversarial",
            "23_Fintech_Payments/instances/public_fis_worldpay_2023_stress.xlsx",
            "FIS Worldpay impairment, disposal and capital-recovery stress proxy",
            "2023-12-31",
            [fis_2023],
            [
                override("Capital & Liquidity", "D5", 11.7, "observed", fis_2023["name"]),
                override("Capital & Liquidity", "D6", 8.7, "derived", fis_2023["name"]),
            ],
            "worldpay_sale_closed_within_12_months",
            1.0,
            1.0,
            "FIS Worldpay sale closed January 31, 2024",
            # hindsight_restated_fact: the sale's closing is a known fact
            # restated as "forecast" -- no independent prediction was made.
            "hindsight_restated_fact",
        ),
    ]

    hertz_2021 = source(
        "Hertz 2021 Form 10-K",
        "https://www.sec.gov/Archives/edgar/data/1657853/000165785322000012/htz-20211231.htm",
        "U.S. SEC / Hertz",
        {"emergence_cash_usd_bn": 7.5, "sponsor_common_equity_usd_bn": 2.8, "rights_offering_usd_bn": 1.6, "preferred_equity_usd_bn": 1.5, "term_loan_usd_bn": 1.5},
    )
    bbby_2022 = source(
        "Bed Bath & Beyond Q2 2022 Form 10-Q",
        "https://www.sec.gov/Archives/edgar/data/886158/000088615822000150/bbby-20220827.htm",
        "U.S. SEC / Bed Bath & Beyond",
        {"cash_usd_mm": 166.7, "six_month_operating_cash_use_usd_mm": 582.4, "post_facility_borrowing_availability_usd_mm": 690.0},
    )
    bbby_bankruptcy = source(
        "Bed Bath & Beyond 2022 Form 10-K and Chapter 11 disclosure",
        "https://www.sec.gov/Archives/edgar/data/886158/000088615823000059/bbby-20230225.htm",
        "U.S. SEC / Bed Bath & Beyond",
        {"chapter_11_filing_date": "2023-04-23"},
    )
    cases["24"] = [
        case(
            "distressed-public-hertz-2021-reorganization",
            "conventional",
            "24_Distressed_Restructuring/instances/public_hertz_2021_reorganization.xlsx",
            "Hertz Chapter 11 emergence financing and recovery",
            "2021-06-30",
            [hertz_2021],
            [
                override("New Money", "C5", 7500.0, "observed", hertz_2021["name"]),
            ],
            "chapter_11_emergence_completed",
            1.0,
            1.0,
            "Hertz 2021 Form 10-K",
            # hindsight_restated_fact: Hertz's emergence from Chapter 11 is a
            # known historical fact restated as "forecast" -- no independent
            # prediction was made before it.
            "hindsight_restated_fact",
        ),
        case(
            "distressed-public-bbby-2022-liquidity",
            "adversarial",
            "24_Distressed_Restructuring/instances/public_bbby_2022_liquidity.xlsx",
            "Bed Bath & Beyond 2022 liquidity deterioration",
            "2022-08-27",
            [bbby_2022, bbby_bankruptcy],
            [
                override("13-Week Liquidity", "C3", 166.7, "observed", bbby_2022["name"]),
                override("New Money", "C5", 690.0, "observed", bbby_2022["name"]),
            ],
            "chapter_11_filing_within_12_months",
            1.0,
            1.0,
            "Bed Bath & Beyond Chapter 11 filing, April 23, 2023",
            # hindsight_restated_fact: BBBY's Chapter 11 filing is a known
            # historical fact restated as "forecast" -- no independent
            # prediction was made before it. Both of model 24's cases are
            # hindsight_restated_fact, so Distressed & Restructuring currently
            # has zero genuine forecast evidence -- tracked in
            # KNOWN_HINDSIGHT_ONLY_MODELS below, same as model 23 Fintech.
            "hindsight_restated_fact",
        ),
    ]

    flagships = []
    for model_id in ("08", "10", "11", "12", "15", "16", "17", "23", "24"):
        meta = MODEL_META[model_id]
        flagships.append(
            {
                "model_id": model_id,
                "domain": meta["domain"],
                "folder": meta["folder"],
                "version": "2.2.0-evidence",
                "risk_tier": meta["risk_tier"],
                "approved_uses": meta["approved_uses"],
                "prohibited_uses": COMMON_PROHIBITED,
                "limitations": meta["limitations"],
                "validation_conclusion": "Engineering evidence approved with limitations at M2; named stakeholder approval and maintained operating history remain mandatory for M3/M4",
                "monitoring": meta["monitoring"],
                "rollback_release": "m2-release-2.2.0",
                "retirement_trigger": meta["retirement_trigger"],
                "cases": cases[model_id],
            }
        )
    return {
        "schema_version": "1.0",
        "as_of": AS_OF,
        "promotion_policy": {
            "m3_requires": [
                "completed_model_card",
                "independent_validation",
                "frozen_external_sources",
                "conventional_public_case",
                "adversarial_public_case",
                "stakeholder_signoff",
                "material_refresh_history",
                "outcomes_analysis",
            ],
            "m4_requires": [
                "m3_approved",
                "two_maintained_public_instances",
                "monitoring_and_escalation",
                "multi_release_outcome_history",
                "rollback_replacement_retirement_evidence",
            ],
            "engineering_test_vectors_count_toward_m4": False,
        },
        "flagships": flagships,
    }
