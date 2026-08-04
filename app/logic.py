"""与 Streamlit 解耦的筛选和历史情景计算。"""

from __future__ import annotations

import math

import pandas as pd


def apply_date_filter(
    frame: pd.DataFrame, column: str, start: object | None, end: object | None
) -> pd.DataFrame:
    if column not in frame.columns:
        return frame.copy()
    values = pd.to_datetime(frame[column], errors="coerce")
    mask = values.notna()
    if start is not None:
        mask &= values.dt.date >= pd.Timestamp(start).date()
    if end is not None:
        mask &= values.dt.date <= pd.Timestamp(end).date()
    return frame.loc[mask].copy()


def historical_capacity_scenario(
    frame: pd.DataFrame,
    score_column: str,
    label_column: str,
    capacity: int,
    unit_cost: float,
    value_column: str | None = None,
) -> dict[str, float | int]:
    if frame.empty:
        raise ValueError("情景模拟需要非空历史预测结果")
    required = {score_column, label_column}
    if not required.issubset(frame.columns):
        raise ValueError(f"情景模拟缺少字段: {sorted(required.difference(frame.columns))}")
    if capacity < 0 or unit_cost < 0:
        raise ValueError("容量和假设单位成本不能为负")
    selected_count = min(int(capacity), len(frame))
    selected = frame.sort_values(score_column, ascending=False, kind="mergesort").head(selected_count)
    total_positive = float(frame[label_column].sum())
    selected_positive = float(selected[label_column].sum())
    result: dict[str, float | int] = {
        "available_count": int(len(frame)),
        "selected_count": selected_count,
        "assumed_total_cost": float(selected_count * unit_cost),
        "selected_positive_count": int(selected_positive),
        "positive_coverage": selected_positive / total_positive if total_positive else math.nan,
    }
    if value_column and value_column in frame.columns:
        total_value = float(frame[value_column].fillna(0).sum())
        selected_value = float(selected[value_column].fillna(0).sum())
        result["value_coverage"] = selected_value / total_value if total_value else math.nan
    return result
