# 意图优化实施计划（v2：运行态契约收敛）

> 更新时间：2026-03-08  
> 上游输入：`docs/plans/2026-03-06-intent-optimization-runtime-contract-v2-design.md`、`docs/内部参考/迭代需求/意图优化_requirements.md`  
> 当前模式：`core`（plan-only，不自动进入执行链）

## 1. 架构影响与约束

### 1.1 模块边界

- `multi_agent_graph`：唯一编排层，负责目标解析、路由门禁、分发与 fallback 收口。
- `agent_prompts`：仅负责 supervisor 语义提示，不承担运行态门禁责任。
- `delivery_contract_validators`：仅负责交付字段校验，不承担路由纠偏。
- `docs`：必须同步 canonical-only 与最小输入视图，避免实现与设计漂移。

### 1.2 依赖方向

- `user_query + persisted_user_visible_chat_message_view -> decompose_goals -> decomposed_goals -> router_guard -> dispatch -> supervisor_fallback/final`。
- 不允许从执行层反向依赖 planner 内部中间对象。
- 不允许从运行态读取历史结构化旧字段。

### 1.3 状态契约

- 运行态唯一目标源：`decomposed_goals`。
- 运行态唯一结构化结果：`additional_kwargs.router_result_v2`。
- 规划输入最小集：当前 `user_query` + 最近 5 轮已落库、面向用户的 `chat_message`。
- 当前未落库用户输入只作为独立 `user_query`，不计入 5 轮窗口。

### 1.4 测试约束

- 不足 5 轮时必须允许短列表/空列表进入规划。
- `tool/system` 与内部结构化产物不得进入 `decompose_goals` 输入视图。
- 任意运行态合同异常必须验证 `supervisor_fallback` 收口。
- 显式 TC 覆盖补齐：`TC-IO-01`、`TC-IO-02`、`TC-IO-03`、`TC-IO-04`、`TC-IO-05`、`TC-IO-06`、`TC-IO-07`。

## 2. 功能机制包（Feature Packet）

| feature_id | 目标 | 文件锚点 | 核心符号 | 风险点 | 验收主命令 |
|---|---|---|---|---|---|
| P1-01 | 运行态目标解析单轨化 | `app/ai/workflow/multi_agent_graph.py` | `_resolve_active_goals` | 误读共享旧状态导致目标漂移 | `PYTHONPATH=. pytest tests/unit/test_intent_layer_boundary.py -q` |
| P1-02 | handoff 合同强校验 | `app/ai/workflow/multi_agent_graph.py` | `_apply_router_contract_guard` | 阻塞条件不稳定 | `PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py -q` |
| P1-03 | values 分发只认 canonical 运行态输入 | `app/ai/workflow/multi_agent_graph.py` | `_dispatch_values_mode_chunk` | 分发链漏掉 supervisor 收口 | `PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py -q` |
| P1-04 | supervisor 判定优先级与元信息反例校准 | `app/ai/prompts/agent_prompts.py` | `SUPERVISOR_PROMPT` | 元信息仍误入数据查询 | `PYTHONPATH=. pytest tests/unit/test_intent_layer_boundary.py -q` |
| P1-05 | planner 回归与最小输入视图验证 | `tests/unit/`,`tests/integration/` | `planner_regression_tests` | 最小输入视图影响规划稳定性 | `PYTHONPATH=. pytest tests/unit/test_intent_plan_model_primary.py -q` |
| P1-06 | canonical-only 回归 | `tests/unit/` | `runtime_contract_regression` | 仍残留旧结构化字段 | `PYTHONPATH=. pytest tests/unit/test_router_ignores_intent_plan_runtime.py -q` |
| P1-07 | 架构文档同步 | `docs/开发文档/架构设计/AI模块设计.md` | `intent_routing_sections` | 文档与实现漂移 | `rg -n "decomposed_goals|router_result_v2|supervisor" docs/开发文档/架构设计/AI模块设计.md` |

## 3. implementation_tasks

