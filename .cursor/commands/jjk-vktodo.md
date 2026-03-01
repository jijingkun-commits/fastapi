---
description: VK 落卡入口（消费 /jjk-vkplan 契约）：基线校验后批量建卡/推进，支持 MCP->本地兜底与作用域绑定
---

> 参考规则: @dual-database

# VK Todo 工作流 (VK Todo Workflow)

`/jjk-vktodo` 是 `jjk-*` 体系里的落卡入口，负责把 `jjk-vkplan` 的 `vk_cards.json` 安全落到 Vibe Kanban，并在失败时提供可观测兜底。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 与 Superpowers / OMX 的分工（强制）

1. `/jjk-vkplan`：负责可执行拆解与契约产物（`parallel_plan.md`、`vk_cards.json`、`_active_task.json`）。
2. `/jjk-vksync`：负责多 worktree G0 基线一致性校验（READY / NOT_READY）。
3. `team`（OMX）：大批量建卡/推进时并行执行与汇总。
4. `/jjk-vktodo`：负责 project 解析、卡片幂等建卡/推进、MCP 失败兜底、`coder4_scope_guard` 作用域绑定。

约束：

1. 禁止在 `/jjk-vktodo` 重复实现 `/jjk-vksync` 的基线判断逻辑；必须调用并消费其结果。
2. 禁止在 `/jjk-vktodo` 重写 `/jjk-vkplan` 的拆解语义；只消费既有契约。
3. Team 可用时按规模自动升级；不可用时必须显式标记 `TEAM_UNAVAILABLE_FALLBACK`。

## 跨 IDE 调用方式

1. Cursor / Claude Code：`/jjk-vktodo`
2. Codex：`/prompts:jjk-vktodo`

> 说明：Codex 的自定义命令入口是 `/prompts:<name>`，不是 `/<name>`。

## 何时使用

| 场景 | 推荐命令 |
|---|---|
| 已完成 `/jjk-vkplan`，准备批量建卡 | `/jjk-vktodo` ✅ |
| 需要批量推进卡片状态（Doing/Review/Gate/Done） | `/jjk-vktodo` ✅ |
| 仅做基线同步检查 | `/jjk-vksync` |
| 仅查看卡片列表 | 直接调用 `list_issues` |

---

## 命名衔接（与 `/jjk-plan`、`/jjk-vkplan` 强一致）

1. `/jjk-vktodo` 处理的 `task_split_dir` 必须来自同主题链路：`/jjk-plan -> /jjk-vkplan`。
2. 主题一致性要求：
   - 迭代需求文档：`docs/内部参考/迭代需求/<主题>_requirements.md`、`docs/内部参考/迭代需求/<主题>_implementation_plan.md`
   - 拆解目录：`docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/`
3. 若检测到“拆解目录主题”与“来源文档主题”语义不一致，`action=create|move` 默认直接失败（除非显式应急放行并记录风险）。
4. 不得回退依赖旧通用名 `requirements.md` / `implementation_plan.md` 作为主输入。

## 模板来源优先级（跨项目，强制）

`/jjk-vktodo` 的模板按以下优先级读取：

1. 全局共享模板（默认主模板）：
   `/Users/jijingkun/.codex/engineering/templates/jjk_vktodo_templates.md`
2. 项目覆盖模板（仅放差异，不放全量复制）：
   `docs/内部参考/迭代需求/_templates/jjk_vktodo_templates.md`

若全局模板缺失，输出标记 `GLOBAL_TEMPLATE_MISSING` 并提示先初始化共享模板目录。

## 输入前置（强制）

1. `task_split_dir` 必须可解析且包含：
   - `parallel_plan.md`
   - `vk_cards.json`
2. `vk_cards.json` 必须可解析且包含：
   - `task_key`
   - `cards[]`
3. `project_id` 必须可确定：
   - 优先显式参数 `project`；
   - 其次读取 `docs/内部参考/任务拆解/_active_task.json`（活跃索引）；
   - 再次尝试 workspace 绑定项目。
