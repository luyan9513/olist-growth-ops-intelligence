"""P12 作品集证据、案例报告与原生报告产物构建器。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.experiments import binary_proportion_mde, binary_proportion_sample_size


def _entity_count(snapshot: dict[str, Any], entity: str) -> int:
    return int(next(row["row_count"] for row in snapshot["source_profile"] if row["entity"] == entity))


def _model_row(task: str, selected_name: str, selected: dict[str, Any], baseline: dict[str, Any],
               metric: str, lower_is_better: bool = False) -> dict[str, Any]:
    selected_value = float(selected[metric])
    baseline_value = float(baseline[metric])
    improvement = baseline_value - selected_value if lower_is_better else selected_value - baseline_value
    return {
        "task": task,
        "selected_model": selected_name,
        "metric": metric,
        "baseline": baseline_value,
        "selected": selected_value,
        "absolute_improvement": improvement,
        "lower_is_better": lower_is_better,
    }


def build_portfolio_evidence(
    snapshot: dict[str, Any],
    lead: dict[str, Any],
    review: dict[str, Any],
    demand: dict[str, Any],
    seller_ops: dict[str, Any],
) -> dict[str, Any]:
    """只汇总已落盘证据，不包含商家明细、干预结果或收益推断。"""

    funnel = snapshot["funnel_overall"][0]
    commerce = snapshot["commerce_overall"][0]
    baseline_low_review_rate = float(commerce["low_review_rate"])
    target_absolute_decrease = 0.03
    experiment = binary_proportion_sample_size(
        baseline_low_review_rate, target_absolute_decrease, direction="decrease"
    )
    p1_count = int(seller_ops["action_counts"]["P1 履约护航"])
    current_mde = binary_proportion_mde(p1_count, baseline_low_review_rate, direction="decrease")

    selected_lead = lead["test_metrics"][lead["selected_model"]]
    selected_review = review["test_metrics"][review["selected_model"]]
    category_selected = demand["metrics"][demand["selected_model"]]
    seller_selected = demand["seller_metrics"][demand["seller_selected_model"]]
    occurrence = demand["seller_occurrence_metrics"]

    strategies = []
    for strategy, values in seller_ops["capacity_strategy_comparison"]["200"].items():
        strategies.append({"strategy": strategy, **values})

    quality_rows = snapshot["data_quality"]
    evidence = {
        "schema_version": "portfolio_evidence_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_scale": {
            "mql_count": _entity_count(snapshot, "mql"),
            "closed_deal_count": _entity_count(snapshot, "closed_deals"),
            "order_count": _entity_count(snapshot, "orders"),
            "order_item_count": _entity_count(snapshot, "order_items"),
            "review_count": _entity_count(snapshot, "reviews"),
            "seller_count": _entity_count(snapshot, "sellers"),
        },
        "business_overview": {
            "won_count": int(funnel["won_count"]),
            "conversion_rate": float(funnel["conversion_rate"]),
            "delivered_orders": int(commerce["delivered_orders"]),
            "delivered_gmv": float(commerce["delivered_gmv"]),
            "delay_rate": float(commerce["delay_rate"]),
            "low_review_rate": baseline_low_review_rate,
        },
        "channels": snapshot["channel_quality"],
        "seller_segments": snapshot["seller_segments"],
        "model_comparisons": [
            _model_row("线索成交排序", lead["selected_model"], selected_lead,
                       lead["test_metrics"]["prevalence_baseline"], "pr_auc"),
            _model_row("订单低评分风险", review["selected_model"], selected_review,
                       review["test_metrics"]["prevalence_baseline"], "pr_auc"),
            _model_row("品类周需求", demand["selected_model"], category_selected,
                       demand["metrics"]["moving_average_4"], "wape", True),
            _model_row("商家周订单量", demand["seller_selected_model"], seller_selected,
                       demand["seller_metrics"]["moving_average_4"], "wape", True),
            _model_row("商家下周活动", "two_stage_classifier", occurrence["two_stage_classifier"],
                       occurrence["prevalence_baseline"], "pr_auc"),
        ],
        "model_operating_metrics": {
            "lead_top20_lift": float(selected_lead["top_k"]["20pct"]["lift"]),
            "lead_top20_recall": float(selected_lead["top_k"]["20pct"]["recall"]),
            "review_top10_lift": float(selected_review["top_k"]["10pct"]["lift"]),
            "review_top10_recall": float(selected_review["top_k"]["10pct"]["recall"]),
            "review_calibrated_brier": float(
                review["calibration"]["comparison"]["sigmoid_calibrated"]["brier_score"]
            ),
        },
        "operations": {
            "scored_seller_count": int(seller_ops["scored_seller_count"]),
            "risk_join_coverage": float(seller_ops["risk_join_coverage"]),
            "action_counts": seller_ops["action_counts"],
            "capacity": 200,
            "strategy_comparison": strategies,
        },
        "experiment_readiness": {
            "status": "仅完成离线实验前规划，尚无真实干预与效果结果",
            "primary_metric": "low_review_rate",
            "baseline_rate": baseline_low_review_rate,
            "target_absolute_decrease": target_absolute_decrease,
            "alpha": experiment.alpha,
            "power": experiment.power,
            "required_total_sample": experiment.total_sample_size,
            "current_p1_candidate_count": p1_count,
            "current_candidate_mde": current_mde,
        },
        "data_quality": {
            "rule_count": len(quality_rows),
            "warning_rule_count": sum(int(row["issue_count"] > 0) for row in quality_rows),
            "issue_rules": [row for row in quality_rows if row["issue_count"] > 0],
        },
        "boundaries": [
            "所有业务结论来自 Olist 匿名公开历史数据，不代表当前市场或线上效果。",
            "容量覆盖是离线排序对照，不是增量订单、利润、ROI 或因果效果。",
            "实验模块只有样本量、MDE、分组和日志契约，没有真实干预结果。",
            "需求预测缺少库存、促销和曝光数据，只能支持资源规划演示。",
        ],
    }
    validate_portfolio_evidence(evidence)
    return evidence


def validate_portfolio_evidence(evidence: dict[str, Any]) -> None:
    """阻止不完整、越界或含商家明细的证据进入对外材料。"""

    if any(value <= 0 for value in evidence["data_scale"].values()):
        raise ValueError("数据规模必须全部大于 0")
    if sum(evidence["operations"]["action_counts"].values()) != evidence["operations"]["scored_seller_count"]:
        raise ValueError("行动类型计数与可评分商家数不一致")
    if sum(row["seller_count"] for row in evidence["seller_segments"]) != evidence["data_scale"]["seller_count"]:
        raise ValueError("商家分群计数与商家总数不一致")
    for row in evidence["operations"]["strategy_comparison"]:
        if row["selected_count"] != evidence["operations"]["capacity"]:
            raise ValueError("策略对照选中数必须等于容量")
        for key in ("predicted_activity_mass_coverage", "expected_order_count_coverage",
                    "latest_13w_gmv_coverage", "high_value_high_risk_coverage"):
            if not 0 <= row[key] <= 1:
                raise ValueError(f"{key} 必须在 [0, 1]")
    if "seller_priority" in evidence:
        raise ValueError("作品集证据不得包含商家级明细")
    if evidence["experiment_readiness"].get("observed_effect") is not None:
        raise ValueError("没有真实干预数据，不得写 observed_effect")


def render_portfolio_case_study(e: dict[str, Any]) -> str:
    """把统一证据渲染为适合招聘方阅读的案例说明。"""

    scale, biz = e["data_scale"], e["business_overview"]
    ops = e["operations"]["strategy_comparison"][0]
    exp = e["experiment_readiness"]
    models = {row["task"]: row for row in e["model_comparisons"]}
    return f"""# 商家增长与履约运营智能平台：作品集案例

