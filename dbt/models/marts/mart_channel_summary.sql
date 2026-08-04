with seller_lifetime as (
    select
        seller_id,
        sum(delivered_gmv) as delivered_gmv,
        sum(delivered_order_count) as delivered_order_count,
        sum(delay_rate * delivery_eligible_count) as delayed_order_count,
        sum(delivery_eligible_count) as delivery_eligible_count,
        sum(low_review_rate * reviewed_order_count) as low_review_order_count,
        sum(reviewed_order_count) as reviewed_order_count
    from {{ ref('mart_seller_performance') }}
    group by seller_id
)

select
    a.origin,
    count(distinct a.seller_id) as acquired_seller_count,
    count(distinct l.seller_id) filter (where l.delivered_order_count > 0) as active_seller_count,
    sum(coalesce(l.delivered_gmv, 0)) as delivered_gmv,
    sum(coalesce(l.delivered_order_count, 0)) as delivered_order_count,
    sum(coalesce(l.delivered_gmv, 0)) / nullif(count(distinct a.seller_id), 0) as gmv_per_acquired_seller,
    sum(l.delayed_order_count) / nullif(sum(l.delivery_eligible_count), 0) as delay_rate,
    sum(l.low_review_order_count) / nullif(sum(l.reviewed_order_count), 0) as low_review_rate
from {{ ref('int_seller_acquisition') }} a
left join seller_lifetime l using (seller_id)
group by a.origin
