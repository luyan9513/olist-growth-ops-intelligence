# P13 发布、视觉与岗位定制完善开发日志

## 1. 阶段信息

- 日期：2026-08-02
- 阶段：P13 发布、视觉与岗位定制完善
- 工作目录：`olist-growth-ops-intelligence`
- 数据状态：沿用已下载并验证的 11 个 Olist 公开历史 CSV；本阶段没有下载新数据
- 模型状态：沿用 P8/P9 已验证模型产物；本阶段没有训练、调参或改写模型结果
- 阶段目标：补齐无数据 CI、仓库发布卫生、看板展示一致性、四类岗位材料、真实业务落地闸门和完整文档验收
- 结果边界：仍无真实干预、渠道成本、利润和线上运行数据，不产生或宣称真实 ROI、增量成交、降低差评或线上收益

## 2. 开发前检查与方案依据

### 2.1 先检查的现状

开发前先读取了现有 Makefile、`pyproject.toml`、作品集测试、10 个 Streamlit 页面、README、P12 演示指南、验证结论、追溯矩阵、日志索引和第三方声明。检查结果是：

1. P12 已有 62 项 Python 测试、29 个 dbt 模型、57 项 dbt 测试和四张真实截图；
2. `tests/test_portfolio.py` 会直接读取被 `.gitignore` 排除的 `artifacts/`，干净 GitHub runner 无法执行全量 Python 测试；
3. 看板功能完整，但多个页面的默认多选框直接占用 sidebar，图表标题和比例轴格式不统一；
4. 只有一组通用简历 Bullet，没有按数据分析、增长分析、商业分析和电商运营分析四类岗位分别组织；
5. 已有实验设计，但缺少真实组织如何接入 owner、数据契约、权限、执行和结果闸门的独立手册；
6. 当前 Git 状态中项目文件全部显示为 `??`，说明尚未形成可对比的已跟踪基线。本阶段不能把“有 CI 文件”写成“GitHub CI 已真实运行”，也不能凭空制造提交历史。

### 2.2 核对的官方资料

- GitHub 官方 `actions/checkout`：当前主版本 v6；
- GitHub 官方 `actions/setup-python`：当前主版本 v6，支持显式 Python 版本和 pip 缓存；
- GitHub 官方 Python 构建文档：确认 pytest/依赖缓存的工作流写法；
- Streamlit 官方配置和主题文档：确认 `.streamlit/config.toml`、sidebar 主题、边框、颜色和图表颜色配置；
- 本机 Streamlit 1.60.0 的 `streamlit config show`：确认 `toolbarMode`、`baseRadius`、`showSidebarBorder`、`chartCategoricalColors` 等配置项实际存在。

选择官方主题和原生 expander，而不是注入针对内部 DOM/testid 的 CSS，原因是后者会随 Streamlit 升级变脆，且容易隐藏重要提示。本阶段没有安装新依赖。

## 3. 新增文件及每个文件的具体作用

### 3.1 仓库、CI 与发布文件

#### `.python-version`

- 固定 Python 主次版本为 3.12，使本地说明与 GitHub Actions 一致；
- 不固定补丁版本，避免 runner 暂时没有某个补丁版本时无必要失败。

#### `.github/workflows/ci.yml`

- 新增 push、pull request 和手动触发的 CI；
- 使用 `actions/checkout@v6`、`actions/setup-python@v6`；
- 权限限制为 `contents: read`，避免默认获得不需要的写权限；
- 使用 requirements 文件作为 pip 缓存键；
- 依次执行仓库检查、dbt parse 和全量 Python 测试；
- 设置 20 分钟超时和同分支取消旧任务，减少重复资源消耗。

没有在 CI 中下载 Olist 数据或运行全量模型，原因是原始数据、DuckDB 和模型产物按许可与体积边界不进入仓库。CI 的职责是验证代码与版本化证据契约，不冒充真实数据全流程。

#### `.github/pull_request_template.md`

- 要求改动说明业务问题、文件、指标口径是否变化；
- 列出仓库、dbt、Python、看板与文档验证检查项；
- 强制提醒不能提交数据/模型/密钥，不能把离线结果写成因果效果。

