# 意图优化实施计划（规划保留、运行剥离）

> 更新时间：2026-03-04  
> 上游输入：`docs/plans/意图优化.design.md`、`docs/内部参考/迭代需求/意图优化_requirements.md`  
> 当前模式：`core`（plan-only，不自动进入执行链）

## 0. 输入来源清单（Superpowers 桥接）

- design：`docs/plans/意图优化.design.md`
- requirements：`docs/内部参考/迭代需求/意图优化_requirements.md`
- 关键代码入口：
  - `app/ai/workflow/multi_agent_graph.py`
  - `app/ai/prompts/agent_prompts.py`
  - `app/ai/contracts/delivery_contract_validators.py`
- 关键测试入口：
  - `tests/unit/test_intent_layer_boundary.py`
  - `tests/unit/test_multi_agent_streaming_helpers.py`
  - `tests/unit/test_multi_intent_queue_flow.py`
  - `tests/integration/test_intent_shadow_metrics.py`

## 1. 架构影响与约束

### 1.1 模块边界

- 规划层：保留现有目标拆解策略链路，保障 `decompose_goals` 稳定产能。
- 运行层：路由门禁与执行编排只消费 `decomposed_goals`。
- 兜底层：异常、阻塞、缺口统一回到 `supervisor`。

### 1.2 状态契约

- 规划阶段：允许使用规划中间契约对象生成 `goals`。
- 运行阶段：`decomposed_goals` 为唯一目标源，`target_agent` 为唯一委派字段。
- 失败路径：统一产生结构化 `reason`，不可静默失败。

### 1.3 可测试性

- 单元测试覆盖：目标归一、路由门禁、values 分支。
- 集成测试覆盖：规划 fallback 与收口完整性。
- 可观测验证：阻塞事件与覆盖结果事件字段完整。

## 2. 功能机制包（Feature Packet）

| feature_id | 目标 | 文件锚点 | 核心符号 | 风险点 | 回滚锚点 |
|---|---|---|---|---|---|
| P1-01 | 运行态目标解析剥离旧状态读取 | `app/ai/workflow/multi_agent_graph.py` | `_resolve_active_goals` | 多目标误判 | 恢复 `_resolve_active_goals` 旧分支 |
| P1-02 | 规划链路稳定与 fallback 观测保留 | `app/ai/workflow/multi_agent_graph.py` | `_resolve_decomposed_goals_for_query` | 规划质量抖动 | `intent_mode=heuristic_only` |
| P1-03 | Router Gate 单轨门禁 | `app/ai/workflow/multi_agent_graph.py` | `_apply_router_contract_guard` | 过拦截 | `ENABLE_ROUTER_CONTRACT_GUARD=false` |
| P1-04 | values 分支显式合同收敛 | `app/ai/workflow/multi_agent_graph.py` | `_dispatch_values_mode_chunk` | 合同误判 | 回退该函数增量 |
| P1-05 | 规划/门禁/覆盖可观测事件补齐 | `app/ai/workflow/multi_agent_graph.py` | `router_handoff_blocked` 等事件 | 字段缺失 | 回退事件字段扩展 |
| P1-06 | Supervisor 兜底路径契约化 | `app/ai/workflow/multi_agent_graph.py` | fallback 相关分支 | 空答复 | `ENABLE_SUPERVISOR_FALLBACK_ONLY=true` |

## 3. 工单级任务拆解（implementation_tasks）

