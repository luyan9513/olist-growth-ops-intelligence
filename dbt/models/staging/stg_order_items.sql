select
    nullif(trim(order_id), '') as order_id,
    try_cast(order_item_id as integer) as order_item_id,
    nullif(trim(product_id), '') as product_id,
    nullif(trim(seller_id), '') as seller_id,
    try_cast(shipping_limit_date as timestamp) as shipping_limit_at,
    try_cast(price as double) as price,
    try_cast(freight_value as double) as freight_value
from {{ source('olist_raw', 'order_items') }}
