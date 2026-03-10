# 监督者主会话状态归属与附件规划实施方案

> 更新时间：2026-03-10 10:04 +08:00
> 上游设计：`docs/plans/2026-03-09-supervisor-conversation-state-ownership-design.md`
> 对应需求：`docs/内部参考/迭代需求/监督者主会话状态归属与附件规划_requirements.md`
> 文档目标：定义 HOW（implementation_tasks、PR 映射、执行合同、实施就绪度），供 `$jjk-imp` 直接承接

## 1. 实施概览

- 规划模式：`core`
- 交付目标：先收口主会话 state owner 与 replay canonical，再把待办/问数 workflow 改成 contract-first，最后落附件规划与文档同步。
- 风险重点：主链状态与局部流程状态混写、附件路由继续依赖 prompt hint、research dispatch 过度工程化。
- 推荐顺序：先做主链 contract，再改 workflow，再落附件规划和文档；避免先改附件导致 owner 继续漂移。

## 2. implementation_tasks（机读）

```yaml
implementation_tasks:
  - task_id: T01
    feature_id: P1-supervisor-state-owner
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[0]
    pr_id: PR-01
    phase: Phase-1
    file_paths:
      - app/ai/state.py
      - docs/开发文档/架构设计/AI模块设计.md
    symbols:
      - BaseAgentState
      - MultiAgentState
      - 状态分层说明
    change_type: refactor
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_multi_agent_context_budget.py -q
    rollback_point: SUPERVISOR_CONVERSATION_STATE_V1=false
    depends_on_tasks: [ROOT]
    owner: ai-workflow
    risk_point: 若 state owner 继续含糊，后续 contract-first 与附件规划都只是表面补丁
    risk_tags: [contract, state]
    mandatory_evidence: [state_owner_single_source, targeted_unit_green]

  - task_id: T02
    feature_id: P1-supervisor-state-owner
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[1]
    pr_id: PR-01
    phase: Phase-2
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
      - app/ai/protocol.py
    symbols:
      - router_result_v2
      - conversation_state replay snapshot
      - _build_expert_inference_messages
    change_type: refactor
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_multi_agent_context_budget.py -q
    rollback_point: SUPERVISOR_CONVERSATION_STATE_V1=false
    depends_on_tasks: [T01]
    owner: ai-workflow
    risk_point: replay canonical 与 expert_input_contract 若不同步，会形成双真理源
    risk_tags: [contract, replay]
    mandatory_evidence: [replay_canonical_single_source, supervisor_final_answer_guard]

  - task_id: T03
    feature_id: P2-workflow-state-isolation
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[2]
    pr_id: PR-02
    phase: Phase-3
    file_paths:
      - app/ai/workflow/todo_graph.py
      - app/ai/workflow/todo_intent_helpers.py
    symbols:
      - analyze_intent
      - filter_messages_for_todo
      - todo expert input contract
    change_type: refactor
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_todo_handoff_observation.py tests/unit/test_todo_nodes.py -q
    rollback_point: EXPERT_INPUT_CONTRACT_FIRST=false
    depends_on_tasks: [T02]
    owner: ai-workflow
    risk_point: 待办 workflow 若继续偷读 recent_messages，会把主链状态与闭环流程耦死
    risk_tags: [contract, workflow]
    mandatory_evidence: [todo_contract_first_verified, targeted_unit_green]

  - task_id: T04
    feature_id: P2-workflow-state-isolation
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[3]
    pr_id: PR-02
    phase: Phase-3
    file_paths:
      - app/ai/workflow/data_graph.py
    symbols:
      - _extract_handoff_context
      - create_data_graph
      - data expert input contract
    change_type: refactor
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_data_graph_pending_handoff_state.py tests/unit/test_data_graph_clarify_guard.py -q
    rollback_point: EXPERT_INPUT_CONTRACT_FIRST=false
    depends_on_tasks: [T02]
    owner: ai-workflow
    risk_point: 问数 workflow 若仍按整句问题或隐式上下文推断，会放大 SQL 澄清噪音
    risk_tags: [contract, workflow]
    mandatory_evidence: [data_contract_first_verified, targeted_unit_green]

  - task_id: T05
    feature_id: P3-research-subagent-dispatch
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[4]
    pr_id: PR-03
    phase: Phase-4
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
      - app/ai/tools/ragflow_tool.py
      - app/ai/tools/chatTools.py
    symbols:
      - knowledge/web research dispatch contract
    change_type: new_feature
    acceptance_cmds:
      - rg -n "knowledge_search|search_tool|research" app/ai/workflow/multi_agent_graph.py app/ai/tools
    rollback_point: RESEARCH_SUBAGENT_DISPATCH_V1=false
    depends_on_tasks: [T02]
    owner: ai-workflow
    risk_point: research dispatch 若过重，会把一次性研究错误建模成跨轮专家
    risk_tags: [contract, subagent]
    mandatory_evidence: [research_dispatch_contract_present, tool_vs_subagent_boundary_frozen]

  - task_id: T06
    feature_id: P5-architecture-doc-sync
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[5]
    pr_id: PR-04
    phase: Phase-5
    file_paths:
      - docs/开发文档/架构设计/AI模块设计.md
      - docs/开发文档/架构设计/待办Agent设计.md
    symbols:
      - capability layering sections
    change_type: modify
    acceptance_cmds:
      - rg -n "workflow|subagent|tool|service|conversation_state" docs/开发文档/架构设计/AI模块设计.md docs/开发文档/架构设计/待办Agent设计.md
    rollback_point: 回退 capability layering 文档原位修改
    depends_on_tasks: [T01, T02, T03, T04, T05]
    owner: docs-governance
    risk_point: 文档若不同步，后续实现会重新滑回旧口径
    risk_tags: [contract, docs]
    mandatory_evidence: [architecture_docs_synced, layering_terms_consistent]

  - task_id: T07
    feature_id: P6-regression-contract-tests
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[6]
    pr_id: PR-04
    phase: Phase-5
    file_paths:
      - tests/unit/test_multi_agent_streaming_helpers.py
      - tests/unit/test_todo_handoff_observation.py
      - tests/unit/test_data_graph_pending_handoff_state.py
    symbols:
      - contract-first regressions
    change_type: modify
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_todo_handoff_observation.py tests/unit/test_data_graph_pending_handoff_state.py -q
    rollback_point: 回退 contract-first 回归用例到改造前基线
    depends_on_tasks: [T02, T03, T04]
    owner: ai-test
    risk_point: 没有回归网会导致 owner 与 handoff 契约反复回退
    risk_tags: [test, regression]
    mandatory_evidence: [contract_regression_green]

  - task_id: T08
    feature_id: P4-attachment-supervisor-planning
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[7]
    pr_id: PR-03
    phase: Phase-4
    file_paths:
      - app/services/chat_service.py
      - app/ai/workflow/multi_agent_graph.py
      - docs/开发文档/架构设计/附件系统设计.md
    symbols:
      - attachment_manifest contract
      - attachment planning
      - planning_route
    change_type: refactor
    acceptance_cmds:
      - rg -n "attachments|read_uploaded_file|attachment_manifest|planning_route|lightweight_probe" app/services/chat_service.py app/ai/workflow/multi_agent_graph.py docs/开发文档/架构设计/附件系统设计.md
    rollback_point: ATTACHMENT_SUPERVISOR_PLANNING_V1=false
    depends_on_tasks: [T02, T04, T05]
    owner: ai-workflow
    risk_point: 若只改 prompt hint 不改 contract，附件规划仍会回到按类型硬路由
    risk_tags: [contract, attachment]
    mandatory_evidence: [attachment_manifest_present, planning_route_enforced, mixed_owner_supervisor]
```

