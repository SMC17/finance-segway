# dbt Analytics Rail

Semantic layer over the Finance-Segway Postgres instance library.

## Purpose

Provide versioned, tested, documented transformations (staging → intermediate → marts) so that portfolio-level analytics, risk views, and performance summaries can be consumed by analysts without writing ad-hoc SQL against raw EAV tables.

This rail does **not** re-implement any underwriting calculation. It only transforms values that have already been committed and recalculated in the governed Excel workbooks.

## Current scope

Pilot on the existing Private Equity / LBO Postgres tables (`deals`, `deal_assumptions`, `deal_sources_uses`, `deal_debt_schedule`, `deal_returns`).

## Layout

```text
analytics/dbt/
  dbt_project.yml
  profiles.yml.example
  models/
    staging/
    intermediate/
    marts/
  tests/
  macros/
  README.md          ← this file
```

## Design rules

1. Source freshness and row counts are tested.
2. Every mart has a primary key and documented grain.
3. No model may contain financial formulas that belong in the Excel archetypes or Python reference engines.
4. Classification (`real_public` vs `synthetic_benchmark`) is preserved and filtered in marts intended for evidence or external use.

## Next concrete steps

1. Implement staging models that cleanly select from the four PE tables.
2. Build an intermediate leverage path and a mart for selected-exit headline returns.
3. Add schema.yml with tests and descriptions.
4. Only after the PE mart is stable, extend the source definitions to additional domains as they gain real instance depth.
