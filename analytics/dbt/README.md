# dbt analytics rail

This optional semantic layer builds tested portfolio views over the Postgres
query layer. It transforms only values extracted from committed,
source-addressed public workbooks; it does not reproduce underwriting formulas.

## Setup

```bash
createdb finance_segway
psql -d finance_segway -f db/schema.sql
pip install -r requirements-postgres.txt
python tools/postgres_etl.py

pip install dbt-core dbt-postgres
cp analytics/dbt/profiles.yml.example ~/.dbt/profiles.yml
cd analytics/dbt
dbt debug
dbt run
dbt test
```

The ETL currently registers two real-public PE cases. No synthetic
classification, case, or fallback is accepted. Connection settings in the
example profile use `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, and
`PGDATABASE`.

## Models

| Model | Grain | Purpose |
|---|---|---|
| `stg_deals` | deal | Source identity and status |
| `stg_deal_returns` | deal, period, metric | Long-form returns |
| `stg_deal_debt_schedule` | deal, period, metric | Long-form debt schedule |
| `mart_selected_exit_returns` | deal | Selected-exit MOIC, IRR, EV, and debt |
| `mart_leverage_path` | deal, period | Debt and cash trajectory |

## Controls

1. Sources accept `real_public` only.
2. Keys, classifications, return completeness, and economic bounds are tested.
3. A zero MOIC and `-100%` IRR are valid total-loss outcomes; tests reject
   negative MOIC or IRR below `-100%`, not legitimate distress.
4. Financial calculations remain in governed workbooks and independent Python
   reference engines.
5. New sources require committed public cases and receipt validation first.
