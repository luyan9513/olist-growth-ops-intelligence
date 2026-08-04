"""训练线索成交、低评分风险和需求预测模型。"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

if not os.environ.get("LOKY_MAX_CPU_COUNT"):
    os.environ["LOKY_MAX_CPU_COUNT"] = "1"

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.data_access import DEFAULT_DATABASE, read_table
from src.decisioning import (
    build_seller_ops_actions,
    seller_ops_capacity_comparison,
    seller_ops_capacity_scenario,
)
from src.evaluate import (
    bootstrap_classification_intervals,
    classification_metrics,
    subgroup_classification_metrics,
    write_json,
)
from src.features import (
    LEAD_CATEGORICAL_FEATURES,
    LEAD_LABEL,
    LEAD_NUMERIC_FEATURES,
    LEAD_TIME,
    REVIEW_CATEGORICAL_FEATURES,
    REVIEW_LABEL,
    REVIEW_NUMERIC_FEATURES,
    REVIEW_TIME,
    validate_lead_features,
    validate_review_features,
)
from src.forecast import (
    build_demand_segments,
    next_week_intermittent_forecast,
    rolling_backtest,
)
from src.validation import expanding_time_windows, temporal_calibration_split, temporal_split


RANDOM_SEED = 42


@dataclass(frozen=True)
class ClassificationSpec:
    name: str
    id_columns: list[str]
    categorical_features: list[str]
    numeric_features: list[str]
    label: str
    event_time: str
    subgroup_columns: list[str]


def build_preprocessor(categorical: list[str], numeric: list[str]) -> ColumnTransformer:
    numeric_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scale", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "one_hot",
                OneHotEncoder(handle_unknown="ignore", min_frequency=2, sparse_output=True),
            ),
        ]
    )
    return ColumnTransformer(
        [("numeric", numeric_pipeline, numeric), ("categorical", categorical_pipeline, categorical)]
    )


def classifier_candidates(spec: ClassificationSpec) -> dict[str, Pipeline]:
    return {
        "prevalence_baseline": Pipeline([("model", DummyClassifier(strategy="prior"))]),
        "logistic_regression": Pipeline(
            [
                ("preprocess", build_preprocessor(spec.categorical_features, spec.numeric_features)),
                (
                    "model",
                    LogisticRegression(
                        max_iter=2000, class_weight="balanced", random_state=RANDOM_SEED
                    ),
                ),
            ]
        ),
        "random_forest": Pipeline(
            [
                ("preprocess", build_preprocessor(spec.categorical_features, spec.numeric_features)),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=300,
                        min_samples_leaf=5,
                        class_weight="balanced_subsample",
                        n_jobs=1,
                        random_state=RANDOM_SEED,
                    ),
                ),
            ]
        ),
    }


def feature_importance(pipeline: Pipeline, limit: int = 30) -> list[dict[str, object]]:
    if "preprocess" not in pipeline.named_steps:
        return []
    preprocess = pipeline.named_steps["preprocess"]
    model = pipeline.named_steps["model"]
    if not hasattr(preprocess, "get_feature_names_out"):
        return []
    names = preprocess.get_feature_names_out()
    if hasattr(model, "coef_"):
        values = model.coef_[0]
        ranking = np.argsort(np.abs(values))[::-1][:limit]
        return [
            {"feature": str(names[index]), "importance": float(values[index])}
            for index in ranking
        ]
    if hasattr(model, "feature_importances_"):
        values = model.feature_importances_
        ranking = np.argsort(values)[::-1][:limit]
        return [
            {"feature": str(names[index]), "importance": float(values[index])}
            for index in ranking
        ]
    return []


def rolling_classification_backtest(
    data: pd.DataFrame,
    spec: ClassificationSpec,
    selected_name: str,
    *,
    n_windows: int = 3,
) -> dict[str, object]:
    """使用扩展训练窗评估先验、逻辑回归和选中模型的跨时间稳定性。"""

    feature_columns = spec.categorical_features + spec.numeric_features
    windows = expanding_time_windows(data[spec.event_time], n_windows=n_windows)
    model_names = list(classifier_candidates(spec))
    records: list[dict[str, object]] = []
    for window_number, window in enumerate(windows, start=1):
        train = data.loc[window.train_index]
        evaluation = data.loc[window.evaluation_index]
        if train[spec.label].nunique() < 2 or evaluation[spec.label].nunique() < 2:
            raise ValueError(f"{spec.name} 滚动窗口 {window_number} 缺少正类或负类")
        candidates = classifier_candidates(spec)
        for model_name in model_names:
            candidate = candidates[model_name]
            candidate.fit(train[feature_columns], train[spec.label])
            scores = candidate.predict_proba(evaluation[feature_columns])[:, 1]
            metrics = classification_metrics(evaluation[spec.label], scores)
            top_k = metrics["top_k"]
            assert isinstance(top_k, dict)
            records.append(
                {
                    "window": window_number,
                    "model": model_name,
                    "train_count": int(len(train)),
                    "evaluation_count": int(len(evaluation)),
                    "train_end": window.train_end.isoformat(),
                    "evaluation_start": window.evaluation_start.isoformat(),
                    "evaluation_end": window.evaluation_end.isoformat(),
                    "positive_rate": metrics["positive_rate"],
                    "pr_auc": metrics["pr_auc"],
                    "brier_score": metrics["brier_score"],
                    "top_10pct_lift": top_k["10pct"]["lift"],
                    "top_20pct_lift": top_k["20pct"]["lift"],
                }
            )

    summary: dict[str, object] = {}
    record_frame = pd.DataFrame(records)
    metric_columns = ["pr_auc", "brier_score", "top_10pct_lift", "top_20pct_lift"]
    for model_name, group in record_frame.groupby("model", sort=False):
        summary[str(model_name)] = {
            metric: {
                "mean": float(group[metric].mean()),
                "std": float(group[metric].std(ddof=0)),
                "minimum": float(group[metric].min()),
                "maximum": float(group[metric].max()),
            }
            for metric in metric_columns
        }
    logistic_rows = record_frame[record_frame["model"] == "logistic_regression"].set_index("window")

    def compare_with_logistic(model_name: str) -> dict[str, object]:
        model_rows = record_frame[record_frame["model"] == model_name].set_index("window")
        comparison = model_rows[["pr_auc", "top_20pct_lift"]].subtract(
            logistic_rows[["pr_auc", "top_20pct_lift"]]
        )
        return {
            "compared_model": model_name,
            "reference_model": "logistic_regression",
            "same_model": model_name == "logistic_regression",
            "pr_auc_wins": int((comparison["pr_auc"] > 0).sum()),
            "top_20pct_lift_wins": int((comparison["top_20pct_lift"] > 0).sum()),
            "evaluated_windows": int(len(comparison)),
        }

    return {
        "strategy": "expanding_window_last_40pct_dates",
        "window_count": n_windows,
        "records": records,
        "summary": summary,
        "selected_vs_logistic": compare_with_logistic(selected_name),
        "random_forest_vs_logistic": compare_with_logistic("random_forest"),
    }


def train_classification(
    frame: pd.DataFrame,
    spec: ClassificationSpec,
    output_dir: Path,
) -> dict[str, object]:
    data = frame.copy()
    data[spec.event_time] = pd.to_datetime(data[spec.event_time], errors="coerce")
    data = data.dropna(subset=[spec.event_time, spec.label]).sort_values(spec.event_time).reset_index(drop=True)
    data[spec.label] = data[spec.label].astype(int)
    split = temporal_split(data[spec.event_time])
    feature_columns = spec.categorical_features + spec.numeric_features

    train = data.loc[split.train_index]
    validation = data.loc[split.validation_index]
    test = data.loc[split.test_index]
    if min(train[spec.label].nunique(), validation[spec.label].nunique(), test[spec.label].nunique()) < 2:
        raise ValueError(f"{spec.name} 的训练/验证/测试集都必须同时包含正负样本")

    calibration_split = temporal_calibration_split(validation[spec.event_time])
    selection = validation.loc[calibration_split.selection_index]
    calibration = validation.loc[calibration_split.calibration_index]
    if min(selection[spec.label].nunique(), calibration[spec.label].nunique()) < 2:
        raise ValueError(f"{spec.name} 的选模期和校准期都必须同时包含正负样本")

    validation_scores: dict[str, float] = {}
    for name, candidate in classifier_candidates(spec).items():
        candidate.fit(train[feature_columns], train[spec.label])
        score = candidate.predict_proba(selection[feature_columns])[:, 1]
        validation_scores[name] = float(average_precision_score(selection[spec.label], score))
    selectable = {name: value for name, value in validation_scores.items() if name != "prevalence_baseline"}
    selected_name = max(selectable, key=selectable.get)

    train_validation = pd.concat([train, validation]).sort_values(spec.event_time)
    test_results: dict[str, object] = {}
    predictions = test[spec.id_columns + [spec.event_time, spec.label] + spec.subgroup_columns].copy()
    fitted_models: dict[str, Pipeline] = {}
    for name, candidate in classifier_candidates(spec).items():
        candidate.fit(train_validation[feature_columns], train_validation[spec.label])
        scores = candidate.predict_proba(test[feature_columns])[:, 1]
        predictions[f"score_{name}"] = scores
        test_results[name] = classification_metrics(test[spec.label], scores)
        fitted_models[name] = candidate

    train_selection = pd.concat([train, selection]).sort_values(spec.event_time)
    calibration_base = classifier_candidates(spec)[selected_name]
    calibration_base.fit(train_selection[feature_columns], train_selection[spec.label])
    uncalibrated_holdout_scores = calibration_base.predict_proba(test[feature_columns])[:, 1]
    calibrated_model = CalibratedClassifierCV(
        FrozenEstimator(calibration_base), method="sigmoid"
    )
    calibrated_model.fit(calibration[feature_columns], calibration[spec.label])
    calibrated_scores = calibrated_model.predict_proba(test[feature_columns])[:, 1]
    predictions["score_selected_uncalibrated_holdout"] = uncalibrated_holdout_scores
    predictions["score_selected_calibrated"] = calibrated_scores
    calibration_comparison = {
        "uncalibrated": classification_metrics(test[spec.label], uncalibrated_holdout_scores),
        "sigmoid_calibrated": classification_metrics(test[spec.label], calibrated_scores),
    }

    bootstrap_intervals = {
        name: bootstrap_classification_intervals(test[spec.label], predictions[f"score_{name}"])
        for name in fitted_models
    }
    bootstrap_intervals["selected_uncalibrated_holdout"] = bootstrap_classification_intervals(
        test[spec.label], uncalibrated_holdout_scores
    )
    bootstrap_intervals["selected_sigmoid_calibrated"] = bootstrap_classification_intervals(
        test[spec.label], calibrated_scores
    )
    rolling_backtest = rolling_classification_backtest(data, spec, selected_name)

    selected_score_column = f"score_{selected_name}"
    subgroup_results = {
        column: subgroup_classification_metrics(
            predictions, column, spec.label, selected_score_column
        )
        for column in spec.subgroup_columns
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions.sort_values(selected_score_column, ascending=False).to_csv(
        output_dir / "test_predictions.csv", index=False
    )
    joblib.dump(fitted_models[selected_name], output_dir / "selected_model.joblib")
    joblib.dump(calibrated_model, output_dir / "selected_calibrated_model.joblib")
    payload: dict[str, object] = {
        "model_name": spec.name,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "random_seed": RANDOM_SEED,
        "feature_columns": feature_columns,
        "selected_model": selected_name,
        "selection_metric": "selection_period_pr_auc",
        "validation_pr_auc": validation_scores,
        "time_split": {
            "train_end": split.train_end.isoformat(),
            "validation_end": split.validation_end.isoformat(),
            "train_count": int(len(train)),
            "validation_count": int(len(validation)),
            "test_count": int(len(test)),
            "selection_end": calibration_split.selection_end.isoformat(),
            "selection_count": int(len(selection)),
            "calibration_count": int(len(calibration)),
        },
        "test_metrics": test_results,
        "calibration": {
            "method": "sigmoid",
            "base_fit_count": int(len(train_selection)),
            "calibration_count": int(len(calibration)),
            "base_fit_end": calibration_split.selection_end.isoformat(),
            "calibration_start": calibration[spec.event_time].min().isoformat(),
            "calibration_end": calibration[spec.event_time].max().isoformat(),
            "test_start": test[spec.event_time].min().isoformat(),
            "comparison": calibration_comparison,
        },
        "bootstrap_intervals": bootstrap_intervals,
        "rolling_time_backtest": rolling_backtest,
        "subgroup_error_analysis": subgroup_results,
        "feature_importance": feature_importance(fitted_models[selected_name]),
        "limitations": [
            "离线排序表现不代表因果增量或线上效果",
            "阈值和 Top-K 需要结合真实运营容量重新确定",
        ],
    }
    write_json(payload, output_dir / "metrics.json")
    return payload


def train_leads(database: Path, artifacts: Path) -> dict[str, object]:
    frame = read_table("marts.mart_lead_features", database)
    validate_lead_features(frame)
    spec = ClassificationSpec(
        name="lead_conversion",
        id_columns=["mql_id"],
        categorical_features=LEAD_CATEGORICAL_FEATURES,
        numeric_features=LEAD_NUMERIC_FEATURES,
        label=LEAD_LABEL,
        event_time=LEAD_TIME,
        subgroup_columns=["origin"],
    )
    return train_classification(frame, spec, artifacts / "lead_conversion")


def train_review_risk(database: Path, artifacts: Path) -> dict[str, object]:
    frame = read_table("marts.mart_review_risk_features", database)
    validate_review_features(frame)
    spec = ClassificationSpec(
        name="review_risk",
        id_columns=["order_id", "primary_seller_id"],
        categorical_features=REVIEW_CATEGORICAL_FEATURES,
        numeric_features=REVIEW_NUMERIC_FEATURES,
        label=REVIEW_LABEL,
        event_time=REVIEW_TIME,
        subgroup_columns=["primary_category_name", "seller_state", "customer_state"],
    )
    return train_classification(frame, spec, artifacts / "review_risk")


def train_demand(database: Path, artifacts: Path) -> dict[str, object]:
    frame = read_table("marts.mart_demand_weekly", database)
    category = (
        frame.groupby(["primary_category_name", "week_start"], as_index=False)["order_count"]
        .sum()
        .sort_values("week_start")
    )
    seller = (
        frame.groupby(["seller_id", "week_start"], as_index=False)["order_count"]
        .sum()
        .sort_values("week_start")
    )
    category_backtest = rolling_backtest(category)
    seller_backtest = rolling_backtest(
        seller, entity_column="seller_id", intermittent=True
    )
    output_dir = artifacts / "demand_forecast"
    output_dir.mkdir(parents=True, exist_ok=True)
    category_backtest.predictions.to_csv(output_dir / "backtest_predictions.csv", index=False)
    seller_backtest.predictions.to_csv(output_dir / "seller_backtest_predictions.csv", index=False)
    category_segments = build_demand_segments(frame, "primary_category_name")
    seller_segments = build_demand_segments(frame, "seller_id")
    seller_activity_priority = next_week_intermittent_forecast(seller)
    seller_segments = seller_segments.merge(
        seller_activity_priority,
        on="seller_id",
        how="left",
        validate="one_to_one",
    )
    category_segments.to_csv(output_dir / "category_resource_plan.csv", index=False)
    seller_segments.to_csv(output_dir / "seller_resource_plan.csv", index=False)
    seller_activity_priority.to_csv(output_dir / "seller_activity_priority.csv", index=False)
    seller_risk = read_table("marts.mart_seller_risk", database)
    seller_ops = build_seller_ops_actions(seller_segments, seller_risk)
    seller_ops.actions.to_csv(output_dir / "seller_ops_action_list.csv", index=False)
    seller_ops_metadata = {
        **seller_ops.metadata,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "capacity_examples": {
            str(capacity): seller_ops_capacity_scenario(seller_ops.actions, capacity)
            for capacity in (50, 100, 200, 500)
        },
        "capacity_strategy_comparison": {
            str(capacity): seller_ops_capacity_comparison(seller_ops.actions, capacity)
            for capacity in (50, 100, 200, 500)
        },
    }
    write_json(seller_ops_metadata, output_dir / "seller_ops_metadata.json")
    pd.DataFrame(seller_backtest.weekly_metrics).to_csv(
        output_dir / "seller_weekly_metrics.csv", index=False
    )
    pd.DataFrame(seller_backtest.weekly_occurrence_metrics).to_csv(
        output_dir / "seller_weekly_occurrence_metrics.csv", index=False
    )
    pd.DataFrame(seller_backtest.segment_metrics).to_csv(
        output_dir / "seller_activity_segment_metrics.csv", index=False
    )
    selected_model = min(
        category_backtest.metrics, key=lambda name: category_backtest.metrics[name]["wape"]
    )
    seller_best_backtest_model = min(
        seller_backtest.metrics, key=lambda name: seller_backtest.metrics[name]["wape"]
    )
    weekly_frame = pd.DataFrame(seller_backtest.weekly_metrics)
    weekly_wape = weekly_frame.pivot(index="week_start", columns="model", values="wape")
    two_stage_noninferior_weeks = int(
        (weekly_wape["two_stage_expected"] <= weekly_wape["moving_average_4"]).sum()
    )
    occurrence_metrics = seller_backtest.occurrence_metrics or {}
    occurrence_pr_auc = float(occurrence_metrics["two_stage_classifier"]["pr_auc"])
    occurrence_baseline = float(occurrence_metrics["two_stage_classifier"]["positive_rate"])
    seller_acceptance = {
        "aggregate_wape_better_than_moving_average_4": bool(
            seller_backtest.metrics["two_stage_expected"]["wape"]
            < seller_backtest.metrics["moving_average_4"]["wape"]
        ),
        "two_stage_noninferior_weeks_vs_moving_average_4": two_stage_noninferior_weeks,
        "required_noninferior_weeks": 5,
        "occurrence_pr_auc_better_than_prevalence": bool(
            occurrence_pr_auc > occurrence_baseline
        ),
    }
    seller_acceptance["accepted_as_order_count_model"] = bool(
        seller_acceptance["aggregate_wape_better_than_moving_average_4"]
        and two_stage_noninferior_weeks >= 5
        and seller_acceptance["occurrence_pr_auc_better_than_prevalence"]
    )
    fallback_models = [
        "seasonal_naive",
        "moving_average_4",
        "hist_gradient_boosting",
        "croston_sba",
    ]
    seller_selected_model = (
        "two_stage_expected"
        if seller_acceptance["accepted_as_order_count_model"]
        else min(fallback_models, key=lambda name: seller_backtest.metrics[name]["wape"])
    )
    payload: dict[str, object] = {
        "model_name": "seller_and_category_weekly_demand",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "backtest": "expanding_window_last_8_weeks",
        "data_end_week": category_backtest.data_end_week.isoformat(),
        "metrics": category_backtest.metrics,
        "selected_model": selected_model,
        "seller_metrics": seller_backtest.metrics,
        "seller_selected_model": seller_selected_model,
        "seller_best_backtest_model": seller_best_backtest_model,
        "seller_occurrence_metrics": seller_backtest.occurrence_metrics,
        "seller_weekly_metrics": seller_backtest.weekly_metrics,
        "seller_weekly_occurrence_metrics": seller_backtest.weekly_occurrence_metrics,
        "seller_activity_segment_metrics": seller_backtest.segment_metrics,
        "seller_model_acceptance": seller_acceptance,
        "seller_delivery_mode": (
            "two_stage_order_count_and_activity"
            if seller_acceptance["accepted_as_order_count_model"]
            else "activity_probability_with_order_count_baseline"
        ),
        "seller_ops": seller_ops_metadata,
        "selection_metric": "wape",
        "limitations": [
            "公开样本不是完整市场需求",
            "商家序列稀疏，预测仅用于运营资源排序",
            "商家两阶段模型必须同时通过聚合、逐周和活动排序门槛，否则订单量采用基线",
            "品类预测不用于 SKU 补货",
        ],
    }
    write_json(payload, output_dir / "metrics.json")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=["lead", "review", "demand", "all"])
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    args = parser.parse_args()
    results: dict[str, object] = {}
    if args.task in {"lead", "all"}:
        results["lead"] = train_leads(args.database, args.artifacts)
    if args.task in {"review", "all"}:
        results["review"] = train_review_risk(args.database, args.artifacts)
    if args.task in {"demand", "all"}:
        results["demand"] = train_demand(args.database, args.artifacts)
    summary: dict[str, object] = {
        name: result.get("selected_model") for name, result in results.items()
    }
    if "demand" in results:
        summary["demand_seller"] = results["demand"].get("seller_selected_model")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
