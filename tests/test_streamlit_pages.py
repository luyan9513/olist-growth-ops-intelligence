import pytest
from streamlit.testing.v1 import AppTest


def test_main_streamlit_app_renders_without_exception():
    app = AppTest.from_file("app/app.py", default_timeout=30).run()
    assert not app.exception


@pytest.mark.parametrize(
    "page_name",
    [
        "growth",
        "channel",
        "sellers",
        "ops_actions",
        "experiments",
        "delivery",
        "leads",
        "demand",
        "scenario",
        "quality",
    ],
)
def test_streamlit_page_renders_without_exception(page_name):
    source = f"from app.pages import {page_name}\n{page_name}.render()"
    app = AppTest.from_string(source, default_timeout=30).run()
    assert not app.exception


def test_ops_actions_default_state_renders_metrics_and_detail():
    source = "from app.pages import ops_actions\nops_actions.render()"
    app = AppTest.from_string(source, default_timeout=30).run()
    assert not app.exception
    metric_labels = {metric.label for metric in app.metric}
    assert {
        "可排期商家",
        "P1 履约护航",
        "活动概率质量覆盖",
        "高价值高风险覆盖",
    }.issubset(metric_labels)
    assert app.dataframe
    assert any("不代表因果关系" in warning.value for warning in app.warning)


def test_experiments_default_state_is_explicitly_planning_only():
    source = "from app.pages import experiments\nexperiments.render()"
    app = AppTest.from_string(source, default_timeout=30).run()
    assert not app.exception
    metric_labels = {metric.label for metric in app.metric}
    assert {"当前候选商家", "规划所需总样本", "当前池可检测 MDE"}.issubset(metric_labels)
    assert any("规划中、未启动" in warning.value for warning in app.warning)
