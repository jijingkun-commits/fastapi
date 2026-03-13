# context-engineering-unification 实施计划

> 更新时间：2026-03-11 18:45 +08:00  
> 上游设计：`docs/plans/2026-03-10-context-engineering-unification-design.md`  
> 对应需求：`docs/内部参考/迭代需求/context-engineering-unification_requirements.md`

## 1. 实施概览

- 规划模式：`core`
- 交付目标：以“单一 pre-model context builder + prompt/tool token 账本 + 技能/工具上下文收口”三段式完成上下文工程治理，不引入第二套 prompt 管道。
- 架构策略：先收口 builder 与预算账本，再补模型感知预算与工具/技能上下文治理，最后用测试、文档与规划门禁收口。
- 风险重点：builder 未成为单一真相源导致双轨拼接、tool schema 未入账本导致误判大头、`loaded_skill_context` 继续全文注入、误恢复旧式 `system_context` 补齐提示与最新 master 语义冲突。

## 2. implementation_tasks（机读）

```yaml
implementation_tasks:
  - task_id: T-01
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[0]
    feature_id: P1-context-builder
    pr_id: PR-01
    phase: Phase-1
    change_type: create_or_modify
    owner: backend-ai-context
    depends_on_tasks: [ROOT]
    risk_point: 若 builder 仍不是单一上下文装配入口，graph 会继续出现 trim 后再追加 system/skill 文本的双轨行为
    rollback_point: ENABLE_CONTEXT_BUILDER_V1=false
    file_paths:
      - app/ai/context_engineering.py
      - app/ai/workflow/multi_agent_graph.py
      - tests/unit/test_multi_agent_context_budget.py
      - tests/unit/test_multi_agent_streaming_helpers.py
    symbols:
      - build_llm_input_context
      - ContextBudgetLedger
      - _prepare_streaming_inference_state
    risk_tags: [contract, context, observability]
    mandatory_evidence: [context_budget_ledger_single_owner, llm_input_context_single_entry]
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_context_budget.py
      - bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py -k 'tool_message_diagnostics or inject_streaming_context_messages_inserts_after_system_prefix'

  - task_id: T-02
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[1]
    feature_id: P1-model-aware-budget
    pr_id: PR-01
    phase: Phase-2
    change_type: modify
    owner: backend-ai-routing
    depends_on_tasks: [T-01]
    risk_point: 若预算仍只看环境变量，不看场景模型与 prompt/tool 固定成本，token 大头会继续被误判成 messages 历史
    rollback_point: ENABLE_CONTEXT_BUILDER_V1=false
    file_paths:
      - app/ai/llm_util.py
      - app/services/llm_scene_service.py
      - app/services/llm_config_service.py
      - app/ai/context_engineering.py
      - app/ai/workflow/multi_agent_graph.py
    symbols:
      - get_scene_llm
      - resolve_model_code
      - get_model_config
      - resolve_context_window_budget
      - SUPERVISOR_PROMPT
      - _get_supervisor_tools
    risk_tags: [contract, context, performance]
    mandatory_evidence: [prompt_token_estimate_accounted, tool_schema_token_estimate_accounted]
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_context_budget.py -k model_aware_budget
      - bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py -k prompt_or_tool_schema

  - task_id: T-03
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[2]
    feature_id: P1-tool-context-editing
    pr_id: PR-01
    phase: Phase-3
    change_type: modify
    owner: backend-ai-orchestration
    depends_on_tasks: [T-01]
    risk_point: 若旧 ToolMessage 和冗余工具集不先去噪，prompt/tool token 账本即便可见，回答质量仍会被噪音拖垮
    rollback_point: ENABLE_TOOL_CONTEXT_EDIT_V1=false
    file_paths:
      - app/ai/context_engineering.py
      - app/ai/workflow/multi_agent_graph.py
      - tests/unit/test_multi_agent_streaming_helpers.py
    symbols:
      - edit_tool_messages_for_context
      - build_retrieval_digest
      - _compact_tool_message_for_inference
    risk_tags: [context, tool_runtime, replay]
    mandatory_evidence: [selected_tools_for_turn_recorded, tool_context_edit_priority_order]
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py -k tool_message
      - bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py -k router_contract_guard

  - task_id: T-04
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[3]
    feature_id: P1-skill-context-canonical
    pr_id: PR-01
    phase: Phase-4
    change_type: modify
    owner: backend-skill-runtime
    depends_on_tasks: [T-01]
    risk_point: 若 `loaded_skill_context` 仍作为真相源全文注入，skills 会继续成为 preprocess token 大头
    rollback_point: ENABLE_SKILL_CONTEXT_CANONICAL_V1=false
    file_paths:
      - app/services/skill_service.py
      - app/ai/state.py
      - app/ai/context_engineering.py
      - app/tests/test_skill_loader_tool.py
    symbols:
      - build_loaded_skill_context_from_registry
      - loaded_skill_registry
      - loaded_skill_context
      - additional_kwargs.context_runtime
    risk_tags: [contract, replay, context]
    mandatory_evidence: [loaded_skill_registry_single_owner, context_runtime_read_old_write_new]
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh app/tests/test_skill_loader_tool.py tests/unit/test_multi_agent_streaming_helpers.py -k skill_context
      - bash scripts/pytest_targeted.sh app/tests/test_skill_loader_tool.py -k replay

  - task_id: T-05
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[4]
    feature_id: P1-doc-and-observability
    pr_id: PR-01
    phase: Phase-5
    change_type: modify
    owner: docs-and-governance
    depends_on_tasks: [T-02, T-03, T-04]
    risk_point: 若不把最新 master 的结果式 replay 语义、账本字段和规划门禁一起收口，下游实现会再次偏离现状
    rollback_point: 回退本轮新增文档与账本说明，恢复 design 基线
    file_paths:
      - docs/开发文档/测试管理/测试报告/README.md
      - docs/plans/2026-03-10-context-engineering-unification-design.md
      - app/ai/context_engineering.py
      - tests/unit/test_multi_agent_context_budget.py
    symbols:
      - context_budget_ledger
      - delivery_meta.context_budget_ledger
    risk_tags: [docs, observability, contract]
    mandatory_evidence: [clarify_plan_alignment_json, planning_temporal_gate_json, docs_guard_strict_clean]
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_context_budget.py tests/unit/test_multi_agent_streaming_helpers.py
      - /Users/jijingkun/.codex/worktrees/4620/fastapi/venv/bin/python scripts/check_workflow_contract.py --mode clarify_plan --requirements-path docs/内部参考/迭代需求/context-engineering-unification_requirements.md --implementation-path docs/内部参考/迭代需求/context-engineering-unification_implementation_plan.md --output docs/内部参考/迭代需求/context-engineering-unification_clarify_plan_alignment.json
      - /Users/jijingkun/.codex/worktrees/4620/fastapi/venv/bin/python scripts/check_workflow_contract.py --mode planning_temporal_gate --implementation-path docs/内部参考/迭代需求/context-engineering-unification_implementation_plan.md --output docs/内部参考/迭代需求/context-engineering-unification_planning_temporal_gate.json
      - /Users/jijingkun/.codex/worktrees/4620/fastapi/venv/bin/python scripts/docs_guard.py --strict
```

