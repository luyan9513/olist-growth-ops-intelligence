# 公开仓库内容边界调整日志

**日期：** 2026-08-06  
**范围：** 将仅供个人使用的准备材料移出公开版本，同时保留项目案例、业务报告、模型卡、截图和可复现工程链路  
**状态：** 已完成；本地隔离、历史过滤、远端 `main` 重写和托管 CI 均已验证

## 1. 背景与边界

用户确认不希望直接用于个人准备的 5 份 Markdown 文档继续出现在公开 GitHub 仓库。处理目标不是删除项目的分析证据，而是重新划分公开与本地私有边界：公开仓库保留技术实现、业务结论、数据卡、模型卡、案例报告、看板截图、CI 和复现说明；个人准备材料保留在本机且被 Git 忽略。

本阶段不读取或输出密钥、Token、个人信息，不修改原始数据、DuckDB、模型二进制和真实分析结果，不重训模型，也不声称产生新的业务效果。

## 2. 修改和新增文件

### 2.1 从公开版本移出的文件

- `docs/interview_guide.md`；
- `docs/09_release_and_role_packaging.md`；
- `reports/resume_bullets.md`；
- `reports/resume_bullets_by_role.md`；
- `reports/jd_tailoring_checklist.md`。

上述文件没有从本机永久删除，而是按原目录类别移动到 `private/job_search/docs/` 和 `private/job_search/reports/`。`private/job_search/` 加入 `.gitignore`，因此私有副本不会成为提交候选文件。逐文件比较原提交 blob 与私有副本的 Git blob 哈希，5 项全部一致。

### 2.2 新增公开发布说明

- `docs/09_repository_release.md`：仅说明公开仓库应该包含什么、不应包含什么，以及 `make ci`、`make portfolio-check`、`make verify` 的验证边界；不再包含个人准备内容。

### 2.3 修改公开入口和项目文档

- `.gitignore`：增加 `private/job_search/` 忽略规则；
- `README.md`：移除 5 份个人材料入口，发布设计入口改为 `docs/09_repository_release.md`，快速验收不再检查个人材料数量；
- `CHANGELOG.md`：删除个人材料交付描述，保留仓库检查、无数据 CI 和真实落地手册；
- `RELEASE_CHECKLIST.md`：发布前文档检查改为项目报告、演示指南与追溯矩阵，不再要求个人材料；
- `THIRD_PARTY_NOTICES.md`、`reports/data_card.md`：将数据用途表述收敛为非商业项目展示，不改变 Olist 数据来源和 CC BY-NC-SA 4.0 边界；
- `docs/00_project_charter.md`：成功标准改为项目交付、证据追溯和公开仓库质量；
- `docs/01_requirements_and_metrics.md`：移除分岗位个人材料需求，证据验收只保留内部链接、截图和产物一致性；
- `docs/02_solution_architecture.md`：将面向个人演练的表述改为项目审阅和演示；
- `docs/04_model_and_experiment_design.md`：P13 的证据消费者改为案例和看板，模型边界不变；
- `docs/05_implementation_plan_and_risks.md`：阶段名称、实施步骤和风险措辞改为报告与项目展示；历史模型、测试和风险编号保持不变；
- `docs/06_validation_results_and_conclusions.md`：P12 验收结论只保留项目证据、链接、截图、页面和回归验证；
- `docs/08_portfolio_demo_guide.md`：改为通用项目演示指南，删除个人材料索引和数量检查；
- `docs/traceability.md`：删除个人材料需求映射，发布设计指向 `docs/09_repository_release.md`；
- `sql/03_marts.sql`：注释改为通用代码审查入口；
- `src/portfolio.py`：案例报告目标读者改为项目审阅者，不改变生成逻辑；
- `docs/logs/README.md`：登记本阶段日志。

### 2.4 修改校验代码

