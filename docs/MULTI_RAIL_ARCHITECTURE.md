# Multi-Rail Architecture Decision Record

**Status**: Accepted  
**Date**: 2026-08-04  
**Owner**: Finance-Segway core maintainers

## Context

Finance-Segway began as a governed multi-domain spreadsheet library with strong model-risk discipline (M0–M4 maturity scale, independent reference engines, evidence packs, atomic promotion). The Postgres layer was added as a thin, read-only query surface over populated instances.

As the project expands, three additional capabilities are required:

1. A versioned, testable semantic/analytics layer over the growing instance library (dbt).
2. A high-velocity time-series research rail for market data, signals, and empirical regimes (kdb+/q).
3. High-performance in-memory risk and portfolio models capable of scaling from small universes toward large equity and derivatives universes ("RAM" models).

These capabilities must not compromise the core governance design.

## Decision

Finance-Segway adopts a **multi-rail architecture**:

```text
┌────────────────────────────────────────────────────────────────────┐
│  GOVERNANCE & DECISION RAIL (core – immutable contract)            │
│  • Excel archetypes + Python builders                              │
│  • Pure-Python reference / reconciled engines                      │
│  • standards/model_inventory.json + maturity gates                 │
│  • Model cards, validation records, source registers, RefreshLog   │
│  • Postgres instance library (Excel remains source of truth)       │
└───────────────────────────────┬────────────────────────────────────┘
                                │ versioned, aggregated contracts only
┌───────────────────────────────▼────────────────────────────────────┐
│  ANALYTICS RAIL (dbt)                                              │
│  • Staging → intermediate → marts over Postgres (and future        │
│    warehouses)                                                     │
│  • Tested, documented semantic models for risk, performance,       │
│    covenant, recovery, and portfolio views                         │
└───────────────────────────────┬────────────────────────────────────┘
                                │
┌───────────────────────────────▼────────────────────────────────────┐
│  RESEARCH / HIGH-VELOCITY RAIL (kdb+/q)                            │
│  • Tick / quote / daily time-series storage and vectorized query   │
│  • Signal research, regime statistics, empirical recovery paths    │
│  • Realized outcome monitoring feeds                               │
└───────────────────────────────┬────────────────────────────────────┘
                                │
┌───────────────────────────────▼────────────────────────────────────┐
│  RAM RISK RAIL (in-memory portfolio & risk models)                 │
│  • High-performance covariance, factor, and stress engines         │
│  • Starts at tiny universes; scales only after validation gates    │
│  • May be accelerated in Zig, pure Python, or q as appropriate     │
└────────────────────────────────────────────────────────────────────┘
```

## Non-negotiable contracts

1. **Excel remains the calculation engine and source of truth for every decision model.** No rail may re-implement underwriting formulas or claim to supersede a governed archetype.
2. **M-maturity claims are owned exclusively by the core inventory and validators.** Research rails never inherit or inflate M2/M3/M4 status.
3. **Data flowing from research rails into decision models must be registered** as dated sources with snapshots (or checksums) in the domain’s `sources/` tree.
4. **Outcome monitoring is bidirectional but controlled**: realized statistics may be summarized back into evidence packs; live research data never silently mutates a frozen instance.
5. **Scaling criteria are explicit**. A risk model does not “support the S&P 500” until it has passed defined numerical, performance, and governance gates on intermediate universes.

## Phased scaling policy for RAM models

| Stage | Universe size | Required gates before promotion |
|-------|---------------|---------------------------------|
| 0 | ≤ 10 names | Pure reference implementation, unit tests, conservation identities |
| 1 | ≤ 50 names | Performance baseline, factor exposure checks, stress monotonicity |
| 2 | S&P 100 | Memory & runtime budgets, cross-sectional consistency, independent benchmark |
| 3 | S&P 500 | Full documentation, outcome monitoring hooks, effective challenge |
| 4 | Nasdaq / selected CME | Domain-specific contracts + separate evidence packs |

No stage may be skipped.

## Consequences

- New directories `analytics/`, `research/kdb/`, and `research/ram/` are first-class citizens of the repository but sit outside the core domain folders `01_`–`24_`.
- CI for the core library continues to ignore or only lightly touch the research rails until their own test suites are mature.
- The Integration Ledger and model inventory remain the single sources of truth for what is governed.

## Related documents

- `docs/MODEL_GOVERNANCE_STANDARD.md`
- `docs/INSTITUTIONAL_DEPTH_BLUEPRINT.md`
- `db/README.md`
- `research/kdb/INTEGRATION_CONTRACTS.md`
- `research/ram/README.md`
