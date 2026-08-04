"""Numerical performance harness; it produces no dataset or evidence claim."""

from __future__ import annotations

import platform
import sys
import time

try:
    from research.ram.simple_covariance import equal_weight_risk, is_positive_semidefinite
except ModuleNotFoundError:  # direct execution from research/ram
    from simple_covariance import equal_weight_risk, is_positive_semidefinite


def reference_covariance(size: int = 10) -> list[list[float]]:
    matrix = [[0.0] * size for _ in range(size)]
    for row in range(size):
        matrix[row][row] = 0.04 + 0.005 * row
        for column in range(row):
            matrix[row][column] = matrix[column][row] = 0.004
    return matrix


def main() -> None:
    covariance = reference_covariance()
    if not is_positive_semidefinite(covariance):
        raise SystemExit("reference covariance is not PSD")
    iterations = 2_000
    started = time.perf_counter()
    for _ in range(iterations):
        equal_weight_risk(covariance)
        is_positive_semidefinite(covariance)
    elapsed = time.perf_counter() - started
    print(f"Python: {sys.version.split()[0]}")
    print(f"Platform: {platform.platform()} / {platform.machine()}")
    print(f"Iterations: {iterations}")
    print(f"Elapsed seconds: {elapsed:.6f}")
    print(f"Milliseconds per iteration: {elapsed / iterations * 1000:.6f}")


if __name__ == "__main__":
    main()
