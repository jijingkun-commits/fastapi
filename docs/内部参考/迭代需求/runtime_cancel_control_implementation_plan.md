# 运行时可取消控制实施方案（P1）

> 文档状态：实施基线（`/jjk-plan core`）
> 更新时间：2026-02-20
> 对应总控：`docs/内部参考/迭代需求/openclaw全量迁移_implementation_plan.md`

---

## 1. 方案概览

目标：把“前端停止按钮”升级为“后端可控中断能力”。

交付：

1. 每次流式请求具备唯一 `run_id`。
2. 提供取消接口：`POST /api/v1/chat/runs/{run_id}/cancel`（权威口径）。
3. SSE 提供可机器识别的 `stopped` 事件。
4. 取消后停止继续产出，且保留已生成内容。

---

## 2. 架构影响与边界

1. 仅增量接线，不重写现有图编排。
2. 兼容现有 `done/result/interrupt` 消费路径。
3. 取消失败不影响服务可用性，但必须记录审计日志。

---

## 3. 数据与状态设计

### 3.1 模型

新增 `t_chat_run`（建议字段）：

1. `run_id`（唯一）
2. `thread_id`
3. `user_id`
4. `status`（`running/stopping/stopped/completed/failed`）
5. `cancel_reason`
6. `created_at/updated_at`

### 3.2 状态流转

1. `running -> stopping -> stopped`
2. `running -> completed`
3. `running -> failed`
4. `stopping` 超时（建议 5~10s）触发兜底：进入 `stopped` 并记录 `cancel_timeout`。

### 3.3 取消权限与幂等

1. 仅允许 run 所属 `user_id` 或管理员取消。
2. 取消接口幂等：重复取消返回相同 accepted 语义。
3. 对 `completed/failed/stopped` run 的取消请求返回“已终态”，不触发二次状态变更。

### 3.4 软/硬取消分级

1. 默认软取消：设置取消标记并在节点检查点安全退出。
2. 超时或阻塞时升级硬取消：终止流输出并强制收口状态。
3. 必须记录 `cancel_mode`（soft/hard）与触发原因，便于审计。

---

## 4. 代码改造点

1. `app/models/chat_run.py`（新增模型）
2. `app/services/run_control_service.py`（run 生命周期与取消执行）
3. `app/services/chat_service.py`（run 注册、取消检查、终止收口）
4. `app/ai/workflow/multi_agent_graph.py`（节点级 `is_cancelled` 检查）
5. `app/schemas/chat.py`（`run_id`）
6. `app/api/v1/endpoints/chat_api.py`（取消接口）

---

## 5. SSE 与 API 契约

### 5.1 流式事件

新增：

```json
{
  "type": "stopped",
  "data": {
    "thread_id": "...",
    "run_id": "...",
    "reason": "user_cancelled"
  }
}
```

约束：

1. `stopped` 为新增兼容事件，不替代 `done`。
2. 终止后不得继续发送 `token`。
3. 发送顺序：`stopped` 先于最终收口事件；若已发送 `stopped`，不得再发送含新内容的 `done.final_content`。
4. `stopped` 与 `error` 互斥：同一次 run 优先保留最先收口事件并在 `meta` 标记原因。

### 5.2 取消接口

`POST /api/v1/chat/runs/{run_id}/cancel`

返回：

1. `accepted=true`（状态进入 `stopping`）
2. 幂等取消返回相同语义

### 5.3 Resume 语义约束

1. 被 `stopped` 的 run 不允许继续 `resume` 到同一执行上下文。
2. 后续用户输入应创建新 run，并复用 thread 历史而非旧 run 继续。
3. 若处于 HITL interrupt，取消后再 resume 必须返回明确提示（需重新发起）。

### 5.4 文档引用规范（防漂移）

1. 本专题默认以函数/模块锚点引用实现，不以固定行号作为唯一定位依据。
2. 涉及取消链路时，统一引用：`chat_api.py` 取消路由、`chat_service.py` 流式收口、`multi_agent_graph.py` 节点取消检查。

---

## 6. 测试计划

1. `tests/api/test_chat_api.py`：取消接口幂等、权限、状态码。
2. `tests/unit/test_run_control_service.py`：状态流转与并发取消。
3. `tests/unit/test_chat_service_cancel_stream.py`：流中取消即停。
4. `tests/unit/test_chat_service_resume_after_cancel.py`：取消后 resume 行为。

### 6.1 观测指标（最低集）

1. `cancel_success_rate`：取消成功率。
2. `cancel_stop_latency_ms`：从 cancel 请求到停止事件的时延。
3. `cancel_after_token_count`：取消后新增 token 数（目标为 0）。
4. `cancel_hard_fallback_rate`：软取消升级硬取消占比。

---

## 7. 发布与回滚

开关建议：

1. `ENABLE_RUN_CONTROL`
2. `ENABLE_SSE_STOPPED_EVENT`

回滚策略：

1. 关闭开关回退旧路径。
2. 保留 `t_chat_run` 表结构，不做回滚删除。

---

