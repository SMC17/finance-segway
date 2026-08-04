-- Optional Postgres query layer for source-addressed public workbook outputs.
-- Excel remains the calculation engine; this schema stores committed results.

BEGIN;

DROP VIEW IF EXISTS v_deal_leverage_path;
DROP VIEW IF EXISTS v_deal_headline;
DROP TABLE IF EXISTS deal_debt_schedule;
DROP TABLE IF EXISTS deal_returns;
DROP TABLE IF EXISTS deal_sources_uses;
DROP TABLE IF EXISTS deal_assumptions;
DROP TABLE IF EXISTS deals;

CREATE TABLE deals (
    deal_id              TEXT PRIMARY KEY,
    deal_name            TEXT NOT NULL,
    classification       TEXT NOT NULL DEFAULT 'real_public'
                         CHECK (classification = 'real_public'),
    sponsor              TEXT,
    entry_date           TEXT,
    active_scenario      TEXT,
    overall_check_status TEXT,
    workbook_path        TEXT NOT NULL,
    source_domain        TEXT NOT NULL DEFAULT 'lbo-pe-mb',
    last_synced_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE deal_assumptions (
    deal_id     TEXT NOT NULL REFERENCES deals(deal_id) ON DELETE CASCADE,
    assumption  TEXT NOT NULL,
    base        NUMERIC,
    downside    NUMERIC,
    active      NUMERIC,
    units       TEXT,
    PRIMARY KEY (deal_id, assumption)
);

CREATE TABLE deal_sources_uses (
    deal_id     TEXT NOT NULL REFERENCES deals(deal_id) ON DELETE CASCADE,
    side        TEXT NOT NULL CHECK (side IN ('Sources', 'Uses')),
    line_item   TEXT NOT NULL,
    amount      NUMERIC NOT NULL,
    PRIMARY KEY (deal_id, side, line_item)
);

CREATE TABLE deal_debt_schedule (
    deal_id       TEXT NOT NULL REFERENCES deals(deal_id) ON DELETE CASCADE,
    period        TEXT NOT NULL,
    period_order  INTEGER NOT NULL,
    metric        TEXT NOT NULL,
    value         NUMERIC,
    PRIMARY KEY (deal_id, period, metric)
);

CREATE TABLE deal_returns (
    deal_id           TEXT NOT NULL REFERENCES deals(deal_id) ON DELETE CASCADE,
    period            TEXT NOT NULL,
    is_selected_exit  BOOLEAN NOT NULL DEFAULT FALSE,
    metric            TEXT NOT NULL,
    value             NUMERIC,
    PRIMARY KEY (deal_id, period, metric)
);

CREATE INDEX idx_deal_debt_schedule_metric ON deal_debt_schedule(metric);
CREATE INDEX idx_deal_returns_metric ON deal_returns(metric);
CREATE INDEX idx_deal_returns_selected ON deal_returns(is_selected_exit)
    WHERE is_selected_exit;

CREATE VIEW v_deal_headline AS
SELECT
    d.deal_id,
    d.deal_name,
    d.sponsor,
    d.active_scenario,
    d.overall_check_status,
    MAX(CASE WHEN r.metric = 'Exit EBITDA' THEN r.value END) AS exit_ebitda,
    MAX(CASE WHEN r.metric = 'Exit multiple' THEN r.value END) AS exit_multiple,
    MAX(CASE WHEN r.metric = 'Exit enterprise value' THEN r.value END) AS exit_ev,
    MAX(CASE WHEN r.metric = 'Net debt' THEN r.value END) AS exit_net_debt,
    MAX(CASE WHEN r.metric = 'Sponsor proceeds' THEN r.value END) AS sponsor_proceeds,
    MAX(CASE WHEN r.metric = 'Sponsor MOIC' THEN r.value END) AS sponsor_moic,
    MAX(CASE WHEN r.metric = 'Sponsor IRR' THEN r.value END) AS sponsor_irr
FROM deals d
LEFT JOIN deal_returns r ON r.deal_id = d.deal_id AND r.is_selected_exit
GROUP BY d.deal_id, d.deal_name, d.sponsor, d.active_scenario,
         d.overall_check_status;

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
GROUP BY d.deal_id, d.deal_name, ds.period, ds.period_order;

COMMIT;
