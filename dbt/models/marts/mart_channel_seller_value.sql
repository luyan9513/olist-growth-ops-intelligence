select
    a.origin,
    p.order_month,
    count(distinct a.seller_id) as acquired_seller_count,
    sum(p.delivered_gmv) as delivered_gmv,
    sum(p.delivered_order_count) as delivered_order_count,
    sum(p.delivered_gmv) / nullif(count(distinct a.seller_id), 0) as gmv_per_acquired_seller,
    sum(p.delay_rate * p.delivery_eligible_count) / nullif(sum(p.delivery_eligible_count), 0) as delay_rate,
    sum(p.low_review_rate * p.reviewed_order_count) / nullif(sum(p.reviewed_order_count), 0) as low_review_rate
from {{ ref('int_seller_acquisition') }} a
inner join {{ ref('mart_seller_performance') }} p using (seller_id)
where p.order_month >= date_trunc('month', a.won_at)::date
group by a.origin, p.order_month
