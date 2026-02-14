# 并行计划书：管理后台总览驾驶舱

> 计划 ID: PP-20260213-ADMIN-OVERVIEW-COCKPIT  
> 主题: 管理后台总览从入口页升级为健康驾驶舱（实时 + 容量成本）  
> 输入来源: `docs/内部参考/迭代需求/requirements.md` / `docs/内部参考/迭代需求/implementation_plan.md`

---

## 0. G0 协议冻结

### 0.1 冻结目标

在并行开发前冻结总览实时事件契约，避免前后端在 `done/result/interrupt` 字段语义上发生漂移。

### 0.2 冻结范围

1. `result`：承载总览增量数据（健康分、告警、趋势、模块矩阵等）。
2. `interrupt`：承载实时链路降级/重连原因（如 `stream_disconnected`）。
3. `done`：承载当前事件批次结束标记，不承载业务字段。

### 0.3 required/optional 与兼容约束

#### `result`

- required：`type`、`data.snapshot_at`、`data.patch`
- optional：`data.trace_id`、`node`
- 枚举与空值约束：
  - `type` 固定 `result`
  - `data.patch` 为对象，允许空对象 `{}`
- 兼容策略：仅允许追加 optional 字段，禁止改写 required 语义。

#### `interrupt`

- required：`type`、`data.reason`、`data.level`
- optional：`data.retry_after_sec`、`data.message`、`node`
- 枚举与空值约束：
  - `type` 固定 `interrupt`
  - `data.level` 枚举：`info|warning|critical`
- 兼容策略：新增原因码需向后兼容旧枚举。

#### `done`

- required：`type`、`data.batch_id`
- optional：`data.final`、`node`
- 枚举与空值约束：
  - `type` 固定 `done`
  - `data.final` 默认 `false`
- 兼容策略：`done` 仅用于流事件收口，禁止附带业务明细。

### 0.4 协议机读文件

- `docs/内部参考/任务拆解/2026-02-13_管理后台总览驾驶舱/contracts/sse_events_v1.json`

### 0.5 owner 与消费方

- 契约 owner：`WS-00_G0_协议冻结`
- 消费只读方：`WS-01`、`WS-02`、`WS-03`、`WS-04`、`WS-G1`、`WS-G2`

---

## 1. seed 来源判定

1. `task_key`：`PP-20260213-ADMIN-OVERVIEW-COCKPIT`
2. `task_key` 来源：`rwfj 推导`（主计划未提供 parallel seed）
3. `card_seed` 来源：`rwfj 推导`
4. 推导依据：
   - 来自 `implementation_plan.md` 的 CAP 列表（CAP-OV-01~05）
   - 冲突图（数据层/后端层/前端层/Gate）
5. 风险提醒：
   - 推导 seed 可能与后续实现边界有偏差，若出现跨 WS 文件冲突，以 Gate 复核后回写 `parallel_plan.md` 为准。

---

## 2. 前置可并行判定（四问）

1. 子任务可独立开始并独立交付：**是（WS-04 可在 G0 后先做 UI 框架）**
2. 文件白名单可做到互斥：**是**
3. 关键状态字段可保证单写入权：**是**
4. 各子任务可执行局部验证：**是**

结论：**并行通过（受限并行）**。  
并行层以“后端链路串行 + 前端先行骨架并行”为主，Gate 仍保持串行。

---

## 3. 自动拆分依据（冲突图）

### 3.1 冲突与依赖

1. 数据表与迁移冲突：`app/models/*` + `alembic/*` 必须单 owner（WS-01）。
2. 观测采集与聚合冲突：`app/services/*overview*` 单 owner（WS-02）。
3. API 与路由冲突：`app/api/v1/router.py`、`app/api/v1/endpoints/*` 单 owner（WS-03）。
4. 前端视图冲突：`web/src/app/admin/page.tsx` 与 `web/src/components/admin/overview/*` 单 owner（WS-04）。
5. Gate 收口冲突：测试矩阵、文档同步、落卡索引仅 Gate WS 可回写。

### 3.2 分组结果

- Foundation：`WS-00`
- 并行交付层：`WS-01`、`WS-02`、`WS-03`、`WS-04`
- 串行门禁层：`WS-G1 -> WS-G2`

---

## 4. 工作包总览

