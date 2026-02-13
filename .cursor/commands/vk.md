---
description: VK 看板生成：基于 /rwfj 产物生成建卡内容与导入提示词（默认 strict，严格读取 card_export）
---

# VK 工作流 (VK Workflow)

用于把 `/rwfj` 的拆解结果转成“可直接导入 Vibe Kanban 的卡片内容 + 提示词”。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 何时使用

| 场景 | 推荐命令 |
|------|----------|
| 已完成 `/rwfj`，需要审阅看板导出内容 | `/vk` ✅ |
| 需要直接落卡（默认路径） | `/vktodo` |
| 需要一体化导出+落卡 | `/vkkb` |

> 默认并行链路：`/plan -> /vkplan -> /vktodo`（或 `/vkkb`）；无需强制单独执行 `/vk`。

---

## 输入约定（支持无参数名）

### 1) 位置参数（推荐）

`/vk <task_split_dir_or_path> [mode]`

- 第 1 个参数：任务拆解目录（无需写 `task_split_dir=`）
- 第 2 个参数（可选）：`mode`，可选 `strict` / `auto`
- 若不传 `mode`，默认 `strict`
- 当仅传 1 个参数且值为 `auto` 或 `strict` 时，视为 `mode`

### 2) 兼容键值参数（可选）

- `task_split_dir=...`
- `mode=strict|auto`
- `project=...`

### 3) 路径规则（关键）

优先级与推荐顺序如下：

1. **目录名（推荐）**：`2026-02-12_文档治理`
   - 默认相对到：`docs/内部参考/任务拆解/`
2. **仓库相对路径（可用）**：`docs/内部参考/任务拆解/2026-02-12_文档治理`
3. **绝对路径（可用，但需校验）**：`/abs/.../docs/内部参考/任务拆解/2026-02-12_文档治理`

约束：解析后的真实路径必须落在 `docs/内部参考/任务拆解/` 目录树内，否则报错并停止。

---

## 模式语义（新增）

### strict（默认，推荐）

- 必须读取到：
  - `parallel_plan.md` 的 `## 9. 看板导出索引`
  - 每个 WS 的 `card_export`
  - `task_key`
- 任一缺失：直接失败（fail-fast），**不做文本推断回退**。

### auto（兼容老文档）

- 优先读取 `card_export`。
- 若缺失，可回退按 WS 文本结构推断；但输出必须标注“推断模式，存在风险”。

---

## 执行步骤

### Step 1: 确认来源拆解目录（关键）

必须先唯一确认“本次生成看板对应哪一轮任务拆解”：

1. 解析输入优先级：
   - `task_split_dir=`（若存在）
   - 否则读取位置参数
2. 位置参数解析规则：
   - 若仅 1 个参数且值为 `auto|strict`，则识别为 `mode`
   - 其他情况，第 1 参数识别为来源目录，第 2 参数（如有）识别为 `mode`
3. 若有来源目录：直接按路径规则解析并校验。
4. 若无来源目录：
   - `mode=strict`（默认）→ 直接报错，要求补目录
   - `mode=auto` → 自动选择“最新且包含 `parallel_plan.md` + `workstreams/WS-*.md`”目录
5. 若存在多个候选且无法唯一确定：输出候选列表并停止，不得盲选。

> 结论：输出开头必须明确“来源目录 = xxx”。

### Step 2: 读取拆解产物

读取以下文件：

1. `parallel_plan.md`
2. `workstreams/WS-*.md`

解析顺序：
1. 读取 `task_key` 与看板导出索引
2. 读取每个 WS 的 `card_export`
3. 组装依赖图（优先 `hard_depends_on`，兼容 `depends_on`）
4. 默认过滤 `WS-00`（Foundation 前置里程碑，不进入 VK 落卡清单）

### Step 3: 生成看板卡片 payload

输出字段至少包含：

- `id`（必须为 `<task_key>::<WS-ID>`）
- `title`（必须为 `<WS-ID> <标题> [<task_key>]`）
- `column`（默认 `Backlog`，`gate` 类型默认 `Gate`）
- `priority`
- `labels`（至少包含 `task_key` 与拆解目录 ID）
- `hard_depends_on`
- `soft_depends_on`
- `file_scope`
- `dod`
- `check_cmd`
- `source_ws_file`

### Step 4: 生成导入提示词

生成 1 条可直接喂给 Vibe Kanban 的提示词，要求其：

1. 仅按 `hard_depends_on` 建立阻塞依赖。
2. 同泳道且无 hard 依赖卡片标记为可并行。
3. Gate 卡保持串行。
4. 若 `file_scope` 冲突，提示阻止并行。

### Step 5: 失败回退

当 `/vk` 解析失败或看板导入失败时：

1. 明确失败点（目录确认失败 / 缺 `task_key` / 缺 `card_export` / 导入失败）。
2. 提供“最小可执行输入”（例如补 `task_split_dir` 或补齐 `card_export`）。
3. 引导使用 `/vktodo` 或 `/vkkb` 进行落卡兜底。

---

## 输出模板（推荐）

```markdown
## VK 来源确认
- 来源任务拆解目录: `<task_split_dir_or_path>`
- 解析后的标准路径: `<resolved_path>`
- 解析模式: `strict|auto`
- 解析文件数: `parallel_plan.md + WS-*.md(<N>)`

## 建卡内容（JSON）
[ ... ]

## Vibe Kanban 导入提示词
...

## 失败回退
- 若导入失败，执行：`/vktodo ...`
```

---

## 使用示例

```text
/vk 2026-02-12_文档治理
```

```text
/vk 2026-02-12_文档治理 auto
```

```text
/vk auto
```

---

*使用 `/vk` 触发。适合把 `/rwfj` 结果转成看板导入内容。*
