# preference 判定链重构设计（v3.2 冻结版）

## 1. `scope_contract`
```yaml
scope_contract:
  objective: "将 preference 记忆从关键词主导升级为 LLM 主判定，并优先降低误记（A2）。"
  scope:
    - "后端记忆判定链：chat_service -> memory_intent_llm_service -> document_memory_service。"
    - "后台可观测：memory_admin 展示“命中/拒绝原因、判定来源、置信度”。"
    - "判定质量门禁：误记/漏记评估与拒绝原因标准化。"
    - "关键词仅用于拒绝门禁与低成本预筛，不作为正向入库必要条件。"
  boundaries:
    - "本轮只冻结设计与 handoff 契约（C3 + I3），不进入实现。"
    - "不改前端交互与提示文案，仅补后台数据面。"
    - "不引入灰度方案，仅保留紧急熔断（E2）。"
  success_criteria:
    - "判定合同与落库合同可机读且单一来源。"
    - "后台查询能解释“为什么记住/为什么拒绝”。"
    - "误记率与漏记率具备可执行测量口径与目标阈值（D2）。"
```

## 2. `product_contract`（PRD-Lite）
```yaml
product_contract:
  target_users:
    - "业务管理员：需要在后台核查记忆判定是否正确。"
    - "对话用户：希望显式偏好被稳定记住，非偏好内容不被误记。"
  core_scenarios:
    - id: SC-01
      name: "显式记忆指令入库"
      statement: "用户说“请永远记住，我叫jjk”后，系统应沉淀可检索的 preference。"
    - id: SC-02
      name: "非记忆任务拒绝入库"
      statement: "用户说“翻译一下：我叫jjk”后，系统应判定拒绝，不写 preference。"
    - id: SC-03
      name: "后台可解释审计"
      statement: "管理员可在后台看到每次判定的 detector/result/reason_code/confidence。"
    - id: SC-04
      name: "无触发词身份偏好识别"
      statement: "用户说“我叫jjk”时，即使未出现“记住”，也应进入主判定链并按合同决定入库。"
    - id: SC-05
      name: "风格偏好结构化沉淀"
      statement: "用户说“以后先给结论、回答简短一点”后，应映射到结构化槽位并可被稳定召回。"
  business_goals:
    - metric: "memory_false_positive_rate"
      target: "<=0.5%"
      window: "7天滚动窗口"
    - metric: "memory_false_negative_rate"
      target: "<=5.0%"
      window: "7天滚动窗口"
    - metric: "decision_audit_coverage"
      target: ">=99%"
      window: "日级"
  non_goals:
    - "不在本轮实现 UI 可视化改版。"
    - "不在本轮引入多模型投票判定。"
    - "不在本轮执行数据回灌迁移。"
  acceptance_gates:
    - "误记反例集通过：翻译/引用/否定表达不落 preference。"
    - "显式偏好样例通过：用户称呼、答复风格、长度等可落库。"
    - "后台查询接口返回判定审计字段且口径一致。"
    - "无触发词身份样例通过：`我叫jjk` 不再依赖关键词门控。"
    - "风格映射样例通过：同义表达映射到统一 slot_key/value。"
  release_constraints:
    - "默认全量开启，不做灰度。"
    - "仅允许紧急熔断开关回退。"
```