## 3. task_to_pr_mapping（机读）

```yaml
task_to_pr_mapping:
  - task_id: T01
    pr_id: PR-01
    pr_branch: codex/supervisor-state-pr-01
    pr_depends_on: []
    pr_subject: "P1 主链收口：supervisor conversation_state owner"
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_multi_agent_context_budget.py -q
    rollback_point: SUPERVISOR_CONVERSATION_STATE_V1=false
  - task_id: T02
    pr_id: PR-01
    pr_branch: codex/supervisor-state-pr-01
    pr_depends_on: []
    pr_subject: "P1 主链收口：replay canonical 与 final answer owner"
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_multi_agent_context_budget.py -q
    rollback_point: SUPERVISOR_CONVERSATION_STATE_V1=false
  - task_id: T03
    pr_id: PR-02
    pr_branch: codex/workflow-contract-pr-02
    pr_depends_on: [PR-01]
    pr_subject: "P2 workflow 收口：待办 contract-first"
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_todo_handoff_observation.py tests/unit/test_todo_nodes.py -q
    rollback_point: EXPERT_INPUT_CONTRACT_FIRST=false
  - task_id: T04
    pr_id: PR-02
    pr_branch: codex/workflow-contract-pr-02
    pr_depends_on: [PR-01]
    pr_subject: "P2 workflow 收口：问数 contract-first"
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_data_graph_pending_handoff_state.py tests/unit/test_data_graph_clarify_guard.py -q
    rollback_point: EXPERT_INPUT_CONTRACT_FIRST=false
  - task_id: T05
    pr_id: PR-03
    pr_branch: codex/research-attachment-pr-03
    pr_depends_on: [PR-01]
    pr_subject: "P3 研究调度：tool vs research_subagent 分层"
    acceptance_cmds:
      - rg -n "knowledge_search|search_tool|research" app/ai/workflow/multi_agent_graph.py app/ai/tools
    rollback_point: RESEARCH_SUBAGENT_DISPATCH_V1=false
  - task_id: T08
    pr_id: PR-03
    pr_branch: codex/research-attachment-pr-03
    pr_depends_on: [PR-01, PR-02]
    pr_subject: "P4 附件规划：supervisor planning contract"
    acceptance_cmds:
      - rg -n "attachments|read_uploaded_file|attachment_manifest|planning_route|lightweight_probe" app/services/chat_service.py app/ai/workflow/multi_agent_graph.py docs/开发文档/架构设计/附件系统设计.md
    rollback_point: ATTACHMENT_SUPERVISOR_PLANNING_V1=false
  - task_id: T06
    pr_id: PR-04
    pr_branch: codex/docs-regression-pr-04
    pr_depends_on: [PR-01, PR-02, PR-03]
    pr_subject: "P5 架构文档同步：能力分层与附件规划"
    acceptance_cmds:
      - rg -n "workflow|subagent|tool|service|conversation_state" docs/开发文档/架构设计/AI模块设计.md docs/开发文档/架构设计/待办Agent设计.md
    rollback_point: 回退 capability layering 文档原位修改
  - task_id: T07
    pr_id: PR-04
    pr_branch: codex/docs-regression-pr-04
    pr_depends_on: [PR-01, PR-02]
    pr_subject: "P6 回归护栏：contract-first regressions"
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_todo_handoff_observation.py tests/unit/test_data_graph_pending_handoff_state.py -q
    rollback_point: 回退 contract-first 回归用例到改造前基线
```

