---
description: PR 交付入口（消费 pr_ready_manifest）：校验任务映射与验收证据后创建/更新 Pull Request
---

> 参考规则: @dual-database

# 创建 Pull Request (Create PR)

`/jjk-create-pr` 是 `jjk-*` 体系里的 PR 交付入口，负责把已完成实现转换为可审查、可追溯、可回滚的 PR 交付物。


## 与 Superpowers / OMX 的分工（强制）
## 跨 IDE 调用方式
## 模板来源优先级（跨项目，强制）

`/jjk-create-pr` 的模板按以下优先级读取：

1. 全局共享模板（默认主模板）：
   `${CODEX_HOME:-$HOME/.codex}/engineering/templates/jjk_create_pr_templates.md`
2. 项目覆盖模板（仅放差异，不放全量复制）：
   `workdocs/_templates/jjk_create_pr_templates.md`

若全局模板缺失，输出标记 `GLOBAL_TEMPLATE_MISSING` 并提示先初始化共享模板目录。

## 输入前置（强制）

必须可解析以下输入之一：

1. `pr_ready_manifest`（来自 `/jjk-imp`）
2. `pr_ready_manifest_ws`（来自 `/jjk-wtimp`，兼容历史 `/jjk-imp-ws`）

最小字段：

- `task_id`
- `card_id`（可空）
- `pr_id`
- `pr_branch`
- `changed_files`
- `acceptance_cmds`
- `rollback_point`

硬约束：

1. 缺字段即 `FAIL_FAST` 输出 `CREATE_PR_INPUT_INCOMPLETE`。
2. 若 `pr_id` 与 `implementation_plan.task_to_pr_mapping` 不一致，`FAIL_FAST` 输出 `CREATE_PR_MAPPING_MISMATCH`。
3. 若 `acceptance_cmds` 无可验证结果，`FAIL_FAST` 输出 `CREATE_PR_VERIFY_MISSING`。
4. 若当前分支与 `pr_branch` 不一致，`FAIL_FAST` 输出 `CREATE_PR_BRANCH_MISMATCH`。

## 执行流程（强制顺序）

### 0) 先探索上下文（强制）

补充执行约束：执行命令时统一遵循 `.cursor/rules/core.mdc` 的“命令执行拆分”规则：单步单目标、失败只重跑当前步、长任务只轮询不重启、输出截断时优先拆短当前步。

至少检查：

1. 当前分支、最近提交、变更范围与目标 `pr_branch` 一致性。
2. manifest 与计划映射的一致性（`task_id/card_id/pr_id`）。
3. 是否已有同 `pr_id` 的打开 PR（避免重复创建）。

### 0.5) 批量场景自动启用 Team（强制判定）

批量交付由 `/jjk-create-pr` 自动升级 Team 模式。

触发条件（满足任一即可）：

1. 待创建/更新 PR 数量 `>= 3`；
2. 涉及 `>= 2` 个 worktree 分支；
3. 需要并行生成多份 PR 描述并核对映射。

执行策略：

1. **有 Team 能力时**：并行准备 PR 草稿与证据摘要，Leader 汇总提交。
2. **无 Team 能力时**：降级单代理执行，并输出 `TEAM_UNAVAILABLE_FALLBACK`。

### 0.6) Team 交叉质检约束

1. Team 模式下必须启用抽检互审：至少抽检 `20%` 工作项（向上取整，最少 `1` 项）。
2. 每个抽检项必须包含：`1` 个质疑点、`1` 条验证命令、`1` 个通过/驳回结论。
3. 抽检未通过的工作项不得推进到下一阶段，必须先复核并补齐证据。
4. 阶段汇报至少包含：`结论`、`证据`、`剩余风险`。

### 1) 基线与分支准备

1. 校验工作区干净度与未提交改动风险。
2. 同步基线分支（`main/master`）并对齐当前分支。
3. 确保目标分支可推送；若未推送远程，输出 `CREATE_PR_BRANCH_NOT_PUBLISHED`。
4. 若基线未对齐，输出 `CREATE_PR_BASELINE_NOT_READY`。

### 2) 证据与回滚校验

1. 汇总 `acceptance_cmds` 的最近执行证据。
2. 校验 `rollback_point` 可执行性与描述完整性。
3. 高风险变更（跨模块/数据库/API）建议先触发 `requesting-code-review`；不可用时输出 `REQUESTING_CODE_REVIEW_UNAVAILABLE_FALLBACK`。

### 3) 生成 PR 描述（强制字段）

PR 描述至少包含：

1. 概述（本次目标）
2. 任务归属（`task_id/card_id/pr_id`）
3. 变更内容（按模块）
4. 影响范围（API/DB/前端/AI-workflow）
5. 验证证据（`acceptance_cmds` + 结果）
6. 回滚方案（`rollback_point`）
7. 风险与后续观察点

### 4) 创建或更新 PR（GitHub MCP 优先）

1. 优先使用 `github-mcp-server` 创建/更新 PR。
2. 若检测到同 `pr_id` 已存在开放 PR，改为更新描述而非重复创建（`CREATE_PR_DUPLICATE_OPEN`）。
3. 若 `github-mcp-server` 不可用，输出 `GITHUB_MCP_UNAVAILABLE_FALLBACK` 并停止，不默认退回 `gh` CLI。

### 5) 状态回填与交接

1. 回填 PR 链接到实现文档或 WS 自检卡。
2. 若接入 VK 流程，建议推进卡片到 `Review`。
3. 输出交接摘要：
   - `pr_id`
   - PR 链接
   - 关联 `task_id/card_id`
   - 验收证据摘要
   - 已知风险与回滚说明

---

## 输出模板（推荐）

见全局模板：`${CODEX_HOME:-$HOME/.codex}/engineering/templates/jjk_create_pr_templates.md`（`输出模板` 段）。
若本项目有覆盖规则，再查：`workdocs/_templates/jjk_create_pr_templates.md`。

## 禁止项（强制）

1. 禁止无 `task_id/pr_id` 创建 PR。
2. 禁止验收证据缺失时创建 PR。
3. 禁止映射不一致（`task_id/card_id/pr_id`）时强行提交。
4. 禁止默认使用 `gh` CLI 替代 GitHub MCP。
5. 禁止创建重复开放 PR 而不先检查同 `pr_id`。

## 推荐链路

`主链: /jjk-imp | /jjk-wtimp -> /jjk-review -> /jjk-verify`

`可选分支: 需要远端 PR 交付时，在 /jjk-review 前插入 /jjk-create-pr`

## 使用示例

```text
/jjk-create-pr
```

```text
/jjk-create-pr @workdocs/任务拆解/<YYYY-MM-DD_主题>/workstreams/WS-01_<并行任务>.md
```

---
*使用 `/jjk-create-pr` 触发。目标是“可追溯、可审查、可回滚”的 PR 交付，而不是仅把分支推上去。*
