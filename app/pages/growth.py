from __future__ import annotations

import plotly.express as px
import streamlit as st

from app.components import format_number, format_percent, page_header, require_data
from app.data import data_as_of, load_mart
from app.theme import polish_figure


def render() -> None:
    funnel = load_mart("mart_channel_funnel")
    page_header("增长总览", "监控 MQL、成交与渠道趋势。", data_as_of(funnel, ("contact_month",)))
    if not require_data(funnel):
        return
    origins = sorted(funnel["origin"].dropna().unique())
    with st.sidebar.expander("增长筛选", expanded=False):
        selected = st.multiselect("来源", origins, default=origins)
        selected_range = st.date_input(
            "首次接触月份",
            value=(funnel["contact_month"].min(), funnel["contact_month"].max()),
        )
    filtered = funnel[funnel["origin"].isin(selected)]
    start, end = selected_range
    filtered = filtered[
        (filtered["contact_month"].dt.date >= start) & (filtered["contact_month"].dt.date <= end)
    ]
    mql = filtered["mql_count"].sum()
    won = filtered["won_mql_count"].sum()
    conversion = won / mql if mql else float("nan")
    columns = st.columns(3)
    columns[0].metric("有效 MQL", format_number(mql))
    columns[1].metric("成交 MQL", format_number(won))
    columns[2].metric("成交率", format_percent(conversion))
    monthly = filtered.groupby("contact_month", as_index=False)[["mql_count", "won_mql_count"]].sum()
    monthly = monthly.rename(columns={"mql_count": "有效 MQL", "won_mql_count": "成交 MQL"})
    figure = px.line(monthly, x="contact_month", y=["有效 MQL", "成交 MQL"], markers=True,
                     title="月度线索与成交趋势",
                     labels={"value": "线索数", "contact_month": "首次接触月", "variable": "指标"})
    st.plotly_chart(polish_figure(figure), width="stretch")
    channel = filtered.groupby("origin", as_index=False)[["mql_count", "won_mql_count"]].sum()
    channel["conversion_rate"] = channel["won_mql_count"] / channel["mql_count"]
    figure = px.bar(channel.sort_values("conversion_rate"), x="conversion_rate", y="origin", orientation="h",
                    title="各渠道历史成交率",
                    labels={"conversion_rate": "成交率", "origin": "渠道"})
    st.plotly_chart(polish_figure(figure, percent_x=True), width="stretch")
