from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from app.components import DISCLAIMER, csv_download, format_percent, page_header, require_data
from app.data import load_csv_artifact, load_json_artifact
from app.theme import polish_figure
from src.decisioning import seller_ops_capacity_comparison, seller_ops_capacity_scenario


def render() -> None:
    actions = load_csv_artifact("demand_forecast/seller_ops_action_list.csv")
    metadata = load_json_artifact("demand_forecast/seller_ops_metadata.json")
    page_header(
        "商家运营行动",
        "把商家价值、履约风险和下一周活动概率转成可审计的人工排期清单。",
        str(metadata.get("cutoff_week", "未知")),
    )
    st.warning(DISCLAIMER)
    if not require_data(
        actions,
        "商家运营行动清单尚未生成。请先运行 `.venv/bin/python -m src.train demand`。",
    ):
        return

    action_options = actions["recommended_action"].dropna().drop_duplicates().tolist()
    state_options = sorted(actions["seller_state"].dropna().unique())
    with st.sidebar.expander("行动筛选", expanded=False):
        selected_actions = st.multiselect("行动类型", action_options, default=action_options)
        selected_states = st.multiselect("卖家州", state_options, default=state_options)
    filtered = actions[
        actions["recommended_action"].isin(selected_actions)
        & actions["seller_state"].isin(selected_states)
    ].copy()
    if not require_data(filtered, "当前行动类型和州筛选下没有商家。"):
        return

    p1_count = int(filtered["recommended_action"].eq("P1 履约护航").sum())
    high_activity_count = int(filtered["activity_band"].eq("高").sum())
    cards = st.columns(4)
    cards[0].metric("可排期商家", f"{len(filtered):,}")
    cards[1].metric("P1 履约护航", f"{p1_count:,}")
    cards[2].metric("高活动概率商家", f"{high_activity_count:,}")
    cards[3].metric("最近 13 周 GMV", f"{filtered['latest_13w_gmv'].sum():,.0f}")

    action_summary = (
        filtered.groupby(["action_priority", "recommended_action"], as_index=False)
        .agg(seller_count=("seller_id", "size"))
        .sort_values("action_priority")
    )
    figure = px.bar(
        action_summary,
        x="recommended_action",
        y="seller_count",
        color="recommended_action",
        title="行动类型与商家规模",
        labels={"recommended_action": "行动类型", "seller_count": "商家数"},
    )
    st.plotly_chart(polish_figure(figure), width="stretch")

    st.subheader("固定容量覆盖")
    st.caption(
        "先按行动类型，再按活动概率、历史已交付 GMV 和商家 ID 排序。覆盖表示当前离线名单质量，不代表干预增量。"
    )
    default_capacity = min(200, len(filtered))
    capacity = st.slider("本周可处理商家数", 0, len(filtered), default_capacity)
    scenario = seller_ops_capacity_scenario(filtered, capacity)
    coverage_cards = st.columns(5)
    coverage_cards[0].metric("选中商家", f"{scenario['selected_count']:,}")
    coverage_cards[1].metric(
        "活动概率质量覆盖",
        format_percent(float(scenario["predicted_activity_mass_coverage"])),
    )
    coverage_cards[2].metric(
        "期望订单量覆盖",
        format_percent(float(scenario["expected_order_count_coverage"])),
    )
    coverage_cards[3].metric(
        "近期 GMV 覆盖", format_percent(float(scenario["latest_13w_gmv_coverage"]))
    )
    coverage_cards[4].metric(
        "高价值高风险覆盖",
        format_percent(float(scenario["high_value_high_risk_coverage"])),
    )
    comparison = seller_ops_capacity_comparison(filtered, capacity)
    comparison_rows = []
    metric_labels = {
        "predicted_activity_mass_coverage": "活动概率质量",
        "expected_order_count_coverage": "期望订单量",
        "latest_13w_gmv_coverage": "近期 GMV",
        "high_value_high_risk_coverage": "高价值高风险商家",
    }
    for strategy, values in comparison.items():
        for metric, label in metric_labels.items():
            comparison_rows.append(
                {"strategy": strategy, "metric": label, "coverage": values[metric]}
            )
    st.caption("对照仅按活动概率或近期 GMV 排名，查看统一行动规则为了风险与增长排期做出的覆盖取舍。")
    figure = px.bar(
        pd.DataFrame(comparison_rows),
        x="metric",
        y="coverage",
        color="strategy",
        barmode="group",
        title=f"容量 {capacity:,} 下的排序策略覆盖取舍",
        labels={"metric": "覆盖指标", "coverage": "覆盖率", "strategy": "排序策略"},
    )
    st.plotly_chart(polish_figure(figure, percent_y=True), width="stretch")

    selected = filtered.sort_values("priority_rank", kind="mergesort").head(capacity)
    if not selected.empty:
        figure = px.scatter(
            selected,
            x="activity_probability",
            y="delivered_gmv",
            color="recommended_action",
            size="expected_order_count",
            hover_name="seller_id",
            hover_data=["seller_state", "activity_segment", "seller_segment"],
            title="入选商家的活动概率与历史价值",
            labels={
                "activity_probability": "下周活动概率",
                "delivered_gmv": "历史已交付 GMV",
                "recommended_action": "行动类型",
                "expected_order_count": "期望订单量",
            },
        )
        st.plotly_chart(polish_figure(figure, percent_x=True), width="stretch")

    st.subheader("本周行动明细")
    st.caption(
        f"预测周：{metadata.get('forecast_week', '未知')}；规则版本：{metadata.get('rule_version', '未知')}。"
    )
    display_columns = [
        "priority_rank",
        "seller_id",
        "seller_state",
        "recommended_action",
        "activity_probability",
        "expected_order_count",
        "latest_13w_gmv",
        "seller_segment",
        "resource_segment",
        "action_reason",
    ]
    st.dataframe(selected[display_columns], width="stretch", hide_index=True)
    csv_download("下载本周行动清单", selected, "seller_weekly_ops_actions.csv")
    st.info(
        "未进入活动排名的风险商家仍保留在商家经营页；本页不会把缺失活动概率填成 0。"
    )
