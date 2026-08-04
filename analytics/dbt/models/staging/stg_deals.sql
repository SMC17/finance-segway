-- Staging model for the core deals table.
-- Grain: one row per deal_id.
-- Source: public.finance_segway.deals (or the schema where postgres_etl loaded the data).

with source as (
    select * from {{ source('finance_segway', 'deals') }}
)

select
    deal_id,
    deal_name,
    classification,
    sponsor,
    entry_date,
    active_scenario,
    overall_check_status,
    workbook_path,
    source_domain,
    last_synced_at
from source
