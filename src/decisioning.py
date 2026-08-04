"""将商家价值、履约风险与活动预测转换为可审计的运营行动清单。"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


SELLER_OPS_RULE_VERSION = "seller_ops_v1"
ACTION_PRIORITY = {
    "P1 履约护航": 1,
    "P2 增长承接": 2,
    "P3 风险巡检": 3,
    "P4 重点经营": 4,
    "P5 常规观察": 5,
}

RESOURCE_REQUIRED_COLUMNS = {
    "seller_id",
    "cutoff_week",
    "forecast_week",
    "latest_13w_gmv",
    "resource_segment",
    "activity_probability",
    "expected_order_count",
    "activity_segment",
}
RISK_REQUIRED_COLUMNS = {
    "seller_id",
    "seller_state",
    "delivered_gmv",
    "delivered_order_count",
    "delay_rate",
    "low_review_rate",
    "is_experience_rate_reliable",
    "seller_segment",
    "risk_reasons",
}


@dataclass(frozen=True)
class SellerOpsDecision:
    actions: pd.DataFrame
    metadata: dict[str, object]


def _validate_unique(frame: pd.DataFrame, name: str) -> None:
    if frame["seller_id"].isna().any():
        raise ValueError(f"{name} 的 seller_id 不能为空")
    if frame["seller_id"].duplicated().any():
        raise ValueError(f"{name} 的 seller_id 必须唯一")


def _action_reason(row: pd.Series) -> str:
    activity = f"下周活动概率 {row['activity_probability']:.1%}（{row['activity_band']}）"
    if row["recommended_action"] == "P1 履约护航":
        decision = "高价值高风险且近期活动不低，优先做履约护航"
    elif row["recommended_action"] == "P2 增长承接":
        decision = "近期高价值高增长且活动概率高，优先承接增长"
    elif row["recommended_action"] == "P3 风险巡检":
        decision = "存在体验风险且近期活动不低，安排风险巡检"
    elif row["recommended_action"] == "P4 重点经营":
        decision = "全生命周期高价值且活动概率高，安排重点经营"
    else:
        decision = "当前未命中优先行动规则，进入常规观察"
    risk = str(row.get("risk_reasons") or "无额外风险原因")
    return f"{decision}；{activity}；风险依据：{risk}"


def build_seller_ops_actions(
    resource_plan: pd.DataFrame,
    seller_risk: pd.DataFrame,
) -> SellerOpsDecision:
    """生成互斥行动类型与稳定优先排名，不构造任意加权总分。"""

    missing_resource = RESOURCE_REQUIRED_COLUMNS.difference(resource_plan.columns)
    missing_risk = RISK_REQUIRED_COLUMNS.difference(seller_risk.columns)
    if missing_resource:
        raise ValueError(f"商家资源计划缺少字段: {sorted(missing_resource)}")
    if missing_risk:
        raise ValueError(f"商家风险表缺少字段: {sorted(missing_risk)}")
    if resource_plan.empty or seller_risk.empty:
        raise ValueError("商家资源计划和风险表都不能为空")
    _validate_unique(resource_plan, "商家资源计划")
    _validate_unique(seller_risk, "商家风险表")

    risk_columns = sorted(RISK_REQUIRED_COLUMNS)
    actions = resource_plan.merge(
        seller_risk[risk_columns],
        on="seller_id",
        how="left",
        validate="one_to_one",
    )
    if actions["seller_segment"].isna().any():
        missing_count = int(actions["seller_segment"].isna().sum())
        raise ValueError(f"有 {missing_count} 个可评分商家无法连接风险表")
    actions["delivered_gmv"] = actions["delivered_gmv"].fillna(0.0)
    actions["delivered_order_count"] = actions["delivered_order_count"].fillna(0)
    actions["risk_reasons"] = actions["risk_reasons"].fillna("无可靠体验风险信号")

    median_threshold = float(actions["activity_probability"].quantile(0.50))
    high_threshold = float(actions["activity_probability"].quantile(0.75))
    actions["activity_band"] = np.select(
        [
            actions["activity_probability"] >= high_threshold,
            actions["activity_probability"] >= median_threshold,
        ],
        ["高", "中"],
        default="低",
    )
    activity_not_low = actions["activity_band"].isin(["高", "中"])
    actions["recommended_action"] = np.select(
        [
            actions["seller_segment"].eq("高价值高风险") & activity_not_low,
            actions["resource_segment"].eq("高价值高增长")
            & actions["activity_band"].eq("高"),
            actions["seller_segment"].eq("体验风险") & activity_not_low,
            actions["seller_segment"].eq("高价值") & actions["activity_band"].eq("高"),
        ],
        ["P1 履约护航", "P2 增长承接", "P3 风险巡检", "P4 重点经营"],
        default="P5 常规观察",
    )
    actions["action_priority"] = actions["recommended_action"].map(ACTION_PRIORITY).astype(int)
    actions["action_reason"] = actions.apply(_action_reason, axis=1)
    actions["rule_version"] = SELLER_OPS_RULE_VERSION
    actions = actions.sort_values(
        ["action_priority", "activity_probability", "delivered_gmv", "seller_id"],
        ascending=[True, False, False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    actions.insert(0, "priority_rank", np.arange(1, len(actions) + 1))

    scored_ids = set(actions["seller_id"])
    risk_ids = set(seller_risk["seller_id"])
    action_counts = {
        str(action): int(count)
        for action, count in actions["recommended_action"].value_counts().sort_index().items()
    }
    metadata: dict[str, object] = {
        "rule_version": SELLER_OPS_RULE_VERSION,
        "scored_seller_count": int(len(actions)),
        "risk_seller_count": int(len(seller_risk)),
        "risk_sellers_without_activity_score": int(len(risk_ids.difference(scored_ids))),
        "risk_join_coverage": float(len(scored_ids) / len(risk_ids)),
        "activity_probability_thresholds": {
            "medium_minimum_median": median_threshold,
            "high_minimum_p75": high_threshold,
        },
        "cutoff_week": str(pd.to_datetime(actions["cutoff_week"]).max().date()),
        "forecast_week": str(pd.to_datetime(actions["forecast_week"]).max().date()),
        "action_counts": action_counts,
        "sort_order": [
            "action_priority ascending",
            "activity_probability descending",
            "delivered_gmv descending",
            "seller_id ascending",
        ],
        "limitations": [
            "公开历史数据与离线预测快照，不代表真实干预效果",
            "无需求序列商家不补造活动概率，不进入本行动排名",
            "容量覆盖不是增量订单、风险减少、利润或 ROI",
        ],
    }
    return SellerOpsDecision(actions=actions, metadata=metadata)


def seller_ops_capacity_scenario(
    actions: pd.DataFrame,
    capacity: int,
) -> dict[str, float | int]:
    """计算固定人工容量下的名单覆盖，不推断干预收益。"""

    required = {
        "priority_rank",
        "activity_probability",
        "expected_order_count",
        "latest_13w_gmv",
        "seller_segment",
    }
    missing = required.difference(actions.columns)
    if missing:
        raise ValueError(f"商家行动容量模拟缺少字段: {sorted(missing)}")
    if actions.empty:
        raise ValueError("商家行动容量模拟需要非空清单")
    if capacity < 0:
        raise ValueError("容量不能为负")

    selected_count = min(int(capacity), len(actions))
    ranked = actions.sort_values("priority_rank", kind="mergesort")
    selected = ranked.head(selected_count)

    def coverage(column: str) -> float:
        denominator = float(ranked[column].fillna(0.0).sum())
        numerator = float(selected[column].fillna(0.0).sum())
        return numerator / denominator if denominator else math.nan

    high_risk = ranked["seller_segment"].eq("高价值高风险")
    selected_high_risk = selected["seller_segment"].eq("高价值高风险")
    return {
        "available_count": int(len(ranked)),
        "selected_count": selected_count,
        "predicted_activity_mass_coverage": coverage("activity_probability"),
        "expected_order_count_coverage": coverage("expected_order_count"),
        "latest_13w_gmv_coverage": coverage("latest_13w_gmv"),
        "high_value_high_risk_count": int(high_risk.sum()),
        "selected_high_value_high_risk_count": int(selected_high_risk.sum()),
        "high_value_high_risk_coverage": (
            float(selected_high_risk.sum() / high_risk.sum()) if high_risk.any() else math.nan
        ),
    }


def seller_ops_capacity_comparison(
    actions: pd.DataFrame,
    capacity: int,
) -> dict[str, dict[str, float | int]]:
    """比较行动规则、只看活动概率和只看近期 GMV 的容量取舍。"""

    strategies = {
        "统一行动规则": actions.sort_values("priority_rank", kind="mergesort"),
        "仅活动概率": actions.sort_values(
            ["activity_probability", "delivered_gmv", "seller_id"],
            ascending=[False, False, True],
            kind="mergesort",
        ),
        "仅近期GMV": actions.sort_values(
            ["latest_13w_gmv", "activity_probability", "seller_id"],
            ascending=[False, False, True],
            kind="mergesort",
        ),
    }
    comparison: dict[str, dict[str, float | int]] = {}
    for name, ordered in strategies.items():
        ranked = ordered.copy().reset_index(drop=True)
        ranked["priority_rank"] = np.arange(1, len(ranked) + 1)
        comparison[name] = seller_ops_capacity_scenario(ranked, capacity)
    return comparison
