# 并行计划书：AI 工具治理架构并行拆解

> 计划 ID: PP-20260216-TOOL-GOVERNANCE
> 主题: AI 工具治理架构（Registry + Policy + Hook + 编排接入）
> 输入来源: `docs/内部参考/迭代需求/requirements.md` / `docs/内部参考/迭代需求/implementation_plan.md`

---

## 0. G0 协议冻结

### 0.1 冻结目标

在并行开发前冻结 `done/result/interrupt` 事件契约，确保 Registry/Policy/Hook 改造期间不引入前后端协议漂移。

### 0.2 冻结范围

1. 事件集合：`done`、`result`、`interrupt`。
2. 语义约束：`done` 只用于生命周期收口，`result` 用于业务结果，`interrupt` 用于人工确认与中断态。
3. 兼容约束：仅允许追加 optional 字段，不允许改变 required 语义。

### 0.3 required/optional 与 owner/consumer

1. 契约 owner：`WS-00`。
2. 消费只读方：`WS-01`、`WS-02`、`WS-03`、`WS-G1`。
3. required 字段冻结：
   - `done`：`type`、`data.thread_id`、`data.message_id`
   - `result`：`type`、`data.data_type`、`data.data`
   - `interrupt`：`type`、`data.thread_id`、`data.interrupt_id`、`data.value`
4. optional 预留：`data.tool_call_id` 仅作为 Phase 3 可选扩展字段。

### 0.4 机读契约

- 协议文件：`docs/内部参考/任务拆解/2026-02-16_AI工具治理架构并行拆解/contracts/sse_events_v1.json`

---

## 1. seed 来源

- `task_key`: `PP-20260216-TOOL-GOVERNANCE`
- 来源：`vkplan 推导`（本轮 `/plan core` 未强制产出 `card_seed`）
- `card_seed` 来源：`implementation_plan.md` 的分阶段路线图 + 代码改造清单 + 门禁章节
- 推导依据与风险：按“先治理底座、再钩子、后编排接线、最后 Gate 收口”拆分；风险在于 WS-02 与 WS-03 存在轻度接线耦合

---

## 2. 目标与边界

### 2.1 目标

1. 交付 Phase 1 的 `Registry + Policy + PolicyStore` 并接入配置契约。
2. 交付 Phase 2 的 Hook 与审计接线基础能力。
3. 在不破坏现有 `chat/stream` 语义前提下完成编排接入与回归闭环。

### 2.2 非目标

1. 不在本轮实现 Phase 4 的并发隔离与取消传播全量能力。
2. 不在本轮引入新的对外业务 API。
3. 不在本轮强制升级为 `start/update/result` 三阶段事件协议。

### 2.3 约束（架构/性能/合规）

1. 双数据库约束不变：治理配置仅来自 `chat_db`，`data_db` 只承载分析查询。
2. 特性开关必须可回退：`TOOL_GOVERNANCE_ENABLED`、`TOOL_HOOKS_ENABLED`。
3. 热路径性能回归控制在主计划既定范围内（首 token 时延误差 ±5%）。

---

## 3. 架构冻结项（并行前必须确认）

1. 模块边界：
   - `WS-01` 负责治理底座（Registry/Policy/PolicyStore/配置契约）。
   - `WS-02` 负责 Hook 与审计能力，避免侵入业务图逻辑。
   - `WS-03` 负责 `multi_agent_graph` 与 `chat_service` 接线及回归闭环。
2. 状态契约：
   - 输入上下文 canonical：`user_id`、`thread_id`、`agent_name`、`scene_key`、`role_codes`。
   - 输出 canonical：`allowed_tools`、`decision_trace`、`fallback_reason`。
3. 路由闭环：
   - `workflow -> registry -> policy_pipeline -> allowed_tools -> tool execution`。
4. 前后端链路时序：
   - 发送前完成上下文注入。
   - `done/result/interrupt` 契约在本轮保持稳定，消费者按只读处理。

---

## 4. 工作包总览

