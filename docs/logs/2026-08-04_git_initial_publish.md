# 2026-08-04 首次 GitHub 发布日志

## 1. 阶段目标与边界

本阶段按用户明确授权，将已完成并验证的项目创建首次 Git 提交并推送到现有远端仓库。目标远端为 `https://github.com/luyan9513/olist-growth-ops-intelligence`，目标分支为 `main`。

这是外部发布操作，不新增模型、不修改业务指标、不生成新的业务效果。推送后仓库为公开可见，但根目录仍没有自有代码 `LICENSE`；因此项目不能仅因公开可访问就宣称为 MIT 或其他开源许可证。Olist 数据许可与第三方 Actions 声明继续以 `THIRD_PARTY_NOTICES.md` 为准。

## 2. 发布前实际检查

### 2.1 GitHub 工具和认证

首次检查时 GitHub CLI 2.97.0 已安装，但账号认证 Token 失效。按照安全边界，没有先创建一半本地提交，而是停止并请用户通过 `gh auth login -h github.com` 自行重新登录；没有要求用户发送 Token，也没有把凭证写入项目文件。

用户确认登录后重新运行 `gh auth status`，结果为账号已通过系统 keyring 登录，Git 操作协议为 HTTPS，权限范围包含仓库和工作流操作。日志不记录真实 Token 内容。

### 2.2 远端状态

`gh repo view luyan9513/olist-growth-ops-intelligence --json nameWithOwner,visibility,defaultBranchRef,url` 的实际结果：

- 仓库：`luyan9513/olist-growth-ops-intelligence`；
- 可见性：`PUBLIC`；
- 地址：`https://github.com/luyan9513/olist-growth-ops-intelligence`；
- 默认分支为空，说明远端尚无首次提交。

`git ls-remote --heads origin` 没有返回分支，和空仓库状态一致。本地位于 `main`，没有历史 commit，`origin/main` 旧引用显示为 gone。

### 2.3 提交范围和忽略规则

发布前 `git status -sb` 显示项目文件全部为未跟踪状态，属于本项目从 P0 到 P13 的完整首次提交，没有发现另一个已跟踪项目或不相关修改混在工作区。

`.gitignore` 和 `git check-ignore -v` 实际确认以下内容不会进入提交：

- 11 个 `data/raw/*.csv` 原始数据文件；
- `data/processed/olist.duckdb` 及 WAL；
- `artifacts/` 下 joblib、逐对象预测和训练产物；
- `.env`；
- `.streamlit/secrets.toml`；
- `.venv`、pytest/dbt 生成目录和编辑器文件。

允许提交的 `data/raw/README.md`、`.gitkeep`、聚合作品集证据和四张脱敏截图是项目复现与展示所需，不包含原始订单或真实密钥。

首次暂存清单额外发现 `dbt/.user.yml`。该文件由本机 dbt 生成，属于用户级状态而非项目运行所需配置；没有读取或输出其内容，直接将 `dbt/.user.yml` 加入 `.gitignore` 并移出暂存区。项目需要提交的是不含个人状态的 `dbt/profiles.yml` 和 `dbt_project.yml`。

### 2.4 仓库验收

发布前运行：

```bash
make repo-check
```

检查通过：在补充本发布日志前有 167 个候选文件，0 个错误，单文件上限 5 MiB。加入 README 真实地址、本日志和日志索引后，提交前会再次运行检查并以最终结果为准。

## 3. 本阶段修改文件

### `README.md`

- 增加真实 GitHub 仓库地址；
- 增加指向当前仓库 `ci.yml` 的 CI 徽章；
- 不增加许可证徽章，避免在尚未选择自有代码许可证时造成误导。

### `docs/logs/README.md`

- 将本次首次 GitHub 发布加入时间顺序索引。

### `docs/logs/2026-08-04_git_initial_publish.md`

- 记录认证问题、远端公开状态、提交范围、忽略规则、验证命令、许可证边界和实际发布证据；
- 不记录 Token、密码、个人邮箱或 Git 身份配置。

### `.gitignore`

- 新增 `dbt/.user.yml`，避免本机 dbt 用户级状态进入公开仓库。

## 4. 实现选择

1. 远端为空且用户明确要求提交并推送，因此直接建立 `main` 首次提交；没有创建无意义的功能分支和空仓库 PR。
2. 整个未跟踪工作树就是用户要求发布的完整项目，且仓库检查已覆盖候选文件，因此可以在最终清单复核后一次性暂存；不是在混杂工作树中盲目 `git add -A`。
3. 不读取或输出 Git 用户邮箱；提交由本地已配置身份完成，若 Git 报缺少身份则停止并让用户自行配置。
4. 不自动创建 `LICENSE`。代码授权是仓库所有者的法律决定，公开仓库在没有许可证时默认不能被他人自由复制、修改和分发。
5. 推送使用 HTTPS 和用户刚恢复的 GitHub 认证，不把凭证放进 remote URL。

## 5. 真实问题与处理

### GitHub CLI 认证失效

- 现象：`gh auth status` 报默认账号 Token 无效；
- 定位：CLI 已安装、remote 地址存在，阻塞来自认证而不是仓库路径或 Git 缺失；
- 处理：停止发布，请用户自行运行 `gh auth login -h github.com`；重新检查后认证恢复；
- 安全性：没有显示、保存或索要用户 Token。

### 暂存清单包含本机 `dbt/.user.yml`

- 现象：首次 `git diff --cached --name-status` 显示该文件准备进入初始提交；
- 定位：这是本机工具生成的用户级文件，不是 dbt 项目必需文件；
- 处理：不读取内容，加入 `.gitignore` 并从 index 移除；
- 验证：最终暂存清单不再包含该文件，`git check-ignore` 能命中新增规则。

除此之外，提交前阶段未遇到新的阻塞问题。

## 6. 提交与推送结果

本节将在实际 Git 提交和远端推送完成后，以后续小型文档提交回填 commit、分支、远端和验证结果；不会在命令执行前填写虚构成功状态。

## 7. 当前限制与后续

- GitHub 托管 CI 只有在首次推送后才会真实触发；本地 `make ci` 通过不能冒充托管 runner 已通过；
- 远端为公开仓库，发布后需等待并检查 Actions；
- 自有代码许可证仍未决定，公开发布不等于开源授权；
- 没有公开部署 Streamlit，仓库中的截图和本地启动方式仍是当前演示入口。