## 3. `architecture_contract`
```yaml
architecture_contract:
  module_boundaries:
    - module: "app/services/chat_service.py"
      responsibility: "编排与写后 recall 触发，不做语义判定。"
      not_responsible: "偏好关键词硬编码规则。"
    - module: "app/services/memory_intent_llm_service.py"
      responsibility: "输出 DecisionContract(level/category/slot_key/canonical_text/confidence)。"
      not_responsible: "文档写入与分块持久化。"
    - module: "app/services/user_preference_memory_service.py"
      responsibility: "结构化槽位映射与有限规则补偿（强身份表达、风格枚举映射）。"
      not_responsible: "主判定链最终裁决。"
    - module: "app/services/document_memory_service.py"
      responsibility: "统一落库、查询、recall 拼装。"
      not_responsible: "业务判定规则。"
    - module: "app/services/memory_intent_worker_service.py"
      responsibility: "异步消费编排与背压治理，不改变判定语义。"
      not_responsible: "DecisionContract 字段改写。"
    - module: "app/services/memory_admin_service.py"
      responsibility: "判定结果审计查询与后台可观测视图。"
      not_responsible: "判定决策。"

  end_to_end_data_flow:
    - step: 1
      action: "接收 user_text + context"
      output: "judging_input"
    - step: 2
      action: "预门禁（翻译/引用/否定）+ 强身份表达预检测"
      output: "precheck_result"
    - step: 3
      action: "LLM 判定（主）"
      output: "DecisionContract"
    - step: 4
      action: "合同/置信/敏感门禁校验"
      output: "accepted|rejected + reason_code"
    - step: 5
      action: "accepted 才进入 document_memory 写入；rejected 仅审计"
      output: "persisted|skipped"
    - step: 6
      action: "本轮 recall 注入 memory_context（非 messages 持久）"
      output: "runtime_context"
    - step: 7
      action: "后台查询展示 detector/result/reason_code/confidence"
      output: "auditable_records"

  state_lifecycle:
    - "received"
    - "prechecked"
    - "judged"
    - "accepted|rejected"
    - "persisted|skipped"
    - "recalled(optional)"
    - "audited"

  exception_semantics:
    - code: "llm_invoke_failed_fallback_rule"
      strategy: "降级规则兜底"
    - code: "task_intent_translation_or_quote"
      strategy: "拒绝入库并记录审计"
    - code: "contract_parse_failed"
      strategy: "拒绝入库并记录审计"
    - code: "negated_memory_intent"
      strategy: "拒绝入库并记录审计"
    - code: "display_name_parse_failed"
      strategy: "拒绝入库并记录审计"
    - code: "persist_failed"
      strategy: "事务回滚 + 返回统一错误语义"

  replay_contract:
    canonical_field: "additional_kwargs.memory_decision"
    legacy_fields:
      - "additional_kwargs.memory_intent_decision"
    migration_semantics: "读旧写新（read_old_write_new），两周后停写 legacy。"
```

