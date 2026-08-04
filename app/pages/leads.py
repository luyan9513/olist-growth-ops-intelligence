from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from app.components import csv_download, page_header, require_data
from app.data import load_csv_artifact, load_json_artifact
from app.theme import polish_figure


def render() -> None:
    predictions = load_csv_artifact("lead_conversion/test_predictions.csv")
    metrics = load_json_artifact("lead_conversion/metrics.json")
    page_header("线索优先级", "测试集离线排序表现与可下载触达清单。")
    if not require_data(predictions, "线索模型尚未运行。请先完成 dbt build，再运行 `.venv/bin/python -m src.train lead`。"):
        return
    selected = str(metrics.get("selected_model", ""))
    score_column = f"score_{selected}"
    top_k = metrics.get("test_metrics", {}).get(selected, {}).get("top_k", {}).get("20pct", {})
    cards = st.columns(3)
    cards[0].metric("选中模型", selected)
    cards[1].metric("Top 20% Precision", f"{top_k.get('precision', float('nan')):.1%}")
    cards[2].metric("Top 20% Recall", f"{top_k.get('recall', float('nan')):.1%}")
    bootstrap = metrics.get("bootstrap_intervals", {}).get(selected, {}).get("metrics", {})
    pr_interval = bootstrap.get("pr_auc", {})
    calibration = metrics.get("calibration", {}).get("comparison", {})
    raw_brier = calibration.get("uncalibrated", {}).get("brier_score", float("nan"))
    calibrated_brier = calibration.get("sigmoid_calibrated", {}).get("brier_score", float("nan"))
    stability_cards = st.columns(3)
    stability_cards[0].metric(
        "PR-AUC 95% 区间",
        f"{pr_interval.get('lower', float('nan')):.3f}–{pr_interval.get('upper', float('nan')):.3f}",
    )
    stability_cards[1].metric("校准前 Brier", f"{raw_brier:.3f}")
    stability_cards[2].metric("校准后 Brier", f"{calibrated_brier:.3f}")
    figure = px.histogram(predictions, x=score_column, color="is_won", nbins=30,
                          title="测试集预测分数分布",
                          labels={score_column: "预测分数", "count": "线索数", "is_won": "是否成交"})
    st.plotly_chart(polish_figure(figure), width="stretch")
    ranked = predictions.sort_values(score_column, ascending=False)
    st.dataframe(ranked, width="stretch", hide_index=True)
    csv_download("下载测试集排序名单", ranked, "lead_priority_test.csv")
    rolling_records = metrics.get("rolling_time_backtest", {}).get("records", [])
    with st.expander("查看滚动时间窗口稳定性"):
        if rolling_records:
            rolling = pd.DataFrame(rolling_records)
            st.dataframe(rolling, width="stretch", hide_index=True)
        else:
            st.info("当前模型产物尚未包含滚动时间回测。")
        st.caption("滚动窗口用于检查跨时间稳定性；bootstrap 区间反映当前测试样本抽样波动，不代表线上因果效果。")
    st.caption("名单含真实测试标签，仅用于离线评估；现实触达时不能提前获得标签。")
