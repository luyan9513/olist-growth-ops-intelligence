# P12 投递版作品集与演示验收开发日志

## 1. 阶段信息

- 阶段：P12 投递版作品集、演示路线与证据验收；
- 日期：2026-08-02（Asia/Shanghai）；
- 开发目标：把 P0–P11 已经完成的数据、模型、行动清单和实验设计整理成招聘方能快速阅读、面试时能稳定演示、关键数字能自动回到权威产物的投递版本；
- 明确不做：不训练新模型，不把离线覆盖写成真实提升，不补造干预日志，不计算不存在的 ROI，不引入新的依赖或外部服务；
- 数据状态：继续使用当前工作区内已经完成 dbt 构建和模型训练的 Olist 匿名公开历史数据产物；本阶段没有下载或修改原始数据。

本阶段先更新需求、风险、演示范围和追踪关系，再写证据构建代码。最终交付包含统一证据 JSON、案例报告、原生可视化报告、四张真实看板截图、根目录 Streamlit 入口、一键验收命令、专项测试和完整文档收口。

## 2. 开发前固定的判断与验收门槛

### 2.1 为什么不继续调模型

P8 已完成分类模型稳健性和低评分增强，P9 已完成间歇需求重构，P10 已完成运营行动层，P11 已完成实验设计入口。当前对求职投递最有价值的缺口不是再增加一个算法，而是让招聘方在 30 秒、5 分钟和 20 分钟三个阅读深度下都能理解项目，并能核查数字来源。因此 P12 固定为“包装与证据工程”，不因开发过程中看到现有分数而临时改变模型。

### 2.2 开发前写入的验收条件

1. 先有 30 秒介绍、5 分钟路线、角色差异和可说/不可说边界；
2. 作品集数字从现有 JSON、DuckDB 汇总产物或行动元数据读取，不在案例报告中维护第二套手填口径；
3. 证据不得包含 `seller_priority` 或商家级 ID 明细；
4. 五类行动数量必须加总为可评分商家数；四个商家分群必须加总为商家总数；
5. 容量 200 的三个策略必须使用相同 `selected_count=200`，覆盖率必须位于 `[0, 1]`；
6. 实验部分只能出现基线、MDE、alpha、power 和样本量规划，不得出现 `observed_effect`；
7. 简历 bullet 必须恰好 5 条，面试问答必须恰好 20 个；
8. 四张截图必须来自当前本地 Streamlit，格式为 PNG，宽至少 1200、高至少 700；
9. 快速验收通过后，还要运行全量 Python 和 dbt 回归；
10. 原生报告必须先通过结构校验再渲染，不能用失败的渲染尝试充当校验。

## 3. 新增与修改文件

### 3.1 开发前文档

#### `docs/08_portfolio_demo_guide.md`

新增 P12 的主展示指南，具体包含：

- 30 秒、3–5 分钟、15–20 分钟三档阅读路径；
- 一句话和 30 秒项目介绍；
- 从原始 CSV、dbt 分层、marts、模型、行动、实验到看板/报告的 Mermaid 架构图；
- 五分钟演示的六段时间分配，并为每段写明应该表达的业务判断和不能越界的措辞；
- 数据分析、增长分析、商业分析、BI 和电商运营分析五类岗位的讲解重点；
- 四张关键截图的名称、用途和当前真实图片；
- 渠道、模型、行动、需求、实验和商业价值的“可说/不可说”矩阵；
- 数字到权威产物的快速索引；
- `make portfolio-check` 的使用方式与演示前检查清单。

选择这种结构，是因为招聘方首先判断业务链和个人判断力，不会先阅读代码目录。若只在 README 增加更多技术细节，仍然无法解决面试演示容易跳页、模型分数压过业务取舍的问题。

#### `docs/01_requirements_and_metrics.md`

新增 FR-15 投递版作品集交付和 NFR-12 证据一致性要求。这样 P12 不是临时做几张图，而是有明确需求 ID、验收条件和追踪关系的正式阶段。

#### `docs/05_implementation_plan_and_risks.md`

开发前新增 P12 阶段、固定实施顺序和 R-31 至 R-34 风险；阶段结束后把状态更新为已完成，并记录真实验收结果：17 项专项、62 项全量 Python、dbt 84 PASS/2 WARN/0 ERROR。

