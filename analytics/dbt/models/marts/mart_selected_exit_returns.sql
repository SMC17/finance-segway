-- Mart: one row per deal with the selected-exit headline metrics an analyst actually wants.
-- Grain: one row per deal_id.
-- Only real_public deals are included by default (controlled by the project var).

with deals as (
    select * from {{ ref('stg_deals') }}
    where classification in ({{ "'" ~ var('evidence_classifications') | join("','") ~ "'" }})
),

selected as (
    select
        deal_id,
        max(case when metric = 'Exit EBITDA' then value end)             as exit_ebitda,
        max(case when metric = 'Exit multiple' then value end)           as exit_multiple,
        max(case when metric = 'Exit enterprise value' then value end)   as exit_ev,
        max(case when metric = 'Net debt' then value end)                as exit_net_debt,
        max(case when metric = 'Sponsor proceeds' then value end)        as sponsor_proceeds,
        max(case when metric = 'Sponsor MOIC' then value end)            as sponsor_moic,
        max(case when metric = 'Sponsor IRR' then value end)             as sponsor_irr
    from {{ ref('stg_deal_returns') }}
    where is_selected_exit
    group by deal_id
)

select
    d.deal_id,
    d.deal_name,
    d.classification,
    d.sponsor,
    d.active_scenario,
    d.overall_check_status,
    s.exit_ebitda,
    s.exit_multiple,
    s.exit_ev,
    s.exit_net_debt,
    s.sponsor_proceeds,
    s.sponsor_moic,
    s.sponsor_irr
from deals d
left join selected s on s.deal_id = d.deal_id
