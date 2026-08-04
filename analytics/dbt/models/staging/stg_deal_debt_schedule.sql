with source as (
    select * from {{ source('finance_segway', 'deal_debt_schedule') }}
)

select deal_id, period, period_order, metric, value
from source
