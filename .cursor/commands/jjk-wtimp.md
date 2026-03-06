---
description: Worktree 隔离实现入口（消费 plan/manifest）：创建隔离分支执行实现并合并回主线，支持 Team 自动升级与 fallback
---

> 参考规则: @dual-database

# Worktree 隔离实现工作流 (Worktree Implementation Workflow)

`/jjk-wtimp` 是 `jjk-*` 体系里的隔离实现入口，负责把“可追溯任务”放到独立 worktree 执行，并以可验证证据合并回主线。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 与 Superpowers / OMX 的分工（强制）
## 跨 IDE 调用方式
## 模板来源优先级（跨项目，强制）

`/jjk-wtimp` 的模板按以下优先级读取：

1. 全局共享模板（默认主模板）：
   `${CODEX_HOME:-$HOME/.codex}/engineering/templates/jjk_wtimp_templates.md`
2. 项目覆盖模板（仅放差异，不放全量复制）：
   `docs/内部参考/迭代需求/_templates/jjk_wtimp_templates.md`

若全局模板缺失，输出标记 `GLOBAL_TEMPLATE_MISSING` 并提示先初始化共享模板目录。
`GLOBAL_TEMPLATE_MISSING` 属于全局预检失败标记，可与命令级 `FAIL_FAST` 标记并存。

## 输入前置（强制）

至少提供以下输入之一：

1. `implementation_plan`（含 `task_id/file_paths/acceptance_cmds`）；
2. `pr_ready_manifest` / `pr_ready_manifest_ws`；
3. `_active_task` 可映射的卡片信息 + 明确执行主题。

硬约束：

1. 若无法解析 `task_id`（`pr_id` 可选），`FAIL_FAST` 输出 `WTIMP_INPUT_INCOMPLETE`。
2. 若执行上下文校验失败（`pwd/branch/worktree` 不一致），`FAIL_FAST` 输出 `WTIMP_CONTEXT_INVALID`。
3. 若 `scope_guard` 未通过，`FAIL_FAST` 输出 `WTIMP_SCOPE_GUARD_FAILED`。
4. 若 `scripts/wt-flow.sh create|merge` 失败，`FAIL_FAST` 输出 `WTIMP_FLOW_SCRIPT_FAILED`。
5. 若实现或合并后缺少验证证据，`FAIL_FAST` 输出 `WTIMP_EVIDENCE_MISSING`。
6. 若命中文档同步规则却未回填，`FAIL_FAST` 输出 `WTIMP_DOC_SYNC_MISSING`。

## 执行流程（强制顺序）

### 0) 先探索上下文（强制）

必须先执行并记录：

```bash
pwd
git branch --show-current
git worktree list
```

并至少检查：

1. 当前活跃任务与计划映射是否一致。
2. 本轮改动范围是否限定在当前卡片职责内。
3. 是否存在未合并的同主题 worktree。

### 0.5) 大范围实现自动启用 Team（强制判定）

触发条件（满足任一即可）：

1. 预期改动文件 `>= 8`；
2. 涉及独立模块 `>= 2`；
3. 任务切片 `task_id` 数量 `>= 6`；
4. 同时涉及后端+前端+AI/数据库两类以上边界。

执行策略：

1. **有 Team 能力时**：在同一 worktree 根目录下分任务并行执行，Leader 汇总统一交付。
2. **无 Team 能力时**：降级单代理执行，并输出 `TEAM_UNAVAILABLE_FALLBACK`。

### 0.6) Team 交叉质检约束

1. Team 模式下必须启用抽检互审：至少抽检 `20%` 工作项（向上取整，最少 `1` 项）。
2. 每个抽检项必须包含：`1` 个质疑点、`1` 条验证命令、`1` 个通过/驳回结论。
3. 抽检未通过的工作项不得推进到下一阶段，必须先复核并补齐证据。
4. 阶段汇报至少包含：`结论`、`证据`、`剩余风险`。

### 1) 创建隔离 worktree

1. 根据主题生成 slug（`YYYYMMDD-<topic-slug>`）。
2. 执行 `bash scripts/wt-flow.sh create <slug>`。
3. 记录输出的 `worktree_path` 与 `feature/<slug>` 分支。

### 2) 切换并校验 worktree 上下文

1. 切换到 `worktree_path` 后再次执行 `pwd/git branch --show-current/git worktree list`。
2. 每轮分派前执行 `python3 scripts/coder4_scope_guard.py`，并记录结果。
3. `scope_guard` 未通过不得继续实现。

### 3) 在 worktree 内执行实现

1. 单代理模式：按 `/jjk-imp` 契约逐 `task_id` 实施。
2. Team 模式：所有 teammate 必须共享当前 `worktree_path`，禁止再嵌套 worktree。
3. 过程中发现计划漂移，输出 `WTIMP_PLAN_DRIFT_DETECTED` 并回退 `/jjk-plan`。

### 4) 文档同步与验证

1. 命中 API/数据库/配置/架构变更时，先完成文档同步再进入合并阶段。
2. 执行 `acceptance_cmds` 与最小必要回归测试。
3. 任一关键验证失败，`FAIL_FAST` 输出 `WTIMP_VERIFY_FAILED`。

### 5) 提交、合并与清理

1. 在 worktree 内按 `implementation_plan.task_to_pr_mapping` 与 `execution_contract.commit_policy` 完成提交。
2. 执行 `bash scripts/wt-flow.sh merge`（可选 `--no-cleanup`）。
3. 若冲突或脚本中断，保留 worktree 并输出下一步处理建议。

### 6) 交付产物（强制）

必须产出：

- `docs/内部参考/迭代需求/wtimp_report_<topic>.md`

最小内容：

1. 输入映射（`task_id/card_id/pr_id|none`）
2. worktree 生命周期轨迹（create -> implement -> verify -> merge）
3. 提交与合并证据（`commit sha`、`merge result`）
4. 文档同步结果与遗留风险
5. 下一步命令建议（`/jjk-review`、`/jjk-verify`）

---

## 输出模板（推荐）

见全局模板：`${CODEX_HOME:-$HOME/.codex}/engineering/templates/jjk_wtimp_templates.md`（`输出模板` 段）。
若本项目有覆盖规则，再查：`docs/内部参考/迭代需求/_templates/jjk_wtimp_templates.md`。

## 禁止项（强制）

1. 禁止绕过执行上下文校验直接开工。
2. 禁止跳过 `scope_guard` 分派并行任务。
3. 禁止手工改写 `_active_task.json`。
4. 禁止在 heartbeat 期间执行破坏性 git 操作（`reset --hard`、`checkout --`、强推）。
5. 禁止无证据结束合并流程。

## 推荐链路

`/jjk-plan -> /jjk-wtimp -> /jjk-review -> /jjk-verify`

## 使用示例

```text
/jjk-wtimp 导出 API 并完成隔离交付
```

```text
/jjk-wtimp @docs/内部参考/迭代需求/<topic>_implementation_plan.md
```

---
*使用 `/jjk-wtimp` 触发。目标是“隔离实现 + 可证据合并”，不是“手工切分支后随意开发”。*
