from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from app.components import page_header, require_data
from app.data import load_csv_artifact, load_json_artifact
from app.theme import polish_figure


def render() -> None:
    with st.sidebar.expander("预测筛选", expanded=False):
        grain = st.radio("预测粒度", ["品类", "商家"])
    if grain == "品类":
        predictions = load_csv_artifact("demand_forecast/backtest_predictions.csv")
        resource_plan = load_csv_artifact("demand_forecast/category_resource_plan.csv")
        metric_key, selected_key = "metrics", "selected_model"
    else:
        predictions = load_csv_artifact("demand_forecast/seller_backtest_predictions.csv")
        resource_plan = load_csv_artifact("demand_forecast/seller_resource_plan.csv")
        segment_metrics = load_csv_artifact(
            "demand_forecast/seller_activity_segment_metrics.csv"
        )
        metric_key, selected_key = "seller_metrics", "seller_selected_model"
    metrics = load_json_artifact("demand_forecast/metrics.json")
    page_header("需求预测", f"{grain}周度滚动回测，用于资源关注排序，不用于 SKU 补货。")
    if not require_data(predictions, "需求模型尚未运行。请先运行 `.venv/bin/python -m src.train demand`。"):
        return
    predictions["week_start"] = pd.to_datetime(predictions["week_start"])
    selected_model = str(metrics.get(selected_key, "seasonal_naive"))
    weekly = predictions.groupby("week_start", as_index=False)[["actual", selected_model]].sum()
    chart = weekly.melt("week_start", var_name="series", value_name="orders")
    chart["series"] = chart["series"].replace({"actual": "实际订单量", selected_model: f"预测：{selected_model}"})
    figure = px.line(chart, x="week_start", y="orders", color="series", markers=True,
                     title=f"{grain}周度回测：实际与预测",
                     labels={"week_start": "周", "orders": "订单量", "series": "序列"})
    st.plotly_chart(polish_figure(figure), width="stretch")
    metric_rows = [dict(model=name, **values) for name, values in metrics.get(metric_key, {}).items()]
    st.dataframe(pd.DataFrame(metric_rows).sort_values("wape"), width="stretch", hide_index=True)
    if grain == "商家":
        acceptance = metrics.get("seller_model_acceptance", {})
        occurrence = metrics.get("seller_occurrence_metrics", {}).get(
            "two_stage_classifier", {}
        )
        st.subheader("商家间歇需求验收")
        st.caption(
            "活动 PR-AUC 衡量谁会在下周有订单；订单量仍需结合 WAPE 阅读，不能把活动排序当成精确需求承诺。"
        )
        columns = st.columns(4)
        columns[0].metric("活动 PR-AUC", f"{occurrence.get('pr_auc', 0):.3f}")
        columns[1].metric("活动率", f"{occurrence.get('positive_rate', 0):.1%}")
        columns[2].metric(
            "不劣于移动平均周数",
            f"{acceptance.get('two_stage_noninferior_weeks_vs_moving_average_4', 0)}/8",
        )
        columns[3].metric(
            "两阶段订单量验收",
            "通过" if acceptance.get("accepted_as_order_count_model") else "未通过",
        )
        if not segment_metrics.empty:
            st.subheader("活动层误差")
            st.dataframe(segment_metrics, width="stretch", hide_index=True)
    st.subheader(f"{grain}资源规划清单")
    st.caption("最近 13 个完整周与前 13 周比较；这是公开历史数据下的运营排序，不是真实补货或收益承诺。")
    if not resource_plan.empty:
        st.dataframe(resource_plan, width="stretch", hide_index=True)