#### `.github/ISSUE_TEMPLATE/bug_report.yml`

- 提供结构化缺陷模板，要求问题现象、复现步骤和脱敏证据；
- 明确禁止粘贴密钥或个人信息。

#### `CONTRIBUTING.md`

- 说明开发流程、提交前命令、指标口径同步规则、数据边界和模型泄漏约束；
- 说明 CI 不能替代本地真实数据验证。

#### `RELEASE_CHECKLIST.md`

- 把发布检查拆成自动验证与人工确认；
- 将自有代码许可证、数据条款、隐私、真实地址和结果措辞列为人工闸门；
- 明确没有自动创建远端仓库、公开部署或真实干预结果。

#### `CHANGELOG.md`

- 记录 1.0.0 本地作品集里程碑包含的数据、模型、决策、实验、CI 和岗位材料；
- 明确版本记录不代表线上业务效果。

#### `scripts/validate_repository.py`

- 使用 `git ls-files --cached --others --exclude-standard` 获取真正可能进入版本控制的文件，而不是遍历 `.venv` 或被忽略的本地数据；
- 检查必需发布文件、禁止的数据/模型路径、DuckDB/joblib/pickle/Parquet、`.env`/`secrets.toml`、5 MiB 文件上限和常见私钥头；
- 解析 CI YAML，确保语法可读取；
- 自动检查四类岗位每类恰好 5 条 Bullet；
- 输出结构化 JSON，并明确该脚本不能替代人工隐私审核。

#### `tests/test_repository.py`

- 把仓库发布卫生纳入 pytest；
- 验证检查状态、候选文件数量和错误列表。

### 3.2 看板主题与测试文件

#### `.streamlit/config.toml`

- 使用内置浅色主题、蓝/青/橙/红/紫的业务配色；
- 配置主背景、次背景、文字、链接、圆角、sidebar 边框和图表颜色；
- toolbar 使用 viewer 模式；
- 不加载外部字体，不新增网络和隐私依赖。

#### `app/theme.py`

- 统一 Plotly 白底主题和离散颜色；
- 提供 `polish_figure`，统一边距、网格、字体、图例与百分比轴；
- 为数据质量 error/warn 固定红/橙颜色；
- 最终比例轴保留两位百分比，避免 0.19% 等真实小异常率显示成 0%。

#### `tests/test_theme.py`

- 验证统一色板确实写入 Plotly 默认值；
- 验证比例轴格式和图表上边距，防止后续回归。

### 3.3 岗位材料和落地配置

#### `reports/resume_bullets_by_role.md`

- 分别为数据分析、增长分析、商业分析、电商运营分析提供 3 条推荐和 2 条备选，共 20 条；
- 数据均来自 `reports/portfolio_evidence.json`：8,000 MQL、99,441 订单、3,095 商家、84/2/0 dbt 结果、模型基线对照、199 个高价值高风险商家、3,051 行行动清单等；
- 每一版都保留公开历史数据、离线排序和非 ROI 边界；
- 没有编造真实团队职责、上线采用或业务收益。

#### `reports/jd_tailoring_checklist.md`

- 指导每次投递只选择 3 条，与具体 JD 的渠道、履约、指标、实验等关键词映射；
- 要求所有数字可追溯、不能把 GMV 写成收入/利润、不能声称未发生的上线或团队职责。

#### `configs/rollout_readiness.yml`

- 用机器可读状态记录业务 owner、线上数据契约、隐私审批、干预动作、实验登记、执行日志和因果结果七类闸门；
- 当前状态如实标为 `pending_real_environment`、`template_only` 或 `not_available`；
- 在闸门未全部通过前，明确禁止真实 ROI、增量成交、降低差评和已上线收益宣称。

### 3.4 新增设计与业务文档

#### `docs/09_release_and_role_packaging.md`

