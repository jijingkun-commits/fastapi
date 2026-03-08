# 意图优化需求文档（v2：运行态契约收敛）

> 更新时间：2026-03-08  
> 上游设计：`docs/plans/2026-03-06-intent-optimization-runtime-contract-v2-design.md`  
> 文档目标：定义 WHAT（需求合同、验收与追溯），供 `意图优化_implementation_plan.md` 承接

## 1. 业务目标与范围

### 1.1 用户故事

- 作为聊天用户，我希望询问记忆、偏好、能力等元信息时，系统不要误派发到数据专家。
- 作为产品/运营同学，我希望路由阻塞与误派发原因可观测、可追溯，便于复盘。
- 作为 AI 工作流研发，我希望在不破坏规划产能的前提下，完成运行态契约收敛，并让后续实现链可执行。

### 1.2 范围

- 运行阶段统一以 `decomposed_goals + handoff.target_agent` 驱动目标解析、路由门禁与分发。
- 规划阶段保留 planner 内部中间契约，但仅限 `decompose_goals` 内部使用，不再外溢为运行态输入。
- `decompose_goals` 输入只允许：当前 `user_query` + 最近 5 轮已落库、面向用户的 `chat_message` 对话视图。
- 结构化路由结果只允许写入 `additional_kwargs.router_result_v2`。
- 路由阻塞、覆盖缺口与运行异常统一回到 `supervisor`。

### 1.3 非范围

- 本轮不重写 planner 全链路。
- 本轮不新增专家节点或专家兜底策略。
- 本轮不改数据库 schema 或新增跨库依赖。
- 本轮不引入灰度开关或旧协议兼容层。

### 1.4 发布约束

- 不兼容旧字段；检测到历史结构化字段读写即 fail-fast。
- 回退只允许代码级回退（revert 变更集），不允许双轨灰度。
- 不得把观察窗口、TTL 成熟或自然时间流逝写入阻断门禁。

## 2. 机读需求合同（强制）

```yaml
requirements_contract:
  topic: "意图优化"
  status: "approved"
  design_source: docs/plans/2026-03-06-intent-optimization-runtime-contract-v2-design.md
  clarify_handoff_source: docs/plans/2026-03-06-intent-optimization-runtime-contract-v2-design.md#clarify_handoff_contract
  clarify_handoff_version: v2
  design_approved: true
  design_approval_evidence: "确认"
  design_freeze_summary:
    design_actionable: true
    missing_blocks: []
    risk_level: medium
    risk_counterexamples_count: 4
    handoff_contract_ready: true
    product_contract_ready: true
    implementation_seed_count: 7
    semantic_frozen: true
    contract_source_decided: true
    handoff_seed_alignment_ok: true
    parallel_dependency_ready: true
    replay_canonical_field_set: true
    blocking_issues: []
  owner: "ai-workflow"
  approver: "jijingkun"
  updated_at: "2026-03-08 03:15"
```

## 3. product_contract_matrix

```yaml
product_contract_matrix:
  - bg_id: BG-01
    target_users: [会话终端用户]
    core_scenario: 元信息/记忆请求不误派发
    business_goal_metric: memory_meta_to_data_expert_misroute_rate<=0.5%
    acceptance_gates: [A1, A2, A4]
    release_constraint: 不兼容旧字段
  - bg_id: BG-02
    target_users: [会话终端用户, AI工作流研发]
    core_scenario: 路由阻塞后 1 回合内 supervisor 收口
    business_goal_metric: route_recovery_ttr<=1_turn
    acceptance_gates: [A2, A3]
    release_constraint: 不允许专家兜底
  - bg_id: BG-03
    target_users: [AI工作流研发]
    core_scenario: 运行态门禁收敛后性能不退化
    business_goal_metric: router_guard_latency_p50<=30ms_and_p95<=150ms
    acceptance_gates: [A1, A4]
    release_constraint: 不引入双轨灰度
  - bg_id: BG-04
    target_users: [运营支持, AI工作流研发]
    core_scenario: planner 异常可回退且不中断主链路
    business_goal_metric: planner_model_failed_rate<=5%
    acceptance_gates: [A3, A4]
    release_constraint: 仅允许代码回退
```

