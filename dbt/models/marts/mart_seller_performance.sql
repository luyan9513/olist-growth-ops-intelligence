with seller_orders as (
    select
        i.seller_id,
        date_trunc('month', o.purchased_at)::date as order_month,
        i.order_id,
        i.gross_value,
        o.order_status,
        o.customer_delivered_at,
        o.estimated_delivery_at,
        o.is_delayed,
        o.review_score,
        o.is_low_review
    from {{ ref('int_order_seller_items') }} i
    inner join {{ ref('int_order_enriched') }} o using (order_id)
)

select
    so.seller_id,
    s.seller_city,
    s.seller_state,
    so.order_month,
    count(distinct so.order_id) as order_count,
    count(distinct so.order_id) filter (where so.order_status = 'delivered') as delivered_order_count,
    sum(so.gross_value) filter (where so.order_status = 'delivered') as delivered_gmv,
    avg(so.gross_value) filter (where so.order_status = 'delivered') as average_order_value,
    count(*) filter (
        where so.customer_delivered_at is not null and so.estimated_delivery_at is not null
    ) as delivery_eligible_count,
    avg(cast(so.is_delayed as integer)) filter (
        where so.customer_delivered_at is not null and so.estimated_delivery_at is not null
    ) as delay_rate,
    count(*) filter (where so.review_score between 1 and 5) as reviewed_order_count,
    avg(cast(so.is_low_review as integer)) filter (where so.review_score between 1 and 5) as low_review_rate,
    avg(so.review_score) filter (where so.review_score between 1 and 5) as average_review_score
from seller_orders so
left join {{ ref('stg_sellers') }} s using (seller_id)
group by so.seller_id, s.seller_city, s.seller_state, so.order_month