## 3. task_to_pr_mapping（机读）

```yaml
planning_contract:
  task_to_pr_mapping:
    - task_id: T-01
      pr_id: PR-01
      pr_branch: codex/context-engineering-unification
      pr_depends_on: []
      pr_subject: "上下文 builder 单一入口与账本基础"
      acceptance_cmds:
        - bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_context_budget.py
      rollback_point: ENABLE_CONTEXT_BUILDER_V1=false
    - task_id: T-02
      pr_id: PR-01
      pr_branch: codex/context-engineering-unification
      pr_depends_on: []
      pr_subject: "模型感知预算与 prompt/tool token 账本"
      acceptance_cmds:
        - bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_context_budget.py -k model_aware_budget
      rollback_point: ENABLE_CONTEXT_BUILDER_V1=false
    - task_id: T-03
      pr_id: PR-01
      pr_branch: codex/context-engineering-unification
      pr_depends_on: []
      pr_subject: "工具上下文去噪与 selected_tools_for_turn 收口"
      acceptance_cmds:
        - bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py -k tool_message
      rollback_point: ENABLE_TOOL_CONTEXT_EDIT_V1=false
    - task_id: T-04
      pr_id: PR-01
      pr_branch: codex/context-engineering-unification
      pr_depends_on: []
      pr_subject: "技能正文 canonical 收口与回放迁移"
      acceptance_cmds:
        - bash scripts/pytest_targeted.sh app/tests/test_skill_loader_tool.py tests/unit/test_multi_agent_streaming_helpers.py -k skill_context
      rollback_point: ENABLE_SKILL_CONTEXT_CANONICAL_V1=false
    - task_id: T-05
      pr_id: PR-01
      pr_branch: codex/context-engineering-unification
      pr_depends_on: []
      pr_subject: "专项测试、文档同步与规划门禁收口"
      acceptance_cmds:
        - /Users/jijingkun/.codex/worktrees/4620/fastapi/venv/bin/python scripts/check_workflow_contract.py --mode clarify_plan --requirements-path docs/内部参考/迭代需求/context-engineering-unification_requirements.md --implementation-path docs/内部参考/迭代需求/context-engineering-unification_implementation_plan.md --output docs/内部参考/迭代需求/context-engineering-unification_clarify_plan_alignment.json
        - /Users/jijingkun/.codex/worktrees/4620/fastapi/venv/bin/python scripts/check_workflow_contract.py --mode planning_temporal_gate --implementation-path docs/内部参考/迭代需求/context-engineering-unification_implementation_plan.md --output docs/内部参考/迭代需求/context-engineering-unification_planning_temporal_gate.json
      rollback_point: 回退本轮新增文档与账本说明，恢复 design 基线
  execution_mode: core
  strict_single_active_card: true
  task_key: PP-20260311-context-engineering-unification
```

