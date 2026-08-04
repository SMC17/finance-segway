-- Postgres portfolio layer -- schema for cross-portfolio SQL analytics on
-- top of the Excel LBO/PE deal instances in 03_Private_Equity/instances/.
--
-- Design principle: Excel remains the calculation engine. Every number in
-- these tables is read directly from a workbook already committed and
-- recalculated -- nothing here is a SQL re-implementation of an IRR solve,
-- a cash sweep cascade, or a returns waterfall, and nothing here mutates
-- or re-recalculates the source workbook (real-public instances are frozen,
-- dated evidence; re-running them would break that). This is a query/
-- reporting layer fed by already-verified output, not a second, parallel
-- calculation engine. See tools/postgres_etl.py for the extraction logic
-- and db/README.md for setup + example analyst queries.
--
-- v2: rebuilt against the post-institutional-rebuild workbook layout
-- (Cover / Institutional Surface / Challenge Log / Lineage Map /
-- Assumptions / Sources & Uses / Operating Model / Debt Schedule /
-- Covenants / Management Equity / Returns Waterfall / Sensitivity /
-- Checks / Sources / RefreshLog). v1 targeted a since-replaced layout
-- (03_Private_Equity/deals/*.xlsx, "Returns" + "Debt Schedule" sheets)
-- that no longer exists anywhere in the repo -- label-driven extraction
-- this time specifically so the next workbook restructuring doesn't
-- silently break every hardcoded cell reference again.
--
-- Run: psql -d finance_segway -f db/schema.sql

BEGIN;

DROP VIEW IF EXISTS v_deal_downside_sensitivity;
DROP VIEW IF EXISTS v_deal_summary;
DROP VIEW IF EXISTS v_deal_headline;
DROP TABLE IF EXISTS deal_debt_schedule;
DROP TABLE IF EXISTS deal_returns;
DROP TABLE IF EXISTS deal_sources_uses;
DROP TABLE IF EXISTS deal_assumptions;
DROP TABLE IF EXISTS deals;

CREATE TABLE deals (
    deal_id              TEXT PRIMARY KEY,        -- e.g. 'home_depot_2023' (matches the workbook filename stem)
    deal_name            TEXT NOT NULL,            -- Cover!C4, e.g. 'The Home Depot FY2023 public-company operating case'
    classification       TEXT NOT NULL CHECK (classification IN ('real_public', 'synthetic_benchmark')),
    sponsor              TEXT,
    entry_date           TEXT,                     -- kept as text: real instances carry actual dates, some fields are still "[date]" placeholders
    active_scenario      TEXT,                     -- Cover!C9, e.g. 'Base'
    overall_check_status TEXT,                     -- Checks sheet's "Overall" row -- PASS/REVIEW/FAIL
    workbook_path        TEXT NOT NULL,            -- repo-relative path to the source .xlsx
    source_domain        TEXT NOT NULL DEFAULT 'lbo-pe-mb',  -- standards/model_inventory.json id
    last_synced_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row per (deal, assumption label). Base/Downside/Active columns
-- preserved as separate fields rather than flattened, since comparing
-- across scenarios on the same row is a common analyst query.
CREATE TABLE deal_assumptions (
    deal_id     TEXT NOT NULL REFERENCES deals(deal_id) ON DELETE CASCADE,
    assumption  TEXT NOT NULL,           -- e.g. 'Entry EBITDA multiple'
    base        NUMERIC,
    downside    NUMERIC,
    active      NUMERIC,
    units       TEXT,                    -- e.g. '%', '$mm', 'x'
    PRIMARY KEY (deal_id, assumption)
);

CREATE TABLE deal_sources_uses (
    deal_id     TEXT NOT NULL REFERENCES deals(deal_id) ON DELETE CASCADE,
    side        TEXT NOT NULL CHECK (side IN ('Sources', 'Uses')),
    line_item   TEXT NOT NULL,
    amount      NUMERIC NOT NULL,
    PRIMARY KEY (deal_id, side, line_item)
);

-- Long/EAV format rather than fixed year columns: the whole point of this
-- rebuild was that a v1 schema hardcoded to specific columns broke the
-- instant the workbook's own layout changed. (deal_id, period, metric) is
-- read directly from each sheet's own row labels and column headers, so
-- it survives a template redesign without a rewrite -- new rows/columns
-- just show up as new metric/period values, nothing to migrate.
CREATE TABLE deal_debt_schedule (
    deal_id       TEXT NOT NULL REFERENCES deals(deal_id) ON DELETE CASCADE,
    period        TEXT NOT NULL,          -- 'Close', 'Year 1', ..., 'Year 7'
    period_order  INTEGER NOT NULL,       -- 0 for Close, 1..7 for Year N -- for ORDER BY without a text-sort footgun
    metric        TEXT NOT NULL,          -- e.g. 'Ending TLB', 'Total debt', 'Net debt'
    value         NUMERIC,
    PRIMARY KEY (deal_id, period, metric)
);

CREATE TABLE deal_returns (
    deal_id           TEXT NOT NULL REFERENCES deals(deal_id) ON DELETE CASCADE,
    period            TEXT NOT NULL,      -- 'Year 1', ..., 'Year 7', 'Selected exit'
    is_selected_exit  BOOLEAN NOT NULL DEFAULT FALSE,
    metric            TEXT NOT NULL,      -- e.g. 'Sponsor MOIC', 'Sponsor IRR', 'Exit enterprise value'
    value             NUMERIC,
    PRIMARY KEY (deal_id, period, metric)
);

CREATE INDEX idx_deal_debt_schedule_metric ON deal_debt_schedule(metric);
CREATE INDEX idx_deal_returns_metric ON deal_returns(metric);
CREATE INDEX idx_deal_returns_selected ON deal_returns(is_selected_exit) WHERE is_selected_exit;
CREATE INDEX idx_deals_classification ON deals(classification);

-- Analyst-facing headline view: one row per deal, pivoting the selected-
-- exit metrics an analyst actually wants without hand-writing a CASE
-- expression every time.
CREATE VIEW v_deal_headline AS
SELECT
    d.deal_id,
    d.deal_name,
    d.classification,
    d.sponsor,
    d.active_scenario,
    d.overall_check_status,
    MAX(CASE WHEN r.metric = 'Exit EBITDA' THEN r.value END)             AS exit_ebitda,
    MAX(CASE WHEN r.metric = 'Exit multiple' THEN r.value END)           AS exit_multiple,
    MAX(CASE WHEN r.metric = 'Exit enterprise value' THEN r.value END)   AS exit_ev,
    MAX(CASE WHEN r.metric = 'Net debt' THEN r.value END)                AS exit_net_debt,
    MAX(CASE WHEN r.metric = 'Sponsor proceeds' THEN r.value END)        AS sponsor_proceeds,
    MAX(CASE WHEN r.metric = 'Sponsor MOIC' THEN r.value END)            AS sponsor_moic,
    MAX(CASE WHEN r.metric = 'Sponsor IRR' THEN r.value END)             AS sponsor_irr
FROM deals d
LEFT JOIN deal_returns r ON r.deal_id = d.deal_id AND r.is_selected_exit
GROUP BY d.deal_id, d.deal_name, d.classification, d.sponsor, d.active_scenario, d.overall_check_status;

-- Leverage trajectory (one row per deal x period) -- the deleveraging
-- path query, pivoted so year-over-year comparison doesn't need a join.
CREATE VIEW v_deal_leverage_path AS
SELECT
    d.deal_id,
    d.deal_name,
    ds.period,
    ds.period_order,
    MAX(CASE WHEN ds.metric = 'Total debt' THEN ds.value END) AS total_debt,
    MAX(CASE WHEN ds.metric = 'Net debt' THEN ds.value END) AS net_debt,
    MAX(CASE WHEN ds.metric = 'Ending cash' THEN ds.value END) AS ending_cash
FROM deals d
JOIN deal_debt_schedule ds ON ds.deal_id = d.deal_id
GROUP BY d.deal_id, d.deal_name, ds.period, ds.period_order
ORDER BY d.deal_id, ds.period_order;

COMMIT;