新增风险分别覆盖：案例数字漂移、为求职夸大个人贡献/因果、演示主线失焦、截图与当前页面不一致。没有新增“模型效果不够好”风险，因为这已经在前序阶段登记并有退出判断。

#### `docs/traceability.md`

开发前新增 FR-15/NFR-12 的待验证行；完成后补齐实现文件、测试、证据和状态。P12 行现在可以从需求定位到 `src/portfolio.py`、三个脚本、案例报告、原生报告和截图目录。

### 3.2 统一证据与报告代码

#### `src/portfolio.py`

新增纯构建模块，主要职责如下：

1. `build_portfolio_evidence` 从五类现有产物读取数据：
   - `artifacts/analysis_snapshot.json`；
   - `artifacts/lead_conversion/metrics.json`；
   - `artifacts/review_risk/metrics.json`；
   - `artifacts/demand_forecast/metrics.json`；
   - `artifacts/demand_forecast/seller_ops_metadata.json`。
2. 统一输出数据规模、整体漏斗/履约、渠道、商家分群、五个模型/任务的基线对照、Top-K 运营指标、行动数量、容量策略、实验可行性和质量告警；
3. 调用 P11 已有的 `binary_proportion_sample_size` 和 `binary_proportion_mde` 重新计算样本量，不手抄 3,864 和 12.10%；
4. `validate_portfolio_evidence` 校验数据规模、行动加总、分群加总、容量一致、覆盖率范围、商家明细禁入和真实效果禁入；
5. `render_portfolio_case_study` 生成招聘方可读的 Markdown 案例；
6. `build_portfolio_artifact` 生成原生报告的 manifest、snapshot 和 source metadata。

没有直接读取商家级行动 CSV，是因为作品集摘要只需要分群和容量对照，读取明细会扩大隐私与误展示风险。证据中也明确拒绝 `seller_priority`，避免公开材料无意带出商家 ID。

模型对照保留“指标越高/越低越好”的方向字段。品类/商家需求使用 WAPE 时计算的是基线减所选模型；分类使用 PR-AUC 时计算的是所选模型减基线，避免把 WAPE 下降错误显示成负改善。

#### `scripts/build_portfolio_evidence.py`

新增确定的生成入口，一次写出：

- `reports/portfolio_evidence.json`：机器可读的统一证据；
- `reports/portfolio_case_study.md`：招聘方阅读案例；
- `reports/portfolio_artifact.json`：原生报告 payload。

脚本不训练模型、不查询外网，只读取当前已落盘产物。选择生成而不是手工写三份报告，是为了后续重训后只维护一个证据来源。

#### `scripts/validate_portfolio.py`

新增快速投递验收，实际检查：

- 已保存证据通过结构和业务规则校验；
- 从当前五类权威产物重新构建一份证据，去掉生成时间后必须与已保存版本完全相同；
- `reports/resume_bullets.md` 必须恰好 5 条编号 bullet；
- `docs/interview_guide.md` 必须恰好 20 个编号问题；
- README 和 docs 顶层 Markdown 的相对链接必须存在；
- 四张指定图片必须是有效 PNG，且不小于 1200×700；
- 输出结构化 JSON 结果，便于日志和 CI 读取。

这里没有用文件修改时间判断新鲜度，因为不同系统复制文件后时间戳不可靠；直接重建并比较内容更能发现口径漂移。仅排除 `generated_at_utc`，其他字段都必须完全一致。

#### `scripts/capture_dashboard_screenshots.mjs`

新增零第三方依赖的截图脚本。它通过 Node 自带 `fetch`、`WebSocket` 和 Chrome DevTools Protocol：

- 打开增长总览、商家运营行动、实验设计、数据质量四个本地地址；
- 等待对应 H1 标题真实出现在 DOM，而不是只等静态 HTML 返回；
- 固定 1440×1000 视口并捕获页面；
- 将结果写入 `docs/assets/portfolio/`；
- 页面 30 秒仍未出现标题时输出文档状态和 WebSocket 诊断，而不是保存加载骨架。

