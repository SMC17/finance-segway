# Stage-1 Promotion Hold

**Date**: 2026-08-04  
**Decision**: **Do not raise runtime cap yet**

## Why

Stage-0 is complete on a real 10-name universe. Stage-1 skeleton and tests exist (`research/ram/stage1/`) with design capacity 50, but:

- No Stage-1 evidence note with measured timings on a 30–50 name real covariance
- No expanded unit corpus on larger PSD matrices
- Service-layer flagship work (Private Credit instance + agent) is higher priority for the AI-native Goldman path

## Required before promotion

1. Fetch a liquid 30–50 name real universe (extend `fetch_real_universe.py`).
2. Bench Stage-1 module on that cov; record machine + timings.
3. Write `evidence/stage1_results_YYYYMMDD.md`.
4. Only then set `_RUNTIME_CAP = 50` in `stage1/covariance.py`.

Until then, production research risk calls stay on Stage-0 (`simple_covariance.py`, cap 10).
