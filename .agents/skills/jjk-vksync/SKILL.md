---
name: jjk-vksync
description: "Use when you need `jjk-vksync` in this repository. Source intent: VK 基线闸门入口（消费 /jjk-vkplan 产物）：多 worktree READY 校验与可控同步（check/apply）"
---
<!-- AUTO-GENERATED: jjk-skill-mirror -->
<!-- source: .cursor/commands/jjk-vksync.md -->

> 参考规则: @dual-database

# VK 基线同步工作流 (VK Sync Workflow)

`$jjk-vksync` 是 `jjk-*` 体系里的基线闸门入口，负责在 `$jjk-vktodo` 前确认 `WS-00_G0_协议冻结` 已被各并行 worktree 吸收。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 与 Superpowers / OMX 的分工（强制）

1. `$jjk-vkplan`：负责生成 G0 相关拆解产物（`parallel_plan.md`、`workstreams/WS-00_G0_协议冻结.md`）。
2. `$jjk-vksync`：负责解析基线提交、对齐各 worktree、输出 READY/NOT_READY 结论。
3. `$jjk-vktodo`：只消费 `$jjk-vksync` 结论，不重复实现基线判定。
4. `team`（OMX）：当 worktree 数量较大时用于并行执行状态采集与同步。

约束：

1. 禁止在 `$jjk-vksync` 重写 `vkplan` 拆解语义；仅消费产物并做基线校验。
2. 禁止在 `$jjk-vktodo` 重复实现本命令的同步逻辑。
3. Team 不可用时必须显式标记 `TEAM_UNAVAILABLE_FALLBACK`。

## 跨 IDE 调用方式

1. Cursor / Claude Code：`$jjk-vksync`
2. Codex：`$jjk-vksync`

> 说明：Codex 推荐显式调用 `$jjk-vksync`。

## 模板来源优先级（跨项目，强制）

`$jjk-vksync` 的模板按以下优先级读取：

1. 全局共享模板（默认主模板）：
   `/Users/jijingkun/.codex/engineering/templates/jjk_vksync_templates.md`
2. 项目覆盖模板（仅放差异，不放全量复制）：
   `docs/内部参考/迭代需求/_templates/jjk_vksync_templates.md`

若全局模板缺失，输出标记 `GLOBAL_TEMPLATE_MISSING` 并提示先初始化共享模板目录。

## 何时使用

| 场景 | 推荐命令 |
|---|---|
| 准备执行 `$jjk-vktodo`，且存在多个 worktree | `$jjk-vksync` ✅ |
| 已发现部分 worktree 落后，需要自动对齐 | `$jjk-vksync ... apply` ✅ |
| 单 worktree 本地演练 | 可跳过 |

---

## 输入约定

`$jjk-vksync <task_split_dir_or_path> [mode] [allow_not_ready]`

- `mode=check`：仅校验，不改动分支（默认）
- `mode=apply`：对未同步 worktree 自动执行 rebase（失败即停止）
- `allow_not_ready=true|false`：是否允许在存在 `NOT_READY` 时继续下游（默认 `false`，仅应急）

## 输入前置（强制）

1. `task_split_dir` 必须可解析。
2. 必须存在并可解析：
   - `parallel_plan.md`
   - `workstreams/WS-00_G0_协议冻结.md`
3. 若缺失任一，`FAIL_FAST` 输出 `VKSYNC_G0_ARTIFACT_MISSING` 并回退 `$jjk-vkplan` 重产。
4. 必须能解析基线提交 `g0_baseline_commit`：
   - 优先从 `parallel_plan.md` 读取；
   - 否则回退 `main/master` HEAD 并输出 `VKSYNC_BASELINE_COMMIT_FALLBACK`。
5. 若基线提交仍不可用，`FAIL_FAST` 输出 `VKSYNC_BASELINE_COMMIT_MISSING`。

---

## 执行流程（强制顺序）

### 0) 先探索上下文（强制）

至少检查：

1. `task_split_dir` 对应主题是否与当前执行链路一致；
2. 当前仓库 worktree 清单及其分支；
3. 最近一次 G0 冻结记录与本轮目标范围。

### 0.5) 大规模场景自动启用 Team（强制判定）

