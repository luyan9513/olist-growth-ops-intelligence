import pytest
from streamlit.testing.v1 import AppTest


PAGE_NAMES = [
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
]


def page_source(page_name: str) -> str:
    return (
        "from tests.streamlit_fixtures import patch_page_data\n"
        f"from app.pages import {page_name}\n"
        f"patch_page_data({page_name!r}, {page_name})\n"
        f"{page_name}.render()"
    )


def test_main_streamlit_app_handles_missing_database_without_exception():
    source = """
from pathlib import Path
import app.data as data
data.DATABASE_PATH = Path("data/processed/fixture_database_does_not_exist.duckdb")
import app.app as app_module
app_module.DATABASE_PATH = data.DATABASE_PATH
app_module.main()
"""
    app = AppTest.from_string(source, default_timeout=30).run()
    assert not app.exception
    assert any("尚未找到数据仓库" in error.value for error in app.error)


@pytest.mark.parametrize(
    "page_name", PAGE_NAMES,
)
def test_streamlit_page_renders_with_synthetic_contract_data(page_name):
    app = AppTest.from_string(page_source(page_name), default_timeout=30).run()
    assert not app.exception


def test_ops_actions_default_state_renders_metrics_and_detail():
    app = AppTest.from_string(page_source("ops_actions"), default_timeout=30).run()
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
    app = AppTest.from_string(page_source("experiments"), default_timeout=30).run()
    assert not app.exception
    metric_labels = {metric.label for metric in app.metric}
    assert {"当前候选商家", "规划所需总样本", "当前池可检测 MDE"}.issubset(metric_labels)
    assert any("规划中、未启动" in warning.value for warning in app.warning)
