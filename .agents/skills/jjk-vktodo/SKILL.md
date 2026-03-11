---
name: jjk-vktodo
description: "Use when you need `jjk-vktodo` in this repository. Source intent: VK 建卡入口（create-only）：消费 /jjk-vkplan 契约并幂等落卡"
---
<!-- AUTO-GENERATED: jjk-skill-mirror -->
<!-- source: .cursor/commands/jjk-vktodo.md -->

> 参考规则: @dual-database

# VK Todo 建卡工作流 (Create-Only)

`$jjk-vktodo` 是 `jjk-*` 体系里的建卡入口，职责仅限把 `jjk-vkplan` 产出的 `vk_cards.json` 幂等落到 Vibe Kanban。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 与 Superpowers / OMX 的分工（强制）
## 跨 IDE 调用方式
## 输入前置（强制）

1. `task_split_dir` 必须可解析且目录存在：
   - `workdocs/任务拆解/<task_split_dir>/contracts/vk_cards.json`
   - `workdocs/任务拆解/<task_split_dir>/parallel_plan.md`（可选；自动生成总览）
2. `vk_cards.json` 必须可解析且包含：
   - `task_key`
   - `cards[]`
3. `project_id` 必须可确定：
   - 优先显式参数 `project`；
   - 否则读取 `workdocs/任务拆解/<task_split_dir>/contracts/_active_task.json`。
4. 若无法解析 `project_id`，`FAIL_FAST` 输出 `VKTODO_MISSING_PROJECT_ID`。
5. 若 `vk_cards.json` 结构非法，`FAIL_FAST` 输出 `VKTODO_INPUT_INVALID`。
6. 若调用参数包含 `action!=create`，`FAIL_FAST` 输出 `VKTODO_ACTION_NOT_ALLOWED`。

## 输入约定（create-only）

### 1) 位置参数（推荐）

`$jjk-vktodo <task_split_dir_or_path> [create]`

- 第 1 个参数：任务拆解目录（目录名/相对路径/绝对路径）
- 第 2 个参数（可选）：`create`（仅允许该值）

### 2) 键值参数

1. `task_split_dir`：任务拆解目录
2. `project`：项目名或项目 ID（可选）
3. `action`：仅允许 `create`
4. `cards`：可选卡片子集（未传则默认使用 `vk_cards.json.cards[*]`）

---

## 执行流程（强制顺序）

### 0) 上下文解析

补充执行约束：执行命令时统一遵循 `.cursor/rules/core.mdc` 的“命令执行拆分”规则：单步单目标、失败只重跑当前步、长任务只轮询不重启、输出截断时优先拆短当前步。

1. 解析 `task_split_dir` 与 `project_id`。
2. 读取 `vk_cards.json` 与任务级 `_active_task.json`，校验 `task_key/task_split_dir` 一致性。
3. 若冲突，`FAIL_FAST` 输出 `VKTODO_ACTIVE_TASK_MISMATCH`。

### 1) 组装建卡清单

1. 默认目标集合：`vk_cards.json.cards[*]`。
2. 若显式传入 `cards`，按传入子集过滤。
3. 目标集合为空时，`FAIL_FAST` 输出 `VKTODO_EMPTY_TARGET_SET`。

### 2) 幂等建卡（MCP 优先）

1. 优先调用 `mcp__vibe_kanban__create_issue` 建卡。
2. 建卡前必须按 `task_key + card_id` 做幂等去重，禁止重复建卡。
3. 建卡 description 必须写入机读关键字段（若存在）：
   - `feature_ids`
   - `mechanism_summary`
   - `acceptance_checks`
   - `rollback_anchors`
   - `evidence_entry`
   - `pr_id`
   - `pr_branch`
   - `pr_depends_on`
   - `pr_subject`

### 3) MCP 不可用兜底

1. MCP 502 或不可用时，输出：
   - `VKTODO_MCP_502_FALLBACK` 或
   - `VKTODO_MCP_UNAVAILABLE_FALLBACK`
2. 切换本地 VK 接口执行等价建卡。
3. 执行后再次查询确认建卡结果，避免误报成功。

### 4) 结果校验与汇总

1. 校验目标卡片是否全部创建成功。
2. 若结果与目标不一致，输出 `VKTODO_RESULT_MISMATCH`。
3. 输出：创建数量、跳过数量（幂等去重）、失败数量、失败原因。

---

## 输出模板（强制）

用户可见输出必须使用三行：

1. `结论: <PASS|BLOCKED|FAIL> + 建卡结果`
2. `当前动作: create-only 建卡 + 幂等统计`
3. `证据: <project_id/task_split_dir/成功与失败明细>`

## 禁止项（强制）

1. 禁止 `action=move` 或任何状态推进动作。
2. 禁止在本命令写入 scope_request 或切换 active_task。
3. 禁止跳过幂等去重直接批量建卡。
4. 禁止在 `VKTODO_RESULT_MISMATCH` 未解除时宣称“建卡完成”。

## 推荐链路

`$jjk-plan -> $jjk-vkplan -> $jjk-vktodo(create-only) -> $jjk-cardrun(loop)`

## 使用示例

```text
$jjk-vktodo 2026-03-01_用户个性化永久记忆与管理能力
```

```text
$jjk-vktodo 2026-03-01_用户个性化永久记忆与管理能力 create
```

```text
$jjk-vktodo task_split_dir=2026-03-01_用户个性化永久记忆与管理能力 action=create project=fastapi
```

---
*使用 `$jjk-vktodo` 触发。目标是“create-only 幂等建卡”，不负责状态推进与作用域切换。*
