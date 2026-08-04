-- Mart: leverage / deleveraging trajectory.
-- Grain: one row per (deal_id, period).
-- Mirrors the spirit of the SQL view v_deal_leverage_path but inside dbt.

with deals as (
    select deal_id, deal_name, classification
    from {{ ref('stg_deals') }}
),

debt as (
    select
        deal_id,
        period,
        period_order,
        max(case when metric = 'Total debt' then value end)  as total_debt,
        max(case when metric = 'Net debt' then value end)    as net_debt,
        max(case when metric = 'Ending cash' then value end) as ending_cash
    from {{ ref('stg_deal_debt_schedule') }}
    group by deal_id, period, period_order
)

select
    d.deal_id,
    d.deal_name,
    d.classification,
    debt.period,
    debt.period_order,
    debt.total_debt,
    debt.net_debt,
    debt.ending_cash
from deals d
join debt on debt.deal_id = d.deal_id
