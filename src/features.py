"""模型特征契约与时间安全的需求滞后特征。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.validation import (
    LEAD_FORBIDDEN_FEATURES,
    REVIEW_RISK_FORBIDDEN_FEATURES,
    assert_no_forbidden_features,
)


LEAD_CATEGORICAL_FEATURES = ["origin", "landing_page_id"]
LEAD_NUMERIC_FEATURES = ["is_origin_missing", "contact_year", "contact_month", "contact_day_of_week"]
LEAD_LABEL = "is_won"
LEAD_TIME = "prediction_at"

REVIEW_CATEGORICAL_FEATURES = [
    "primary_category_name",
    "seller_state",
    "customer_state",
    "payment_types",
]
REVIEW_NUMERIC_FEATURES = [
    "seller_count",
    "is_multi_seller",
    "item_count",
    "product_count",
    "item_value",
    "freight_value",
    "gross_value",
    "average_item_value",
    "freight_ratio",
    "total_product_weight_g",
    "total_product_volume_cm3",
    "average_product_description_length",
    "max_product_photos_qty",
    "promised_delivery_days",
    "max_payment_installments",
    "purchase_month",
    "purchase_day_of_week",
    "purchase_hour",
    "is_cross_state",
    "is_delivery_history_cold_start",
    "is_review_history_cold_start",
    "seller_historical_delivered_count",
    "seller_historical_delay_rate",
    "seller_historical_reviewed_count",
    "seller_historical_low_review_rate",
    "seller_historical_average_review",
    "global_historical_delay_rate",
    "global_historical_low_review_rate",
    "seller_smoothed_delay_rate",
    "seller_smoothed_low_review_rate",
]
REVIEW_LABEL = "is_low_review"
REVIEW_TIME = "prediction_at"


def validate_feature_contract(
    frame: pd.DataFrame,
    categorical: list[str],
    numeric: list[str],
    label: str,
    event_time: str,
    forbidden: frozenset[str],
    model_name: str,
) -> None:
    required = set(categorical + numeric + [label, event_time])
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"{model_name} 缺少字段: {', '.join(missing)}")
    assert_no_forbidden_features(categorical + numeric, forbidden, model_name)


def validate_lead_features(frame: pd.DataFrame) -> None:
    validate_feature_contract(
        frame,
        LEAD_CATEGORICAL_FEATURES,
        LEAD_NUMERIC_FEATURES,
        LEAD_LABEL,
        LEAD_TIME,
        LEAD_FORBIDDEN_FEATURES,
        "线索成交模型",
    )


def validate_review_features(frame: pd.DataFrame) -> None:
    validate_feature_contract(
        frame,
        REVIEW_CATEGORICAL_FEATURES,
        REVIEW_NUMERIC_FEATURES,
        REVIEW_LABEL,
        REVIEW_TIME,
        REVIEW_RISK_FORBIDDEN_FEATURES,
        "低评分风险模型",
    )


def complete_weekly_series(
    frame: pd.DataFrame,
    entity_column: str,
    time_column: str = "week_start",
    target_column: str = "order_count",
) -> pd.DataFrame:
    """按实体补齐从首次出现到全局数据截点的周，缺失需求填 0。"""

    required = {entity_column, time_column, target_column}
    if not required.issubset(frame.columns):
        raise ValueError(f"周序列缺少字段: {sorted(required.difference(frame.columns))}")
    data = frame[[entity_column, time_column, target_column]].copy()
    data[time_column] = pd.to_datetime(data[time_column])
    data = data.groupby([entity_column, time_column], as_index=False)[target_column].sum()
    global_end = data[time_column].max()
    pieces = []
    for entity, group in data.groupby(entity_column):
        weeks = pd.date_range(group[time_column].min(), global_end, freq="7D")
        completed = group.set_index(time_column).reindex(weeks)
        completed.index.name = time_column
        completed[entity_column] = entity
        completed[target_column] = completed[target_column].fillna(0.0)
        pieces.append(completed.reset_index())
    if not pieces:
        return data
    return pd.concat(pieces, ignore_index=True).sort_values([entity_column, time_column])


def add_demand_lag_features(
    frame: pd.DataFrame,
    entity_column: str,
    target_column: str = "order_count",
) -> pd.DataFrame:
    """所有滚动特征先 shift(1)，当前周和未来周不会进入特征。"""

    result = frame.sort_values([entity_column, "week_start"]).copy()
    grouped = result.groupby(entity_column, sort=False)[target_column]
    for lag in (1, 2, 4, 8, 13, 52):
        result[f"lag_{lag}"] = grouped.shift(lag)
    shifted = grouped.shift(1)
    for window in (4, 8, 13):
        result[f"rolling_mean_{window}"] = shifted.groupby(result[entity_column]).transform(
            lambda values: values.rolling(window, min_periods=1).mean()
        )
        result[f"rolling_std_{window}"] = shifted.groupby(result[entity_column]).transform(
            lambda values: values.rolling(window, min_periods=2).std()
        )
    active = result[target_column].gt(0).astype(int)
    shifted_active = active.groupby(result[entity_column], sort=False).shift(1)
    for window in (4, 8, 13):
        result[f"active_weeks_last_{window}"] = shifted_active.groupby(
            result[entity_column], sort=False
        ).transform(lambda values: values.rolling(window, min_periods=1).sum())

    def weeks_since_prior_order(values: pd.Series) -> pd.Series:
        prior_active = values.shift(1).gt(0).to_numpy()
        positions = np.arange(len(values), dtype=float)
        last_active = pd.Series(
            np.where(prior_active, positions - 1.0, np.nan), index=values.index
        ).ffill()
        return pd.Series(positions, index=values.index) - last_active

    result["weeks_since_last_order"] = grouped.transform(weeks_since_prior_order)
    result["week_of_year"] = pd.to_datetime(result["week_start"]).dt.isocalendar().week.astype(int)
    return result
