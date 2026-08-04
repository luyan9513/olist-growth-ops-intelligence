from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.experiments import (
    ASSIGNMENT_REQUIRED_COLUMNS,
    assignment_balance,
    assign_sellers,
    binary_proportion_mde,
    binary_proportion_sample_size,
    validate_experiment_logs,
)


def eligible_sellers(count: int = 200) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "seller_id": [f"s{index:04d}" for index in range(count)],
            "recommended_action": ["P1 履约护航"] * count,
            "activity_band": ["高" if index % 2 == 0 else "中" for index in range(count)],
            "seller_state": ["SP" if index % 3 else "RJ" for index in range(count)],
            "resource_segment": ["稳定运营"] * count,
            "seller_segment": ["高价值高风险"] * count,
        }
    )


def registry_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "experiment_id": "exp1",
                "experiment_name": "履约护航",
                "owner": "ops_team",
                "decision_question": "是否降低低评分率",
                "assignment_unit": "seller_id",
                "eligibility_rule": "P1",
                "treatment_name": "履约护航",
                "control_name": "现有流程",
                "primary_metric": "low_review_rate",
                "guardrail_metrics": "delay_rate,cancel_rate,cost",
                "planned_start_date": "2026-08-03",
                "planned_end_date": "2026-09-30",
                "timezone": "Asia/Shanghai",
                "alpha": 0.05,
                "power": 0.80,
                "status": "draft",
                "design_version": "v1",
            }
        ]
    )


def test_binary_sample_size_is_monotonic_and_mde_can_be_recovered():
    smaller_effect = binary_proportion_sample_size(0.15, 0.02)
    larger_effect = binary_proportion_sample_size(0.15, 0.05)
    assert smaller_effect.total_sample_size > larger_effect.total_sample_size
    assert larger_effect.treatment_sample_size == larger_effect.control_sample_size
    recovered = binary_proportion_mde(larger_effect.total_sample_size, 0.15)
    assert recovered == pytest.approx(0.05, abs=0.001)
    increase = binary_proportion_sample_size(0.15, 0.05, direction="increase")
    assert increase.alternative_rate == pytest.approx(0.20)
    assert larger_effect.alternative_rate == pytest.approx(0.10)


@pytest.mark.parametrize(
    "baseline,mde",
    [(0, 0.05), (1, 0.05), (0.04, 0.05), (0.2, 0)],
)
def test_binary_sample_size_rejects_invalid_planning_inputs(baseline, mde):
    with pytest.raises(ValueError):
        binary_proportion_sample_size(baseline, mde)


def test_hash_assignment_is_stable_and_independent_of_row_order():
    eligible = eligible_sellers()
    first = assign_sellers(
        eligible,
        "exp1",
        assignment_timestamp="2026-08-03",
        eligibility_snapshot_date="2026-08-01",
    ).sort_values("seller_id")
    second = assign_sellers(
        eligible.sample(frac=1, random_state=99),
        "exp1",
        assignment_timestamp="2026-08-03",
        eligibility_snapshot_date="2026-08-01",
    ).sort_values("seller_id")
    pd.testing.assert_frame_equal(first.reset_index(drop=True), second.reset_index(drop=True))
    assert set(first.columns) == ASSIGNMENT_REQUIRED_COLUMNS
    assert set(first["assigned_group"]) == {"treatment", "control"}
    assert first["assignment_id"].is_unique


def test_assignment_rejects_duplicate_seller_and_post_treatment_stratum():
    eligible = eligible_sellers(10)
    duplicate = pd.concat([eligible, eligible.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="必须唯一"):
        assign_sellers(
            duplicate,
            "exp1",
            assignment_timestamp="2026-08-03",
            eligibility_snapshot_date="2026-08-01",
        )
    eligible["final_review_score"] = 5
    with pytest.raises(ValueError, match="未批准"):
        assign_sellers(
            eligible,
            "exp1",
            strata=("final_review_score",),
            assignment_timestamp="2026-08-03",
            eligibility_snapshot_date="2026-08-01",
        )


def test_assignment_balance_uses_pretreatment_dimensions():
    eligible = eligible_sellers()
    assignments = assign_sellers(
        eligible,
        "exp1",
        assignment_timestamp="2026-08-03",
        eligibility_snapshot_date="2026-08-01",
    )
    balance = assignment_balance(assignments, eligible)
    assert set(balance["dimension"]) == {"activity_band", "seller_state"}
    group_sums = balance.groupby(["dimension", "assigned_group"])["within_group_share"].sum()
    assert (group_sums.round(12) == 1).all()


def test_log_validation_accepts_consistent_chain_and_rejects_bad_outcome():
    eligible = eligible_sellers(1)
    assignments = assign_sellers(
        eligible,
        "exp1",
        assignment_timestamp="2026-08-03",
        eligibility_snapshot_date="2026-08-01",
    )
    assignment = assignments.iloc[0]
    executions = pd.DataFrame(
        [
            {
                "execution_id": "run1",
                "assignment_id": assignment["assignment_id"],
                "experiment_id": "exp1",
                "seller_id": assignment["seller_id"],
                "assigned_group": assignment["assigned_group"],
                "execution_timestamp": "2026-08-04",
                "execution_status": "completed",
                "intervention_type": "fulfillment_guard",
                "operator_id_hash": "approved_hash",
                "cost_amount": 10.0,
                "cost_currency": "BRL",
                "notes_code": "ok",
            }
        ]
    )
    outcomes = pd.DataFrame(
        [
            {
                "outcome_id": "out1",
                "assignment_id": assignment["assignment_id"],
                "experiment_id": "exp1",
                "seller_id": assignment["seller_id"],
                "outcome_window_start": "2026-08-04",
                "outcome_window_end": "2026-09-04",
                "orders_count": 10,
                "delivered_orders_count": 8,
                "late_orders_count": 1,
                "reviewed_orders_count": 6,
                "low_review_orders_count": 1,
                "gmv": 1000,
                "cancelled_orders": 1,
                "refund_amount": 20,
                "observed_at": "2026-09-10",
            }
        ]
    )
    counts = validate_experiment_logs(registry_frame(), assignments, executions, outcomes)
    assert counts == {
        "experiment_count": 1,
        "assignment_count": 1,
        "execution_count": 1,
        "outcome_count": 1,
    }
    invalid = outcomes.copy()
    invalid["low_review_orders_count"] = 7
    with pytest.raises(ValueError, match="低评分订单数"):
        validate_experiment_logs(registry_frame(), assignments, executions, invalid)
    invalid = outcomes.copy()
    invalid["orders_count"] = 10.5
    with pytest.raises(ValueError, match="必须是整数"):
        validate_experiment_logs(registry_frame(), assignments, executions, invalid)


def test_experiment_templates_are_header_only_and_match_contract():
    template_dir = Path("data/templates/experiment")
    for filename in [
        "experiment_registry.csv",
        "assignment_log.csv",
        "execution_log.csv",
        "outcome_log.csv",
    ]:
        frame = pd.read_csv(template_dir / filename)
        assert frame.empty
    assert set(pd.read_csv(template_dir / "assignment_log.csv").columns) == ASSIGNMENT_REQUIRED_COLUMNS