```yaml
implementation_tasks:
  - task_id: T01
    source_seed_ref: clarify_handoff_contract.implementation_seeds[0]
    feature_id: P1-01
    phase: Phase-1
    change_type: refactor
    owner: ai-workflow
    pr_id: PR-01
    risk_point: 运行态目标来源切换后复合目标可能漏识别
    rollback_point: 恢复 _resolve_active_goals 旧读取分支
    depends_on_tasks: [ROOT]
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
    symbols:
      - _resolve_active_goals
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_intent_layer_boundary.py -q

  - task_id: T02
    source_seed_ref: clarify_handoff_contract.implementation_seeds[1]
    feature_id: P1-02
    phase: Phase-1
    change_type: modify
    owner: ai-workflow
    pr_id: PR-02
    risk_point: 规划策略保留后指标口径和新测试不一致
    rollback_point: 保持规划链路原样并切回 heuristic_only
    depends_on_tasks: [T01]
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
      - tests/unit/test_goal_planner_model_primary.py
    symbols:
      - _resolve_decomposed_goals_for_query
      - _build_decomposed_goals_for_query
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_goal_planner_model_primary.py -q

  - task_id: T03
    source_seed_ref: clarify_handoff_contract.implementation_seeds[2]
    feature_id: P1-03
    phase: Phase-2
    change_type: refactor
    owner: ai-workflow
    pr_id: PR-03
    risk_point: 门禁条件变更导致误拦截
    rollback_point: ENABLE_ROUTER_CONTRACT_GUARD=false
    depends_on_tasks: [T01, T02]
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
      - tests/unit/test_multi_intent_queue_flow.py
    symbols:
      - _apply_router_contract_guard
      - _build_router_dispatch_goal_queue
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py -q

  - task_id: T04
    source_seed_ref: clarify_handoff_contract.implementation_seeds[3]
    feature_id: P1-04
    phase: Phase-2
    change_type: refactor
    owner: ai-workflow
    pr_id: PR-04
    risk_point: 显式合同判定收敛后 values 分支行为波动
    rollback_point: 恢复 _dispatch_values_mode_chunk 旧判定路径
    depends_on_tasks: [T03]
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
      - tests/unit/test_multi_agent_streaming_helpers.py
    symbols:
      - _dispatch_values_mode_chunk
      - has_explicit_router_contract
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py -q

  - task_id: T05
    source_seed_ref: clarify_handoff_contract.implementation_seeds[4]
    feature_id: P1-05
    phase: Phase-3
    change_type: modify
    owner: ai-workflow
    pr_id: PR-05
    risk_point: 观测字段增加后事件结构不稳定
    rollback_point: 回退事件字段扩展并保留最小事件
    depends_on_tasks: [T04]
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
      - tests/integration/test_goal_shadow_metrics.py
    symbols:
      - planner_fallback_activated
      - router_handoff_blocked
      - coverage_result
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/integration/test_goal_shadow_metrics.py -q

  - task_id: T06
    source_seed_ref: clarify_handoff_contract.implementation_seeds[5]
    feature_id: P1-06
    phase: Phase-3
    change_type: add
    owner: ai-workflow
    pr_id: PR-06
    risk_point: 兜底路径契约不一致导致最终答复不稳定
    rollback_point: 恢复 fallback 收口前版本
    depends_on_tasks: [T04, T05]
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
      - tests/unit/test_supervisor_fallback_contract.py
    symbols:
      - supervisor_fallback_activated
      - final_answer
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_supervisor_fallback_contract.py -q
```

## 4. Task -> PR 映射（task_to_pr_mapping）

