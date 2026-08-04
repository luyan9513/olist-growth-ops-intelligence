from __future__ import annotations

import plotly.express as px
import streamlit as st

from app.components import page_header, require_data
from app.data import data_as_of, load_mart
from app.theme import polish_figure


def render() -> None:
    frame = load_mart("mart_channel_summary")
    page_header("渠道质量", "把成交与成交商家的后续经营、履约体验放在一起看。")
    if not require_data(frame):
        return
    figure = px.scatter(frame, x="acquired_seller_count", y="delivered_gmv", size="delivered_order_count",
                        color="delay_rate", hover_name="origin", title="渠道成交规模与后续经营质量",
                        labels={"acquired_seller_count": "成交商家数", "delivered_gmv": "后续已交付 GMV", "delay_rate": "延迟率"})
    st.plotly_chart(polish_figure(figure), width="stretch")
    st.caption("没有渠道成本和毛利，本页不计算 ROI；图中 GMV 是成交商家后续交易规模代理。")
    st.dataframe(frame.sort_values("delivered_gmv", ascending=False), width="stretch", hide_index=True)
