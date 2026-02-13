# 并行计划书：Skill 检索能力对齐 Cursor（MVP）

> 计划 ID: PP-20260213-SKILL-RETRIEVAL-MVP  
> 主题: Skill 自动触发与检索链路平台化升级  
> 输入来源: `docs/内部参考/迭代需求/requirements.md` / `docs/内部参考/迭代需求/implementation_plan.md`

---

## 0. G0 协议冻结

### 0.1 冻结目标

在并行开发前冻结跨端事件契约，避免并发开发导致 `done/result/interrupt` 字段语义漂移。

### 0.2 冻结范围与约束

#### `result`

- required:
  - `type`
  - `data.data_type`
  - `data.data`
- optional:
  - `node`
  - `data.message`
- 枚举/空值约束:
  - `type` 固定为 `result`
  - `data.data_type` 非空字符串
- 兼容说明:
  - 新字段仅可追加 optional，不得变更 required 语义

#### `interrupt`

- required:
  - `type`
  - `data.thread_id`
  - `data.interrupt_id`
  - `data.value`
- optional:
  - `node`
  - `data.value.message`
  - `data.value.action_requests`
  - `data.value.review_configs`
- 枚举/空值约束:
  - `type` 固定为 `interrupt`
  - `interrupt_id` 非空字符串
- 兼容说明:
  - `value` 内仅允许追加可选字段，不得删除既有 required

#### `done`

- required:
  - `type`
  - `data.thread_id`
  - `data.message_id`
- optional:
  - `node`
  - `data.final_content`
- 枚举/空值约束:
  - `type` 固定为 `done`
  - 禁止携带结构化业务数据
- 兼容说明:
  - `done` 仅用于生命周期收口，结构化数据必须走 `result`

### 0.3 协议 owner 与消费方

- 协议 owner：`WS-00_G0_协议冻结`
- 只读消费：`WS-01`、`WS-02`、`WS-03`、`WS-04`、`WS-G1`、`WS-G2`

---

## 1. seed 来源说明

- `task_key`: `PP-20260213-SKILL-RETRIEVAL-MVP`
- `task_key` 来源：`plan`
- `card_seed` 来源：`docs/内部参考/迭代需求/implementation_plan.md`
- 推导依据与风险：
  - 本轮未做 `rwfj` 临时推导，直接消费主计划 seed。
  - 风险在于 `app/services/skill_service.py` 跨 WS 触碰，已通过 hard 依赖 + 合并顺序消解。

---

## 2. 前置可并行判定（四问）

1. 子任务可独立开始并独立交付：**是**
2. 文件白名单可做到互斥：**是（共享文件由依赖顺序串行化）**
3. 关键状态字段可保证单写入权：**是**
4. 各子任务可执行局部验证：**是**

结论：**并行通过**。

---

## 3. 自动拆分依据

### 3.1 冲突关系

1. 结构层冲突：`app/models/**` 仅归属 `WS-01`。
2. 导入与检索冲突：`app/services/skill_service.py` 由 `WS-02 -> WS-03 -> WS-04` 依赖串接。
3. 运行时注入冲突：`app/ai/workflow/multi_agent_graph.py` 仅归属 `WS-03`。
4. Gate 收口冲突：仅 `WS-G1/WS-G2` 修改 Gate 与文档文件。

### 3.2 分组结果

- Foundation：`WS-00`
- 并行交付层：`WS-01`、`WS-02`、`WS-03`、`WS-04`
- 串行门禁层：`WS-G1 -> WS-G2`

---

## 4. 工作包总览

| WS | 名称 | 类型 | 可并行 | hard 依赖 |
|---|---|---|---|---|
| WS-00 | G0 协议冻结 | Foundation | 否 | 无 |
| WS-01 | 技能元数据与迁移 | Parallel | 是 | WS-00 |
| WS-02 | SKILL 导入与 frontmatter 治理 | Parallel | 是 | WS-00, WS-01 |
| WS-03 | 混合检索与注入策略 | Parallel | 是 | WS-00, WS-01, WS-02 |
| WS-04 | 可观测与离线评测 | Parallel | 是 | WS-00, WS-03 |
| WS-G1 | 集成回归门禁 | Gate | 否 | WS-01, WS-02, WS-03, WS-04 |
| WS-G2 | 文档终稿门禁 | Gate | 否 | WS-G1 |

---

## 5. 冲突矩阵（互不干涉硬约束）

