"""导出报告所需的可追溯业务分析快照。"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd


def json_default(value: object) -> object:
    if pd.isna(value):
        return None
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    raise TypeError(f"无法序列化类型: {type(value)!r}")


def rows(connection: duckdb.DuckDBPyConnection, query: str) -> list[dict[str, object]]:
    return connection.execute(query).fetchdf().to_dict(orient="records")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("data/processed/olist.duckdb"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/analysis_snapshot.json"))
    args = parser.parse_args()
    connection = duckdb.connect(str(args.database), read_only=True)
    snapshot = {
        "source_profile": rows(
            connection,
            """
            select 'mql' as entity, count(*) as row_count, min(first_contact_at) as min_date, max(first_contact_at) as max_date from staging.stg_marketing_qualified_leads
            union all select 'closed_deals', count(*), min(won_at), max(won_at) from staging.stg_closed_deals
            union all select 'orders', count(*), min(purchased_at), max(purchased_at) from staging.stg_orders
            union all select 'order_items', count(*), null, null from staging.stg_order_items
            union all select 'reviews', count(*), min(review_created_at), max(review_created_at) from staging.stg_order_reviews
            union all select 'sellers', count(*), null, null from staging.stg_sellers
            """,
        ),
        "funnel_overall": rows(
            connection,
            """
            select sum(mql_count) as mql_count, sum(won_mql_count) as won_count,
                   sum(won_mql_count)::double / nullif(sum(mql_count), 0) as conversion_rate
            from marts.mart_channel_funnel
            """,
        ),
        "channel_quality": rows(
            connection,
            """
            with funnel as (
                select origin, sum(mql_count) as mql_count, sum(won_mql_count) as won_count,
                       sum(won_mql_count)::double / nullif(sum(mql_count), 0) as conversion_rate
                from marts.mart_channel_funnel group by origin
            )
            select f.*, s.acquired_seller_count, s.active_seller_count, s.delivered_gmv,
                   s.delivered_order_count, s.gmv_per_acquired_seller, s.delay_rate, s.low_review_rate
            from funnel f left join marts.mart_channel_summary s using (origin)
            order by f.mql_count desc
            """,
        ),
        "commerce_overall": rows(
            connection,
            """
            select count(*) as seller_orders,
                   count(*) filter (where order_status = 'delivered') as delivered_orders,
                   sum(gross_value) filter (where order_status = 'delivered') as delivered_gmv,
                   count(*) filter (where customer_delivered_at is not null and estimated_delivery_at is not null) as delivery_eligible_count,
                   avg(is_delayed::integer) filter (where customer_delivered_at is not null and estimated_delivery_at is not null) as delay_rate,
                   count(*) filter (where review_score between 1 and 5) as reviewed_count,
                   avg(is_low_review::integer) filter (where review_score between 1 and 5) as low_review_rate
            from marts.mart_delivery_experience
            """,
        ),
        "experience_hotspots": rows(
            connection,
            """
            select dimension_type, dimension_value, seller_order_count, delivered_gmv,
                   delivery_eligible_count, delay_rate, reviewed_count, low_review_rate
            from marts.mart_delivery_breakdown
            where delivery_eligible_count >= 500 and reviewed_count >= 500
            qualify row_number() over (partition by dimension_type order by delay_rate desc, delivery_eligible_count desc) <= 5
            order by dimension_type, delay_rate desc
            """,
        ),
        "seller_segments": rows(
            connection,
            """
            select seller_segment, count(*) as seller_count, sum(delivered_gmv) as delivered_gmv,
                   sum(delivered_order_count) as delivered_order_count
            from marts.mart_seller_risk group by seller_segment order by delivered_gmv desc
            """,
        ),
        "seller_priority": rows(
            connection,
            """
            select seller_id, seller_state, delivered_gmv, delivered_order_count,
                   delivery_eligible_count, delay_rate, reviewed_order_count, low_review_rate, risk_reasons
            from marts.mart_seller_risk where seller_segment = '高价值高风险'
            order by delivered_gmv desc limit 15
            """,
        ),
        "data_quality": rows(
            connection,
            "select rule_id, rule_name, severity, checked_count, issue_count, issue_rate from marts.mart_data_quality order by rule_id",
        ),
        "mart_counts": rows(
            connection,
            """
            select 'mart_lead_features' as mart, count(*) as row_count from marts.mart_lead_features
            union all select 'mart_review_risk_features', count(*) from marts.mart_review_risk_features
            union all select 'mart_delivery_experience', count(*) from marts.mart_delivery_experience
            union all select 'mart_seller_performance', count(*) from marts.mart_seller_performance
            union all select 'mart_seller_risk', count(*) from marts.mart_seller_risk
            union all select 'mart_demand_weekly', count(*) from marts.mart_demand_weekly
            """,
        ),
    }
    connection.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, default=json_default), encoding="utf-8"
    )
    print(json.dumps({key: len(value) for key, value in snapshot.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
