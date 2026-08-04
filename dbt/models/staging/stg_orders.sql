select
    nullif(trim(order_id), '') as order_id,
    nullif(trim(customer_id), '') as customer_id,
    coalesce(nullif(trim(order_status), ''), 'unknown') as order_status,
    try_cast(order_purchase_timestamp as timestamp) as purchased_at,
    try_cast(order_approved_at as timestamp) as approved_at,
    try_cast(order_delivered_carrier_date as timestamp) as carrier_delivered_at,
    try_cast(order_delivered_customer_date as timestamp) as customer_delivered_at,
    try_cast(order_estimated_delivery_date as timestamp) as estimated_delivery_at
from {{ source('olist_raw', 'orders') }}
