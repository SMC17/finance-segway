# Stage-0 RAM Evidence Note (Real Data)

**Date**: 2026-08-04  
**Model**: `research/ram/simple_covariance.py`  
**Universe**: real US mega-cap 10 (`AAPL MSFT GOOGL AMZN META NVDA BRK-B JPM XOM JNJ`)  
**As-of**: 2026-08-04  
**Return window**: 275 daily log returns (Yahoo Finance adjusted close)  
**Author**: Finance-Segway maintainers

## Proof that the Stage-0 template works on real data

- Covariance estimated from real adjusted closes → annualised sample covariance.
- Cholesky PSD check: **PASS**.
- Equal-weight portfolio: variance ≈ 0.01577, **vol ≈ 12.56%**.
- Inverse-vol portfolio: variance ≈ 0.01100, **vol ≈ 10.49%** (lower, as expected).
- Inverse-vol weights sum to 1.0; higher weight on lower-vol names (BRK-B, JNJ, etc.).
- Contract-1 regime CSV written with realized_vol_1y_avg ≈ 0.276, p50 ≈ 0.280, avg_pairwise_corr ≈ 0.079.

Commands used:

```bash
python research/ram/fetch_real_universe.py
python research/ram/bench_stage0.py
python research/ram/build_universe_viz.py
python -m unittest research.ram.test_simple_covariance -v   # or from research/ram
```

## Measured performance (this environment)

| Metric | Value | Notes |
|--------|-------|-------|
| Covariance | real us_mega10_liquid | |
| Iterations | 2000 × (equal-weight risk + Cholesky PSD) | |
| Total wall time | **0.0951 s** | |
| Per iteration | **0.0475 ms** | |
| Python | 3.12.3 | |
| Platform | Linux-6.12.8+-x86_64-with-glibc2.39 | |
| Machine | x86_64 | |

These numbers satisfy the spirit of the Stage-1 performance gate (≪ 5 ms per evaluation even at 50 names is expected to remain easy for pure Python at this complexity).

## Test status

`test_simple_covariance.py` covers universe cap, analytic identities, PSD accept/reject (including identity, diagonal-dominant, asymmetric, zero), and conservation of portfolio variance. All must stay green.

## Checklist status for Stage 0 → Stage 1

- [x] Stage-0 unit tests exist and are green.
- [x] Real-data path exercised; PSD and risk identities hold.
- [x] Measured runtime recorded above.
- [x] Excel visualization generated from real cov + real regime CSV.
- [ ] Optional: expand random PSD corpus further if desired.
- [ ] Formal review of this evidence pack before raising the hard cap.

## Artifacts

- `research/ram/data/universe_real_10.json`
- `research/ram/data/cov_real_10.json`
- `research/kdb/exports/regime_summary_20260804.csv`
- `research/ram/visualizations/_universe_viz_stage0.xlsx` (regenerate with `build_universe_viz.py`)
- `research/ram/STAGE1_DESIGN.md`

## Next action

After review of this note, implementation of the Stage-1 skeleton (cap 50) may begin following `STAGE1_DESIGN.md`.
