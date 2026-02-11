# 并行计划书（重生版，按 `/rwfj` 默认规则）

> 计划 ID: PP-20260210-TODO-REBUILD-V2  
> 主题: 待办隐式指代与跨模块稳定性收敛（基于最新代码）  
> 输入来源: `docs/内部参考/迭代需求/requirements.md` / `docs/内部参考/迭代需求/implementation_plan.md`

---

## 0. G0 协议冻结

### 0.1 目标

在并行拆分前冻结跨端事件契约，确保后端 owner 与前端消费者在本轮内遵循同一字段语义，避免并发开发导致协议漂移。

### 0.2 事件冻结清单

#### `done`

- required:
  - `thread_id`
  - `message_id`
- optional:
  - `final_content`
  - `meta`
- 兼容说明:
  - 新增可选字段只能追加，不得删除已有 required 字段。
  - 前端消费方在未知字段存在时必须忽略而非报错。

#### `result`

- required:
  - `type`
  - `content`
- optional:
  - `chart`
  - `table`
  - `meta`
- 兼容说明:
  - `content` 语义保持稳定，结构化数据通过可选字段扩展。

#### `interrupt`

- required:
  - `reason`
  - `message`
- optional:
  - `recoverable`
  - `suggested_action`
- 兼容说明:
  - `reason` 枚举扩展时必须保持旧值可识别；未知值按“可恢复中断”处理。

### 0.3 owner / consumer 关系

- 后端契约 owner：`WS-02_后端契约与持久化收敛`
- 前端只读 consumer：`WS-03_前端SSE与交互收敛`
- 状态语义 owner（与协议消费耦合字段）：`WS-01_后端意图与工作流收敛`

---

## 1. 并行判定（四问）

### 1.1 判定结果

1. 子任务是否可独立开始并独立交付：**是**
2. 文件白名单是否可互斥：**是**
3. 是否不存在共享状态字段语义冲突：**是（通过单写入权约束）**
4. 是否可各自完成局部验收：**是**

**结论：并行通过。**

---

## 2. 自动拆分依据

### 2.1 任务单元抽取

从主计划抽取候选单元：

1. 意图/澄清/状态收敛（workflow/state）
2. 契约/路由/持久化收敛（endpoint/service/repository/model）
3. 前端 SSE 消费与交互收敛（hooks/lib/components/types）
4. 集成回归门禁
5. 文档终稿门禁

### 2.2 冲突关系建模

- 文件重叠冲突：通过白名单互斥划分消解。
- 状态字段写入冲突：`clarify_*`、`turn_act`、`pending_operation` 归 WS-01 单写入。
- 协议字段冲突：SSE 字段定义归 WS-02 owner，WS-03 只读消费。
- 强依赖阻断：Gate 类任务依赖并行层完成，不纳入并行层。

### 2.3 自动分组结果（动态 WS）

- 并行层（可并行）：`WS-01`、`WS-02`、`WS-03`
- 串行门禁层：`WS-G1` → `WS-G2`

说明：本轮冲突图收敛为 3 个核心并行 WS + 2 个串行 Gate WS；后续轮次允许按同规则自动增减为 `WS-01...WS-N`。

---

## 3. 目标与边界

### 3.1 目标

1. 收敛待办隐式指代与意图闭环，消除重复澄清循环风险。
2. 收敛后端契约、持久化与管理能力，修复关键测试阻断。
3. 收敛前端 SSE 消费与消息类型，消除 tsc 阻断并提升交互稳定性。

### 3.2 非目标

1. 不引入全新业务域。
2. 不在并行阶段执行跨 WS 的最终门禁（放到 Gate WS）。

### 3.3 约束

1. 双数据库约束必须保持：`chat_db` 与 `data_db` 不串库。
2. 共享字段仅允许单写入权。
3. 任何 WS 不得破坏路由收敛闭环。
4. WS-01 的架构细化执行引用 `docs/内部参考/迭代需求/implementation_plan_多智能体上下文管理重构.md`。

---

## 4. 工作包总览

