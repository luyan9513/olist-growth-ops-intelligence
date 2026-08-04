from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.portfolio import build_portfolio_artifact, validate_portfolio_evidence


def load(name: str) -> dict:
    return json.loads(Path(name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def evidence() -> dict:
    return load("reports/portfolio_evidence.json")


def test_evidence_reconciles_counts_and_contains_no_seller_detail(evidence):
    assert sum(evidence["operations"]["action_counts"].values()) == 3051
    assert sum(row["seller_count"] for row in evidence["seller_segments"]) == 3095
    assert "seller_priority" not in evidence


def test_experiment_evidence_is_planning_not_observed_effect(evidence):
    experiment = evidence["experiment_readiness"]
    assert experiment["required_total_sample"] == 3864
    assert experiment["current_p1_candidate_count"] == 158
    assert "observed_effect" not in experiment
    assert "尚无真实干预" in experiment["status"]


def test_validator_rejects_capacity_drift_and_observed_effect(evidence):
    invalid = copy.deepcopy(evidence)
    invalid["operations"]["strategy_comparison"][0]["selected_count"] = 199
    with pytest.raises(ValueError, match="容量"):
        validate_portfolio_evidence(invalid)
    invalid = copy.deepcopy(evidence)
    invalid["experiment_readiness"]["observed_effect"] = 0.01
    with pytest.raises(ValueError, match="observed_effect"):
        validate_portfolio_evidence(invalid)


def test_artifact_has_required_report_order_and_bounded_datasets(evidence):
    artifact = build_portfolio_artifact(evidence)
    manifest, snapshot = artifact["manifest"], artifact["snapshot"]
    assert manifest["blocks"][0]["body"] == f"# {manifest['title']}"
    assert manifest["blocks"][1]["body"].startswith("## Executive Summary")
    assert any(block["type"] == "chart" for block in manifest["blocks"])
    assert all(isinstance(rows, list) and len(rows) <= 2000 for rows in snapshot["datasets"].values())
