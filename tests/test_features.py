import pandas as pd
import pytest

from src.features import add_demand_lag_features, complete_weekly_series
from src.forecast import (
    build_demand_segments,
    croston_sba_fitted,
    demand_activity_segment,
    rolling_backtest,
    trim_trailing_incomplete_weeks,
)


def test_complete_weekly_series_fills_internal_gaps():
    frame = pd.DataFrame(
        {
            "entity": ["a", "a"],
            "week_start": pd.to_datetime(["2024-01-01", "2024-01-15"]),
            "order_count": [2, 3],
        }
    )
    result = complete_weekly_series(frame, "entity")
    assert result["order_count"].tolist() == [2, 0, 3]


def test_demand_lags_do_not_use_current_or_future_value():
    frame = pd.DataFrame(
        {
            "entity": ["a"] * 5,
            "week_start": pd.date_range("2024-01-01", periods=5, freq="7D"),
            "order_count": [1, 2, 3, 4, 999],
        }
    )
    features = add_demand_lag_features(frame, "entity")
    assert features.loc[4, "lag_1"] == 4
    assert features.loc[4, "rolling_mean_4"] == pytest.approx(2.5)
    changed = frame.copy()
    changed.loc[4, "order_count"] = -999
    changed_features = add_demand_lag_features(changed, "entity")
    assert changed_features.loc[4, "rolling_mean_4"] == features.loc[4, "rolling_mean_4"]
    assert changed_features.loc[4, "active_weeks_last_4"] == features.loc[4, "active_weeks_last_4"]
    assert changed_features.loc[4, "weeks_since_last_order"] == features.loc[4, "weeks_since_last_order"]


def test_demand_activity_features_only_use_prior_weeks():
    frame = pd.DataFrame(
        {
            "entity": ["a"] * 5,
            "week_start": pd.date_range("2024-01-01", periods=5, freq="7D"),
            "order_count": [0, 2, 0, 0, 4],
        }
    )
    result = add_demand_lag_features(frame, "entity")
    assert result.loc[4, "active_weeks_last_4"] == 1
    assert result.loc[2, "weeks_since_last_order"] == 1
    assert result.loc[4, "weeks_since_last_order"] == 3


def test_croston_fitted_prediction_does_not_use_current_or_future_demand():
    original = pd.Series([0, 2, 0, 0, 4, 0], dtype=float)
    changed = original.copy()
    changed.iloc[4:] = [400, 900]
    original_forecast = croston_sba_fitted(original)
    changed_forecast = croston_sba_fitted(changed)
    assert original_forecast[:5].tolist() == pytest.approx(changed_forecast[:5].tolist())
    assert original_forecast[2] == pytest.approx(0.95)


def test_fixed_activity_segments():
    result = demand_activity_segment(pd.Series([0, 1, 2, 6, 7, 13]))
    assert result.tolist() == [
        "长尾/沉默",
        "长尾/沉默",
        "间歇活跃",
        "间歇活跃",
        "持续活跃",
        "持续活跃",
    ]


def test_intermittent_backtest_outputs_activity_and_nonnegative_demand():
    weeks = pd.date_range("2024-01-01", periods=20, freq="7D")
    frame = pd.concat(
        [
            pd.DataFrame(
                {
                    "entity": entity,
                    "week_start": weeks,
                    "order_count": values,
                }
            )
            for entity, values in {
                "a": [1 if index % 2 == 0 else 0 for index in range(20)],
                "b": [2 if index % 3 == 0 else 0 for index in range(20)],
                "c": [1 if index % 5 == 0 else 0 for index in range(20)],
            }.items()
        ],
        ignore_index=True,
    )
    result = rolling_backtest(
        frame, entity_column="entity", test_weeks=4, intermittent=True
    )
    assert {"croston_sba", "two_stage_expected"}.issubset(result.metrics)
    assert result.predictions["two_stage_expected"].ge(0).all()
    assert result.predictions["activity_probability"].between(0, 1).all()
    assert result.occurrence_metrics is not None
    assert result.weekly_metrics is not None and len(result.weekly_metrics) == 20
    assert result.weekly_occurrence_metrics is not None
    assert len(result.weekly_occurrence_metrics) == 8
    assert result.segment_metrics is not None


def test_complete_weekly_series_rejects_missing_columns():
    with pytest.raises(ValueError, match="缺少字段"):
        complete_weekly_series(pd.DataFrame({"entity": ["a"]}), "entity")


def test_complete_weekly_series_extends_inactive_entity_to_global_end():
    frame = pd.DataFrame(
        {
            "entity": ["a", "b", "b"],
            "week_start": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-15"]),
            "order_count": [2, 1, 3],
        }
    )
    result = complete_weekly_series(frame, "entity")
    entity_a = result[result["entity"] == "a"]
    assert entity_a["order_count"].tolist() == [2, 0, 0]


def test_trailing_incomplete_weeks_are_removed_without_touching_normal_weeks():
    frame = pd.DataFrame(
        {
            "primary_category_name": ["a"] * 11,
            "week_start": pd.date_range("2024-01-01", periods=11, freq="7D"),
            "order_count": [100] * 9 + [10, 1],
        }
    )
    trimmed = trim_trailing_incomplete_weeks(frame)
    assert trimmed["week_start"].max() == pd.Timestamp("2024-02-26")


def test_demand_segments_use_two_non_overlapping_windows():
    weeks = pd.date_range("2024-01-01", periods=26, freq="7D")
    frame = pd.DataFrame(
        {
            "entity": ["a"] * 26,
            "week_start": weeks,
            "order_count": [1] * 13 + [2] * 13,
            "gross_value": [10.0] * 13 + [20.0] * 13,
        }
    )
    result = build_demand_segments(frame, "entity")
    assert result.loc[0, "latest_13w_orders"] == 26
    assert result.loc[0, "prior_13w_orders"] == 13