没有安装 Playwright、Selenium 或 websocket-client。本地检查确认这些库都不存在；根据项目规则，不能为了截图擅自安装。Node 26 已存在，因此用标准能力完成同样工作，新增脚本约束在本地调试地址，不包含密钥或外部上传。

#### `tests/test_portfolio.py`

新增 4 个测试：

1. 行动数为 3,051、商家分群为 3,095，且证据不含 `seller_priority`；
2. 实验规划重新得到 3,864 和 158，并确认没有 observed effect；
3. 人为把容量 200 改成 199、或人为加入 `observed_effect` 时必须失败；
4. 原生报告第一块标题与 manifest 一致，第二块为 Executive Summary，至少有图表块，所有数据集不超过 2,000 行。

测试没有断言新的业务效果，只断言已有产物的契约与公开边界。

### 3.3 Streamlit 入口修复

#### `streamlit_app.py`

新增项目根目录入口，只导入并调用 `app.app.main()`。根目录入口避免 `app/app.py` 作为脚本运行时把 `app` 解析为同名脚本，而不是 Python 包。

#### `app/app.py`

把原有顶层页面注册和渲染逻辑收进 `main()`。这不是业务页面重构，页面列表、标题、路径和渲染函数都保持不变。

必须增加显式函数的原因是：单纯在根目录写 `from app.app import *` 虽然解决包遮蔽，但 Streamlit/组件扫描或多会话中的 Python 模块缓存会让 `app.app` 只执行一次；后续会话只得到静态外壳，没有 UI delta。调用缓存模块中的 `main()` 可以保证每个 Streamlit 会话重新执行页面注册和 `navigation.run()`。

#### `Makefile`

修改与新增：

- `dashboard` 从 `streamlit run app/app.py` 改为 `streamlit run streamlit_app.py`；
- `portfolio-build` 生成三份作品集产物；
- `portfolio-check` 先生成、再校验、最后运行作品集和 10 页页面专项测试；
- `.PHONY` 同步新增目标。

脚本通过 `python -m scripts...` 执行，而不是 `python scripts/...py`。原因见本日志真实问题 4.1。

### 3.4 生成产物与截图

#### `reports/portfolio_evidence.json`

当前包含：

- 8,000 MQL、842 条成交记录、99,441 笔订单、112,650 条商品、99,224 条评价、3,095 个商家；
- 整体合法成交、GMV、延迟与低评分；
- 渠道和四个商家分群；
- 线索、低评分、品类需求、商家订单量和商家活动五个任务的基线/所选模型对照；
- 3,051 个可评分商家的五类行动数量和容量 200 的三策略对照；
- 以当前历史低评分率重新计算的实验规划；
- 14 条质量规则及有问题规则；
- 四条明确限制。

#### `reports/portfolio_case_study.md`

生成面向招聘方的案例报告，顺序为 Executive Summary、业务决策、模型证据、运营取舍、实验准备度、工程可信度、下一步和结论边界。它没有写“提高利润”“减少差评”或“产生 ROI”，只陈述离线证据和下一步验证条件。

#### `reports/portfolio_artifact.json`

生成原生报告，包括：

- 4 个有界 snapshot 数据集；
- 3 类顶层来源；
- 容量策略覆盖分组柱图；
- 商家分群 GMV 柱图；
- 模型与简单基线对照表；
- 每个图表/表格对应可运行的 DuckDB SQL 和指标定义；
- 开头匹配 manifest 标题的一级标题和紧随其后的 Executive Summary；
- 下一步与无真实干预/ROI 的限制。

#### `docs/assets/portfolio/*.png`

生成四张 1440×1000 PNG：

- `01_growth_overview.png`：显示 8,000 MQL、841 合法成交、10.5% 成交率和趋势图；
- `02_seller_ops_actions.png`：显示 3,051 可排期商家、158 个 P1、行动分布和离线边界；
- `03_experiment_design.png`：显示 158 个当前候选、3,864 个规划样本、每组 1,932 和 12.1% 当前 MDE；
- `04_data_quality.png`：显示 14 条质量规则、0 个 error 异常数、2,348 个 warn 记录总数和规则明细。

四张图片都经过文件格式检查和人工目视检查，没有保留最初错误生成的加载骨架。

### 3.5 收口文档

