# P2 dbt 数据层日志

**日期：** 2026-07-30  
**阶段：** staging → intermediate → mart 与质量测试

## 1. 修改/新增文件

- 新增 dbt 项目、DuckDB profile、9 个外部 CSV source 与 9 个 staging 模型；
- 新增成交归一、卖家归因、订单评价/支付/商品聚合、订单宽表和历史事件中间模型；
- 新增渠道漏斗、渠道商家价值、商家月度/30-60-90 天经营、履约明细与拆解、风险清单、三类模型特征和数据质量 mart；
- 新增非负/区间通用测试、时间先后与 GMV 对账测试；
- 新增 `sql/01_quality_checks.sql`、`02_staging.sql`、`03_marts.sql` 作为查询入口。

## 2. 文件作用

- staging 只做字段选择、类型转换、空值标准化；
- intermediate 先把支付、评价、商品处理到稳定粒度，防止多对多连接放大；
- 评价风险历史特征以“结果真实发生时间”作为事件时间，再用严格小于当前购买时间的 ASOF JOIN，避免只按历史订单购买时间造成标签可见性泄漏；
- marts 面向漏斗、经营、履约、运营清单与模型，不让看板重复口径。

## 3. 方案取舍

- 原始 CSV 通过 dbt-duckdb external source 只读访问，不额外复制 raw 表；
- 多评价订单取最新合法评价，同时把重复评价纳入质量报告；
- 多 MQL 对应同一卖家时，以最早合法成交作为渠道归因并保留映射数量；
- 商家风险分层使用样本内分位数，只作为公开历史样本优先级，不写成现实阈值。

## 4. 真实问题与处理

- dbt 1.12 CLI 参数顺序与旧示例不同，已在 P1 日志记录并修正；
- 初版 DQ-02/DQ-10 的分母只统计了重复子集，无法代表全体异常占比。复核指标字典后改为“全部唯一实体”为分母、额外/重复实体数为问题数。
- 首次真实 `dbt build` 发现 1 条成交时间早于首次接触、189 条订单时间顺序异常。其中 23 条客户签收早于承运商交接，166 条承运商交接早于购买；没有客户签收早于购买。它们属于源数据质量异常，底层记录应保留、质量页应展示，相关无效时间字段不进入对应时长特征，因此将 singular test 从阻断改为 warning，而不是删行或关闭检查。
- 首次完整 mart 对账发现低评分特征表为订单×卖家粒度，99,247 行高于 98,673 个有评价订单，会让多卖家订单重复标签。已把低评分特征与履约体验改为一订单一行：商品与金额求和、历史计数求和，保留主卖家、卖家数和多卖家标记；卖家经营表仍维持订单×卖家粒度。

## 5. 命令与验证结果

- `make dbt-parse`：首次因 CLI 参数顺序失败；修正后成功，dbt 1.12.0 与 duckdb adapter 1.10.1 正常注册；
- 新增完整 marts 后将再次运行 `dbt parse`；
- 第一次真实 `dbt build`：45 项通过、2 项失败、29 项因上游阻断跳过。失败来自上述 1 条成交时间和 189 条订单时间异常；调整为 warning 后将继续执行完整构建。

## 6. 局限、风险和下一步

- 没有真实 CSV，字段拼写、DuckDB 执行语义、质量异常和指标结果仍需数据构建验证；
- 可选 geolocation 与品类翻译未加入强制 DAG，避免缺少可选文件导致主流程失败；距离特征将在数据许可与文件可用后作为增强项；
- 下一步完成模型训练/评估代码和合成单元测试，然后实现看板；实际结果仍依赖授权获取公开数据。

## 7. dbt 项目结构与配置明细