`$jjk-team-vksync` 不再作为主入口。
统一由 `$jjk-vksync` 在大规模同步场景自动升级 Team 模式。

触发条件（满足任一即可）：

1. 待检查 worktree 数量 `>= 10`；
2. `NOT_READY` worktree 数量 `>= 4`；
3. 需要同时执行“状态采集 + 自动同步 + 冲突回收”。

执行策略：

1. **有 Team 能力时**：并行采集/同步，Leader 汇总唯一结论。
2. **无 Team 能力时**：降级单代理执行，并输出 `TEAM_UNAVAILABLE_FALLBACK`。

### 0.6) Team 交叉质检约束（新增，轻量）

1. Team 模式下必须启用抽检互审：至少抽检 `20%` 工作项（向上取整，最少 `1` 项）。
2. 每个抽检项必须包含：`1` 个质疑点、`1` 条验证命令、`1` 个通过/驳回结论。
3. 抽检未通过的工作项不得推进到下一阶段，必须先复核并补齐证据。
4. 阶段汇报至少包含：`结论`、`证据`、`剩余风险`。

### 1) 解析基线提交

1. 优先读取 `parallel_plan.md` 中的 `g0_baseline_commit`。
2. 若缺失则回退到 `main/master` HEAD，并输出 `VKSYNC_BASELINE_COMMIT_FALLBACK`。
3. 记录最终生效的 `g0_baseline_commit`，作为后续判定真理源。

### 2) 校验 worktree 同步状态

1. 枚举所有并行 worktree。
2. 对每个 worktree 执行祖先校验：
   - `git -C <wt> merge-base --is-ancestor <g0_baseline_commit> HEAD`
3. 输出 READY / NOT_READY 清单与数量。

### 3) 处理 NOT_READY（按 mode）

1. `mode=check`：
   - 存在 `NOT_READY` 时输出 `VKSYNC_NOT_READY`，默认阻断下游。
2. `mode=apply`：
   - 对 `NOT_READY` worktree 逐个执行 rebase 对齐；
   - 若冲突，立即停止并输出 `VKSYNC_REBASE_CONFLICT`（附冲突 worktree）。

### 4) 通过判定与风险放行

1. 全部 READY 时输出 `VKSYNC_READY`，允许进入 `$jjk-vktodo`。
2. 存在 `NOT_READY` 且 `allow_not_ready=false` 时，必须阻断。
3. 仅当 `allow_not_ready=true` 时允许带风险继续，并输出 `VKSYNC_BYPASS_ACK`。

### 5) 产物与回执（强制）

必须给出结构化回执：

1. `g0_baseline_commit`
2. `ready_worktrees[]`
3. `not_ready_worktrees[]`
4. `mode`
5. `allow_not_ready`
6. `final_gate`（`PASS|BLOCKED|BYPASS`）

建议落盘：

- `docs/内部参考/任务拆解/<task_split_dir>/sync/vksync_status.json`

---

## 输出模板（推荐）

见全局模板：`/Users/jijingkun/.codex/engineering/templates/jjk_vksync_templates.md`（`输出模板` 段）。
若本项目有覆盖规则，再查：`docs/内部参考/迭代需求/_templates/jjk_vksync_templates.md`。

## 禁止项（强制）

1. 禁止在 G0 产物缺失时继续同步。
2. 禁止在 `VKSYNC_NOT_READY` 且未显式放行时进入 `$jjk-vktodo`。
3. 禁止 `mode=apply` 发生冲突后继续批量 rebase。
4. 禁止输出口头结论而无 READY/NOT_READY 清单证据。

## 推荐链路

`$jjk-plan -> $jjk-vkplan -> $jjk-vksync -> $jjk-vktodo -> $jjk-imp-ws`

## 使用示例

```text
$jjk-vksync 2026-02-12_skill检索对齐_cursor_mvp
```

```text
$jjk-vksync 2026-02-12_skill检索对齐_cursor_mvp apply
```

```text
$jjk-vksync 2026-02-12_skill检索对齐_cursor_mvp check allow_not_ready=true
```

---
*使用 `$jjk-vksync` 触发。目标是“先基线一致，再允许落卡”。*
