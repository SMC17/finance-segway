-- Equity IRR cannot be less than -100%; exactly -100% is a valid total loss.
select deal_id, sponsor_irr
from {{ ref('mart_selected_exit_returns') }}
where classification = 'real_public'
  and (sponsor_irr is null or sponsor_irr < -1)