## 4. planning_contract 摘要
- 执行模式：`core`，不走并行拆卡；原因是 builder、prompt/tool 账本、技能上下文 canonical、replay 语义互相耦合，半切换状态风险高于并行收益。
- PR 策略：所有 `task_id` 归并到单一 `PR-01`，以 `single_commit` 收口，避免主干出现“账本已上、技能 canonical 未上”的中间态。
- 阶段顺序：`T-01` 打底单一入口与账本结构，`T-02/T-03/T-04` 分别完成模型感知预算、工具去噪、技能 canonical，`T-05` 统一补测试、文档与规划门禁。
- 阻断策略：任一阶段未通过专项验收，不进入下一阶段；不允许引入依赖自然时间成熟、TTL 到期或观察窗口成熟的阻断条件。

## 5. execution_contract（机读）

```yaml
execution_contract:
  delivery_mode: staged
  execution_unit: all_tasks
  commit_policy: single_commit
  stop_boundary: none
  stop_on_blocked: true
  source_seed_ref: clarify_handoff_contract.required.execution_chain_seed.execution_contract_hint
```

## 6. implementation_readiness（机读）

```yaml
implementation_readiness:
  implementation_ready: true
  blocked_by: []
  next_step: $jjk-imp
  execution_contract_ready: true
```

## 7. acceptance_cmd_contracts（机读扩展）

```yaml
acceptance_cmd_contracts:
  - task_id: T-01
    acceptance_cmds:
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_context_budget.py
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py -k 'tool_message_diagnostics or inject_streaming_context_messages_inserts_after_system_prefix'
  - task_id: T-02
    acceptance_cmds:
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_context_budget.py -k model_aware_budget
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py -k prompt_or_tool_schema
  - task_id: T-03
    acceptance_cmds:
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py -k tool_message
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py -k router_contract_guard
  - task_id: T-04
    acceptance_cmds:
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh app/tests/test_skill_loader_tool.py tests/unit/test_multi_agent_streaming_helpers.py -k skill_context
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh app/tests/test_skill_loader_tool.py -k replay
  - task_id: T-05
    acceptance_cmds:
      - kind: integration
        cmd: /Users/jijingkun/.codex/worktrees/4620/fastapi/venv/bin/python scripts/check_workflow_contract.py --mode clarify_plan --requirements-path docs/内部参考/迭代需求/context-engineering-unification_requirements.md --implementation-path docs/内部参考/迭代需求/context-engineering-unification_implementation_plan.md --output docs/内部参考/迭代需求/context-engineering-unification_clarify_plan_alignment.json
      - kind: integration
        cmd: /Users/jijingkun/.codex/worktrees/4620/fastapi/venv/bin/python scripts/check_workflow_contract.py --mode planning_temporal_gate --implementation-path docs/内部参考/迭代需求/context-engineering-unification_implementation_plan.md --output docs/内部参考/迭代需求/context-engineering-unification_planning_temporal_gate.json
      - kind: integration
        cmd: /Users/jijingkun/.codex/worktrees/4620/fastapi/venv/bin/python scripts/docs_guard.py --strict
```

## 8. TC 覆盖映射

```yaml
tc_execution_mapping:
  - tc_id: TC-CEU-01
    task_id: T-01
    pr_id: PR-01
  - tc_id: TC-CEU-02
    task_id: T-02
    pr_id: PR-01
  - tc_id: TC-CEU-03
    task_id: T-03
    pr_id: PR-01
  - tc_id: TC-CEU-04
    task_id: T-04
    pr_id: PR-01
  - tc_id: TC-CEU-05
    task_id: T-05
    pr_id: PR-01
```