- 在业务代码前先固定 P13 目标、非目标、仓库包含/排除内容、CI/本地边界、看板原则和岗位材料原则；
- 增加 GitHub Actions 与 Streamlit 官方文档链接和核对日期；
- 阶段结束后补入实际 64 项 Python、17 项专项、84/2/0 dbt、167 个最终候选文件和四张截图结果。

#### `docs/10_real_world_rollout_playbook.md`

- 说明当前只是离线作品集，不是已上线系统；
- 定义业务 owner、运营执行、数据分析、数据工程、风控/法务最小职责；
- 列出登记、资格快照、发布分组、执行、成熟结果和质量六类输入；
- 给出 0–30 天影子运行、31–60 天小流量可行性、61–90 天跨周累计与正式分析；
- 定义串组、未成熟记 0、动作不一致、护栏恶化等停止条件；
- 只有真实日志、成本和收益口径齐全后才允许讨论 ROI。

## 4. 修改文件及每个文件的具体作用

### 4.1 测试、命令与版本

#### `tests/test_portfolio.py`

- 将 fixture 从被忽略的 `artifacts/*` 改为读取版本化的聚合证据 `reports/portfolio_evidence.json`；
- 仍保留行动数量、商家分层、实验无 observed effect 和有界报告数据集检查；
- 这样干净 CI 可以运行全部 Python 测试，真实 artifacts 新鲜度仍由本地 `make portfolio-check` 验证。

#### `Makefile`

- 新增 `repo-check`：执行仓库卫生检查；
- 新增 `ci`：依次执行 repo-check、dbt parse 和全量 Python 测试；
- 保留 `portfolio-check` 和 `verify` 的不同职责，没有用快速检查替代真实全流程。

#### `pyproject.toml`

- 将本地作品集里程碑版本从 0.1.0 更新为 1.0.0；
- 许可证字段仍明确指向作品集边界和第三方声明，没有擅自写 MIT。

### 4.2 Streamlit 入口和页面

#### `app/app.py`

- 在页面配置后加载统一 Plotly 默认主题；
- sidebar 增加“10 个分析页面·本地只读作品集”，让展示属性和边界更清楚。

#### `app/pages/growth.py`

- 将来源和日期放入默认折叠的“增长筛选”；
- 将指标系列改为中文；
- 增加“月度线索与成交趋势”“各渠道历史成交率”标题；
- 成交率使用统一比例轴。

#### `app/pages/channel.py`

- 为渠道散点图增加“渠道成交规模与后续经营质量”标题；
- 应用统一图表样式，继续保留无成本不算 ROI 的说明。

#### `app/pages/sellers.py`

- 将卖家州放入默认折叠的“商家筛选”；
- 增加 GMV 趋势和价值×风险分布标题；
- 延迟率按统一百分比展示。

#### `app/pages/delivery.py`

- 为品类/地区履约拆解图增加明确标题；
- 延迟率轴改为百分比，保留低评分率作为颜色。

#### `app/pages/leads.py`

- 为测试集分数直方图增加标题；
- 将是否成交的图例名称中文化；
- 不改变模型分数、Top-K 指标或离线标签边界。

#### `app/pages/demand.py`

- 将预测粒度放入默认折叠筛选；
- 将 actual 和模型名映射为“实际订单量”“预测：模型名”；
- 增加按品类/商家变化的回测标题；
- 没有弱化商家 WAPE 高和不用于补货的限制。

#### `app/pages/ops_actions.py`

- 将行动类型和卖家州放入默认折叠筛选；
- 为行动规模、策略覆盖取舍、入选商家活动概率×历史价值三张图增加标题；
- 覆盖率和活动概率使用统一比例轴；
- 仍同时展示风险覆盖与单目标排序代价，没有只展示对统一规则有利的指标。

#### `app/pages/experiments.py`

- 将 treatment/control 图例改为处理组/对照组；
- 增加草案分组平衡标题；
- 保留“规划中、未启动”和样本量不足说明。

#### `app/pages/quality.py`

- 使用固定 error 红色、warn 橙色；
- 增加“各质量规则异常率”标题；
- 比例轴最终保留两位百分比，以显示 0.01%–1.42% 的真实异常范围。