## 8. 与总控迁移方案映射

对应总控文档：`docs/内部参考/迭代需求/openclaw全量迁移_implementation_plan.md`

1. 批次映射：本专题作为 P1 前置能力，优先于原 Batch-1/2 功能开发。
2. 退出条件：取消接口、SSE stopped、测试与回滚开关全部落地。
3. 风险控制：SSE 契约采用新增字段方式，避免破坏现有前端消费。

---

## 9. C00 预检卡（P1 开工前强制）

卡片名称：`[C00] 迁移前置四风险修订收口`

阻断规则：`C00` 未通过前，不得进入 `[P1-01]`。

预检项（全部必过）：

1. `evidence` 门禁按 `task_mode/requires_evidence` 启用（闲聊不误伤）。
2. 模型 fallback 入口统一为 `LLMSceneService.resolve_model_code` 链路。
3. `Plugin Registry` 后置，不阻塞 `P1~P4` 主线。
4. 引用由行号改为函数/模块锚点，避免漂移。

`C00` 验收 DoD（全部满足才可结单）：

1. 变更文件：`迁移执行波次_implementation_plan.md`、`openclaw全量迁移_implementation_plan.md`、`runtime_cancel_control_implementation_plan.md` 同步完成。
2. 测试用例：执行 `python3 scripts/docs_guard.py --strict` 通过。
3. 回滚开关：`ENABLE_RUN_CONTROL`、`ENABLE_SSE_STOPPED_EVENT` 仍可独立回滚且语义不变。
4. 证据链接：Gate 看板条目与 P1 工单条目已回填，且可追踪到同一责任人/日期。

执行记录（2026-02-20）：

1. DoD-1：通过。
2. DoD-2：通过（docs_guard 严格模式 `errors=0, warnings=0`）。
3. DoD-3：通过（回滚开关保持不变）。
4. DoD-4：通过（Gate 看板与工单模板已回填）。

结论：`C00` 已通过，允许进入 `[P1-01]`。

说明：跨波次执行状态以 `迁移执行波次_implementation_plan.md` 为唯一权威；本文仅维护 P1 细节、测试证据与工单模板。

---

## 10. P1 工单拆解模板（可直接贴 Jira/飞书）

统一字段模板：

1. 工单标题：`[P1-xx] <模块> <动作>`
2. 责任人：
3. 前置依赖：
4. 输入：涉及文件与上下文约束
5. 输出：代码变更、契约变更、开关变更
6. 验收标准：测试用例 + 观测指标 + 回滚演练
7. 回滚方案：对应开关与数据兼容策略
8. 回查记录四元组（触发时强制）：`卡点`、`回查来源`、`结论`、`代码改动`
9. Gate 关联：对应 `G-1/G-2/G-3/G-4` 并回填状态链接

推荐拆分（本周执行顺序）：

1. `[P1-01] chat_run 模型落地`
   - 输入：`app/models/chat_run.py`、数据库设计约束。
   - 输出：`run_id/thread_id/user_id/status/cancel_reason/created_at/updated_at` 模型与迁移脚本。
   - 验收：重复创建 run 不破坏唯一性，状态枚举与索引可用。
2. `[P1-02] run_control_service 取消控制面`
   - 输入：`app/services/run_control_service.py`。
   - 输出：`running -> stopping -> stopped` 状态流转、幂等取消、超时硬取消兜底。
   - 验收：并发取消与终态重复取消均通过，审计字段完整。
3. `[P1-03] chat_api 取消接口`
   - 输入：`app/api/v1/endpoints/chat_api.py`。
   - 输出：`POST /api/v1/chat/runs/{run_id}/cancel`，包含权限校验与幂等返回语义。
   - 验收：`tests/api/test_chat_api.py` 覆盖权限、状态码、幂等。
4. `[P1-04] chat_service run 贯穿与流式收口`
   - 输入：`app/services/chat_service.py`、`app/schemas/chat.py`。
   - 输出：请求到 SSE 全链路携带 `run_id`，取消后停止回灌 token，禁止旧 run resume。
   - 验收：`tests/unit/test_chat_service_cancel_stream.py`、`tests/unit/test_chat_service_resume_after_cancel.py` 通过。
5. `[P1-05] multi_agent_graph 节点取消检查`
   - 输入：`app/ai/workflow/multi_agent_graph.py`。
   - 输出：关键节点增加 `is_cancelled` 检查与安全退出路径。
   - 验收：取消后不再推进后续节点，流程能稳定收口。

跨工单统一验收清单：

1. SSE 新增 `stopped` 事件并保持兼容。
2. `cancel_after_token_count` 指标目标为 0。
3. `ENABLE_RUN_CONTROL` 与 `ENABLE_SSE_STOPPED_EVENT` 可独立回滚。
4. 契约文档同步：
   - `docs/API文档/接口文档.md`
   - `docs/开发文档/代码解读/SSE事件协议.md`
   - `docs/开发文档/架构设计/数据库设计.md`
5. 若触发定向回查，必须在工单内补全“四元组”，否则不得结单。
