\"\"\"Stage-0 tests for the simple covariance RAM skeleton.\"\"\"
from __future__ import annotations

import math
import unittest

from simple_covariance import (
    MAX_STAGE0_UNIVERSE,
    equal_weight_risk,
    frobenius_norm,
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

    def test_psd_cholesky_good(self):
        good = [
            [0.04, 0.01, 0.00],
            [0.01, 0.09, 0.02],
            [0.00, 0.02, 0.16],
        ]
        self.assertTrue(is_positive_semidefinite(good))

    def test_psd_rejects_negative_eigen(self):
        # Construct a matrix that is symmetric but not PSD
        bad = [
            [0.04, 0.10],
            [0.10, 0.04],
        ]
        self.assertFalse(is_positive_semidefinite(bad))

    def test_psd_rejects_asymmetric(self):
        asym = [
            [0.04, 0.02],
            [0.01, 0.09],
        ]
        self.assertFalse(is_positive_semidefinite(asym))

    def test_portfolio_variance_conservation(self):
        cov = [
            [0.04, 0.01],
            [0.01, 0.09],
        ]
        w = (0.6, 0.4)
        var = portfolio_variance(w, cov)
        # Manual expansion: 0.6^2*0.04 + 0.4^2*0.09 + 2*0.6*0.4*0.01
        expected = 0.36 * 0.04 + 0.16 * 0.09 + 2 * 0.6 * 0.4 * 0.01
        self.assertAlmostEqual(var, expected)

    def test_frobenius_norm_positive(self):
        cov = [[0.04, 0.01], [0.01, 0.09]]
        self.assertGreater(frobenius_norm(cov), 0.0)


if __name__ == "__main__":
    unittest.main()
