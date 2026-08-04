"""实验前规划、稳定随机分组和真实干预日志契约校验。"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from statistics import NormalDist
from typing import Literal

import pandas as pd


ASSIGNMENT_VERSION = "seller_experiment_hash_v1"
ALLOWED_GROUPS = {"treatment", "control"}
ALLOWED_EXPERIMENT_STATUS = {"draft", "approved", "running", "completed", "cancelled"}
ALLOWED_PRETREATMENT_STRATA = {
    "recommended_action",
    "activity_band",
    "seller_state",
    "resource_segment",
    "seller_segment",
}

REGISTRY_REQUIRED_COLUMNS = {
    "experiment_id",
    "experiment_name",
    "owner",
    "decision_question",
    "assignment_unit",
    "eligibility_rule",
    "treatment_name",
    "control_name",
    "primary_metric",
    "guardrail_metrics",
    "planned_start_date",
    "planned_end_date",
    "timezone",
    "alpha",
    "power",
    "status",
    "design_version",
}
ASSIGNMENT_REQUIRED_COLUMNS = {
    "assignment_id",
    "experiment_id",
    "seller_id",
    "assigned_group",
    "assignment_timestamp",
    "eligibility_snapshot_date",
    "stratum",
    "recommended_action",
    "activity_band",
    "assignment_hash",
    "design_version",
}
EXECUTION_REQUIRED_COLUMNS = {
    "execution_id",
    "assignment_id",
    "experiment_id",
    "seller_id",
    "assigned_group",
    "execution_timestamp",
    "execution_status",
    "intervention_type",
    "operator_id_hash",
    "cost_amount",
    "cost_currency",
    "notes_code",
}
OUTCOME_REQUIRED_COLUMNS = {
    "outcome_id",
    "assignment_id",
    "experiment_id",
    "seller_id",
    "outcome_window_start",
    "outcome_window_end",
    "orders_count",
    "delivered_orders_count",
    "late_orders_count",
    "reviewed_orders_count",
    "low_review_orders_count",
    "gmv",
    "cancelled_orders",
    "refund_amount",
    "observed_at",
}


@dataclass(frozen=True)
class BinaryExperimentPlan:
    baseline_rate: float
    alternative_rate: float
    absolute_mde: float
    alpha: float
    power: float
    treatment_share: float
    direction: str
    control_sample_size: int
    treatment_sample_size: int
    total_sample_size: int


def _validate_probability(value: float, name: str, *, inclusive: bool = False) -> None:
    lower_valid = value >= 0 if inclusive else value > 0
    upper_valid = value <= 1 if inclusive else value < 1
    if not math.isfinite(value) or not lower_valid or not upper_valid:
        boundary = "[0, 1]" if inclusive else "(0, 1)"
        raise ValueError(f"{name} 必须在 {boundary} 范围内")


def binary_proportion_sample_size(
    baseline_rate: float,
    absolute_mde: float,
    *,
    alpha: float = 0.05,
    power: float = 0.80,
    treatment_share: float = 0.50,
    direction: Literal["decrease", "increase"] = "decrease",
) -> BinaryExperimentPlan:
    """用两个独立比例的双侧正态近似规划样本量。"""

    _validate_probability(baseline_rate, "基线率")
    _validate_probability(alpha, "alpha")
    _validate_probability(power, "power")
    _validate_probability(treatment_share, "处理组比例")
    if not math.isfinite(absolute_mde) or absolute_mde <= 0:
        raise ValueError("绝对 MDE 必须大于 0")
    if direction not in {"decrease", "increase"}:
        raise ValueError("direction 只能是 decrease 或 increase")
    alternative_rate = (
        baseline_rate - absolute_mde if direction == "decrease" else baseline_rate + absolute_mde
    )
    if not 0 < alternative_rate < 1:
        raise ValueError("基线率按指定方向变化绝对 MDE 后必须在 (0, 1)")

    normal = NormalDist()
    z_alpha = normal.inv_cdf(1 - alpha / 2)
    z_power = normal.inv_cdf(power)
    pooled_rate = (baseline_rate + alternative_rate) / 2
    equal_arm_size = (
        (
            z_alpha * math.sqrt(2 * pooled_rate * (1 - pooled_rate))
            + z_power
            * math.sqrt(
                baseline_rate * (1 - baseline_rate)
                + alternative_rate * (1 - alternative_rate)
            )
        )
        ** 2
        / absolute_mde**2
    )
    equal_total = 2 * equal_arm_size
    allocation_efficiency = 4 * treatment_share * (1 - treatment_share)
    total = int(math.ceil(equal_total / allocation_efficiency))
    treatment = int(math.ceil(total * treatment_share))
    control = int(math.ceil(total * (1 - treatment_share)))
    total = treatment + control
    return BinaryExperimentPlan(
        baseline_rate=baseline_rate,
        alternative_rate=alternative_rate,
        absolute_mde=absolute_mde,
        alpha=alpha,
        power=power,
        treatment_share=treatment_share,
        direction=direction,
        control_sample_size=control,
        treatment_sample_size=treatment,
        total_sample_size=total,
    )


def binary_proportion_mde(
    total_sample_size: int,
    baseline_rate: float,
    *,
    alpha: float = 0.05,
    power: float = 0.80,
    treatment_share: float = 0.50,
    direction: Literal["decrease", "increase"] = "decrease",
) -> float:
    """给定总候选量，反解上述规划公式下的绝对 MDE。"""

    if total_sample_size < 4:
        raise ValueError("总样本量至少为 4")
    _validate_probability(baseline_rate, "基线率")
    if direction not in {"decrease", "increase"}:
        raise ValueError("direction 只能是 decrease 或 increase")
    upper = (baseline_rate if direction == "decrease" else 1 - baseline_rate) - 1e-9
    if upper <= 1e-6:
        raise ValueError("基线率过高，无法反解正向 MDE")
    smallest = binary_proportion_sample_size(
        baseline_rate,
        min(1e-6, upper / 2),
        alpha=alpha,
        power=power,
        treatment_share=treatment_share,
        direction=direction,
    )
    if smallest.total_sample_size <= total_sample_size:
        return 0.0
    low, high = 1e-6, upper
    for _ in range(80):
        midpoint = (low + high) / 2
        required = binary_proportion_sample_size(
            baseline_rate,
            midpoint,
            alpha=alpha,
            power=power,
            treatment_share=treatment_share,
            direction=direction,
        ).total_sample_size
        if required <= total_sample_size:
            high = midpoint
        else:
            low = midpoint
    return high


def _hash_assignment(experiment_id: str, seller_id: str, version: str) -> tuple[str, float]:
    digest = hashlib.sha256(f"{experiment_id}|{seller_id}|{version}".encode("utf-8")).hexdigest()
    uniform_value = int(digest, 16) / 2**256
    return digest, uniform_value


def assign_sellers(
    eligible: pd.DataFrame,
    experiment_id: str,
    *,
    treatment_share: float = 0.50,
    strata: tuple[str, ...] = ("recommended_action", "activity_band", "seller_state"),
    assignment_timestamp: str,
    eligibility_snapshot_date: str,
    assignment_version: str = ASSIGNMENT_VERSION,
) -> pd.DataFrame:
    """按商家生成行序无关、可复现的实验草案分组。"""

    if not experiment_id.strip() or not assignment_version.strip():
        raise ValueError("experiment_id 和 assignment_version 不能为空")
    _validate_probability(treatment_share, "处理组比例")
    if "seller_id" not in eligible.columns:
        raise ValueError("资格快照缺少 seller_id")
    forbidden = set(strata).difference(ALLOWED_PRETREATMENT_STRATA)
    if forbidden:
        raise ValueError(f"存在未批准的分层字段: {sorted(forbidden)}")
    missing = set(strata).difference(eligible.columns)
    if missing:
        raise ValueError(f"资格快照缺少分层字段: {sorted(missing)}")
    if eligible.empty:
        raise ValueError("资格快照不能为空")
    if eligible["seller_id"].isna().any() or eligible["seller_id"].astype(str).str.strip().eq("").any():
        raise ValueError("seller_id 不能为空")
    if eligible["seller_id"].duplicated().any():
        raise ValueError("同一资格快照中的 seller_id 必须唯一")
    assignment_time = pd.to_datetime(assignment_timestamp, errors="coerce", utc=True)
    snapshot_time = pd.to_datetime(eligibility_snapshot_date, errors="coerce", utc=True)
    if pd.isna(assignment_time) or pd.isna(snapshot_time):
        raise ValueError("分组时间和资格快照日期必须是合法日期时间")
    if assignment_time < snapshot_time:
        raise ValueError("分组时间不能早于资格快照日期")

    records: list[dict[str, object]] = []
    for row in eligible.sort_values("seller_id", kind="mergesort").to_dict("records"):
        seller_id = str(row["seller_id"])
        digest, uniform_value = _hash_assignment(experiment_id, seller_id, assignment_version)
        group = "treatment" if uniform_value < treatment_share else "control"
        stratum = "|".join(f"{column}={row[column]}" for column in strata)
        records.append(
            {
                "assignment_id": f"{experiment_id}:{seller_id}",
                "experiment_id": experiment_id,
                "seller_id": seller_id,
                "assigned_group": group,
                "assignment_timestamp": assignment_time.isoformat(),
                "eligibility_snapshot_date": snapshot_time.date().isoformat(),
                "stratum": stratum,
                "recommended_action": row.get("recommended_action"),
                "activity_band": row.get("activity_band"),
                "assignment_hash": digest,
                "design_version": assignment_version,
            }
        )
    return pd.DataFrame(records, columns=sorted(ASSIGNMENT_REQUIRED_COLUMNS))


def assignment_balance(
    assignments: pd.DataFrame,
    eligible: pd.DataFrame,
    dimensions: tuple[str, ...] = ("activity_band", "seller_state"),
) -> pd.DataFrame:
    """汇总处理/对照在干预前维度上的数量和组内占比。"""

    missing = {"seller_id", "assigned_group"}.difference(assignments.columns)
    if missing:
        raise ValueError(f"分组表缺少字段: {sorted(missing)}")
    invalid_dimensions = set(dimensions).difference(ALLOWED_PRETREATMENT_STRATA)
    if invalid_dimensions:
        raise ValueError(f"存在未批准的平衡维度: {sorted(invalid_dimensions)}")
    missing_dimensions = set(dimensions).difference(eligible.columns)
    if missing_dimensions:
        raise ValueError(f"资格快照缺少平衡维度: {sorted(missing_dimensions)}")
    joined = assignments[["seller_id", "assigned_group"]].merge(
        eligible[["seller_id", *dimensions]], on="seller_id", how="left", validate="one_to_one"
    )
    rows: list[dict[str, object]] = []
    group_sizes = joined.groupby("assigned_group")["seller_id"].size()
    for dimension in dimensions:
        counts = joined.groupby(["assigned_group", dimension], dropna=False).size()
        for (group, value), count in counts.items():
            rows.append(
                {
                    "dimension": dimension,
                    "value": str(value),
                    "assigned_group": group,
                    "seller_count": int(count),
                    "within_group_share": float(count / group_sizes[group]),
                }
            )
    return pd.DataFrame(rows)


def _require_columns(frame: pd.DataFrame, required: set[str], name: str) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{name} 缺少字段: {sorted(missing)}")


def _require_unique(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    if frame[columns].isna().any().any() or frame[columns].astype(str).apply(
        lambda column: column.str.strip().eq("")
    ).any().any():
        raise ValueError(f"{name} 的主键不能为空")
    if frame.duplicated(columns).any():
        raise ValueError(f"{name} 的主键必须唯一: {columns}")


def _parse_required_time(frame: pd.DataFrame, column: str, name: str) -> pd.Series:
    parsed = pd.to_datetime(frame[column], errors="coerce", utc=True)
    if parsed.isna().any():
        raise ValueError(f"{name}.{column} 存在非法或缺失时间")
    return parsed


def validate_experiment_logs(
    registry: pd.DataFrame,
    assignments: pd.DataFrame,
    executions: pd.DataFrame,
    outcomes: pd.DataFrame,
) -> dict[str, int]:
    """校验真实实验日志的主键、连接、时间和分子分母关系。"""

    _require_columns(registry, REGISTRY_REQUIRED_COLUMNS, "实验登记表")
    _require_columns(assignments, ASSIGNMENT_REQUIRED_COLUMNS, "分组日志")
    _require_columns(executions, EXECUTION_REQUIRED_COLUMNS, "执行日志")
    _require_columns(outcomes, OUTCOME_REQUIRED_COLUMNS, "结果日志")
    if registry.empty:
        raise ValueError("实验登记表不能为空")
    _require_unique(registry, ["experiment_id"], "实验登记表")
    if not set(registry["status"]).issubset(ALLOWED_EXPERIMENT_STATUS):
        raise ValueError("实验登记表存在非法 status")
    alpha_values = pd.to_numeric(registry["alpha"], errors="coerce")
    power_values = pd.to_numeric(registry["power"], errors="coerce")
    if alpha_values.isna().any() or (alpha_values <= 0).any() or (alpha_values >= 1).any():
        raise ValueError("实验登记表 alpha 必须在 (0, 1)")
    if power_values.isna().any() or (power_values <= 0).any() or (power_values >= 1).any():
        raise ValueError("实验登记表 power 必须在 (0, 1)")
    if not registry["assignment_unit"].eq("seller_id").all():
        raise ValueError("当前实验框架的 assignment_unit 必须是 seller_id")
    planned_start = _parse_required_time(registry, "planned_start_date", "实验登记表")
    planned_end = _parse_required_time(registry, "planned_end_date", "实验登记表")
    if (planned_end < planned_start).any():
        raise ValueError("实验计划结束时间不能早于开始时间")

    if not assignments.empty:
        _require_unique(assignments, ["assignment_id"], "分组日志")
        _require_unique(assignments, ["experiment_id", "seller_id"], "分组日志")
        if not set(assignments["assigned_group"]).issubset(ALLOWED_GROUPS):
            raise ValueError("分组日志存在非法 assigned_group")
        if not set(assignments["experiment_id"]).issubset(set(registry["experiment_id"])):
            raise ValueError("分组日志存在未登记 experiment_id")
        assignment_time = _parse_required_time(assignments, "assignment_timestamp", "分组日志")
        snapshot_time = _parse_required_time(assignments, "eligibility_snapshot_date", "分组日志")
        if (assignment_time < snapshot_time).any():
            raise ValueError("分组时间不能早于资格快照时间")
    else:
        assignment_time = pd.Series(dtype="datetime64[ns, UTC]")

    assignment_lookup = assignments.set_index("assignment_id") if not assignments.empty else assignments
    if not executions.empty:
        _require_unique(executions, ["execution_id"], "执行日志")
        if not set(executions["assignment_id"]).issubset(set(assignments["assignment_id"])):
            raise ValueError("执行日志存在无法连接的 assignment_id")
        execution_time = _parse_required_time(executions, "execution_timestamp", "执行日志")
        linked = executions.join(
            assignment_lookup[["experiment_id", "seller_id", "assigned_group", "assignment_timestamp"]],
            on="assignment_id",
            rsuffix="_assignment",
        )
        for column in ["experiment_id", "seller_id", "assigned_group"]:
            if not linked[column].astype(str).eq(linked[f"{column}_assignment"].astype(str)).all():
                raise ValueError(f"执行日志的 {column} 与分组日志不一致")
        linked_assignment_time = pd.to_datetime(linked["assignment_timestamp"], utc=True)
        if (execution_time.reset_index(drop=True) < linked_assignment_time.reset_index(drop=True)).any():
            raise ValueError("执行时间不能早于分组时间")
        costs = pd.to_numeric(executions["cost_amount"], errors="coerce")
        if costs.isna().any() or (costs < 0).any():
            raise ValueError("执行成本必须是非负数")
        missing_currency = executions["cost_currency"].isna() | executions[
            "cost_currency"
        ].astype(str).str.strip().eq("")
        if ((costs > 0) & missing_currency).any():
            raise ValueError("非零执行成本必须填写币种")

    if not outcomes.empty:
        _require_unique(outcomes, ["outcome_id"], "结果日志")
        _require_unique(
            outcomes,
            ["assignment_id", "outcome_window_start", "outcome_window_end"],
            "结果日志观察窗",
        )
        if not set(outcomes["assignment_id"]).issubset(set(assignments["assignment_id"])):
            raise ValueError("结果日志存在无法连接的 assignment_id")
        start = _parse_required_time(outcomes, "outcome_window_start", "结果日志")
        end = _parse_required_time(outcomes, "outcome_window_end", "结果日志")
        observed = _parse_required_time(outcomes, "observed_at", "结果日志")
        if (end < start).any() or (observed < end).any():
            raise ValueError("结果窗口或观察时间顺序非法")
        linked = outcomes.join(
            assignment_lookup[["experiment_id", "seller_id", "assignment_timestamp"]],
            on="assignment_id",
            rsuffix="_assignment",
        )
        for column in ["experiment_id", "seller_id"]:
            if not linked[column].astype(str).eq(linked[f"{column}_assignment"].astype(str)).all():
                raise ValueError(f"结果日志的 {column} 与分组日志不一致")
        linked_assignment_time = pd.to_datetime(linked["assignment_timestamp"], utc=True)
        if (start.reset_index(drop=True) < linked_assignment_time.reset_index(drop=True)).any():
            raise ValueError("结果窗口不能早于分组时间")
        numeric_columns = [
            "orders_count",
            "delivered_orders_count",
            "late_orders_count",
            "reviewed_orders_count",
            "low_review_orders_count",
            "gmv",
            "cancelled_orders",
            "refund_amount",
        ]
        numeric = outcomes[numeric_columns].apply(pd.to_numeric, errors="coerce")
        if numeric.isna().any().any() or (numeric < 0).any().any():
            raise ValueError("结果日志的计数和金额必须是非负数")
        count_columns = [column for column in numeric_columns if column.endswith("_count")]
        if not numeric[count_columns].apply(lambda column: column.mod(1).eq(0)).all().all():
            raise ValueError("结果日志的订单计数必须是整数")
        if (numeric["delivered_orders_count"] > numeric["orders_count"]).any():
            raise ValueError("已交付订单数不能超过订单数")
        if (numeric["late_orders_count"] > numeric["delivered_orders_count"]).any():
            raise ValueError("延迟订单数不能超过已交付订单数")
        if (numeric["reviewed_orders_count"] > numeric["orders_count"]).any():
            raise ValueError("评价订单数不能超过订单数")
        if (numeric["low_review_orders_count"] > numeric["reviewed_orders_count"]).any():
            raise ValueError("低评分订单数不能超过评价订单数")
        if (numeric["cancelled_orders"] > numeric["orders_count"]).any():
            raise ValueError("取消订单数不能超过订单数")

    return {
        "experiment_count": int(len(registry)),
        "assignment_count": int(len(assignments)),
        "execution_count": int(len(executions)),
        "outcome_count": int(len(outcomes)),
    }
