with events as (
    select
        i.seller_id,
        o.review_created_at as event_at,
        1 as reviewed_count,
        cast(o.is_low_review as integer) as low_review_count,
        o.review_score
    from {{ ref('int_order_seller_items') }} i
    inner join {{ ref('int_order_enriched') }} o using (order_id)
    where o.review_created_at is not null
      and o.review_score between 1 and 5
), by_time as (
    select
        seller_id,
        event_at,
        sum(reviewed_count) as reviewed_count,
        sum(low_review_count) as low_review_count,
        sum(review_score) as review_score_sum
    from events
    group by seller_id, event_at
)

select
    seller_id,
    event_at,
    sum(reviewed_count) over seller_history as historical_reviewed_count,
    sum(low_review_count) over seller_history as historical_low_review_count,
    sum(review_score_sum) over seller_history as historical_review_score_sum
from by_time
window seller_history as (
    partition by seller_id order by event_at
    rows between unbounded preceding and current row
)