## 4. `requirement_seeds`
```yaml
requirement_seeds:
  - design_item: "D-01"
    fr_id: "FR-01"
    trigger: "用户输入触发记忆判定"
    input_contract:
      required_fields: [user_id, user_text]
      optional_fields: [source_thread_id, source_message_id, context]
      defaults:
        context: {}
    output_contract:
      required_fields: [result, level, category, slot_key, confidence, reason_code, detector]
      optional_fields: [canonical_text, durability_score]
    failure_semantics: "判定失败统一 rejected 并输出 reason_code"
    observability_fields: [trace_id, decision_id, detector, result, reason_code, confidence, latency_ms]
    rollback_anchor: "feature.memory_preference_llm_judge_enabled=false"
    acceptance_cmd_ref: "venv/bin/python -m pytest tests/unit/test_memory_intent_llm_service.py -q"

  - design_item: "D-02"
    fr_id: "FR-02"
    trigger: "后台查询记忆审计"
    input_contract:
      required_fields: [user_id]
      optional_fields: [slot_key, category, level, keyword, status]
      defaults:
        status: "active"
    output_contract:
      required_fields: [items, total]
      optional_fields: [decision_reason, detector, confidence, result]
    failure_semantics: "查询失败返回统一错误口径并携带 trace_id"
    observability_fields: [trace_id, query_filters, total, latency_ms]
    rollback_anchor: "feature.memory_admin_decision_observability=false"
    acceptance_cmd_ref: "venv/bin/python -m pytest tests/unit/test_memory_admin_service.py tests/unit/test_memory_admin_api.py -q"

  - design_item: "D-03"
    fr_id: "FR-03"
    trigger: "用户输入命中强身份表达（我叫/叫我/称呼我/你叫）"
    input_contract:
      required_fields: [user_id, user_text, precheck_result]
      optional_fields: [source_thread_id, source_message_id, context]
      defaults:
        precheck_result:
          strong_identity_hit: false
    output_contract:
      required_fields: [result, slot_key, canonical_text, detector, reason_code]
      optional_fields: [confidence, reverse_intent]
    failure_semantics: "命中强身份表达但解析失败时统一 rejected + reason_code=display_name_parse_failed"
    observability_fields: [trace_id, decision_id, strong_identity_hit, detector, reason_code, confidence]
    rollback_anchor: "feature.memory_identity_pattern_bypass_enabled=false"
    acceptance_cmd_ref: "venv/bin/python -m pytest tests/unit/test_user_preference_memory_service.py tests/unit/test_document_memory_service.py -q"

  - design_item: "D-04"
    fr_id: "FR-04"
    trigger: "用户输入表达风格偏好（语气/长度/结构）"
    input_contract:
      required_fields: [user_id, user_text, decision_contract]
      optional_fields: [source_thread_id, source_message_id]
      defaults:
        decision_contract: {}
    output_contract:
      required_fields: [result, slot_key, normalized_value, detector, reason_code]
      optional_fields: [raw_value, confidence]
    failure_semantics: "不支持的风格表达统一 rejected + reason_code=style_expression_unsupported"
    observability_fields: [trace_id, decision_id, slot_key, normalized_value, reason_code, confidence]
    rollback_anchor: "feature.memory_style_taxonomy_enabled=false"
    acceptance_cmd_ref: "venv/bin/python -m pytest tests/unit/test_user_preference_memory_service.py tests/unit/test_memory_slot_governance_service.py -q"

  - design_item: "D-05"
    fr_id: "FR-05"
    trigger: "写入链路执行记忆判定并产出审计记录"
    input_contract:
      required_fields: [user_id, user_text, source_message_id]
      optional_fields: [source_thread_id, context, async_mode]
      defaults:
        async_mode: false
    output_contract:
      required_fields: [result, persist_action, decision_id, detector, reason_code, confidence]
      optional_fields: [slot_key, operation, audit_payload]
    failure_semantics: "任一判定步骤失败必须写 rejected 审计，主对话不中断"
    observability_fields: [trace_id, decision_id, detector, reason_code, confidence, pipeline_stage, latency_ms]
    rollback_anchor: "feature.memory_llm_primary_pipeline_enabled=false"
    acceptance_cmd_ref: "venv/bin/python -m pytest tests/unit/test_chat_service_memory_flags.py tests/unit/test_memory_intent_worker_service.py -q"
```

## 5. `implementation_seeds`
```yaml
implementation_seeds:
  - task_id: "T-01"
    file_paths:
      - "app/services/chat_service.py"
      - "app/services/memory_intent_llm_service.py"
      - "app/services/document_memory_service.py"
    symbols:
      - "_persist_document_memory_context"
      - "decide"
      - "flush_canonical_memory"
    change_type: "modify"
    blocked_by: []

  - task_id: "T-02"
    file_paths:
      - "app/services/memory_admin_service.py"
      - "app/api/v1/endpoints/memory_admin_api.py"
      - "app/schemas/memory_admin.py"
    symbols:
      - "list_memories"
      - "search_memories"
      - "MemoryQueryItem"
    change_type: "modify"
    blocked_by: ["T-01"]

  - task_id: "T-03"
    file_paths:
      - "tests/unit/test_memory_intent_llm_service.py"
      - "tests/unit/test_user_preference_memory_service.py"
      - "tests/unit/test_document_memory_service.py"
    symbols:
      - "test_*_translation_should_not_persist"
      - "test_*_explicit_preference_should_persist"
    change_type: "modify"
    blocked_by: ["T-01"]

  - task_id: "T-04"
    file_paths:
      - "app/services/user_preference_memory_service.py"
      - "app/services/document_memory_service.py"
      - "tests/unit/test_user_preference_memory_service.py"
      - "tests/unit/test_document_memory_service.py"
    symbols:
      - "_USER_DISPLAY_NAME_PATTERN"
      - "extract_explicit_preference_candidates"
      - "upsert_preference_documents_from_input"
    change_type: "modify"
    blocked_by: ["T-01"]

  - task_id: "T-05"
    file_paths:
      - "app/services/user_preference_memory_service.py"
      - "app/services/memory_slot_governance_service.py"
      - "tests/unit/test_user_preference_memory_service.py"
      - "tests/unit/test_memory_slot_governance_service.py"
    symbols:
      - "_DISPLAY_MAPPING"
      - "_normalize_controlled_memory_value"
      - "normalize_slot_key"
    change_type: "modify"
    blocked_by: ["T-01", "T-04"]

  - task_id: "T-06"
    file_paths:
      - "app/services/memory_admin_service.py"
      - "app/api/v1/endpoints/memory_admin_api.py"
      - "app/schemas/memory_admin.py"
      - "tests/unit/test_memory_admin_service.py"
      - "tests/unit/test_memory_admin_api.py"
    symbols:
      - "list_memories"
      - "get_memory_detail"
      - "MemoryListItem"
      - "MemoryDetailResponse"
    change_type: "modify"
    blocked_by: ["T-01"]
```

