from __future__ import annotations

import plotly.express as px
import streamlit as st

from app.components import csv_download, format_percent, page_header, require_data
from app.data import data_as_of, load_mart
from app.theme import polish_figure


def render() -> None:
    detail = load_mart("mart_delivery_experience")
    breakdown = load_mart("mart_delivery_breakdown")
    page_header("履约体验", "拆解延迟和低评分，并形成订单级跟进清单。", data_as_of(detail, ("purchased_at",)))
    if not require_data(detail):
        return
    eligible = detail[detail["customer_delivered_at"].notna() & detail["estimated_delivery_at"].notna()]
    reviewed = detail[detail["review_score"].between(1, 5)]
    cards = st.columns(3)
    cards[0].metric("可判断履约订单", f"{len(eligible):,}")
    cards[1].metric("延迟率", format_percent(eligible["is_delayed"].mean()))
    cards[2].metric("低评分率", format_percent(reviewed["is_low_review"].mean()))
    dimension = st.selectbox("拆解维度", ["category", "seller_state", "customer_state"],
                             format_func={"category": "品类", "seller_state": "卖家州", "customer_state": "客户州"}.get)
    selected = breakdown[breakdown["dimension_type"] == dimension].nlargest(20, "delivery_eligible_count")
    figure = px.bar(selected.sort_values("delay_rate"), x="delay_rate", y="dimension_value", orientation="h",
                    color="low_review_rate", title="高订单量分组的延迟与低评分风险",
                    labels={"delay_rate": "延迟率", "dimension_value": "分组", "low_review_rate": "低评分率"})
    st.plotly_chart(polish_figure(figure, percent_x=True), width="stretch")
    risk_orders = detail[(detail["is_delayed"] == True) | (detail["is_low_review"] == True)].sort_values(
        "gross_value", ascending=False
    )
    st.dataframe(risk_orders.head(1000), width="stretch", hide_index=True)
    csv_download("下载历史风险订单", risk_orders, "historical_risk_orders.csv")
