# RAM model stage gates

Promotion is manual and evidence-backed. Passing unit tests alone does not
promote a rail.

## Stage 0 → Stage 1

### Numerical controls

- [x] Ten-name cap is enforced.
- [x] Portfolio variance identity tests cover equal and arbitrary long-only weights.
- [x] PSD checks accept valid matrices and reject asymmetric or unusable matrices.
- [ ] Independent analytic two-asset benchmark is documented.

### Real-data controls

- [ ] Named public universe and observation window.
- [ ] Dated source URL and permissible frozen snapshot.
- [ ] SHA-256 receipt and transformation methodology.
- [ ] Missing-value, corporate-action, and survivorship-bias policy.
- [ ] Realized-risk comparison reviewed by a human.

### Performance and process

- [ ] Runtime and peak-memory measurements on documented hardware.
- [ ] Algorithmic complexity review.
- [ ] Independent approval of the evidence note.
- [ ] Hard cap changed only in the reviewed promotion PR.

## Later stages

Stage 1 → 2 adds a public factor benchmark, resource budgets, and cross-sectional
consistency. Stage 2 → 3 requires a full evidence pack and outcome monitoring.
Later gates are intentionally not claimed complete.

## Current status

Stage 0 engine skeleton: implemented and numerically tested.  
Stage 0 empirical evidence: absent.  
Stage 1 promotion: blocked.