## 4. fr_contract_matrix

```yaml
fr_contract_matrix:
  - fr_id: FR-01
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[0]
    user_value: 运行态目标解析单轨化，避免误读共享旧状态
    trigger: 进入路由与分发路径
    input_contract:
      required_fields: [decomposed_goals]
      source_of_truth: app/ai/workflow/multi_agent_graph.py::_resolve_active_goals
    output_contract:
      required_fields: [additional_kwargs.router_result_v2.route_decisions]
      consumer: app/ai/workflow/multi_agent_graph.py::_dispatch_values_mode_chunk
    failure_semantics: no_pending_goal -> supervisor_fallback
    observability_fields: [event, turn_id, goal_id, reason]
    rollback_anchor: revert:T01~T03
    linked_business_goals: [BG-01, BG-02]

  - fr_id: FR-02
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[1]
    user_value: handoff 契约字段缺失时稳定阻塞并回流 supervisor
    trigger: 生成或校验 handoff
    input_contract:
      required_fields: [target_agent, task_description]
      optional_fields: [allowed_agents, frame]
      source_of_truth: app/ai/workflow/multi_agent_graph.py::_apply_router_contract_guard
    output_contract:
      required_fields: [additional_kwargs.router_result_v2.router_contract_blocked]
      consumer: supervisor_fallback
    failure_semantics: invalid_target_agent|invalid_task_description|target_not_in_allowed_agents -> supervisor_fallback
    observability_fields: [event, turn_id, target_agent, reason]
    rollback_anchor: revert:T02
    linked_business_goals: [BG-01, BG-02]

  - fr_id: FR-03
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[2]
    user_value: 异常、阻塞与覆盖缺口统一由 supervisor 收口
    trigger: block/coverage_missing/runtime_error
    input_contract:
      required_fields: [blocked_handoffs, missing_goals, runtime_error]
      source_of_truth: app/ai/workflow/multi_agent_graph.py
    output_contract:
      required_fields: [supervisor_fallback_activated, final_answer_non_empty]
      consumer: final_composer
    failure_semantics: no_expert_fallback; coverage_missing -> supervisor_fallback
    observability_fields: [event, turn_id, reason, missing_goal_ids]
    rollback_anchor: revert:T03~T04
    linked_business_goals: [BG-02]

  - fr_id: FR-04
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[3]
    user_value: planner 输入最小化且对话视图来源明确
    trigger: decompose_goals 调用
    input_contract:
      required_fields: [user_query, messages]
      constraints:
        messages_window: recent_5_persisted_user_visible_chat_turns
        included_roles: [user, assistant]
        message_source: persisted_user_visible_chat_message_view
        assistant_message_scope: final_user_visible_reply_only
        current_user_query_counted_in_window: false
        allow_short_or_empty_window: true
      source_of_truth: app/ai/workflow/multi_agent_graph.py::decompose_goals
    output_contract:
      required_fields: [goals, source]
      consumer: app/ai/workflow/multi_agent_graph.py::_dispatch_values_mode_chunk
    failure_semantics: planner_model_failed -> heuristic_fallback; unresolved_reference -> clarify_needed
    observability_fields: [planner_mode, source, fallback_hit_rate]
    rollback_anchor: revert:planner-preservation-delta
    linked_business_goals: [BG-03, BG-04]

  - fr_id: FR-05
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[4]
    user_value: 结构化路由结果只存在唯一 canonical 字段
    trigger: 写入结构化路由结果
    input_contract:
      required_fields: [additional_kwargs.router_result_v2]
      source_of_truth: app/ai/workflow/multi_agent_graph.py
    output_contract:
      required_fields: [additional_kwargs.router_result_v2.version, additional_kwargs.router_result_v2.route_decisions]
      consumer: route_guard_and_coverage
    failure_semantics: legacy_field_detected|canonical_missing -> fail_fast_event
    observability_fields: [event, turn_id, field_version]
    rollback_anchor: revert:canonical-router-result-v2
    linked_business_goals: [BG-01, BG-03]

  - fr_id: FR-06
    source_seed_ref: derived.FR-06
    user_value: 文档与实施计划必须反映 canonical-only 与最小输入视图
    trigger: 进入实施与交付门禁
    input_contract:
      required_fields: [requirements_contract, implementation_tasks]
      source_of_truth: docs/内部参考/迭代需求/意图优化_implementation_plan.md
    output_contract:
      required_fields: [traceability_matrix, implementation_readiness]
      consumer: release_gate
    failure_semantics: docs_or_plan_drift -> block_release
    observability_fields: [task_id, acceptance_cmd_ref]
    rollback_anchor: revert:T07
    linked_business_goals: [BG-01, BG-04]
```

