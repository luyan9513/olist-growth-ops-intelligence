-- 运行前：make dbt-build
-- 输出每条规则的异常数、检查分母和异常占比。
select
    rule_id,
    rule_name,
    severity,
    checked_count,
    issue_count,
    issue_rate,
    run_at
from marts.mart_data_quality
order by severity, rule_id;
