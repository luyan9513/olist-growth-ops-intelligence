with checks as (
    select 'DQ-01' as rule_id, 'MQL 主键重复' as rule_name, 'error' as severity,
           count(*) as checked_count,
           count(*) - count(distinct mql_id) as issue_count
    from {{ ref('stg_marketing_qualified_leads') }}
    union all
    select 'DQ-02', '同一 MQL 多条成交', 'error',
           (select count(distinct mql_id) from {{ ref('stg_closed_deals') }}),
           coalesce(sum(record_count - 1), 0)
    from (
        select mql_id, count(*) as record_count
        from {{ ref('stg_closed_deals') }}
        group by mql_id
        having count(*) > 1
    )
    union all
    select 'DQ-03', '成交缺失 seller_id', 'error', count(*), count(*) filter (where seller_id is null)
    from {{ ref('stg_closed_deals') }}
    union all
    select 'DQ-04', '成交早于首次接触', 'warn', count(*), count(*) filter (where d.won_at < m.first_contact_at)
    from {{ ref('stg_closed_deals') }} d left join {{ ref('stg_marketing_qualified_leads') }} m using (mql_id)
    union all
    select 'DQ-05', '订单主键重复', 'error', count(*), count(*) - count(distinct order_id)
    from {{ ref('stg_orders') }}
    union all
    select 'DQ-06', '商品或运费为负', 'error', count(*), count(*) filter (where price < 0 or freight_value < 0)
    from {{ ref('stg_order_items') }}
    union all
    select 'DQ-07', '支付金额为负', 'error', count(*), count(*) filter (where payment_value < 0)
    from {{ ref('stg_order_payments') }}
    union all
    select 'DQ-08', '订单时间顺序异常', 'warn', count(*), count(*) filter (
        where carrier_delivered_at < purchased_at
           or customer_delivered_at < purchased_at
           or customer_delivered_at < carrier_delivered_at
    ) from {{ ref('stg_orders') }}
    union all
    select 'DQ-09', '评分不在 1-5', 'error', count(*), count(*) filter (where review_score not between 1 and 5)
    from {{ ref('stg_order_reviews') }}
    union all
    select 'DQ-10', '订单存在多条评价', 'warn',
           (select count(distinct order_id) from {{ ref('stg_order_reviews') }}),
           count(*)
    from (
        select order_id
        from {{ ref('stg_order_reviews') }}
        group by order_id
        having count(*) > 1
    )
    union all
    select 'DQ-11', '订单商品无法关联卖家', 'error', count(*), count(*) filter (where s.seller_id is null)
    from {{ ref('stg_order_items') }} i left join {{ ref('stg_sellers') }} s using (seller_id)
    union all
    select 'DQ-12', '订单无法关联客户', 'warn', count(*), count(*) filter (where c.customer_id is null)
    from {{ ref('stg_orders') }} o left join {{ ref('stg_customers') }} c using (customer_id)
    union all
    select 'DQ-13', '已交付订单缺少延迟判断时间', 'warn', count(*) filter (where order_status = 'delivered'),
           count(*) filter (where order_status = 'delivered' and (customer_delivered_at is null or estimated_delivery_at is null))
    from {{ ref('stg_orders') }}
    union all
    select 'DQ-14', '订单商品无法关联品类', 'warn', count(*), count(*) filter (where p.product_id is null or p.category_name = 'unknown')
    from {{ ref('stg_order_items') }} i left join {{ ref('stg_products') }} p using (product_id)
)

select
    rule_id,
    rule_name,
    severity,
    checked_count,
    issue_count,
    issue_count::double / nullif(checked_count, 0) as issue_rate,
    current_timestamp as run_at
from checks
