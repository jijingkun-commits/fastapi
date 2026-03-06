# composite-query-multimodal-response-contract 需求文档

> 更新时间：2026-03-07 00:00 +08:00  
> 上游设计：`docs/plans/2026-03-06-composite-query-multimodal-response-design.md`  
> 文档目标：定义 WHAT（需求合同、验收门禁、追溯矩阵），供 `composite-query-multimodal-response-contract_implementation_plan.md` 承接

## 1. 需求范围与目标

### 1.1 核心目标
- 保持现有 `/api/v1/chat/stream` SSE 主链路不变，收敛为唯一结构化通道 `result(data_type,data,message?)`。
- 让复合型提问稳定支持文字、表格、图片等多模态联合输出，并保证实时流 / 刷新回放 / resume 一致。
- 把结构化结果从“自由字符串 + 散落分支”升级为“单一契约源 + 强类型 + 明确降级 + CI 门禁”。
- 把 SSE 可靠性最小集（`id/retry/heartbeat/Last-Event-ID`）纳入正式契约，避免断线重连重复渲染或乱序。

### 1.2 范围
- 后端契约与归一：`app/ai/protocol.py`、`app/ai/events.py`、`app/services/chat_service.py`、`app/core/types.py`
- 前端解析与渲染：`web/src/lib/backend.ts`、`web/src/hooks/useSSEStream.ts`、`web/src/components/chat/messages/ai.tsx`、`web/src/types/message.ts`
- 回放与持久化归一：`web/src/lib/message-normalizer.ts`、`app/repositories/chat_repo.py`、`app/ai/workflow/multi_agent_graph.py`
- 契约与文档：`contracts/streaming/result-event.schema.json`、`docs/开发文档/代码解读/SSE事件协议.md`、`docs/产品文档/聊天系统需求.md`、`docs/api/streaming-events.asyncapi.yaml`、`docs/api/openapi.yaml`
- CI 与门禁：`scripts/contract/check_result_contract.sh`、`.github/workflows/contract-gate.yml`

### 1.3 非范围
- 不改 `/api/v1/chat/stream` 路由路径。
- 不替换 SSE 为 WebSocket。
- 不改多智能体调度策略与数据库表结构。
- 不新增第二套对外响应协议。

## 2. 机读需求合同（强制）

```yaml
requirements_contract:
  topic: "composite-query-multimodal-response-contract"
  status: "approved"
  design_source: docs/plans/2026-03-06-composite-query-multimodal-response-design.md
  clarify_handoff_source: docs/plans/2026-03-06-composite-query-multimodal-response-design.md#clarify_handoff_contract
  clarify_handoff_version: v2
  design_approved: true
  design_approval_evidence: "用户明确回复：好的"
  design_freeze_summary:
    design_actionable: true
    missing_blocks: []
    risk_level: medium
    risk_counterexamples_count: 5
    product_contract_ready: true
  owner: "chat-contract"
  approver: "jijingkun"
  updated_at: "2026-03-07 00:00"
```

## 3. 产品契约矩阵（PRD-Lite 承接）

```yaml
product_contract_matrix:
  target_users:
    - 运营/分析人员
    - 业务管理员
    - 研发维护者
  core_scenarios:
    - 复合提问一次性返回文字+表格+图片
    - 历史回放与实时链路展示一致
    - 未知 data_type 可见降级不丢失
    - 断线重连后不重复渲染且顺序稳定
  business_goals:
    - KPI-01 结构化事件渲染成功率（非 fallback）>=99%
    - KPI-02 未知 data_type 静默丢失率=0
    - KPI-03 回放一致性（实时 vs 刷新）>=99.5%
    - KPI-04 新增 data_type 的跨端联动缺陷在 CI 阶段拦截率>=95%
    - KPI-05 SSE 重连重复渲染率=0
  non_goals:
    - 不替换 SSE 为 WebSocket
    - 不重构可视化基础库
    - 不变更数据库表结构
  acceptance_gates:
    - AG-01 单一契约源冻结并能生成 JSON Schema + TS 类型
    - AG-02 未知类型 fallback 可见且带 warning 日志
    - AG-03 多结果 result_events[] 实时与回放顺序一致
    - AG-04 SSE 可靠性最小集（id/retry/heartbeat/Last-Event-ID）通过
    - AG-05 契约门禁测试、对齐检查、docs_guard 全部通过
```

