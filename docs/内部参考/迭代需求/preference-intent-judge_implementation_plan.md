# preference-intent-judge 实施方案（v1：LLM 语义判定与 atomic_batch）

> 更新时间：2026-03-08 14:25 CST  
> 上游设计：`docs/plans/2026-03-05-preference-intent-judge-design.md`  
> 关联需求：`docs/内部参考/迭代需求/preference-intent-judge_requirements.md`

## 1. 实施概览

- 执行模式：`core`，按单主线串行推进，优先降低共享文件冲突与语义漂移。
- 任务编排：先稳定判定主链，再补 identity/style 语义，再补后台审计合同，最后统一回归质量门禁。
- 关键取舍：虽然上游 seeds 允许 `T-02..T-06` 在 `T-01` 后并行，但 `memory_intent_llm_service.py`、`memory_admin_service.py` 与 `document_memory_service.py` 存在高耦合共享修改面，本轮以设计正确性优先，采用串行收敛。

## 2. implementation_tasks（机读）

```yaml
implementation_tasks:
  - task_id: T-01
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[0]
    feature_id: P1-01
    phase: Phase-1
    change_type: modify
    owner: memory-platform
    pr_id: PR-01
    risk_point: 主链同时改动 chat 编排、LLM 决策合同与 document_memory 写入入口，最容易出现 accepted/rejected 口径漂移
    rollback_point: feature.memory_llm_primary_pipeline_enabled=false
    depends_on_tasks: [DESIGN-APPROVED]
    file_paths:
      - app/services/chat_service.py
      - app/services/memory_intent_llm_service.py
      - app/services/document_memory_service.py
    symbols:
      - _persist_document_memory_context
      - decide
      - flush_canonical_memory
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_memory_intent_llm_service.py tests/unit/test_chat_service_memory_flags.py -q
      - venv/bin/python -m pytest tests/unit/test_memory_intent_worker_service.py -q

  - task_id: T-04
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[3]
    feature_id: P1-02
    phase: Phase-2
    change_type: modify
    owner: memory-platform
    pr_id: PR-04
    risk_point: Prompt 与解析合同若不同步，会让 identity memory 漏记或返回非数组 memories
    rollback_point: feature.memory_identity_semantic_judge_enabled=false
    depends_on_tasks: [T-01]
    file_paths:
      - app/ai/prompts/agent_prompts.py
      - app/services/memory_intent_llm_service.py
      - tests/unit/test_memory_intent_llm_service.py
    symbols:
      - MEMORY_INTENT_DECISION_PROMPT
      - decide
      - test_*_identity_semantic_should_accept_without_trigger
      - test_*_multi_memory_items_should_return_array
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_memory_intent_llm_service.py -q -k "identity_semantic or multi_memory_items"

  - task_id: T-05
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[4]
    feature_id: P1-03
    phase: Phase-2
    change_type: modify
    owner: memory-platform
    pr_id: PR-05
    risk_point: slot taxonomy 与多 item 原子校验若不同步，会造成 style 归一漂移或批量部分成功
    rollback_point: feature.memory_style_semantic_judge_enabled=false
    depends_on_tasks: [T-01, T-04]
    file_paths:
      - app/services/memory_intent_llm_service.py
      - app/services/memory_slot_governance_service.py
      - tests/unit/test_memory_intent_llm_service.py
      - tests/unit/test_memory_slot_governance_service.py
      - tests/unit/test_document_memory_service.py
    symbols:
      - decide
      - normalize_slot_key
      - test_*_style_semantic_should_normalize
      - test_*_multi_preference_sentence_should_emit_two_memories
      - test_*_atomic_batch_should_reject_partial_invalid_memories
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_memory_intent_llm_service.py tests/unit/test_memory_slot_governance_service.py -q
      - venv/bin/python -m pytest tests/unit/test_document_memory_service.py -q -k atomic_batch

  - task_id: T-02
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[1]
    feature_id: P2-01
    phase: Phase-3
    change_type: modify
    owner: memory-platform
    pr_id: PR-02
    risk_point: memory_admin 列表与详情若新增字段不同步，会形成后台口径漂移
    rollback_point: feature.memory_admin_decision_observability=false
    depends_on_tasks: [T-01]
    file_paths:
      - app/services/memory_admin_service.py
      - app/api/v1/endpoints/memory_admin_api.py
      - app/schemas/memory_admin.py
    symbols:
      - list_memories
      - search_memories
      - MemoryQueryItem
    acceptance_cmds:
      - venv/bin/python -m pytest tests/api/test_memory_admin_api.py -q -k "memories_list or memory_detail"
      - rg -n "decision_id|confidence|reason_code" app/schemas/memory_admin.py app/services/memory_admin_service.py app/api/v1/endpoints/memory_admin_api.py

  - task_id: T-06
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[5]
    feature_id: P2-02
    phase: Phase-3
    change_type: modify
    owner: memory-platform
    pr_id: PR-06
    risk_point: `rejected_items_count/item_errors` 若未在 admin contract 中合同化，atomic_batch 拒绝将不可复盘
    rollback_point: feature.memory_admin_decision_observability=false
    depends_on_tasks: [T-02, T-05]
    file_paths:
      - app/services/memory_admin_service.py
      - app/api/v1/endpoints/memory_admin_api.py
      - app/schemas/memory_admin.py
      - tests/api/test_memory_admin_api.py
    symbols:
      - list_memories
      - get_memory_detail
      - MemoryListItem
      - MemoryDetailResponse
    acceptance_cmds:
      - rg -n "rejected_items_count|item_errors|decision_id|confidence" app/schemas/memory_admin.py app/services/memory_admin_service.py app/api/v1/endpoints/memory_admin_api.py
      - venv/bin/python -m pytest tests/api/test_memory_admin_api.py -q

  - task_id: T-03
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[2]
    feature_id: P3-01
    phase: Phase-4
    change_type: modify
    owner: memory-platform
    pr_id: PR-03
    risk_point: 误记/漏记质量门禁若不在最终合同落稳后统一补齐，容易遗漏翻译/否定/显式偏好边界回归
    rollback_point: revert:test-memory-quality-gates
    depends_on_tasks: [T-01, T-04, T-05, T-06]
    file_paths:
      - tests/unit/test_memory_intent_llm_service.py
      - tests/unit/test_user_preference_memory_service.py
      - tests/unit/test_document_memory_service.py
    symbols:
      - test_*_translation_should_not_persist
      - test_*_explicit_preference_should_persist
      - test_*_identity_semantic_should_accept_without_trigger
      - test_*_atomic_batch_should_reject_partial_invalid_memories
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_memory_intent_llm_service.py tests/unit/test_user_preference_memory_service.py tests/unit/test_document_memory_service.py -q
      - python3 scripts/check_workflow_contract.py --mode clarify_plan --requirements-path docs/内部参考/迭代需求/preference-intent-judge_requirements.md --implementation-path docs/内部参考/迭代需求/preference-intent-judge_implementation_plan.md --output docs/内部参考/迭代需求/preference-intent-judge_clarify_plan_alignment.json
      - python3 scripts/check_workflow_contract.py --mode planning_temporal_gate --implementation-path docs/内部参考/迭代需求/preference-intent-judge_implementation_plan.md --output docs/内部参考/迭代需求/preference-intent-judge_planning_temporal_gate.json
```

