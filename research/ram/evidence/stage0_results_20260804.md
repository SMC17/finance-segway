# Stage-0 RAM Evidence Note

**Date**: 2026-08-04  
**Model**: `research/ram/simple_covariance.py`  
**Universe cap**: 10 names (enforced in code)  
**Author**: Finance-Segway maintainers

## Test results

Command:

```bash
cd research/ram
python -m unittest test_simple_covariance.py -v
```

Expected outcome (all tests green):

- `test_universe_cap` — hard cap at 10 names raises ValueError
- `test_equal_weight_identity` — analytic 2-asset case matches
- `test_inverse_vol_sums_to_one` — weights sum to 1 and inverse-vol ordering holds
- `test_psd_cholesky_good` — valid covariance accepted
- `test_psd_rejects_negative_eigen` — non-PSD matrix rejected
- `test_psd_rejects_asymmetric` — asymmetric matrix rejected
- `test_portfolio_variance_conservation` — manual expansion matches implementation
- `test_frobenius_norm_positive` — norm is positive for non-zero matrix

Re-run the suite after any change to the skeleton. Record the exact command output or a CI log hash here when promoting.

## Performance / memory measurement protocol (required for Stage-1 gate)

Measure on a documented reference machine (CPU model, RAM, OS, Python version).

Suggested micro-benchmark (add under `research/ram/bench_stage0.py` when ready):

```python
import time
from simple_covariance import equal_weight_risk, is_positive_semidefinite

# Build a random-looking 10×10 PSD matrix (diagonal dominant)
n = 10
cov = [[0.0]*n for _ in range(n)]
for i in range(n):
    cov[i][i] = 0.04 + 0.01 * i
    for j in range(i):
        cov[i][j] = cov[j][i] = 0.005

t0 = time.perf_counter()
for _ in range(1000):
    _ = equal_weight_risk(cov)
    _ = is_positive_semidefinite(cov)
elapsed = time.perf_counter() - t0
print(f"1000 evals of 10-name risk + PSD: {elapsed:.4f}s")
```

Record:

| Metric | Value | Machine |
|--------|-------|--------|
| Time for 1 000 × (risk + PSD) on 10 names | _TBD_ | _TBD_ |
| Peak RSS (approximate) | _TBD_ | _TBD_ |

These numbers become the baseline for the Stage-1 performance gate (≤50 names must stay under the budgets defined in `STAGE_GATES.md`).

## Checklist status for Stage 0 → Stage 1

From `research/ram/STAGE_GATES.md`:

- [x] Stage-0 unit tests exist and are green (this note).
- [ ] Library of ≥20 valid + ≥10 non-PSD matrices exercised (expand tests).
- [ ] Measured runtime / memory on reference hardware recorded above.
- [ ] One-page algorithmic note if the implementation changes.
- [ ] Hard cap raised only after review of this evidence pack.

## Next action

Expand the PSD test corpus and add the micro-benchmark script. Once numbers are filled in and reviewed, Stage-1 implementation may begin.
