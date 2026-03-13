# agent-intent-anti-false-trigger 实施计划

## 1. 实施概览

- 规划模式：`core`
- 交付目标：先建立 `DataIntentContract + Router/Resolver`，再把 workflow 接线迁走，随后补齐负样本/补充轮/回放/真理源回归，最后同步文档。
- 风险重点：热点大文件继续膨胀、回放 canonical 漂移、补充轮误伤、影子对账阻塞主路径。
- 门禁收口：当前规划以 `router_result_v2` 为唯一 runtime/replay contract，最终通过 `clarify_plan + planning_temporal_gate + docs_guard` 三道门禁收口。

## 2. implementation_tasks

```yaml
implementation_tasks:
  - task_id: T01
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[0]
    feature_id: P1-data-intent-contract-and-router
    pr_id: PR-01
    phase: Phase-1
    change_type: add
    owner: ai-routing
    depends_on_tasks: [ROOT]
    risk_point: Router contract 若与现有 route_decisions 骨架脱节，会直接制造第二套运行态结构
    rollback_point: revert:data-intent-contract-and-router
    risk_tags: []
    mandatory_evidence: []
    file_paths:
      - app/ai/router/data_intent_contract.py
      - app/ai/router/data_intent_router.py
    symbols:
      - DataIntentContract
      - ClarifyContract
      - decide_data_intent
      - build_candidate_signals
      - frame_supported_supplement
      - shadow_compare_async
    acceptance_cmds:
      - cmd: bash scripts/pytest_targeted.sh tests/unit/test_data_intent_router_contract.py -q
        kind: unit
      - cmd: bash scripts/pytest_targeted.sh tests/unit/test_data_intent_router_shadow_compare.py -q
        kind: unit

  - task_id: T02
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[1]
    feature_id: P1-data-intent-resolver-and-guards
    pr_id: PR-02
    phase: Phase-1
    change_type: add
    owner: data-runtime
    depends_on_tasks: [T01]
    risk_point: Resolver 若没有把时间/维度/列语义与安全边界收口，会继续让编排层兜底
    rollback_point: revert:data-intent-resolver-and-guards
    risk_tags: [data_db]
    mandatory_evidence: [data_db_route_sql_result]
    file_paths:
      - app/ai/router/data_intent_resolver.py
      - app/services/time_parser.py
    symbols:
      - resolve_data_intent
      - resolve_metric_source_of_truth
      - resolve_dimension_with_whitelist
      - resolve_chart_slots
      - NaturalTimeParser
      - safe_to_execute
    acceptance_cmds:
      - cmd: bash scripts/pytest_targeted.sh tests/unit/test_data_intent_resolver_guardrails.py -q
        kind: data_db
      - cmd: bash scripts/pytest_targeted.sh tests/unit/test_data_intent_semantic_source_contract.py -q
        kind: data_db

  - task_id: T03
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[2]
    feature_id: P1-workflow-legacy-branch-retirement
    pr_id: PR-03
    phase: Phase-2
    change_type: refactor
    owner: data-workflow
    depends_on_tasks: [T01, T02]
    risk_point: 热点 workflow 文件若继续新增私有 helper，会违反 lean 门禁并把旧问题搬新地方
    rollback_point: revert:workflow-legacy-branch-retirement
    risk_tags: [data_db]
    mandatory_evidence: [data_db_route_sql_result]
    file_paths:
      - app/ai/workflow/data_graph.py
      - app/ai/workflow/data_intent_helpers.py
      - app/ai/workflow/session_intent_kernel.py
    symbols:
      - classify_turn_act
      - data_intent_router_integration
    acceptance_cmds:
      - cmd: bash scripts/pytest_targeted.sh tests/unit/test_data_intent_router_negative_cases.py -q
        kind: data_db
      - cmd: bash scripts/pytest_targeted.sh tests/unit/test_data_intent_router_supplement_cases.py -q
        kind: data_db
      - cmd: bash scripts/pytest_targeted.sh tests/unit/test_data_intent_router_contract.py tests/unit/test_data_intent_router_negative_cases.py tests/unit/test_data_intent_router_supplement_cases.py -q
        kind: data_db

  - task_id: T04
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[3]
    feature_id: P2-router-result-v2-integration
    pr_id: PR-04
    phase: Phase-2
    change_type: modify
    owner: chat-runtime
    depends_on_tasks: [T03]
    risk_point: router_result_v2 若扩展到错误层级，会破坏 replay 与历史消费方
    rollback_point: revert:router-result-v2-data-intent-extension
    risk_tags: [chat_db]
    mandatory_evidence: [chat_db_write_read]
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
      - app/ai/state.py
      - app/repositories/chat_repo.py
    symbols:
      - _build_router_result_v2_payload
      - _extract_router_result_v2
      - route_decisions[].data_intent
      - additional_kwargs.router_result_v2
      - router_replay_bridge
    acceptance_cmds:
      - cmd: bash scripts/pytest_targeted.sh tests/unit/test_router_result_v2_replay.py -q
        kind: chat_db

  - task_id: T05
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[4]
    feature_id: P2-router-regression-suite
    pr_id: PR-05
    phase: Phase-3
    change_type: add
    owner: ai-quality
    depends_on_tasks: [T03, T04]
    risk_point: 负样本与补充轮样本不足，会让误触发问题回流主干
    rollback_point: revert:router-regression-suite
    risk_tags: []
    mandatory_evidence: []
    file_paths:
      - tests/unit/test_data_intent_router_contract.py
      - tests/unit/test_data_intent_router_negative_cases.py
      - tests/unit/test_data_intent_router_supplement_cases.py
      - tests/unit/test_data_intent_router_shadow_compare.py
    symbols:
      - router_contract_tests
      - anti_false_trigger_tests
      - supplement_tests
      - shadow_compare_tests
    acceptance_cmds:
      - cmd: bash scripts/pytest_targeted.sh tests/unit/test_data_intent_router_contract.py -q
        kind: unit
      - cmd: bash scripts/pytest_targeted.sh tests/unit/test_data_intent_router_negative_cases.py -q
        kind: unit
      - cmd: bash scripts/pytest_targeted.sh tests/unit/test_data_intent_router_supplement_cases.py -q
        kind: unit
      - cmd: bash scripts/pytest_targeted.sh tests/unit/test_data_intent_router_shadow_compare.py -q
        kind: unit

  - task_id: T06
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[5]
    feature_id: P2-clarify-and-source-contract-regression
    pr_id: PR-06
    phase: Phase-3
    change_type: add
    owner: ai-contract
    depends_on_tasks: [T02, T04, T05]
    risk_point: Clarify contract 或真理源 contract 若没有独立回归，后续很容易被局部补丁打穿
    rollback_point: revert:clarify-and-source-contract-regression
    risk_tags: [data_db]
    mandatory_evidence: [data_db_route_sql_result]
    file_paths:
      - tests/unit/test_data_intent_resolver_guardrails.py
      - tests/unit/test_data_intent_clarify_contract.py
      - tests/unit/test_data_intent_semantic_source_contract.py
    symbols:
      - resolver_guardrail_tests
      - clarify_contract_tests
      - semantic_source_tests
    acceptance_cmds:
      - cmd: bash scripts/pytest_targeted.sh tests/unit/test_data_intent_clarify_contract.py -q
        kind: data_db
      - cmd: bash scripts/pytest_targeted.sh tests/unit/test_data_intent_semantic_source_contract.py -q
        kind: data_db

  - task_id: T07
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[6]
    feature_id: P3-doc-sync-and-plan-gates
    pr_id: PR-07
    phase: Phase-4
    change_type: modify
    owner: docs-governance
    depends_on_tasks: [T01, T02, T03, T04, T05, T06]
    risk_point: 文档与规划门禁若不同步，后续执行链会再次发生 contract 漂移
    rollback_point: revert:doc-sync-and-plan-gates
    risk_tags: []
    mandatory_evidence: []
    file_paths:
      - docs/开发文档/架构设计/AI模块设计.md
      - docs/内部参考/迭代需求/agent-intent-anti-false-trigger_requirements.md
      - docs/内部参考/迭代需求/agent-intent-anti-false-trigger_implementation_plan.md
    symbols:
      - router_contract_runtime_sections
      - clarify_plan_alignment_report
      - planning_temporal_gate_report
      - docs_guard_strict
    acceptance_cmds:
      - cmd: PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/docs_guard.py --strict
        kind: integration
      - cmd: PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/check_workflow_contract.py --mode clarify_plan --requirements-path docs/内部参考/迭代需求/agent-intent-anti-false-trigger_requirements.md --implementation-path docs/内部参考/迭代需求/agent-intent-anti-false-trigger_implementation_plan.md --output docs/内部参考/迭代需求/agent-intent-anti-false-trigger_clarify_plan_alignment.json
        kind: integration
      - cmd: PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/check_workflow_contract.py --mode planning_temporal_gate --implementation-path docs/内部参考/迭代需求/agent-intent-anti-false-trigger_implementation_plan.md --output docs/内部参考/迭代需求/agent-intent-anti-false-trigger_planning_temporal_gate.json
        kind: integration
```

## 3. execution_contract

```yaml
execution_contract:
  preferred_mode: core
  execution_contract_ready: true
  delivery_mode: staged
  execution_unit: per_task
  commit_policy: per_pr
  stop_boundary: per_pr
```

## 4. implementation_readiness

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
