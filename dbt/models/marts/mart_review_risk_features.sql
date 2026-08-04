with base as (
    select
        i.order_id,
        i.seller_id,
        o.purchased_at as prediction_at,
        i.primary_category_name,
        i.item_count,
        i.product_count,
        i.item_value,
        i.freight_value,
        i.gross_value,
        i.total_product_weight_g,
        i.total_product_volume_cm3,
        i.average_product_description_length,
        i.max_product_photos_qty,
        s.seller_state,
        o.customer_state,
        o.promised_delivery_days,
        o.payment_types,
        o.max_payment_installments,
        o.review_score,
        o.is_low_review
    from {{ ref('int_order_seller_items') }} i
    inner join {{ ref('int_order_enriched') }} o using (order_id)
    left join {{ ref('stg_sellers') }} s using (seller_id)
    where o.purchased_at is not null
      and o.review_score between 1 and 5
), with_delivery_history as (
    select b.*, h.historical_delivered_count, h.historical_delayed_count
    from base b
    asof left join {{ ref('int_seller_delivery_history') }} h
      on b.seller_id = h.seller_id and b.prediction_at > h.event_at
), with_all_history as (
    select d.*, r.historical_reviewed_count, r.historical_low_review_count, r.historical_review_score_sum
    from with_delivery_history d
    asof left join {{ ref('int_seller_review_history') }} r
      on d.seller_id = r.seller_id and d.prediction_at > r.event_at
), global_delivery_by_time as (
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
        sum(delivered_count) over (order by event_at rows between unbounded preceding and current row) as historical_delivered_count,
        sum(delayed_count) over (order by event_at rows between unbounded preceding and current row) as historical_delayed_count
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
        sum(reviewed_count) over (order by event_at rows between unbounded preceding and current row) as historical_reviewed_count,
        sum(low_review_count) over (order by event_at rows between unbounded preceding and current row) as historical_low_review_count
    from global_review_by_time
), with_global_delivery as (
    select
        h.*,
        g.historical_delivered_count as global_historical_delivered_count,
        g.historical_delayed_count as global_historical_delayed_count
    from with_all_history h
    asof left join global_delivery_history g
      on h.prediction_at > g.event_at
), with_global_history as (
    select
        d.*,
        g.historical_reviewed_count as global_historical_reviewed_count,
        g.historical_low_review_count as global_historical_low_review_count
    from with_global_delivery d
    asof left join global_review_history g
      on d.prediction_at > g.event_at
), order_level as (
    select
        order_id,
        prediction_at,
        arg_max(seller_id, gross_value) as primary_seller_id,
        count(*) as seller_count,
        count(*) > 1 as is_multi_seller,
        arg_max(primary_category_name, gross_value) as primary_category_name,
        sum(item_count) as item_count,
        sum(product_count) as product_count,
        sum(item_value) as item_value,
        sum(freight_value) as freight_value,
        sum(gross_value) as gross_value,
        sum(total_product_weight_g) as total_product_weight_g,
        sum(total_product_volume_cm3) as total_product_volume_cm3,
        sum(average_product_description_length * item_count) / nullif(sum(item_count), 0) as average_product_description_length,
        max(max_product_photos_qty) as max_product_photos_qty,
        arg_max(seller_state, gross_value) as seller_state,
        any_value(customer_state) as customer_state,
        any_value(promised_delivery_days) as promised_delivery_days,
        any_value(payment_types) as payment_types,
        any_value(max_payment_installments) as max_payment_installments,
        any_value(review_score) as review_score,
        any_value(is_low_review) as is_low_review,
        arg_max(coalesce(historical_delivered_count, 0), gross_value) as historical_delivered_count,
        arg_max(coalesce(historical_delayed_count, 0), gross_value) as historical_delayed_count,
        arg_max(coalesce(historical_reviewed_count, 0), gross_value) as historical_reviewed_count,
        arg_max(coalesce(historical_low_review_count, 0), gross_value) as historical_low_review_count,
        arg_max(coalesce(historical_review_score_sum, 0), gross_value) as historical_review_score_sum,
        any_value(global_historical_delivered_count) as global_historical_delivered_count,
        any_value(global_historical_delayed_count) as global_historical_delayed_count,
        any_value(global_historical_reviewed_count) as global_historical_reviewed_count,
        any_value(global_historical_low_review_count) as global_historical_low_review_count
    from with_global_history
    group by order_id, prediction_at
)

select
    * exclude (
        historical_delivered_count,
        historical_delayed_count,
        historical_reviewed_count,
        historical_low_review_count,
        historical_review_score_sum
    ),
    historical_delivered_count as seller_historical_delivered_count,
    historical_delayed_count as seller_historical_delayed_count,
    coalesce(historical_delayed_count, 0)::double / nullif(historical_delivered_count, 0) as seller_historical_delay_rate,
    coalesce(historical_reviewed_count, 0) as seller_historical_reviewed_count,
    historical_low_review_count as seller_historical_low_review_count,
    coalesce(historical_low_review_count, 0)::double / nullif(historical_reviewed_count, 0) as seller_historical_low_review_rate,
    historical_review_score_sum::double / nullif(historical_reviewed_count, 0) as seller_historical_average_review,
    global_historical_delayed_count::double / nullif(global_historical_delivered_count, 0) as global_historical_delay_rate,
    global_historical_low_review_count::double / nullif(global_historical_reviewed_count, 0) as global_historical_low_review_rate,
    (historical_delayed_count + 20 * global_historical_delayed_count::double / nullif(global_historical_delivered_count, 0))
        / nullif(historical_delivered_count + 20, 0) as seller_smoothed_delay_rate,
    (historical_low_review_count + 20 * global_historical_low_review_count::double / nullif(global_historical_reviewed_count, 0))
        / nullif(historical_reviewed_count + 20, 0) as seller_smoothed_low_review_rate,
    historical_delivered_count = 0 as is_delivery_history_cold_start,
    historical_reviewed_count = 0 as is_review_history_cold_start,
    extract(month from prediction_at) as purchase_month,
    extract(dow from prediction_at) as purchase_day_of_week,
    extract(hour from prediction_at) as purchase_hour,
    item_value / nullif(item_count, 0) as average_item_value,
    freight_value / nullif(gross_value, 0) as freight_ratio,
    seller_state <> customer_state as is_cross_state
from order_level
