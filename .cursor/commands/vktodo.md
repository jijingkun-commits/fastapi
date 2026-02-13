---
description: VK Todo 批量建卡：优先走 MCP（issue API），502 时自动切本地后端兜底
---

# VK Todo 工作流 (VK Todo Workflow)

用于在 Vibe Kanban 中批量创建与推进卡片，优先使用 MCP 工具，失败时自动兜底。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 何时使用

| 场景 | 推荐命令 |
|------|----------|
| 需要批量创建开发卡片 | `/vktodo` ✅ |
| 需要把一批卡片推进到 Doing/Review/Gate/Done | `/vktodo` ✅ |
| 仅查看卡片列表 | 直接用 `list_issues` |

---

## 输入约定

建议在命令中明确以下字段：

1. `project`：项目名或项目 ID（必填）
2. `action`：`create` / `move`（必填）
3. `cards`：
   - 批量编号模式：如 `PP-20260213::WS-00..PP-20260213::WS-08`
   - 或显式标题列表：如 `["PP-20260213::WS-01", "PP-20260213::WS-02"]`
4. `status`：目标列（如 `Backlog/Doing/Review/Gate/Done`）
5. `move_filter`：推进时的筛选条件（如 `prefix:PP-20260213,top:5`）

> 若卡片来源于某轮 `/rwfj` 拆解，建议先执行 `/vk <任务拆解目录>`（默认 strict）生成标准建卡内容，再由 `/vktodo` 负责落卡。

---

## 执行步骤

### Step 1: 解析项目与基线

1. 调用 `mcp__vibe_kanban__list_organizations` + `mcp__vibe_kanban__list_projects`，将 `project` 解析为唯一 `project_id`。
2. 调用 `mcp__vibe_kanban__list_issues` 获取变更前统计（按状态聚合）。

### Step 2: 优先 MCP 批量执行（issue API）

1. `action=create`：循环调用 `mcp__vibe_kanban__create_issue`。
2. `action=move`：先筛选目标卡片，再调用 `mcp__vibe_kanban__update_issue` 修改状态。
3. 记录每张卡片的执行结果（成功 / 失败原因）。
4. 建卡时建议把 `task_key` 与 `source_ws_file` 放入 description，便于追溯。

### Step 3: MCP 502 自动兜底

当出现 `502 Bad Gateway` 或 MCP 通道不可用：

1. 明确说明 MCP 不可用，不再盲目重试。
2. 自动切换到本地 VK 后端接口做同等操作（创建或状态更新）。
3. 兜底执行时先按 `card_key/title` 去重，避免重复建卡。
4. 兜底后再次查询卡片列表，确认实际落库结果。

### Step 4: 结果校验与汇总

1. 校验目标卡片是否全部创建/迁移成功。
2. 重新统计项目卡片状态分布。
3. 输出“做了什么 + 结果数字 + 下一步建议”。

---

## 输出模板（推荐）

```markdown
VK 的 MCP 可直接操作 issue（`create_issue` / `update_issue`）。
本次优先走 MCP，若返回 `502 Bad Gateway` 则自动走本地后端兜底。

- 项目：`<project_name>`（`<project_id>`）
- 已处理卡片：`<N>` 张（`<start>` 到 `<end>`）
- 目标状态：`<target_status>`
- 当前统计：总计 `<total>` 张（`Backlog: <x>`，`Doing: <y>`，`Review: <z>`，`Gate: <g>`，`Done: <d>`）

如需下一步，我可以继续把 `<filter>` 的 `<k>` 张卡片自动推进到 `<next_status>`。
```

---

## 使用示例

```text
/vktodo project=fastapi action=create cards=PP-20260213-TODO::WS-00..PP-20260213-TODO::WS-08 status=Backlog
```

```text
/vktodo project=fastapi action=move move_filter=prefix:PP-20260213-TODO,top:3 status=Doing
```

---
*使用 `/vktodo` 触发。适合 VK 看板批量操作与 MCP 故障兜底场景。*
