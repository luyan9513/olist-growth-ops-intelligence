-- 面试/代码审查入口：CTE、窗口函数和多表 JOIN 的实际实现位于 dbt/models。
-- 本查询统一列出核心 mart 规模，具体血缘由 dbt docs 生成。
with mart_counts as (
    select 'mart_channel_funnel' as mart_name, count(*) as row_count from marts.mart_channel_funnel
    union all
    select 'mart_seller_performance', count(*) from marts.mart_seller_performance
    union all
    select 'mart_delivery_experience', count(*) from marts.mart_delivery_experience
    union all
    select 'mart_lead_features', count(*) from marts.mart_lead_features
    union all
    select 'mart_review_risk_features', count(*) from marts.mart_review_risk_features
    union all
    select 'mart_demand_weekly', count(*) from marts.mart_demand_weekly
    union all
    select 'mart_seller_risk', count(*) from marts.mart_seller_risk
)
select
    mart_name,
    row_count,
    row_number() over (order by mart_name) as display_order
from mart_counts
order by display_order;
