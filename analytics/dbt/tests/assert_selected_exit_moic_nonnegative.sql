-- A zero MOIC is a valid total-loss outcome; a negative MOIC is impossible.
select deal_id, sponsor_moic
from {{ ref('mart_selected_exit_returns') }}
where classification = 'real_public'
  and (sponsor_moic is null or sponsor_moic < 0)