## Executive Summary

基于 Olist 匿名公开历史数据，我把 **{scale['mql_count']:,} 条线索、{scale['order_count']:,} 笔订单和 {scale['seller_count']:,} 个商家** 串成“获客—成交—经营—履约—体验”决策链。项目交付的不只是模型，而是可测试的数据口径、时间安全的风险排序、容量受限的行动清单，以及在没有成本和真实干预数据时明确克制的结论边界。

## 业务问题与决策产物

- 漏斗与渠道：历史口径下有效成交 {biz['won_count']:,}，整体成交率 {biz['conversion_rate']:.2%}；渠道同时比较成交、后续 GMV、延迟与低评分，避免只追短期转化。
- 商家经营：识别高价值与体验风险分群，把 {e['operations']['scored_seller_count']:,} 个可评分商家分成五类互斥动作。
- 履约体验：历史已交付 GMV 为 R$ {biz['delivered_gmv']:,.2f}，可判断订单延迟率 {biz['delay_rate']:.2%}，合法评价低评分率 {biz['low_review_rate']:.2%}。
- 容量 200 的统一规则覆盖 {ops['high_value_high_risk_coverage']:.1%} 可评分高价值高风险商家；这是历史排序覆盖，不是增量收益。

## 模型证据与边界

- 线索成交：时间外测试 PR-AUC 从 {models['线索成交排序']['baseline']:.3f} 提升至 {models['线索成交排序']['selected']:.3f}，Top 20% Lift {e['model_operating_metrics']['lead_top20_lift']:.2f}。
- 低评分风险：订单创建时模型 PR-AUC 从 {models['订单低评分风险']['baseline']:.3f} 提升至 {models['订单低评分风险']['selected']:.3f}，Top 10% Lift {e['model_operating_metrics']['review_top10_lift']:.2f}；独立时间校准 Brier {e['model_operating_metrics']['review_calibrated_brier']:.3f}。
- 品类需求：WAPE 从 {models['品类周需求']['baseline']:.2%} 降到 {models['品类周需求']['selected']:.2%}。商家订单量 WAPE 仍为 {models['商家周订单量']['selected']:.2%}，只称有限改善。
- 防泄漏：线索模型不使用成交后字段；低评分模型不使用最终评价、实际签收或最终延迟结果。

