# 需求基线（聊天多会话并发重分析）

## 0. 需求契约（机读）

```yaml
requirements_contract:
  topic: "聊天多会话并发重分析"
  status: approved
  design_source: docs/plans/2026-03-04-chat-multi-session-concurrency-reanalysis-design.md
  design_approved: true
  owner: "chat-frontend + chat-backend"
  approver: "jijingkun"
  updated_at: "2026-03-04 18:30"
```

## 1. 输入来源清单（Superpowers 对齐桥接）

1. 设计文档（已审批）  
   `docs/plans/2026-03-04-chat-multi-session-concurrency-reanalysis-design.md`
2. 历史并发能力参考  
   `docs/plans/2026-03-01-chat-multi-session-concurrency-design.md`
3. 停止稳定性既有方案（约束不回退）  
   `docs/内部参考/迭代需求/聊天停止后并发占用稳定性修复_implementation_plan.md`
4. 关键代码锚点  
   `web/src/hooks/useSSEStream.ts`  
   `web/src/providers/StreamContext.tsx`  
   `web/src/components/chat/ChatInput.tsx`  
   `app/api/v1/endpoints/chat_api.py`  
   `app/services/run_control_service.py`

## 2. 背景与问题陈述

当前系统在“强停止”与 run 生命周期方面已具备基础能力，但前端运行态仍是全局单实例：一个会话流式期间会阻断其他会话提交；刷新后也缺少“当前用户活跃 run 列表”恢复能力。结果是用户无法获得类似 Codex App 的“同页多会话并行”体验，且停止隔离、并发门禁与观测仍不足。

## 3. 目标与非目标

### 3.1 目标
1. 支持同一用户在单页并行运行多个会话（按 `thread_id` 隔离）。
2. 保持“强停止（hard cancel）”语义，停止仅作用于目标会话。
3. 页面刷新后恢复运行态（active runs），避免“任务消失”错觉。
4. 建立前后端双层并发门禁，并提供可观测的降级与回滚路径。

### 3.2 非目标
1. 不做 token 级历史事件回放。
2. 不做多窗格同屏工作台。
3. 不变更 LangGraph 业务节点编排语义，仅调整运行态与契约层。

## 4. 用户故事

1. 作为业务用户，我希望在会话 A 运行时切换到会话 B 继续提问，两个会话互不影响。
2. 作为业务用户，我希望点击“停止”只终止当前会话，不会误停其他会话。
3. 作为值班工程师，我希望刷新页面后仍能看到哪些会话在运行，并快速定位异常 run。
4. 作为维护人员，我希望并发超限有统一错误口径、日志可追踪、可快速回滚。

## 5. 功能需求契约（FR）

