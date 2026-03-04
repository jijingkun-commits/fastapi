# 监督者移除Planner重构实施方案

> 日期：2026-03-03  
> 需求基线：`docs/内部参考/迭代需求/监督者移除Planner重构_requirements.md`  
> 设计输入：`docs/plans/2026-03-02-supervisor-refactor-remove-planner-design.md`  
> 模式：`core (plan-only)`

## 0. 输入来源清单

1. `docs/plans/2026-03-02-supervisor-refactor-remove-planner-design.md`
2. `docs/plans/2026-03-02-supervisor-refactor-remove-planner.md`
3. `docs/内部参考/迭代需求/监督者移除Planner重构_requirements.md`
4. `app/ai/workflow/multi_agent_graph.py`
5. `app/ai/state.py`
6. `app/ai/contracts/delivery_contracts.py`
7. `app/ai/contracts/delivery_contract_validators.py`
8. `app/ai/events.py`
9. `app/services/chat_service.py`
10. `web/src/types/message.ts`
11. `tests/unit/*planner*`, `tests/unit/*intent*`, `tests/api/test_chat_sse_intent_goal_status.py`, `tests/integration/test_intent_shadow_metrics.py`

## 1. 架构影响与约束

1. **模块边界**
   - 决策与拆解能力统一收敛到 `supervisor` 层。
   - `todo_expert` / `data_expert` 仅消费委派，不承载上游目标拆解职责。

2. **状态契约**
   - 目标主状态从 `intent_plan` 迁移到 `decomposed_goals`。
   - 兼容迁移期通过 `_resolve_active_goals(state)` 统一读取，避免读路径散落。

3. **路由闭环**
   - `supervisor -> router_guard -> evaluate -> coverage_gate -> final_composer` 全链一致使用活动目标集。
   - 禁止出现“router 用 A 状态、coverage 用 B 状态”的双口径。

4. **端到端链路**
   - `current_todo_id` 必须在 `preprocess` 注入后被 Supervisor 直接消费。
   - 选中待办 + 模糊更新表达优先走待办 update 委派路径。

5. **可测试性**
   - 单测覆盖：目标拆解、路由门禁、coverage 计算、SSE 兼容开关。
   - API 覆盖：SSE 事件契约（兼容态与最终态）。
   - 回归覆盖：复合请求与选中待办关键场景。

## 2. 功能机制包（Feature Packet）

| feature_id | 目标与边界 | 触发与状态流转 | 代码锚点 | 关键契约字段 | 回滚锚点 | 验证命令 | 来源证据 |
|---|---|---|---|---|---|---|---|
| P1-01 | 移除 `planner` 节点，仅保留 `preprocess -> supervisor`；不改 expert 子图 | 应用启动时构图生效；运行时不再进入 planner 节点 | `app/ai/workflow/multi_agent_graph.py` | `workflow edges` | 回退到保留 planner 的旧拓扑分支 | `cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py -q` | 设计文档 2.1/3.1 |
| P1-02 | 目标主状态迁移到 `decomposed_goals`，兼容期提供统一读取入口 | preprocess/supervisor 写入 goals；router/coverage/final 统一读取 | `app/ai/state.py`, `app/ai/workflow/multi_agent_graph.py` | `decomposed_goals`, `_resolve_active_goals` | 保留兼容读回退（只读）直到清理完成 | `cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py tests/unit/test_multi_intent_coverage_reconcile.py -q` | 设计文档 3.2/3.4 |
| P1-03 | Supervisor 按需调用 `decompose_goals`；简单请求不拆解 | 复合请求 -> 调用拆解 -> 目标写入状态；拆解失败 -> `general.reply` | `app/ai/workflow/multi_agent_graph.py`, `app/ai/prompts/agent_prompts.py` | `goals[*].kind/order/allowed_agents` | 关闭拆解路径并降级单目标 | `cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py -q` | 设计文档 3.3 |
| P1-04 | Router/Coverage/Final 全链迁移到 active goals；不允许漏项收口 | handoff -> guarded dispatch -> coverage gate -> final answer | `app/ai/workflow/multi_agent_graph.py` | `goal_count_initial`, `missing_goals`, `goal_results` | 关闭强门禁开关回到保守策略 | `cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py tests/unit/test_multi_intent_coverage_reconcile.py -q` | 设计文档 3.4 |
| P1-05 | `plan_ready` 事件双阶段迁移：兼容期开关保留，最终移除 | compat=true: 继续发；compat=false: 不发 | `app/ai/events.py`, `app/services/chat_service.py`, `web/src/types/message.ts` | `ENABLE_PLAN_READY_COMPAT` | 设置 compat=true 并回滚分支 | `cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/api/test_chat_sse_intent_goal_status.py -q` | 设计文档 3.5 |
| P1-06 | 测试体系重构：删除 planner 强耦合旧测，补齐新合同测试 | unit->integration->api 分层收敛 | `tests/unit/**`, `tests/integration/**`, `tests/api/**` | 测试矩阵与断言口径 | 回退到迁移前测试清单 | `cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit tests/integration tests/api -k "intent or planner or coverage or sse" -q` | 并行调研输出（team） |

