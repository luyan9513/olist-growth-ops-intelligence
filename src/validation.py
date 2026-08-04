"""时间切分与特征泄漏防护。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Collection, Iterable

import pandas as pd


LEAD_FORBIDDEN_FEATURES = frozenset(
    {
        "won_date",
        "won_at",
        "seller_id",
        "order_id",
        "gmv",
        "order_count",
        "review_score",
    }
)

REVIEW_RISK_FORBIDDEN_FEATURES = frozenset(
    {
        "review_score",
        "low_review_flag",
        "review_comment_title",
        "review_comment_message",
        "review_creation_date",
        "review_answer_timestamp",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "is_delayed",
        "delivery_days",
    }
)


def assert_no_forbidden_features(
    columns: Collection[str], forbidden: Collection[str], model_name: str
) -> None:
    """发现禁用特征时立即失败，并给出可定位的列名。"""

    collisions = sorted(set(columns).intersection(forbidden))
    if collisions:
        joined = ", ".join(collisions)
        raise ValueError(f"{model_name} 检测到泄漏风险字段: {joined}")


@dataclass(frozen=True)
class TimeSplit:
    train_index: pd.Index
    validation_index: pd.Index
    test_index: pd.Index
    train_end: pd.Timestamp
    validation_end: pd.Timestamp


@dataclass(frozen=True)
class CalibrationSplit:
    selection_index: pd.Index
    calibration_index: pd.Index
    selection_end: pd.Timestamp


@dataclass(frozen=True)
class ExpandingWindow:
    train_index: pd.Index
    evaluation_index: pd.Index
    train_end: pd.Timestamp
    evaluation_start: pd.Timestamp
    evaluation_end: pd.Timestamp


def temporal_split(
    event_time: Iterable[object],
    train_fraction: float = 0.65,
    validation_fraction: float = 0.15,
) -> TimeSplit:
    """按唯一日期切分，保证同一天不会跨集合。"""

    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction 必须位于 (0, 1)")
    if not 0 < validation_fraction < 1:
        raise ValueError("validation_fraction 必须位于 (0, 1)")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("训练与验证占比之和必须小于 1")

    times = pd.to_datetime(pd.Series(event_time), errors="coerce", format="mixed")
    if times.isna().any():
        raise ValueError("时间切分字段不能包含无效或缺失时间")
    unique_dates = pd.Index(times.dt.normalize().unique()).sort_values()
    if len(unique_dates) < 3:
        raise ValueError("时间切分至少需要 3 个不同日期")

    train_pos = min(len(unique_dates) - 3, max(0, int(len(unique_dates) * train_fraction) - 1))
    validation_pos = min(
        len(unique_dates) - 2,
        max(train_pos + 1, int(len(unique_dates) * (train_fraction + validation_fraction)) - 1),
    )
    train_end = pd.Timestamp(unique_dates[train_pos])
    validation_end = pd.Timestamp(unique_dates[validation_pos])
    normalized = times.dt.normalize()
    return TimeSplit(
        train_index=times.index[normalized <= train_end],
        validation_index=times.index[(normalized > train_end) & (normalized <= validation_end)],
        test_index=times.index[normalized > validation_end],
        train_end=train_end,
        validation_end=validation_end,
    )


def temporal_calibration_split(
    event_time: Iterable[object], selection_fraction: float = 0.5
) -> CalibrationSplit:
    """将验证期按日期拆成较早选模期和较晚校准期。"""

    if not 0 < selection_fraction < 1:
        raise ValueError("selection_fraction 必须位于 (0, 1)")
    times = pd.to_datetime(pd.Series(event_time), errors="coerce", format="mixed")
    if times.isna().any():
        raise ValueError("校准切分字段不能包含无效或缺失时间")
    unique_dates = pd.Index(times.dt.normalize().unique()).sort_values()
    if len(unique_dates) < 2:
        raise ValueError("选模与校准至少需要 2 个不同日期")
    selection_position = min(
        len(unique_dates) - 2,
        max(0, int(len(unique_dates) * selection_fraction) - 1),
    )
    selection_end = pd.Timestamp(unique_dates[selection_position])
    normalized = times.dt.normalize()
    return CalibrationSplit(
        selection_index=times.index[normalized <= selection_end],
        calibration_index=times.index[normalized > selection_end],
        selection_end=selection_end,
    )


def expanding_time_windows(
    event_time: Iterable[object],
    *,
    n_windows: int = 3,
    minimum_train_fraction: float = 0.6,
) -> list[ExpandingWindow]:
    """构建连续、互不重叠的评估窗，每窗训练数据严格早于评估数据。"""

    if n_windows < 1:
        raise ValueError("n_windows 必须至少为 1")
    if not 0 < minimum_train_fraction < 1:
        raise ValueError("minimum_train_fraction 必须位于 (0, 1)")
    times = pd.to_datetime(pd.Series(event_time), errors="coerce", format="mixed")
    if times.isna().any():
        raise ValueError("滚动窗口字段不能包含无效或缺失时间")
    unique_dates = pd.Index(times.dt.normalize().unique()).sort_values()
    minimum_train_dates = max(1, int(len(unique_dates) * minimum_train_fraction))
    evaluation_dates = unique_dates[minimum_train_dates:]
    if len(evaluation_dates) < n_windows:
        raise ValueError("可用评估日期不足以构建指定数量的滚动窗口")

    base_size, remainder = divmod(len(evaluation_dates), n_windows)
    windows: list[ExpandingWindow] = []
    cursor = 0
    normalized = times.dt.normalize()
    for window_number in range(n_windows):
        size = base_size + (1 if window_number < remainder else 0)
        window_dates = evaluation_dates[cursor : cursor + size]
        evaluation_start = pd.Timestamp(window_dates[0])
        evaluation_end = pd.Timestamp(window_dates[-1])
        train_mask = normalized < evaluation_start
        evaluation_mask = (normalized >= evaluation_start) & (normalized <= evaluation_end)
        windows.append(
            ExpandingWindow(
                train_index=times.index[train_mask],
                evaluation_index=times.index[evaluation_mask],
                train_end=pd.Timestamp(unique_dates[minimum_train_dates + cursor - 1]),
                evaluation_start=evaluation_start,
                evaluation_end=evaluation_end,
            )
        )
        cursor += size
    return windows