- `README.md`：增加作品集指南、案例、简历 bullet 入口；测试数改为 62；分析命令改为 Makefile 目标；增加 P12 结论和 `make portfolio-check`；
- `docs/06_validation_results_and_conclusions.md`：补充 P12 终验、入口问题、原生报告和截图结论；
- `docs/interview_guide.md`：增加五分钟演示与案例报告入口，原有 20 问保持不变；
- `docs/logs/README.md`：增加本日志索引。

## 4. 真实遇到的问题、定位与解决

### 4.1 直接执行脚本无法导入 `src`

#### 现象

第一次运行：

```bash
.venv/bin/python scripts/build_portfolio_evidence.py
```

报错：

```text
ModuleNotFoundError: No module named 'src'
```

#### 定位

直接执行位于 `scripts/` 下的文件时，Python 把 `scripts/` 放在首要模块路径，项目根目录没有按预期进入导入路径。现有 `export_analysis_snapshot.py` 没有导入 `src`，所以此前没有暴露这个问题。

#### 解决

Makefile 改为：

```bash
.venv/bin/python -m scripts.build_portfolio_evidence
.venv/bin/python -m scripts.validate_portfolio
```

没有在代码里动态修改 `sys.path`，也没有依赖调用者设置 `PYTHONPATH`。模块执行方式更明确、可复现。修改后生成脚本和 4 个新增测试通过。

### 4.2 原生报告结构第一次未通过校验

#### 现象与三次真实反馈

原生报告校验器依次指出：

1. `manifest.cards[0].title` 不受支持；
2. block 类型 `card` 不受支持，只允许 markdown、metric-strip、chart、table、html；
3. chart/table source 必须包含实际 SQL 查询文本。

#### 定位

初版把报告卡片当成普通前端组件设计，和原生报告 v1 的 schema 不一致。报告还只在顶层声明 JSON 来源，未为每个图表说明如何得到当前数据表。

#### 解决

- 删除非必要 headline card，避免为了四个数字增加复杂且重复的组件；
- 保留报告必须的 markdown、chart 和 table 阅读顺序；
- 为容量策略、商家分群和模型对照分别增加可在 DuckDB 中运行的 `read_json_auto` SQL、来源文件和指标定义；
- 容量策略 SQL 使用 `unnest` + `unpivot` 转为长表，和图表的 x/y/color 编码一致；
- 每次修改后只调用校验器，不用渲染器试错。

最终校验返回 `ok=true`，报告包含 4 个数据集、3 类来源，snapshot 状态为 ready。

### 4.3 `streamlit run app/app.py` 出现包遮蔽

#### 现象

用真实浏览器打开旧命令后，页面显示：

```text
ModuleNotFoundError: No module named 'app.components'; 'app' is not a package
```

#### 定位

入口文件路径是 `app/app.py`。在当前 Streamlit/Python 启动路径下，同名脚本 `app.py` 会遮蔽目录包 `app`，因此页面模块里的 `from app.components ...` 被解析到脚本而不是包。

#### 解决

新增项目根目录 `streamlit_app.py`，Makefile 改为运行该入口。这样项目根目录是导入基准，`app` 能解析为包。没有把各页面的绝对导入批量改成相对导入，因为那会扩大改动范围，并让页面作为 Streamlit callable 的行为更难维护。

### 4.4 只做根目录导入后，新会话仍只显示空壳

#### 现象

初版根入口使用 `from app.app import *`。静态页面和 WebSocket 都返回成功，Chrome 网络诊断显示 101 Switching Protocols 和 Streamlit 初始帧，但 DOM 只有 `Deploy`，没有业务标题。Streamlit debug 日志显示每个会话开始 Running script 后很快结束，没有页面 delta。

#### 定位

顶层导入依赖模块首次执行副作用。模块在同一 Python 进程中被缓存后，新会话再次执行根入口不会重新执行 `app.app` 的顶层页面注册。根入口虽然解决了包名，却没有保证每个会话都渲染。

#### 解决

把 `app/app.py` 的 UI 逻辑收进 `main()`，根入口每次显式调用 `main()`。页面定义和业务逻辑不变。重启服务后，四个页面的 H1 都能在几秒内出现，截图脚本一次完成四张图片。

