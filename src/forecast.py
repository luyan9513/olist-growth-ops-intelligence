"""商家/品类周度需求滚动回测。"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass

if not os.environ.get("LOKY_MAX_CPU_COUNT"):
    os.environ["LOKY_MAX_CPU_COUNT"] = "1"

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import average_precision_score, brier_score_loss

from src.evaluate import forecast_metrics
from src.features import add_demand_lag_features, complete_weekly_series


@dataclass
class ForecastBacktest:
    metrics: dict[str, dict[str, float]]
    predictions: pd.DataFrame
    data_end_week: pd.Timestamp
    occurrence_metrics: dict[str, dict[str, float]] | None = None
    weekly_metrics: list[dict[str, object]] | None = None
    weekly_occurrence_metrics: list[dict[str, object]] | None = None
    segment_metrics: list[dict[str, object]] | None = None


BASE_FEATURE_COLUMNS = [
    "lag_1",
    "lag_2",
    "lag_4",
    "lag_8",
    "lag_13",
    "lag_52",
    "rolling_mean_4",
    "rolling_std_4",
    "rolling_mean_8",
    "rolling_std_8",
    "rolling_mean_13",
    "rolling_std_13",
    "week_of_year",
]

INTERMITTENT_FEATURE_COLUMNS = BASE_FEATURE_COLUMNS + [
    "active_weeks_last_4",
    "active_weeks_last_8",
    "active_weeks_last_13",
    "weeks_since_last_order",
]


def croston_sba_fitted(values: pd.Series | np.ndarray, alpha: float = 0.1) -> np.ndarray:
    """返回每个时点的 Croston-SBA 单步预测；当前值只在预测生成后更新状态。"""

    if not 0 < alpha <= 1:
        raise ValueError("alpha 必须位于 (0, 1]")
    demand = np.asarray(values, dtype=float)
    forecasts = np.zeros(len(demand), dtype=float)
    demand_level: float | None = None
    interval_level: float | None = None
    last_nonzero_position: int | None = None
    for position, current in enumerate(demand):
        if demand_level is not None and interval_level is not None and interval_level > 0:
            forecasts[position] = (1.0 - alpha / 2.0) * demand_level / interval_level
        if current <= 0:
            continue
        if demand_level is None:
            demand_level = float(current)
            interval_level = float(position + 1)
        else:
            assert interval_level is not None and last_nonzero_position is not None
            interval = float(position - last_nonzero_position)
            demand_level = alpha * float(current) + (1.0 - alpha) * demand_level
            interval_level = alpha * interval + (1.0 - alpha) * interval_level
        last_nonzero_position = position
    return forecasts


def demand_activity_segment(active_weeks_last_13: pd.Series) -> pd.Series:
    """按预测时点前 13 周活跃次数划分固定活动层。"""

    values = active_weeks_last_13.fillna(0.0)
    return pd.Series(
        np.select(
            [values >= 7, values >= 2],
            ["持续活跃", "间歇活跃"],
            default="长尾/沉默",
        ),
        index=values.index,
    )


def _direct_regressor(random_seed: int) -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(
        loss="poisson", max_iter=200, learning_rate=0.05, random_state=random_seed
    )


def _activity_classifier(random_seed: int) -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(
        loss="log_loss",
        max_iter=150,
        learning_rate=0.05,
        max_leaf_nodes=15,
        min_samples_leaf=30,
        l2_regularization=0.1,
        random_state=random_seed,
    )


def _conditional_regressor(random_seed: int) -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(
        loss="poisson",
        max_iter=150,
        learning_rate=0.05,
        max_leaf_nodes=15,
        min_samples_leaf=20,
        l2_regularization=0.1,
        random_state=random_seed,
    )


def _occurrence_metrics(actual: pd.Series, probability: pd.Series) -> dict[str, float]:
    labels = actual.astype(int)
    result = {
        "sample_count": float(len(labels)),
        "positive_count": float(labels.sum()),
        "positive_rate": float(labels.mean()),
        "brier_score": float(brier_score_loss(labels, probability)),
    }
    result["pr_auc"] = (
        float(average_precision_score(labels, probability)) if labels.nunique() > 1 else math.nan
    )
    return result


def build_demand_segments(
    frame: pd.DataFrame,
    entity_column: str,
    weeks_per_window: int = 13,
) -> pd.DataFrame:
    """基于完整历史周构建资源规划分层，不将尾部截断周当作需求下滑。"""

    required = {entity_column, "week_start", "order_count", "gross_value"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"需求分层缺少字段: {sorted(missing)}")
    data = trim_trailing_incomplete_weeks(frame, "order_count")
    data["week_start"] = pd.to_datetime(data["week_start"])
    cutoff = data["week_start"].max()
    latest_start = cutoff - pd.Timedelta(weeks=weeks_per_window - 1)
    prior_start = latest_start - pd.Timedelta(weeks=weeks_per_window)
    entity_week = data.groupby([entity_column, "week_start"], as_index=False).agg(
        order_count=("order_count", "sum"), gross_value=("gross_value", "sum")
    )
    rows: list[dict[str, object]] = []
    for entity, group in entity_week.groupby(entity_column):
        latest = group[group["week_start"].between(latest_start, cutoff)]
        prior = group[(group["week_start"] >= prior_start) & (group["week_start"] < latest_start)]
        weekly_orders = latest.set_index("week_start")["order_count"].reindex(
            pd.date_range(latest_start, cutoff, freq="7D"), fill_value=0.0
        )
        latest_orders = float(latest["order_count"].sum())
        prior_orders = float(prior["order_count"].sum())
        rows.append(
            {
                entity_column: entity,
                "cutoff_week": cutoff,
                "latest_13w_orders": latest_orders,
                "prior_13w_orders": prior_orders,
                "growth_rate": (latest_orders - prior_orders) / prior_orders
                if prior_orders > 0
                else np.nan,
                "latest_13w_gmv": float(latest["gross_value"].sum()),
                "average_weekly_orders": float(weekly_orders.mean()),
                "weekly_order_cv": float(weekly_orders.std(ddof=0) / weekly_orders.mean())
                if weekly_orders.mean() > 0
                else np.nan,
            }
        )
    result = pd.DataFrame(rows)
    result["value_percentile"] = result["latest_13w_gmv"].rank(pct=True, method="average")
    result["volatility_percentile"] = result["weekly_order_cv"].rank(
        pct=True, method="average", na_option="bottom"
    )
    high_value = result["value_percentile"] >= 0.75
    high_growth = result["growth_rate"] >= 0.10
    high_volatility = result["volatility_percentile"] >= 0.75
    result["resource_segment"] = np.select(
        [high_value & high_growth, high_value & high_volatility, result["value_percentile"] <= 0.25],
        ["高价值高增长", "高价值高波动", "低价值长尾"],
        default="稳定运营",
    )
    return result.sort_values(["resource_segment", "latest_13w_gmv"], ascending=[True, False])


def trim_trailing_incomplete_weeks(
    frame: pd.DataFrame,
    target_column: str = "order_count",
    lookback: int = 8,
    minimum_ratio: float = 0.25,
) -> pd.DataFrame:
    """移除相对前期异常稀疏的尾部周，避免数据截断冒充需求骤降。"""

    result = frame.copy()
    while result["week_start"].nunique() > lookback + 1:
        weekly = result.groupby("week_start")[target_column].sum().sort_index()
        previous = weekly.iloc[-(lookback + 1) : -1]
        reference = float(previous.median())
        if reference <= 0 or float(weekly.iloc[-1]) >= reference * minimum_ratio:
            break
        result = result[result["week_start"] < weekly.index[-1]].copy()
    return result


def rolling_backtest(
    frame: pd.DataFrame,
    entity_column: str = "primary_category_name",
    target_column: str = "order_count",
    test_weeks: int = 8,
    random_seed: int = 42,
    intermittent: bool = False,
) -> ForecastBacktest:
    source = frame.copy()
    source["week_start"] = pd.to_datetime(source["week_start"])
    source = trim_trailing_incomplete_weeks(source, target_column)
    completed = complete_weekly_series(source, entity_column, target_column=target_column)
    featured = add_demand_lag_features(completed, entity_column, target_column)
    if intermittent:
        featured["croston_sba"] = featured.groupby(entity_column, sort=False)[
            target_column
        ].transform(croston_sba_fitted)
    weeks = pd.Index(featured["week_start"].unique()).sort_values()
    if len(weeks) < test_weeks + 8:
        raise ValueError("周度需求回测至少需要 test_weeks + 8 个不同周")
    evaluation_weeks = weeks[-test_weeks:]
    feature_columns = INTERMITTENT_FEATURE_COLUMNS if intermittent else BASE_FEATURE_COLUMNS
    prediction_rows = []
    for week in evaluation_weeks:
        train = featured[featured["week_start"] < week].dropna(subset=["lag_1"])
        test = featured[featured["week_start"] == week].copy()
        if train.empty or test.empty:
            continue
        medians = train[feature_columns].median(numeric_only=True).fillna(0.0)
        x_train = train[feature_columns].fillna(medians)
        x_test = test[feature_columns].fillna(medians)
        tree = _direct_regressor(random_seed)
        tree.fit(x_train, train[target_column])
        seasonal = test["lag_52"].where(test["lag_52"].notna(), test["lag_4"])
        seasonal = seasonal.where(seasonal.notna(), test["lag_1"]).fillna(0.0)
        moving_average = test["rolling_mean_4"].fillna(test["lag_1"]).fillna(0.0)
        tree_prediction = np.maximum(0.0, tree.predict(x_test))
        if intermittent:
            active_train = train[target_column].gt(0).astype(int)
            if active_train.nunique() < 2:
                raise ValueError(f"{week.date()} 之前的活动标签缺少正类或负类")
            classifier = _activity_classifier(random_seed)
            classifier.fit(x_train, active_train)
            activity_probability = classifier.predict_proba(x_test)[:, 1]
            positive_train = train[train[target_column] > 0]
            conditional_medians = positive_train[feature_columns].median(numeric_only=True).fillna(0.0)
            conditional = _conditional_regressor(random_seed)
            conditional.fit(
                positive_train[feature_columns].fillna(conditional_medians),
                positive_train[target_column],
            )
            conditional_prediction = np.maximum(
                0.0, conditional.predict(test[feature_columns].fillna(conditional_medians))
            )
            expected_prediction = activity_probability * conditional_prediction
            baseline_probability = float(active_train.mean())
            activity_segments = demand_activity_segment(test["active_weeks_last_13"])

        for position, (index, row) in enumerate(test.iterrows()):
            result_row = {
                entity_column: row[entity_column],
                "week_start": row["week_start"],
                "actual": float(row[target_column]),
                "seasonal_naive": float(seasonal.loc[index]),
                "moving_average_4": float(moving_average.loc[index]),
                "hist_gradient_boosting": float(tree_prediction[position]),
            }
            if intermittent:
                result_row.update(
                    {
                        "croston_sba": float(row["croston_sba"]),
                        "activity_actual": int(row[target_column] > 0),
                        "activity_probability_baseline": baseline_probability,
                        "activity_probability": float(activity_probability[position]),
                        "conditional_order_count": float(conditional_prediction[position]),
                        "two_stage_expected": float(expected_prediction[position]),
                        "activity_segment": str(activity_segments.loc[index]),
                    }
                )
            prediction_rows.append(result_row)
    predictions = pd.DataFrame(prediction_rows)
    if predictions.empty:
        raise ValueError("滚动回测未产生预测，请检查时间覆盖与实体序列")
    model_columns = ["seasonal_naive", "moving_average_4", "hist_gradient_boosting"]
    if intermittent:
        model_columns.extend(["croston_sba", "two_stage_expected"])
    metrics = {
        model: forecast_metrics(predictions["actual"], predictions[model])
        for model in model_columns
    }
    if any(math.isnan(values["wape"]) for values in metrics.values()):
        raise ValueError("回测真实需求总和为 0，WAPE 无法计算")
    occurrence_metrics = None
    weekly_metrics = None
    weekly_occurrence_metrics = None
    segment_metrics = None
    if intermittent:
        occurrence_metrics = {
            "prevalence_baseline": _occurrence_metrics(
                predictions["activity_actual"], predictions["activity_probability_baseline"]
            ),
            "two_stage_classifier": _occurrence_metrics(
                predictions["activity_actual"], predictions["activity_probability"]
            ),
        }
        weekly_metrics = []
        weekly_occurrence_metrics = []
        for week, group in predictions.groupby("week_start", sort=True):
            for model in model_columns:
                weekly_metrics.append(
                    {
                        "week_start": pd.Timestamp(week).isoformat(),
                        "model": model,
                        **forecast_metrics(group["actual"], group[model]),
                    }
                )
            for model, probability_column in {
                "prevalence_baseline": "activity_probability_baseline",
                "two_stage_classifier": "activity_probability",
            }.items():
                weekly_occurrence_metrics.append(
                    {
                        "week_start": pd.Timestamp(week).isoformat(),
                        "model": model,
                        **_occurrence_metrics(
                            group["activity_actual"], group[probability_column]
                        ),
                    }
                )
        segment_metrics = []
        for segment, group in predictions.groupby("activity_segment", sort=False):
            occurrence = _occurrence_metrics(group["activity_actual"], group["activity_probability"])
            for model in model_columns:
                segment_metrics.append(
                    {
                        "activity_segment": str(segment),
                        "model": model,
                        "sample_count": int(len(group)),
                        "actual_orders": float(group["actual"].sum()),
                        "activity_rate": float(group["activity_actual"].mean()),
                        "occurrence_pr_auc": occurrence["pr_auc"],
                        "occurrence_brier_score": occurrence["brier_score"],
                        **forecast_metrics(group["actual"], group[model]),
                    }
                )
    return ForecastBacktest(
        metrics=metrics,
        predictions=predictions,
        data_end_week=pd.Timestamp(weeks[-1]),
        occurrence_metrics=occurrence_metrics,
        weekly_metrics=weekly_metrics,
        weekly_occurrence_metrics=weekly_occurrence_metrics,
        segment_metrics=segment_metrics,
    )


def next_week_intermittent_forecast(
    frame: pd.DataFrame,
    entity_column: str = "seller_id",
    target_column: str = "order_count",
    random_seed: int = 42,
) -> pd.DataFrame:
    """使用完整可用历史生成下一完整周的活动概率与期望订单量。"""

    source = frame.copy()
    source["week_start"] = pd.to_datetime(source["week_start"])
    source = trim_trailing_incomplete_weeks(source, target_column)
    completed = complete_weekly_series(source, entity_column, target_column=target_column)
    cutoff = pd.Timestamp(completed["week_start"].max())
    forecast_week = cutoff + pd.Timedelta(weeks=1)
    future = pd.DataFrame(
        {
            entity_column: completed[entity_column].drop_duplicates().to_numpy(),
            "week_start": forecast_week,
            target_column: 0.0,
        }
    )
    combined = pd.concat([completed, future], ignore_index=True)
    featured = add_demand_lag_features(combined, entity_column, target_column)
    train = featured[featured["week_start"] <= cutoff].dropna(subset=["lag_1"])
    scoring = featured[featured["week_start"] == forecast_week].copy()
    medians = train[INTERMITTENT_FEATURE_COLUMNS].median(numeric_only=True).fillna(0.0)
    x_train = train[INTERMITTENT_FEATURE_COLUMNS].fillna(medians)
    x_scoring = scoring[INTERMITTENT_FEATURE_COLUMNS].fillna(medians)
    classifier = _activity_classifier(random_seed)
    classifier.fit(x_train, train[target_column].gt(0).astype(int))
    positive_train = train[train[target_column] > 0]
    conditional_medians = positive_train[INTERMITTENT_FEATURE_COLUMNS].median(
        numeric_only=True
    ).fillna(0.0)
    conditional = _conditional_regressor(random_seed)
    conditional.fit(
        positive_train[INTERMITTENT_FEATURE_COLUMNS].fillna(conditional_medians),
        positive_train[target_column],
    )
    probability = classifier.predict_proba(x_scoring)[:, 1]
    conditional_orders = np.maximum(
        0.0,
        conditional.predict(
            scoring[INTERMITTENT_FEATURE_COLUMNS].fillna(conditional_medians)
        ),
    )
    return pd.DataFrame(
        {
            entity_column: scoring[entity_column].to_numpy(),
            "forecast_week": forecast_week,
            "activity_probability": probability,
            "conditional_order_count": conditional_orders,
            "expected_order_count": probability * conditional_orders,
            "activity_segment": demand_activity_segment(
                scoring["active_weeks_last_13"]
            ).to_numpy(),
            "active_weeks_last_13": scoring["active_weeks_last_13"].fillna(0.0).to_numpy(),
            "weeks_since_last_order": scoring["weeks_since_last_order"].to_numpy(),
        }
    ).sort_values(["activity_probability", "expected_order_count"], ascending=False)