## 6. `execution_chain_seed`
```yaml
execution_chain_seed:
  preferred_mode: "core"
  task_key: "PP-20260305-preference-intent-judge"
  card_seed:
    - card_id: "T-01"
      title: "判定主链重构"
      blocked_by: []
      done_gate:
        - "venv/bin/python -m pytest tests/unit/test_memory_intent_llm_service.py tests/unit/test_chat_service_memory_flags.py -q"
    - card_id: "T-02"
      title: "后台可观测落地"
      blocked_by: ["T-01"]
      done_gate:
        - "venv/bin/python -m pytest tests/unit/test_memory_admin_service.py tests/unit/test_memory_admin_api.py -q"
    - card_id: "T-03"
      title: "误记/漏记质量门禁"
      blocked_by: ["T-01"]
      done_gate:
        - "venv/bin/python -m pytest tests/unit/test_memory_intent_llm_service.py tests/unit/test_user_preference_memory_service.py tests/unit/test_document_memory_service.py -q"
    - card_id: "T-04"
      title: "强身份表达绕过关键词门控"
      blocked_by: ["T-01"]
      done_gate:
        - "venv/bin/python -m pytest tests/unit/test_user_preference_memory_service.py tests/unit/test_document_memory_service.py -q"
    - card_id: "T-05"
      title: "风格偏好 taxonomy 归一化"
      blocked_by: ["T-01", "T-04"]
      done_gate:
        - "venv/bin/python -m pytest tests/unit/test_user_preference_memory_service.py tests/unit/test_memory_slot_governance_service.py -q"
    - card_id: "T-06"
      title: "后台审计字段合同化"
      blocked_by: ["T-01"]
      done_gate:
        - "venv/bin/python -m pytest tests/unit/test_memory_admin_service.py tests/unit/test_memory_admin_api.py -q"
  execution_contract_hint:
    delivery_mode: "staged"
    execution_unit: "per_task"
    commit_policy: "per_pr"
    stop_boundary: "design_approval_required"
    runtime_mode: "freeze_only"
```

## 7. `risk_rollback_contract`
```yaml
risk_rollback_contract:
  rollback_anchor:
    feature_flag: "feature.memory_preference_llm_judge_enabled"
    default: true
    rollback_value: false
    fallback_behavior: "回退至规则兜底；保留审计，不写入 preference 文档。"

  key_risks:
    - risk_id: "R-01"
      description: "翻译/转述任务被误判为偏好并写入长期记忆。"
      counterexample: "翻译一下：我叫jjk"
      mitigation: "任务类型门禁 + reason_code=task_intent_translation + rejected 强约束。"
    - risk_id: "R-02"
      description: "否定表达被反向写入（如：不要记住）。"
      counterexample: "不要记住我刚才说的话"
      mitigation: "negated_memory_intent 语义门禁 + 拒绝落库。"
    - risk_id: "R-03"
      description: "后台字段口径与判定口径漂移，导致审计误导。"
      counterexample: "接口返回 accepted，但 reason_code 为空"
      mitigation: "reason_code 必填校验 + memory_admin 返回合同统一化。"
    - risk_id: "R-04"
      description: "无触发词的强身份表达漏记，导致用户称呼体验不稳定。"
      counterexample: "我叫jjk"
      mitigation: "强身份表达预检测 + 不依赖触发词进入主判定链。"
    - risk_id: "R-05"
      description: "风格表达变体漂移，导致相同偏好落在不同槽位。"
      counterexample: "以后回答狠一点，别太官方"
      mitigation: "风格 taxonomy 归一化 + 不支持表达统一 rejected。"
```

