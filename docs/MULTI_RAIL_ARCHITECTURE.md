# Multi-Rail Architecture Decision Record

**Status:** Accepted  
**Date:** 2026-08-04  
**Owner:** Finance-Segway core maintainers

Finance-Segway separates governed decision models from optional analytics and
research capabilities. The separation is architectural, not a license to lower
evidence standards.

| Rail | Responsibility | Authoritative source |
|---|---|---|
| Governance and decisions | Excel archetypes, builders, oracles, maturity gates | Committed workbooks and `standards/` |
| Analytics | Tested semantic views over extracted workbook outputs | Postgres tables loaded from public cases |
| Time-series research | Public market observations and controlled empirical exports | Dated, checksummed source snapshots |
| RAM risk | Hand-rolled covariance, factor, stress, and allocation engines | Versioned code plus independent tests |

## Non-negotiable contracts

1. Excel remains the calculation engine and evidence record for decision models.
2. Only core inventory validators can assign M0–M4 maturity.
3. Research inputs crossing into a decision model require a source URL, as-of
   date, methodology, checksum, and source-register entry.
4. No live feed silently mutates a frozen public case.
5. Business evidence must be real and source-addressed. Synthetic datasets,
   generated business cases, and synthetic evidence exports are prohibited.
6. Small deterministic numerical vectors are allowed only inside unit or oracle
   tests; they are never evidence and never count toward maturity.
7. Scaling claims require measured, reviewed stage gates.

## RAM scaling gates

| Stage | Maximum universe | Promotion boundary |
|---|---:|---|
| 0 | 10 | Pure implementation, identities, and numerical tests |
| 1 | 50 | Public observations, performance baseline, factor checks |
| 2 | S&P 100 | Independent benchmark and resource budgets |
| 3 | S&P 500 | Full evidence pack and outcome monitoring |
| 4 | Selected Nasdaq/CME scope | Separate domain contracts and review |

No stage may be skipped. Passing numerical tests establishes an engine
skeleton; it does not establish empirical fitness or a promotion claim.

## Governance

- Rail contracts and policy code are CODEOWNED.
- Analytics and research outputs remain outside the 24-domain maturity inventory
  until explicitly admitted through the normal evidence gate.
- Issue #7 remains the human effective-challenge and sign-off boundary.

Related documents: `docs/MODEL_GOVERNANCE_STANDARD.md`, `db/README.md`,
`research/kdb/INTEGRATION_CONTRACTS.md`, and `research/ram/STAGE_GATES.md`.
