# P14 GitHub 托管 CI 数据隔离修复日志

## 1. 阶段目标

修复首次公开推送后 GitHub Actions 在“Run Python tests”失败的问题，使页面测试在没有 Olist 原始 CSV、DuckDB 和被忽略模型产物的 runner 中仍可重复执行，同时保留真实数据本地集成验收。

本阶段只修改测试与验证文档，不改变业务指标、模型、真实数据产物或看板展示逻辑。测试用微型数据明确属于合成 fixture，不进入业务报告，不替代真实数据结果。

## 2. 首次托管运行的真实结果

- 仓库与分支：`luyan9513/olist-growth-ops-intelligence`，`main`；
- commit：`98a9392`；
- GitHub Actions run：`30891909430`；
- Checkout、Python 3.12、依赖安装、仓库检查、dbt parse 均通过；
- Python 测试步骤失败，共 7 项失败。

失败分为两类：

1. `growth`、`channel`、`sellers`、`delivery`、`quality` 直接调用 `load_mart`，干净 runner 没有 `data/processed/olist.duckdb`，抛出 `FileNotFoundError`；
2. `ops_actions` 和 `experiments` 在 artifacts 缺失时按设计返回空表并提前展示提示，但测试仍断言真实数据环境中的指标卡存在，因此失败。

本地此前 64 项通过，是因为本机恰好存在被 `.gitignore` 排除的 DuckDB 和 artifacts。由此证明 P13“全量 Python 已与 ignored artifacts 隔离”的表述只对作品集证据测试成立，没有覆盖页面测试，是一次真实的验收缺口。

## 3. 修复设计

1. 主应用测试明确把数据库路径指向不存在的临时路径，验证无数据时显示准备说明且不抛异常；
2. 10 个页面测试不读取本机或 CI 文件系统，统一注入确定性的最小 DataFrame/JSON；
3. fixture 仅提供页面渲染所需字段和极少行数，不复制真实订单、卖家或模型明细；
4. 商家行动与实验页面仍运行真实容量、样本量、分组和平衡函数，只把输入替换为合成小表；
5. 真实 DuckDB、artifacts、模型新鲜度、真实截图继续由 `make dbt-build`、`make portfolio-check` 和本地浏览器验收负责。

与“在 CI 下载原始数据”“提交 DuckDB”“直接跳过全部页面测试”相比，该方案同时守住许可/体积边界和页面契约覆盖。

## 4. 修改文件

### `tests/streamlit_fixtures.py`

- 新增仅供 Streamlit 测试使用的微型合成 mart、模型预测、模型指标和商家行动输入；
- 覆盖 5 个 DuckDB 页面和 5 个 artifacts 页面所需字段；
- 商家行动使用 4 个 `fixture_seller_*`，保证实验 MDE 函数满足最小样本输入；
- 所有 ID、日期和数字都明确为 fixture，不复制真实卖家、订单或线索明细；
- `patch_page_data` 只替换页面模块已经导入的数据读取函数，不改生产代码。

### `tests/test_streamlit_pages.py`

- 主应用测试不再依赖本机数据库是否存在，而是强制指向不存在路径并断言“尚未找到数据仓库”；
- 10 页参数化测试统一调用 `page_source` 注入合成数据；
- 行动页继续断言容量指标、明细和非因果警告；
- 实验页继续断言候选量、规划样本、MDE 和“规划中、未启动”；
- 没有简单 skip 页面测试，也没有降低原有 13 项页面测试数量。

### `README.md` 与 `CONTRIBUTING.md`

- 解释无数据主应用测试、合成页面契约测试和真实本地集成验收的差别；
- 明确禁止把 fixture 数字写进业务报告。

### `docs/05_implementation_plan_and_risks.md`

- 新增 P14 阶段和 R-39“本地数据掩盖 CI 依赖”风险。

### `docs/06_validation_results_and_conclusions.md`

- 记录首次托管失败、本地无数据库复验和合成 fixture 边界。

### `docs/09_release_and_role_packaging.md`

- 更正“本地等价 CI 通过”不能等同托管 runner 通过，并链接本日志。

### `docs/traceability.md` 与 `docs/logs/README.md`

- 增加 NFR-15 和本阶段日志索引；最终托管结果出来后再关闭状态。

### `docs/logs/2026-08-04_git_initial_publish.md`

- 回填实际 commit、推送和首次 Actions 失败，不保留“将在未来填写”的占位状态。

### `reports/portfolio_evidence.json` 与 `reports/portfolio_artifact.json`

- `make portfolio-check` 重新生成时间戳，业务数据、模型数字和结论未变化。

## 5. 真实问题、命令与结果

### 5.1 GitHub Actions 失败定位

```bash
gh run view 30891909430 --json name,workflowName,conclusion,status,url,event,headBranch,headSha,jobs
gh run view 30891909430 --log-failed
```

结果：quality job 只有 Python 测试步骤失败，7 项失败均来自 `tests/test_streamlit_pages.py`；数据库页面抛 `FileNotFoundError`，行动/实验页面因 artifacts 为空未渲染指标。

### 5.2 页面专项测试

```bash
.venv/bin/python -m pytest tests/test_streamlit_pages.py -q
```

结果：13 项全部通过。

### 5.3 不存在数据库路径下的 CI 等价测试

```bash
OLIST_DB_PATH=/private/tmp/olist_ci_missing.duckdb make ci
```

结果：仓库检查 169 个候选文件、0 错误；dbt parse 通过；64 项 Python 测试全部通过，用时 4.91 秒。该命令显式排除了本机 DuckDB 对测试的帮助。

### 5.4 真实作品集回归

```bash
make portfolio-check
```

结果：证据生成与对账通过，5 条通用 Bullet、20 个面试问题、0 个无效链接、4 张 1440×1000 图片通过；作品集与页面专项共 17 项通过。

文档全部更新后再次串联运行同两条命令，最终结果仍为 169 个候选文件、64 项 Python 全部通过（4.57 秒）、17 项专项通过、0 个无效链接；`git diff --check` 无空白错误。

### 5.5 本阶段真实问题

除首次托管 CI 已记录的 7 项失败外，本地修复和复验未遇到新的阻塞问题。页面 fixture 第一次实现即通过 13 项专项；未虚构额外调试过程。

## 6. 局限与下一步

- 合成 fixture 只能证明页面输入契约和组件渲染，不能证明真实指标正确；
- CI 成功后仍不能替代真实数据的 dbt、模型和截图验收；
- 当前工作流只有 CI，没有自动部署，因此不称完整 CD。