```yaml
fr_contract_matrix:
  - fr_id: FR-01
    user_value: 用户可在单页面并行推进多个会话任务
    trigger: 用户在会话A流式期间切换到会话B并发送新问题
    input_contract:
      required_fields: [thread_id, prompt, idempotency_key]
      source_of_truth: web/src/hooks/useSSEStream.ts
    output_contract:
      required_fields: [run_id, thread_id, status, messages]
      consumer: web/src/components/chat/index.tsx
    failure_semantics: 同一thread重复提交时返回明确阻断提示；跨thread不阻断
    observability_fields: [user_id, thread_id, run_id, phase, updated_at]
    rollback_anchor: ENABLE_CHAT_MULTI_SESSION_RUNTIME=true（回退时置false）
    owner: frontend-chat

  - fr_id: FR-02
    user_value: 停止动作精准命中目标会话，避免误杀
    trigger: 用户点击当前会话停止按钮或侧边栏会话级停止按钮
    input_contract:
      required_fields: [path_run_id, cancel_mode]
      source_of_truth: app/api/v1/endpoints/chat_api.py
    output_contract:
      required_fields: [accepted, run_id, thread_id, status, idempotent]
      consumer: web/src/lib/backend.ts
    failure_semantics: run不存在返回404；权限不符403；thread_id不匹配返回400（仅在传入thread_id时校验）
    observability_fields: [user_id, run_id, thread_id, cancel_mode, reason]
    rollback_anchor: ENABLE_CHAT_RUN_THREAD_GUARD=true（回退时置false）
    owner: backend-chat

  - fr_id: FR-03
    user_value: 刷新后仍可看到运行中的会话并继续控制
    trigger: 页面冷启动或刷新后加载历史线程列表
    input_contract:
      required_fields: [jwt_user_id]
      source_of_truth: app/services/run_control_service.py
    output_contract:
      required_fields: [run_id, thread_id, status, cancel_reason, updated_at]
      consumer: web/src/components/chat/history/index.tsx
    failure_semantics: 查询失败时降级为空列表并提示“运行态恢复失败，可手动刷新”
    observability_fields: [user_id, active_run_count, query_latency_ms]
    rollback_anchor: ENABLE_CHAT_ACTIVE_RUN_RECOVERY=true（回退时置false）
    owner: backend-chat

  - fr_id: FR-04
    user_value: 并发上限可控，避免资源被单用户占满
    trigger: 用户创建新run前触发并发检查
    input_contract:
      required_fields: [user_id, thread_id]
      source_of_truth: app/services/run_control_service.py
    output_contract:
      required_fields: [accepted, reason, limit, active_count]
      consumer: app/api/v1/endpoints/chat_api.py
    failure_semantics: 超限返回429；文案包含当前活跃数与上限值
    observability_fields: [user_id, active_count, limit, rejected_at]
    rollback_anchor: ENABLE_CHAT_PARALLEL_LIMIT=true（回退时置false）
    owner: backend-chat

  - fr_id: FR-05
    user_value: 用户可识别“长时间无token”风险并快速处理
    trigger: 会话运行态持续超过30秒无新token
    input_contract:
      required_fields: [thread_id, last_token_at, status_phase]
      source_of_truth: web/src/hooks/useSSEStream.ts
    output_contract:
      required_fields: [badge_state, warning_text, stop_action]
      consumer: web/src/components/chat/history/index.tsx
    failure_semantics: tool_running/interrupt阶段不触发卡死告警，避免误报
    observability_fields: [thread_id, idle_seconds, status_phase]
    rollback_anchor: ENABLE_CHAT_STALL_WARNING=true（回退时置false）
    owner: frontend-chat

  - fr_id: FR-06
    user_value: 研发可从日志和指标快速定位并发/停止问题
    trigger: cancel失败、并发拒绝、运行态恢复失败
    input_contract:
      required_fields: [trace_id, user_id, thread_id, run_id]
      source_of_truth: app/api/v1/endpoints/chat_api.py
    output_contract:
      required_fields: [structured_log, metric_event]
      consumer: ops-observability
    failure_semantics: 记录失败不影响主流程，但必须保底落普通日志
    observability_fields: [event_type, error_code, duration_ms, retry_count]
    rollback_anchor: ENABLE_CHAT_MULTI_SESSION_OBSERVABILITY=true（回退时置false）
    owner: backend-chat
```

## 6. 非功能需求（NFR）

1. `NFR-01（性能）`：`GET /api/v1/chat/runs/active` 在生产 P95 `< 120ms`，P99 `< 250ms`。  
2. `NFR-02（稳定）`：停止接口 5xx 错误率 `< 0.3%`，并发拒绝日志完整率 `= 100%`。  
3. `NFR-03（一致性）`：停止隔离误杀率 `= 0`；跨会话消息串写率 `= 0`。  
4. `NFR-04（恢复）`：刷新后运行态恢复展示时间 `< 1s`（首屏完成后）。  
5. `NFR-05（资源）`：前端 RuntimeBucket 常驻数量上限 `<= 10`；结束态 30 秒清理。

## 7. 验收标准

### 7.1 功能验收（Happy Path）
1. A 会话运行中切换至 B 提交，A/B 均可完成并持久化。
2. 停止 B 后，B 进入 `stopping/stopped`，A 持续运行并完成。
3. 刷新页面后侧边栏恢复 active runs，并能继续执行停止操作。

