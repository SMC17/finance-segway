\"\"\"Micro-benchmark for Stage-0 RAM risk + PSD.

Prefers the real 10-name covariance when present; falls back to a
diagonal-dominant synthetic matrix only if real data has not been fetched.
\"\"\"
from __future__ import annotations

import json
import platform
import sys
import time
from pathlib import Path

from simple_covariance import equal_weight_risk, is_positive_semidefinite

DATA_DIR = Path(__file__).resolve().parent / "data"


def load_cov() -> tuple[list[list[float]], str]:
    cov_path = DATA_DIR / "cov_real_10.json"
    if cov_path.exists():
        cov = json.loads(cov_path.read_text())
        return cov, "real (us_mega10_liquid)"
    # fallback synthetic
    n = 10
    cov = [[0.0] * n for _ in range(n)]
    for i in range(n):
        cov[i][i] = 0.04 + 0.005 * i
        for j in range(i):
            cov[i][j] = cov[j][i] = 0.004
    return cov, "synthetic diagonal-dominant fallback"


def main() -> None:
    cov, label = load_cov()
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
    print(f"Covariance      : {label}")
    print(f"Universe size   : {len(cov)}")
    print(f"Iterations      : {iterations} (risk + PSD each)")
    print(f"Total wall time : {elapsed:.4f} s")
    print(f"Per iteration   : {elapsed / iterations * 1000:.4f} ms")
    print()
    print("Paste the numbers above into research/ram/evidence/ when promoting.")


if __name__ == "__main__":
    main()
