\"\"\"Stage-0 tests for the simple covariance RAM skeleton.\"\"\"
from __future__ import annotations

import math
import unittest

from simple_covariance import (
    MAX_STAGE0_UNIVERSE,
    equal_weight_risk,
    inverse_vol_weights,
    is_positive_semidefinite,
    portfolio_variance,
)


class TestSimpleCovariance(unittest.TestCase):
    def test_universe_cap(self):
        big = [[0.01] * 11 for _ in range(11)]
        with self.assertRaises(ValueError):
            equal_weight_risk(big)

    def test_equal_weight_identity(self):
        cov = [[0.04, 0.0], [0.0, 0.04]]
        res = equal_weight_risk(cov)
        self.assertAlmostEqual(res.variance, 0.02)
        self.assertAlmostEqual(res.volatility, math.sqrt(0.02))

    def test_inverse_vol_sums_to_one(self):
        w = inverse_vol_weights([0.1, 0.2, 0.4])
        self.assertAlmostEqual(sum(w), 1.0)
        self.assertGreater(w[0], w[1])
        self.assertGreater(w[1], w[2])

    def test_psd_symmetry_and_diagonal(self):
        good = [[0.04, 0.01], [0.01, 0.09]]
        self.assertTrue(is_positive_semidefinite(good))
        bad_diag = [[-0.01, 0.0], [0.0, 0.04]]
        self.assertFalse(is_positive_semidefinite(bad_diag))


if __name__ == "__main__":
    unittest.main()
