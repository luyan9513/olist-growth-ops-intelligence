with ranked as (
    select
        mql_id,
        seller_id,
        won_at,
        business_segment,
        lead_type,
        lead_behaviour_profile,
        business_type,
        declared_product_catalog_size,
        declared_monthly_revenue,
        row_number() over (
            partition by mql_id
            order by won_at, seller_id
        ) as deal_rank,
        count(*) over (partition by mql_id) as deal_record_count,
        count(distinct seller_id) over (partition by mql_id) as seller_count
    from {{ ref('stg_closed_deals') }}
)

select * exclude (deal_rank)
from ranked
where deal_rank = 1
