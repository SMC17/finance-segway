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
        expected = 0.36 * 0.04 + 0.16 * 0.09 + 2 * 0.6 * 0.4 * 0.01
        self.assertAlmostEqual(var, expected)

    def test_frobenius_norm_positive(self):
        cov = [[0.04, 0.01], [0.01, 0.09]]
        self.assertGreater(frobenius_norm(cov), 0.0)

    def test_psd_identity_matrix(self):
        ident = [[1.0 if i == j else 0.0 for j in range(5)] for i in range(5)]
        self.assertTrue(is_positive_semidefinite(ident))

    def test_psd_diagonal_dominant(self):
        n = 8
        cov = [[0.0] * n for _ in range(n)]
        for i in range(n):
            cov[i][i] = 1.0
            for j in range(i):
                cov[i][j] = cov[j][i] = 0.05
        self.assertTrue(is_positive_semidefinite(cov))

    def test_psd_zero_matrix_rejected(self):
        # Zero matrix has zero pivots; treated as not strictly usable for risk.
        zero = [[0.0] * 3 for _ in range(3)]
        self.assertFalse(is_positive_semidefinite(zero))

    def test_equal_weight_three_asset(self):
        cov = [
            [0.04, 0.01, 0.00],
            [0.01, 0.09, 0.02],
            [0.00, 0.02, 0.16],
        ]
        res = equal_weight_risk(cov)
        # Manual: w = 1/3 each
        w = 1.0 / 3.0
        expected = (
            w * w * 0.04 + w * w * 0.09 + w * w * 0.16
            + 2 * w * w * 0.01 + 2 * w * w * 0.00 + 2 * w * w * 0.02
        )
        self.assertAlmostEqual(res.variance, expected, places=10)


if __name__ == "__main__":
    unittest.main()
