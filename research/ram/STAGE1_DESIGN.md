# Stage-1 design (maximum 50 assets)

**Status:** Design only. The hard cap remains ten until Stage-0 real-data,
performance, and independent-review gates are complete.

## Stable API

- `portfolio_variance(weights, covariance)`
- `equal_weight_risk(covariance)`
- `inverse_vol_weights(volatilities)`
- `is_positive_semidefinite(covariance)`

The Stage-0 pure-Python implementation remains the reference even if a later
implementation adds acceleration.

## Real-data boundary

Stage 1 requires a fixed, reviewable universe and observation window. A data
release must include raw observations where redistribution permits, exact source
URLs, an as-of date, a SHA-256 receipt, corporate-action and missing-value
policies, derived covariance, and a realized-risk comparison. There is no
generated-data or offline fallback.

The initial design target is a liquid public US equity universe with at least
250 common daily observations. The exact constituents are fixed only in the
promotion PR; no S&P 100/500 coverage is implied.

## Planned structure

```text
research/ram/
  simple_covariance.py
  stage1/
    covariance.py
    data.py
    bench_stage1.py
  evidence/
    stage0_results_<as-of>.md
```

## Promotion trigger

1. All Stage-0 numerical tests pass.
2. A source-addressed Stage-0 public dataset and receipt are reviewed.
3. Performance and peak memory are measured on documented hardware.
4. Bias, corporate-action, and missing-value policies are accepted.
5. An independent reviewer approves the evidence delta.

Only then may code raise the universe cap.
