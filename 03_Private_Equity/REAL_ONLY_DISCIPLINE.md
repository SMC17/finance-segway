# Private Equity — Real-Only Instance Discipline

**Status**: Active  
**Flagship**: Yes (AI-native Goldman roadmap)

## Current real public instances

| Slug | Class | Role |
|------|-------|------|
| `public_home_depot_2023` | real_public | Reference / conventional operating case |
| `public_macys_2020_adversarial` | real_public | Adversarial / stressed case |

These are the only instances that count toward M3/M4 evidence for this domain.

## Synthetic quarantine

Any remaining synthetic or benchmark workbooks under `instances/` (or legacy paths) are **engineering fixtures only**. They:

- Must be labeled `synthetic_benchmark` in any ETL or inventory view
- Do **not** count toward maturity promotion
- Should be retired or moved under an explicit `fixtures/` path when capacity allows

## Required for M3 (this domain)

- [x] Model card + validation present
- [x] ≥2 real public instances (reference + adversarial)
- [ ] Source register rows complete for material inputs on both instances
- [ ] Visible Checks green on both after recalc
- [ ] Effective challenge / stakeholder perspectives documented
- [ ] Named owner + dated release evidence

## Required for M4

- [ ] ≥3 material RefreshLog entries per instance
- [ ] ≥1 documented outcome comparison
- [ ] Source snapshots retained
- [ ] Release artifact reproducibility

## Service-layer note

PE is a flagship for sell-side / buy-side flex. Depth here templates the evidence pattern for the other five flagships and, later, the remaining domains under `docs/DOMAIN_MAX_POLICY.md`.
