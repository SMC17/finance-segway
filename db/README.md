# Postgres portfolio layer

A cross-portfolio SQL query layer on top of the Excel LBO/PE deal instances
in `03_Private_Equity/instances/`. Pilot scope: Private Equity / LBO, the
domain with the deepest set of populated instances (2 real-public dated
cases -- Home Depot FY2023, Macy's FY2020 -- plus 2 synthetic benchmarks).
Extend `DEALS` in `tools/postgres_etl.py` as other domains build out the
same instance depth.

## Design principle: Excel is the calculation engine, Postgres is the query layer

Every number in this database is read directly from a workbook that is
already committed, dated, and recalculated -- nothing here re-implements
an IRR solve, a cash sweep cascade, or a returns waterfall in SQL, and
nothing here mutates or re-recalculates the source workbook. Real-public
instances are frozen, dated evidence (see each domain's `sources/` and
receipt files) -- re-running them through a solver would break that
guarantee. This is a reporting layer fed by already-verified output, not
a parallel calculation engine that could drift from the spreadsheets.

**Extraction is label-driven, not coordinate-driven.** `tools/postgres_etl.py`
reads each sheet by scanning its own row labels and column headers (see
`read_labeled_table`), not by hardcoded cell references. The first version
of this layer hardcoded `03_Private_Equity/deals/*.xlsx` and fixed cell
addresses inside a `"Returns"` / `"Debt Schedule"` sheet pair; a later,
independent institutional rebuild of the whole workbook (different sheet
names, different layout, moved to `instances/`) silently broke every one
of those references. `deal_debt_schedule` and `deal_returns` are stored in
long/EAV format (`deal_id, period, metric, value`) specifically so the next
template restructuring adds or renames metrics without invalidating the
schema -- there's no fixed column to break.

## Setup

```bash
createdb finance_segway                          # or: psql -c "CREATE DATABASE finance_segway;"
psql -d finance_segway -f db/schema.sql
pip install psycopg2-binary
python3 tools/postgres_etl.py                     # loads all 4 registered deals
```

`tools/postgres_etl.py --dry-run` extracts and prints without touching the
database. `tools/verify_postgres_etl.py` re-extracts fresh from the
workbooks and diffs against what's stored -- a standing smoke test for ETL
bugs (not a financial-correctness oracle; the workbook's committed cells
are the ground truth here, see the design principle above).

Connection defaults to `dbname=finance_segway` (peer/local auth). Override
with `--dsn` or the `FINANCE_SEGWAY_PG_DSN` environment variable.

## Schema

- `deals` — one row per deal: name, classification (`real_public` vs. `synthetic_benchmark`), sponsor, active scenario, overall Checks-sheet status.
- `deal_assumptions` — one row per (deal, assumption label): Base / Downside / Active columns preserved separately.
- `deal_sources_uses` — Sources & Uses line items at entry.
- `deal_debt_schedule` — long format: one row per (deal, period, metric) -- e.g. `('home_depot_2023', 'Year 3', 'Total debt', 115534.77)`.
- `deal_returns` — long format: one row per (deal, period, metric), with `is_selected_exit` flagging the workbook's own chosen exit year.
- `v_deal_headline` — analyst-facing pivot of the selected-exit metrics (MOIC, IRR, exit EV, net debt) an analyst actually wants, no manual `CASE` needed.
- `v_deal_leverage_path` — deleveraging trajectory pivoted by period, per deal.

## Example queries

Cross-portfolio headline view:

```sql
SELECT deal_id, deal_name, classification, sponsor_moic, sponsor_irr, overall_check_status
FROM v_deal_headline
ORDER BY classification, deal_id;
```

Only real, source-addressed deals (excluding synthetic benchmarks):

```sql
SELECT deal_id, deal_name, sponsor_moic, sponsor_irr
FROM v_deal_headline
WHERE classification = 'real_public'
ORDER BY sponsor_irr DESC;
```

Leverage (deleveraging) trajectory for one deal:

```sql
SELECT period, total_debt, net_debt, ending_cash
FROM v_deal_leverage_path
WHERE deal_id = 'home_depot_2023'
ORDER BY period_order;
```

Compare Base vs. Downside on a specific assumption across the whole portfolio:

```sql
SELECT deal_id, assumption, base, downside, active, units
FROM deal_assumptions
WHERE assumption = 'Entry EBITDA multiple'
ORDER BY deal_id;
```

Sources & Uses for one deal:

```sql
SELECT side, line_item, amount
FROM deal_sources_uses
WHERE deal_id = 'home_depot_2023'
ORDER BY side, line_item;
```

## Known limitations

- Pilot scope: LBO/PE only, 4 deals (2 real, 2 synthetic). Other domains
  don't have the same instance depth yet.
- The synthetic-benchmark classification exists because, at the time this
  was built, a separate in-flight change was retiring the whole synthetic-
  benchmark evidence system in favor of real-only source-addressed cases.
  If/when that lands, re-run `tools/postgres_etl.py` after updating the
  `DEALS` registry -- the schema and `classification` column already
  anticipate that split, but stale synthetic rows won't auto-delete
  themselves if their source files disappear.
- This loads pre-computed OUTPUTS (returns, debt schedule), not the full
  formula graph -- it's a reporting/query layer, not a substitute for
  opening the workbook to change an assumption.
- No incremental sync: re-running the ETL fully re-extracts and upserts
  every registered deal each time. Fine at this scale.