### 7.2 异常/边界验收
1. 同线程重复提交被阻断，并返回可理解提示。
2. 并发超限返回 429，提示当前活跃数与上限。
3. 使用错误 `thread_id` 停止 run 返回 400（当请求携带 `thread_id` 时）。
4. cancel 接口幂等：重复停止不报错，返回 `accepted=true, idempotent=true`。

### 7.3 可观测与回滚验收
1. 并发拒绝、停止失败、运行态恢复失败均有结构化日志。
2. 关闭相关开关后可回退到单会话模型，不影响既有问答与强停止基础能力。

## 8. 测试用例矩阵（TC）

| tc_id | fr_id | 场景 | 预期 |
|---|---|---|---|
| TC-MSC-001 | FR-01 | A/B 并发提交 | 双会话完成且不串写 |
| TC-MSC-002 | FR-02 | 仅停止B | B停止，A继续 |
| TC-MSC-003 | FR-03 | 刷新恢复 | active runs恢复正确 |
| TC-MSC-004 | FR-01 | 同线程重复提交 | 被阻断并提示 |
| TC-MSC-005 | FR-04 | 超过并发上限 | 返回429并提示 |
| TC-MSC-006 | FR-01 | 切换会话后回看消息 | 消息完整无丢失 |
| TC-MSC-007 | FR-02 | 停止后立即重提 | 新run可正常启动 |
| TC-MSC-008 | FR-03 | 刷新瞬间run完成 | 状态及时清理 |
| TC-MSC-009 | FR-02 | 错thread_id停止 | 返回400（携带thread_id时） |
| TC-MSC-010 | FR-04 | 双标签并发抢占 | 原子门禁生效，不超限 |

## 9. 追溯矩阵（Traceability）

```yaml
traceability_matrix:
  - design_item: D-01 RuntimeRegistry
    fr_id: FR-01
    feature_id: P1-01
    task_id: T-01
    tc_id: TC-MSC-001
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi/web && pnpm exec vitest run src/hooks/__tests__/useSSEStream.multi-session.test.ts
    evidence_entry: docs/内部参考/迭代需求/聊天多会话并发重分析_implementation_plan.md

  - design_item: D-02 StopIsolation
    fr_id: FR-02
    feature_id: P2-01
    task_id: T-04
    tc_id: TC-MSC-002
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/api/test_chat_api.py -k cancel_run_thread_guard -q
    evidence_entry: docs/内部参考/迭代需求/聊天多会话并发重分析_implementation_plan.md

  - design_item: D-03 ActiveRunsRecovery
    fr_id: FR-03
    feature_id: P2-02
    task_id: T-05
    tc_id: TC-MSC-003
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/api/test_chat_api.py -k active_runs -q
    evidence_entry: docs/内部参考/迭代需求/聊天多会话并发重分析_implementation_plan.md

  - design_item: D-04 ParallelLimit
    fr_id: FR-04
    feature_id: P2-03
    task_id: T-07
    tc_id: TC-MSC-005
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_run_control_service.py -k parallel_limit -q
    evidence_entry: docs/内部参考/迭代需求/聊天多会话并发重分析_implementation_plan.md

  - design_item: D-05 StallWarning
    fr_id: FR-05
    feature_id: P1-03
    task_id: T-03
    tc_id: TC-MSC-006
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi/web && pnpm exec vitest run src/components/chat/history/__tests__/thread-runtime-badge.test.tsx
    evidence_entry: docs/内部参考/迭代需求/聊天多会话并发重分析_implementation_plan.md

  - design_item: D-06 Observability
    fr_id: FR-06
    feature_id: P3-01
    task_id: T-08
    tc_id: TC-MSC-010
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_run_control_service.py -k observability -q
    evidence_entry: docs/内部参考/迭代需求/聊天多会话并发重分析_implementation_plan.md
```

## 10. 决策权衡（最终方案口径）

本次需求冻结为“方案 B v2：会话级并发运行态 + 后端 active runs 查询 + 强停止隔离”。放弃事件回放型方案，原因是其引入事件存储与重放协议，超出当前迭代成本与交付节奏。