| WS | 名称 | 类型 | 可并行 | hard 依赖 |
|---|---|---|---|---|
| WS-00 | G0 协议冻结 | Foundation | 否 | 无 |
| WS-01 | 总览观测快照模型与迁移 | Parallel | 是 | WS-00 |
| WS-02 | 指标采集与健康聚合服务 | Parallel | 是 | WS-00, WS-01 |
| WS-03 | 总览 API 与 SSE 通道 | Parallel | 是 | WS-00, WS-02 |
| WS-04 | 前端驾驶舱页面与实时接入 | Parallel | 是 | WS-00, WS-03 |
| WS-G1 | 集成回归门禁 | Gate | 否 | WS-01, WS-02, WS-03, WS-04 |
| WS-G2 | 文档终稿门禁 | Gate | 否 | WS-G1 |

---

## 5. 冲突矩阵（互不干涉硬约束）

| 资源 | Owner WS | 其他 WS 是否可改 | 规则 |
|---|---|---|---|
| `app/models/ops_metric_snapshot.py` | WS-01 | 否 | 模型单所有者 |
| `alembic/versions/*ops_snapshot*` | WS-01 | 否 | 迁移单所有者 |
| `app/services/admin_overview_service.py` | WS-02 | 否 | 聚合策略单所有者 |
| `app/api/v1/endpoints/admin_overview_api.py` | WS-03 | 否 | 接口契约单所有者 |
| `app/api/v1/router.py` | WS-03 | 否 | 路由注册单所有者 |
| `web/src/app/admin/page.tsx` | WS-04 | 否 | 页面入口单所有者 |
| `web/src/components/admin/overview/*` | WS-04 | 否 | 前端组件单所有者 |
| `docs/开发文档/测试管理/管理后台测试案例.md` | WS-G2 | 否 | 文档终稿单所有者 |

---

## 6. 依赖图与里程碑

### 6.1 依赖图

`WS-00 -> WS-01 -> WS-02 -> WS-03 -> WS-04 -> WS-G1 -> WS-G2`

### 6.2 里程碑

1. M0：G0 契约冻结完成。
2. M1：观测快照表与迁移完成。
3. M2：聚合服务输出 `OverviewSnapshot`。
4. M3：summary/trends/stream 三接口可用。
5. M4：前端 8 块驾驶舱可视化接入完成。
6. M5：集成回归门禁通过。
7. M6：文档终稿门禁通过并进入落卡执行。

---

## 7. 合并策略

1. 合并顺序固定：`WS-00 -> WS-01 -> WS-02 -> WS-03 -> WS-04 -> WS-G1 -> WS-G2`。
2. 同一文件如发生越界修改，必须在 Gate 阶段阻断并回退到 owner WS。
3. 禁止跳过 `WS-G1` 直接进入 `WS-G2`。

---

## 8. 串行回退说明

- 是否触发：否
- 触发条件：
  1. `app/api/v1/router.py` 或 `web/src/app/admin/page.tsx` 发生跨 WS 并发冲突不可解。
  2. SSE 契约变更导致 WS-03/WS-04 语义不一致。
  3. G1 无法定位责任 WS。
- 回退路线：`WS-01 -> WS-02 -> WS-03 -> WS-04 -> WS-G1 -> WS-G2`

---

## 9. 看板导出索引

1. `task_key`: `PP-20260213-ADMIN-OVERVIEW-COCKPIT`
2. 拆解目录 ID：`2026-02-13_管理后台总览驾驶舱`
3. WS 总数：`7`
4. Gate 总数：`2`
5. 默认列流转：`Backlog -> Doing -> Review -> Gate -> Done`
6. 卡片 ID 规则：`<task_key>::<WS-ID>`
7. 卡片标题规则：`<WS-ID> <标题> [<task_key>]`
8. VK 落卡范围：`WS-01...WS-G2`（`WS-00` 为前置里程碑不落卡）

---

## 10. Gate 执行状态（收口）

### 10.1 WS-G1

- 结果：通过（2026-02-14）
- 阻塞项：无

### 10.2 WS-G2

- 结果：通过（2026-02-14）
- 阻塞项：无

---

## 11. Gate 收口结果（收口）

1. `WS-G1` 已执行：是
2. `WS-G2` 已执行：是
3. Gate 结论：通过（2026-02-14，docs_guard 严格模式通过）
