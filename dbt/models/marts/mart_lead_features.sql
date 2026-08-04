select
    m.mql_id,
    m.first_contact_at as prediction_at,
    m.origin,
    m.landing_page_id,
    m.is_origin_missing,
    extract(year from m.first_contact_at)::integer as contact_year,
    extract(month from m.first_contact_at)::integer as contact_month,
    extract(dow from m.first_contact_at)::integer as contact_day_of_week,
    d.won_at is not null and d.won_at >= m.first_contact_at as is_won
from {{ ref('stg_marketing_qualified_leads') }} m
left join {{ ref('int_lead_deals') }} d using (mql_id)
