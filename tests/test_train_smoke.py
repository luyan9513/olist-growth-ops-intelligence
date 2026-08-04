import numpy as np
import pandas as pd

from src.train import ClassificationSpec, train_classification


def test_classification_training_smoke(tmp_path):
    rng = np.random.default_rng(42)
    size = 240
    signal = np.tile([0, 1, 0], size // 3)
    frame = pd.DataFrame(
        {
            "entity_id": [f"id_{index}" for index in range(size)],
            "prediction_at": pd.date_range("2024-01-01", periods=size, freq="D"),
            "channel": np.where(signal == 1, "high", "low"),
            "value": signal + rng.normal(0, 0.2, size),
            "label": signal,
        }
    )
    spec = ClassificationSpec(
        name="synthetic_smoke_test",
        id_columns=["entity_id"],
        categorical_features=["channel"],
        numeric_features=["value"],
        label="label",
        event_time="prediction_at",
        subgroup_columns=["channel"],
    )
    result = train_classification(frame, spec, tmp_path)
    assert result["selected_model"] in {"logistic_regression", "random_forest"}
    assert (tmp_path / "metrics.json").is_file()
    assert (tmp_path / "test_predictions.csv").is_file()
    assert (tmp_path / "selected_model.joblib").is_file()
    assert (tmp_path / "selected_calibrated_model.joblib").is_file()
    assert result["calibration"]["calibration_count"] > 0
    assert result["bootstrap_intervals"]["selected_sigmoid_calibrated"]["valid_resamples"] == 500
    assert result["rolling_time_backtest"]["window_count"] == 3
    assert "random_forest" in result["rolling_time_backtest"]["summary"]
