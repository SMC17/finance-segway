"""Regression tests for the pure-Python finance reference engines."""
from __future__ import annotations

import unittest

from reference_engines import (
    annualized_irr_single_exit,
    black_scholes,
    bond_price,
    debt_sweep,
    dscr,
    llcr,
    macaulay_duration,
    modified_duration,
    numerical_convexity,
    numerical_duration,
    put_call_parity_residual,
    sequential_pay_waterfall,
)


class OptionsReferenceTests(unittest.TestCase):
    def test_put_call_parity_across_grid(self) -> None:
        for spot in (80.0, 100.0, 120.0):
            for strike in (90.0, 100.0, 110.0):
                result = black_scholes(spot, strike, 0.75, 0.04, 0.01, 0.25)
                residual = put_call_parity_residual(
                    spot, strike, 0.75, 0.04, 0.01, result.call, result.put
                )
                self.assertAlmostEqual(residual, 0.0, places=10)

    def test_expected_greek_signs(self) -> None:
        result = black_scholes(100.0, 100.0, 1.0, 0.05, 0.0, 0.20)
        self.assertGreater(result.call_delta, 0.0)
        self.assertLess(result.put_delta, 0.0)
        self.assertGreater(result.gamma, 0.0)
        self.assertGreater(result.vega, 0.0)
        self.assertGreater(result.call_rho, 0.0)
        self.assertLess(result.put_rho, 0.0)


class FixedIncomeReferenceTests(unittest.TestCase):
    def test_price_and_duration_reference(self) -> None:
        price = bond_price(1000.0, 0.05, 10.0, 0.055, 2)
        self.assertAlmostEqual(price, 961.932, places=2)

        closed_form = modified_duration(1000.0, 0.05, 10.0, 0.055, 2)
        finite_difference = numerical_duration(1000.0, 0.05, 10.0, 0.055, 2)
        self.assertLess(abs(closed_form - finite_difference) / closed_form, 0.001)

        self.assertGreater(macaulay_duration(1000.0, 0.05, 10.0, 0.055, 2), closed_form)
        self.assertGreater(numerical_convexity(1000.0, 0.05, 10.0, 0.055, 2), 0.0)

    def test_price_is_monotone_in_yield(self) -> None:
        low_yield = bond_price(1000.0, 0.05, 10.0, 0.04, 2)
        high_yield = bond_price(1000.0, 0.05, 10.0, 0.07, 2)
        self.assertGreater(low_yield, high_yield)


class CapitalStructureReferenceTests(unittest.TestCase):
    def test_debt_sweep_conserves_cash_and_debt(self) -> None:
        periods = debt_sweep(
            opening_debt=500.0,
            cash_available=[100.0, 120.0, 150.0],
            annual_rate=0.08,
            mandatory_amortization_rate=0.05,
            sweep_percent=0.75,
        )
        previous_closing = 500.0
        for period in periods:
            self.assertAlmostEqual(period.opening_debt, previous_closing, places=12)
            self.assertGreaterEqual(period.closing_debt, 0.0)
            self.assertLessEqual(period.closing_debt, period.opening_debt)
            self.assertAlmostEqual(
                period.opening_debt
                - period.mandatory_amortization
                - period.cash_sweep,
                period.closing_debt,
                places=12,
            )
            previous_closing = period.closing_debt

    def test_debt_sweep_reports_unfunded_debt_service_as_shortfall(self) -> None:
        # Interest due is 8.0 and mandatory amortization due is 10.0 against
        # 2.0 of cash: the cascade must not pretend the payments happened.
        # Interest absorbs all cash, nothing amortizes, debt is unchanged,
        # and the unpaid 16.0 is reported instead of silently vanishing.
        period = debt_sweep(
            opening_debt=100.0,
            cash_available=[2.0],
            annual_rate=0.08,
            mandatory_amortization_rate=0.10,
        )[0]
        self.assertAlmostEqual(period.cash_interest, 2.0, places=12)
        self.assertAlmostEqual(period.mandatory_amortization, 0.0, places=12)
        self.assertAlmostEqual(period.cash_sweep, 0.0, places=12)
        self.assertAlmostEqual(period.closing_debt, 100.0, places=12)
        self.assertAlmostEqual(period.funding_shortfall, 16.0, places=12)

    def test_debt_sweep_partial_funding_amortizes_only_paid_amounts(self) -> None:
        # 12.0 of cash: interest 8.0 paid in full, 4.0 of the 10.0 scheduled
        # amortization funded, debt falls only by the funded 4.0.
        period = debt_sweep(
            opening_debt=100.0,
            cash_available=[12.0],
            annual_rate=0.08,
            mandatory_amortization_rate=0.10,
        )[0]
        self.assertAlmostEqual(period.cash_interest, 8.0, places=12)
        self.assertAlmostEqual(period.mandatory_amortization, 4.0, places=12)
        self.assertAlmostEqual(period.closing_debt, 96.0, places=12)
        self.assertAlmostEqual(period.funding_shortfall, 6.0, places=12)

    def test_debt_sweep_exact_funding_conserves_cash(self) -> None:
        # Cash exactly covers interest + mandatory amortization; no sweep, no
        # shortfall, and every unit of cash is accounted for.
        period = debt_sweep(
            opening_debt=100.0,
            cash_available=[18.0],
            annual_rate=0.08,
            mandatory_amortization_rate=0.10,
        )[0]
        self.assertAlmostEqual(period.cash_interest, 8.0, places=12)
        self.assertAlmostEqual(period.mandatory_amortization, 10.0, places=12)
        self.assertAlmostEqual(period.closing_debt, 90.0, places=12)
        self.assertAlmostEqual(period.funding_shortfall, 0.0, places=12)
        self.assertAlmostEqual(
            period.cash_interest
            + period.mandatory_amortization
            + period.cash_sweep
            + period.excess_cash_after_sweep,
            18.0,
            places=12,
        )

    def test_single_exit_irr_matches_moic_identity(self) -> None:
        irr = annualized_irr_single_exit(250.0, 100.0, 5.0)
        self.assertAlmostEqual((1.0 + irr) ** 5.0, 2.5, places=12)


class ProjectAndStructuredReferenceTests(unittest.TestCase):
    def test_dscr_and_llcr(self) -> None:
        self.assertAlmostEqual(dscr(130.0, 100.0), 1.30, places=12)
        ratio = llcr([130.0, 135.0, 140.0, 145.0], 0.08, 400.0)
        self.assertGreater(ratio, 1.0)

    def test_sequential_waterfall_conserves_principal(self) -> None:
        payments, residual = sequential_pay_waterfall(180.0, [100.0, 80.0, 50.0])
        self.assertEqual(payments, [100.0, 80.0, 0.0])
        self.assertAlmostEqual(sum(payments) + residual, 180.0, places=12)

        payments, residual = sequential_pay_waterfall(260.0, [100.0, 80.0, 50.0])
        self.assertEqual(payments, [100.0, 80.0, 50.0])
        self.assertAlmostEqual(residual, 30.0, places=12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