```yaml
implementation_tasks:
  - task_id: T01
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[0]
    feature_id: P1-01
    phase: Phase-1
    change_type: refactor
    owner: ai-workflow
    pr_id: PR-01
    risk_point: 目标解析仍残留共享旧状态读取
    rollback_point: revert:T01~T03
    depends_on_tasks: [ROOT]
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
    symbols:
      - _resolve_active_goals
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_intent_layer_boundary.py -q

  - task_id: T02
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[1]
    feature_id: P1-02
    phase: Phase-1
    change_type: refactor
    owner: ai-workflow
    pr_id: PR-02
    risk_point: handoff 校验分支不完整导致 supervisor 收口缺失
    rollback_point: revert:T02
    depends_on_tasks: [T01]
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
    symbols:
      - _apply_router_contract_guard
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py -q

  - task_id: T03
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[2]
    feature_id: P1-03
    phase: Phase-1
    change_type: refactor
    owner: ai-workflow
    pr_id: PR-03
    risk_point: values 分发链仍读取非 canonical 运行态结构
    rollback_point: revert:T01~T03
    depends_on_tasks: [T02]
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
    symbols:
      - _dispatch_values_mode_chunk
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py -q

  - task_id: T04
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[3]
    feature_id: P1-04
    phase: Phase-2
    change_type: modify
    owner: ai-workflow
    pr_id: PR-04
    risk_point: prompt 口径与运行态收敛规则不一致
    rollback_point: revert:T03~T04
    depends_on_tasks: [T03]
    file_paths:
      - app/ai/prompts/agent_prompts.py
    symbols:
      - SUPERVISOR_PROMPT
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_intent_layer_boundary.py -q

  - task_id: T05
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[4]
    feature_id: P1-05
    phase: Phase-2
    change_type: modify
    owner: ai-workflow
    pr_id: PR-05
    risk_point: planner 最小输入视图导致规划稳定性回归
    rollback_point: revert:planner-preservation-delta
    depends_on_tasks: [T03]
    file_paths:
      - tests/unit/test_intent_plan_model_primary.py
      - tests/integration/test_intent_shadow_metrics.py
    symbols:
      - planner_regression_tests
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_intent_plan_model_primary.py -q
      - PYTHONPATH=. pytest tests/integration/test_intent_shadow_metrics.py -q

  - task_id: T06
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[5]
    feature_id: P1-06
    phase: Phase-2
    change_type: add
    owner: ai-workflow
    pr_id: PR-06
    risk_point: canonical-only 规则未被回归用例锁死
    rollback_point: revert:canonical-router-result-v2
    depends_on_tasks: [T03]
    file_paths:
      - tests/unit/test_router_ignores_intent_plan_runtime.py
    symbols:
      - runtime_contract_regression
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_router_ignores_intent_plan_runtime.py -q

  - task_id: T07
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[6]
    feature_id: P1-07
    phase: Phase-3
    change_type: modify
    owner: ai-workflow
    pr_id: PR-07
    risk_point: 架构文档未同步 canonical-only 与最小输入视图
    rollback_point: revert:T07
    depends_on_tasks: [T01, T02, T03, T04, T05, T06]
    file_paths:
      - docs/开发文档/架构设计/AI模块设计.md
    symbols:
      - intent_routing_sections
    acceptance_cmds:
      - rg -n "decomposed_goals|router_result_v2|supervisor" docs/开发文档/架构设计/AI模块设计.md
```

## 4. task_to_pr_mapping

