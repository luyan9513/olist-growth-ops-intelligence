# 需求追踪矩阵

状态以 2026-08-02 真实公开数据构建、P8/P9 模型结果、P10 行动清单、P11 实验设计框架和 P12 投递验收为准。原数据和 DuckDB 不进入 Git；所需产物均可按 README 复现。

| 需求 ID | 需求 | 实现文件 | 测试/验收 | 结果/证据 | 状态 |
|---|---|---|---|---|---|
| FR-01 | 数据准备 | `src/ingest.py`、`data/raw/README.md` | `make manifest` | `data/processed/raw_manifest.json` | 完成 |
| FR-02 | dbt 三层 | `dbt/models/{staging,intermediate,marts}` | `dbt build`：29 模型 | `PASS=84 WARN=2 ERROR=0` | 完成 |
| FR-03 | 数据质量 | `mart_data_quality`、严格历史截点等 57 项 dbt tests | 57 项 dbt tests | 1 条成交时间、189 条订单时间告警；新增历史截点测试通过 | 完成 |
| FR-04 | 漏斗/渠道 | `mart_channel_funnel`、`mart_channel_summary`、渠道页 | 去重商家粒度、加权体验率 | `analysis_snapshot.json`、业务报告 | 完成 |
| FR-05 | 商家经营 | `mart_seller_performance`、`mart_seller_windows`、商家页 | GMV 对账、商家主键 | 16,441 商家月记录 | 完成 |
| FR-06 | 履约体验 | `mart_delivery_experience`、`mart_seller_risk` | 订单粒度唯一、率分母门槛 | 199 个高价值高风险商家 | 完成 |
| FR-07 | 线索预测 | `src/features.py`、`src/train.py`、`src/evaluate.py` | 时间切分、黑名单、Top-K | `artifacts/lead_conversion/metrics.json`，PR-AUC 0.193 | 完成 |
| FR-08 | 低评分预测 | `mart_review_risk_features`、训练/评估模块 | 严格历史截点、校准、分组误差 | 逻辑回归 PR-AUC 0.197；校准 Brier 0.097 | 完成 |
| FR-09 | 商家/品类需求 | `src/forecast.py`、`src/train.py` | 滞后/活动特征泄漏、尾部截断、Croston 历史截点、8 周滚动回测 | 品类 WAPE 31.31%；商家活动 PR-AUC 0.680、两阶段 WAPE 84.46% | 完成 |
| FR-10 | 历史情景模拟 | `app/pages/scenario.py` | 容量边界和覆盖测试 | 公开历史测试集模拟，无 ROI 宣称 | 完成 |
| FR-11 | 可下载清单 | 看板、`artifacts/demand_forecast/*.csv` | 无评论文本/精确地理 | 商家风险、线索、需求资源清单 | 完成 |
| FR-12 | 文档追溯 | `docs/`、`reports/`、README | 链接、占位符、数字抽查 | 本矩阵与阶段日志 | 完成 |
| NFR-01 | 可复现 | requirements、Makefile、README | 环境检查与全流程命令 | Python 3.12.13 锁定环境 | 完成 |
| NFR-02 | 本地优先 | DuckDB/dbt/Streamlit | 本地构建 | 无云服务依赖 | 完成 |
| NFR-03 | 隐私安全 | `.gitignore`、数据卡 | 敏感模式扫描 | 原数据/模型产物不入 Git | 完成 |
| NFR-04 | 性能 | 聚合 mart、Streamlit cache | 运行时记录 | dbt build 2.65 秒；本地环境数字 | 完成 |
| NFR-05 | 可解释 | 特征重要性、分组误差、原因字段 | 产物存在性/模型卡 | 三份模型卡 | 完成 |
| NFR-06 | 诚实表达 | 业务/技术报告、简历 | 占位符与 ROI/因果措辞检查 | 局限、告警、负面模型结果均披露 | 完成 |
| NFR-07 | 分类模型稳健性 | `src/evaluate.py`、`src/train.py`、模型卡 | 3 个滚动时间窗、500 次 bootstrap、独立校准测试 | 两任务 metrics JSON 已包含完整产物 | 完成 |
| NFR-08 | 增强特征时间安全 | `mart_review_risk_features`、`src/features.py` | dbt 范围测试、禁用字段、严格历史截点测试 | `assert_review_history_is_strictly_prior` 通过 | 完成 |
| NFR-09 | 商家间歇需求稳健性 | `src/forecast.py`、`src/train.py`、P9 测试、需求模型卡 | 活动特征反事实、Croston 历史截点、8 周逐周和活动层评估 | 39 项测试通过；两阶段对移动平均 7/8 周不劣；活动三层误差已披露 | 完成 |
| FR-13 / NFR-10 | 统一商家运营行动清单 | `src/decisioning.py`、`src/train.py`、`app/pages/ops_actions.py`、P10 测试 | 一对一覆盖、规则互斥、排序确定性、容量边界、9 页看板渲染 | 3,051 行唯一清单；46 项测试通过；容量 200 高价值高风险覆盖 79.40% | 完成 |
| FR-14 / NFR-11 | 干预与随机实验框架 | `src/experiments.py`、`app/pages/experiments.py`、`data/templates/experiment/`、`docs/07_intervention_and_experiment_design.md` | 公式边界/方向、稳定且行序无关分组、禁用结果分层、日志链路、10 页看板 | 58 项测试通过；P1 158 个候选对 3pp MDE 需 3,864；模板 0 行 | 完成 |
| FR-15 / NFR-12 | 投递版作品集包装 | `docs/08_portfolio_demo_guide.md`、`reports/portfolio_case_study.md`、`src/portfolio.py`、`scripts/{build_portfolio_evidence.py,validate_portfolio.py,capture_dashboard_screenshots.mjs}`、4 张关键截图 | 原生报告校验通过；`make portfolio-check` 17 项专项通过；62 项全量 Python 通过；dbt 84 PASS/2 WARN/0 ERROR | `reports/portfolio_evidence.json`、`reports/portfolio_artifact.json`、`docs/assets/portfolio/`、P12 日志 | 完成 |
| FR-16 / NFR-13 / NFR-14 | 仓库发布与无数据 CI | `.github/workflows/ci.yml`、PR/Issue 模板、`CONTRIBUTING.md`、`RELEASE_CHECKLIST.md`、`scripts/validate_repository.py` | `make ci`：最终 167 个候选文件检查通过、dbt parse 通过、64 项 Python 通过；真实 dbt build 84 PASS/2 WARN/0 ERROR | `docs/09_release_and_role_packaging.md`、P13 日志 | 完成 |
| FR-17 | 四类岗位投递材料 | `reports/resume_bullets_by_role.md`、`reports/jd_tailoring_checklist.md`、README 与面试指南入口 | 仓库检查核对四版各 5 条；数字逐项取自 `portfolio_evidence.json`，明确离线/非 ROI 边界 | P13 日志 | 完成 |
| FR-18 | 看板展示体验 | `.streamlit/config.toml`、`app/theme.py`、9 个图表页面、更新截图 | 10 页冒烟属于 64 项全量测试；4 张 1440×1000 PNG 真实浏览器生成、格式/尺寸自动检查并目视复核 | `docs/assets/portfolio/`、P13 日志 | 完成 |
| NFR-15 | 托管 CI 与本地数据隔离 | `tests/test_streamlit_pages.py`、`tests/streamlit_fixtures.py`、`.github/workflows/ci.yml` | 首次 run `30891909430` 失败根因已确认；待本地干净数据模拟与新 GitHub run 后填写 | P14 日志 | 开发中 |

## 文档验收索引

| 读者问题 | 主要文档 |
|---|---|
| 为什么做、服务谁、成功标准是什么 | `00_project_charter.md` |
| 功能与指标怎么算 | `01_requirements_and_metrics.md`、`metric_dictionary.md` |
| 数据如何流动、为什么这样选型 | `02_solution_architecture.md` |
| 数据来源、粒度、质量和许可 | `03_data_design.md`、`reports/data_card.md` |
| 模型怎么切分、评估和防泄漏 | `04_model_and_experiment_design.md`、`reports/models/` |
| 干预如何记录、随机化和评估 | `07_intervention_and_experiment_design.md`、`reports/experiment_design_report.md` |
| 实际结果、问题、结论和局限 | `06_validation_results_and_conclusions.md`、`logs/` |
| 怎么在面试中介绍 | `interview_guide.md`、`08_portfolio_demo_guide.md`、`reports/portfolio_case_study.md`、`reports/resume_bullets.md`、`reports/resume_bullets_by_role.md` |
| 怎么发布、真实业务如何落地 | `09_release_and_role_packaging.md`、`10_real_world_rollout_playbook.md`、`RELEASE_CHECKLIST.md` |
