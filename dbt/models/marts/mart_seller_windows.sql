with anchor as (
    select max(purchased_at) as data_as_of_at
    from {{ ref('int_order_enriched') }}
), seller_orders as (
    select
        i.seller_id,
        i.order_id,
        o.purchased_at,
        o.order_status,
        i.gross_value,
        o.is_delayed,
        o.customer_delivered_at,
        o.estimated_delivery_at,
        o.is_low_review,
        o.review_score,
        a.data_as_of_at
    from {{ ref('int_order_seller_items') }} i
    inner join {{ ref('int_order_enriched') }} o using (order_id)
    cross join anchor a
), aggregated as (
    select
        seller_id,
        data_as_of_at,
        count(distinct order_id) filter (where purchased_at > data_as_of_at - interval 30 day) as orders_30d,
        count(distinct order_id) filter (where purchased_at > data_as_of_at - interval 60 day) as orders_60d,
        count(distinct order_id) filter (where purchased_at > data_as_of_at - interval 90 day) as orders_90d,
        sum(gross_value) filter (where order_status = 'delivered' and purchased_at > data_as_of_at - interval 30 day) as gmv_30d,
        sum(gross_value) filter (where order_status = 'delivered' and purchased_at > data_as_of_at - interval 60 day) as gmv_60d,
        sum(gross_value) filter (where order_status = 'delivered' and purchased_at > data_as_of_at - interval 90 day) as gmv_90d,
        avg(cast(is_delayed as integer)) filter (
            where customer_delivered_at is not null and estimated_delivery_at is not null
              and purchased_at > data_as_of_at - interval 90 day
        ) as delay_rate_90d,
        avg(cast(is_low_review as integer)) filter (
            where review_score between 1 and 5 and purchased_at > data_as_of_at - interval 90 day
        ) as low_review_rate_90d
    from seller_orders
    group by seller_id, data_as_of_at
)

select
    *,
    percent_rank() over (order by coalesce(gmv_90d, 0)) as gmv_90d_percentile,
    percent_rank() over (order by coalesce(orders_90d, 0)) as orders_90d_percentile
from aggregated
