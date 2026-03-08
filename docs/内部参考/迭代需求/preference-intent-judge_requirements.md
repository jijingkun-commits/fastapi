# preference-intent-judge 需求文档（v1：LLM 记忆判定与原子批量写入）

> 更新时间：2026-03-08 14:25 CST  
> 上游设计：`docs/plans/2026-03-05-preference-intent-judge-design.md`  
> 文档目标：定义 WHAT（需求合同、验收与追溯），供 `preference-intent-judge_implementation_plan.md` 承接

## 1. 需求范围与目标

### 1.1 用户故事

- 作为对话用户，我希望明确表达的身份与答复风格能被稳定记住，但翻译、引用、否定等非长期偏好内容不能被误记。
- 作为业务管理员，我希望在后台看到每次记忆判定的 `decision/reason_code/confidence/memories_count`，并能复盘拒绝原因。
- 作为记忆链路研发，我希望把 `preference` 判定从关键词主导收敛为模型主判定，并且把多记忆句落库语义冻结为 `atomic_batch`。

### 1.2 范围

- 以 `DecisionContract(decision, reason_code, confidence, memories[])` 作为唯一判定合同。
- 由 LLM 负责语义识别，工程层只负责 schema、slot taxonomy、敏感信息、幂等与审计校验。
- 支持 `user_identity / response_preference / assistant_persona / profile_fact` 四类 `memory_kind`。
- 写入链路必须支持单句 `0..N` 条 `memories[]`，并以 `atomic_batch` 保证整批一致性。
- `memory_admin` 需返回 `decision_id / confidence / rejected_items_count / item_errors` 等审计字段。

### 1.3 非范围

- 本轮不引入关键词/正则作为正向写入兜底。
- 本轮不引入多模型投票、人工审核工作流或数据回灌迁移。
- 本轮不重做后台 UI，只冻结后台接口与审计口径。

### 1.4 发布约束

- 默认全量开启，不做灰度。
- 所有新增开关默认 `true`，回退时切到 `false`。
- 不允许把观察窗口成熟、TTL 到期或自然时间流逝写入阻断型验收门禁。

## 2. 机读需求合同（强制）

```yaml
requirements_contract:
  topic: "preference-intent-judge"
  status: "approved"
  design_source: docs/plans/2026-03-05-preference-intent-judge-design.md
  clarify_handoff_source: docs/plans/2026-03-05-preference-intent-judge-design.md#clarify_handoff_contract
  clarify_handoff_version: v2
  design_approved: true
  design_approval_evidence: "用户回复：确认"
  design_freeze_summary:
    design_actionable: true
    missing_blocks: []
    risk_level: medium
    risk_counterexamples_count: 7
    handoff_contract_ready: true
    product_contract_ready: true
    implementation_seed_count: 6
    semantic_frozen: true
    contract_source_decided: true
    handoff_seed_alignment_ok: true
    parallel_dependency_ready: true
    replay_canonical_field_set: true
    blocking_issues: []
  owner: "memory-platform"
  approver: "jijingkun"
  updated_at: "2026-03-08 14:25 CST"
```

## 3. product_contract_matrix

```yaml
product_contract_matrix:
  - bg_id: BG-01
    target_users: [对话用户]
    core_scenario: 显式身份与风格偏好被稳定沉淀并可召回
    business_goal_metric: memory_false_negative_rate<=5.0%
    acceptance_gates: [A-02, A-04, A-05]
    release_constraint: 默认全量开启，不做灰度

  - bg_id: BG-02
    target_users: [对话用户]
    core_scenario: 翻译/引用/否定表达不被误记为长期偏好
    business_goal_metric: memory_false_positive_rate<=0.5%
    acceptance_gates: [A-01, A-04, A-05]
    release_constraint: 禁止关键词规则兜底写入

  - bg_id: BG-03
    target_users: [业务管理员]
    core_scenario: 每次判定均可在后台按统一口径复盘
    business_goal_metric: decision_audit_coverage>=99%
    acceptance_gates: [A-03, A-06]
    release_constraint: 审计口径只允许镜像 canonical DecisionContract

  - bg_id: BG-04
    target_users: [对话用户, 业务管理员]
    core_scenario: 多记忆句写入保持原子一致，不出现部分成功
    business_goal_metric: partial_memory_write_incident_count=0
    acceptance_gates: [A-06]
    release_constraint: 仅允许 atomic_batch，不允许 partial_success
```

