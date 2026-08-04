\"\"\"Micro-benchmark for Stage-0 RAM risk + PSD on a 10-name universe.

Records wall time for repeated evaluations. Run on a documented reference
machine and paste results into research/ram/evidence/stage0_results_*.md
before attempting Stage-1 promotion.
\"\"\"
from __future__ import annotations

import platform
import sys
import time
from simple_covariance import equal_weight_risk, is_positive_semidefinite


def make_diag_dominant_cov(n: int = 10) -> list[list[float]]:
    cov = [[0.0] * n for _ in range(n)]
    for i in range(n):
        cov[i][i] = 0.04 + 0.005 * i
        for j in range(i):
            cov[i][j] = cov[j][i] = 0.004
    return cov


def main() -> None:
    n = 10
    cov = make_diag_dominant_cov(n)
    assert is_positive_semidefinite(cov), "benchmark covariance must be PSD"

    iterations = 2000
    t0 = time.perf_counter()
    for _ in range(iterations):
        _ = equal_weight_risk(cov)
        _ = is_positive_semidefinite(cov)
    elapsed = time.perf_counter() - t0

    print("=== Stage-0 RAM micro-benchmark ===")
    print(f"Python          : {sys.version.split()[0]}")
    print(f"Platform        : {platform.platform()}")
    print(f"Machine         : {platform.machine()}")
    print(f"Universe size   : {n}")
    print(f"Iterations      : {iterations} (risk + PSD each)")
    print(f"Total wall time : {elapsed:.4f} s")
    print(f"Per iteration   : {elapsed / iterations * 1000:.4f} ms")
    print()
    print("Paste the numbers above into the evidence note before Stage-1.")


if __name__ == "__main__":
    main()
