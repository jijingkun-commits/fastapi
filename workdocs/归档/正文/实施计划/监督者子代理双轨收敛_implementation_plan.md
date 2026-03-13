# 监督者子代理双轨收敛实施方案

> 日期：2026-03-01
> 需求基线：`workdocs/归档/正文/需求/监督者子代理双轨收敛_requirements.md`
> 执行模式：`serial`

## 0. 输入来源清单

1. `workdocs/归档/正文/设计/` 中的历史讨论结论（B1 + A1）
2. `app/ai/workflow/multi_agent_graph.py`
3. `app/ai/prompts/agent_prompts.py`
4. `tests/unit/test_planner_*.py`
5. `tests/unit/test_multi_intent_queue_flow.py`

## 1. 架构影响与约束

1. 模块边界：仅改 Planner 路由、Coverage Gate 决策、Deliverable 抽取与 Prompt 规则。
2. 状态契约：新增 `coverage_partial_gap_allowed`、`handoff_execution_trace.supervisor_excerpt`。
3. 路由闭环：A1 策略下子任务缺口允许收口，但仅限“缺口目标全部属于专家目标”。
4. 端到端链路：保持 `final_composer` 作为唯一对外答复出口。
5. 可测试性：新增/更新单测覆盖默认策略、缺口路由、supervisor 摘要交付。

## 2. 功能机制包

| feature_id | 目标 | 代码锚点 | 验证命令 | 回滚锚点 |
|---|---|---|---|---|
| P1-01 | Planner 默认 single-call（json_object） | `app/ai/workflow/multi_agent_graph.py` | `PYTHONPATH=. pytest tests/unit/test_planner_strategy_router.py -q` | `PLANNER_DISABLE_TOOL_CALL=false` |
| P1-02 | json_object 失败即 heuristic（默认不走 text_parse） | `app/ai/workflow/multi_agent_graph.py` | `PYTHONPATH=. pytest tests/unit/test_planner_json_object_fallback.py tests/unit/test_planner_text_parse_fallback.py -q` | `PLANNER_DISABLE_TEXT_PARSE=false` |
| P1-03 | A1 缺口路由（仅专家目标缺失可收口） | `app/ai/workflow/multi_agent_graph.py` | `PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py -q` | `ENABLE_COVERAGE_GATE_ENFORCED=false` |
| P1-04 | 保留 supervisor 直答摘要并入交付物 | `app/ai/workflow/multi_agent_graph.py` `app/ai/prompts/agent_prompts.py` | `PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py -q` | 回退 prompt 复合问题规则 |

## 3. implementation_tasks

```yaml
implementation_tasks:
  - task_id: T-01
    feature_id: P1-01
    phase: Phase-1
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
      - tests/unit/test_planner_strategy_router.py
      - tests/unit/test_planner_tool_call_primary.py
    symbols:
      - _resolve_planner_structured_strategy
      - _infer_model_intent_plan_via_tool_call
    change_type: modify
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_planner_strategy_router.py tests/unit/test_planner_tool_call_primary.py -q
    rollback_point: tool_call default disable rollback

  - task_id: T-02
    feature_id: P1-02
    phase: Phase-1
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
      - tests/unit/test_planner_json_object_fallback.py
      - tests/unit/test_planner_text_parse_fallback.py
    symbols:
      - _infer_model_intent_plan_via_text_parse
      - _infer_model_intent_plan_by_strategy
    change_type: modify
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_planner_json_object_fallback.py tests/unit/test_planner_text_parse_fallback.py -q
    rollback_point: text_parse default disable rollback

  - task_id: T-03
    feature_id: P1-03
    phase: Phase-2
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
      - app/ai/state.py
      - tests/unit/test_multi_intent_queue_flow.py
    symbols:
      - _resolve_coverage_gate_route
      - _final_composer_node
      - MultiAgentState
    change_type: modify
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py -q
    rollback_point: coverage partial gap policy rollback

  - task_id: T-04
    feature_id: P1-04
    phase: Phase-2
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
      - app/ai/prompts/agent_prompts.py
      - tests/unit/test_multi_intent_queue_flow.py
    symbols:
      - _dispatch_values_mode_chunk
      - _build_delivery_artifacts
      - SUPERVISOR_PROMPT
    change_type: modify
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py -q
    rollback_point: supervisor excerpt deliverable rollback
```

## 4. task_to_pr_mapping