## 4. fr_contract_matrix

```yaml
fr_contract_matrix:
  - fr_id: FR-01
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[0]
    user_value: 用户输入进入模型主判定，统一产出 memories[] 决策合同
    trigger: 用户消息进入记忆判定链路
    input_contract:
      required_fields: [user_id, user_text]
      optional_fields: [source_thread_id, source_message_id, context]
      source_of_truth: app/services/memory_intent_llm_service.py::decide
    output_contract:
      required_fields: [decision, reason_code, confidence, memories]
      consumer: app/services/chat_service.py::_persist_document_memory_context
    failure_semantics: contract_missing_required|low_confidence|task_intent_translation_or_quote|negated_memory_intent -> rejected_audit_only
    observability_fields: [trace_id, decision_id, detector, reason_code, confidence, memories_count]
    rollback_anchor: feature.memory_preference_llm_judge_enabled=false
    linked_business_goals: [BG-01, BG-02, BG-03]

  - fr_id: FR-02
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[1]
    user_value: 后台可按统一审计口径查询列表与详情
    trigger: 管理员访问 memory_admin 列表/详情接口
    input_contract:
      required_fields: [user_id]
      optional_fields: [slot_key, category, level, keyword, status]
      source_of_truth: app/services/memory_admin_service.py::list_memories
    output_contract:
      required_fields: [items, total]
      optional_fields: [decision_reason, detector, confidence, decision_id]
      consumer: app/api/v1/endpoints/memory_admin_api.py::list_memories
    failure_semantics: query_failed -> unified_error_with_trace_id
    observability_fields: [trace_id, query_filters, total, latency_ms]
    rollback_anchor: feature.memory_admin_decision_observability=false
    linked_business_goals: [BG-03]

  - fr_id: FR-03
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[2]
    user_value: 无触发词身份表达也能由模型直接识别为长期记忆或明确拒绝
    trigger: 用户输入身份/称呼类长期信息
    input_contract:
      required_fields: [user_id, user_text, context]
      source_of_truth: app/services/memory_intent_llm_service.py::decide
    output_contract:
      required_fields: [decision, reason_code, confidence, memories]
      consumer: app/services/document_memory_service.py::flush_canonical_memory
    failure_semantics: identity_semantic_unresolved -> rejected_audit_only
    observability_fields: [trace_id, decision_id, detector, reason_code, confidence, "memories[*].memory_kind"]
    rollback_anchor: feature.memory_identity_semantic_judge_enabled=false
    linked_business_goals: [BG-01, BG-02]

  - fr_id: FR-04
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[3]
    user_value: 风格/结构/长度偏好由模型归一为稳定槽位
    trigger: 用户输入答复风格偏好
    input_contract:
      required_fields: [user_id, user_text, context]
      source_of_truth: app/services/memory_intent_llm_service.py::decide
    output_contract:
      required_fields: [decision, reason_code, confidence, memories]
      consumer: app/services/memory_slot_governance_service.py::normalize_slot_key
    failure_semantics: style_semantic_unresolved -> rejected_audit_only
    observability_fields: [trace_id, decision_id, reason_code, confidence, "memories[*].slot_key", "memories[*].normalized_value"]
    rollback_anchor: feature.memory_style_semantic_judge_enabled=false
    linked_business_goals: [BG-01, BG-02]

  - fr_id: FR-05
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[4]
    user_value: 写入链路对多记忆句执行 atomic_batch，并把拒绝原因写入审计
    trigger: accepted DecisionContract 进入持久化阶段
    input_contract:
      required_fields: [decision, memories, source_message_id]
      optional_fields: [source_thread_id, context, async_mode]
      source_of_truth: app/services/document_memory_service.py::flush_canonical_memory
    output_contract:
      required_fields: [persist_action, decision_id, reason_code, confidence, memories_count]
      optional_fields: [memory_ids, audit_payload, rejected_items_count, item_errors]
      consumer: app/services/memory_admin_service.py::get_memory_detail
    failure_semantics: invalid_memory_item|batch_write_failed -> rejected_with_memory_batch_atomic_reject
    observability_fields: [trace_id, decision_id, detector, persist_mode, rejected_items_count, item_errors]
    rollback_anchor: feature.memory_llm_primary_pipeline_enabled=false
    linked_business_goals: [BG-02, BG-03, BG-04]
```

