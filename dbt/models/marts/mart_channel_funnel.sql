with leads as (
    select
        date_trunc('month', m.first_contact_at)::date as contact_month,
        m.origin,
        m.mql_id,
        d.won_at,
        d.seller_id,
        d.won_at is not null and d.won_at >= m.first_contact_at as is_won,
        case when d.won_at >= m.first_contact_at then date_diff('day', m.first_contact_at, d.won_at) end as days_to_won
    from {{ ref('stg_marketing_qualified_leads') }} m
    left join {{ ref('int_lead_deals') }} d using (mql_id)
)

select
    contact_month,
    origin,
    count(*) as mql_count,
    count(*) filter (where is_won) as won_mql_count,
    count(distinct seller_id) filter (where is_won) as won_seller_count,
    count(*) filter (where is_won)::double / nullif(count(*), 0) as conversion_rate,
    median(days_to_won) filter (where is_won) as median_days_to_won
from leads
group by contact_month, origin
