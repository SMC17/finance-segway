# RAM Model Stage Gates

Promotion between stages is **not** automatic. Each gate must be evidenced in a short note under `research/ram/evidence/` before the hard universe cap is raised.

## Stage 0 → Stage 1 (≤10 names → ≤50 names)

### Numerical / correctness gates

- [ ] All Stage-0 unit tests remain green.
- [ ] PSD check (Cholesky) passes on a library of ≥20 randomly generated valid covariance matrices and correctly rejects ≥10 deliberately non-PSD matrices.
- [ ] Portfolio variance identity holds to 1e-10 relative tolerance for equal-weight, inverse-vol, and random long-only weights.
- [ ] A small numerical benchmark (analytic 2-asset case) is included and passes.

### Performance / memory gates (measured on a reference laptop, document exact machine)

- [ ] Construction of a 50×50 covariance matrix + one portfolio variance evaluation completes in < 5 ms (pure Python is acceptable at this stage).
- [ ] Peak memory for a 50-name run stays under 50 MB.
- [ ] No hidden O(n³) or worse algorithms without an explicit comment and measured cost.

### Process / documentation gates

- [ ] `STAGE_GATES.md` updated with the measured numbers and date.
- [ ] A one-page note explaining any algorithmic change from the Stage-0 skeleton.
- [ ] The hard cap in code is raised only after the above checklist is complete and reviewed.

## Stage 1 → Stage 2 (≤50 → S&P 100)

Additional gates will be defined only after Stage 1 is stable. Expected themes:

- Independent benchmark against a published factor model or risk system on a public universe.
- Explicit factor-exposure conservation tests.
- Runtime and memory budgets appropriate for interactive research use.
- First hooks for outcome monitoring (predicted vs realised risk).

## Stage 2 → Stage 3 (S&P 100 → S&P 500) and beyond

These gates will require formal evidence packs analogous to the core M3 requirements. They are deliberately not specified yet.

## Current status

- Stage 0: implemented and tested (2026-08-04).
- Stage 1: gates defined; implementation not started.
