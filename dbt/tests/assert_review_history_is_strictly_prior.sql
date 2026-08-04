with global_delivery_by_time as (
    select
        customer_delivered_at as event_at,
        count(*) as delivered_count,
        sum(cast(is_delayed as integer)) as delayed_count
    from {{ ref('int_order_enriched') }}
    where customer_delivered_at is not null
    group by customer_delivered_at
), global_delivery_history as (
    select
        event_at,
        sum(delivered_count) over (order by event_at rows between unbounded preceding and current row) as delivered_count,
        sum(delayed_count) over (order by event_at rows between unbounded preceding and current row) as delayed_count
    from global_delivery_by_time
), global_review_by_time as (
    select
        review_created_at as event_at,
        count(*) as reviewed_count,
        sum(cast(is_low_review as integer)) as low_review_count
    from {{ ref('int_order_enriched') }}
    where review_created_at is not null
      and review_score between 1 and 5
    group by review_created_at
), global_review_history as (
    select
        event_at,
        sum(reviewed_count) over (order by event_at rows between unbounded preceding and current row) as reviewed_count,
        sum(low_review_count) over (order by event_at rows between unbounded preceding and current row) as low_review_count
    from global_review_by_time
), with_expected_delivery as (
    select
        m.*,
        d.delivered_count as expected_delivered_count,
        d.delayed_count as expected_delayed_count
    from {{ ref('mart_review_risk_features') }} m
    asof left join global_delivery_history d
      on m.prediction_at > d.event_at
), with_expected_history as (
    select
        d.*,
        r.reviewed_count as expected_reviewed_count,
        r.low_review_count as expected_low_review_count
    from with_expected_delivery d
    asof left join global_review_history r
      on d.prediction_at > r.event_at
)

select order_id
from with_expected_history
where coalesce(global_historical_delivered_count, 0) <> coalesce(expected_delivered_count, 0)
   or coalesce(global_historical_delayed_count, 0) <> coalesce(expected_delayed_count, 0)
   or coalesce(global_historical_reviewed_count, 0) <> coalesce(expected_reviewed_count, 0)
   or coalesce(global_historical_low_review_count, 0) <> coalesce(expected_low_review_count, 0)
