# 监督者主会话状态归属与附件规划需求文档

> 更新时间：2026-03-10 10:04 +08:00
> 上游设计：`workdocs/归档/正文/设计/2026-03-09-supervisor-conversation-state-ownership-design.md`
> 文档目标：定义 WHAT（需求合同、验收门禁、追溯矩阵），供 `监督者主会话状态归属与附件规划_implementation_plan.md` 承接

## 1. 需求范围与目标

### 1.1 核心目标

- 冻结 `supervisor` 为主会话多轮上下文的唯一 owner。
- 将 `todo/data` 收敛为 workflow，把重资料研究能力收敛为 stateless subagent，把一次性文件/检索/视觉动作收敛为 tool。
- 建立“附件先规划、再路由”的统一口径，禁止按文件类型硬路由。
- 固定 `mixed` 计划的 owner 仍为 `supervisor`，避免子能力互相抢主导权。

### 1.2 范围

- 主链控制面：`app/services/chat_service.py`、`app/ai/workflow/multi_agent_graph.py`
- 状态模型：`app/ai/state.py`、`app/ai/protocol.py`
- 领域 workflow：`app/ai/workflow/todo_graph.py`、`app/ai/workflow/data_graph.py`
- 附件与工具：`app/ai/tools/file_tools.py`、`app/ai/tools/chatTools.py`、`app/ai/tools/ragflow_tool.py`
- 架构文档：`docs/开发文档/架构设计/AI模块设计.md`、`docs/开发文档/架构设计/附件系统设计.md`、`docs/开发文档/架构设计/待办Agent设计.md`

### 1.3 非范围

- 不在本轮重写整个多智能体链路。
- 不新增数据库 schema 或新的持久化 conversation_state 表。
- 不把所有工具包装成 agent。
- 不在本轮实现完整 research subagent，只冻结接入契约与调度边界。

## 2. requirements_contract（机读）

```yaml
requirements_contract:
  topic: "监督者主会话状态归属与附件规划"
  status: approved
  design_source: workdocs/归档/正文/设计/2026-03-09-supervisor-conversation-state-ownership-design.md
  clarify_handoff_source: workdocs/归档/正文/设计/2026-03-09-supervisor-conversation-state-ownership-design.md#clarify_handoff_contract
  clarify_handoff_version: v2
  design_approved: true
  design_approval_evidence: "好的"
  design_freeze_summary:
    design_actionable: true
    missing_blocks: []
    risk_level: medium
    risk_counterexamples_count: 4
    handoff_contract_ready: true
    product_contract_ready: true
    implementation_seed_count: 8
    semantic_frozen: true
    contract_source_decided: true
    handoff_seed_alignment_ok: true
    parallel_dependency_ready: true
    replay_canonical_field_set: true
  owner: "ai-workflow"
  approver: "jijingkun"
  updated_at: "2026-03-10 10:04 +08:00"
```

## 3. product_contract_matrix（PRD-Lite 承接）

```yaml
product_contract_matrix:
  target_users:
    - AI 主链与工作流维护者
    - 本仓库后续迭代研发
    - 对话终端用户（间接受益）
  core_scenarios:
    - 主会话连续多轮时由 supervisor 统一持有上下文与 pending user action
    - todo/data 进入澄清、确认、恢复流程时只维护局部状态
    - 用户上传任意附件后由 supervisor 结合 user_goal 与 probe 结果规划去向
    - 同一轮存在多个附件子目标时由 supervisor 维护 mixed execution_items[]
    - 根据会议纪要、需求文档等附件提炼待办时允许 todo_workflow 消费附件
  business_goal_metrics:
    - supervisor_conversation_owner_uniqueness=100%
    - expert_full_messages_default_usage=0
    - attachment_type_hard_route_count=0
    - mixed_plan_supervisor_owned=100%
    - replay_canonical_unique_field_count=1
  non_goals:
    - 一次性重写全链
    - 引入新的 conversation_state 持久化表
    - 将 research subagent 做成跨轮有状态专家
    - 为每一种文件类型单独新增 agent
  acceptance_gates:
    - SCP-AC-01
    - SCP-AC-02
    - SCP-AC-03
    - SCP-AC-04
    - SCP-AC-05
    - SCP-AC-06
    - SCP-AC-07
  release_constraints:
    - SUPERVISOR_CONVERSATION_STATE_V1 默认 true，回退为 false
    - EXPERT_INPUT_CONTRACT_FIRST 默认 true，回退为 false
    - ATTACHMENT_SUPERVISOR_PLANNING_V1 默认 true，回退为 false
    - RESEARCH_SUBAGENT_DISPATCH_V1 默认 true，回退为 false
```

