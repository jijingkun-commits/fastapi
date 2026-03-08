# composite-query-multimodal-response-contract 实施计划

> 更新时间：2026-03-08 13:56 +08:00  
> 上游设计：`docs/plans/2026-03-06-composite-query-multimodal-response-design.md`  
> 对应需求：`docs/内部参考/迭代需求/composite-query-multimodal-response-contract_requirements.md`

## 1. 实施概览
- 规划模式：`parallel`
- 交付目标：先固化后端契约源，再并行推进前端解析/回放迁移/文档同步，最后统一补上 CI 门禁。
- 风险重点：多结果覆盖、重连重复渲染、历史字段兼容、fallback 摘要泄露。
- 门禁收口：T-05 负责新增 `scripts/contract/check_result_contract.sh` 与 `.github/workflows/contract-gate.yml`，并输出正式规划对齐报告。

## 2. implementation_tasks（机读）

```yaml
implementation_tasks:
  - task_id: T-01
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[0]
    feature_id: P1-result-contract-source
    pr_id: PR-01
    phase: Phase-1
    change_type: modify
    owner: chat-contract
    depends_on_tasks: [ROOT]
    risk_point: envelope 回填与 producer 校验若不统一，会继续产生协议旁路
    rollback_point: ENABLE_RESULT_TYPED_EVENT_V1=false
    file_paths:
      - app/ai/protocol.py
      - app/ai/events.py
      - app/services/chat_service.py
      - app/core/types.py
      - app/contracts/result_event_contract.py
      - contracts/streaming/result-event.schema.json
    symbols:
      - ResultEventUnion
      - build_streaming_result_payload_from_fields
      - emit_result
      - _normalize_result_event_payload
      - envelope_backfill
      - sse_retry_and_heartbeat
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && bash scripts/pytest_targeted.sh tests/unit/test_chat_service_done_payload.py tests/unit/test_chat_service_turn_slice.py -q

  - task_id: T-02
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[1]
    feature_id: P1-frontend-parser-and-registry
    pr_id: PR-02
    phase: Phase-2
    change_type: modify
    owner: frontend-chat
    depends_on_tasks: [T-01]
    risk_point: registry 与累加器若设计不当，会造成未知类型吞事件或多结果覆盖
    rollback_point: ENABLE_RESULT_RENDER_REGISTRY_V1=false
    file_paths:
      - web/src/lib/backend.ts
      - web/src/hooks/useSSEStream.ts
      - web/src/components/chat/messages/ai.tsx
      - web/src/types/message.ts
      - web/src/types/generated/result-event.ts
      - web/src/lib/validators/result-event.ts
    symbols:
      - normalizeResultEventData
      - handleStructuredResultEvent
      - AssistantMessage
      - rendererRegistry
      - resultEventsAccumulator
      - dedupByEventId
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && pnpm --filter web test -- --runInBand

  - task_id: T-03
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[2]
    feature_id: P1-replay-canonical-migration
    pr_id: PR-03
    phase: Phase-2
    change_type: modify
    owner: chat-runtime
    depends_on_tasks: [T-01]
    risk_point: 读旧写新迁移若缺排序与兼容来源标记，会导致刷新后卡片缺失或乱序
    rollback_point: ENABLE_RESULT_REPLAY_CANONICAL_V1=false
    file_paths:
      - web/src/lib/message-normalizer.ts
      - app/repositories/chat_repo.py
      - app/ai/workflow/multi_agent_graph.py
    symbols:
      - additional_kwargs.result_events
      - read_old_write_new
      - compat_source
      - sequence_number_sort
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && bash scripts/pytest_targeted.sh tests/unit/test_multi_intent_coverage_reconcile.py -q

  - task_id: T-04
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[3]
    feature_id: P1-streaming-contract-docs
    pr_id: PR-04
    phase: Phase-2
    change_type: modify
    owner: docs-governance
    depends_on_tasks: [T-01]
    risk_point: 文档若未同步 `result_events[]`、可靠性字段与版本命名，会造成下游误实现
    rollback_point: 回退 docs 变更并恢复 design_source 口径
    file_paths:
      - docs/开发文档/代码解读/SSE事件协议.md
      - docs/产品文档/聊天系统需求.md
      - docs/api/streaming-events.asyncapi.yaml
      - docs/api/openapi.yaml
    symbols:
      - result_event_union
      - text_event_stream_itemSchema
      - asyncapi_transitional_contract
      - last_event_id_resume
      - payload_budget_rules
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/docs_guard.py --strict

  - task_id: T-05
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[4]
    feature_id: P1-contract-ci-gates
    pr_id: PR-05
    phase: Phase-3
    change_type: modify
    owner: ci-governance
    depends_on_tasks: [T-02, T-03, T-04]
    risk_point: CI 覆盖不足会让 schema drift、重连重复、fallback 脱敏问题回流主干
    rollback_point: ENABLE_RESULT_SCHEMA_GATE_CI=false
    file_paths:
      - scripts/contract/check_result_contract.sh
      - .github/workflows/contract-gate.yml
      - tests/unit/test_chat_service_done_payload.py
      - tests/unit/test_chat_service_turn_slice.py
      - tests/unit/test_multi_intent_coverage_reconcile.py
      - web/e2e/todo-sse-protocol.spec.cjs
    symbols:
      - contract_drift_gate
      - unknown_data_type_fallback_test
      - replay_consistency_test
      - multi_result_ordering_test
      - sse_resume_dedup_test
      - redaction_whitelist_test
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && bash scripts/contract/check_result_contract.sh
      - cd /Users/jijingkun/bojxAI/fastapi && PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/check_workflow_contract.py --mode clarify_plan --requirements-path docs/内部参考/迭代需求/composite-query-multimodal-response-contract_requirements.md --implementation-path docs/内部参考/迭代需求/composite-query-multimodal-response-contract_implementation_plan.md --output docs/内部参考/迭代需求/composite-query-multimodal-response-contract_clarify_plan_alignment.json
      - cd /Users/jijingkun/bojxAI/fastapi && PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/check_workflow_contract.py --mode planning_temporal_gate --implementation-path docs/内部参考/迭代需求/composite-query-multimodal-response-contract_implementation_plan.md --output docs/内部参考/迭代需求/composite-query-multimodal-response-contract_planning_temporal_gate.json
```