## 4. planning_contract（机读）

```yaml
planning_contract:
  plan_mode: core
  design_source: docs/plans/2026-03-09-supervisor-conversation-state-ownership-design.md
  requirements_source: docs/内部参考/迭代需求/监督者主会话状态归属与附件规划_requirements.md
  task_to_pr_mapping:
    - task_id: T01
      pr_id: PR-01
      pr_branch: codex/supervisor-state-pr-01
      pr_depends_on: []
      pr_subject: "P1 主链收口：supervisor conversation_state owner"
      acceptance_cmds:
        - bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_multi_agent_context_budget.py -q
      rollback_point: SUPERVISOR_CONVERSATION_STATE_V1=false
    - task_id: T02
      pr_id: PR-01
      pr_branch: codex/supervisor-state-pr-01
      pr_depends_on: []
      pr_subject: "P1 主链收口：replay canonical 与 final answer owner"
      acceptance_cmds:
        - bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_multi_agent_context_budget.py -q
      rollback_point: SUPERVISOR_CONVERSATION_STATE_V1=false
    - task_id: T03
      pr_id: PR-02
      pr_branch: codex/workflow-contract-pr-02
      pr_depends_on: [PR-01]
      pr_subject: "P2 workflow 收口：待办 contract-first"
      acceptance_cmds:
        - bash scripts/pytest_targeted.sh tests/unit/test_todo_handoff_observation.py tests/unit/test_todo_nodes.py -q
      rollback_point: EXPERT_INPUT_CONTRACT_FIRST=false
    - task_id: T04
      pr_id: PR-02
      pr_branch: codex/workflow-contract-pr-02
      pr_depends_on: [PR-01]
      pr_subject: "P2 workflow 收口：问数 contract-first"
      acceptance_cmds:
        - bash scripts/pytest_targeted.sh tests/unit/test_data_graph_pending_handoff_state.py tests/unit/test_data_graph_clarify_guard.py -q
      rollback_point: EXPERT_INPUT_CONTRACT_FIRST=false
    - task_id: T05
      pr_id: PR-03
      pr_branch: codex/research-attachment-pr-03
      pr_depends_on: [PR-01]
      pr_subject: "P3 研究调度：tool vs research_subagent 分层"
      acceptance_cmds:
        - rg -n "knowledge_search|search_tool|research" app/ai/workflow/multi_agent_graph.py app/ai/tools
      rollback_point: RESEARCH_SUBAGENT_DISPATCH_V1=false
    - task_id: T08
      pr_id: PR-03
      pr_branch: codex/research-attachment-pr-03
      pr_depends_on: [PR-01, PR-02]
      pr_subject: "P4 附件规划：supervisor planning contract"
      acceptance_cmds:
        - rg -n "attachments|read_uploaded_file|attachment_manifest|planning_route|lightweight_probe" app/services/chat_service.py app/ai/workflow/multi_agent_graph.py docs/开发文档/架构设计/附件系统设计.md
      rollback_point: ATTACHMENT_SUPERVISOR_PLANNING_V1=false
    - task_id: T06
      pr_id: PR-04
      pr_branch: codex/docs-regression-pr-04
      pr_depends_on: [PR-01, PR-02, PR-03]
      pr_subject: "P5 架构文档同步：能力分层与附件规划"
      acceptance_cmds:
        - rg -n "workflow|subagent|tool|service|conversation_state" docs/开发文档/架构设计/AI模块设计.md docs/开发文档/架构设计/待办Agent设计.md
      rollback_point: 回退 capability layering 文档原位修改
    - task_id: T07
      pr_id: PR-04
      pr_branch: codex/docs-regression-pr-04
      pr_depends_on: [PR-01, PR-02]
      pr_subject: "P6 回归护栏：contract-first regressions"
      acceptance_cmds:
        - bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_todo_handoff_observation.py tests/unit/test_data_graph_pending_handoff_state.py -q
      rollback_point: 回退 contract-first 回归用例到改造前基线
```

