from __future__ import annotations

import plotly.express as px
import streamlit as st

from app.components import format_percent, page_header, require_data
from app.data import load_mart
from app.theme import SEVERITY_COLORS, polish_figure


def render() -> None:
    quality = load_mart("mart_data_quality")
    page_header("数据质量", "每项规则展示检查分母、异常数量、异常率与严重级别。")
    if not require_data(quality):
        return
    errors = int(quality.loc[quality["severity"] == "error", "issue_count"].sum())
    warnings = int(quality.loc[quality["severity"] == "warn", "issue_count"].sum())
    columns = st.columns(3)
    columns[0].metric("质量规则", f"{len(quality):,}")
    columns[1].metric("Error 异常数", f"{errors:,}")
    columns[2].metric("Warn 异常数", f"{warnings:,}")
    chart_data = quality.copy()
    chart_data["issue_rate_label"] = chart_data["issue_rate"].map(format_percent)
    figure = px.bar(chart_data, x="issue_rate", y="rule_name", orientation="h", color="severity",
                    color_discrete_map=SEVERITY_COLORS, title="各质量规则异常率",
                    hover_data=["checked_count", "issue_count", "issue_rate_label"],
                    labels={"issue_rate": "异常率", "rule_name": "规则", "severity": "严重级别"})
    st.plotly_chart(polish_figure(figure, percent_x=True), width="stretch")
    st.dataframe(quality.sort_values(["severity", "issue_rate"], ascending=[True, False]), width="stretch", hide_index=True)