| WS | 名称 | 类型 | 可并行 | 依赖 |
|---|---|---|---|---|
| WS-00 | G0 协议冻结 | foundation | 否 | 无 |
| WS-01 | 工具注册中心与策略管线落地 | parallel | 是 | WS-00 |
| WS-02 | 工具调用钩子与审计链路接线 | parallel | 是 | WS-01 |
| WS-03 | 编排接入与回归测试闭环 | parallel | 是 | WS-01（硬），WS-02（软） |
| WS-G1 | 集成回归门禁 | gate | 否 | WS-01, WS-02, WS-03 |
| WS-G2 | 文档终稿门禁 | gate | 否 | WS-G1 |

---

## 5. 冲突矩阵（互不干涉）

| 资源 | Owner WS | 其他 WS 是否可改 | 规则 |
|---|---|---|---|
| `contracts/sse_events_v1.json` | WS-00 | 否 | 契约单所有者 |
| `app/ai/tools/registry.py`、`app/ai/tools/policy.py`、`app/ai/tools/policy_store.py` | WS-01 | 否 | 治理底座单所有者 |
| `app/ai/tools/hooks.py`、`app/services/tool_audit_service.py` | WS-02 | 否 | Hook/审计单所有者 |
| `app/ai/workflow/multi_agent_graph.py` | WS-03 | 否 | 编排接线单所有者 |
| `parallel_plan.md` Gate 回填区块 | WS-G1 / WS-G2 | 否 | Gate 串行写入 |

---

## 6. 依赖图与里程碑

- 依赖图：`WS-00 -> WS-01 -> WS-02 -> WS-G1 -> WS-G2`，其中 `WS-03` 为 `hard_dep: WS-01`、`soft_dep: WS-02`
- 里程碑：
  1. M1：完成 G0 契约冻结并发布机读文件（WS-00）
  2. M2：完成 Registry + Policy + DB 策略源接入（WS-01）
  3. M3：完成 Hook 与审计链路可开关运行（WS-02）
  4. M4：完成编排接入与集成回归（WS-03）
  5. M5：完成 Gate 收口与文档终稿（WS-G1/WS-G2）

---

## 7. 合并策略

1. 合并顺序：`WS-01 -> WS-02 -> WS-03 -> WS-G1 -> WS-G2`。
2. 回归门禁：G1 必须覆盖单元、集成、API 与文档门禁。
3. 回滚策略：优先按 WS 粒度回滚；若发生系统性异常，使用治理开关回退旧链路。

---

## 8. 串行回退说明（若触发）

- 是否触发：否（初始）
- 触发条件：
  1. `done/result/interrupt` 契约在实现阶段出现语义分歧。
  2. `WS-02` 与 `WS-03` 出现共享文件冲突且无法在一次迭代内收敛。
- 串行路线：`WS-01 -> WS-02 -> WS-03` 单线推进，再进入 Gate。

---

## 9. 看板导出索引

- `task_key`: `PP-20260216-TOOL-GOVERNANCE`
- 拆解目录 ID: `2026-02-16_AI工具治理架构并行拆解`
- WS 总数: 6（其中 Gate 2，Foundation 1）
- Gate 总数: 2
- 默认列流转：`Backlog -> Doing -> Review -> Gate -> Done`
- 卡片 ID 规则：`<task_key>::<WS-ID>`
- 卡片标题规则：`<WS-ID> <标题> [<task_key>]`

---

## 10. Gate 执行状态

### 10.1 WS-G1 结果（待回填）

- `pytest`：待执行
- `api`：待执行
- `docs_guard`：待执行

### 10.2 WS-G2 预期动作

1. 同步 `AI模块设计.md`、配置说明与 `.env.example`。
2. 回填 `implementation_plan.md` 与 `parallel_plan.md` 的执行状态。
3. 执行 `python3 scripts/docs_guard.py --strict` 并记录结果。

---

## 11. Gate 收口结果（待回填）

1. `WS-G1` 已执行：待回填
2. `WS-G2` 已执行：待回填
3. Gate 结论：待回填
