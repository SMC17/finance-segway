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
where classification = 'real_public'