`app/pages/scenario.py` 没有图表和 sidebar 默认筛选，不做无关修改；其历史模拟、假设成本和非 ROI 边界保持不变。

#### `scripts/capture_dashboard_screenshots.mjs`

- 在检测到页面标题后继续等待 skeleton 和运行状态控件消失；
- 连续两次稳定后强制 `window.scrollTo(0, 0)`，再等待 750ms；
- 解决页面滚动位置残留和输入组件半加载截图问题；
- 保留 1440×1000 和四个固定路由。

#### `docs/assets/portfolio/01_growth_overview.png`

- 用最终主题和真实数据重新生成增长总览截图。

#### `docs/assets/portfolio/02_seller_ops_actions.png`

- 用最终主题和真实行动清单重新生成运营行动截图。

#### `docs/assets/portfolio/03_experiment_design.png`

- 等待所有输入组件加载后重新生成实验设计截图。

#### `docs/assets/portfolio/04_data_quality.png`

- 以两位百分比轴和真实 14 条规则重新生成数据质量截图。

四张图片均为 1440×1000、8-bit RGB、非交错 PNG，已逐张目视检查。

### 4.3 说明、追溯与发布文档

#### `README.md`

- 当前状态加入无数据 CI 和仓库检查；
- 增加 P13 两份文档、四岗位 Bullet 和 JD 清单入口；
- 增加 `make repo-check`、`make ci` 及其与真实全流程的区别；
- 更新为 64 项 Python 测试；
- 增加 P13 成果摘要；
- 明确远程 Actions 引用、自有代码许可证未决定和不得宣称 MIT。

#### `THIRD_PARTY_NOTICES.md`

- 将状态更新至 2026-08-02；
- 记录 `actions/checkout@v6`、`actions/setup-python@v6` 的上游 URL、引用版本、MIT 许可证、未复制源文件和未修改；
- 保留 Olist 数据许可和未复用参考项目说明。

#### `docs/00_project_charter.md`

- 在求职成功标准中增加无数据 CI、仓库卫生和四岗位材料；
- 明确远端仓库、公开部署和真实业务接入尚未发生。

#### `docs/01_requirements_and_metrics.md`

- 开发前增加 FR-16 仓库/CI、FR-17 岗位材料、FR-18 看板展示、NFR-13 无数据 CI、NFR-14 发布/许可克制；
- 这些要求先于实现写入，避免开发后倒推验收标准。

#### `docs/02_solution_architecture.md`

- 增加 repo-check → GitHub Actions → 本地真实数据验收 → 人工发布闸门的三层验证架构；
- 解释 CI 为什么不读取原始数据和模型产物。

#### `docs/03_data_design.md`

- 增加公共仓库可版本化/不可版本化边界；
- 说明 5 MiB、路径、扩展名和私钥检查能力与限制；
- 提醒真实业务必须重新做权限和保存周期治理。

#### `docs/04_model_and_experiment_design.md`

- 新增 P13 模型冻结说明；
- 明确本阶段不改标签、特征、切分、选模和模型结果，展示证据不能替代模型新鲜度验证。

#### `docs/05_implementation_plan_and_risks.md`

- 开发前新增 P13 阶段、实施顺序和 R-35 至 R-38 风险；
- 完成后更新为实际 64 项 Python、17 项专项、84/2/0 dbt 和四张实图；
- 保留不制造许可证、Git 历史和实验效果的边界。

#### `docs/06_validation_results_and_conclusions.md`

- 更新当前 Python 测试总数；
- 新增 P13 仓库、视觉、岗位材料、真实问题和未完成外部动作的验收结论；
- P12 章节仍保留当时 62 项测试，作为历史阶段记录，不把过去结果改写成 64。

#### `docs/08_portfolio_demo_guide.md`

- 说明截图已在 P13 统一主题后重新生成；
- 增加四岗位材料、发布和真实落地证据入口；
- 演示前增加 `make repo-check`。

#### `docs/interview_guide.md`

- 在演示入口增加四岗位 Bullet、JD 检查清单和真实业务落地手册。

