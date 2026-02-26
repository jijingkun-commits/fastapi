---
description: VK Todo 批量建卡：强制基线校验后落卡，优先走 MCP（issue API），502 时自动切本地后端兜底
---

# VK Todo 工作流 (VK Todo Workflow)

用于在 Vibe Kanban 中批量创建与推进卡片，优先使用 MCP 工具，失败时自动兜底。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 何时使用

| 场景 | 推荐命令 |
|------|----------|
| 需要批量创建开发卡片 | `/jjk-vktodo` ✅ |
| 需要把一批卡片推进到 Doing/Review/Gate/Done | `/jjk-vktodo` ✅ |
| 仅查看卡片列表 | 直接用 `list_issues` |

> 多 worktree 场景：`/jjk-vktodo` 默认执行基线硬拦截；存在未同步 worktree 时直接失败。

---

## 命名衔接（与 `/jjk-plan`、`/jjk-vkplan` 强一致）

1. `/jjk-vktodo` 处理的 `task_split_dir` 必须来自同主题链路：`/jjk-plan -> /jjk-vkplan`。
2. 主题一致性要求：
   - 迭代需求文档：`docs/内部参考/迭代需求/<主题>_requirements.md`、`docs/内部参考/迭代需求/<主题>_implementation_plan.md`
   - 拆解目录：`docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/`
3. 若检测到“拆解目录主题”与“来源文档主题”语义不一致，`action=create|move` 默认直接失败（除非显式应急放行并记录风险）。
4. 不得回退依赖旧通用名 `requirements.md` / `implementation_plan.md` 作为主输入。

---

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

### 3) 自动推断规则（新增）

当提供 `task_split_dir` 且未显式提供 `cards` 时：

1. 默认读取 `<task_split_dir>/vk_cards.json` 作为建卡输入。
2. `action=create` 时，自动使用 `vk_cards.json.cards[*]`：
   - 卡片 ID 与标题：来自 JSON
   - 依赖关系：优先使用 `hard_depends_on`
   - 状态：若未传 `status`，使用卡片内 `column`
3. `action=move` 时，若未传 `move_filter`，从 `vk_cards.json.task_key` 推导：
   - `move_filter=prefix:<task_key>`
4. 若 `vk_cards.json` 缺失：直接失败并提示先执行 `/jjk-vkplan` 重新生成并行拆解产物。
5. 若 `vk_cards.json` 结构非法：直接失败并提示人工修复拆解产物。
6. `vk_cards.json.cards[*]` 默认仅包含可落卡工作包（`WS-01...WS-G2`），不包含 `WS-00`。

> 推荐最短链路：`/jjk-plan -> /jjk-vkplan -> /jjk-vktodo <任务拆解目录>`

---

## 执行步骤

### Step 0: G0 基线前置校验（必做）

1. 执行 `/jjk-vksync <task_split_dir_or_path> check`，获取 READY / NOT_READY 清单。
2. 默认行为：若存在 `NOT_READY`，立即失败并停止 `/jjk-vktodo`。
3. 仅当显式传入 `allow_not_ready=true` 时，允许继续；输出“风险确认”并记录跳过原因。
4. 未显式确认风险时，不得创建/推进任何卡片。

### Step 1: 解析来源目录、项目与基线

1. 若传入 `task_split_dir`（或位置参数），先按路径规则解析并校验目录合法性。
2. 校验命名衔接：`task_split_dir` 中 `<主题>` 必须与 `/jjk-plan` / `/jjk-vkplan` 产物保持一致（`parallel_plan.md`、`vk_cards.json`、WS 来源字段）。
3. 若未传 `cards`，尝试读取 `<task_split_dir>/vk_cards.json`；缺失则直接失败并提示先执行 `/jjk-vkplan` 重新生成。
4. 调用 `mcp__vibe_kanban__list_organizations` + `mcp__vibe_kanban__list_projects`，将 `project` 解析为唯一 `project_id`（若 workspace 已绑定项目可省略）。
5. 调用 `mcp__vibe_kanban__list_issues` 获取变更前统计（按状态聚合）。

### Step 2: 组装执行清单

1. `action=create`：
   - 若传了 `cards`，按 `cards` 生成目标清单。
   - 若没传 `cards`，按 `vk_cards.json.cards[*]` 生成目标清单。
   - 若传入列表中包含 `WS-00`，自动忽略并提示“WS-00 为前置里程碑，不落卡”。
