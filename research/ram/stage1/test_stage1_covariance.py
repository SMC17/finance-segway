"""Stage-1 tests — runtime still capped at 10 until evidence promotion."""
from __future__ import annotations

import math
import unittest

try:
    from research.ram.stage1.covariance import (
        MAX_STAGE1_DESIGN_UNIVERSE,
        equal_weight_risk,
        inverse_vol_weights,
        is_positive_semidefinite,
        portfolio_variance,
    )
except ImportError:
    from covariance import (
        MAX_STAGE1_DESIGN_UNIVERSE,
        equal_weight_risk,
        inverse_vol_weights,
        is_positive_semidefinite,
        portfolio_variance,
    )


class TestStage1Skeleton(unittest.TestCase):
    def test_design_capacity_documented(self):
        self.assertEqual(MAX_STAGE1_DESIGN_UNIVERSE, 50)

    def test_runtime_still_gated_at_10(self):
        big = [[0.01] * 11 for _ in range(11)]
        with self.assertRaises(ValueError):
            equal_weight_risk(big)

    def test_equal_weight_identity(self):
        cov = [[0.04, 0.0], [0.0, 0.04]]
        res = equal_weight_risk(cov)
        self.assertAlmostEqual(res.variance, 0.02)
        self.assertAlmostEqual(res.volatility, math.sqrt(0.02))

    def test_psd_and_inv_vol(self):
        cov = [
            [0.04, 0.01, 0.0],
            [0.01, 0.09, 0.02],
            [0.0, 0.02, 0.16],
        ]
        self.assertTrue(is_positive_semidefinite(cov))
        vols = [math.sqrt(cov[i][i]) for i in range(3)]
        w = inverse_vol_weights(vols)
        self.assertAlmostEqual(sum(w), 1.0)
        var = portfolio_variance(w, cov)
        self.assertGreater(var, 0.0)


if __name__ == "__main__":
    unittest.main()