#### `docs/traceability.md`

- 开发前增加 FR-16/17/18 映射；
- 完成后回填具体文件、命令、167 个最终候选文件、64 项测试、4 张截图和完成状态；
- 文档验收索引增加发布与真实落地入口。

#### `docs/logs/README.md`

- 增加本 P13 日志到时间顺序索引。

#### `reports/portfolio_evidence.json`

- `make portfolio-check` 从当前 artifacts 重新生成，业务数字没有因 P13 改变；
- 生成时间更新，继续作为无数据 CI 的聚合证据。

#### `reports/portfolio_case_study.md`

- 由作品集构建命令重新生成，确保案例数字与证据包一致。

#### `reports/portfolio_artifact.json`

- 由作品集构建命令重新生成，保持原生可视化报告与当前证据一致。

## 5. 为什么采用这些方案而不是其他方案

### 5.1 CI 只做无数据契约，不在 runner 下载全量数据

原始数据受 CC BY-NC-SA 4.0 边界约束且不进入 Git，模型产物和 DuckDB 体积较大。让公共 CI 自动下载 Kaggle 数据还会引入凭证、网络波动和许可风险。因此 CI 验证代码、dbt 解析、页面和聚合证据，本地 `make verify`/`dbt build` 承担真实数据复现。

### 5.2 版本化聚合证据，而不是提交逐对象预测

作品集测试只需要验证数量、结构和结论边界，不需要订单/商家级明细。聚合证据可审阅、体积小且不暴露细粒度对象；新鲜度问题由本地生成与对账命令解决。

### 5.3 原生主题和折叠筛选，而不是大段 CSS

官方配置可跨页面统一生效，升级风险更低。默认折叠保留全部筛选能力，也让招聘方第一屏先看到结论而不是长多选框。

### 5.4 分岗位改写同一组事实，而不是制造四个项目版本

不同岗位只是阅读重点不同，事实不能变化。四版各自突出数据治理、增长排序、商业取舍或履约运营，但数字全部来自同一证据包，避免为匹配 JD 夸大个人贡献。

### 5.5 真实落地用闸门状态，而不是填示例“成功结果”

当前没有真实组织、执行和结果数据。使用 `pending_real_environment` 等状态能够展示落地思考，同时不把模板行或假设写成真实业务成果。

### 5.6 不自动添加 MIT LICENSE、远端仓库或公开部署

自有代码许可证具有法律效果，且 Olist 数据本身是 CC BY-NC-SA 4.0；应由仓库所有者确认兼容边界。创建远端仓库、推送和部署属于外部状态变更，也需要真实账号与地址。因此本阶段把文件、检查和清单准备好，但没有虚构为已发布。

## 6. 遇到的真实问题、定位和解决

### 问题 1：仓库检查第一次把说明文件和脚本自身误判为风险

**现象：** 首次运行 `python -m scripts.validate_repository` 失败，报告 `artifacts/.gitkeep`、`data/raw/.gitkeep`、`data/processed/.gitkeep`、`data/raw/README.md` 为禁止产物，并在检查脚本自身发现三条私钥标记。

**定位：** 路径规则过宽，所有 `data/raw/`、`data/processed/`、`artifacts/` 文件都被拒绝；脚本常量本身包含需要查找的私钥头文本，因此自检必然命中。

**解决：** 只允许四个明确的占位/说明文件，不放宽其他数据文件；文本扫描排除检查脚本自身。修复时复跑 166 个候选文件通过，加入本阶段日志后最终为 167 个，错误列表为空。

### 问题 2：沙箱不允许直接绑定本机 Streamlit 端口

**现象：** 首次执行 Streamlit 绑定 `127.0.0.1:8767` 报 `PermissionError: [Errno 1] Operation not permitted`。

**定位：** 不是代码或依赖错误，而是当前受限环境禁止监听端口。

**解决：** 按权限流程请求允许后，仍只绑定回环地址 `127.0.0.1`，没有对局域网或公网开放。服务成功启动，截图结束后已停止。

### 问题 3：无头 Chrome 命令两次因 shell 引号失败