2. `action=move`：
   - 若传了 `move_filter`，按 `move_filter` 筛选。
   - 若没传 `move_filter` 且有 `vk_cards.json.task_key`，自动使用 `prefix:<task_key>`。
3. 若 create/move 均无法得到目标卡片集合，直接失败并提示补参数。

### Step 3: 优先 MCP 批量执行（issue API）

1. `action=create`：循环调用 `mcp__vibe_kanban__create_issue`。
2. `action=move`：先筛选目标卡片，再调用 `mcp__vibe_kanban__update_issue` 修改状态。
3. 记录每张卡片执行结果（成功 / 失败原因）。
4. 建卡时必须把机读增强字段写入 description（若存在）：
   - `feature_ids`
   - `mechanism_summary`
   - `code_anchor_refs`
   - `acceptance_checks`
   - `rollback_anchors`
   - `evidence_entry`
5. 若 `vk_cards.json` 中存在 `execution_mode=serial`，建卡后默认只推进首张卡到 Doing，其余保持 Backlog。

### Step 4: MCP 502 自动兜底

当出现 `502 Bad Gateway` 或 MCP 通道不可用：

1. 明确说明 MCP 不可用，不再盲目重试。
2. 自动切换到本地 VK 后端接口做同等操作（创建或状态更新）。
3. 兜底执行时先按 `card_key/title` 去重，避免重复建卡。
4. 兜底后再次查询卡片列表，确认实际落库结果。

### Step 5: 结果校验与汇总

1. 校验目标卡片是否全部创建/迁移成功。
2. 重新统计项目卡片状态分布。
3. 输出“做了什么 + 结果数字 + 下一步建议”。

### Step 6: 自动执行器作用域绑定（新增，强制）

当本轮提供了 `task_split_dir` 与 `project_id` 时，必须在 `/jjk-vktodo` 结束后执行：

1. 写入 `/Users/jijingkun/.openclaw/workspace-dev/state/coder4_scope_request.json`：
   - `task_split_dir`
   - `project_id`
   - `requested_at`
   - `requested_by`
   - `applied=false`
2. 执行：
   - `python3 scripts/coder4_scope_guard.py --repo-root /Users/jijingkun/bojxAI/fastapi --active-task docs/内部参考/任务拆解/_active_task.json --scope-request /Users/jijingkun/.openclaw/workspace-dev/state/coder4_scope_request.json`
3. 回读 `_active_task.json`，校验：
   - `task_split_dir` 一致
   - `project_id` 一致
   - `task_key` 与 `vk_cards.json.task_key` 一致
4. 任一失败：`FAIL_FAST`，并禁止进入 coder4 自动执行。

---

## 输出模板（推荐）

```markdown
VK 的 MCP 可直接操作 issue（`create_issue` / `update_issue`）。
本次优先走 MCP，若返回 `502 Bad Gateway` 则自动走本地后端兜底。

- 项目：`<project_name>`（`<project_id>`）
- 来源目录：`<task_split_dir_or_path>`（可选，若使用路径直传）
- 已处理卡片：`<N>` 张（`<start>` 到 `<end>`）
- 目标状态：`<target_status>`
- 当前统计：总计 `<total>` 张（`Backlog: <x>`，`Doing: <y>`，`Review: <z>`，`Gate: <g>`，`Done: <d>`）

如需下一步，我可以继续把 `<filter>` 的 `<k>` 张卡片自动推进到 `<next_status>`。
```

---

## 使用示例

```text
/jjk-vktodo project=fastapi action=create cards=PP-20260213-TODO::WS-01..PP-20260213-TODO::WS-08 status=Backlog
```

```text
/jjk-vktodo project=fastapi action=move move_filter=prefix:PP-20260213-TODO,top:3 status=Doing
```

```text
/jjk-vktodo 2026-02-12_skill检索对齐_cursor_mvp
```

```text
/jjk-vktodo 2026-02-12_skill检索对齐_cursor_mvp create Backlog project=fastapi
```

```text
/jjk-vktodo 2026-02-12_skill检索对齐_cursor_mvp move Doing project=fastapi
```

---
*使用 `/jjk-vktodo` 触发。适合 VK 看板批量操作与 MCP 故障兜底场景。*
