import pytest

from src.evaluate import bootstrap_classification_intervals, classification_metrics, forecast_metrics


def test_classification_metrics_contains_top_k_and_calibration():
    y_true = [0, 1] * 20
    y_score = [0.1, 0.9] * 20
    result = classification_metrics(y_true, y_score)
    assert result["pr_auc"] == pytest.approx(1.0)
    assert "20pct" in result["top_k"]
    assert result["calibration"]


def test_forecast_metrics():
    result = forecast_metrics([10, 20], [8, 25])
    assert result["mae"] == pytest.approx(3.5)
    assert result["wape"] == pytest.approx(7 / 30)


def test_bootstrap_classification_intervals_are_reproducible():
    y_true = [0, 1] * 30
    y_score = [0.1, 0.9] * 30
    first = bootstrap_classification_intervals(y_true, y_score, n_resamples=40)
    second = bootstrap_classification_intervals(y_true, y_score, n_resamples=40)
    assert first == second
    assert first["valid_resamples"] == 40
    assert first["metrics"]["pr_auc"]["estimate"] == pytest.approx(1.0)
    assert first["metrics"]["pr_auc"]["lower"] == pytest.approx(1.0)


def test_bootstrap_rejects_single_class():
    with pytest.raises(ValueError, match="正负样本"):
        bootstrap_classification_intervals([0, 0], [0.1, 0.2], n_resamples=5)
