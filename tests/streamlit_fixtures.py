"""Streamlit 页面契约测试的微型合成输入，不代表真实业务结果。"""

from __future__ import annotations

from types import ModuleType

import pandas as pd


def _mart_frames() -> dict[str, pd.DataFrame]:
    return {
        "mart_channel_funnel": pd.DataFrame(
            {
                "origin": ["organic_search", "paid_search"],
                "contact_month": pd.to_datetime(["2018-01-01", "2018-02-01"]),
                "mql_count": [100, 80],
                "won_mql_count": [12, 8],
            }
        ),
        "mart_channel_summary": pd.DataFrame(
            {
                "origin": ["organic_search", "paid_search"],
                "acquired_seller_count": [12, 8],
                "active_seller_count": [7, 5],
                "delivered_gmv": [12000.0, 8000.0],
                "delivered_order_count": [60, 40],
                "delay_rate": [0.05, 0.08],
                "low_review_rate": [0.10, 0.13],
            }
        ),
        "mart_seller_performance": pd.DataFrame(
            {
                "seller_id": ["seller_1", "seller_2"],
                "seller_state": ["SP", "RJ"],
                "order_month": pd.to_datetime(["2018-01-01", "2018-02-01"]),
                "delivered_gmv": [5000.0, 3000.0],
                "delivered_order_count": [25, 15],
            }
        ),
        "mart_seller_risk": pd.DataFrame(
            {
                "seller_id": ["seller_1", "seller_2"],
                "seller_state": ["SP", "RJ"],
                "delivered_gmv": [5000.0, 3000.0],
                "delivered_order_count": [25, 15],
                "delay_rate": [0.16, 0.04],
                "low_review_rate": [0.20, 0.08],
                "seller_segment": ["高价值高风险", "常规关注"],
            }
        ),
        "mart_delivery_experience": pd.DataFrame(
            {
                "order_id": ["order_1", "order_2"],
                "purchased_at": pd.to_datetime(["2018-01-10", "2018-01-11"]),
                "customer_delivered_at": pd.to_datetime(["2018-01-20", "2018-01-18"]),
                "estimated_delivery_at": pd.to_datetime(["2018-01-18", "2018-01-20"]),
                "review_score": [2, 5],
                "is_delayed": [True, False],
                "is_low_review": [True, False],
                "gross_value": [200.0, 100.0],
            }
        ),
        "mart_delivery_breakdown": pd.DataFrame(
            {
                "dimension_type": ["category", "seller_state", "customer_state"],
                "dimension_value": ["fixture_category", "SP", "RJ"],
                "delivery_eligible_count": [20, 15, 12],
                "delay_rate": [0.10, 0.08, 0.06],
                "low_review_rate": [0.15, 0.12, 0.10],
            }
        ),
        "mart_data_quality": pd.DataFrame(
            {
                "rule_id": ["DQ-FIXTURE-01", "DQ-FIXTURE-02"],
                "rule_name": ["合成主键检查", "合成时间检查"],
                "severity": ["error", "warn"],
                "checked_count": [10, 10],
                "issue_count": [0, 1],
                "issue_rate": [0.0, 0.1],
                "run_at": pd.to_datetime(["2018-01-01", "2018-01-01"]),
            }
        ),
    }


def _seller_actions() -> pd.DataFrame:
    seller_ids = [f"fixture_seller_{index}" for index in range(1, 5)]
    return pd.DataFrame(
        {
            "priority_rank": [1, 2, 3, 4],
            "seller_id": seller_ids,
            "seller_state": ["SP", "RJ", "SP", "MG"],
            "recommended_action": ["P1 履约护航"] * 4,
            "action_priority": [1] * 4,
            "activity_probability": [0.90, 0.80, 0.70, 0.60],
            "activity_band": ["高", "高", "中", "中"],
            "activity_segment": ["持续活跃", "持续活跃", "间歇活跃", "间歇活跃"],
            "expected_order_count": [3.0, 2.5, 2.0, 1.5],
            "latest_13w_gmv": [5000.0, 4000.0, 3000.0, 2000.0],
            "delivered_gmv": [12000.0, 10000.0, 8000.0, 6000.0],
            "seller_segment": ["高价值高风险"] * 4,
            "resource_segment": ["高价值高增长", "高价值高增长", "常规", "常规"],
            "action_reason": ["合成页面契约测试原因"] * 4,
            "cutoff_week": ["2018-08-20"] * 4,
            "forecast_week": ["2018-08-27"] * 4,
        }
    )