```yaml
planning_contract:
  execution_mode: serial
  card_order: [C01, C02, C03, C04, C05, C06]
  strict_single_active_card: true
  cards:
    - card_id: C01
      wave: P1
      feature_ids: [P1-01]
      depends_on: []
      task_mode: implementation-card
      merge_required: true
      done_gate: [T01 done]
      acceptance_checks:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_intent_layer_boundary.py -q
      evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md
    - card_id: C02
      wave: P1
      feature_ids: [P1-02]
      depends_on: [C01]
      task_mode: implementation-card
      merge_required: true
      done_gate: [T02 done]
      acceptance_checks:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_goal_planner_model_primary.py -q
      evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md
    - card_id: C03
      wave: P1
      feature_ids: [P1-03]
      depends_on: [C02]
      task_mode: implementation-card
      merge_required: true
      done_gate: [T03 done]
      acceptance_checks:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py -q
      evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md
    - card_id: C04
      wave: P1
      feature_ids: [P1-04]
      depends_on: [C03]
      task_mode: implementation-card
      merge_required: true
      done_gate: [T04 done]
      acceptance_checks:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py -q
      evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md
    - card_id: C05
      wave: P1
      feature_ids: [P1-05]
      depends_on: [C04]
      task_mode: implementation-card
      merge_required: true
      done_gate: [T05 done]
      acceptance_checks:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/integration/test_goal_shadow_metrics.py -q
      evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md
    - card_id: C06
      wave: P1
      feature_ids: [P1-06]
      depends_on: [C04, C05]
      task_mode: implementation-card
      merge_required: true
      done_gate: [T06 done]
      acceptance_checks:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_supervisor_fallback_contract.py -q
      evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md
  task_to_pr_mapping:
    - task_id: T01
      pr_id: PR-01
      pr_branch: codex/intent-opt-pr-01
      pr_subject: "运行态目标解析剥离旧状态读取"
      pr_depends_on: []
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_intent_layer_boundary.py -q
      rollback_point: 恢复 _resolve_active_goals 旧分支
    - task_id: T02
      pr_id: PR-02
      pr_branch: codex/intent-opt-pr-02
      pr_subject: "规划链路稳定与 fallback 观测保留"
      pr_depends_on: [PR-01]
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_goal_planner_model_primary.py -q
      rollback_point: intent_mode 回退到 heuristic_only
    - task_id: T03
      pr_id: PR-03
      pr_branch: codex/intent-opt-pr-03
      pr_subject: "Router Gate 单轨门禁收敛"
      pr_depends_on: [PR-02]
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py -q
      rollback_point: ENABLE_ROUTER_CONTRACT_GUARD=false
    - task_id: T04
      pr_id: PR-04
      pr_branch: codex/intent-opt-pr-04
      pr_subject: "values 分支显式合同判定收敛"
      pr_depends_on: [PR-03]
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py -q
      rollback_point: 恢复 _dispatch_values_mode_chunk 旧逻辑
    - task_id: T05
      pr_id: PR-05
      pr_branch: codex/intent-opt-pr-05
      pr_subject: "观测事件与指标字段补齐"
      pr_depends_on: [PR-04]
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/integration/test_goal_shadow_metrics.py -q
      rollback_point: 回退事件字段扩展
    - task_id: T06
      pr_id: PR-06
      pr_branch: codex/intent-opt-pr-06
      pr_subject: "Supervisor 兜底契约化回归"
      pr_depends_on: [PR-04, PR-05]
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_supervisor_fallback_contract.py -q
      rollback_point: 恢复 fallback 收口路径
```

## 5. TC 显式映射（tc_task_mapping）

```yaml
tc_task_mapping:
  - tc_id: TC-IO-01
    task_id: T01
    pr_id: PR-01
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_intent_layer_boundary.py -q
  - tc_id: TC-IO-02
    task_id: T01
    pr_id: PR-01
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_intent_layer_boundary.py -q
  - tc_id: TC-IO-03
    task_id: T03
    pr_id: PR-03
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py -q
  - tc_id: TC-IO-04
    task_id: T06
    pr_id: PR-06
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_supervisor_fallback_contract.py -q
  - tc_id: TC-IO-05
    task_id: T03
    pr_id: PR-03
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py -q
  - tc_id: TC-IO-06
    task_id: T04
    pr_id: PR-04
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py -q
  - tc_id: TC-IO-07
    task_id: T02
    pr_id: PR-02
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_goal_planner_model_primary.py -q
  - tc_id: TC-IO-08
    task_id: T05
    pr_id: PR-05
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/integration/test_goal_shadow_metrics.py -q
  - tc_id: TC-IO-09
    task_id: T06
    pr_id: PR-06
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_supervisor_fallback_contract.py -q
```

## 6. 执行契约（execution_contract）

```yaml
execution_contract:
  delivery_mode: one_shot
  execution_unit: all_tasks
  commit_policy: single_commit
  stop_boundary: none
  stop_on_blocked: true
  source_seed_ref: clarify_handoff_contract.execution_chain_seed.execution_contract_hint
```

## 7. 规划就绪状态（implementation_readiness）

```yaml
implementation_readiness:
  implementation_ready: true
  blocked_by: []
  next_step: /jjk-imp
  execution_contract_ready: true
```
