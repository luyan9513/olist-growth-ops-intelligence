# 商家增长与履约运营智能平台

[![CI](https://github.com/luyan9513/olist-growth-ops-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/luyan9513/olist-growth-ops-intelligence/actions/workflows/ci.yml)

项目仓库：[github.com/luyan9513/olist-growth-ops-intelligence](https://github.com/luyan9513/olist-growth-ops-intelligence)

基于 Olist 匿名公开历史数据，串联“线索获取 → 商家成交 → 商家经营 → 订单履约 → 用户体验”的本地分析、预测与运营决策项目。

> 当前状态：已使用 11 个 Olist 官方公开 CSV 完成真实 dbt 构建、三类模型回测、统一商家运营行动清单、干预实验设计框架、10 页 Streamlit 看板、案例报告、无数据 CI 和发布前仓库检查。没有真实渠道成本和干预结果，项目不宣称真实 ROI、线上提升或因果效果。

## 文档入口

- [项目章程](docs/00_project_charter.md)
- [需求与指标](docs/01_requirements_and_metrics.md)
- [解决方案架构](docs/02_solution_architecture.md)
- [数据设计](docs/03_data_design.md)
- [模型与实验设计](docs/04_model_and_experiment_design.md)
- [干预与随机实验设计](docs/07_intervention_and_experiment_design.md)
- [实施计划与风险](docs/05_implementation_plan_and_risks.md)
- [需求追踪](docs/traceability.md)
- [真实验证结果](docs/06_validation_results_and_conclusions.md)
- [技术报告](reports/technical_report.md)
- [业务报告](reports/business_report.md)
- [商家运营行动决策报告](reports/seller_ops_decision_report.md)
- [实验设计报告](reports/experiment_design_report.md)
- [数据卡](reports/data_card.md)
- [线索模型卡](reports/models/lead_conversion_model_card.md)
- [低评分模型卡](reports/models/review_risk_model_card.md)
- [需求预测模型卡](reports/models/demand_forecast_model_card.md)
- [项目演示指南](docs/08_portfolio_demo_guide.md)
- [仓库发布设计](docs/09_repository_release.md)
- [真实业务落地手册](docs/10_real_world_rollout_playbook.md)
- [项目案例报告](reports/portfolio_case_study.md)

## 本地环境

项目要求 Python 3.11+，当前验证环境为 Python 3.12.13。

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
make check-env
make test
```

无需原始数据或模型产物的提交前检查：

```bash
make repo-check
make ci
```

`make ci` 检查仓库边界、解析 dbt 项目并运行全部 Python 测试；它与 GitHub Actions 的核心步骤一致，但不替代带真实数据的 `dbt build`、模型重训和看板验收。

页面测试分为两类：主应用在数据库缺失时必须给出明确准备提示；10 个业务页面使用微型合成 fixture 验证字段契约和组件渲染。合成 fixture 不参与任何业务指标或模型结果，真实页面仍由本地 DuckDB、artifacts、`make portfolio-check` 和浏览器截图验收。

原始数据不会进入 Git。文件要求与清单生成方式见 [data/raw/README.md](data/raw/README.md)。

将两份 Kaggle 数据的 11 个 CSV 放入 `data/raw/` 后，完整复现流程：

```bash
make manifest
make dbt-build
.venv/bin/python -m src.train all
make analysis
make test
make dashboard
```

原始数据已就位时，也可用 `make verify` 一次完成环境、清单、dbt、模型、分析快照和测试验收。

已验证环境中，64 个 Python 测试（含 10 页看板冒烟、作品集证据、主题和仓库发布检查）全部通过；dbt 运行 29 个模型和 57 项数据测试，结果为 84 通过、2 数据异常告警、0 错误。应用包含 10 个业务页面，数据不存在时不回退到假数据。

P8 增强后，两个分类任务都增加了 3 个扩展时间窗口、500 次 bootstrap 95% 区间和独立时间段 sigmoid 校准。低评分任务最终按选模期 PR-AUC 选择逻辑回归：测试 PR-AUC 0.197，Top 10% Lift 2.32；独立校准后 Brier 0.097，略优于先验基线 0.099。随机森林在 3 个滚动窗口中仅 1 次胜过逻辑回归，未证明复杂模型有稳定优势。

P9 将稀疏的商家周需求拆为“下周是否活跃 + 活跃时订单量”。活动分类器在 23,268 个时间外商家周上的 PR-AUC 为 0.680，8/8 周都高于当周活动率；两阶段期望订单量 WAPE 为 84.46%，相对 4 周移动平均 86.95% 有限改善，并在 8 周中 7 周不劣。间歇活跃层 WAPE 仍为 122.99%，因此结果用于活动优先级和资源排序，不用于精确补货。

P10 将活动概率与商家价值、增长和履约风险一对一整合为 3,051 行行动清单。默认 200 个历史模拟名额覆盖 79.4% 的可评分高价值高风险商家；只按活动概率和只按近期 GMV 排序分别为 22.6% 和 26.6%。统一规则因此更适合“优先保护风险暴露”，但活动概率质量和近期 GMV覆盖低于单目标排序，页面和报告会同时展示这一取舍。

P11 增加实验登记、稳定 SHA-256 草案分组、执行/结果日志契约、样本量/MDE 规划和日志质量校验。默认 P1 池有 158 个商家；若规划基线低评分率 14.19%、希望识别下降 3 个百分点、alpha 0.05、power 80%，近似需要 3,864 个成熟样本，当前池只能识别约 12.10 个百分点的下降。该结论用于说明实验可行性，不是预计效果；四张日志模板只有表头。

P12 把当前分析、模型、行动和实验产物归并为统一证据 JSON、案例报告和原生可视化报告。四张关键截图均来自当前真实本地看板；`make portfolio-check` 会重新生成证据、对账权威产物、检查内部链接和截图尺寸，并运行作品集/页面专项测试。

P13 补齐项目发布层：GitHub Actions 使用 Python 3.12、只读仓库权限和 pip 缓存，CI 不依赖被忽略的原始数据、DuckDB 或模型二进制；仓库检查拒绝大于 5 MiB 的候选文件、数据产物和常见私钥标记。看板改用 Streamlit 官方主题配置、统一 Plotly 配色与原生折叠筛选，并重新生成四张真实截图，同时提供真实环境 30/60/90 天落地闸门。

快速展示验收：

```bash
make portfolio-check
```

## 许可与边界

- 数据来自 Olist 公开匿名样本；2026-07-30 核对的两份官方 Kaggle 数据页均标注 CC BY-NC-SA 4.0，使用时必须署名、非商业并以相同方式共享；
- CI 远程引用 GitHub 官方 Actions，但未复制其源文件；具体版本与许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)；
- 自有代码许可证仍需仓库所有者在公开发布前人工决定；在根目录存在正式 `LICENSE` 前，不应把本项目宣称为 MIT 开源仓库；
- 本项目是公开历史数据下的作品集项目，不是生产系统或现实业务效果证明。