## 4. FR 合同矩阵（字段级）

```yaml
fr_contract_matrix:
  - fr_id: FR-01
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[0]
    user_value: 保持单一结构化协议，降低跨端分叉成本
    trigger: 任意复合提问命中结构化输出
    input_contract:
      required_fields: [data_type, data]
      source_of_truth: app/contracts/result_event_contract.py
    output_contract:
      required_fields: [event, data_type, data]
      consumer: app/services/chat_service.py
    failure_semantics: 缺少必填字段时后端统一转 error 事件，禁止透传空壳 result
    observability_fields: [trace_id, thread_id, run_id, data_type, reason_code, result_contract_version]
    rollback_anchor: ENABLE_RESULT_TYPED_EVENT_V1=false
    owner: chat-contract

  - fr_id: FR-02
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[1]
    user_value: 新类型不再因为漏注册而静默消失
    trigger: 前端收到 result 事件
    input_contract:
      required_fields: [data_type, data]
      source_of_truth: web/src/lib/validators/result-event.ts
    output_contract:
      required_fields: [renderer_hit_or_fallback]
      consumer: web/src/components/chat/messages/ai.tsx
    failure_semantics: 未知 data_type 必须 fallback 可见并打 warning，不得吞事件
    observability_fields: [thread_id, run_id, data_type, renderer_key, fallback_used]
    rollback_anchor: ENABLE_RESULT_RENDER_REGISTRY_V1=false
    owner: frontend-chat

  - fr_id: FR-03
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[2]
    user_value: 刷新和 resume 后仍能恢复完整结构化结果
    trigger: 历史消息加载或 resume 流恢复
    input_contract:
      required_fields: [message_id]
      source_of_truth: message.additional_kwargs.result_events
    output_contract:
      required_fields: [render_consistent_with_realtime]
      consumer: web/src/lib/message-normalizer.ts
    failure_semantics: 缺 canonical 时允许文本回放，但必须展示结构化降级提示
    observability_fields: [message_id, thread_id, compat_source, data_type]
    rollback_anchor: ENABLE_RESULT_REPLAY_CANONICAL_V1=false
    owner: chat-runtime

  - fr_id: FR-04
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[3]
    user_value: 契约变更自动触发前后端联动，减少回归返工
    trigger: schema/type/renderer 任一变更
    input_contract:
      required_fields: [result_event_schema, generated_ts_types, parser_tests]
      source_of_truth: contracts/streaming/result-event.schema.json
    output_contract:
      required_fields: [ci_pass]
      consumer: .github/workflows/contract-gate.yml
    failure_semantics: 任一联动缺失即 CI fail，不允许合入
    observability_fields: [commit_sha, drift_kind, failed_gate]
    rollback_anchor: ENABLE_RESULT_SCHEMA_GATE_CI=false
    owner: ci-governance

  - fr_id: FR-05
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[4]
    user_value: 长连接在断线重连后保持顺序与幂等
    trigger: SSE 建连、断开、重连
    input_contract:
      required_fields: [event, data, event_id, retry]
      source_of_truth: app/services/chat_service.py
    output_contract:
      required_fields: [ordered_delivery_or_deduped_resume]
      consumer: web/src/lib/backend.ts
    failure_semantics: 无法续传时允许整轮重放，但不得造成重复渲染或乱序
    observability_fields: [thread_id, run_id, event_id, last_event_id, reconnect_count, dedup_drop_count]
    rollback_anchor: ENABLE_SSE_RELIABILITY_V1=false
    owner: chat-runtime

  - fr_id: FR-06
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[5]
    user_value: 复合提问可稳定展示多份结构化结果
    trigger: 单轮 assistant 产生 2 个及以上结构化结果
    input_contract:
      required_fields: [sequence_number, data_type, data]
      source_of_truth: app/contracts/result_event_contract.py
    output_contract:
      required_fields: [additional_kwargs.result_events]
      consumer: web/src/hooks/useSSEStream.ts
    failure_semantics: 不允许后到事件覆盖先到事件，必须保序累积
    observability_fields: [thread_id, run_id, result_count, sequence_number]
    rollback_anchor: ENABLE_RESULT_EVENTS_ARRAY_V1=false
    owner: chat-contract

  - fr_id: FR-07
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[6]
    user_value: 避免大 payload 拖垮流式链路并防止敏感信息直出
    trigger: result 包含大表格、图片或 fallback 摘要
    input_contract:
      required_fields: [data_type, data]
      source_of_truth: app/services/chat_service.py
    output_contract:
      required_fields: [payload_within_budget_or_externalized]
      consumer: app/ai/events.py
    failure_semantics: 超预算 payload 必须外置为资产引用；fallback 摘要必须脱敏
    observability_fields: [thread_id, run_id, payload_bytes, externalized, redaction_applied]
    rollback_anchor: ENABLE_RESULT_PAYLOAD_BUDGET_V1=false
    owner: chat-runtime
```