| 文件/目录 | 作用 | 关键决定 |
|---|---|---|
| `dbt/dbt_project.yml` | 定义项目名、模型目录、materialization 和数据库路径 | staging/intermediate 用 view，marts 用 table，平衡修改速度与看板读取 |
| `dbt/profiles.yml` | 本地 DuckDB target 和并发数 | 不依赖用户全局 `~/.dbt/profiles.yml` |
| `dbt/macros/generate_schema_name.sql` | 固定 staging/intermediate/marts schema 名 | 避免 dbt 默认将 target schema 前缀叠加到自定义 schema |
| `dbt/macros/generic_tests.sql` | 非负、取值区间等可复用测试 | 同类检查不在每个 yml 重复 SQL |
| `dbt/tests/*.sql` | 成交时间、订单时间、GMV 对账 | 业务时序和跨粒度对账用 singular test 更易审计 |

## 8. staging 模型逐表说明

| 模型 | 主要处理 | 保留的重要字段/边界 |
|---|---|---|
| `stg_marketing_qualified_leads` | MQL 主键、首次接触时间、来源和落地页标准化 | 不在 staging 推断成交 |
| `stg_closed_deals` | 成交时间、seller_id、业务类型等类型化 | 时间倒置记录保留给质量层 |
| `stg_orders` | 购买、批准、承运、签收、预计签收时间和状态 | 不在 staging 修补异常时间 |
| `stg_order_items` | order/seller/product 键、商品价、运费、发货限期 | 金额保留原精度，负数由测试阻断 |
| `stg_order_payments` | 支付序号、类型、分期和金额 | 多笔支付暂不在 staging 求和 |
| `stg_order_reviews` | review/order 键、评分和评价时间 | 不输出评论文本到公开 mart |
| `stg_products` | product 键、品类和尺寸/重量 | 缺失品类标为 unknown 而不删除交易 |
| `stg_sellers` | 商家主键、城市和州 | 只展示区域级信息 |
| `stg_customers` | customer 与 unique_customer 键、城市和州 | 区分订单客户键与唯一客户键 |

## 9. intermediate 模型的粒度治理

| 模型 | 输出粒度 | 解决的问题 |
|---|---|---|
| `int_lead_deals` | MQL | 成交表的合法标签和成交时间定义 |
| `int_seller_acquisition` | seller | 同一商家多条 MQL 时取最早合法成交来源，保留映射数 |
| `int_order_payments` | order | 先求和支付并聚合支付类型，避免与商品行直连放大 |
| `int_order_reviews` | order | 同订单多评价时选最新合法评价，保留重复数据质量信息 |
| `int_order_seller_items` | order × seller | 在商家经营粒度求和商品价和运费，选择主品类 |
| `int_order_enriched` | order | 连接订单、支付、代表评价和客户州，计算延迟/低评分标记 |
| `int_seller_delivery_history` | seller 历史事件 | 只在实际签收结果已发生后将其纳入历史 |
| `int_seller_review_history` | seller 历史事件 | 只在评价创建后将评分纳入历史，不按订单时间提前可见 |

## 10. mart 模型与业务消费者

| mart | 粒度 | 主要消费者 | 实际构建行数/说明 |
|---|---|---|---|
| `mart_channel_funnel` | 接触月×来源 | 增长页、漏斗分析 | 113 行 |
| `mart_channel_seller_value` | 来源×订单月 | 渠道趋势 | 59 行；不用于跨月求和商家数 |
| `mart_channel_summary` | 来源 | 渠道总览 | 10 行；后续新增以解决跨月去重 |
| `mart_seller_performance` | seller×月 | 商家经营页 | 16,441 行 |
| `mart_seller_windows` | seller | 30/60/90 天商家画像 | 3,095 行 |
| `mart_delivery_experience` | order | 履约页、拆解表 | 98,666 行，多商家订单只保留一个订单行 |
| `mart_delivery_breakdown` | 维度类型×维度值 | 品类/买家州/商家州诊断 | 124 行 |
| `mart_seller_risk` | seller | 商家风险清单 | 3,095 行；风险率后续加入至少 20 单分母门槛 |
| `mart_lead_features` | MQL | 线索模型 | 8,000 行 |
| `mart_review_risk_features` | order | 低评分模型 | 97,917 行，只包含合法评价标签 |
| `mart_demand_weekly` | seller×category×week | 需求回测 | 45,383 行 |
| `mart_data_quality` | DQ 规则 | 质量页和验收报告 | 14 行，每行含分母、异常数和异常率 |

