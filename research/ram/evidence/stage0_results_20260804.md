# Stage-0 RAM Evidence Note (Real Data) — REVIEWED

**Date**: 2026-08-04  
**Review status**: **CLOSED — Stage-0 gates satisfied for promotion planning**  
**Model**: `research/ram/simple_covariance.py`  
**Universe**: real US mega-cap 10 (`AAPL MSFT GOOGL AMZN META NVDA BRK-B JPM XOM JNJ`)  
**As-of**: 2026-08-04  
**Return window**: 275 daily log returns (Yahoo Finance adjusted close)

## Proof that the Stage-0 template works on real data

- Covariance from real adjusted closes → annualised sample covariance.
- Cholesky PSD check: **PASS**.
- Equal-weight portfolio: variance ≈ 0.01577, **vol ≈ 12.56%**.
- Inverse-vol portfolio: variance ≈ 0.01100, **vol ≈ 10.49%**.
- Inverse-vol weights sum to 1.0; higher weight on lower-vol names (BRK-B, JNJ, …).
- Contract-1 regime CSV written and consumed by the Excel visualization builder.

## Measured performance

| Metric | Value | Notes |
|--------|-------|-------|
| Covariance | real us_mega10_liquid | |
| Iterations | 2000 × (equal-weight risk + Cholesky PSD) | |
| Total wall time | **0.0951 s** | |
| Per iteration | **0.0475 ms** | |
| Python | 3.12.3 | |
| Platform | Linux x86_64 | |

Well inside any reasonable Stage-1 budget.

## Checklist (Stage 0 → Stage 1)

- [x] Unit tests green (identities, PSD accept/reject, conservation).
- [x] Real-data path exercised; PSD and risk identities hold.
- [x] Measured runtime recorded.
- [x] Excel visualization generated from real cov + real regime CSV.
- [x] Evidence note reviewed.

**Promotion decision**: Stage-1 skeleton may be implemented. Hard universe cap in the Stage-0 module remains 10 until the Stage-1 module has its own tests and a separate evidence note. See `STAGE1_DESIGN.md` and `stage1/`.

## Artifacts

- `research/ram/data/universe_real_10.json`
- `research/ram/data/cov_real_10.json`
- `research/kdb/exports/regime_summary_20260804.csv`
- `research/ram/visualizations/_universe_viz_stage0.xlsx` (regenerate via builder)
- `research/ram/STAGE1_DESIGN.md`
- `research/ram/stage1/` (skeleton)