def _csv_artifacts() -> dict[str, pd.DataFrame]:
    lead_predictions = pd.DataFrame(
        {
            "mql_id": ["fixture_mql_1", "fixture_mql_2", "fixture_mql_3"],
            "is_won": [1, 0, 0],
            "score_random_forest": [0.80, 0.40, 0.20],
        }
    )
    return {
        "lead_conversion/test_predictions.csv": lead_predictions,
        "review_risk/test_predictions.csv": pd.DataFrame(
            {
                "order_id": ["fixture_order_1", "fixture_order_2", "fixture_order_3"],
                "is_low_review": [1, 0, 0],
                "score_logistic_regression": [0.75, 0.35, 0.10],
            }
        ),
        "demand_forecast/backtest_predictions.csv": pd.DataFrame(
            {
                "week_start": ["2018-08-06", "2018-08-13"],
                "actual": [100.0, 110.0],
                "hist_gradient_boosting": [98.0, 108.0],
            }
        ),
        "demand_forecast/category_resource_plan.csv": pd.DataFrame(
            {
                "category": ["fixture_category"],
                "forecast_orders": [108.0],
                "resource_segment": ["重点关注"],
            }
        ),
        "demand_forecast/seller_ops_action_list.csv": _seller_actions(),
    }


def _json_artifacts() -> dict[str, dict[str, object]]:
    classification_common = {
        "bootstrap_intervals": {
            "random_forest": {"metrics": {"pr_auc": {"lower": 0.10, "upper": 0.30}}}
        },
        "calibration": {
            "comparison": {
                "uncalibrated": {"brier_score": 0.20},
                "sigmoid_calibrated": {"brier_score": 0.15},
            }
        },
        "rolling_time_backtest": {"records": []},
    }
    lead_metrics = {
        "selected_model": "random_forest",
        "test_metrics": {
            "random_forest": {
                "pr_auc": 0.20,
                "top_k": {"20pct": {"precision": 0.30, "recall": 0.40}},
            }
        },
        **classification_common,
    }
    review_metrics = {
        "selected_model": "logistic_regression",
        "test_metrics": {"logistic_regression": {"pr_auc": 0.20}},
        "bootstrap_intervals": {
            "logistic_regression": {"metrics": {"pr_auc": {"lower": 0.15, "upper": 0.25}}}
        },
        "calibration": classification_common["calibration"],
    }
    return {
        "lead_conversion/metrics.json": lead_metrics,
        "review_risk/metrics.json": review_metrics,
        "demand_forecast/metrics.json": {
            "selected_model": "hist_gradient_boosting",
            "metrics": {
                "seasonal_naive": {"wape": 0.35, "mae": 20.0},
                "hist_gradient_boosting": {"wape": 0.30, "mae": 18.0},
            },
        },
        "demand_forecast/seller_ops_metadata.json": {
            "cutoff_week": "2018-08-20",
            "forecast_week": "2018-08-27",
            "rule_version": "fixture_rule_v1",
        },
    }


def patch_page_data(page_name: str, module: ModuleType) -> None:
    """用确定性合成输入替换页面模块已导入的数据读取函数。"""

    marts = _mart_frames()
    csv_artifacts = _csv_artifacts()
    json_artifacts = _json_artifacts()
    if hasattr(module, "load_mart"):
        module.load_mart = lambda name: marts.get(name, pd.DataFrame()).copy()
    if hasattr(module, "load_csv_artifact"):
        module.load_csv_artifact = lambda path: csv_artifacts.get(path, pd.DataFrame()).copy()
    if hasattr(module, "load_json_artifact"):
        module.load_json_artifact = lambda path: dict(json_artifacts.get(path, {}))