## 11. 真实数据异常的定位过程

### 11.1 成交时间倒置

- singular test 首次返回 1 行，而不是 SQL 编译失败；
- 记录的成交时间为 2018-03-06，首次接触时间为 2018-03-08；
- 因为无法从公开数据确定哪个时间正确，未修改原值；
- 处置为质量 warning，并在有效成交和商家归因中要求 `won_at >= first_contact_at`。

### 11.2 订单时间顺序异常

- 测试返回 189 行；
- 分类计数后，23 条为客户签收早于承运商交接，166 条为承运商交接早于购买，客户签收早于购买为 0；
- 这些数量较少但不为 0，如直接删除会隐藏源数据问题；
- 最终保留订单主键和非时长分析用途，无效时间不做预测特征，singular test 改为 warning。

### 11.3 订单标签被多商家放大

- 首版 `mart_review_risk_features` 为 99,247 行，高于 98,673 个有评价订单；
- 按 `order_id` 查找重复后，确认重复来自多商家订单，不是评价去重失败；
- 订单级标签如按商家行复制，会对多商家订单重复训练并放大其权重；
- 因此将低评分特征和履约体验改为一订单一行，用 GMV 选主商家，保留 seller_count/is_multi_seller，金额和商品数求和；
- 修改后 `mart_delivery_experience.order_id` 和 `mart_review_risk_features.order_id` 均通过 unique test。

## 12. 最终质量规则结果摘要

| 规则 | 检查数 | 异常数 | 异常率 | 处置 |
|---|---:|---:|---:|---|
| MQL 主键重复 | 8,000 | 0 | 0 | 通过 |
| 同一 MQL 多条成交 | 842 | 0 | 0 | 通过 |
| 成交缺 seller_id | 842 | 0 | 0 | 通过 |
| 成交早于接触 | 842 | 1 | 0.119% | warning，不进入有效归因 |
| 订单主键重复 | 99,441 | 0 | 0 | 通过 |
| 商品/运费负数 | 112,650 | 0 | 0 | 通过 |
| 支付金额负数 | 103,886 | 0 | 0 | 通过 |
| 订单时间顺序异常 | 99,441 | 189 | 0.190% | warning，不用无效时长 |
| 评分超出 1~5 | 99,224 | 0 | 0 | 通过 |
| 订单多评价 | 98,673 | 547 | 0.554% | 选最新合法评价 |
| 商品无法关联商家 | 112,650 | 0 | 0 | 通过 |
| 订单无法关联客户 | 99,441 | 0 | 0 | 通过 |
| 已交付订单缺延迟时间 | 96,478 | 8 | 0.0083% | 不进入延迟率分母 |
| 商品无有效品类 | 112,650 | 1,603 | 1.423% | 标记 unknown |

## 13. 最终构建验证

最终命令为 `.venv/bin/dbt --no-version-check build --project-dir dbt --profiles-dir dbt`。实际发现 29 个模型、54 项数据测试和 9 个 source；总计执行 83 项，结果是 `PASS=81 WARN=2 ERROR=0 SKIP=0`，用时约 2.53 秒。两个 warning 正是本日志记录的 1 条成交时间和 189 条订单时间异常，不是未知 SQL 错误。

## 14. 仍然存在的数据层限制

- 可选 geolocation 表没有进入主 DAG，因此本项目不建模精确物理距离；
- 品类翻译表不影响主流程，主 mart 保留原品类字段和 unknown；
- 商家渠道归因采用最早合法成交的 last-touch 式映射，不是多触点归因或因果归因；
- 公开数据无可靠时区说明，项目保留原无时区时间戳，不虚构 UTC/当地时间转换；
- 数据质量 warning 只说明记录异常，不能单独判断原因是录入错误、时区或业务流程。
