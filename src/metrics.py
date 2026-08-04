"""可复用、可单测的业务与模型指标。"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


def safe_rate(numerator: float, denominator: float) -> float:
    """计算比率；分母为 0 或缺失时返回 NaN，避免把未知误写成 0。"""

    if pd.isna(denominator) or denominator == 0:
        return float("nan")
    return float(numerator) / float(denominator)


def conversion_rate(won: Iterable[object]) -> float:
    """根据布尔/0-1 成交标签计算成交率。"""

    values = pd.Series(won, dtype="Float64").dropna()
    return safe_rate(float(values.sum()), float(len(values)))


def delay_rate(actual: Iterable[object], estimated: Iterable[object]) -> float:
    """仅在实际和预计签收时间均有效的记录上计算延迟率。"""

    frame = pd.DataFrame(
        {
            "actual": pd.to_datetime(pd.Series(actual), errors="coerce", format="mixed"),
            "estimated": pd.to_datetime(
                pd.Series(estimated), errors="coerce", format="mixed"
            ),
        }
    ).dropna()
    if frame.empty:
        return float("nan")
    return float((frame["actual"] > frame["estimated"]).mean())


@dataclass(frozen=True)
class TopKMetrics:
    requested_fraction: float
    selected_count: int
    threshold: float
    precision: float
    recall: float
    lift: float


def top_k_metrics(
    y_true: Iterable[int], y_score: Iterable[float], fraction: float = 0.20
) -> TopKMetrics:
    """按稳定排序计算 Top-K 指标，K 使用向上取整且至少为 1。"""

    if not 0 < fraction <= 1:
        raise ValueError("fraction 必须位于 (0, 1] 区间")
    frame = pd.DataFrame({"y_true": y_true, "y_score": y_score})
    if frame.empty:
        raise ValueError("Top-K 指标至少需要一条样本")
    if frame.isna().any().any():
        raise ValueError("y_true 和 y_score 不能包含缺失值")
    if not set(frame["y_true"].unique()).issubset({0, 1}):
        raise ValueError("y_true 只能包含 0 和 1")

    selected_count = max(1, math.ceil(len(frame) * fraction))
    ranked = frame.sort_values("y_score", ascending=False, kind="mergesort")
    selected = ranked.head(selected_count)
    positives = int(frame["y_true"].sum())
    selected_positives = int(selected["y_true"].sum())
    precision = safe_rate(selected_positives, selected_count)
    recall = safe_rate(selected_positives, positives)
    prevalence = safe_rate(positives, len(frame))
    lift = safe_rate(precision, prevalence)
    return TopKMetrics(
        requested_fraction=fraction,
        selected_count=selected_count,
        threshold=float(selected["y_score"].min()),
        precision=precision,
        recall=recall,
        lift=lift,
    )


def wape(y_true: Iterable[float], y_pred: Iterable[float]) -> float:
    """计算 WAPE；真实值绝对值之和为 0 时返回 NaN。"""

    actual = np.asarray(list(y_true), dtype=float)
    predicted = np.asarray(list(y_pred), dtype=float)
    if actual.shape != predicted.shape:
        raise ValueError("y_true 与 y_pred 长度必须一致")
    return safe_rate(np.abs(actual - predicted).sum(), np.abs(actual).sum())