4. 若仍无法解析 `project_id`，必须 `FAIL_FAST` 输出 `VKTODO_MISSING_PROJECT_ID`。
5. 若 `vk_cards.json` 缺失或结构非法，必须 `FAIL_FAST` 输出 `VKTODO_INPUT_INVALID`。
6. `parallel_plan.md`（或来源 implementation plan）必须可回查 `task_to_pr_mapping`：
   - `task_id`
   - `pr_id`
   - `pr_branch`
   - `pr_depends_on`
   - `pr_subject`
7. 若缺少 `task_to_pr_mapping` 或 `vk_cards.json.cards[*].pr_id` 缺失，必须 `FAIL_FAST` 输出 `VKTODO_PR_MAPPING_MISSING`。

## 输入约定（支持路径直传）

### 1) 位置参数（推荐）

`/jjk-vktodo <task_split_dir_or_path> [action] [status]`

- 第 1 个参数：任务拆解目录（目录名/相对路径/绝对路径）
- 第 2 个参数（可选）：`action`，支持 `create` / `move`，默认 `create`
- 第 3 个参数（可选）：目标状态（如 `Backlog/Doing/Review/Gate/Done`）

### 2) 键值参数（兼容）

1. `task_split_dir`：任务拆解目录（推荐与位置参数二选一）
2. `project`：项目名或项目 ID（可选；若当前 workspace 已绑定项目可省略）
3. `action`：`create` / `move`（可选，默认 `create`）
4. `cards`：
   - 批量编号模式：如 `PP-20260213::WS-01..PP-20260213::WS-08`
   - 或显式列表：如 `["PP-20260213::WS-01", "PP-20260213::WS-02"]`
5. `status`：目标列（如 `Backlog/Doing/Review/Gate/Done`）
6. `move_filter`：推进时筛选条件（如 `prefix:PP-20260213,top:5`）
7. `allow_not_ready`：是否允许跳过基线硬拦截（`false|true`，默认 `false`，仅应急使用）

### 3) 自动推断规则

当提供 `task_split_dir` 且未显式提供 `cards` 时：

1. 默认读取 `<task_split_dir>/vk_cards.json` 作为建卡输入。
2. `action=create` 时，自动使用 `vk_cards.json.cards[*]`：
   - 卡片 ID 与标题：来自 JSON
   - 依赖关系：优先使用 `hard_depends_on`
   - 状态：若未传 `status`，使用卡片内 `column`
3. `action=move` 时，若未传 `move_filter`，从 `vk_cards.json.task_key` 推导：
   - `move_filter=prefix:<task_key>`
4. `vk_cards.json.cards[*]` 默认仅包含可落卡工作包（`WS-01...WS-G2`），不包含 `WS-00`。

> 推荐最短链路：`/jjk-plan -> /jjk-vkplan -> /jjk-vksync -> /jjk-vktodo <任务拆解目录>`

---

## 执行流程（强制顺序）

### 0) G0 基线前置校验（必做）

1. 执行 `/jjk-vksync <task_split_dir_or_path> check`，获取 READY / NOT_READY 清单。
2. 默认行为：若存在 `NOT_READY`，立即失败并输出 `VKTODO_BASELINE_NOT_READY`。
3. 仅当显式传入 `allow_not_ready=true` 时，允许继续；必须输出 `VKTODO_BASELINE_BYPASS_ACK` 并记录风险原因。
4. 未显式确认风险时，不得创建/推进任何卡片。

### 0.5) 大任务自动启用 Team（强制判定）

`/jjk-team-vktodo` 不再作为主入口。
统一由 `/jjk-vktodo` 在大批量操作时自动升级 Team 模式。

触发条件（满足任一即可）：

1. 本轮目标卡片数量 `>= 15`；
2. 预计需要分批执行 `>= 3` 轮 create/move；
3. 同时涉及“批量建卡 + 状态推进 + 结果核对”三段操作；
4. 存在多工作树并行推进且需统一回写统计。

