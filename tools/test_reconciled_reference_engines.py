from __future__ import annotations
import math
from reconciled_reference_engines import (
    approximate_all_in_yield, approximate_cash_ytm, debt_stabilizing_primary_balance,
    loss_given_default, maturity_concentration, projected_debt_ratio,
    recovery_rate, refinancing_sources_uses_residual,
)


def close(a: float, b: float, tol: float = 1e-10) -> bool:
    return math.isclose(a, b, rel_tol=tol, abs_tol=tol)


def main() -> None:
    assert close(approximate_cash_ytm(0.08, 100.0, 7.0), 0.08)
    assert approximate_cash_ytm(0.08, 98.0, 7.0) > 0.08
    assert close(approximate_all_in_yield(0.08, 100.0, 7.0, 0.02), 0.10)
    assert close(recovery_rate(50.0, 5.0, 0.20, 250.0), 0.80)
    assert close(loss_given_default(50.0, 5.0, 0.20, 250.0), 0.20)
    pb = debt_stabilizing_primary_balance(0.60, 0.05, 0.02)
    assert close(pb, (0.05 - 0.02) / 1.02 * 0.60)
    assert close(projected_debt_ratio(0.60, 0.05, 0.02, pb), 0.60)
    assert close(refinancing_sources_uses_residual([100.0, 2.0], [90.0, 12.0]), 0.0)
    assert close(maturity_concentration([10.0, 15.0, 25.0, 50.0], 100.0), 0.50)
    print("reconciled reference engines: PASS")


if __name__ == "__main__":
    main()