| WS | 名称 | 类型 | 可并行 | 依赖 |
|---|---|---|---|---|
| WS-01 | 后端意图与工作流收敛 | Backend | 是 | 无 |
| WS-02 | 后端契约与持久化收敛 | Backend | 是 | G0（协议冻结） |
| WS-03 | 前端 SSE 与交互收敛 | Frontend | 是 | G0（协议冻结） |
| WS-G1 | 集成回归门禁 | Gate | 否 | WS-01, WS-02, WS-03 |
| WS-G2 | 文档终稿门禁 | Gate | 否 | WS-G1 |

---

## 5. 冲突矩阵（互不干涉）

| 资源 | Owner WS | 其他 WS 是否可改 | 规则 |
|---|---|---|---|
| `app/ai/workflow/*` | WS-01 | 否 | 工作流单所有者 |
| `app/ai/state.py` | WS-01 | 否 | 状态契约单写入权 |
| `app/api/v1/endpoints/*` | WS-02 | 否 | 接口层单所有者 |
| `app/services/*` | WS-02 | 否 | 业务编排单所有者 |
| `app/repositories/*` | WS-02 | 否 | 持久化单所有者 |
| `web/src/hooks/useSSEStream.ts` | WS-03 | 否 | SSE 消费单所有者 |
| `web/src/lib/backend.ts` | WS-03 | 否 | 前端协议适配单所有者 |
| `web/src/types/message.ts` | WS-03 | 否 | 前端类型单所有者 |
| SSE 事件字段定义 | WS-02 | WS-03 只读 | 契约冻结后适配 |
| `clarify_*` / `turn_act` 字段语义 | WS-01 | 否 | 状态语义单写入 |

---

## 6. 依赖图与里程碑

### 6.1 依赖图

- 并行层：`WS-01 || WS-02 || WS-03`
- 串行门禁层：`WS-G1 -> WS-G2`

### 6.2 里程碑

1. M1：并行层各 WS 达成局部 DoD。
2. M2：WS-G1 完成跨模块回归与豁免清单确认。
3. M3：WS-G2 完成文档终稿与发布清单。

---

## 7. 合并策略

1. 合并顺序：`WS-01/02/03`（并行层）→ `WS-G1` → `WS-G2`
2. 回归门禁：
   - `venv/bin/python -m pytest -q --maxfail=20`
   - `cd web && npx tsc --noEmit`
   - `cd web && npm run -s lint`
   - `venv/bin/python scripts/docs_guard.py --strict`
3. 回滚策略：按 WS 粒度回滚，禁止跨 WS 混合回滚。

---

## 8. 串行回退说明（若触发）

当前结论：**未触发串行回退**（并行判定通过）。

若后续实施中出现以下任一情况，必须回退：

1. 共享关键文件无法指定唯一 owner。
2. 共享状态字段无法保证单写入权。
3. 任一 WS 必须等待其他 WS 产出才能开始。

回退路线：停止并行执行，改为单任务 `/imp` 或先做冲突消解后重跑 `/rwfj`。

---

## 9. Gate 执行状态（2026-02-10）

### 9.1 WS-G1 结果（自动回填：2026-02-10 23:50）

- `pytest`：通过（428 passed）
- `tsc`：通过
- `lint`：通过（38 warning）
- `docs_guard`：通过（0 error, 0 warning）

### 9.2 WS-G2 预期动作

1. 修复文档索引失效链接。
2. 复测 `docs_guard --strict` 并回填结果。
3. 关闭 `EX-G1-002` 文档门禁豁免项。

---

## 10. Gate 收口结果（自动回填：2026-02-10 23:50）

1. `WS-G1` 已执行：
   - `pytest` 通过（428 passed）
   - `tsc` 通过
   - `lint` 通过（38 warning）
   - `docs_guard` 通过（0 error, 0 warning）
2. `WS-G2` 已执行：
   - `docs_guard --strict` 通过（0 error, 0 warning）
3. Gate 结论：
   - 业务与文档门禁通过，可关闭本轮 Gate。