## 从预测到运营动作

在相同容量 200 下，统一行动规则、仅活动概率、仅近期 GMV 三种队列并排比较。统一规则优先保护高价值高风险商家，但会牺牲一部分活动概率和近期 GMV 覆盖；项目保留这个取舍，而不使用没有经济依据的伪精确总分。

## 实验准备度

当前只有离线实验前规划，没有真实运营效果。以历史低评分率 {exp['baseline_rate']:.2%} 为基线，若希望识别绝对下降 3 个百分点，在双侧 α={exp['alpha']:.2f}、power={exp['power']:.0%} 的近似下需要 {exp['required_total_sample']:,} 个成熟样本；单周 P1 候选只有 {exp['current_p1_candidate_count']}，对应可检测变化约 {exp['current_candidate_mde']:.2%}，不能把“不显著”解释成“没有效果”。

## 工程可信度

DuckDB + dbt-duckdb 按 staging → intermediate → mart 分层；模型和报告读取同一批落盘证据。作品集验收会检查证据再生成一致性、行动计数、分群总数、对外材料数量和截图文件，降低手工复制导致的口径漂移。

## 下一步

真实业务价值最高的下一步不是继续调参，而是接入真实触达与履约动作，跨周积累足够成熟样本，按预注册主指标和护栏完成 ITT 评估；若仍只有公开历史数据，则应把精力放在解释决策取舍与维护可复现交付。

## 结论边界

""" + "\n".join(f"- {item}" for item in e["boundaries"]) + "\n"


def build_portfolio_artifact(e: dict[str, Any]) -> dict[str, Any]:
    """构建 Data Analytics 原生报告的 manifest 与有界 snapshot。"""

    generated = e["generated_at_utc"]
    strategies = []
    labels = {
        "high_value_high_risk_coverage": "高价值高风险覆盖",
        "predicted_activity_mass_coverage": "活动概率质量覆盖",
        "latest_13w_gmv_coverage": "近13周GMV覆盖",
    }
    for row in e["operations"]["strategy_comparison"]:
        for field, label in labels.items():
            strategies.append({"strategy": row["strategy"], "metric": label, "coverage": row[field]})
    segment_rows = sorted(e["seller_segments"], key=lambda x: x["delivered_gmv"], reverse=True)
    sources = [
        {"id": "analysis", "label": "业务分析快照", "path": "artifacts/analysis_snapshot.json",
         "query": {"description": "DuckDB mart 汇总后的数据规模、漏斗、履约与商家分群证据"}},
        {"id": "models", "label": "模型评估产物", "path": "artifacts/*/metrics.json",
         "query": {"description": "时间切分测试集上的基线、所选模型和容量指标"}},
        {"id": "ops", "label": "商家行动元数据", "path": "artifacts/demand_forecast/seller_ops_metadata.json",
         "query": {"description": "相同容量下三种离线排序策略的覆盖对照"}},
    ]
    strategy_source = {
        "id": "portfolio_strategy_query", "label": "容量策略覆盖查询",
        "path": "reports/portfolio_evidence.json",
        "query": {
            "engine": "DuckDB", "language": "sql",
            "description": "展开统一证据中的容量 200 策略，并转换为长表供分组柱图使用",
            "sql": """with wide as (
  select unnest(operations.strategy_comparison, recursive := true)
  from read_json_auto('reports/portfolio_evidence.json')
), tidy as (
  unpivot wide on high_value_high_risk_coverage, predicted_activity_mass_coverage,
    latest_13w_gmv_coverage into name metric value coverage
)
select strategy,
  case metric
    when 'high_value_high_risk_coverage' then '高价值高风险覆盖'
    when 'predicted_activity_mass_coverage' then '活动概率质量覆盖'
    when 'latest_13w_gmv_coverage' then '近13周GMV覆盖'
  end as metric,
  coverage
