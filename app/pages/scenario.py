from __future__ import annotations

import streamlit as st

from app.components import DISCLAIMER, format_percent, page_header, require_data
from app.data import load_csv_artifact, load_json_artifact
from app.logic import historical_capacity_scenario


def render() -> None:
    page_header("历史情景模拟", "调整运营容量，观察测试集历史覆盖。")
    st.warning(DISCLAIMER)
    task = st.radio("模拟对象", ["线索触达", "风险订单干预"], horizontal=True)
    artifact = "lead_conversion" if task == "线索触达" else "review_risk"
    label = "is_won" if task == "线索触达" else "is_low_review"
    predictions = load_csv_artifact(f"{artifact}/test_predictions.csv")
    metrics = load_json_artifact(f"{artifact}/metrics.json")
    if not require_data(predictions, f"{task}模型尚未运行，暂不能进行真实历史测试集模拟。"):
        return
    selected_model = str(metrics.get("selected_model"))
    selected_metrics = metrics.get("test_metrics", {}).get(selected_model, {})
    bootstrap = metrics.get("bootstrap_intervals", {}).get(selected_model, {}).get("metrics", {})
    pr_interval = bootstrap.get("pr_auc", {})
    calibration = metrics.get("calibration", {}).get("comparison", {})
    calibrated_brier = calibration.get("sigmoid_calibrated", {}).get("brier_score", float("nan"))
    st.caption(
        f"当前模型：{selected_model}；测试 PR-AUC {selected_metrics.get('pr_auc', float('nan')):.3f}；"
        f"95% bootstrap 区间 {pr_interval.get('lower', float('nan')):.3f}–{pr_interval.get('upper', float('nan')):.3f}；"
        f"独立时间校准后 Brier {calibrated_brier:.3f}。"
    )
    capacity = st.slider("可触达/干预数量", 0, len(predictions), min(len(predictions), max(1, len(predictions) // 5)))
    unit_cost = st.number_input("每个对象假设成本（仅情景输入）", min_value=0.0, value=1.0, step=0.5)
    result = historical_capacity_scenario(predictions, f"score_{selected_model}", label, capacity, unit_cost)
    cards = st.columns(4)
    cards[0].metric("选中数量", f"{result['selected_count']:,}")
    cards[1].metric("历史正例覆盖", format_percent(float(result["positive_coverage"])))
    cards[2].metric("历史正例数", f"{result['selected_positive_count']:,}")
    cards[3].metric("假设总成本", f"{result['assumed_total_cost']:,.2f}")
    st.info("这里只回答固定容量在历史测试集覆盖了多少正例，不估算增量成交、减少差评或真实 ROI。")
