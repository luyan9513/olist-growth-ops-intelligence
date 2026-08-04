from __future__ import annotations

import plotly.express as px
from plotly.graph_objects import Figure


CHART_COLORS = ["#0F6CBD", "#12A594", "#F59E0B", "#E45756", "#7C3AED", "#64748B"]
SEVERITY_COLORS = {"error": "#C62828", "warn": "#F59E0B"}


def configure_chart_defaults() -> None:
    """设置所有页面共享的 Plotly 默认主题，不注入脆弱的 HTML/CSS。"""

    px.defaults.template = "plotly_white"
    px.defaults.color_discrete_sequence = CHART_COLORS


def polish_figure(figure: Figure, *, percent_x: bool = False, percent_y: bool = False) -> Figure:
    """统一图表留白、字体和比例轴格式。"""

    figure.update_layout(
        margin={"l": 12, "r": 12, "t": 64, "b": 12},
        font={"color": "#172033"},
        legend_title_text="",
        hovermode="closest",
    )
    figure.update_xaxes(showgrid=True, gridcolor="#E7EDF5", zeroline=False)
    figure.update_yaxes(showgrid=True, gridcolor="#E7EDF5", zeroline=False)
    if percent_x:
        figure.update_xaxes(tickformat=".2%")
    if percent_y:
        figure.update_yaxes(tickformat=".2%")
    return figure
