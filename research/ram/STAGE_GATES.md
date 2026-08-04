# RAM Model Stage Gates

Promotion between stages is **not** automatic. Each gate must be evidenced before the hard universe cap is raised.

## Stage 0 → Stage 1 (≤10 → ≤50 names)

### Numerical / correctness

- [x] Stage-0 unit tests green.
- [x] Real-data covariance PSD + risk identities hold.
- [x] Measured runtime recorded (0.0475 ms/iter on real 10×10).

### Process

- [x] Evidence note reviewed (`evidence/stage0_results_20260804.md`).
- [x] Stage-1 design and skeleton module exist (`STAGE1_DESIGN.md`, `stage1/`).
- [ ] Stage-1 own unit tests + bench on a 30–50 name real (or carefully constructed) universe.
- [ ] Stage-1 evidence note written and reviewed.
- [ ] Runtime cap in `stage1/covariance.py` raised from 10 → 50 only after the above.

## Stage 1 → Stage 2 (≤50 → S&P 100)

Defined only after Stage 1 is stable. Expected themes: independent benchmark, factor exposures, interactive runtime budgets, first outcome-monitoring hooks.

## Stage 2 → Stage 3 (S&P 100 → S&P 500) and beyond

Require formal evidence packs analogous to core M3/M4. Not specified yet.

## Current status

- Stage 0: **complete and reviewed** (real data).
- Stage 1: skeleton open; runtime still gated at 10 until Stage-1 evidence exists.
