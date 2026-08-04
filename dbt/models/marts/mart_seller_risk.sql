with aggregated as (
    select
        seller_id,
        any_value(seller_city) as seller_city,
        any_value(seller_state) as seller_state,
        sum(delivered_gmv) as delivered_gmv,
        sum(delivered_order_count) as delivered_order_count,
        sum(delay_rate * delivery_eligible_count) / nullif(sum(delivery_eligible_count), 0) as delay_rate,
        sum(low_review_rate * reviewed_order_count) / nullif(sum(reviewed_order_count), 0) as low_review_rate,
        sum(delivery_eligible_count) as delivery_eligible_count,
        sum(reviewed_order_count) as reviewed_order_count
    from {{ ref('mart_seller_performance') }}
    group by seller_id
), value_scored as (
    select
        *,
        percent_rank() over (order by delivered_gmv) as gmv_percentile
    from aggregated
), delay_scored as (
    select
        seller_id,
        percent_rank() over (order by delay_rate) as delay_percentile
    from aggregated
    where delivery_eligible_count >= 20
), review_scored as (
    select
        seller_id,
        percent_rank() over (order by low_review_rate) as low_review_percentile
    from aggregated
    where reviewed_order_count >= 20
), scored as (
    select
        v.*,
        d.delay_percentile,
        r.low_review_percentile
    from value_scored v
    left join delay_scored d using (seller_id)
    left join review_scored r using (seller_id)
)

select
    *,
    (delivery_eligible_count >= 20 or reviewed_order_count >= 20) as is_experience_rate_reliable,
    case
        when gmv_percentile >= 0.75 and (coalesce(delay_percentile, 0) >= 0.75 or coalesce(low_review_percentile, 0) >= 0.75)
            then '高价值高风险'
        when gmv_percentile >= 0.75 then '高价值'
        when coalesce(delay_percentile, 0) >= 0.75 or coalesce(low_review_percentile, 0) >= 0.75 then '体验风险'
        else '常规关注'
    end as seller_segment,
    concat_ws(', ',
        case when gmv_percentile >= 0.75 then 'GMV较高' end,
        case when delay_percentile >= 0.75 then '延迟率较高（样本≥20）' end,
        case when low_review_percentile >= 0.75 then '低评分率较高（样本≥20）' end
    ) as risk_reasons
from scored
