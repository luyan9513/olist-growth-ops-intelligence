from __future__ import annotations

import streamlit as st

from app.components import DISCLAIMER
from app.data import DATABASE_PATH, database_ready
from app.pages import (
    channel,
    delivery,
    demand,
    experiments,
    growth,
    leads,
    ops_actions,
    quality,
    scenario,
    sellers,
)
from app.theme import configure_chart_defaults


def main() -> None:
    """渲染应用；由根目录入口显式调用，确保每个 Streamlit 会话都执行。"""

    st.set_page_config(page_title="Olist 商家增长与履约运营", page_icon="📦", layout="wide")
    configure_chart_defaults()

    st.sidebar.markdown("### Olist 运营智能平台")
    st.sidebar.caption("10 个分析页面 · 本地只读作品集")
    st.sidebar.caption(DISCLAIMER)

    if not database_ready():
        st.title("商家增长与履约运营智能平台")
        st.error(f"尚未找到数据仓库：`{DATABASE_PATH}`")
        st.markdown(
            "请先按照 `data/raw/README.md` 准备 Olist 原始 CSV，然后运行：\n\n"
            "```bash\nmake manifest\nmake dbt-build\n.venv/bin/python -m src.train all\n```"
        )
        st.stop()

    pages = {
        "增长与经营": [
            st.Page(growth.render, title="增长总览", icon="📈", url_path="growth", default=True),
            st.Page(channel.render, title="渠道质量", icon="🧭", url_path="channels"),
            st.Page(sellers.render, title="商家经营", icon="🏪", url_path="sellers"),
            st.Page(ops_actions.render, title="商家运营行动", icon="📋", url_path="ops-actions"),
            st.Page(experiments.render, title="实验设计", icon="⚖️", url_path="experiments"),
        ],
        "履约与预测": [
            st.Page(delivery.render, title="履约体验", icon="🚚", url_path="delivery"),
            st.Page(leads.render, title="线索优先级", icon="🎯", url_path="leads"),
            st.Page(demand.render, title="需求预测", icon="🔭", url_path="demand"),
            st.Page(scenario.render, title="历史情景模拟", icon="🧪", url_path="scenario"),
        ],
        "治理": [st.Page(quality.render, title="数据质量", icon="✅", url_path="quality")],
    }

    navigation = st.navigation(pages)
    navigation.run()
