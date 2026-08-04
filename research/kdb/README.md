# kdb+/q Research Rail

High-velocity time-series research and market-data rail for Finance-Segway.

## Purpose

- Store and query daily / intraday market data, quotes, and derived signals.
- Compute empirical regimes, recovery distributions, volatility surfaces, and stress paths.
- Provide controlled summary exports that can be registered as sources for governed decision models.
- Support outcome monitoring (realized vs predicted) that feeds back into M3/M4 evidence packs.

This rail is **not** part of the core maturity claims. It does not underwrite deals or replace Excel archetypes.

## Directory layout

```text
research/kdb/
  README.md
  INTEGRATION_CONTRACTS.md
  schema/
    market.q          # example table definitions
  scripts/
    load_daily.q      # placeholder
  notebooks/          # q / Python research notebooks (future)
```

## Design principles

1. kdb+ holds research and market data; the governance rail holds decision models and evidence.
2. Any data that influences a governed model must cross the boundary via a versioned, dated export that is recorded in a domain’s source register.
3. Licensing and data-vendor constraints are the responsibility of the operator; this repository will only contain public or synthetic examples.

## Immediate next work

- Flesh out minimal table schemas for daily equity bars and simple factor returns.
- Define the exact shape of the “regime summary” and “recovery distribution” export tables that the core can consume.
- Add a tiny synthetic loader so the rail is executable without external vendor data.