| 资源 | Owner WS | 其他 WS 是否可改 | 规则 |
|---|---|---|---|
| `app/models/agent_skill.py` | WS-01 | 否 | 模型结构单所有者 |
| `alembic/**`（本轮 skill 迁移） | WS-01 | 否 | 迁移单所有者 |
| `app/services/skill_service.py` | WS-02/WS-03/WS-04 | 否（同一时间） | 仅按 hard 依赖串行修改 |
| `app/ai/workflow/multi_agent_graph.py` | WS-03 | 否 | 注入策略单所有者 |
| `tests/**`（skill 相关） | WS-04 | 可追加不可改语义 | 回归资产 owner |
| `docs/内部参考/任务拆解/**` | WS-G1 | 部分 | 仅 Gate owner 可回填状态 |
| `docs/**`（终稿） | WS-G2 | 否（Gate 前） | 文档终稿单所有者 |

---

## 6. 依赖图与里程碑

### 6.1 依赖图

`WS-00 -> WS-01 -> WS-02 -> WS-03 -> WS-04 -> WS-G1 -> WS-G2`

### 6.2 里程碑

1. M0：`WS-00` 完成协议冻结。
2. M1：`WS-01` 元数据迁移完成。
3. M2：`WS-02` 导入治理完成。
4. M3：`WS-03` 检索与注入策略完成。
5. M4：`WS-04` 观测与评测完成。
6. M5：`WS-G1` 集成回归门禁通过。
7. M6：`WS-G2` 文档门禁通过并收口。

---

## 7. 合并策略

1. 合并顺序固定：`WS-00 -> WS-01 -> WS-02 -> WS-03 -> WS-04 -> WS-G1 -> WS-G2`。
2. 同泳道无 hard 依赖任务方可并行开发；存在 file_scope 冲突必须阻止并行。
3. Gate 卡片保持串行，不允许跳过 `WS-G1` 直接执行 `WS-G2`。

---

## 8. 串行回退说明

- 是否触发：否
- 触发条件（满足任一即触发）：
  1. `app/services/skill_service.py` 出现不可解并发冲突。
  2. `skill_context` 或 `selected_skill_ids` 出现双 owner。
  3. Gate 失败且无法定位责任 WS。
- 串行路线（回退后）：`WS-01 -> WS-02 -> WS-03 -> WS-04 -> WS-G1 -> WS-G2`

---

## 9. 看板导出索引

- `task_key`: `PP-20260213-SKILL-RETRIEVAL-MVP`
- 拆解目录 ID：`2026-02-12_skill检索对齐_cursor_mvp`
- WS 总数：`7`
- VK 落卡总数：`6`（不含 `WS-00`）
- Gate 总数：`2`
- 默认列流转：`Backlog -> Doing -> Review -> Gate -> Done`
- 卡片 ID 规则：`<task_key>::<WS-ID>`
- 卡片标题规则：`<WS-ID> <标题> [<task_key>]`
- 落卡范围：`WS-01...WS-G2`（`WS-00` 仅前置里程碑）
- 卡片列表：
  - `PP-20260213-SKILL-RETRIEVAL-MVP::WS-01`
  - `PP-20260213-SKILL-RETRIEVAL-MVP::WS-02`
  - `PP-20260213-SKILL-RETRIEVAL-MVP::WS-03`
  - `PP-20260213-SKILL-RETRIEVAL-MVP::WS-04`
  - `PP-20260213-SKILL-RETRIEVAL-MVP::WS-G1`
  - `PP-20260213-SKILL-RETRIEVAL-MVP::WS-G2`

## 10. Gate 执行记录

### 10.1 WS-G1 结果（自动回填：2026-02-13 22:27）

- `pytest`：通过（21 passed）
- `tsc`：通过
- `lint`：通过（38 warning）
- `docs_guard`：失败（4 error, 0 warning）

### 10.2 WS-G2 预期动作

- 修复 `docs/SUMMARY.md` 中以下断链后重跑 strict：
  - `内部参考/迭代需求/requirements.md`
  - `内部参考/迭代需求/implementation_plan.md`
- `docs_guard --strict` 全绿后再执行 `WS-G2` 收口。

## 11. Gate 收口结果（自动回填：2026-02-13 22:27）

1. `WS-G1` 已执行：
   - `pytest` 通过（21 passed）
   - `tsc` 通过
   - `lint` 通过（38 warning）
   - `docs_guard` 失败（4 error, 0 warning）
2. `WS-G2` 已执行：
   - `docs_guard --strict` 失败（4 error, 0 warning）
3. Gate 结论：
   - 业务门禁可通过但文档门禁未通过，请先修复文档后重跑 Gate。