## 4. fr_contract_matrix（字段级功能需求）

```yaml
fr_contract_matrix:
  - fr_id: FR-01
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[0]
    business_goal_refs:
      - supervisor_conversation_owner_uniqueness=100%
      - replay_canonical_unique_field_count=1
    user_value: 主会话多轮上下文只认一个 owner，后续能力演进不会再串味
    trigger: 任意用户输入进入主链
    input_contract:
      required_fields: [prompt, thread_id, current_state]
      source_of_truth: app/ai/state.py
    output_contract:
      required_fields: [conversation_state, active_goal_ids, pending_user_action]
      consumer: app/ai/workflow/multi_agent_graph.py
    failure_semantics: owner 不唯一时直接阻断进入执行链
    observability_fields: [turn_id, active_goal_ids, active_workflow, pending_user_action]
    rollback_anchor: SUPERVISOR_CONVERSATION_STATE_V1=false
    owner: ai-workflow

  - fr_id: FR-02
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[1]
    business_goal_refs:
      - expert_full_messages_default_usage=0
    user_value: todo/data 只关注本领域局部流程，不再被主会话全量消息污染
    trigger: supervisor 路由到 todo_workflow 或 data_workflow
    input_contract:
      required_fields: [expert_input_contract, workflow_local_state]
      source_of_truth: app/ai/workflow/multi_agent_graph.py
    output_contract:
      required_fields: [workflow_result, local_state_delta]
      consumer: app/ai/workflow/todo_graph.py + app/ai/workflow/data_graph.py
    failure_semantics: workflow 默认透传完整 messages 视为契约违规
    observability_fields: [target_workflow, contract_version, state_owner]
    rollback_anchor: EXPERT_INPUT_CONTRACT_FIRST=false
    owner: ai-workflow

  - fr_id: FR-03
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[2]
    business_goal_refs:
      - expert_full_messages_default_usage=0
    user_value: 重资料研究能力可隔离运行，不把研究 scratchpad 带回主会话
    trigger: 命中文档/网页/知识整合型任务
    input_contract:
      required_fields: [research_task_contract]
      source_of_truth: app/ai/workflow/multi_agent_graph.py
    output_contract:
      required_fields: [summary, evidence, insufficiency]
      consumer: app/services/chat_service.py
    failure_semantics: subagent 出现跨轮持久 scratchpad 即视为违规
    observability_fields: [research_task_id, source_count, citation_count]
    rollback_anchor: RESEARCH_SUBAGENT_DISPATCH_V1=false
    owner: ai-workflow

  - fr_id: FR-04
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[3]
    business_goal_refs:
      - expert_full_messages_default_usage=0
      - supervisor_conversation_owner_uniqueness=100%
    user_value: supervisor 交接专家时有稳定 contract，后续才能安全扩能力
    trigger: supervisor 调用 workflow/subagent
    input_contract:
      required_fields: [selected_facts, constraints, output_schema]
      source_of_truth: app/ai/workflow/multi_agent_graph.py
    output_contract:
      required_fields: [expert_input_contract]
      consumer: app/ai/workflow/todo_graph.py + app/ai/workflow/data_graph.py + future research_subagent
    failure_semantics: 默认透传完整多轮对话视为不合格
    observability_fields: [contract_id, source_fields, target_agent]
    rollback_anchor: EXPERT_INPUT_CONTRACT_FIRST=false
    owner: ai-workflow

  - fr_id: FR-05
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[4]
    business_goal_refs:
      - replay_canonical_unique_field_count=1
    user_value: 历史回放和在线状态看到的是同一份 conversation snapshot，不再分裂
    trigger: supervisor 写出用户可见 AIMessage
    input_contract:
      required_fields: [router_result_v2, conversation_snapshot]
      source_of_truth: app/ai/protocol.py
    output_contract:
      required_fields: [additional_kwargs.router_result_v2.conversation_state]
      consumer: app/services/chat_service.py
    failure_semantics: 出现第二套 canonical 字段即阻断
    observability_fields: [replay_source, canonical_field, snapshot_version]
    rollback_anchor: SUPERVISOR_CONVERSATION_STATE_V1=false
    owner: chat-runtime

  - fr_id: FR-06
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[5]
    business_goal_refs:
      - supervisor_conversation_owner_uniqueness=100%
    user_value: 无论中间调了谁，最后用户听到的都还是 supervisor 的统一答复
    trigger: workflow 或 subagent 返回结果
    input_contract:
      required_fields: [workflow_or_subagent_result]
      source_of_truth: app/ai/workflow/multi_agent_graph.py
    output_contract:
      required_fields: [supervisor_final_answer]
      consumer: app/services/chat_service.py
    failure_semantics: 专家节点直接兜底用户最终答复视为违规
    observability_fields: [final_answer_owner, coverage_pass, summarized_by]
    rollback_anchor: SUPERVISOR_CONVERSATION_STATE_V1=false
    owner: ai-workflow

  - fr_id: FR-07
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[6]
    business_goal_refs:
      - attachment_type_hard_route_count=0
      - mixed_plan_supervisor_owned=100%
    user_value: 用户上传什么文件都能按目标来规划，不会因为文件类型被系统提前锁死
    trigger: 用户上传任意附件并提出处理请求
    input_contract:
      required_fields: [user_goal, attachment_manifest, lightweight_probe, conversation_state]
      source_of_truth: app/services/chat_service.py
    output_contract:
      required_fields: [attachment_plan, route, selected_attachment_ids, attachment_roles, planner_reason]
      consumer: app/ai/workflow/multi_agent_graph.py
    failure_semantics: 按 MIME/后缀硬编码唯一路由，或把 prompt hint 当唯一契约时直接阻断
    observability_fields: [attachment_count, selected_attachment_ids, attachment_role, planning_route, requires_user_confirmation]
    rollback_anchor: ATTACHMENT_SUPERVISOR_PLANNING_V1=false
    owner: ai-workflow
```