执行策略：

1. **有 Team 能力时**：并行分片执行 create/move/reconcile，Leader 汇总唯一结果。
2. **无 Team 能力时**：降级为单代理执行，并输出 `TEAM_UNAVAILABLE_FALLBACK`。

### 0.6) Team 交叉质检约束（新增，轻量）

1. Team 模式下必须启用抽检互审：至少抽检 `20%` 工作项（向上取整，最少 `1` 项）。
2. 每个抽检项必须包含：`1` 个质疑点、`1` 条验证命令、`1` 个通过/驳回结论。
3. 抽检未通过的工作项不得推进到下一阶段，必须先复核并补齐证据。
4. 阶段汇报至少包含：`结论`、`证据`、`剩余风险`。

### 1) 解析来源目录、项目与契约

1. 若传入 `task_split_dir`（或位置参数），先按路径规则解析并校验目录合法性。
2. 校验命名衔接：`task_split_dir` 中 `<主题>` 必须与 `/jjk-plan` / `/jjk-vkplan` 产物一致。
3. 读取 `vk_cards.json`、任务级 `_active_task.json`（`<task_split_dir>/_active_task.json`）与活跃索引 `_active_task.json`（若存在），校验 `task_key/task_split_dir/project_id`：
   - 若冲突，`FAIL_FAST` 输出 `VKTODO_ACTIVE_TASK_MISMATCH`。
4. 调用 `mcp__vibe_kanban__list_organizations` + `mcp__vibe_kanban__list_projects`，将 `project` 解析为唯一 `project_id`。
5. 调用 `mcp__vibe_kanban__list_issues` 获取变更前统计（按状态聚合）。

### 1.5) Task->PR 映射校验（强制）

1. 读取 `task_to_pr_mapping` 与 `vk_cards.json.cards[*]`，按 `card_id/task_id/pr_id` 做一致性校验。
2. 目标卡片集合中的每张卡必须包含：
   - `pr_id`
   - `pr_branch`
   - `pr_depends_on`
   - `pr_subject`
3. 若发现“同一卡片映射多个 PR”或“卡片 PR 与 `task_to_pr_mapping` 不一致”，必须 `FAIL_FAST` 输出 `VKTODO_PR_MAPPING_BROKEN`。
4. 未通过映射校验时，禁止执行 create/move。

### 2) 组装执行清单

1. `action=create`：
   - 若传了 `cards`，按 `cards` 生成目标清单；
   - 若没传 `cards`，按 `vk_cards.json.cards[*]` 生成目标清单；
   - 若传入列表中包含 `WS-00`，自动忽略并提示“WS-00 为前置里程碑，不落卡”。
2. `action=move`：
   - 若传了 `move_filter`，按 `move_filter` 筛选；
   - 若没传 `move_filter` 且有 `vk_cards.json.task_key`，自动使用 `prefix:<task_key>`。
3. 若 create/move 均无法得到目标集合，直接失败并输出 `VKTODO_EMPTY_TARGET_SET`。

### 3) 优先 MCP 批量执行（issue API）

1. `action=create`：调用 `mcp__vibe_kanban__create_issue` 创建卡片。
2. `action=move`：先筛选目标卡片，再调用 `mcp__vibe_kanban__update_issue` 修改状态。
3. 执行前必须做幂等检查（按 `card_key/title` 去重），避免重复建卡。
4. 记录每张卡片执行结果（成功 / 失败原因 / 执行通道）。
5. 建卡时必须把机读增强字段写入 description（若存在）：
   - `feature_ids`
   - `mechanism_summary`
   - `code_anchor_refs`
   - `acceptance_checks`
   - `rollback_anchors`
   - `evidence_entry`
   - `pr_id`
   - `pr_branch`
   - `pr_depends_on`
   - `pr_subject`
6. 若 `vk_cards.json` 中存在 `execution_mode=serial`，建卡后默认只推进首张卡到 Doing，其余保持 Backlog。