- `scripts/validate_portfolio.py`：保留聚合证据新鲜度、内部链接、四张 PNG 格式与尺寸校验，删除对已私有化文档的读取和数量断言；
- `scripts/validate_repository.py`：公开仓库必需文件改为 `docs/09_repository_release.md`，删除个人材料存在性和分组数量检查；候选列表增加 `path.exists()` 过滤，使提交前已删除但索引仍跟踪的路径不会触发 `FileNotFoundError`。

## 3. 为什么采用这种实现

1. **保留本地副本而不是永久删除。** 用户只要求不提交公开仓库，材料本身仍可能用于个人准备；移动到明确忽略目录既满足公开边界，也避免不可恢复删除。
2. **保留技术案例和项目演示资产。** 案例报告、截图和证据包是项目结果，不等同于个人材料；全部删除会削弱项目的可审查性。
3. **让校验逻辑与公开交付边界一致。** 如果只删 Markdown 而不改校验脚本，CI 会因缺失文件失败；删除相应断言比创建空占位文件更符合真实边界。
4. **拆出纯技术发布说明。** 原 P13 文档混合仓库发布和个人准备内容，直接整份删除会丢失 CI、数据隔离和发布边界，因此新增纯技术版本。
5. **保留历史开发日志。** 旧日志记录当时确实发生过的开发活动，但不包含这 5 份文件的完整正文。改写所有旧日志会破坏事实时间线，因此只清理当前入口和活跃设计文档。

## 4. 真实问题、定位与解决

### 4.1 GitHub CLI 登录失效

`gh auth status` 返回当前账号 Token 无效。该问题不影响本地修改和测试，但可能阻塞远端查询或推送。没有读取或输出 Token；远端操作优先尝试现有 Git 凭据，若失败则由用户重新执行官方登录流程。

### 4.2 提交前仓库检查读取已删除路径

首次运行 `make ci` 时，`scripts.validate_repository.repository_files()` 使用 `git ls-files --cached --others --exclude-standard`。旧文件在提交前仍属于索引中的已跟踪路径，但工作区已不存在；后续 `path.stat()` 因此抛出 `FileNotFoundError`。

定位证据是堆栈明确指向 `scripts/validate_repository.py` 的 `path.stat()`，缺失路径正是本阶段移出的旧文档。修复方式是在候选路径构造后过滤 `path.exists()`。重新运行仓库检查后覆盖 165 个候选文件，状态 `pass`、错误数 0。

### 4.3 私有副本哈希检查第一次命令失败

第一次完整性检查把“原路径和新路径”放在同一个 shell 变量中，依赖变量按空格拆分。zsh 默认没有按预期拆词，Git 将两个路径识别成一个不存在的路径并报错。该命令没有修改文件。

解决方式是为 5 组路径分别运行显式的 `git rev-parse HEAD:<原路径>` 与 `git hash-object <私有路径>` 比较。最终输出 `private_copy_integrity=pass`，且 `git check-ignore` 对 5 个私有路径全部返回匹配。

## 5. 命令与验证结果

### 5.1 文件与引用检查

- `git ls-tree -r --name-only HEAD`：确认 5 份材料已存在于当前提交；
- `rg`：定位 README、活跃设计文档、校验脚本和历史日志中的引用；
- `git check-ignore private/job_search/...`：5 个私有文件全部被忽略；
- 原 blob 与私有副本逐文件哈希比较：`private_copy_integrity=pass`；
- `git diff --check`：通过，无空白错误。

### 5.2 项目证据验收

运行 `make portfolio-check`：

- 证据生成与当前 artifacts 对账通过；
- 4 张截图均为 1440×1000；
- 无效内部链接 0；
- 作品证据与 10 页看板专项测试 17/17 通过。

该命令只更新了证据文件生成时间；为避免把与本阶段无关的时间戳提交，随后将两个 JSON 的时间戳恢复为原提交值，业务数据没有变化。

### 5.3 无数据 CI 等价验证