```yaml
task_to_pr_mapping:
  - task_id: T-01
    pr_id: PR-01
    pr_branch: codex/dualtrack-a1-pr01-planner
    pr_subject: Planner 默认 single-call 收敛
    pr_depends_on: []
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_planner_strategy_router.py tests/unit/test_planner_tool_call_primary.py -q
    rollback_point: tool_call default disable rollback

  - task_id: T-02
    pr_id: PR-01
    pr_branch: codex/dualtrack-a1-pr01-planner
    pr_subject: json_object 失败直 heuristic
    pr_depends_on: []
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_planner_json_object_fallback.py tests/unit/test_planner_text_parse_fallback.py -q
    rollback_point: text_parse default disable rollback

  - task_id: T-03
    pr_id: PR-02
    pr_branch: codex/dualtrack-a1-pr02-coverage
    pr_subject: A1 缺口路由与 composer 收敛
    pr_depends_on: [PR-01]
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py -q
    rollback_point: coverage partial gap policy rollback

  - task_id: T-04
    pr_id: PR-02
    pr_branch: codex/dualtrack-a1-pr02-coverage
    pr_subject: supervisor 直答摘要入交付物
    pr_depends_on: [PR-01]
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py -q
    rollback_point: supervisor excerpt deliverable rollback
```

## 5. planning_contract

```yaml
planning_contract:
  execution_mode: serial
  card_order: [C01, C02, G01]
  cards:
    - card_id: C01
      feature_ids: [P1-01, P1-02]
      depends_on: []
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - planner single-call enabled
      acceptance_checks:
        - PYTHONPATH=. pytest tests/unit/test_planner_strategy_router.py tests/unit/test_planner_tool_call_primary.py tests/unit/test_planner_json_object_fallback.py tests/unit/test_planner_text_parse_fallback.py -q
      evidence_entry: workdocs/归档/正文/实施计划/监督者子代理双轨收敛_implementation_plan.md

    - card_id: C02
      feature_ids: [P1-03, P1-04]
      depends_on: [C01]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - A1 partial-gap route enabled
        - supervisor excerpt captured
      acceptance_checks:
        - PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py -q
      evidence_entry: workdocs/归档/正文/实施计划/监督者子代理双轨收敛_implementation_plan.md

    - card_id: G01
      feature_ids: [G-1]
      depends_on: [C02]
      task_mode: inspection-card
      merge_required: false
      done_gate:
        - targeted tests all green
      acceptance_checks:
        - PYTHONPATH=. pytest tests/unit/test_planner_strategy_router.py tests/unit/test_planner_tool_call_primary.py tests/unit/test_planner_json_object_fallback.py tests/unit/test_planner_text_parse_fallback.py tests/unit/test_multi_intent_queue_flow.py -q
      evidence_entry: workdocs/归档/正文/实施计划/监督者子代理双轨收敛_implementation_plan.md
```

## 6. implementation_readiness

```yaml
implementation_readiness:
  implementation_ready: true
  blocked_by: []
  next_step: /jjk-imp
```

## 7. pr_ready_manifest

```yaml
pr_ready_manifest:
  - task_id: T-01
    pr_id: PR-01
    card_id: C01
    changed_files:
      - app/ai/workflow/multi_agent_graph.py
      - tests/unit/test_planner_strategy_router.py
      - tests/unit/test_planner_tool_call_primary.py
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_planner_strategy_router.py tests/unit/test_planner_tool_call_primary.py -q
    rollback_point: tool_call default disable rollback

  - task_id: T-02
    pr_id: PR-01
    card_id: C01
    changed_files:
      - app/ai/workflow/multi_agent_graph.py
      - tests/unit/test_planner_json_object_fallback.py
      - tests/unit/test_planner_text_parse_fallback.py
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_planner_json_object_fallback.py tests/unit/test_planner_text_parse_fallback.py -q
    rollback_point: text_parse default disable rollback

  - task_id: T-03
    pr_id: PR-02
    card_id: C02
    changed_files:
      - app/ai/workflow/multi_agent_graph.py
      - app/ai/state.py
      - tests/unit/test_multi_intent_queue_flow.py
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py -q
    rollback_point: coverage partial gap policy rollback

  - task_id: T-04
    pr_id: PR-02
    card_id: C02
    changed_files:
      - app/ai/workflow/multi_agent_graph.py
      - app/ai/prompts/agent_prompts.py
      - tests/unit/test_multi_intent_queue_flow.py
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py -q
    rollback_point: supervisor excerpt deliverable rollback
```
