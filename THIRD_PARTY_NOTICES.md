# Third-Party Notices

## 当前状态

截至 2026-08-02，本项目未复制或修改第三方业务代码。GitHub Actions 工作流通过版本标签远程调用以下官方 Action；源代码未被 vendoring 到本仓库。

| 上游 | URL | 引用版本 | 许可证 | 复用文件 | 本项目修改 |
|---|---|---|---|---|---|
| actions/checkout | https://github.com/actions/checkout | `v6` | MIT | 无；工作流远程 `uses` | 无 |
| actions/setup-python | https://github.com/actions/setup-python | `v6` | MIT | 无；工作流远程 `uses` | 无 |

上述版本依据 2026-08-02 的官方仓库和 GitHub Actions Python 文档核对。公共发布前仍应复核版本、供应链策略和许可证；若改为复制源码或固定到具体提交，必须补充精确 commit、复用文件和修改内容。

## 计划参考但尚未复用

| 上游 | URL | commit | 许可证 | 复用文件 | 当前处理 |
|---|---|---|---|---|---|
| Olist Deep Dive | https://github.com/PavelGrigoryevDS/olist-deep-dive | 待决定是否复用后固定 | 开发文档标注为 MIT，复用前再次核验 | 无 | 仅作为潜在参考，尚未复制代码 |
| Olist Marketing Analytics | https://github.com/olist/work-at-olist-marketing | 不适用 | 题目仓库仅作参考；数据页为 CC BY-NC-SA 4.0 | 无 | 仅参考官方题目与数据说明，不复制他人答案 |

## 数据许可

- Brazilian E-Commerce Public Dataset by Olist：https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce，CC BY-NC-SA 4.0，核对日期 2026-07-30；
- Marketing Funnel by Olist：https://www.kaggle.com/datasets/olistbr/marketing-funnel-olist，CC BY-NC-SA 4.0，核对日期 2026-07-30；
- 本项目不提交原始数据，分析产物用于非商业求职作品集，并保留来源署名和相同方式共享要求。

如后续复用第三方代码，本文件必须在同一阶段更新上游 URL、精确 commit、复用文件、许可证、版权/NOTICE 和本项目修改内容，并保留许可证要求的原文文件。