## 5. nfr_contract_matrix

```yaml
nfr_contract_matrix:
  - nfr_id: NFR-01
    metric: memory_false_positive_rate
    threshold: <=0.5%
    scope: 误记控制
    verification_method: 误记反例集 + 审计抽样复盘

  - nfr_id: NFR-02
    metric: memory_false_negative_rate
    threshold: <=5.0%
    scope: 漏记控制
    verification_method: 身份/风格正例集 + 回归用例

  - nfr_id: NFR-03
    metric: decision_audit_coverage
    threshold: >=99%
    scope: 后台可观测
    verification_method: memory_admin 列表/详情字段检查 + 审计记录抽样

  - nfr_id: NFR-04
    metric: partial_memory_write_incident_count
    threshold: =0
    scope: 多记忆句原子一致性
    verification_method: atomic_batch 失败用例 + 持久化层事务验证
```

## 6. traceability_matrix

```yaml
traceability_matrix:
  - design_item: D-01
    fr_id: FR-01
    bg_id: BG-02
    feature_id: P1-01
    task_id: T-01
    tc_id: TC-01
    acceptance_cmd_ref: 'cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest tests/unit/test_memory_intent_llm_service.py tests/unit/test_chat_service_memory_flags.py -q'

  - design_item: D-02
    fr_id: FR-02
    bg_id: BG-03
    feature_id: P2-01
    task_id: T-02
    tc_id: TC-02
    acceptance_cmd_ref: 'cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest tests/api/test_memory_admin_api.py -q -k "memories_list or memory_detail"'

  - design_item: D-05
    fr_id: FR-05
    bg_id: BG-04
    feature_id: P3-01
    task_id: T-03
    tc_id: TC-03
    acceptance_cmd_ref: 'cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest tests/unit/test_memory_intent_llm_service.py tests/unit/test_user_preference_memory_service.py tests/unit/test_document_memory_service.py -q'

  - design_item: D-03
    fr_id: FR-03
    bg_id: BG-01
    feature_id: P1-02
    task_id: T-04
    tc_id: TC-04
    acceptance_cmd_ref: 'cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest tests/unit/test_memory_intent_llm_service.py -q -k "identity_semantic or multi_memory_items"'

  - design_item: D-04
    fr_id: FR-04
    bg_id: BG-01
    feature_id: P1-03
    task_id: T-05
    tc_id: TC-05
    acceptance_cmd_ref: 'cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest tests/unit/test_memory_intent_llm_service.py tests/unit/test_memory_slot_governance_service.py -q'

  - design_item: D-05
    fr_id: FR-05
    bg_id: BG-03
    feature_id: P2-02
    task_id: T-06
    tc_id: TC-06
    acceptance_cmd_ref: 'cd /Users/jijingkun/bojxAI/fastapi && rg -n "rejected_items_count|item_errors|decision_id|confidence" app/schemas/memory_admin.py app/services/memory_admin_service.py app/api/v1/endpoints/memory_admin_api.py'
```
