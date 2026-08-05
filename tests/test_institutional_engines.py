from math import exp, isclose, isfinite
import unittest

from finance_segway.engines import (
    DebtTranche,
    OperatingAssumptions,
    Tranche,
    american_binomial,
    apply_transaction_costs,
    black_scholes,
    bond_price,
    build_debt_schedule,
    capacity_adjusted_returns,
    collateral_cash_flows,
    construction_draw_schedule,
    covenant_headroom,
    denominator_effect,
    expected_shortfall,
    forecast_operating,
    historical_var,
    implied_volatility,
    irr,
    key_rate_dv01,
    linear_zero_rate,
    liquidity_coverage,
    llcr,
    macaulay_duration,
    max_drawdown,
    modified_duration,
    numerical_convexity,
    recovery_waterfall,
    sculpt_debt_service,
    sequential_waterfall,
    sharpe_ratio,
    sortino_ratio,
    walk_forward_splits,
    weighted_average_life,
)


class EngineTests(unittest.TestCase):
    def test_operating_forecast_conservation(self):
        assumptions = OperatingAssumptions(
            revenue_growth=[0.1, 0.05],
            ebitda_margin=[0.2, 0.21],
            capex_pct_revenue=[0.03, 0.03],
            nwc_pct_revenue=[0.08, 0.08],
            tax_rate=[0.25, 0.25],
            depreciation_pct_opening_ppe=[0.1, 0.1],
        )
        rows = forecast_operating(
            opening_revenue=100, opening_ppe=50, opening_nwc=8,
            assumptions=assumptions,
        )
        self.assertEqual(len(rows), 2)
        self.assertAlmostEqual(rows[0].revenue, 110)
        self.assertAlmostEqual(rows[0].ending_ppe, 48.3)
        self.assertAlmostEqual(
            rows[0].unlevered_fcf,
            rows[0].ebitda - rows[0].taxes - rows[0].capex - rows[0].change_nwc,
        )

    def test_debt_schedule_never_negative(self):
        rows = build_debt_schedule(
            [
                DebtTranche("revolver", 20, 0.08, cash_sweep_pct=1.0, priority=0),
                DebtTranche(
                    "term", 100, 0.1, pik_rate=0.02,
                    mandatory_amort_pct=0.01, cash_sweep_pct=0.5, priority=1,
                ),
            ],
            [50, 50, 50],
        )
        self.assertTrue(all(row.ending_balance >= 0 for row in rows))
        self.assertLess(rows[-1].ending_balance, 100)
        self.assertAlmostEqual(covenant_headroom(4.5, 5.0, maximum=True), 0.5)

    def test_recovery_waterfall_conserves_value(self):
        result = recovery_waterfall(90, [("revolver", 20), ("term", 100)])
        self.assertEqual(result["revolver"], 20)
        self.assertEqual(result["term"], 70)
        self.assertEqual(sum(result.values()), 90)

    def test_irr(self):
        self.assertAlmostEqual(irr([-100, 0, 121]), 0.1, places=9)

    def test_black_scholes_parity_and_iv(self):
        result = black_scholes(100, 100, 1.0, 0.05, 0.2, 0.02)
        parity = result.call - result.put - (
            100 * exp(-0.02) - 100 * exp(-0.05)
        )
        self.assertAlmostEqual(parity, 0.0, places=10)
        volatility = implied_volatility(
            result.call, is_call=True, spot=100, strike=100,
            maturity=1.0, rate=0.05, dividend_yield=0.02,
        )
        self.assertAlmostEqual(volatility, 0.2, places=7)
        self.assertGreater(result.gamma, 0)
        self.assertGreater(result.vega, 0)

    def test_american_put_not_below_european(self):
        european = black_scholes(100, 110, 1.0, 0.05, 0.25)
        american = american_binomial(
            spot=100, strike=110, maturity=1.0, rate=0.05,
            volatility=0.25, steps=300, is_call=False,
        )
        self.assertGreaterEqual(american + 1e-6, european.put)

    def test_bond_reference_values(self):
        price = bond_price(1000, 0.05, 10, 0.055, 2)
        self.assertAlmostEqual(price, 962.05, delta=0.3)
        self.assertGreater(
            macaulay_duration(1000, 0.05, 10, 0.055, 2),
            modified_duration(1000, 0.05, 10, 0.055, 2),
        )
        self.assertGreater(
            numerical_convexity(1000, 0.05, 10, 0.055, 2), 0,
        )
        curve = {1.0: 0.04, 5.0: 0.045, 10.0: 0.05}
        self.assertAlmostEqual(linear_zero_rate(3.0, curve), 0.0425)
        self.assertGreater(
            key_rate_dv01(
                face=1000, coupon_rate=0.05, maturity=10,
                zero_curve=curve, key_tenor=10.0,
            ),
            0,
        )

    def test_project_finance(self):
        construction = construction_draw_schedule(
            [100, 100], debt_share=0.7, debt_rate_per_period=0.05,
        )
        self.assertGreater(construction[-1].closing_debt, 140)
        sculpted = sculpt_debt_service(
            [40, 45, 50, 55], 1.3, opening_debt=120,
            rate_per_period=0.06,
        )
        self.assertTrue(all(row["ending_debt"] >= 0 for row in sculpted))
        self.assertTrue(all(
            row["dscr"] >= 1.3 - 1e-9 or row["ending_debt"] == 0
            for row in sculpted
        ))
        self.assertGreater(llcr([40, 45, 50], 0.06, 100), 1)

    def test_structured_credit(self):
        collateral = collateral_cash_flows(
            opening_balance=1000, periods=24, annual_coupon=0.08,
            annual_cpr=0.12, annual_cdr=0.03, recovery_rate=0.4,
        )
        self.assertAlmostEqual(collateral[-1].ending_balance, 0.0, places=8)
        waterfall = sequential_waterfall(
            collateral,
            [Tranche("A", 700, 0.05, 0), Tranche("B", 200, 0.08, 1)],
        )
        self.assertTrue(all(row.ending_balance >= 0 for row in waterfall))
        principal = [
            row.principal_paid for row in waterfall if row.tranche == "A"
        ]
        self.assertGreater(weighted_average_life(principal), 0)

    def test_waterfall_routes_recoveries_to_principal_and_conserves_cash(self):
        collateral = collateral_cash_flows(
            opening_balance=1000, periods=24, annual_coupon=0.08,
            annual_cpr=0.12, annual_cdr=0.03, recovery_rate=0.4,
        )
        tranches = [Tranche("A", 700, 0.05, 0), Tranche("B", 200, 0.08, 1)]
        waterfall = sequential_waterfall(collateral, tranches)
        rows = {
            period.period: [r for r in waterfall if r.period == period.period]
            for period in collateral
        }
        for period in collateral:
            paid_interest = sum(r.interest_paid for r in rows[period.period])
            paid_principal = sum(r.principal_paid for r in rows[period.period])
            # Interest collections alone fund coupons; recoveries are
            # principal collections. Residuals (excess spread, OC release)
            # must be non-negative - no cash invented, none lost untracked.
            self.assertLessEqual(paid_interest, period.interest + 1e-9)
            self.assertLessEqual(
                paid_principal,
                period.scheduled_principal + period.prepayment
                + period.recoveries + 1e-9,
            )
        # Total principal returned to the stack never exceeds collateral
        # principal collections, and the stack is fully retired here because
        # collections (including recoveries) exceed the 900 of tranches.
        total_principal_collected = sum(
            p.scheduled_principal + p.prepayment + p.recoveries
            for p in collateral
        )
        total_principal_paid = sum(r.principal_paid for r in waterfall)
        self.assertLessEqual(total_principal_paid, total_principal_collected + 1e-9)
        self.assertAlmostEqual(waterfall[-1].ending_balance, 0.0, places=8)
        # Discriminates the routing: in period 1 the senior balance (700)
        # dwarfs collections, so principal paid must equal scheduled +
        # prepayment + RECOVERIES exactly. The old routing paid only
        # scheduled + prepayment and discarded the recovery cash.
        first = collateral[0]
        self.assertAlmostEqual(
            sum(r.principal_paid for r in rows[1]),
            first.scheduled_principal + first.prepayment + first.recoveries,
            places=9,
        )

    def test_waterfall_junior_waits_for_senior(self):
        collateral = collateral_cash_flows(
            opening_balance=1000, periods=24, annual_coupon=0.08,
            annual_cpr=0.30, annual_cdr=0.0, recovery_rate=0.0,
        )
        waterfall = sequential_waterfall(
            collateral,
            [Tranche("A", 700, 0.05, 0), Tranche("B", 200, 0.08, 1)],
        )
        senior_balance = {r.period: r.ending_balance
                         for r in waterfall if r.tranche == "A"}
        for row in waterfall:
            if row.tranche == "B" and row.principal_paid > 0:
                self.assertAlmostEqual(senior_balance[row.period], 0.0, places=9)

    def test_risk_and_backtest(self):
        returns = [-0.05, 0.02, -0.01, 0.03, -0.02, 0.01]
        self.assertLess(max_drawdown(returns), 0)
        self.assertGreaterEqual(historical_var(returns, 0.95), 0)
        self.assertGreaterEqual(
            expected_shortfall(returns, 0.95),
            historical_var(returns, 0.95),
        )
        self.assertTrue(isclose(
            apply_transaction_costs([0.01], [0.5], 10)[0], 0.0095,
        ))
        self.assertEqual(len(walk_forward_splits(100, train=40, test=10)), 6)
        self.assertTrue(isfinite(sharpe_ratio(returns)))
        self.assertTrue(isfinite(sortino_ratio(returns)))
        net = capacity_adjusted_returns(
            [0.01], [0.1], capital=1_000_000, adv=[10_000_000],
            linear_cost_bps=5, impact_coefficient=0.01,
        )
        self.assertLess(net[0], 0.01)

    def test_long_horizon_liquidity(self):
        cash = liquidity_coverage(100, [20, 30], [5, 10], [10, 10])
        self.assertEqual(cash, [75, 45])
        self.assertGreater(denominator_effect(40, 60, -0.5), 0.4)


if __name__ == "__main__":
    unittest.main()
