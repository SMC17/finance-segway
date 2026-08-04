# RAM Risk Rail — In-Memory Portfolio & Risk Models

High-performance risk and portfolio engines that start small and scale only after explicit validation gates.

## Naming

“RAM” here means **Risk & Asset Management** models that are designed to live primarily in memory for speed (covariance, factor models, stress engines, portfolio optimizers). Implementation language may be pure Python initially, later Zig, q, or hybrid.

## Scaling policy (binding)

See `docs/MULTI_RAIL_ARCHITECTURE.md`. Stages cannot be skipped.

| Stage | Max universe | Gate |
|-------|--------------|------|
| 0 | 10 names | Reference implementation + unit tests + conservation |
| 1 | 50 names | Runtime & memory baseline + factor checks |
| 2 | S&P 100 | Independent benchmark + documentation |
| 3 | S&P 500 | Full evidence pack + outcome hooks |
| 4 | Nasdaq / CME slices | Separate domain contracts |

## Current status (Stage 0)

- `simple_covariance.py` — pure-Python equal-weighted and inverse-volatility portfolio risk on a synthetic 10-name universe.
- Explicit numerical tests for positive-semidefiniteness and portfolio variance identity.

## Non-goals at this stage

- No claim of production S&P 500 coverage.
- No replacement of the governed Risk Management archetype (`09_Risk_Management`).
- No live market-data dependency in the Stage-0 skeleton.