## 5. NFR 合同矩阵（数值阈值）

```yaml
nfr_contract_matrix:
  - nfr_id: NFR-01
    requirement: SSE 心跳间隔 <= 15 秒
    owner: chat-runtime
  - nfr_id: NFR-02
    requirement: 同一 run_id 下 sequence_number 必须严格单调递增
    owner: chat-contract
  - nfr_id: NFR-03
    requirement: 断线重连重复渲染率 = 0
    owner: frontend-chat
  - nfr_id: NFR-04
    requirement: 契约门禁总耗时 <= 5 分钟
    owner: ci-governance
  - nfr_id: NFR-05
    requirement: fallback 摘要敏感字段泄露率 = 0
    owner: chat-runtime
```

## 6. 追溯矩阵（设计 -> FR -> Feature -> Task -> TC）

```yaml
traceability_matrix:
  - design_item: D-01
    fr_id: FR-01
    feature_id: P1-result-contract-source
    task_id: T-01
    tc_id: TC-01
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_chat_service_done_payload.py tests/unit/test_chat_service_turn_slice.py -q
    evidence_entry: docs/内部参考/迭代需求/composite-query-multimodal-response-contract_implementation_plan.md
  - design_item: D-02
    fr_id: FR-02
    feature_id: P1-frontend-parser-and-registry
    task_id: T-02
    tc_id: TC-02
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && pnpm --filter web test -- --runInBand
    evidence_entry: docs/内部参考/迭代需求/composite-query-multimodal-response-contract_implementation_plan.md
  - design_item: D-03
    fr_id: FR-03
    feature_id: P1-replay-canonical-migration
    task_id: T-03
    tc_id: TC-03
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_intent_coverage_reconcile.py -q
    evidence_entry: docs/内部参考/迭代需求/composite-query-multimodal-response-contract_implementation_plan.md
  - design_item: D-04
    fr_id: FR-04
    feature_id: P1-contract-ci-gates
    task_id: T-05
    tc_id: TC-04
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/contract/check_result_contract.sh
    evidence_entry: docs/内部参考/迭代需求/composite-query-multimodal-response-contract_implementation_plan.md
  - design_item: D-05
    fr_id: FR-05
    feature_id: P1-result-contract-source
    task_id: T-01
    tc_id: TC-05
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_chat_service_done_payload.py tests/unit/test_chat_service_turn_slice.py -q
    evidence_entry: docs/内部参考/迭代需求/composite-query-multimodal-response-contract_implementation_plan.md
  - design_item: D-06
    fr_id: FR-06
    feature_id: P1-frontend-parser-and-registry
    task_id: T-02
    tc_id: TC-06
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && pnpm --filter web test -- --runInBand
    evidence_entry: docs/内部参考/迭代需求/composite-query-multimodal-response-contract_implementation_plan.md
  - design_item: D-07
    fr_id: FR-07
    feature_id: P1-streaming-contract-docs
    task_id: T-04
    tc_id: TC-07
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/docs_guard.py --strict
    evidence_entry: docs/内部参考/迭代需求/composite-query-multimodal-response-contract_implementation_plan.md
```
