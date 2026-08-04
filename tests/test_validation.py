import pandas as pd
import pytest

from src.validation import (
    LEAD_FORBIDDEN_FEATURES,
    REVIEW_RISK_FORBIDDEN_FEATURES,
    assert_no_forbidden_features,
    expanding_time_windows,
    temporal_calibration_split,
    temporal_split,
)


def test_lead_feature_blacklist_blocks_post_conversion_fields():
    with pytest.raises(ValueError, match="seller_id"):
        assert_no_forbidden_features(
            ["origin", "seller_id"], LEAD_FORBIDDEN_FEATURES, "线索成交模型"
        )


def test_review_feature_blacklist_blocks_final_outcome():
    with pytest.raises(ValueError, match="review_score"):
        assert_no_forbidden_features(
            ["category", "review_score"],
            REVIEW_RISK_FORBIDDEN_FEATURES,
            "低评分风险模型",
        )


def test_temporal_split_keeps_same_day_together_and_orders_partitions():
    dates = pd.to_datetime(
        [
            "2024-01-01 09:00",
            "2024-01-01 17:00",
            "2024-01-02",
            "2024-01-03",
            "2024-01-04",
            "2024-01-05",
        ],
        format="mixed",
    )
    split = temporal_split(dates, train_fraction=0.5, validation_fraction=0.2)
    partitions = [set(split.train_index), set(split.validation_index), set(split.test_index)]
    assert 0 in partitions[0] and 1 in partitions[0]
    assert all(left.isdisjoint(right) for i, left in enumerate(partitions) for right in partitions[i + 1 :])
    assert dates[split.train_index].max().normalize() <= split.train_end
    assert dates[split.test_index].min().normalize() > split.validation_end


def test_temporal_split_rejects_invalid_times():
    with pytest.raises(ValueError, match="无效"):
        temporal_split(["2024-01-01", "bad", "2024-01-03"])


def test_temporal_calibration_split_keeps_dates_separate():
    times = pd.Series(pd.date_range("2024-01-01", periods=8, freq="D"))
    split = temporal_calibration_split(times)
    assert times.loc[split.selection_index].max() < times.loc[split.calibration_index].min()
    assert set(split.selection_index).isdisjoint(split.calibration_index)


def test_expanding_time_windows_are_ordered_and_non_overlapping():
    times = pd.Series(pd.date_range("2024-01-01", periods=30, freq="D"))
    windows = expanding_time_windows(times, n_windows=3, minimum_train_fraction=0.6)
    seen_evaluation: set[int] = set()
    for window in windows:
        assert times.loc[window.train_index].max() < times.loc[window.evaluation_index].min()
        assert seen_evaluation.isdisjoint(set(window.evaluation_index))
        seen_evaluation.update(window.evaluation_index)
