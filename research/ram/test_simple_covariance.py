"""Numerical identity and failure-mode tests; not business evidence."""

from __future__ import annotations

import math
import unittest

from research.ram.simple_covariance import (
    equal_weight_risk,
    frobenius_norm,
    inverse_vol_weights,
    is_positive_semidefinite,
    portfolio_variance,
)


class SimpleCovarianceTests(unittest.TestCase):
    def test_universe_cap(self) -> None:
        with self.assertRaises(ValueError):
            equal_weight_risk([[0.01] * 11 for _ in range(11)])

    def test_equal_weight_identity(self) -> None:
        result = equal_weight_risk([[0.04, 0.0], [0.0, 0.04]])
        self.assertAlmostEqual(0.02, result.variance)
        self.assertAlmostEqual(math.sqrt(0.02), result.volatility)

    def test_arbitrary_weight_identity(self) -> None:
        covariance = [[0.04, 0.01], [0.01, 0.09]]
        expected = 0.6**2 * 0.04 + 0.4**2 * 0.09 + 2 * 0.6 * 0.4 * 0.01
        self.assertAlmostEqual(expected, portfolio_variance((0.6, 0.4), covariance))

    def test_inverse_volatility_weights(self) -> None:
        weights = inverse_vol_weights([0.1, 0.2, 0.4])
        self.assertAlmostEqual(1.0, sum(weights))
        self.assertGreater(weights[0], weights[1])
        self.assertGreater(weights[1], weights[2])

    def test_psd_accepts_positive_definite_and_singular(self) -> None:
        self.assertTrue(is_positive_semidefinite([[1.0, 0.5], [0.5, 1.0]]))
        self.assertTrue(is_positive_semidefinite([[1.0, 1.0], [1.0, 1.0]]))
        self.assertTrue(is_positive_semidefinite([[0.0, 0.0], [0.0, 0.0]]))

    def test_psd_rejects_indefinite_and_asymmetric(self) -> None:
        self.assertFalse(is_positive_semidefinite([[0.04, 0.10], [0.10, 0.04]]))
        self.assertFalse(is_positive_semidefinite([[0.04, 0.02], [0.01, 0.09]]))

    def test_invalid_numbers_fail_closed(self) -> None:
        self.assertFalse(is_positive_semidefinite([[float("nan")]]))
        with self.assertRaises(ValueError):
            inverse_vol_weights([0.1, float("inf")])
        with self.assertRaises(ValueError):
            portfolio_variance([1.0], [[-0.1]])
        with self.assertRaises(ValueError):
            portfolio_variance([1.0, 0.0], [[0.04, 0.10], [0.10, 0.04]])

    def test_frobenius_norm(self) -> None:
        self.assertAlmostEqual(5.0, frobenius_norm([[3.0, 0.0], [0.0, 4.0]]))


if __name__ == "__main__":
    unittest.main()