**现象：** 第一次 `--remote-allow-origins=*` 被 zsh 当 glob，报 `no matches found`；第二次可执行文件路径没有整体加引号，空格导致 `no such file or directory: /Applications/Google`。

**定位：** 两次都是命令行转义问题，不是 Chrome 缺失。

**解决：** 对通配参数和完整应用路径分别加引号。Chrome 最终在 `127.0.0.1:9222` 启动，截图后用 Ctrl-C 停止。

### 问题 4：第一轮截图存在比例舍入、滚动位置和加载骨架

**现象：** 数据质量图 0.1% 级异常率显示为多个“0%”；商家行动页标题上沿被截；实验页部分 selectbox 仍是灰色加载骨架。

**定位：** `.0%` 精度不足；CDP 新 target 仍可能继承页面滚动状态；仅等待 H1 出现不足以保证 Streamlit 所有组件完成渲染。

**解决：** 百分比格式先改为一位，目视仍不足后最终改为两位；截图脚本等待 skeleton/运行控件连续两次为 0，强制滚动到顶部并额外等待 750ms。重新生成后，四页均从顶部开始、输入控件完整、质量图可显示 0.20% 等刻度。

### 问题 5：Streamlit 提示缺少 Watchdog

**现象：** 本地服务提示安装 Watchdog 可获得更好的开发性能。

**判断与处理：** 这是可选性能提示，不影响页面加载、测试或截图。本阶段没有因提示新增依赖，避免未经确认安装非必要组件。

除以上问题外，本阶段未遇到阻塞问题。dbt 的 1 条成交时间倒置和 189 条订单时间顺序异常是已知真实数据告警，不是 P13 新回归，也没有被隐藏或删除。

## 7. 实际运行命令与结果

### 7.1 配置能力核对

```bash
.venv/bin/streamlit config show | rg -n "toolbarMode|baseRadius|showSidebarBorder|chartCategoricalColors|linkColor|primaryColor|font =|backgroundColor"
```

结果：本机 Streamlit 1.60.0 确认所用配置项存在。

### 7.2 仓库检查首次失败与修复后复验

```bash
.venv/bin/python -m scripts.validate_repository
```

首次结果：失败，出现 4 个允许说明/占位文件误报和 3 个脚本自检误报。修复后结果：`status=pass`；写入本日志前候选文件 166，最终复验为 167，错误 0，单文件上限 5 MiB。

### 7.3 中间全量 Python 回归

```bash
make repo-check && .venv/bin/python -m pytest -q
```

结果：仓库检查通过；64 项 Python 测试全部通过。

### 7.4 本地真实页面与截图

```bash
.venv/bin/streamlit run streamlit_app.py --server.headless true --server.address 127.0.0.1 --server.port 8767
```

沙箱内首次失败，获准后本机回环地址启动成功。

```bash
'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  --headless=new \
  --remote-debugging-port=9222 \
  '--remote-allow-origins=*' \
  --user-data-dir=/private/tmp/olist-p13-chrome \
  --no-first-run \
  --no-default-browser-check \
  about:blank

node scripts/capture_dashboard_screenshots.mjs
```

结果：最终四张截图均生成成功，尺寸都是 1440×1000；最后一轮已目视确认。截图流程结束后 Streamlit 和 Chrome 均已停止，端口不再监听。

### 7.5 最终三层验收

```bash
make ci && make portfolio-check && make dbt-build
```

实际结果：

1. `make ci`
   - 仓库检查：首次完整串联时 166 个候选文件，0 错误；写入本日志后最终复验为 167 个，0 错误；
   - dbt parse：通过；
   - pytest：64 passed，5.45 秒。
2. `make portfolio-check`
   - 重新生成 `portfolio_evidence.json`、案例报告和原生报告；
   - 5 条通用简历 Bullet、20 个面试问题、0 个无效内部链接；
   - 4 张截图均为 1440×1000；
   - 17 项作品集/页面专项测试通过。
