"""Public historical evidence registry for the final six governed M2 domains."""
from __future__ import annotations

from typing import Any

try:
    from tools.frontier_evidence_registry import (
        COMMON_PROHIBITED,
        case,
        override,
        source,
    )
except ModuleNotFoundError:
    from frontier_evidence_registry import COMMON_PROHIBITED, case, override, source

AS_OF = "2026-08-04"

MODEL_META: dict[str, dict[str, Any]] = {
    "01": {
        "domain": "Investment Banking",
        "folder": "01_Investment_Banking",
        "risk_tier": "Tier 1",
        "approved_uses": [
            "Transaction valuation and offer-premium diagnostics",
            "Accretion, dilution, synergy and financing stress",
            "Historical announced and completed transaction comparison",
        ],
        "limitations": [
            "Public merger consideration is simplified into a static transaction model",
            "Fairness, tax, legal, regulatory and purchase-accounting conclusions require transaction-specific diligence",
            "Unsourced DCF, synergy, financing and share-issuance cells remain modeler assumptions",
        ],
        "monitoring": [
            {"metric": "offer_premium", "warning": 0.30, "breach": 0.50, "action": "Reconcile unaffected price, control premium and synergy support"},
            {"metric": "eps_accretion", "warning": 0.00, "breach": -0.10, "action": "Escalate financing, synergy and share-issuance assumptions"},
        ],
        "retirement_trigger": "Transaction terms, capital structure, forecasts, or closing conditions are superseded",
    },
    "02": {
        "domain": "Corporate Finance",
        "folder": "02_Corporate_Finance",
        "risk_tier": "Tier 1",
        "approved_uses": [
            "Treasury, liquidity and capital-allocation diagnostics",
            "Leverage, coverage and shareholder-distribution stress",
            "Historical public-company cash deployment comparison",
        ],
        "limitations": [
            "Annual public statements do not replace a daily treasury forecast",
            "Debt issuance and repayment values aggregate multiple instruments",
            "Minimum cash, leverage and coverage thresholds remain policy assumptions unless separately approved",
        ],
        "monitoring": [
            {"metric": "minimum_cash_headroom", "warning": 0.20, "breach": 0.00, "action": "Escalate funding, capex and shareholder-distribution plan"},
            {"metric": "net_leverage", "warning": 3.0, "breach": 3.5, "action": "Re-underwrite capital structure and deleveraging path"},
        ],
        "retirement_trigger": "Capital allocation, liquidity policy, debt structure or operating plan changes materially",
    },
    "05": {
        "domain": "Private Credit",
        "folder": "05_Private_Credit",
        "risk_tier": "Tier 1",
        "approved_uses": [
            "Portfolio concentration and leverage diagnostics",
            "DSCR, PIK, amendment and recovery stress",
            "Historical performing and distressed credit comparison",
        ],
        "limitations": [
            "Public BDC and borrower disclosures are portfolio- or company-level proxies",
            "Recovery values require collateral appraisals, claim schedules and legal priority analysis",
            "CFADS, covenant and amendment cells remain assumptions unless explicitly sourced",
        ],
        "monitoring": [
            {"metric": "downside_dscr", "warning": 1.20, "breach": 1.00, "action": "Escalate amendment, liquidity and sponsor-support plan"},
            {"metric": "recovery_rate", "warning": 0.70, "breach": 0.60, "action": "Re-underwrite collateral, claims and restructuring alternatives"},
        ],
        "retirement_trigger": "Credit agreement, collateral, capital structure or operating case is superseded",
    },
    "06": {
        "domain": "Debt Finance",
        "folder": "06_Debt_Finance",
        "risk_tier": "Tier 1",
        "approved_uses": [
            "Debt rollforward, maturity and refinancing diagnostics",
            "Weighted-cost and interest-coverage stress",
            "Historical investment-grade and emergency-financing comparison",
        ],
        "limitations": [
            "Public debt balances aggregate secured, unsecured, fixed, floating and convertible instruments",
            "Maturity buckets and committed facilities require instrument-level confirmation",
            "Pricing, covenant and refinancing assumptions remain modeler-owned unless sourced",
        ],
        "monitoring": [
            {"metric": "refinancing_gap", "warning": 0.00, "breach": 1.00, "action": "Escalate maturity, liquidity and capital-markets plan"},
            {"metric": "interest_coverage", "warning": 2.50, "breach": 2.00, "action": "Re-underwrite earnings, rates and debt capacity"},
        ],
        "retirement_trigger": "Debt structure, maturity schedule, liquidity or refinancing plan is superseded",
    },
    "07": {
        "domain": "Public Finance",
        "folder": "07_Public_Finance",
        "risk_tier": "Tier 1",
        "approved_uses": [
            "Debt-sustainability and primary-balance diagnostics",
            "Debt-service and reserve-coverage stress",
            "Historical sovereign reform and distress comparison",
        ],
        "limitations": [
            "Sovereign ratios are simplified into a static fiscal-debt model",
            "Nominal interest, growth and debt-service paths require country-specific debt-stock detail",
            "IMF program projections are conditional scenarios rather than guarantees",
        ],
        "monitoring": [
            {"metric": "projected_debt_ratio", "warning": 0.90, "breach": 1.00, "action": "Escalate fiscal, financing and debt-treatment analysis"},
            {"metric": "primary_balance_gap", "warning": 0.00, "breach": -0.02, "action": "Re-underwrite revenue, expenditure and financing assumptions"},
        ],
        "retirement_trigger": "Fiscal framework, debt treatment, program assumptions or reporting basis changes materially",
    },
    "13": {
        "domain": "Venture Capital",
        "folder": "13_Venture_Capital",
        "risk_tier": "Tier 1",
        "approved_uses": [
            "Round pricing, ownership and dilution diagnostics",
            "Follow-on reserve and exit-return stress",
            "Historical up-round and down-round comparison",
        ],
        "limitations": [
            "IPO offerings are used as observable financing and valuation events",
            "Preferred terms, liquidation preferences, pro rata rights and option-pool treatment require executed documents",
            "Exit values and follow-on requirements remain modeler assumptions unless explicitly sourced",
        ],
        "monitoring": [
            {"metric": "reserve_gap", "warning": 0.00, "breach": 1.00, "action": "Escalate reserve allocation and ownership-defense plan"},
            {"metric": "round_price_change", "warning": 0.00, "breach": -0.25, "action": "Re-underwrite dilution, anti-dilution and portfolio marks"},
        ],
        "retirement_trigger": "Financing terms, ownership, reserve policy or exit assumptions are superseded",
    },
}


