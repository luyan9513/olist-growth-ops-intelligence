select
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    c.customer_city,
    c.customer_state,
    o.order_status,
    o.purchased_at,
    o.approved_at,
    o.carrier_delivered_at,
    o.customer_delivered_at,
    o.estimated_delivery_at,
    p.payment_value,
    p.max_payment_installments,
    p.payment_types,
    r.review_id,
    r.review_score,
    r.review_created_at,
    r.review_record_count,
    r.is_low_review,
    o.customer_delivered_at is not null
        and o.estimated_delivery_at is not null
        and o.customer_delivered_at > o.estimated_delivery_at as is_delayed,
    case
        when o.customer_delivered_at is not null and o.purchased_at is not null
        then date_diff('day', o.purchased_at, o.customer_delivered_at)
    end as delivery_days,
    case
        when o.estimated_delivery_at is not null and o.purchased_at is not null
        then date_diff('day', o.purchased_at, o.estimated_delivery_at)
    end as promised_delivery_days
from {{ ref('stg_orders') }} o
left join {{ ref('stg_customers') }} c using (customer_id)
left join {{ ref('int_order_payments') }} p using (order_id)
left join {{ ref('int_order_reviews') }} r using (order_id)