### 4.5 第一次无头截图只得到加载骨架

#### 现象

直接运行 Chrome `--screenshot` 配合 `--virtual-time-budget` 得到约 8 KB 图片。人工查看后只有灰色加载骨架，没有任何业务数字。

#### 定位

Streamlit 先返回静态壳，再通过 WebSocket 接收页面 delta。虚拟时间会推进浏览器计时器，但不能替代真实后端会话完成；“Chrome 命令退出成功”和“图片是 PNG”都不能证明页面已经渲染。

#### 解决

- 删除/覆盖这张错误图片，不把它作为交付；
- 截图脚本改为等待指定 H1 进入 DOM；
- 加入 30 秒超时和 WebSocket/DOM 诊断；
- 截图后同时做 `file` 检查、尺寸检查和人工目视检查。

### 4.6 本地服务绑定范围被安全检查拒绝

#### 现象

一次 Streamlit 启动命令没有指定绑定地址，系统拒绝执行，理由是可能显示 Network/External URL，与“仅本机监听”的授权不一致。

#### 解决

改为显式：

```bash
--server.address 127.0.0.1 --server.port 8767
```

后续 Chrome 调试接口也显式绑定 `127.0.0.1:9222`。没有绕过安全限制，也没有把本地项目暴露到局域网或外网。

### 4.7 浏览器插件与本机回环环境隔离

#### 现象

应用内浏览器和 Chrome 扩展控制能访问静态外壳，但无法稳定复用本机回环服务完成截图；普通 Chrome 一次性截图又不能等待 WebSocket 页面完成。

#### 解决

使用本机 Chrome 无头进程和 DevTools Protocol，截图脚本与 Streamlit 都在同一本机网络空间。诊断时确认 WebSocket 成功升级、收到帧；最终问题并非网络，而是 4.4 的模块缓存。修复 `main()` 后脚本一次通过。

这部分没有修改系统代理，没有安装浏览器扩展，没有上传截图。

## 5. 实际运行命令与结果

以下为本阶段实际执行的主要命令。失败命令保留在日志中，避免只记录最终成功路径。

### 5.1 初次生成与新增测试

失败：

```bash
.venv/bin/python scripts/build_portfolio_evidence.py
```

结果：`ModuleNotFoundError: No module named 'src'`。

修复后：

```bash
.venv/bin/python -m scripts.build_portfolio_evidence
.venv/bin/python -m pytest tests/test_portfolio.py -q
```

结果：三份报告产物生成；4 项新增测试通过。

### 5.2 原生报告校验

通过 Data Analytics 原生报告校验器对完整 manifest 和 bounded snapshot 做校验。初版三次收到 schema/source 错误并逐项修复，最终结果：

```text
ok=true
surface=report
dataset_count=4
source_count=3
snapshot_status=ready
```

校验前没有调用正式渲染；最终校验通过后才进入交付渲染。

### 5.3 Streamlit 和截图

最终本地服务命令：

```bash
.venv/bin/streamlit run streamlit_app.py \
  --server.headless true \
  --server.address 127.0.0.1 \
  --server.port 8767 \
  --browser.gatherUsageStats false
```

本机 Chrome 调试接口只监听 `127.0.0.1:9222`。最终截图命令：

```bash
node scripts/capture_dashboard_screenshots.mjs
```

结果：4/4 页面成功，均为 1440×1000。

文件复验：

```bash
file docs/assets/portfolio/*.png
du -h docs/assets/portfolio/*.png
```

结果：四个文件均为 PNG、RGB、非隔行，尺寸 1440×1000；单文件约 128–196 KB。随后逐张目视确认标题、关键数字、免责声明和图表存在。

### 5.4 快速作品集验收

```bash
make portfolio-check
```

实际结果：

```text
portfolio_evidence_v1
resume_bullets=5
interview_questions=20
screenshots=4 × 1440x1000
broken_links=0
17 passed
```

17 项由 4 个作品集证据测试和 13 个 Streamlit 页面/路由测试组成。该命令不重训模型，也不重建 dbt。

### 5.5 全量回归

```bash
.venv/bin/python -m pytest -q
.venv/bin/dbt --no-version-check build --project-dir dbt --profiles-dir dbt
```

