# dbt Analytics Rail

Semantic layer over the Finance-Segway Postgres instance library.

## Purpose

Provide versioned, tested, documented transformations (staging → intermediate → marts) so that portfolio-level analytics, risk views, and performance summaries can be consumed by analysts without writing ad-hoc SQL against raw EAV tables.

This rail does **not** re-implement any underwriting calculation. It only transforms values that have already been committed and recalculated in the governed Excel workbooks.

## Prerequisites

1. A local Postgres database with the Finance-Segway schema applied and the PE instances loaded:

```bash
createdb finance_segway
psql -d finance_segway -f db/schema.sql
pip install psycopg2-binary
python tools/postgres_etl.py          # loads the four registered PE deals
```

2. dbt Core (1.7+ recommended):

```bash
pip install dbt-core dbt-postgres
```

## Pointing dbt at the database

Copy the example profile and edit if needed:

```bash
cp analytics/dbt/profiles.yml.example ~/.dbt/profiles.yml
# or keep it inside the project and set DBT_PROFILES_DIR
```

Default connection (peer/local auth):

```yaml
finance_segway:
  target: dev
  outputs:
    dev:
      type: postgres
      host: localhost
      user: "{{ env_var('PGUSER', 'postgres') }}"
      password: "{{ env_var('PGPASSWORD', '') }}"
      port: 5432
      dbname: finance_segway
      schema: analytics          # dbt will create models here
      threads: 4
```

Override with environment variables `PGUSER`, `PGPASSWORD`, or `FINANCE_SEGWAY_PG_DSN` as needed.

## Run

From the repository root (or set `dbt_project.yml` path accordingly):

```bash
cd analytics/dbt
dbt deps                    # currently empty packages.yml
dbt debug                   # verify connection
dbt run                     # build staging + marts
dbt test                    # run schema + data tests
```

Useful selectors:

```bash
dbt run --select staging
dbt run --select marts
dbt test --select mart_selected_exit_returns
```

## Current models

| Model | Grain | Description |
|-------|-------|-------------|
| `stg_deals` | deal_id | Clean deals table |
| `stg_deal_returns` | deal_id, period, metric | Long-format returns |
| `stg_deal_debt_schedule` | deal_id, period, metric | Long-format debt schedule |
| `mart_selected_exit_returns` | deal_id | Selected-exit headline metrics (real_public only by default) |
| `mart_leverage_path` | deal_id, period | Deleveraging trajectory (total debt, net debt, ending cash) |

## Design rules

1. Source freshness and row counts are tested.
2. Every mart has a primary key and documented grain.
3. No model may contain financial formulas that belong in the Excel archetypes or Python reference engines.
4. Classification (`real_public` vs `synthetic_benchmark`) is preserved; evidence-oriented marts filter to `real_public` via the project var `evidence_classifications`.

## Next steps

- Add intermediate models if cross-domain joins become common.
- Introduce dbt_utils once a concrete need appears.
- Extend sources as additional domains gain real instance depth and are loaded by the ETL.
