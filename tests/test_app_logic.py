import math

import pandas as pd
import pytest

from app.logic import historical_capacity_scenario


def test_historical_capacity_scenario_uses_highest_scores():
    frame = pd.DataFrame({"score": [0.1, 0.9, 0.8], "label": [0, 1, 0]})
    result = historical_capacity_scenario(frame, "score", "label", capacity=2, unit_cost=3.0)
    assert result["selected_count"] == 2
    assert result["selected_positive_count"] == 1
    assert result["positive_coverage"] == 1.0
    assert result["assumed_total_cost"] == 6.0


def test_historical_capacity_zero_positive_returns_nan():
    frame = pd.DataFrame({"score": [0.2], "label": [0]})
    result = historical_capacity_scenario(frame, "score", "label", 1, 0)
    assert math.isnan(result["positive_coverage"])


def test_historical_capacity_rejects_negative_input():
    frame = pd.DataFrame({"score": [0.2], "label": [0]})
    with pytest.raises(ValueError, match="不能为负"):
        historical_capacity_scenario(frame, "score", "label", -1, 0)