## 3. task_to_pr_mapping（机读）

```yaml
planning_contract:
  task_to_pr_mapping:
    - task_id: T-01
      pr_id: PR-01
      pr_branch: codex/composite-query-multimodal-response-contract-pr-01
      pr_depends_on: []
      pr_subject: "P1 核心契约源：result union、envelope 与可靠性字段"
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && bash scripts/pytest_targeted.sh tests/unit/test_chat_service_done_payload.py tests/unit/test_chat_service_turn_slice.py -q
      rollback_point: ENABLE_RESULT_TYPED_EVENT_V1=false
    - task_id: T-02
      pr_id: PR-02
      pr_branch: codex/composite-query-multimodal-response-contract-pr-02
      pr_depends_on: [PR-01]
      pr_subject: "P2 前端 parser、registry 与 fallback 可见化"
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && pnpm --filter web test -- --runInBand
      rollback_point: ENABLE_RESULT_RENDER_REGISTRY_V1=false
    - task_id: T-03
      pr_id: PR-03
      pr_branch: codex/composite-query-multimodal-response-contract-pr-03
      pr_depends_on: [PR-01]
      pr_subject: "P2 回放 canonical 迁移与 result_events[] 保序"
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && bash scripts/pytest_targeted.sh tests/unit/test_multi_intent_coverage_reconcile.py -q
      rollback_point: ENABLE_RESULT_REPLAY_CANONICAL_V1=false
    - task_id: T-04
      pr_id: PR-04
      pr_branch: codex/composite-query-multimodal-response-contract-pr-04
      pr_depends_on: [PR-01]
      pr_subject: "P2 流式契约文档收敛与版本口径统一"
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/docs_guard.py --strict
      rollback_point: 回退 docs 变更并恢复 design_source 口径
    - task_id: T-05
      pr_id: PR-05
      pr_branch: codex/composite-query-multimodal-response-contract-pr-05
      pr_depends_on: [PR-02, PR-03, PR-04]
      pr_subject: "P3 契约 CI 门禁与重连/脱敏/多结果测试补齐"
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && bash scripts/contract/check_result_contract.sh
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/check_workflow_contract.py --mode clarify_plan --requirements-path docs/内部参考/迭代需求/composite-query-multimodal-response-contract_requirements.md --implementation-path docs/内部参考/迭代需求/composite-query-multimodal-response-contract_implementation_plan.md --output docs/内部参考/迭代需求/composite-query-multimodal-response-contract_clarify_plan_alignment.json
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/check_workflow_contract.py --mode planning_temporal_gate --implementation-path docs/内部参考/迭代需求/composite-query-multimodal-response-contract_implementation_plan.md --output docs/内部参考/迭代需求/composite-query-multimodal-response-contract_planning_temporal_gate.json
      rollback_point: ENABLE_RESULT_SCHEMA_GATE_CI=false
  execution_mode: parallel
  strict_single_active_card: false
  card_seed:
    - card_id: C01
      task_id: T-01
      wave: P1
      depends_on: []
    - card_id: C02
      task_id: T-02
      wave: P2
      depends_on: [C01]
    - card_id: C03
      task_id: T-03
      wave: P2
      depends_on: [C01]
    - card_id: C04
      task_id: T-04
      wave: P2
      depends_on: [C01]
    - card_id: C05
      task_id: T-05
      wave: P3
      depends_on: [C02, C03, C04]
```

## 4. planning_contract 摘要
- 并行策略：`T-02/T-03/T-04` 在 `T-01` 完成后并行；`T-05` 作为统一收口。
- PR 策略：每个 `task_id` 独立一个 `pr_id`，便于验证与回退。
- 停止边界：按 PR 停止，任一 PR 阻塞不影响其它并行项继续推进。

## 5. execution_contract（机读）

```yaml
execution_contract:
  delivery_mode: staged
  execution_unit: per_pr
  commit_policy: per_pr
  stop_boundary: per_pr
  stop_on_blocked: true
  source_seed_ref: clarify_handoff_contract.required.execution_chain_seed.execution_contract_hint
```

## 6. implementation_readiness（机读）

```yaml
implementation_readiness:
  implementation_ready: true
  blocked_by: []
  next_step: /jjk-vkplan
  execution_contract_ready: true
```

## 7. TC 覆盖映射

```yaml
tc_execution_mapping:
  - tc_id: TC-01
    task_id: T-01
    pr_id: PR-01
  - tc_id: TC-02
    task_id: T-02
    pr_id: PR-02
  - tc_id: TC-03
    task_id: T-03
    pr_id: PR-03
  - tc_id: TC-04
    task_id: T-05
    pr_id: PR-05
  - tc_id: TC-05
    task_id: T-01
    pr_id: PR-01
  - tc_id: TC-06
    task_id: T-02
    pr_id: PR-02
  - tc_id: TC-07
    task_id: T-04
    pr_id: PR-04
```