from tidy""",
            "tables_used": ["reports/portfolio_evidence.json"],
            "metric_definitions": ["覆盖率=入选队列对应指标总量/全部可评分商家对应指标总量"],
        },
    }
    segment_source = {
        "id": "portfolio_segment_query", "label": "商家分群查询",
        "path": "reports/portfolio_evidence.json",
        "query": {
            "engine": "DuckDB", "language": "sql",
            "description": "展开统一证据中的商家分群汇总",
            "sql": "select unnest(seller_segments, recursive := true) from read_json_auto('reports/portfolio_evidence.json') order by delivered_gmv desc",
            "tables_used": ["reports/portfolio_evidence.json"],
            "metric_definitions": ["已交付GMV=已交付订单的商品价与运费之和"],
        },
    }
    model_source = {
        "id": "portfolio_model_query", "label": "模型对照查询",
        "path": "reports/portfolio_evidence.json",
        "query": {
            "engine": "DuckDB", "language": "sql",
            "description": "展开统一证据中的模型与简单基线对照",
            "sql": "select unnest(model_comparisons, recursive := true) from read_json_auto('reports/portfolio_evidence.json') order by task",
            "tables_used": ["reports/portfolio_evidence.json"],
            "metric_definitions": ["PR-AUC 越高越好；WAPE 越低越好；均为时间外测试或回测结果"],
        },
    }
    manifest = {
        "version": 1,
        "surface": "report",
        "title": "商家增长与履约运营智能平台：决策证据报告",
        "description": "基于 Olist 匿名公开历史数据的作品集证据，不代表线上效果或 ROI。",
        "generatedAt": generated,
        "sources": sources,
        "charts": [
            {"id": "strategy_chart", "title": "容量 200 的策略覆盖对照", "dataset": "strategy_coverage",
             "source": strategy_source,
             "type": "bar", "encodings": {"x": {"field": "metric", "type": "nominal", "title": "覆盖指标"},
             "y": {"field": "coverage", "type": "quantitative", "title": "覆盖率", "format": "percent"},
             "color": {"field": "strategy", "type": "nominal", "title": "排序策略"}},
             "options": {"orientation": "vertical", "grouping": "grouped"}},
            {"id": "segment_chart", "title": "商家分群的历史已交付 GMV", "dataset": "seller_segments",
             "source": segment_source,
             "type": "bar", "encodings": {"x": {"field": "seller_segment", "type": "nominal", "title": "商家分群"},
             "y": {"field": "delivered_gmv", "type": "quantitative", "title": "已交付 GMV", "format": "currency"}},
             "options": {"orientation": "vertical"}},
        ],
        "tables": [{"id": "model_table", "title": "模型与简单基线对照", "dataset": "model_comparisons",
                    "source": model_source,
                    "columns": [{"field": "task", "label": "任务"}, {"field": "selected_model", "label": "所选模型"},
                                {"field": "metric", "label": "指标"}, {"field": "baseline", "label": "基线"},
                                {"field": "selected", "label": "所选模型结果"}],
                    "defaultSort": {"field": "task", "direction": "asc"}}],
        "blocks": [
            {"id": "title", "type": "markdown", "body": "# 商家增长与履约运营智能平台：决策证据报告"},
            {"id": "summary", "type": "markdown", "body": "## Executive Summary\n\n项目把获客、成交、商家经营、履约与体验串成一条可追溯决策链。主要价值是可测试口径、时间安全模型和容量受限行动清单；所有结果均为公开历史数据下的离线证据。"},
            {"id": "ops_text", "type": "markdown", "body": "## 运营策略取舍\n\n统一规则优先保护高价值高风险商家；仅活动概率和仅近期 GMV 策略在各自目标上覆盖更高。图中展示的是相同容量下的历史排序覆盖，不是因果收益。"},
            {"id": "strategy_block", "type": "chart", "chartId": "strategy_chart"},
            {"id": "seller_text", "type": "markdown", "body": "## 商家经营分层\n\n分群同时保留价值和体验风险，避免只按 GMV 排序。"},
            {"id": "segment_block", "type": "chart", "chartId": "segment_chart"},
            {"id": "model_text", "type": "markdown", "body": "## 模型证据\n\n所有模型均按时间切分并与简单基线比较。WAPE 越低越好，PR-AUC 越高越好；结果不外推为线上提升。"},
            {"id": "model_block", "type": "table", "tableId": "model_table"},
            {"id": "next", "type": "markdown", "body": "## 下一步与限制\n\n下一步应接入真实动作日志并跨周积累成熟样本，用预注册指标完成 ITT 评估。当前没有真实干预、成本、利润或 ROI 结果。"},
        ],
    }
    high_risk = next(row for row in e["seller_segments"] if row["seller_segment"] == "高价值高风险")
    snapshot = {
        "version": 1, "status": "ready", "generatedAt": generated,
        "datasets": {
            "headline": [{**e["data_scale"], "high_risk_count": high_risk["seller_count"]}],
            "strategy_coverage": strategies,
            "seller_segments": segment_rows,
            "model_comparisons": e["model_comparisons"],
        },
    }
    return {"surface": "report", "manifest": manifest, "snapshot": snapshot, "sources": sources}
