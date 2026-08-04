"""分类与预测模型评估工具。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    mean_absolute_error,
)

from src.metrics import top_k_metrics, wape


def classification_metrics(
    y_true: Iterable[int], y_score: Iterable[float], fractions: tuple[float, ...] = (0.05, 0.10, 0.20)
) -> dict[str, object]:
    actual = np.asarray(list(y_true), dtype=int)
    score = np.asarray(list(y_score), dtype=float)
    predicted = (score >= 0.5).astype(int)
    matrix = confusion_matrix(actual, predicted, labels=[0, 1])
    probability_true, probability_predicted = calibration_curve(
        actual, score, n_bins=min(10, max(2, len(actual) // 20)), strategy="quantile"
    )
    result: dict[str, object] = {
        "sample_count": int(len(actual)),
        "positive_count": int(actual.sum()),
        "positive_rate": float(actual.mean()),
        "pr_auc": float(average_precision_score(actual, score)),
        "brier_score": float(brier_score_loss(actual, score)),
        "confusion_matrix_at_0_5": matrix.tolist(),
        "calibration": [
            {"mean_prediction": float(pred), "observed_rate": float(obs)}
            for pred, obs in zip(probability_predicted, probability_true)
        ],
        "top_k": {},
    }
    top_k = result["top_k"]
    assert isinstance(top_k, dict)
    for fraction in fractions:
        metrics = top_k_metrics(actual, score, fraction)
        top_k[f"{int(fraction * 100)}pct"] = {
            "selected_count": metrics.selected_count,
            "threshold": metrics.threshold,
            "precision": metrics.precision,
            "recall": metrics.recall,
            "lift": metrics.lift,
        }
    return result


def bootstrap_classification_intervals(
    y_true: Iterable[int],
    y_score: Iterable[float],
    *,
    n_resamples: int = 500,
    confidence_level: float = 0.95,
    random_seed: int = 42,
    top_fraction: float = 0.20,
) -> dict[str, object]:
    """对最终测试指标做有放回样本 bootstrap，返回百分位区间。"""

    actual = np.asarray(list(y_true), dtype=int)
    score = np.asarray(list(y_score), dtype=float)
    if len(actual) != len(score) or len(actual) == 0:
        raise ValueError("标签与分数必须等长且不能为空")
    if np.unique(actual).size < 2:
        raise ValueError("bootstrap 分类区间需要同时包含正负样本")
    if n_resamples < 1:
        raise ValueError("n_resamples 必须至少为 1")
    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level 必须位于 (0, 1)")

    point_top_k = top_k_metrics(actual, score, top_fraction)
    point_estimates = {
        "pr_auc": float(average_precision_score(actual, score)),
        "brier_score": float(brier_score_loss(actual, score)),
        "top_k_precision": point_top_k.precision,
        "top_k_recall": point_top_k.recall,
        "top_k_lift": point_top_k.lift,
    }
    samples: dict[str, list[float]] = {name: [] for name in point_estimates}
    rng = np.random.default_rng(random_seed)
    for _ in range(n_resamples):
        indices = rng.integers(0, len(actual), size=len(actual))
        sampled_actual = actual[indices]
        if np.unique(sampled_actual).size < 2:
            continue
        sampled_score = score[indices]
        sampled_top_k = top_k_metrics(sampled_actual, sampled_score, top_fraction)
        values = {
            "pr_auc": float(average_precision_score(sampled_actual, sampled_score)),
            "brier_score": float(brier_score_loss(sampled_actual, sampled_score)),
            "top_k_precision": sampled_top_k.precision,
            "top_k_recall": sampled_top_k.recall,
            "top_k_lift": sampled_top_k.lift,
        }
        for name, value in values.items():
            samples[name].append(value)

    valid_resamples = len(samples["pr_auc"])
    if valid_resamples == 0:
        raise ValueError("bootstrap 未产生同时包含正负样本的有效抽样")
    alpha = (1.0 - confidence_level) / 2.0
    intervals = {
        name: {
            "estimate": point_estimates[name],
            "lower": float(np.quantile(values, alpha)),
            "upper": float(np.quantile(values, 1.0 - alpha)),
        }
        for name, values in samples.items()
    }
    return {
        "method": "row_bootstrap_percentile",
        "requested_resamples": n_resamples,
        "valid_resamples": valid_resamples,
        "confidence_level": confidence_level,
        "random_seed": random_seed,
        "top_fraction": top_fraction,
        "metrics": intervals,
    }


def subgroup_classification_metrics(
    frame: pd.DataFrame,
    group_column: str,
    label_column: str,
    score_column: str,
    minimum_size: int = 30,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for group_value, group in frame.groupby(group_column, dropna=False):
        if len(group) < minimum_size or group[label_column].nunique() < 2:
            continue
        rows.append(
            {
                "group": str(group_value),
                "sample_count": int(len(group)),
                "positive_rate": float(group[label_column].mean()),
                "pr_auc": float(average_precision_score(group[label_column], group[score_column])),
            }
        )
    return sorted(rows, key=lambda row: row["sample_count"], reverse=True)


def forecast_metrics(y_true: Iterable[float], y_pred: Iterable[float]) -> dict[str, float]:
    actual = np.asarray(list(y_true), dtype=float)
    predicted = np.asarray(list(y_pred), dtype=float)
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "wape": float(wape(actual, predicted)),
    }


def write_json(payload: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
