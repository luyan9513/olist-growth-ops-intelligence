with candidates as (
    select
        d.seller_id,
        d.mql_id,
        d.won_at,
        m.first_contact_at,
        m.origin,
        row_number() over (
            partition by d.seller_id
            order by d.won_at, m.first_contact_at, d.mql_id
        ) as acquisition_rank,
        count(*) over (partition by d.seller_id) as mapped_mql_count
    from {{ ref('int_lead_deals') }} d
    inner join {{ ref('stg_marketing_qualified_leads') }} m using (mql_id)
    where d.seller_id is not null
      and d.won_at >= m.first_contact_at
)

select * exclude (acquisition_rank)
from candidates
where acquisition_rank = 1