3. `make dbt-build`
   - 29 个模型、57 项数据测试、9 个 sources；
   - 总计 86 节点，84 PASS、2 WARN、0 ERROR、0 SKIP；
   - 运行 3.47 秒；
   - WARN 保持为 1 条成交早于首次接触、189 条订单时间顺序异常。

GitHub Actions 文件已按官方当前版本配置，且本地等价命令通过；由于没有创建或推送远端仓库，本阶段不能声称 GitHub 托管 runner 已实际执行。

写入本日志并更新追溯矩阵后，又执行一次：

```bash
make ci && make portfolio-check
```

最终结果：仓库候选文件 167、0 错误；dbt parse 通过；64 项 Python 测试 4.96 秒全部通过；作品集 17 项专项通过；5 条通用 Bullet、20 个问题、0 个无效链接和四张 1440×1000 截图继续通过。

## 8. 文档验收

假设读者不看代码，只看 `docs/`，现在可以回答：

1. **项目目的和目标岗位是什么？** `00_project_charter.md`；
2. **功能、指标、分母和验收是什么？** `01_requirements_and_metrics.md`、`metric_dictionary.md`；
3. **数据如何流动，CI 与真实数据验证如何分层？** `02_solution_architecture.md`；
4. **数据来源、关系、质量、许可和公共仓库边界是什么？** `03_data_design.md`；
5. **模型标签、时间切分、基线、泄漏防护和冻结状态是什么？** `04_model_and_experiment_design.md`；
6. **实施顺序、真实风险和剩余限制是什么？** `05_implementation_plan_and_risks.md`；
7. **实际命令、模型表现、问题和结论是什么？** `06_validation_results_and_conclusions.md` 与 `logs/`；
8. **如何做真实干预实验？** `07_intervention_and_experiment_design.md`；
9. **如何演示和投递？** `08_portfolio_demo_guide.md`、`interview_guide.md`；
10. **如何公开发布、四岗位如何组织、真实业务如何落地？** `09_release_and_role_packaging.md`、`10_real_world_rollout_playbook.md`；
11. **每个需求对应哪些文件和证据？** `traceability.md`。

文档没有把 P13 的工程完善写成模型提升，也没有把规划闸门写成真实上线。

## 9. 仍存在的局限和风险

1. Git 当前所有项目文件仍显示为未跟踪 `??`；没有历史提交可供对比。本阶段未擅自创建初始提交或伪造演进历史；
2. 没有创建远端 GitHub 仓库、推送代码、真实运行托管 CI 或生成公开演示地址；
3. 自有代码许可证仍未决定。公开发布前必须人工确认 `LICENSE`，不能仅凭上游 Actions 使用 MIT 就把本项目宣称为 MIT；
4. 仓库检查只识别预设路径、文件类型、大小和常见私钥头，不能保证发现所有敏感信息；公开前仍需人工审阅；
5. CI 使用 Action 主版本标签而非精确提交 SHA，易维护但供应链不可变性较弱。若目标组织要求高安全级别，应在发布时核对并固定官方完整 commit；
6. 四岗位 Bullet 不是完整个人简历，也没有针对某个真实 JD；最终仍需结合用户真实经历、版面和岗位要求选择 3 条；
7. 看板是本地只读作品集，不含认证、行级权限、实时刷新、告警和生产监控；
8. 模型结果没有变化：商家订单量 WAPE 仍高，公开数据缺少库存、促销、曝光、成本和利润；
9. 没有真实干预日志，因此实验页仍只有规划，任何业务效果与 ROI 都不可声称；
10. 数据来自 2016–2018 年匿名公开样本，不能直接外推当前市场。

## 10. 下一步

项目内可自动完成的 P13 工作已完成。真正对外发布前的下一步必须由仓库所有者做两项选择：

1. 确认自有代码许可证，并复核与 Olist 数据 CC BY-NC-SA 4.0 的展示边界；
2. 决定是否创建远端 GitHub 仓库、形成真实初始提交并启用托管 CI。

若进入真实业务环境，按 `docs/10_real_world_rollout_playbook.md` 从影子运行开始，不直接把当前离线名单用于自动触达或处罚。