## 3. task_to_pr_mapping（机读）

```yaml
planning_contract:
  task_to_pr_mapping:
    - task_id: T-01
      pr_id: PR-01
      pr_branch: codex/preference-intent-judge-pr-01
      pr_depends_on: []
      pr_subject: "P1 主判定链重构：DecisionContract + 主链编排"
      acceptance_cmds:
        - venv/bin/python -m pytest tests/unit/test_memory_intent_llm_service.py tests/unit/test_chat_service_memory_flags.py -q
      rollback_point: feature.memory_llm_primary_pipeline_enabled=false

    - task_id: T-04
      pr_id: PR-04
      pr_branch: codex/preference-intent-judge-pr-04
      pr_depends_on: [PR-01]
      pr_subject: "P1 身份语义直判与 memories[] 合同化"
      acceptance_cmds:
        - venv/bin/python -m pytest tests/unit/test_memory_intent_llm_service.py -q -k "identity_semantic or multi_memory_items"
      rollback_point: feature.memory_identity_semantic_judge_enabled=false

    - task_id: T-05
      pr_id: PR-05
      pr_branch: codex/preference-intent-judge-pr-05
      pr_depends_on: [PR-04]
      pr_subject: "P1 风格槽位归一与 atomic_batch 校验"
      acceptance_cmds:
        - venv/bin/python -m pytest tests/unit/test_memory_intent_llm_service.py tests/unit/test_memory_slot_governance_service.py -q
        - venv/bin/python -m pytest tests/unit/test_document_memory_service.py -q -k atomic_batch
      rollback_point: feature.memory_style_semantic_judge_enabled=false

    - task_id: T-02
      pr_id: PR-02
      pr_branch: codex/preference-intent-judge-pr-02
      pr_depends_on: [PR-01]
      pr_subject: "P2 后台查询审计口径收敛"
      acceptance_cmds:
        - venv/bin/python -m pytest tests/api/test_memory_admin_api.py -q -k "memories_list or memory_detail"
      rollback_point: feature.memory_admin_decision_observability=false

    - task_id: T-06
      pr_id: PR-06
      pr_branch: codex/preference-intent-judge-pr-06
      pr_depends_on: [PR-02, PR-05]
      pr_subject: "P2 admin 审计字段合同化与 atomic_batch 拒绝可见化"
      acceptance_cmds:
        - rg -n "rejected_items_count|item_errors|decision_id|confidence" app/schemas/memory_admin.py app/services/memory_admin_service.py app/api/v1/endpoints/memory_admin_api.py
      rollback_point: feature.memory_admin_decision_observability=false

    - task_id: T-03
      pr_id: PR-03
      pr_branch: codex/preference-intent-judge-pr-03
      pr_depends_on: [PR-01, PR-04, PR-05, PR-06]
      pr_subject: "P3 误记/漏记质量门禁与规划门禁收口"
      acceptance_cmds:
        - venv/bin/python -m pytest tests/unit/test_memory_intent_llm_service.py tests/unit/test_user_preference_memory_service.py tests/unit/test_document_memory_service.py -q
        - python3 scripts/check_workflow_contract.py --mode clarify_plan --requirements-path docs/内部参考/迭代需求/preference-intent-judge_requirements.md --implementation-path docs/内部参考/迭代需求/preference-intent-judge_implementation_plan.md --output docs/内部参考/迭代需求/preference-intent-judge_clarify_plan_alignment.json
        - python3 scripts/check_workflow_contract.py --mode planning_temporal_gate --implementation-path docs/内部参考/迭代需求/preference-intent-judge_implementation_plan.md --output docs/内部参考/迭代需求/preference-intent-judge_planning_temporal_gate.json
      rollback_point: revert:test-memory-quality-gates
  execution_mode: serial
  strict_single_active_card: true
  card_order: [C01, C02, C03, C04, C05, C06]
  cards:
    - card_id: C01
      task_id: T-01
      wave: P1
      depends_on: []
    - card_id: C02
      task_id: T-04
      wave: P1
      depends_on: [C01]
    - card_id: C03
      task_id: T-05
      wave: P1
      depends_on: [C02]
    - card_id: C04
      task_id: T-02
      wave: P2
      depends_on: [C01]
    - card_id: C05
      task_id: T-06
      wave: P2
      depends_on: [C03, C04]
    - card_id: C06
      task_id: T-03
      wave: P3
      depends_on: [C01, C02, C03, C05]
```