## 5. nfr_contract_matrix（数值阈值）

```yaml
nfr_contract_matrix:
  - nfr_id: NFR-01
    requirement: 主会话 replay canonical 字段数 = 1
    owner: chat-runtime
  - nfr_id: NFR-02
    requirement: workflow/subagent 默认透传完整 messages 次数 = 0
    owner: ai-workflow
  - nfr_id: NFR-03
    requirement: 附件类型硬路由命中次数 = 0
    owner: ai-workflow
  - nfr_id: NFR-04
    requirement: mixed 计划中 execution_items[] 的 owner 偏离次数 = 0
    owner: ai-workflow
  - nfr_id: NFR-05
    requirement: 规划门禁与 targeted contract 检查总耗时 <= 10 分钟
    owner: ci-governance
```

## 6. traceability_matrix（设计 -> FR -> Feature -> Task -> TC）

```yaml
traceability_matrix:
  - design_item: D-01
    fr_id: FR-01
    feature_id: P1-supervisor-state-owner
    task_id: T01
    tc_id: TC-SCP-01
    acceptance_cmd_ref: bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_multi_agent_context_budget.py -q
    evidence_entry: workdocs/归档/正文/实施计划/监督者主会话状态归属与附件规划_implementation_plan.md
  - design_item: D-02
    fr_id: FR-02
    feature_id: P2-workflow-state-isolation
    task_id: T03
    tc_id: TC-SCP-02
    acceptance_cmd_ref: bash scripts/pytest_targeted.sh tests/unit/test_todo_handoff_observation.py tests/unit/test_todo_nodes.py -q
    evidence_entry: workdocs/归档/正文/实施计划/监督者主会话状态归属与附件规划_implementation_plan.md
  - design_item: D-03
    fr_id: FR-03
    feature_id: P3-research-subagent-dispatch
    task_id: T05
    tc_id: TC-SCP-03
    acceptance_cmd_ref: rg -n "knowledge_search|search_tool|research" app/ai/workflow/multi_agent_graph.py app/ai/tools
    evidence_entry: workdocs/归档/正文/实施计划/监督者主会话状态归属与附件规划_implementation_plan.md
  - design_item: D-04
    fr_id: FR-04
    feature_id: P1-supervisor-state-owner
    task_id: T02
    tc_id: TC-SCP-04
    acceptance_cmd_ref: bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_multi_agent_context_budget.py -q
    evidence_entry: workdocs/归档/正文/实施计划/监督者主会话状态归属与附件规划_implementation_plan.md
  - design_item: D-05
    fr_id: FR-05
    feature_id: P1-supervisor-state-owner
    task_id: T02
    tc_id: TC-SCP-05
    acceptance_cmd_ref: bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_multi_agent_context_budget.py -q
    evidence_entry: workdocs/归档/正文/实施计划/监督者主会话状态归属与附件规划_implementation_plan.md
  - design_item: D-06
    fr_id: FR-06
    feature_id: P1-supervisor-state-owner
    task_id: T02
    tc_id: TC-SCP-06
    acceptance_cmd_ref: bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_multi_agent_context_budget.py -q
    evidence_entry: workdocs/归档/正文/实施计划/监督者主会话状态归属与附件规划_implementation_plan.md
  - design_item: D-07
    fr_id: FR-07
    feature_id: P4-attachment-supervisor-planning
    task_id: T08
    tc_id: TC-SCP-07
    acceptance_cmd_ref: rg -n "attachments|read_uploaded_file|attachment_manifest|planning_route|lightweight_probe" app/services/chat_service.py app/ai/workflow/multi_agent_graph.py docs/开发文档/架构设计/附件系统设计.md
    evidence_entry: workdocs/归档/正文/实施计划/监督者主会话状态归属与附件规划_implementation_plan.md
  - design_item: D-08
    fr_id: FR-02
    feature_id: P2-workflow-state-isolation
    task_id: T04
    tc_id: TC-SCP-08
    acceptance_cmd_ref: bash scripts/pytest_targeted.sh tests/unit/test_data_graph_pending_handoff_state.py tests/unit/test_data_graph_clarify_guard.py -q
    evidence_entry: workdocs/归档/正文/实施计划/监督者主会话状态归属与附件规划_implementation_plan.md
  - design_item: D-09
    fr_id: FR-04
    feature_id: P5-architecture-doc-sync
    task_id: T06
    tc_id: TC-SCP-09
    acceptance_cmd_ref: rg -n "workflow|subagent|tool|service|conversation_state" docs/开发文档/架构设计/AI模块设计.md docs/开发文档/架构设计/待办Agent设计.md
    evidence_entry: workdocs/归档/正文/实施计划/监督者主会话状态归属与附件规划_implementation_plan.md
  - design_item: D-10
    fr_id: FR-04
    feature_id: P6-regression-contract-tests
    task_id: T07
    tc_id: TC-SCP-10
    acceptance_cmd_ref: bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_todo_handoff_observation.py tests/unit/test_data_graph_pending_handoff_state.py -q
    evidence_entry: workdocs/归档/正文/实施计划/监督者主会话状态归属与附件规划_implementation_plan.md
```