## 5. execution_contract（机读）

```yaml
execution_contract:
  delivery_mode: staged
  execution_unit: per_task
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
  next_step: $jjk-imp
  execution_contract_ready: true
```

## 7. TC -> Task 追溯映射

| tc_id | feature_id | task_id | acceptance_cmd |
|---|---|---|---|
| TC-SCP-01 | P1-supervisor-state-owner | T01 | `bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_multi_agent_context_budget.py -q` |
| TC-SCP-02 | P2-workflow-state-isolation | T03 | `bash scripts/pytest_targeted.sh tests/unit/test_todo_handoff_observation.py tests/unit/test_todo_nodes.py -q` |
| TC-SCP-03 | P3-research-subagent-dispatch | T05 | `rg -n "knowledge_search|search_tool|research" app/ai/workflow/multi_agent_graph.py app/ai/tools` |
| TC-SCP-04 | P1-supervisor-state-owner | T02 | `bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_multi_agent_context_budget.py -q` |
| TC-SCP-05 | P1-supervisor-state-owner | T02 | `bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_multi_agent_context_budget.py -q` |
| TC-SCP-06 | P1-supervisor-state-owner | T02 | `bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_multi_agent_context_budget.py -q` |
| TC-SCP-07 | P4-attachment-supervisor-planning | T08 | `rg -n "attachments|read_uploaded_file|attachment_manifest|planning_route|lightweight_probe" app/services/chat_service.py app/ai/workflow/multi_agent_graph.py docs/开发文档/架构设计/附件系统设计.md` |
| TC-SCP-08 | P2-workflow-state-isolation | T04 | `bash scripts/pytest_targeted.sh tests/unit/test_data_graph_pending_handoff_state.py tests/unit/test_data_graph_clarify_guard.py -q` |
| TC-SCP-09 | P5-architecture-doc-sync | T06 | `rg -n "workflow|subagent|tool|service|conversation_state" docs/开发文档/架构设计/AI模块设计.md docs/开发文档/架构设计/待办Agent设计.md` |
| TC-SCP-10 | P6-regression-contract-tests | T07 | `bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_todo_handoff_observation.py tests/unit/test_data_graph_pending_handoff_state.py -q` |
