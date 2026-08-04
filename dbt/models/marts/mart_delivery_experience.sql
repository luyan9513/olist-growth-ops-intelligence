with order_items as (
    select
        order_id,
        arg_max(seller_id, gross_value) as primary_seller_id,
        string_agg(seller_id, ', ' order by seller_id) as seller_ids,
        count(*) as seller_count,
        sum(item_count) as item_count,
        sum(gross_value) as gross_value,
        arg_max(primary_category_name, gross_value) as primary_category_name
    from {{ ref('int_order_seller_items') }}
    group by order_id
)

select
    i.order_id,
    i.primary_seller_id as seller_id,
    i.seller_ids,
    i.seller_count,
    i.seller_count > 1 as is_multi_seller,
    s.seller_city,
    s.seller_state,
    o.customer_state,
    i.primary_category_name,
    i.item_count,
    i.gross_value,
    o.order_status,
    o.purchased_at,
    o.carrier_delivered_at,
    o.customer_delivered_at,
    o.estimated_delivery_at,
    o.delivery_days,
    o.promised_delivery_days,
    o.is_delayed,
    o.review_score,
    o.is_low_review,
    o.review_created_at
from order_items i
inner join {{ ref('int_order_enriched') }} o using (order_id)
left join {{ ref('stg_sellers') }} s on i.primary_seller_id = s.seller_id