def registry() -> dict[str, Any]:
    cases: dict[str, list[dict[str, Any]]] = {}

    linkedin_2016 = source(
        "LinkedIn September 2016 Form 10-Q merger disclosure",
        "https://www.sec.gov/Archives/edgar/data/1271024/000127102416000059/a20160930-10qdocument.htm",
        "U.S. SEC / LinkedIn",
        {
            "cash_consideration_per_share_usd": 196.0,
            "transaction_value_including_net_cash_usd_mm": 26200.0,
            "implied_diluted_shares_mm": 133.673469,
        },
    )
    linkedin_close = source(
        "LinkedIn merger completion Form 8-K",
        "https://www.sec.gov/Archives/edgar/data/1271024/000110465916161289/a16-22816_18k.htm",
        "U.S. SEC / LinkedIn",
        {"merger_completed": 1},
    )
    hp_autonomy = source(
        "Hewlett-Packard 2012 Form 10-K Autonomy impairment",
        "https://www.sec.gov/Archives/edgar/data/47217/000104746912011417/a2211959z10-k.htm",
        "U.S. SEC / Hewlett-Packard",
        {
            "autonomy_purchase_price_usd_mm": 11100.0,
            "autonomy_impairment_usd_mm": 8800.0,
            "residual_value_after_impairment_usd_mm": 2300.0,
        },
    )
    cases["01"] = [
        case(
            "ib-public-microsoft-linkedin-2016",
            "conventional",
            "01_Investment_Banking/instances/public_microsoft_linkedin_2016.xlsx",
            "Microsoft acquisition of LinkedIn",
            "2016-12-08",
            [linkedin_2016, linkedin_close],
            [
                override("Transaction Analysis", "C5", 26200.0, "observed", linkedin_2016["name"]),
                override("Transaction Analysis", "C8", 133.673469, "derived", linkedin_2016["name"]),
                override("Transaction Analysis", "C9", 196.0, "observed", linkedin_2016["name"]),
            ],
            "transaction_completed",
            1.0,
            1.0,
            linkedin_close["name"],
            # hindsight_restated_fact: linkedin_close's own captured_values is
            # just {"merger_completed": 1} -- a fact restated as "forecast",
            # not an independent prediction.
            "hindsight_restated_fact",
        ),
        case(
            "ib-public-hp-autonomy-2012-stress",
            "adversarial",
            "01_Investment_Banking/instances/public_hp_autonomy_2012_stress.xlsx",
            "Hewlett-Packard Autonomy acquisition impairment",
            "2012-10-31",
            [hp_autonomy],
            [
                override("Transaction Analysis", "D5", 11100.0, "observed", hp_autonomy["name"]),
                override("Transaction Analysis", "D8", 1.0, "modeler_assumption", "Transaction normalization to one unit"),
                override("Transaction Analysis", "D9", 11100.0, "derived", hp_autonomy["name"]),
                override("Transaction Analysis", "D16", 2300.0, "derived", hp_autonomy["name"]),
            ],
            "impairment_usd_mm",
            0.0,
            8800.0,
            hp_autonomy["name"],
            "point_forecast",
        ),
    ]

    microsoft_2024 = source(
        "Microsoft 2024 Form 10-K",
        "https://www.sec.gov/Archives/edgar/data/789019/000095017024087843/msft-20240630.htm",
        "U.S. SEC / Microsoft",
        {
            "operating_cash_flow_usd_mm": 118548.0,
            "capital_expenditures_usd_mm": 44477.0,
            "dividends_usd_mm": 21771.0,
            "share_repurchases_usd_mm": 17254.0,
            "debt_issued_usd_mm": 24395.0,
            "debt_repaid_usd_mm": 29070.0,
            "cash_and_short_term_investments_usd_mm": 75543.0,
            "ending_debt_usd_mm": 67127.0,
            "derived_opening_debt_usd_mm": 71802.0,
        },
    )
    intel_2024 = source(
        "Intel second-quarter 2024 Form 10-Q",
        "https://www.sec.gov/Archives/edgar/data/50863/000005086324000124/intc-20240629.htm",
        "U.S. SEC / Intel",
        {
            "new_senior_notes_usd_mm": 2600.0,
            "remarketed_bonds_usd_mm": 438.0,
            "total_observed_new_debt_usd_mm": 3038.0,
            "quarterly_dividend_suspension_announced": 1,
        },
    )
    cases["02"] = [
        case(
            "corporate-public-microsoft-2024",
            "conventional",
            "02_Corporate_Finance/instances/public_microsoft_2024.xlsx",
            "Microsoft FY2024 treasury and capital allocation",
            "2024-06-30",
            [microsoft_2024],
            [
                override("Treasury & Liquidity", "C6", 118548.0, "observed", microsoft_2024["name"]),
                override("Treasury & Liquidity", "C7", 44477.0, "observed", microsoft_2024["name"]),
                override("Treasury & Liquidity", "C8", 21771.0, "observed", microsoft_2024["name"]),
                override("Treasury & Liquidity", "C9", 17254.0, "observed", microsoft_2024["name"]),
                override("Treasury & Liquidity", "C10", 24395.0, "observed", microsoft_2024["name"]),
                override("Treasury & Liquidity", "C11", 29070.0, "observed", microsoft_2024["name"]),
                override("Treasury & Liquidity", "C12", 71802.0, "derived", microsoft_2024["name"]),
            ],
            "ending_cash_and_short_term_investments_usd_mm",
            75000.0,
            75543.0,
            microsoft_2024["name"],
            "point_forecast",
        ),
        case(
            "corporate-public-intel-2024-stress",
            "adversarial",
            "02_Corporate_Finance/instances/public_intel_2024_stress.xlsx",
            "Intel 2024 debt issuance and capital-allocation reset",
            "2024-06-29",
            [intel_2024],
            [
                override("Treasury & Liquidity", "D10", 3038.0, "derived", intel_2024["name"]),
                override("Treasury & Liquidity", "D8", 0.0, "derived", intel_2024["name"]),
            ],
            "quarterly_dividend_suspended",
            0.0,
            1.0,
            intel_2024["name"],
            "point_forecast",
        ),
    ]

    ares_2024 = source(
        "Ares Capital 2024 Form 10-K",
        "https://www.sec.gov/Archives/edgar/data/1287750/000128775025000012/arcc-20241231.htm",
        "U.S. SEC / Ares Capital",
        {
            "investment_portfolio_fair_value_usd_mm": 26720.0,
            "derived_top_five_exposures_usd_mm": [9352.0, 6680.0, 5344.0, 3206.4, 2137.6],
        },
    )
    ares_q2_2025 = source(
        "Ares Capital second-quarter 2025 Form 10-Q",
        "https://www.sec.gov/Archives/edgar/data/1287750/000128775025000050/arcc-20250630.htm",
        "U.S. SEC / Ares Capital",
        {"investment_portfolio_fair_value_usd_mm": 27886.1},
    )
    yellow_2022 = source(
        "Yellow Corporation 2022 annual report",
        "https://www.sec.gov/Archives/edgar/data/716006/000119312522064324/d186462dars.pdf",
        "U.S. SEC / Yellow Corporation",
        {
            "cash_and_cash_equivalents_usd_mm": 235.1,
            "minimum_trailing_twelve_month_adjusted_ebitda_covenant_usd_mm": 200.0,
        },
    )
    yellow_bankruptcy = source(
        "Yellow Corporation bankruptcy Form 8-K filing index",
        "https://www.sec.gov/Archives/edgar/data/716006/0001193125-23-204370-index.htm",
        "U.S. SEC / Yellow Corporation",
        {"chapter_11_filing_date": "2023-08-06", "chapter_11_filed": 1},
    )
    cases["05"] = [
        case(
            "credit-public-ares-2024",
            "conventional",
            "05_Private_Credit/instances/public_ares_2024.xlsx",
            "Ares Capital 2024 investment portfolio",
            "2024-12-31",
            [ares_2024, ares_q2_2025],
            [
                override("Portfolio & Concentration", "C5", 9352.0, "derived", ares_2024["name"]),
                override("Portfolio & Concentration", "C6", 6680.0, "derived", ares_2024["name"]),
                override("Portfolio & Concentration", "C7", 5344.0, "derived", ares_2024["name"]),
                override("Portfolio & Concentration", "C8", 3206.4, "derived", ares_2024["name"]),
                override("Portfolio & Concentration", "C9", 2137.6, "derived", ares_2024["name"]),
            ],
            "next_reported_portfolio_fair_value_usd_mm",
            27000.0,
            27886.1,
            ares_q2_2025["name"],
            "point_forecast",
        ),
        case(
            "credit-public-yellow-2022-stress",
            "adversarial",
            "05_Private_Credit/instances/public_yellow_2022_stress.xlsx",
            "Yellow Corporation pre-bankruptcy liquidity and covenant stress",
            "2022-12-31",
            [yellow_2022, yellow_bankruptcy],
            [
                override("Amendment Economics", "D9", 200.0, "derived", yellow_2022["name"]),
                override("Amendment Economics", "D12", 235.1, "observed", yellow_2022["name"]),
            ],
            "chapter_11_filed_within_twelve_months",
            0.0,
            1.0,
            yellow_bankruptcy["name"],
            "point_forecast",
        ),
    ]

    carnival_2020 = source(
        "Carnival 2020 Form 10-K",
        "https://www.sec.gov/Archives/edgar/data/815097/000081509721000012/ccl-20201130.htm",
        "U.S. SEC / Carnival",
        {
            "available_liquidity_usd_mm": 9500.0,
            "senior_secured_notes_usd_mm": 4000.0,
            "convertible_notes_usd_mm": 1750.0,
            "observed_emergency_debt_issuance_usd_mm": 5750.0,
        },
    )
    cases["06"] = [
        case(
            "debt-public-microsoft-2024",
            "conventional",
            "06_Debt_Finance/instances/public_microsoft_2024.xlsx",
            "Microsoft FY2024 debt and liquidity profile",
            "2024-06-30",
            [microsoft_2024],
            [
                override("Refinancing & Rates", "C5", 71802.0, "derived", microsoft_2024["name"]),
                override("Refinancing & Rates", "C6", 24395.0, "observed", microsoft_2024["name"]),
                override("Refinancing & Rates", "C7", 29070.0, "observed", microsoft_2024["name"]),
                override("Refinancing & Rates", "C13", 75543.0, "observed", microsoft_2024["name"]),
            ],
            "ending_debt_usd_mm",
            70000.0,
            67127.0,
            microsoft_2024["name"],
            "point_forecast",
        ),
        case(
            "debt-public-carnival-2020-stress",
            "adversarial",
            "06_Debt_Finance/instances/public_carnival_2020_stress.xlsx",
            "Carnival 2020 emergency debt financing",
            "2020-11-30",
            [carnival_2020],
            [
                override("Refinancing & Rates", "D6", 5750.0, "derived", carnival_2020["name"]),
                override("Refinancing & Rates", "D13", 9500.0, "observed", carnival_2020["name"]),
                override("Refinancing & Rates", "D15", 4000.0, "observed", carnival_2020["name"]),
                override("Refinancing & Rates", "D17", 1750.0, "observed", carnival_2020["name"]),
            ],
            "emergency_debt_issued_usd_mm",
            0.0,
            5750.0,
            carnival_2020["name"],
            "point_forecast",
        ),
    ]

    jamaica_2024 = source(
        "IMF Jamaica 2024 Article IV Consultation and second reviews",
        "https://www.imf.org/en/publications/cr/issues/2024/03/08/jamaica-2024-article-iv-consultation-and-second-reviews-under-the-arrangement-under-the-545715",
        "International Monetary Fund",
        {
            "public_debt_to_gdp": 0.75,
            "primary_surplus_to_gdp": 0.057,
            "nominal_growth_assumption": 0.08,
            "nominal_interest_assumption": 0.07,
            "review_completed": 1,
        },
    )
    sri_lanka_2023 = source(
        "IMF Sri Lanka 2023 EFF request and debt-sustainability analysis",
        "https://www.elibrary.imf.org/view/journals/002/2023/116/article-A001-en.xml",
        "International Monetary Fund",
        {
            "public_debt_to_gdp_2022": 1.281,
            "primary_balance_to_gdp_2022": -0.038,
            "real_growth_projection_2023": -0.03,
            "eff_approved": 1,
        },
    )
    cases["07"] = [
        case(
            "public-finance-jamaica-2024",
            "conventional",
            "07_Public_Finance/instances/public_jamaica_2024.xlsx",
            "Jamaica 2024 debt-reduction and fiscal-resilience case",
            "2024-03-08",
            [jamaica_2024],
            [
                override("Revenue Stress", "C5", 0.75, "observed", jamaica_2024["name"]),
                override("Revenue Stress", "C6", 0.07, "derived", jamaica_2024["name"]),
                override("Revenue Stress", "C7", 0.08, "derived", jamaica_2024["name"]),
                override("Revenue Stress", "C8", 0.057, "observed", jamaica_2024["name"]),
            ],
            "imf_review_completed",
            1.0,
            1.0,
            jamaica_2024["name"],
            # hindsight_restated_fact: jamaica_2024's own captured_values
            # already includes "review_completed": 1 -- a fact restated as
            # "forecast", not an independent prediction.
            "hindsight_restated_fact",
        ),
        case(
            "public-finance-sri-lanka-2023-stress",
            "adversarial",
            "07_Public_Finance/instances/public_sri_lanka_2023_stress.xlsx",
            "Sri Lanka sovereign debt-distress and IMF program case",
            "2023-03-20",
            [sri_lanka_2023],
            [
                override("Revenue Stress", "D5", 1.281, "observed", sri_lanka_2023["name"]),
                override("Revenue Stress", "D8", -0.038, "observed", sri_lanka_2023["name"]),
            ],
            "imf_extended_fund_facility_approved",
            0.0,
            1.0,
            sri_lanka_2023["name"],
            "point_forecast",
        ),
    ]

    snowflake_2020 = source(
        "Snowflake 2020 final IPO prospectus",
        "https://www.sec.gov/Archives/edgar/data/1640147/000162828020013667/snowflake424b4.htm",
        "U.S. SEC / Snowflake",
        {
            "ipo_shares_mm": 28.0,
            "ipo_price_per_share_usd": 120.0,
            "gross_primary_proceeds_usd_mm": 3360.0,
            "derived_pre_money_value_usd_mm": 30000.0,
            "derived_existing_shares_mm": 250.0,
            "ipo_completed": 1,
        },
    )
    instacart_2023 = source(
        "Maplebear 2023 final IPO prospectus",
        "https://www.sec.gov/Archives/edgar/data/1579091/000119312523237900/d55348d424b4.htm",
        "U.S. SEC / Maplebear",
        {
            "total_offered_shares_mm": 22.0,
            "primary_shares_mm": 14.1,
            "ipo_price_per_share_usd": 30.0,
            "gross_primary_proceeds_usd_mm": 423.0,
            "prior_private_valuation_usd_mm": 39000.0,
            "derived_existing_shares_mm": 285.9,
            "down_round": 1,
        },
    )
    cases["13"] = [
        case(
            "vc-public-snowflake-2020",
            "conventional",
            "13_Venture_Capital/instances/public_snowflake_2020.xlsx",
            "Snowflake 2020 IPO financing",
            "2020-09-16",
            [snowflake_2020],
            [
                override("Ownership & Dilution", "C5", 30000.0, "derived", snowflake_2020["name"]),
                override("Ownership & Dilution", "C6", 3360.0, "derived", snowflake_2020["name"]),
                override("Ownership & Dilution", "C7", 250.0, "derived", snowflake_2020["name"]),
                override("Ownership & Dilution", "C8", 28.0, "observed", snowflake_2020["name"]),
            ],
            "ipo_completed",
            1.0,
            1.0,
            snowflake_2020["name"],
            # hindsight_restated_fact: snowflake_2020's own captured_values
            # already includes "ipo_completed": 1 -- the case's source is the
            # final IPO prospectus itself, so "forecast" restates a fact the
            # source already confirms, not an independent prediction.
            "hindsight_restated_fact",
        ),
        case(
            "vc-public-instacart-2023-down-round",
            "adversarial",
            "13_Venture_Capital/instances/public_instacart_2023_down_round.xlsx",
            "Instacart 2023 IPO relative to prior private valuation",
            "2023-09-18",
            [instacart_2023],
            [
                override("Ownership & Dilution", "D5", 39000.0, "observed", instacart_2023["name"]),
                override("Ownership & Dilution", "D6", 423.0, "derived", instacart_2023["name"]),
                override("Ownership & Dilution", "D7", 285.9, "derived", instacart_2023["name"]),
                override("Ownership & Dilution", "D8", 14.1, "observed", instacart_2023["name"]),
            ],
            "down_round_relative_to_prior_private_valuation",
            0.0,
            1.0,
            instacart_2023["name"],
            "point_forecast",
        ),
    ]

    flagships = []
    for model_id in ("01", "02", "05", "06", "07", "13"):
        meta = MODEL_META[model_id]
        flagships.append(
            {
                "model_id": model_id,
                "domain": meta["domain"],
                "folder": meta["folder"],
                "version": "3.0.0-evidence",
                "risk_tier": meta["risk_tier"],
                "approved_uses": meta["approved_uses"],
                "prohibited_uses": COMMON_PROHIBITED,
                "limitations": meta["limitations"],
                "validation_conclusion": (
                    "Engineering and historical public evidence approved with limitations at M2; "
                    "named stakeholder approval and maintained operating history remain mandatory for M3/M4"
                ),
                "monitoring": meta["monitoring"],
                "rollback_release": "m2-frontier-release-3.0.0",
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