## 4. planning_contract 摘要

- 采用 `core + serial`，不是因为任务不能并行，而是因为 `memory_intent_llm_service.py`、`document_memory_service.py`、`memory_admin_service.py` 三个核心点位共享语义边界，串行更容易保持合同一致。
- `T-04/T-05` 先于 `T-02/T-06`，原因是后台展示字段必须建立在 identity/style/atomic_batch 合同先落稳之后。
- `T-03` 作为统一质量收口，最后绑定 `clarify_plan` 与 `planning_temporal_gate`，避免边做边失配。

## 5. execution_contract（机读）

```yaml
execution_contract:
  preferred_mode: core
  execution_contract_ready: true
  delivery_mode: staged
  execution_unit: per_task
  commit_policy: per_pr
  stop_boundary: per_task
  temporal_gate_forbidden: true
  context_verified: true
  design_source: docs/plans/2026-03-05-preference-intent-judge-design.md
  requirements_source: docs/内部参考/迭代需求/preference-intent-judge_requirements.md
```

## 6. implementation_readiness（机读）

```yaml
implementation_readiness:
  implementation_ready: true
  execution_contract_ready: true
  requirements_ready: true
  traceability_ready: true
  blocked_by: []
  next_step: /jjk-imp
  readiness_note: approved_design_and_hydrated_tasks
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
    task_id: T-04
    pr_id: PR-04
  - tc_id: TC-05
    task_id: T-05
    pr_id: PR-05
  - tc_id: TC-06
    task_id: T-06
    pr_id: PR-06
```