结果：

- Python：62 项全部通过；
- dbt 版本：core 1.12.0、duckdb adapter 1.10.1；
- 发现 29 个模型、57 个数据测试、9 个 sources；
- 总计 86 个节点，耗时 3.31 秒；
- `PASS=84 WARN=2 ERROR=0 SKIP=0`；
- 两个保留告警仍是 1 条成交早于首次接触和 189 条订单时间异常，没有新增错误或修改告警严重级别。

### 5.6 依赖与系统影响检查

本阶段确认当前虚拟环境没有 Selenium、Playwright、websocket-client，但没有安装它们。截图使用已安装 Chrome、已有 Node 26 和项目内脚本。没有修改系统 Python、系统代理、浏览器默认配置或项目锁定依赖。

## 6. 文档验收

按“读者不看代码，只看 docs/”重新检查后，当前文档可以回答：

1. 项目为何存在、目标岗位与成功标准：`00_project_charter.md`；
2. 功能、指标口径和验收条件：`01_requirements_and_metrics.md`、`metric_dictionary.md`；
3. 数据流、模块关系与技术取舍：`02_solution_architecture.md`；
4. 数据来源、表关系、质量、许可和隐私：`03_data_design.md`、数据卡；
5. 模型标签、特征、时间切分、基线、泄漏和误差：`04_model_and_experiment_design.md`、三份模型卡；
6. 实际实现、结果、真实问题、结论与局限：`06_validation_results_and_conclusions.md` 和阶段日志；
7. 真实干预还缺什么、为什么当前不能说有效：`07_intervention_and_experiment_design.md`；
8. 如何做 30 秒介绍、五分钟演示、不同岗位取舍：`08_portfolio_demo_guide.md`；
9. 需求如何映射到文件、测试和证据：`traceability.md`；
10. 如何回答 20 个常见面试问题：`interview_guide.md`。

内部链接自动检查结果为 0 个无效链接。案例报告和 README 为招聘方快速入口；详细日志保留失败路径和修复依据，不需要读者猜测 3,864、79.40% 或模型结果从何而来。

## 7. 当前局限、风险和下一步

### 7.1 仍存在的局限

1. 证据包依赖当前已生成的 artifacts；新机器需要先按 README 运行数据和模型流程；
2. `portfolio-check` 是快速投递验收，不会重训模型，也不会重建 dbt；全量重现仍用 `make verify`；
3. 截图是 2026-08-02 的静态快照，页面或数据产物改变后要重新运行截图脚本；
4. Chrome 调试截图脚本假设本机已有 Chrome 和 Node，README 的核心项目复现不依赖该脚本，但重新截图需要相同能力；
5. 原生报告是当前证据的阅读层，不是线上监控系统，没有自动刷新或云端分享；
6. 项目仍是 2016–2018 年公开匿名历史数据，缺少成本、利润、库存、促销、曝光和真实干预结果；
7. 62 个测试和 dbt 0 error 证明当前实现契约通过，不证明现实业务中模型仍有效；
8. 低评分、延迟和渠道差异仍是相关性证据，不是因果结论。

### 7.2 对模型提升的结论没有改变

P12 没有提供继续调参的新证据。线索和低评分模型可以支持离线排序；品类需求有小幅改善；商家订单量误差仍高。真正有业务价值的下一步仍是接入真实动作日志、跨周积累成熟样本并按预注册口径做 ITT，而不是在同一历史测试集继续搜索更高分。

### 7.3 推荐下一步

若项目只用于岗位投递：冻结当前模型和数字，针对具体 JD 选择五分钟路线，并在投递前运行 `make portfolio-check`。

若能获得真实业务环境：优先完成以下顺序：

1. 确认动作 owner、触达渠道、单位成本和执行 SLA；
2. 把 P11 四表接入真实执行系统；
3. 跨周滚动入组，等待统一成熟窗；
4. 先检查分组平衡、执行率、污染和成熟率；
5. 按预注册主指标和护栏做 ITT；
6. 只有实验结果和成本完整后再讨论增量、利润或 ROI。

本阶段不存在真实运营上线、真实干预效果或真实收益，日志与报告均未声称这些结果。
