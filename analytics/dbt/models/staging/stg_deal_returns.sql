-- Staging model for deal_returns (long/EAV format).
-- Grain: one row per (deal_id, period, metric).

with source as (
    select * from {{ source('finance_segway', 'deal_returns') }}
)

select
    deal_id,
    period,
    is_selected_exit,
    metric,
    value
from source