修复提交前删除路径处理后重新运行 `make ci`：

- 仓库检查：165 个候选文件，`status=pass`，0 错误；
- dbt parse：通过，dbt 1.12.0、dbt-duckdb 1.10.1；
- Python：64/64 测试通过，用时 7.05 秒。

## 6. 局限、风险与下一步

1. 本地私有目录仍位于项目工作区，依赖 `.gitignore` 防止误提交；后续提交前仍应运行 `make repo-check` 和检查 `git status`。
2. 普通删除只会从最新版本移除文件，旧提交仍可读取正文；因此本阶段下一步是对这 5 个精确路径执行历史过滤并强制更新远端 `main`。
3. 历史重写会改变现有提交哈希；若有其他克隆，需要重新同步或重新克隆。当前检查只发现本地 `main` 和 `origin/main`，没有本地其他分支或标签。
4. 即使远端分支不再引用旧对象，GitHub 对旧提交 URL 或缓存的清除不保证立即完成；这些材料不含密钥，如需处理真正敏感信息还应联系 GitHub Support。
5. 当前 `gh` 登录无效。若 Git 凭据不能完成强制推送，需要用户重新登录后继续。

## 7. 远端历史重写与托管复验

用户在了解默认分支提交哈希变化、协作者需要重新同步、旧 URL/缓存可能暂时保留等风险后，明确授权重写远端 `main`。

### 7.1 本地历史过滤

使用 Git 自带 `filter-branch --index-filter`，只对第 2.1 节列出的 5 个精确旧路径执行 `git rm --cached --ignore-unmatch`。共重写 4 个提交，没有压平其他文件的开发历史。随后删除 `refs/original` 备份引用、过期全部本地 reflog，并运行 `git gc --prune=now`。

过滤后验证：

- `git rev-list --all --objects` 未找到 5 个旧路径；
- `git fsck --full --no-reflogs --unreachable` 未报告相关不可达 commit 或 blob；
- 5 个本地私有副本仍然存在且继续被 `.gitignore` 排除；
- 清理后的本地提交序列为 `1a1e682`、`dc248e3`、`338566b`、`317c435`。

### 7.2 远端保护式强制更新

推送前记录远端旧 `main` 完整哈希 `9e39bee3eb7dfcab9d1fc979712c9c3387ff93d5`。第一次强制推送请求被执行环境的安全审核拒绝，原因是用户此前虽同意按建议处理，但尚未逐字明确授权重写默认分支。没有绕过安全审核；等待用户明确回复后才继续。

最终执行带精确旧哈希的保护式推送：

```text
git push --force-with-lease=refs/heads/main:<清理前完整哈希> origin main
```

结果：远端 `main` 从 `9e39bee` 更新为 `317c435`，输出标记为 `forced update`。`git ls-remote origin refs/heads/main` 返回 `317c435ed7c178ae06b68590765b3a1964260623`，与本地 `HEAD` 完全一致；`git status -sb` 显示本地与 `origin/main` 同步。

### 7.3 GitHub Actions

历史重写触发 GitHub Actions run `31087474329`：

- Checkout repository：通过；
- Set up Python：通过；
- Install dependencies：通过；
- Validate repository package：通过；
- Parse dbt project：通过；
- Run Python tests：通过；
- `quality` job 总耗时约 1 分 6 秒，最终结论 `success`。

运行地址：<https://github.com/luyan9513/olist-growth-ops-intelligence/actions/runs/31087474329>

### 7.4 最终边界

远端可达 `main` 历史已不包含 5 份材料的文件路径和正文；当前公开版本也没有对应入口或强制校验依赖。本地私有副本仍完整保留。GitHub 对旧提交 URL、服务端缓存或第三方镜像的立即清除不作保证，但这些文件不包含密钥；若未来处理真正敏感数据，应按 GitHub 敏感数据移除流程另行处理。
