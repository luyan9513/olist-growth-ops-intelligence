with item_detail as (
    select
        i.order_id,
        i.seller_id,
        i.order_item_id,
        i.product_id,
        coalesce(p.category_name, 'unknown') as category_name,
        i.price,
        i.freight_value,
        i.shipping_limit_at,
        p.product_weight_g,
        p.product_length_cm * p.product_height_cm * p.product_width_cm as product_volume_cm3,
        p.product_description_length,
        p.product_photos_qty
    from {{ ref('stg_order_items') }} i
    left join {{ ref('stg_products') }} p using (product_id)
)

select
    order_id,
    seller_id,
    count(*) as item_count,
    count(distinct product_id) as product_count,
    count(distinct category_name) as category_count,
    arg_max(category_name, coalesce(price, 0) + coalesce(freight_value, 0)) as primary_category_name,
    string_agg(distinct category_name, ', ' order by category_name) as category_names,
    sum(price) as item_value,
    sum(freight_value) as freight_value,
    sum(price + freight_value) as gross_value,
    sum(product_weight_g) as total_product_weight_g,
    sum(product_volume_cm3) as total_product_volume_cm3,
    avg(product_description_length) as average_product_description_length,
    max(product_photos_qty) as max_product_photos_qty,
    max(shipping_limit_at) as shipping_limit_at
from item_detail
group by order_id, seller_id
