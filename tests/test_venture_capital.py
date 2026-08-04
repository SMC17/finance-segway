import unittest

from finance_segway.venture_capital import (
    PreferredSecurity,
    liquidation_waterfall,
)


def preferred_stack(*, participating: bool = False):
    return [
        PreferredSecurity(
            "Series B", shares=1_000_000, invested=5_000_000,
            seniority=3, participating=participating,
        ),
        PreferredSecurity(
            "Series A", shares=1_500_000, invested=3_000_000, seniority=2,
        ),
        PreferredSecurity(
            "Seed", shares=1_000_000, invested=1_000_000, seniority=1,
        ),
    ]


class VentureCapitalWaterfallTests(unittest.TestCase):
    def solve(self, exit_proceeds):
        return liquidation_waterfall(
            exit_proceeds=exit_proceeds,
            common_shares=7_000_000,
            preferred=preferred_stack(),
        )

    def test_downside_respects_seniority_and_conserves(self):
        result = self.solve(8_000_000)
        payouts = {line.name: line.payout for line in result.preferred}
        self.assertEqual(payouts, {"Series B": 5_000_000, "Series A": 3_000_000, "Seed": 0})
        self.assertEqual(result.common_payout, 0)
        self.assertAlmostEqual(result.total_distributed, result.exit_proceeds)

    def test_middle_range_selects_holder_by_holder(self):
        result = self.solve(20_000_000)
        elections = {line.name: line.election for line in result.preferred}
        self.assertEqual(
            elections,
            {"Series B": "preference", "Series A": "preference", "Seed": "convert"},
        )
        self.assertAlmostEqual(result.common_payout, 10_500_000)
        self.assertAlmostEqual(result.total_distributed, result.exit_proceeds)

    def test_high_exit_can_still_have_a_mixed_election(self):
        result = self.solve(50_000_000)
        elections = {line.name: line.election for line in result.preferred}
        self.assertEqual(
            elections,
            {"Series B": "preference", "Series A": "convert", "Seed": "convert"},
        )
        series_b = next(line for line in result.preferred if line.name == "Series B")
        self.assertEqual(series_b.payout, 5_000_000)
        self.assertAlmostEqual(result.total_distributed, result.exit_proceeds)

    def test_all_convert_above_the_last_crossover(self):
        result = self.solve(60_000_000)
        self.assertTrue(all(line.election == "convert" for line in result.preferred))
        self.assertAlmostEqual(result.total_distributed, result.exit_proceeds)

    def test_payouts_are_monotonic_across_exit_values(self):
        previous = {name: 0.0 for name in ("Series B", "Series A", "Seed", "Common")}
        for exit_proceeds in range(0, 101_000_000, 500_000):
            result = self.solve(exit_proceeds)
            current = {line.name: line.payout for line in result.preferred}
            current["Common"] = result.common_payout
            for name, payout in current.items():
                self.assertGreaterEqual(payout + 1e-7, previous[name])
            previous = current

    def test_participating_terms_fail_closed(self):
        with self.assertRaisesRegex(NotImplementedError, "participating preferred"):
            liquidation_waterfall(
                exit_proceeds=20_000_000,
                common_shares=7_000_000,
                preferred=preferred_stack(participating=True),
            )


if __name__ == "__main__":
    unittest.main()