```yaml
task_to_pr_mapping:
  - task_id: T01
    pr_id: PR-01
    pr_branch: codex/intent-runtime-v2-pr-01
    pr_subject: "运行态目标源单轨化"
    pr_depends_on: []
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_intent_layer_boundary.py -q
    rollback_point: revert:T01~T03

  - task_id: T02
    pr_id: PR-02
    pr_branch: codex/intent-runtime-v2-pr-02
    pr_subject: "handoff 合同强校验与 supervisor 收口"
    pr_depends_on: [PR-01]
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py -q
    rollback_point: revert:T02

  - task_id: T03
    pr_id: PR-03
    pr_branch: codex/intent-runtime-v2-pr-03
    pr_subject: "values 分发只认 canonical 运行态输入"
    pr_depends_on: [PR-02]
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py -q
    rollback_point: revert:T01~T03

  - task_id: T04
    pr_id: PR-04
    pr_branch: codex/intent-runtime-v2-pr-04
    pr_subject: "supervisor 语义优先级校准"
    pr_depends_on: [PR-03]
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_intent_layer_boundary.py -q
    rollback_point: revert:T03~T04

  - task_id: T05
    pr_id: PR-05
    pr_branch: codex/intent-runtime-v2-pr-05
    pr_subject: "planner 回归与最小输入视图验证"
    pr_depends_on: [PR-03]
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_intent_plan_model_primary.py -q
      - PYTHONPATH=. pytest tests/integration/test_intent_shadow_metrics.py -q
    rollback_point: revert:planner-preservation-delta

  - task_id: T06
    pr_id: PR-06
    pr_branch: codex/intent-runtime-v2-pr-06
    pr_subject: "canonical-only 回归锁定"
    pr_depends_on: [PR-03]
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_router_ignores_intent_plan_runtime.py -q
    rollback_point: revert:canonical-router-result-v2

  - task_id: T07
    pr_id: PR-07
    pr_branch: codex/intent-runtime-v2-pr-07
    pr_subject: "架构文档同步 canonical-only 口径"
    pr_depends_on: [PR-01, PR-02, PR-03, PR-04, PR-05, PR-06]
    acceptance_cmds:
      - rg -n "decomposed_goals|router_result_v2|supervisor" docs/开发文档/架构设计/AI模块设计.md
    rollback_point: revert:T07
```

## 5. planning_contract

```yaml
planning_contract:
  execution_mode: serial
  card_order: [C01, C02, C03, C04, C05, C06, C07]
  strict_single_active_card: true
  cards:
    - card_id: C01
      feature_ids: [P1-01]
      depends_on: []
      done_gate: [T01 done]
      acceptance_checks:
        - PYTHONPATH=. pytest tests/unit/test_intent_layer_boundary.py -q
    - card_id: C02
      feature_ids: [P1-02]
      depends_on: [C01]
      done_gate: [T02 done]
      acceptance_checks:
        - PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py -q
    - card_id: C03
      feature_ids: [P1-03]
      depends_on: [C02]
      done_gate: [T03 done]
      acceptance_checks:
        - PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py -q
    - card_id: C04
      feature_ids: [P1-04]
      depends_on: [C03]
      done_gate: [T04 done]
      acceptance_checks:
        - PYTHONPATH=. pytest tests/unit/test_intent_layer_boundary.py -q
    - card_id: C05
      feature_ids: [P1-05]
      depends_on: [C03]
      done_gate: [T05 done]
      acceptance_checks:
        - PYTHONPATH=. pytest tests/unit/test_intent_plan_model_primary.py -q
        - PYTHONPATH=. pytest tests/integration/test_intent_shadow_metrics.py -q
    - card_id: C06
      feature_ids: [P1-06]
      depends_on: [C03]
      done_gate: [T06 done]
      acceptance_checks:
        - PYTHONPATH=. pytest tests/unit/test_router_ignores_intent_plan_runtime.py -q
    - card_id: C07
      feature_ids: [P1-07]
      depends_on: [C01, C02, C03, C04, C05, C06]
      done_gate: [T07 done]
      acceptance_checks:
        - rg -n "decomposed_goals|router_result_v2|supervisor" docs/开发文档/架构设计/AI模块设计.md
```

## 6. execution_contract

```yaml
execution_contract:
  preferred_mode: core
  execution_contract_ready: true
  delivery_mode: staged
  execution_unit: per_task
  commit_policy: per_pr
  stop_boundary: per_pr
  temporal_gate_forbidden: true
  context_verified: true
  design_source: docs/plans/2026-03-06-intent-optimization-runtime-contract-v2-design.md
  requirements_source: docs/内部参考/迭代需求/意图优化_requirements.md
```

## 7. implementation_readiness

```yaml
implementation_readiness:
  implementation_ready: true
  execution_contract_ready: true
  requirements_ready: true
  traceability_ready: true
  blocking_issue_count: 0
  readiness_note: approved_design_and_hydrated_tasks
```
