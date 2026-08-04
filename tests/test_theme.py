from __future__ import annotations

import plotly.express as px

from app.theme import CHART_COLORS, configure_chart_defaults, polish_figure


def test_chart_theme_uses_consistent_palette_and_percent_axis():
    configure_chart_defaults()
    assert px.defaults.color_discrete_sequence == CHART_COLORS
    figure = polish_figure(px.bar(x=[0.1, 0.2], y=["A", "B"]), percent_x=True)
    assert figure.layout.xaxis.tickformat == ".2%"
    assert figure.layout.margin.t == 64