## 8. 工程流一致性冻结结论
```yaml
consistency_gate_contract:
  product_contract_ready: true
  semantic_frozen: true
  semantic_single_strategy:
    missing_required_field: "统一返回 rejected + reason_code=contract_missing_required"
    low_confidence: "统一返回 rejected + reason_code=low_confidence"
    translation_or_quote: "统一返回 rejected + reason_code=task_intent_translation_or_quote"
    negated_memory_intent: "统一返回 rejected + reason_code=negated_memory_intent"
    style_expression_unsupported: "统一返回 rejected + reason_code=style_expression_unsupported"
  contract_source_decided: true
  contract_source:
    canonical_source: "app/services/memory_intent_llm_service.py::DecisionContract"
    mirror_policy: "memory_admin schema 由 canonical_source 字段镜像，不允许并存多源。"
  handoff_seed_alignment_ok: true
  alignment_check:
    requirement_seed_ids: ["FR-01", "FR-02", "FR-03", "FR-04", "FR-05"]
    implementation_task_ids: ["T-01", "T-02", "T-03", "T-04", "T-05", "T-06"]
    card_seed_ids: ["T-01", "T-02", "T-03", "T-04", "T-05", "T-06"]
  parallel_dependency_ready: true
  parallel_dependency_note: "preferred_mode=core，本门禁按通过处理。"
  replay_canonical_field_set: true
  replay_canonical:
    field: "additional_kwargs.memory_decision"
    migration: "read_old_write_new"
```

## 9. 设计冻结回执（机读）
```yaml
design_freeze_summary:
  design_actionable: true
  missing_blocks: []
  risk_level: medium
  risk_counterexamples_count: 5
  handoff_contract_ready: true
  product_contract_ready: true
  implementation_seed_count: 6
  semantic_frozen: true
  contract_source_decided: true
  handoff_seed_alignment_ok: true
  parallel_dependency_ready: true
  replay_canonical_field_set: true
  blocking_issues: []
```

