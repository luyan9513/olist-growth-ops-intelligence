"""看板共用组件。"""

from __future__ import annotations

import pandas as pd
import streamlit as st


DISCLAIMER = "公开历史数据离线分析，不代表因果关系、真实 ROI、线上效果或业务收益。"


def page_header(title: str, description: str, freshness: str | None = None) -> None:
    st.title(title)
    st.caption(description)
    if freshness:
        st.caption(f"数据截至：{freshness}｜{DISCLAIMER}")


def require_data(frame: pd.DataFrame, empty_message: str = "当前筛选范围没有数据。") -> bool:
    if frame.empty:
        st.info(empty_message)
        return False
    return True


def format_percent(value: float) -> str:
    return "—" if pd.isna(value) else f"{value:.1%}"


def format_number(value: float) -> str:
    return "—" if pd.isna(value) else f"{value:,.0f}"


def format_money(value: float) -> str:
    return "—" if pd.isna(value) else f"{value:,.2f}"


def csv_download(label: str, frame: pd.DataFrame, filename: str) -> None:
    st.download_button(
        label,
        frame.to_csv(index=False).encode("utf-8-sig"),
        file_name=filename,
        mime="text/csv",
    )