## 5. nfr_contract_matrix

```yaml
nfr_contract_matrix:
  - nfr_id: NFR-01
    metric: router_guard_latency
    threshold: P50<=30ms,P95<=150ms
    source: BG-03
  - nfr_id: NFR-02
    metric: planner_model_failed_rate
    threshold: <=5%
    source: BG-04
  - nfr_id: NFR-03
    metric: memory_meta_to_data_expert_misroute_rate
    threshold: <=0.5%
    source: BG-01
  - nfr_id: NFR-04
    metric: route_recovery_ttr
    threshold: <=1_turn
    source: BG-02
```

## 6. 验收场景

- 场景 1：用户问“我的偏好是什么”，不得派发到 `data_expert`。
- 场景 2：用户问“帮我查贷款余额”，允许派发合法数据专家。
- 场景 3：用户说“好的，再改一改”，仅依赖当前 `user_query` + 最近 5 轮已落库用户可见对话做意图消解。
- 场景 4：handoff 缺失 `target_agent` 时必须阻塞并回流 `supervisor`。
- 场景 5：历史不足 5 轮时允许短列表或空列表进入 `decompose_goals`。

## 7. traceability_matrix

```yaml
traceability_matrix:
  - design_item: D-01 runtime_goal_single_source
    fr_id: FR-01
    feature_id: P1-01
    task_id: T01
    tc_id: TC-IO-01
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_intent_layer_boundary.py -q
    evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md

  - design_item: D-02 handoff_contract_guard
    fr_id: FR-02
    feature_id: P1-02
    task_id: T02
    tc_id: TC-IO-02
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py -q
    evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md

  - design_item: D-03 dispatch_single_track
    fr_id: FR-01
    feature_id: P1-03
    task_id: T03
    tc_id: TC-IO-03
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py -q
    evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md

  - design_item: D-04 supervisor_prompt_priority
    fr_id: FR-03
    feature_id: P1-04
    task_id: T04
    tc_id: TC-IO-04
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_intent_layer_boundary.py -q
    evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md

  - design_item: D-05 planner_regression_and_input_view
    fr_id: FR-04
    feature_id: P1-05
    task_id: T05
    tc_id: TC-IO-05
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_intent_plan_model_primary.py -q
    evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md

  - design_item: D-06 canonical_runtime_contract_regression
    fr_id: FR-05
    feature_id: P1-06
    task_id: T06
    tc_id: TC-IO-06
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_router_ignores_intent_plan_runtime.py -q
    evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md

  - design_item: D-07 architecture_doc_sync
    fr_id: FR-06
    feature_id: P1-07
    task_id: T07
    tc_id: TC-IO-07
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && rg -n "decomposed_goals|router_result_v2|supervisor" docs/开发文档/架构设计/AI模块设计.md
    evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md
```
