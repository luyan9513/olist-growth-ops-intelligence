from __future__ import annotations

import plotly.express as px
import streamlit as st

from app.components import csv_download, page_header, require_data
from app.data import data_as_of, load_mart
from app.theme import polish_figure


def render() -> None:
    performance = load_mart("mart_seller_performance")
    risk = load_mart("mart_seller_risk")
    page_header("商家经营", "定位高价值商家、经营变化和体验风险。", data_as_of(performance, ("order_month",)))
    if not require_data(performance):
        return
    states = sorted(performance["seller_state"].dropna().unique())
    with st.sidebar.expander("商家筛选", expanded=False):
        selected = st.multiselect("卖家州", states, default=states)
    filtered = performance[performance["seller_state"].isin(selected)]
    monthly = filtered.groupby("order_month", as_index=False).agg(
        delivered_gmv=("delivered_gmv", "sum"), delivered_order_count=("delivered_order_count", "sum")
    )
    figure = px.line(monthly, x="order_month", y="delivered_gmv", markers=True,
                     title="已交付 GMV 月度趋势",
                     labels={"order_month": "订单月", "delivered_gmv": "已交付 GMV"})
    st.plotly_chart(polish_figure(figure), width="stretch")
    risk_filtered = risk[risk["seller_state"].isin(selected)]
    figure = px.scatter(risk_filtered, x="delivered_gmv", y="delay_rate", color="seller_segment",
                        size="delivered_order_count", hover_name="seller_id", title="商家价值与履约风险分布",
                        labels={"delivered_gmv": "已交付 GMV", "delay_rate": "延迟率"})
    st.plotly_chart(polish_figure(figure, percent_y=True), width="stretch")
    priority = risk_filtered[risk_filtered["seller_segment"] == "高价值高风险"].sort_values(
        "delivered_gmv", ascending=False
    )
    st.subheader("高价值高风险商家清单")
    st.dataframe(priority, width="stretch", hide_index=True)
    csv_download("下载商家风险清单", priority, "seller_risk_priority.csv")
