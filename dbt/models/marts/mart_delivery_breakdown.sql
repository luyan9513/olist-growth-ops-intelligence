with base as (
    select * from {{ ref('mart_delivery_experience') }}
), dimensions as (
    select 'category' as dimension_type, primary_category_name as dimension_value, * from base
    union all
    select 'seller_state', seller_state, * from base
    union all
    select 'customer_state', customer_state, * from base
)

select
    dimension_type,
    dimension_value,
    count(distinct order_id) as seller_order_count,
    sum(gross_value) filter (where order_status = 'delivered') as delivered_gmv,
    count(*) filter (where customer_delivered_at is not null and estimated_delivery_at is not null) as delivery_eligible_count,
    avg(cast(is_delayed as integer)) filter (
        where customer_delivered_at is not null and estimated_delivery_at is not null
    ) as delay_rate,
    count(*) filter (where review_score between 1 and 5) as reviewed_count,
    avg(cast(is_low_review as integer)) filter (where review_score between 1 and 5) as low_review_rate
from dimensions
group by dimension_type, dimension_value
