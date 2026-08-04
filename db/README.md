# Postgres portfolio layer

This optional layer supports cross-portfolio SQL analysis of committed Excel
outputs. The pilot covers the two source-addressed Private Equity / LBO cases
in `03_Private_Equity/instances/`:

- Home Depot FY2023;
- Macy's FY2020 adversarial case.

Synthetic cases are neither registered nor accepted. Extend `DEALS` in
`tools/postgres_etl.py` only with committed, source-addressed public cases.

## Design boundary

Excel remains the calculation engine and evidence record. Postgres is a query
layer only: it reads cached results from already recalculated workbooks and
does not recalculate, mutate, or reproduce financial formulas in SQL.

Extraction is label-driven rather than coordinate-driven. Debt schedules and
returns use long-form `(deal_id, period, metric, value)` records so ordinary
template changes do not silently redirect fixed cell references.

## Setup

```bash
createdb finance_segway
psql -d finance_segway -f db/schema.sql
pip install -r requirements-postgres.txt
python3 tools/postgres_etl.py
```

`python3 tools/postgres_etl.py --dry-run` verifies extraction without a
database write. `tools/verify_postgres_etl.py` re-extracts each registered
workbook and compares it with the database. That is an ETL-integrity check,
not a second financial oracle; independent financial oracles live in
`tools/verify_reference_calcs.py`.

Connection defaults to `dbname=finance_segway`. Override it with `--dsn` or
`FINANCE_SEGWAY_PG_DSN`.

## Schema

- `deals` — source workbook identity and workbook check status.
- `deal_assumptions` — Base, Downside, and Active values by label.
- `deal_sources_uses` — sources and uses at entry.
- `deal_debt_schedule` — long-form debt and cash metrics by period.
- `deal_returns` — long-form return metrics and selected-exit flag.
- `v_deal_headline` — selected-exit MOIC, IRR, EV, and net debt.
- `v_deal_leverage_path` — debt and cash trajectory by period.

## Example queries

```sql
SELECT deal_id, deal_name, sponsor_moic, sponsor_irr, overall_check_status
FROM v_deal_headline
ORDER BY deal_id;
```

```sql
SELECT period, total_debt, net_debt, ending_cash
FROM v_deal_leverage_path
WHERE deal_id = 'home_depot_2023'
ORDER BY period_order;
```

```sql
SELECT deal_id, assumption, base, downside, active, units
FROM deal_assumptions
WHERE assumption = 'Entry EBITDA multiple'
ORDER BY deal_id;
```

## Known limitations

- Pilot scope is two source-addressed LBO/PE cases.
- It loads committed outputs, not the workbook formula graph.
- Sync is full-registry upsert, not incremental change capture.
- Removed registry entries are pruned by the ETL, but schema initialization
  remains destructive and should run only in a dedicated database.
