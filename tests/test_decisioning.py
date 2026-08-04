import math

import pandas as pd
import pytest

from src.decisioning import (
    build_seller_ops_actions,
    seller_ops_capacity_comparison,
    seller_ops_capacity_scenario,
)


def sample_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    resource = pd.DataFrame(
        {
            "seller_id": ["s1", "s2", "s3", "s4", "s5", "s6", "s7"],
            "cutoff_week": ["2024-01-01"] * 7,
            "forecast_week": ["2024-01-08"] * 7,
            "latest_13w_gmv": [100, 90, 80, 70, 10, 0, 5],
            "resource_segment": [
                "稳定运营",
                "高价值高增长",
                "稳定运营",
                "稳定运营",
                "稳定运营",
                "低价值长尾",
                "低价值长尾",
            ],
            "activity_probability": [0.90, 0.85, 0.70, 0.85, 0.10, 0.40, 0.20],
            "expected_order_count": [3.0, 2.0, 1.0, 1.5, 0.1, 0.5, 0.2],
            "activity_segment": [
                "持续活跃",
                "持续活跃",
                "间歇活跃",
                "持续活跃",
                "长尾/沉默",
                "间歇活跃",
                "长尾/沉默",
            ],
        }
    )
    risk = pd.DataFrame(
        {
            "seller_id": ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"],
            "seller_state": ["SP"] * 8,
            "delivered_gmv": [1000, 900, 800, 700, 100, 50, 20, 10],
            "delivered_order_count": [100, 90, 80, 70, 10, 5, 2, 1],
            "delay_rate": [0.2, 0.05, 0.3, 0.04, 0.01, 0.02, 0.03, 0.01],
            "low_review_rate": [0.2, 0.05, 0.3, 0.04, 0.01, 0.02, 0.03, 0.01],
            "is_experience_rate_reliable": [True] * 8,
            "seller_segment": [
                "高价值高风险",
                "常规关注",
                "体验风险",
                "高价值",
                "常规关注",
                "常规关注",
                "常规关注",
                "常规关注",
            ],
            "risk_reasons": ["测试原因", "测试原因", "测试原因", "测试原因", None, "测试原因", "测试原因", "测试原因"],
        }
    )
    return resource, risk


def test_seller_ops_actions_are_mutually_exclusive_and_stably_ranked():
    resource, risk = sample_inputs()
    result = build_seller_ops_actions(resource, risk)
    actions = result.actions.set_index("seller_id")
    assert actions.loc["s1", "recommended_action"] == "P1 履约护航"
    assert actions.loc["s2", "recommended_action"] == "P2 增长承接"
    assert actions.loc["s3", "recommended_action"] == "P3 风险巡检"
    assert actions.loc["s4", "recommended_action"] == "P4 重点经营"
    assert actions.loc["s5", "recommended_action"] == "P5 常规观察"
    assert "无可靠体验风险信号" in actions.loc["s5", "action_reason"]
    assert sorted(result.actions["priority_rank"]) == list(range(1, 8))
    assert result.actions["priority_rank"].is_unique
    assert result.metadata["risk_sellers_without_activity_score"] == 1
    repeated = build_seller_ops_actions(resource, risk).actions
    assert repeated["seller_id"].tolist() == result.actions["seller_id"].tolist()


def test_seller_ops_rejects_duplicate_or_missing_risk_join():
    resource, risk = sample_inputs()
    duplicate = pd.concat([resource, resource.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="必须唯一"):
        build_seller_ops_actions(duplicate, risk)
    with pytest.raises(ValueError, match="无法连接风险表"):
        build_seller_ops_actions(resource, risk[risk["seller_id"] != "s1"])


def test_seller_ops_capacity_uses_rank_and_handles_boundaries():
    resource, risk = sample_inputs()
    actions = build_seller_ops_actions(resource, risk).actions
    zero = seller_ops_capacity_scenario(actions, 0)
    assert zero["selected_count"] == 0
    assert zero["predicted_activity_mass_coverage"] == 0
    top_two = seller_ops_capacity_scenario(actions, 2)
    assert top_two["selected_count"] == 2
    assert top_two["selected_high_value_high_risk_count"] == 1
    all_rows = seller_ops_capacity_scenario(actions, 99)
    assert all_rows["selected_count"] == len(actions)
    assert all_rows["expected_order_count_coverage"] == pytest.approx(1.0)
    assert all_rows["latest_13w_gmv_coverage"] == pytest.approx(1.0)
    with pytest.raises(ValueError, match="不能为负"):
        seller_ops_capacity_scenario(actions, -1)


def test_seller_ops_capacity_returns_nan_for_zero_value_denominator():
    resource, risk = sample_inputs()
    resource["latest_13w_gmv"] = 0.0
    actions = build_seller_ops_actions(resource, risk).actions
    result = seller_ops_capacity_scenario(actions, 1)
    assert math.isnan(result["latest_13w_gmv_coverage"])


def test_seller_ops_capacity_comparison_uses_three_transparent_strategies():
    resource, risk = sample_inputs()
    actions = build_seller_ops_actions(resource, risk).actions
    comparison = seller_ops_capacity_comparison(actions, 3)
    assert set(comparison) == {"统一行动规则", "仅活动概率", "仅近期GMV"}
    assert all(result["selected_count"] == 3 for result in comparison.values())
