# Stage-1 Design Skeleton (≤50 names)

**Status**: Design only. Hard universe cap remains **10** until the Stage-0 evidence checklist in `STAGE_GATES.md` is complete and reviewed.

## Goals for Stage 1

- Support universes up to 50 names with the same pure-Python risk primitives (or a carefully profiled acceleration).
- Keep numerical identities and PSD guarantees.
- Record performance and memory against the budgets in `STAGE_GATES.md`.
- Continue to feed Contract-1 regime exports and the Excel visualization path.

## Planned structure (do not implement until Stage-0 gates pass)

```text
research/ram/
  simple_covariance.py          # Stage 0 (cap 10) — remains the reference
  stage1/
    __init__.py
    covariance.py               # same API, cap raised to 50 after evidence
    data.py                     # loaders for 50-name real universes
    bench_stage1.py
  evidence/
    stage0_results_*.md         # must be complete first
    stage1_results_*.md         # created only after promotion
```

## API stability

Stage 1 will preserve:

- `portfolio_variance(weights, cov) -> float`
- `equal_weight_risk(cov) -> RiskResult`
- `inverse_vol_weights(vols) -> tuple[float, ...]`
- `is_positive_semidefinite(cov) -> bool`

Optional additions (behind explicit flags):

- Leading-eigenvalue or factor-adjusted covariance cleaning
- Simple long-only risk-parity solver
- Batch evaluation helpers for visualization

## Data

Stage 1 will continue to use the Yahoo chart API (or a later vendor) and will write:

- `universe_real_50.json`
- `cov_real_50.json`
- matching Contract-1 regime CSV under `research/kdb/exports/`

Universe selection criteria (to be fixed at promotion time):

- Liquid US large-cap names
- Sufficient common history (≥ 250 daily observations)
- Explicit exclusion list for corporate actions / thin trading if needed

## Non-goals for Stage 1

- No S&P 500 claim
- No options or futures
- No replacement of the governed `09_Risk_Management` archetype
- No M-maturity rating for research artifacts

## Promotion trigger

Only after:

1. Stage-0 unit tests green
2. Measured Stage-0 benchmark numbers recorded in evidence
3. PSD corpus and conservation tests reviewed
4. This design note accepted

Then the hard cap in code may be raised and `stage1/` implementation may begin.