### 4) MCP 异常自动兜底

当出现 `502 Bad Gateway` 或 MCP 通道不可用：

1. 明确说明 MCP 异常，不再盲目重试。
2. 输出对应标记：
   - `VKTODO_MCP_502_FALLBACK` 或
   - `VKTODO_MCP_UNAVAILABLE_FALLBACK`
3. 自动切换到本地 VK 后端接口执行同等操作（创建或状态更新）。
4. 兜底执行仍需先做去重，再次查询列表确认实际落库结果。

### 5) 结果校验与汇总

1. 校验目标卡片是否全部创建/迁移成功。
2. 重新统计项目卡片状态分布。
3. 统计本轮按 `pr_id` 聚合的变更结果（created/moved/failed）。
4. 若结果与目标集合不一致，输出 `VKTODO_RESULT_MISMATCH`。
5. 输出“做了什么 + 结果数字 + PR 维度统计 + 下一步建议（/jjk-cardrun、/jjk-imp-ws 或下一批推进）”。

### 6) 自动执行器作用域绑定（强制）

当本轮提供了 `task_split_dir` 与 `project_id` 时，必须在 `/jjk-vktodo` 结束后执行：

1. 写入 `/Users/jijingkun/.openclaw/workspace-dev/state/coder4_scope_request.json`：
   - `task_split_dir`
   - `project_id`
   - `requested_at`
   - `requested_by`
   - `applied=false`
2. 执行：
   - `python3 scripts/coder4_scope_guard.py --repo-root /Users/jijingkun/bojxAI/fastapi --active-task docs/内部参考/任务拆解/_active_task.json --scope-request /Users/jijingkun/.openclaw/workspace-dev/state/coder4_scope_request.json`
3. 回读任务级 `_active_task.json` 与活跃索引 `_active_task.json`，校验：
   - `task_split_dir` 一致
   - `project_id` 一致
   - `task_key` 与 `vk_cards.json.task_key` 一致
4. 任一失败：`FAIL_FAST` 输出 `VKTODO_SCOPE_BIND_MISMATCH`，并禁止进入 coder4 自动执行。

---

## 输出模板（推荐）

见全局模板：`/Users/jijingkun/.codex/engineering/templates/jjk_vktodo_templates.md`（`输出模板` 段）。
若本项目有覆盖规则，再查：`docs/内部参考/迭代需求/_templates/jjk_vktodo_templates.md`。

## 禁止项（强制）

1. 禁止跳过 `/jjk-vksync` 直接建卡/推进（除非显式 `allow_not_ready=true` 且有风险确认）。
2. 禁止 `project_id` 未解析成功时继续执行。
3. 禁止跳过幂等去重，导致重复建卡。
4. 禁止在 `VKTODO_RESULT_MISMATCH` 未消除时继续推进到 `/jjk-imp-ws`。
5. 禁止在 `VKTODO_PR_MAPPING_MISSING` / `VKTODO_PR_MAPPING_BROKEN` 未解除时创建或推进卡片。
6. 禁止把 `/jjk-vktodo` 当“自由编排命令”重写上游拆解语义。

## 推荐链路

`/jjk-plan -> /jjk-vkplan -> /jjk-vksync -> /jjk-vktodo -> /jjk-cardrun -> /jjk-imp-ws`

## 使用示例

```text
/jjk-vktodo 2026-02-12_skill检索对齐_cursor_mvp
```

```text
/jjk-vktodo 2026-02-12_skill检索对齐_cursor_mvp create Backlog project=fastapi
```

```text
/jjk-vktodo 2026-02-12_skill检索对齐_cursor_mvp move Doing project=fastapi
```

```text
/jjk-vktodo project=fastapi action=move move_filter=prefix:PP-20260213-TODO,top:5 status=Review
```

---
*使用 `/jjk-vktodo` 触发。目标是“契约化落卡 + 可观测兜底 + 作用域对齐”。*
