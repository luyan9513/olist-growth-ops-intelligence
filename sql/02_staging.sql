-- staging 由 dbt 模型实现。本查询用于构建后快速核对各层行数。
select 'stg_marketing_qualified_leads' as model_name, count(*) as row_count from staging.stg_marketing_qualified_leads
union all
select 'stg_closed_deals', count(*) from staging.stg_closed_deals
union all
select 'stg_orders', count(*) from staging.stg_orders
union all
select 'stg_order_items', count(*) from staging.stg_order_items
union all
select 'stg_order_payments', count(*) from staging.stg_order_payments
union all
select 'stg_order_reviews', count(*) from staging.stg_order_reviews;
