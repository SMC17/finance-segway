-- Singular data test: every real_public deal in the selected-exit mart
-- must have a positive Sponsor MOIC.
-- This test does not require dbt_utils.

select
    deal_id,
    sponsor_moic
from {{ ref('mart_selected_exit_returns') }}
where classification = 'real_public'
  and (sponsor_moic is null or sponsor_moic <= 0)