### 每个 feature 的最小代码样例（伪代码）

```python
# P1-02: 统一目标读取入口

def _resolve_active_goals(state: MultiAgentState) -> list[dict]:
    goals = state.get("decomposed_goals") or []
    if goals:
        return _normalize_goals(goals)
    # 兼容迁移期：仅用于读回退，最终删除
    legacy_plan = state.get("intent_plan") or {}
    return _normalize_goals(legacy_plan.get("goals") or _default_general_goal())
```

```python
# P1-05: plan_ready 兼容开关

def emit_plan_ready_compat(writer, plan_payload):
    if not is_feature_enabled("ENABLE_PLAN_READY_COMPAT", True):
        return
    emit_plan_ready(writer, plan_payload, node="supervisor")
```

## 3. test_strategy（推荐）

```yaml
test_strategy:
  - feature_id: P1-01
    test_cases:
      - TC-SRP-01: 简单问候不进入planner
      - TC-SRP-02: 单目标委派链路正常
    test_first: true
  - feature_id: P1-02
    test_cases:
      - TC-SRP-03: active_goals 统一读取顺序正确
      - TC-SRP-08: coverage 缺口识别一致
    test_first: true
  - feature_id: P1-05
    test_cases:
      - TC-SRP-06: compat=true 时仍有plan_ready
      - TC-SRP-07: compat=false 时无plan_ready
    test_first: true
```

## 4. implementation_tasks（工单级 HOW）

```yaml
implementation_tasks:
  - task_id: T-01
    feature_id: P1-01
    pr_id: PR-01
    phase: Phase-1
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
    symbols:
      - create_multi_agent_graph
      - workflow.add_edge
    change_type: modify
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py -q
    rollback_point: 恢复 planner 节点与边定义

  - task_id: T-02
    feature_id: P1-02
    pr_id: PR-01
    phase: Phase-1
    file_paths:
      - app/ai/state.py
      - app/ai/workflow/multi_agent_graph.py
    symbols:
      - MultiAgentState
      - _resolve_active_goals
    change_type: modify
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py -q
    rollback_point: 仅保留只读兼容层，不删除旧字段

  - task_id: T-03
    feature_id: P1-03
    pr_id: PR-02
    phase: Phase-2
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
      - app/ai/prompts/agent_prompts.py
    symbols:
      - decompose_goals
      - SUPERVISOR_PROMPT
    change_type: add
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py -q
    rollback_point: 关闭 decompose_goals 调用并降级单目标

  - task_id: T-04
    feature_id: P1-04
    pr_id: PR-02
    phase: Phase-2
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
    symbols:
      - _build_router_dispatch_goal_queue
      - _apply_router_contract_guard
      - _dispatch_values_mode_chunk
    change_type: modify
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py tests/unit/test_multi_agent_streaming_helpers.py -q
    rollback_point: router 读取回退到兼容入口

  - task_id: T-05
    feature_id: P1-04
    pr_id: PR-03
    phase: Phase-3
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
    symbols:
      - _compute_coverage_report
      - _render_final_answer
      - _render_coverage_blocked_message
    change_type: modify
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_intent_coverage_reconcile.py tests/unit/test_multi_intent_queue_flow.py -q
    rollback_point: coverage_gate 强门禁降级

  - task_id: T-06
    feature_id: P1-02
    pr_id: PR-03
    phase: Phase-3
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
      - app/ai/contracts/delivery_contracts.py
      - app/ai/contracts/delivery_contract_validators.py
    symbols:
      - validate_intent_plan_contract
      - IntentPlanContract
      - build_contract_validation_meta
    change_type: modify
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_delivery_contract_validators.py -q
    rollback_point: 合同层保留旧入口兼容

  - task_id: T-07
    feature_id: P1-05
    pr_id: PR-04
    phase: Phase-4
    file_paths:
      - app/ai/events.py
      - app/services/chat_service.py
    symbols:
      - emit_plan_ready
      - _normalize_plan_ready_event_payload
      - ChatService.stream
      - sse_resume_stream
    change_type: modify
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/api/test_chat_sse_intent_goal_status.py -q
    rollback_point: ENABLE_PLAN_READY_COMPAT=true

  - task_id: T-08
    feature_id: P1-05
    pr_id: PR-04
    phase: Phase-4
    file_paths:
      - web/src/types/message.ts
      - web/src/lib/backend.ts
    symbols:
      - StreamEventType
      - dispatchSSEEvent
    change_type: modify
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && pnpm -C web test -- --runInBand
    rollback_point: 恢复 plan_ready 类型定义兼容

  - task_id: T-09
    feature_id: P1-06
    pr_id: PR-05
    phase: Phase-5
    file_paths:
      - tests/unit/test_planner_reason_codes.py
      - tests/unit/test_intent_plan_model_primary.py
      - tests/unit/test_multi_intent_queue_flow.py
      - tests/integration/test_intent_shadow_metrics.py
      - tests/api/test_chat_sse_intent_goal_status.py
    symbols:
      - test_*
    change_type: modify
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit tests/integration tests/api -k "planner or intent or coverage or sse" -q
    rollback_point: 回退到迁移前测试集合

  - task_id: T-10
    feature_id: P1-01
    pr_id: PR-05
    phase: Phase-5
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
      - app/ai/state.py
    symbols:
      - _planner_node
      - intent_plan
    change_type: delete
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && rg -n "intent_plan|_planner_node|emit_plan_ready" app/ai app/services web/src tests
    rollback_point: 恢复兼容分支并撤销删除提交

  - task_id: T-11
    feature_id: P1-06
    pr_id: PR-05
    phase: Phase-5
    file_paths:
      - docs/SUMMARY.md
      - docs/内部参考/迭代需求/监督者移除Planner重构_requirements.md
      - docs/内部参考/迭代需求/监督者移除Planner重构_implementation_plan.md
    symbols:
      - 迭代需求索引
      - planning_contract
    change_type: modify
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/docs_guard.py --strict
    rollback_point: 回退文档索引与计划文档版本
```