## 10. `clarify_handoff_contract`（v2）
```yaml
clarify_handoff_contract:
  version: "v2"
  topic: "preference-intent-judge"
  design_source: "docs/plans/2026-03-05-preference-intent-judge-design.md"
  handoff_ready: true

  required:
    product_contract_summary:
      target_users:
        - "业务管理员"
        - "对话用户"
      core_scenarios:
        - "SC-01 显式记忆指令入库"
        - "SC-02 非记忆任务拒绝入库"
        - "SC-03 后台可解释审计"
        - "SC-04 无触发词身份偏好识别"
        - "SC-05 风格偏好结构化沉淀"
      business_goal_metrics:
        - "memory_false_positive_rate<=0.5%"
        - "memory_false_negative_rate<=5.0%"
        - "decision_audit_coverage>=99%"
      non_goals:
        - "不改前端 UI"
        - "不引入多模型投票"
        - "不做数据回灌迁移"
      acceptance_gates:
        - "翻译/引用/否定不落 preference"
        - "显式偏好能落库"
        - "后台审计字段完整"
        - "我叫jjk 不依赖触发词门控"
        - "风格同义表达映射统一 slot_key/value"

    requirement_seeds:
      - design_item: "D-01"
        fr_id: "FR-01"
        trigger: "用户输入触发记忆判定"
        input_contract:
          required_fields: [user_id, user_text]
          optional_fields: [source_thread_id, source_message_id, context]
          defaults:
            context: {}
        output_contract:
          required_fields: [result, level, category, slot_key, confidence, reason_code, detector]
        failure_semantics: "判定失败统一 rejected 并输出 reason_code"
        observability_fields: [trace_id, decision_id, detector, result, reason_code, confidence, latency_ms]
        rollback_anchor: "feature.memory_preference_llm_judge_enabled=false"
        acceptance_cmd_ref: "venv/bin/python -m pytest tests/unit/test_memory_intent_llm_service.py -q"

      - design_item: "D-02"
        fr_id: "FR-02"
        trigger: "后台查询记忆审计"
        input_contract:
          required_fields: [user_id]
          optional_fields: [slot_key, category, level, keyword, status]
          defaults:
            status: "active"
        output_contract:
          required_fields: [items, total]
          optional_fields: [decision_reason, detector, confidence, result]
        failure_semantics: "查询失败返回统一错误口径并携带 trace_id"
        observability_fields: [trace_id, query_filters, total, latency_ms]
        rollback_anchor: "feature.memory_admin_decision_observability=false"
        acceptance_cmd_ref: "venv/bin/python -m pytest tests/unit/test_memory_admin_service.py tests/unit/test_memory_admin_api.py -q"

      - design_item: "D-03"
        fr_id: "FR-03"
        trigger: "用户输入命中强身份表达（我叫/叫我/称呼我/你叫）"
        input_contract:
          required_fields: [user_id, user_text, precheck_result]
          optional_fields: [source_thread_id, source_message_id, context]
          defaults:
            precheck_result:
              strong_identity_hit: false
        output_contract:
          required_fields: [result, slot_key, canonical_text, detector, reason_code]
          optional_fields: [confidence, reverse_intent]
        failure_semantics: "命中强身份表达但解析失败时统一 rejected + reason_code=display_name_parse_failed"
        observability_fields: [trace_id, decision_id, strong_identity_hit, detector, reason_code, confidence]
        rollback_anchor: "feature.memory_identity_pattern_bypass_enabled=false"
        acceptance_cmd_ref: "venv/bin/python -m pytest tests/unit/test_user_preference_memory_service.py tests/unit/test_document_memory_service.py -q"

      - design_item: "D-04"
        fr_id: "FR-04"
        trigger: "用户输入表达风格偏好（语气/长度/结构）"
        input_contract:
          required_fields: [user_id, user_text, decision_contract]
          optional_fields: [source_thread_id, source_message_id]
          defaults:
            decision_contract: {}
        output_contract:
          required_fields: [result, slot_key, normalized_value, detector, reason_code]
          optional_fields: [raw_value, confidence]
        failure_semantics: "不支持的风格表达统一 rejected + reason_code=style_expression_unsupported"
        observability_fields: [trace_id, decision_id, slot_key, normalized_value, reason_code, confidence]
        rollback_anchor: "feature.memory_style_taxonomy_enabled=false"
        acceptance_cmd_ref: "venv/bin/python -m pytest tests/unit/test_user_preference_memory_service.py tests/unit/test_memory_slot_governance_service.py -q"

      - design_item: "D-05"
        fr_id: "FR-05"
        trigger: "写入链路执行记忆判定并产出审计记录"
        input_contract:
          required_fields: [user_id, user_text, source_message_id]
          optional_fields: [source_thread_id, context, async_mode]
          defaults:
            async_mode: false
        output_contract:
          required_fields: [result, persist_action, decision_id, detector, reason_code, confidence]
          optional_fields: [slot_key, operation, audit_payload]
        failure_semantics: "任一判定步骤失败必须写 rejected 审计，主对话不中断"
        observability_fields: [trace_id, decision_id, detector, reason_code, confidence, pipeline_stage, latency_ms]
        rollback_anchor: "feature.memory_llm_primary_pipeline_enabled=false"
        acceptance_cmd_ref: "venv/bin/python -m pytest tests/unit/test_chat_service_memory_flags.py tests/unit/test_memory_intent_worker_service.py -q"

    implementation_seeds:
      - task_id: "T-01"
        file_paths:
          - "app/services/chat_service.py"
          - "app/services/memory_intent_llm_service.py"
          - "app/services/document_memory_service.py"
        symbols:
          - "_persist_document_memory_context"
          - "decide"
          - "flush_canonical_memory"
        change_type: "modify"
      - task_id: "T-02"
        file_paths:
          - "app/services/memory_admin_service.py"
          - "app/api/v1/endpoints/memory_admin_api.py"
          - "app/schemas/memory_admin.py"
        symbols:
          - "list_memories"
          - "search_memories"
          - "MemoryQueryItem"
        change_type: "modify"
      - task_id: "T-03"
        file_paths:
          - "tests/unit/test_memory_intent_llm_service.py"
          - "tests/unit/test_user_preference_memory_service.py"
          - "tests/unit/test_document_memory_service.py"
        symbols:
          - "test_*_translation_should_not_persist"
          - "test_*_explicit_preference_should_persist"
        change_type: "modify"
      - task_id: "T-04"
        file_paths:
          - "app/services/user_preference_memory_service.py"
          - "app/services/document_memory_service.py"
          - "tests/unit/test_user_preference_memory_service.py"
          - "tests/unit/test_document_memory_service.py"
        symbols:
          - "_USER_DISPLAY_NAME_PATTERN"
          - "extract_explicit_preference_candidates"
          - "upsert_preference_documents_from_input"
        change_type: "modify"
      - task_id: "T-05"
        file_paths:
          - "app/services/user_preference_memory_service.py"
          - "app/services/memory_slot_governance_service.py"
          - "tests/unit/test_user_preference_memory_service.py"
          - "tests/unit/test_memory_slot_governance_service.py"
        symbols:
          - "_DISPLAY_MAPPING"
          - "_normalize_controlled_memory_value"
          - "normalize_slot_key"
        change_type: "modify"
      - task_id: "T-06"
        file_paths:
          - "app/services/memory_admin_service.py"
          - "app/api/v1/endpoints/memory_admin_api.py"
          - "app/schemas/memory_admin.py"
          - "tests/unit/test_memory_admin_service.py"
          - "tests/unit/test_memory_admin_api.py"
        symbols:
          - "list_memories"
          - "get_memory_detail"
          - "MemoryListItem"
          - "MemoryDetailResponse"
        change_type: "modify"

    execution_chain_seed:
      preferred_mode: "core"
      task_key: "PP-20260305-preference-intent-judge"
      card_seed:
        - card_id: "T-01"
          blocked_by: []
        - card_id: "T-02"
          blocked_by: ["T-01"]
        - card_id: "T-03"
          blocked_by: ["T-01"]
        - card_id: "T-04"
          blocked_by: ["T-01"]
        - card_id: "T-05"
          blocked_by: ["T-01", "T-04"]
        - card_id: "T-06"
          blocked_by: ["T-01"]
      execution_contract_hint:
        delivery_mode: "staged"
        execution_unit: "per_task"
        commit_policy: "per_pr"
        stop_boundary: "design_approval_required"
        runtime_mode: "freeze_only"

    alignment_contract:
      strict_match: true
      requirement_seed_ids: ["FR-01", "FR-02", "FR-03", "FR-04", "FR-05"]
      implementation_task_ids: ["T-01", "T-02", "T-03", "T-04", "T-05", "T-06"]
      card_seed_ids: ["T-01", "T-02", "T-03", "T-04", "T-05", "T-06"]

  extended:
    observability_hints:
      - "所有 rejected 记录必须输出 reason_code 与 detector。"
      - "memory_admin 查询返回 confidence，便于误记复盘。"
      - "memory_admin 列表/详情返回 decision_id，支持一次判定全链路追踪。"
      - "审计口径以 DecisionContract 字段镜像为唯一来源，禁止后台二次推导。"
    risk_counterexample_map:
      - risk_id: "R-01"
        counterexample: "翻译一下：我叫jjk"
        guard: "task_intent_translation -> rejected"
      - risk_id: "R-02"
        counterexample: "不要记住我刚才说的话"
        guard: "negated_memory_intent -> rejected"
      - risk_id: "R-03"
        counterexample: "accepted 但 reason_code 为空"
        guard: "reason_code required 校验"
      - risk_id: "R-04"
        counterexample: "我叫jjk（无记住触发词）"
        guard: "strong_identity_hit -> 进入主判定链"
      - risk_id: "R-05"
        counterexample: "以后回答狠一点，别太官方"
        guard: "style taxonomy normalize or rejected(style_expression_unsupported)"
    assumptions:
      - "LLM 判定服务可用，失败时可稳定降级到规则兜底。"
      - "memory_admin 接口允许扩展审计字段且向后兼容。"
```

## 11. 审批记录
```yaml
design_approval:
  design_approved: false
  approved_at: ""
  approved_round: ""
  approval_evidence: ""
  approval_mode: "pending"
  go_no_go: "NO_GO"
```
