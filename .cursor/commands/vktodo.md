---
description: VK Todo 批量建卡：优先走 MCP，502 时自动切本地后端兜底
---

# VK Todo 工作流 (VK Todo Workflow)

用于在 VibeKanban 中批量创建与推进任务卡片，优先使用 MCP 工具，失败时自动兜底。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 何时使用

| 场景 | 推荐命令 |
|------|----------|
| 需要批量创建开发计划卡片 | `/vktodo` ✅ |
| 需要把一批卡片推进到 inprogress / inreview | `/vktodo` ✅ |
| 仅查看卡片列表 | 直接用 `list_tasks` |

---

## 输入约定

建议在命令中明确以下字段：

1. `project`：项目名或项目 ID（必填）
2. `action`：`create` / `move`（必填）
3. `cards`：
   - 批量编号模式：如 `OC-DY-001..OC-DY-015`
   - 或显式标题列表：如 `["OC-DY-001", "OC-DY-002"]`
4. `status`：默认 `todo`（创建时可省略）
5. `move_filter`：推进时的筛选条件（如 `prefix=P0`、`top=5`）

---

## 执行步骤

### Step 1: 解析项目与基线

1. 调用 `mcp__vibe_kanban__list_projects`，将 `project` 解析为唯一 `project_id`。
2. 调用 `mcp__vibe_kanban__list_tasks` 获取变更前统计（`todo/inprogress/inreview/done`）。

### Step 2: 优先 MCP 批量执行

1. `action=create`：循环调用 `mcp__vibe_kanban__create_task`。
2. `action=move`：先筛选目标卡片，再调用 `mcp__vibe_kanban__update_task` 修改状态。
3. 记录每张卡片的执行结果（成功 / 失败原因）。

### Step 3: MCP 502 自动兜底

当出现 `502 Bad Gateway` 或 MCP 通道不可用：

1. 明确说明 MCP 不可用，不再盲目重试。
2. 自动切换到本地 VK 后端接口做同等操作（创建或状态更新）。
3. 兜底执行时先按标题去重，避免重复建卡。
4. 兜底后再次查询任务列表，确认实际落库结果。

### Step 4: 结果校验与汇总

1. 校验目标卡片是否全部创建/迁移成功。
2. 重新统计项目任务状态分布。
3. 输出“做了什么 + 结果数字 + 下一步建议”。

---

## 输出模板（推荐）

```markdown
你说得对，VK 的 MCP 确实有这个能力（`create_task` / `update_task`）。
这边的问题是 MCP 通道返回 `502 Bad Gateway`，所以我改走了本地 VK 后端接口兜底执行。

- 已在项目 `<project_name>`（`<project_id>`）成功处理 `<N>` 张卡片：`<card_start>` 到 `<card_end>`
- 本次目标状态：`<target_status>`
- 当前任务统计：总计 `<total>` 张（`todo: <x>`，`inprogress: <y>`，`inreview: <z>`，`done: <d>`）

所以现在你的看板已同步完成。
如果你需要，我可以下一步把 `<filter>` 的 `<k>` 张卡片自动挪到 `<next_status>`。
```

---

## 使用示例

```text
/vktodo project=opencrawl action=create cards=OC-DY-001..OC-DY-015 status=todo
```

```text
/vktodo project=opencrawl action=move move_filter=prefix:P0,top:5 status=inprogress
```

---

*使用 `/vktodo` 触发。适合 VK 看板批量操作与 MCP 故障兜底场景。*
