from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from app.components import DISCLAIMER, csv_download, format_percent, page_header, require_data
from app.data import load_csv_artifact, load_json_artifact
from app.theme import polish_figure
from src.experiments import (
    assignment_balance,
    assign_sellers,
    binary_proportion_mde,
    binary_proportion_sample_size,
)


TEMPLATE_PATH = Path("data/templates/experiment")


def render() -> None:
    actions = load_csv_artifact("demand_forecast/seller_ops_action_list.csv")
    metadata = load_json_artifact("demand_forecast/seller_ops_metadata.json")
    page_header(
        "实验设计",
        "用真实行动候选池规划样本量和随机分组；当前没有干预执行或结果数据。",
        str(metadata.get("cutoff_week", "未知")),
    )
    st.warning(f"规划中、未启动。{DISCLAIMER} 本页所有 MDE 和分组均为设计草案。")
    if not require_data(actions, "行动清单尚未生成，无法建立真实候选池。"):
        return

    st.subheader("1. 固定候选池和主指标")
    action_options = actions["recommended_action"].dropna().drop_duplicates().tolist()
    default_actions = [action for action in action_options if action == "P1 履约护航"]
    selected_actions = st.multiselect(
        "候选行动类型",
        action_options,
        default=default_actions or action_options[:1],
        help="建议首个实验只纳入 P1 履约护航，避免混合不同干预目标。",
    )
    eligible = actions[actions["recommended_action"].isin(selected_actions)].copy()
    if not require_data(eligible, "当前选择下没有实验候选商家。"):
        return
    st.caption(
        "默认分组单位为唯一 seller_id；主指标建议为结果窗低评分率，延迟率、取消率、退款和成本作为护栏。"
    )

    st.subheader("2. 样本量与可检测变化")
    inputs = st.columns(5)
    baseline_rate = inputs[0].number_input(
        "规划基线率",
        min_value=0.01,
        max_value=0.90,
        value=0.1419,
        step=0.01,
        format="%.4f",
    )
    absolute_mde = inputs[1].number_input(
        "绝对 MDE",
        min_value=0.005,
        max_value=0.30,
        value=0.03,
        step=0.005,
        format="%.3f",
        help="例如 0.03 表示 3 个百分点；它是希望识别的变化，不是预计提升。",
    )
    direction_label = inputs[2].selectbox("目标方向", ["降低（风险指标）", "提高（增长指标）"])
    direction = "decrease" if direction_label.startswith("降低") else "increase"
    alpha = inputs[3].selectbox("alpha", [0.10, 0.05, 0.01], index=1)
    power = inputs[4].selectbox("把握度", [0.80, 0.90], index=0)
    treatment_share = 0.50
    plan = binary_proportion_sample_size(
        float(baseline_rate),
        float(absolute_mde),
        alpha=float(alpha),
        power=float(power),
        treatment_share=treatment_share,
        direction=direction,
    )
    detectable_mde = binary_proportion_mde(
        len(eligible),
        float(baseline_rate),
        alpha=float(alpha),
        power=float(power),
        treatment_share=treatment_share,
        direction=direction,
    )
    feasible = len(eligible) >= plan.total_sample_size
    cards = st.columns(5)
    cards[0].metric("当前候选商家", f"{len(eligible):,}")
    cards[1].metric("规划所需总样本", f"{plan.total_sample_size:,}")
    cards[2].metric("处理组所需", f"{plan.treatment_sample_size:,}")
    cards[3].metric("对照组所需", f"{plan.control_sample_size:,}")
    cards[4].metric("当前池可检测 MDE", format_percent(detectable_mde))
    if feasible:
        st.success("按当前近似公式，候选池数量达到所填 MDE 的规划样本量。上线前仍要考虑标签成熟和设计效应。")
    else:
        shortfall = plan.total_sample_size - len(eligible)
        st.info(
            f"当前候选池比规划样本少 {shortfall:,} 个。可延长入组周期、扩大预先定义的资格池，或接受更大的可检测变化；不要把样本不足写成无效果。"
        )

    st.subheader("3. 草案随机分组与平衡检查")
    experiment_id = st.text_input("实验 ID", value="draft_p11_fulfillment_guard_v1")
    snapshot_date = str(metadata.get("cutoff_week", actions["cutoff_week"].max()))
    assignment_date = str(metadata.get("forecast_week", actions["forecast_week"].max()))
    assignments = assign_sellers(
        eligible,
        experiment_id,
        treatment_share=treatment_share,
        assignment_timestamp=assignment_date,
        eligibility_snapshot_date=snapshot_date,
    )
    group_counts = assignments["assigned_group"].value_counts()
    group_cards = st.columns(3)
    group_cards[0].metric("草案处理组", f"{int(group_counts.get('treatment', 0)):,}")
    group_cards[1].metric("草案对照组", f"{int(group_counts.get('control', 0)):,}")
    group_cards[2].metric(
        "草案处理组占比",
        format_percent(float(group_counts.get("treatment", 0) / len(assignments))),
    )
    balance = assignment_balance(assignments, eligible)
    activity_balance = balance[balance["dimension"] == "activity_band"]
    activity_balance = activity_balance.copy()
    activity_balance["assigned_group"] = activity_balance["assigned_group"].replace(
        {"treatment": "处理组", "control": "对照组"}
    )
    figure = px.bar(
        activity_balance,
        x="value",
        y="seller_count",
        color="assigned_group",
        barmode="group",
        title="草案分组的干预前活动档位平衡",
        labels={"value": "干预前活动档位", "seller_count": "商家数", "assigned_group": "草案组别"},
    )
    st.plotly_chart(polish_figure(figure), width="stretch")
    st.caption("稳定哈希保证相同实验 ID、商家 ID 和版本重复运行一致，但小样本平衡仍需人工审核。")
    csv_download("下载草案分组（非真实执行记录）", assignments, "draft_experiment_assignments.csv")

    st.subheader("4. 真实日志接入模板")
    st.caption("以下文件目前只有表头。只有真实分组发布、真实执行和结果成熟后才能追加记录并做效果分析。")
    template_names = [
        "experiment_registry.csv",
        "assignment_log.csv",
        "execution_log.csv",
        "outcome_log.csv",
    ]
    columns = st.columns(len(template_names))
    for column, filename in zip(columns, template_names, strict=True):
        path = TEMPLATE_PATH / filename
        column.download_button(
            f"下载 {filename}",
            path.read_bytes(),
            file_name=filename,
            mime="text/csv",
        )

    st.markdown(
        "详细的 ITT 口径、时间顺序、隐私边界和数据质量门槛见 "
        "`docs/07_intervention_and_experiment_design.md`。"
    )
