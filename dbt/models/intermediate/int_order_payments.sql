select
    order_id,
    sum(payment_value) as payment_value,
    max(payment_installments) as max_payment_installments,
    count(*) as payment_record_count,
    string_agg(distinct payment_type, ', ' order by payment_type) as payment_types
from {{ ref('stg_order_payments') }}
group by order_id
