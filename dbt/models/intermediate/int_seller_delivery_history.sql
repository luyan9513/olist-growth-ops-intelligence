with events as (
    select
        i.seller_id,
        o.customer_delivered_at as event_at,
        1 as delivered_count,
        cast(o.is_delayed as integer) as delayed_count
    from {{ ref('int_order_seller_items') }} i
    inner join {{ ref('int_order_enriched') }} o using (order_id)
    where o.customer_delivered_at is not null
), by_time as (
    select seller_id, event_at, sum(delivered_count) as delivered_count, sum(delayed_count) as delayed_count
    from events
    group by seller_id, event_at
)

select
    seller_id,
    event_at,
    sum(delivered_count) over seller_history as historical_delivered_count,
    sum(delayed_count) over seller_history as historical_delayed_count
from by_time
window seller_history as (
    partition by seller_id order by event_at
    rows between unbounded preceding and current row
)
