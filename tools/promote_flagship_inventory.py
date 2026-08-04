"""Promote validated flagship builder contracts in the model inventory."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROMOTIONS: dict[str, dict[str, Any]] = {
    "03": {
        "builder": "tools/builders/build_lbo_release.py",
        "maturity": "M2",
        "engines": [
            "operating_model", "sources_uses", "working_capital", "tax",
            "revolver", "multi_tranche_debt", "pik", "cash_sweep",
            "covenants", "management_equity", "exit_waterfall", "sensitivity",
        ],
        "perspectives": ["sponsor", "lender", "management", "lp_ic"],
        "checks": [
            "sources_uses_balance", "debt_schedule_conservation",
            "cash_minimum", "covenant_headroom", "waterfall_conservation",
            "returns_identity",
        ],
    },
    "04": {
        "builder": "tools/builders/build_lbo_release.py",
        "maturity": "M2",
        "engines": [
            "operating_model", "sources_uses", "working_capital", "tax",
            "revolver", "multi_tranche_debt", "pik", "cash_sweep",
            "covenants", "management_equity", "exit_waterfall", "sensitivity",
        ],
        "perspectives": ["principal", "lender", "management", "investment_committee"],
        "checks": [
            "sources_uses_balance", "debt_schedule_conservation",
            "cash_minimum", "covenant_headroom", "waterfall_conservation",
            "returns_identity",
        ],
    },
    "09": {
        "builder": "tools/builders/build_risk_institutional.py",
        "maturity": "M2",
        "engines": [
            "position_inventory", "factor_covariance", "var", "expected_shortfall",
            "stress_testing", "liquidity_risk", "pnl_explain", "limit_monitoring",
        ],
        "perspectives": ["trader", "risk", "management", "regulator"],
        "checks": [
            "covariance_bounds", "variance_nonnegative",
            "expected_shortfall_var_order", "limit_headroom",
        ],
    },
    "14": {
        "builder": "tools/builders/build_options_institutional.py",
        "maturity": "M2",
        "engines": [
            "black_scholes", "implied_volatility", "american_option",
            "volatility_surface", "portfolio_greeks", "scenario_pnl",
            "strategy_payoff",
        ],
        "perspectives": ["trader", "market_maker", "risk", "portfolio_manager"],
        "checks": [
            "put_call_parity", "implied_volatility_convergence",
            "option_price_bounds", "greek_signs", "american_european_bound",
        ],
    },
    "18": {
        "builder": "tools/builders/build_insurance_release.py",
        "maturity": "M2",
        "engines": [
            "paid_triangle", "chain_ladder", "bornhuetter_ferguson",
            "underwriting", "embedded_value", "capital_requirement",
            "stress_testing",
        ],
        "perspectives": ["actuary", "underwriter", "management", "regulator", "rating_agency"],
        "checks": [
            "triangle_monotonicity", "development_factor_bounds",
            "reserve_nonnegative", "capital_coverage",
        ],
    },
    "19": {
        "builder": "tools/builders/build_securitization_institutional.py",
        "maturity": "M2",
        "engines": [
            "collateral_rollforward", "cpr_cdr", "recovery_lag",
            "interest_waterfall", "principal_waterfall", "oc_ic_triggers",
            "wal", "sensitivity",
        ],
        "perspectives": ["issuer", "investor", "servicer", "trustee", "rating_agency"],
        "checks": [
            "collateral_conservation", "waterfall_conservation",
            "tranche_balance_nonnegative", "wal_bounds",
        ],
    },
    "20": {
        "builder": "tools/builders/build_project_finance_institutional.py",
        "maturity": "M2",
        "engines": [
            "construction_draw", "interest_during_construction", "sources_uses",
            "operating_cfads", "debt_sculpting", "dsra", "dscr", "llcr",
            "plcr", "sensitivity",
        ],
        "perspectives": ["sponsor", "lender", "independent_engineer", "offtaker", "dfi"],
        "checks": [
            "sources_uses_balance", "construction_draw_conservation",
            "debt_schedule_conservation", "dscr_identity", "llcr_identity",
        ],
    },
    "21": {
        "builder": "tools/builders/build_fixed_income_release.py",
        "maturity": "M2",
        "engines": [
            "zero_curve", "bond_pricing", "duration", "convexity",
            "key_rate_dv01", "carry_roll", "curve_scenarios", "pnl_explain",
        ],
        "perspectives": ["trader", "portfolio_manager", "risk", "treasury"],
        "checks": [
            "price_yield_monotonicity", "duration_positive", "convexity_positive",
            "key_rate_reconciliation", "discount_factor_monotonicity",
        ],
    },
    "22": {
        "builder": "tools/builders/build_quant_institutional.py",
        "maturity": "M2",
        "engines": [
            "point_in_time_backtest", "walk_forward", "transaction_costs",
            "capacity", "performance", "var_es", "stress_testing",
            "backtest_live_controls",
        ],
        "perspectives": ["researcher", "portfolio_manager", "risk", "execution"],
        "checks": [
            "gross_net_order", "max_drawdown_identity", "var_es_order",
            "walk_forward_partition", "cost_monotonicity",
        ],
    },
}


def promote(inventory: dict[str, Any], *, version: str) -> dict[str, Any]:
    models = {item["id"]: item for item in inventory["models"]}
    missing = sorted(set(PROMOTIONS) - set(models))
    if missing:
        raise ValueError(f"inventory missing flagship IDs: {missing}")
    inventory["version"] = version
    for model_id, promotion in PROMOTIONS.items():
        model = models[model_id]
        model["builder"] = promotion["builder"]
        model["declared_maturity"] = promotion["maturity"]
        model["required_engines"] = promotion["engines"]
        model["required_perspectives"] = promotion["perspectives"]
        model["reference_checks"] = promotion["checks"]
    return inventory


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inventory", type=Path, nargs="?", default=Path("standards/model_inventory.json"))
    parser.add_argument("--version", default="2.1.0")
    args = parser.parse_args()
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    promote(inventory, version=args.version)
    args.inventory.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    print(f"promoted {len(PROMOTIONS)} flagship model contracts to inventory {args.version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