## 5. planning_contract（供 `$jjk-vkplan` / `$jjk-imp` 消费）

```yaml
planning_contract:
  execution_mode: serial
  card_order: [C01, C02, C03, C04, G01]
  strict_single_active_card: true
  auto_done_policy:
    implementation-card: hard_gate
    inspection-card: policy_gate
  gate_contract:
    mode: as_cards
    gate_ids: [G01]
    depends_on:
      G01: [C04]

  cards:
    - card_id: C01
      wave: P1
      feature_ids: [P1-01, P1-02]
      depends_on: []
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - 拓扑切换完成且active_goals入口可用
      acceptance_checks:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_multi_intent_queue_flow.py -q
      evidence_entry: docs/内部参考/迭代需求/监督者移除Planner重构_implementation_plan.md

    - card_id: C02
      wave: P1
      feature_ids: [P1-03, P1-04]
      depends_on: [C01]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - decompose_goals 生效
        - router/coverage 使用统一目标口径
      acceptance_checks:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py tests/unit/test_multi_intent_coverage_reconcile.py -q
      evidence_entry: docs/内部参考/迭代需求/监督者移除Planner重构_implementation_plan.md

    - card_id: C03
      wave: P2
      feature_ids: [P1-02]
      depends_on: [C02]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - 合同校验入口完成迁移并可兼容
      acceptance_checks:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_delivery_contract_validators.py -q
      evidence_entry: docs/内部参考/迭代需求/监督者移除Planner重构_implementation_plan.md

    - card_id: C04
      wave: P2
      feature_ids: [P1-05, P1-06]
      depends_on: [C03]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - plan_ready 兼容开关可控
        - 分层测试口径更新完成
      acceptance_checks:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/api/test_chat_sse_intent_goal_status.py -q
      evidence_entry: docs/内部参考/迭代需求/监督者移除Planner重构_implementation_plan.md

    - card_id: G01
      wave: Gate
      feature_ids: [G-1]
      depends_on: [C04]
      task_mode: inspection-card
      merge_required: false
      done_gate:
        - 关键链路测试通过且文档门禁通过
      acceptance_checks:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit tests/integration tests/api -k "intent or planner or coverage or sse" -q
        - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/docs_guard.py --strict
      evidence_entry: docs/内部参考/迭代需求/监督者移除Planner重构_implementation_plan.md

  task_to_pr_mapping:
    - task_id: T-01
      pr_id: PR-01
      pr_branch: codex/supervisor-remove-planner-pr01
      pr_subject: 图拓扑与状态入口迁移（第一阶段）
      pr_depends_on: []
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_multi_intent_queue_flow.py -q
      rollback_point: 恢复 planner 节点接线

    - task_id: T-02
      pr_id: PR-01
      pr_branch: codex/supervisor-remove-planner-pr01
      pr_subject: 图拓扑与状态入口迁移（第一阶段）
      pr_depends_on: []
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py -q
      rollback_point: 保留 intent_plan 只读回退

    - task_id: T-03
      pr_id: PR-02
      pr_branch: codex/supervisor-remove-planner-pr02
      pr_subject: Supervisor 拆解与Router链路迁移
      pr_depends_on: [PR-01]
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py -q
      rollback_point: 关闭 decompose_goals 路径

    - task_id: T-04
      pr_id: PR-02
      pr_branch: codex/supervisor-remove-planner-pr02
      pr_subject: Supervisor 拆解与Router链路迁移
      pr_depends_on: [PR-01]
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py tests/unit/test_multi_agent_streaming_helpers.py -q
      rollback_point: router 回退兼容入口

    - task_id: T-05
      pr_id: PR-03
      pr_branch: codex/supervisor-remove-planner-pr03
      pr_subject: Coverage/Final/Contracts 合同迁移
      pr_depends_on: [PR-02]
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_intent_coverage_reconcile.py tests/unit/test_multi_intent_queue_flow.py -q
      rollback_point: 降级 coverage 门禁策略

    - task_id: T-06
      pr_id: PR-03
      pr_branch: codex/supervisor-remove-planner-pr03
      pr_subject: Coverage/Final/Contracts 合同迁移
      pr_depends_on: [PR-02]
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_delivery_contract_validators.py -q
      rollback_point: 保留旧合同校验入口

    - task_id: T-07
      pr_id: PR-04
      pr_branch: codex/supervisor-remove-planner-pr04
      pr_subject: SSE plan_ready 兼容开关与下线
      pr_depends_on: [PR-03]
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/api/test_chat_sse_intent_goal_status.py -q
      rollback_point: ENABLE_PLAN_READY_COMPAT=true

    - task_id: T-08
      pr_id: PR-04
      pr_branch: codex/supervisor-remove-planner-pr04
      pr_subject: SSE plan_ready 兼容开关与下线
      pr_depends_on: [PR-03]
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && pnpm -C web test -- --runInBand
      rollback_point: 前端类型回退 plan_ready 声明

    - task_id: T-09
      pr_id: PR-05
      pr_branch: codex/supervisor-remove-planner-pr05
      pr_subject: 测试矩阵收敛与旧路径清理
      pr_depends_on: [PR-04]
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit tests/integration tests/api -k "planner or intent or coverage or sse" -q
      rollback_point: 回退测试迁移提交

    - task_id: T-10
      pr_id: PR-05
      pr_branch: codex/supervisor-remove-planner-pr05
      pr_subject: 测试矩阵收敛与旧路径清理
      pr_depends_on: [PR-04]
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && rg -n "intent_plan|_planner_node|emit_plan_ready" app/ai app/services web/src tests
      rollback_point: 恢复兼容代码分支

    - task_id: T-11
      pr_id: PR-05
      pr_branch: codex/supervisor-remove-planner-pr05
      pr_subject: 测试矩阵收敛与旧路径清理
      pr_depends_on: [PR-04]
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/docs_guard.py --strict
      rollback_point: 恢复文档索引变更
```

## 6. execution_contract（机读契约）

```yaml
execution_contract:
  delivery_mode: staged
  execution_unit: per_pr
  commit_policy: per_pr
  stop_boundary: per_pr
  stop_on_blocked: true
```

## 7. implementation_readiness（机读结论）

```yaml
implementation_readiness:
  implementation_ready: true
  blocked_by: []
  next_step: /jjk-imp
  execution_contract_ready: true
```

## 8. pr_ready_manifest（本轮更新：PR-02）

```yaml
pr_ready_manifest:
  - task_id: T-03
    pr_id: PR-02
    card_id: C02
    changed_files:
      - app/ai/workflow/multi_agent_graph.py
      - app/ai/prompts/agent_prompts.py
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py -q
    rollback_point: 关闭 decompose_goals 路径

  - task_id: T-04
    pr_id: PR-02
    card_id: C02
    changed_files:
      - app/ai/workflow/multi_agent_graph.py
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py tests/unit/test_multi_agent_streaming_helpers.py -q
    rollback_point: router 回退兼容入口
```
