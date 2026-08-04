select
    nullif(trim(order_id), '') as order_id,
    try_cast(payment_sequential as integer) as payment_sequence,
    coalesce(nullif(trim(payment_type), ''), 'unknown') as payment_type,
    try_cast(payment_installments as integer) as payment_installments,
    try_cast(payment_value as double) as payment_value
from {{ source('olist_raw', 'order_payments') }}
