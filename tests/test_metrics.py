import math

import pytest

from src.metrics import conversion_rate, delay_rate, safe_rate, top_k_metrics, wape


def test_safe_rate_zero_denominator_returns_nan():
    assert math.isnan(safe_rate(1, 0))


def test_conversion_rate_uses_valid_labels():
    assert conversion_rate([1, 0, 1, None]) == pytest.approx(2 / 3)


def test_delay_rate_excludes_missing_timestamps():
    actual = ["2024-01-03", "2024-01-02", None]
    estimated = ["2024-01-02", "2024-01-02", "2024-01-01"]
    assert delay_rate(actual, estimated) == pytest.approx(0.5)


def test_top_k_metrics_rounds_up_and_reports_recall():
    result = top_k_metrics([1, 0, 1, 0, 0], [0.9, 0.8, 0.7, 0.2, 0.1], 0.20)
    assert result.selected_count == 1
    assert result.precision == 1.0
    assert result.recall == 0.5
    assert result.lift == 2.5


def test_top_k_rejects_invalid_fraction():
    with pytest.raises(ValueError, match="fraction"):
        top_k_metrics([1], [0.5], 0)


def test_wape():
    assert wape([10, 20], [8, 25]) == pytest.approx(7 / 30)
    assert math.isnan(wape([0, 0], [1, 2]))
