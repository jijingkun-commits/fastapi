# chat-composite-latency-local-refactor 实施计划

> 日期：2026-03-12
> 需求基线：`docs/内部参考/迭代需求/chat-composite-latency-local-refactor_requirements.md`
> 方案基线：`docs/plans/2026-03-12-chat-composite-latency-local-refactor-design.md`
> execution_mode：`serial`
> change_mode：`refactor`

## 0. 输入来源清单

1. `docs/内部参考/迭代需求/chat-composite-latency-local-refactor_requirements.md`
2. `docs/plans/2026-03-12-chat-composite-latency-local-refactor-design.md`
3. `docs/plans/2026-03-10-composite-chat-latency-design.md`
4. `app/ai/workflow/multi_agent_graph.py`
5. `app/ai/workflow/todo_graph.py`
6. `app/services/chat_service.py`
7. `tests/unit/test_multi_agent_streaming_helpers.py`
8. `tests/unit/test_multi_intent_queue_flow.py`
9. `tests/unit/test_chat_service_done_payload.py`
10. `app/tests/test_handoff_detection.py`

## 1. execution_strategy

1. 不引入全量并行图，不新增生产级并行 runtime；优先在现有热点内部做减法收口。
2. 先修“可见时延”与“frozen todo.query 误澄清”两个最贵问题，再补 coverage 正确性和 timing 观测。
3. 所有 answered/coverage 口径必须围绕最小 goal outcome helper 收敛，禁止继续用 summary/evidence 弱信号做成功判断。
4. 文档同步只在实现确认不漂移后一次性更新，避免先写文档后又推翻口径。

## 2. task_breakdown

```yaml
task_breakdown:
  - task_id: T-01
    goal: "局部收口 preprocess fast lane，让 explicit composite 的 external.lookup 能提前回流可见正文"
    requirement_ids: [FR-01, FR-06]
    design_refs:
      - "module_boundaries"
      - "Runtime Design Details/1"
      - "Shrink Contract"
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
      - tests/unit/test_multi_agent_streaming_helpers.py
    symbols:
      - _preprocess_multimodal
      - _resolve_decomposed_goals_for_query
      - emit_plan_ready
      - emit_token
    depends_on: []
    change_type: modify
    acceptance_cmds:
      - kind: env_probe
        cmd: "bash scripts/repo_python.sh"
      - kind: targeted_pytest
        cmd: "bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py -k 'fast_lane or preview' -q"
    rollback_point: "恢复为只有 data bucket 命中时才允许 external preview 的旧门槛"
    risk_tags: [preview-regression, duplicate-visible-output]
    mandatory_evidence:
      - "todo+weather 场景可在 final_answer 前回流用户可见正文"
      - "status/tool_start/handoff 不被当作首个用户可见内容"
      - "单一提问与非显式复合路径无回退"
    db_migration_cmds:
      - "none"

  - task_id: T-02
    goal: "让 frozen todo.query 直通执行，不再被整句复合原句误裁成 out_of_scope"
    requirement_ids: [FR-02]
    design_refs:
      - "module_boundaries"
      - "dependency_direction"
      - "Runtime Design Details/2"
    file_paths:
      - app/ai/workflow/todo_graph.py
      - tests/unit/test_todo_nodes.py
      - app/tests/test_handoff_detection.py
    symbols:
      - _should_skip_out_of_scope_guard
      - analyze_intent
      - pending_handoff.frame.todo_action
    depends_on: []
    change_type: modify
    acceptance_cmds:
      - kind: env_probe
        cmd: "bash scripts/repo_python.sh"
      - kind: targeted_pytest
        cmd: "bash scripts/pytest_targeted.sh tests/unit/test_todo_nodes.py app/tests/test_handoff_detection.py -q"
    rollback_point: "恢复为 todo_graph 可重新基于整句原问题裁决 frozen todo.query 的旧路径"
    risk_tags: [todo-query-regression, clarify-regression]
    mandatory_evidence:
      - "todo.query 在复合天气场景下不再误判为 out_of_scope"
      - "只有 handoff 缺失或不完整时才回退到 clarify"
      - "create/update/delete/complete 现有路径不被误伤"
    db_migration_cmds:
      - "none"

  - task_id: T-03
    goal: "把 coverage/final 收口切到最小 goal outcome 口径，clarify/failed/pending 不再计入 answered"
    requirement_ids: [FR-03, FR-04]
    design_refs:
      - "dependency_direction"
      - "state_ownership"
      - "Runtime Design Details/3"
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
      - tests/unit/test_multi_intent_queue_flow.py
    symbols:
      - _can_match_deliverable_for_coverage
      - _can_render_goal_attempt
      - _compute_coverage_report
      - _render_final_answer
    depends_on: [T-01, T-02]
    change_type: modify
    acceptance_cmds:
      - kind: env_probe
        cmd: "bash scripts/repo_python.sh"
      - kind: targeted_pytest
        cmd: "bash scripts/pytest_targeted.sh tests/unit/test_multi_intent_queue_flow.py -q"
    rollback_point: "恢复现有 deliverable summary/evidence 驱动的 answered 口径"
    risk_tags: [coverage-regression, final-answer-drift]
    mandatory_evidence:
      - "clarify_needed/failed/pending 不再计入 answered_goals"
      - "coverage_pass=false 时 final_answer 不再出现“已全部覆盖”"
      - "goal 顺序与最终答复顺序保持一致"
    db_migration_cmds:
      - "none"

  - task_id: T-04
    goal: "补齐请求级与 per-goal timing 观测，并保证 stream/resume 使用同一套口径"
    requirement_ids: [FR-05, FR-06]
    design_refs:
      - "state_ownership"
      - "Runtime Design Details/4"
      - "Doc Sync Flags"
    file_paths:
      - app/services/chat_service.py
      - tests/unit/test_chat_service_done_payload.py
      - tests/unit/test_chat_service_latency_runtime.py
    symbols:
      - stream
      - sse_resume_stream
      - final_answer.meta
      - done.meta
    depends_on: [T-01, T-03]
    change_type: modify
    acceptance_cmds:
      - kind: env_probe
        cmd: "bash scripts/repo_python.sh"
      - kind: targeted_pytest
        cmd: "bash scripts/pytest_targeted.sh tests/unit/test_chat_service_done_payload.py tests/unit/test_chat_service_latency_runtime.py -q"
    rollback_point: "删除新增 timing meta，回退到现有 request 生命周期输出"
    risk_tags: [timing-contract-drift, resume-drift]
    mandatory_evidence:
      - "first_event/first_visible/final_answer/done 结构化字段可见"
      - "若补充了 goal_timing，则 stream 与 resume 口径一致"
      - "done/final_answer 既有契约未被破坏"
    db_migration_cmds:
      - "none"

  - task_id: T-05
    goal: "同步 API/产品/架构/测试真理源，确保局部重构版 B 与实现口径一致"
    requirement_ids: [FR-01, FR-02, FR-03, FR-04, FR-05, FR-06]
    design_refs:
      - "Doc Sync Flags"
      - "Shrink Contract"
    file_paths:
      - docs/API文档/接口文档.md
      - docs/产品文档/聊天系统需求.md
      - docs/开发文档/架构设计/AI模块设计.md
      - docs/开发文档/测试管理/聊天系统测试案例.md
      - docs/开发文档/测试管理/测试用例库.md
      - docs/内部参考/迭代需求/chat-composite-latency-local-refactor_implementation_plan.md
      - docs/内部参考/迭代需求/chat-composite-latency-local-refactor_uat_cases.md
    symbols:
      - composite_fast_lane_local_refactor
      - frozen_todo_query_contract
      - goal_outcome_based_coverage
      - request_goal_timing_meta
    depends_on: [T-04]
    change_type: modify
    acceptance_cmds:
      - kind: doc_sync
        cmd: "bash scripts/check_doc_sync.sh --strict"
    rollback_point: "回退文档到旧串行口径，并重新评审实现漂移"
    risk_tags: [doc-drift, traceability-gap]
    mandatory_evidence:
      - "API/产品/架构/测试文档同步完成"
      - "UAT 与自动化覆盖映射完整"
      - "doc sync / docs guard 不再出现同主题双口径"
    db_migration_cmds:
      - "none"
```

## 3. task_dependencies

```yaml
task_dependencies:
  - T-01 -> [T-03, T-04]
  - T-02 -> [T-03]
  - T-03 -> [T-04]
  - T-04 -> [T-05]
```

## 4. acceptance_cmds

```yaml
acceptance_cmds:
  - kind: env_probe
    cmd: "bash scripts/repo_python.sh"
  - kind: targeted_pytest
    cmd: "bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_todo_nodes.py app/tests/test_handoff_detection.py tests/unit/test_multi_intent_queue_flow.py tests/unit/test_chat_service_done_payload.py tests/unit/test_chat_service_latency_runtime.py -q"
  - kind: doc_sync
    cmd: "bash scripts/check_doc_sync.sh --strict"
```

## 5. risk_and_rollback

| 风险 | 说明 | 控制手段 | 回退策略 |
|---|---|---|---|
| R-01 | preview 提前回流导致重复正文 | 用显式去重与 first_visible 判定保护 | 回退到旧 preview 门槛 |
| R-02 | frozen todo.query 直通误伤其他 todo 动作 | 只限定 `todo_action=query` 的 frozen contract | 恢复旧 guard 路径 |
| R-03 | coverage 口径切换后出现 false negative | 先补定向回归，再切 answered 判定 | 回退到旧 coverage predicate |
| R-04 | request timing 与 resume timing 漂移 | 使用同一 meta builder，测试同时覆盖两条路径 | 暂时回退 goal_timing，仅保留 request timing |
| R-05 | 文档写成“已并行化”而实现仍是局部重构 | 文档同步时明确 B 方案边界，不借题发挥 | 回退文档口径并重新评审 |

## 6. db_migration_plan

```yaml
db_migration_plan:
  db_migration_required: false
  release_migration_required: false
  tasks: []
```

## 7. done_criteria

```yaml
done_criteria:
  - "显式复合 todo+weather 请求能在 final_answer 前看到首段用户可见正文"
  - "frozen todo.query 不再误入 out_of_scope -> need_clarify"
  - "coverage 只把 answered goal 计入 answered_goals"
  - "有缺口时 final_answer 不再出现“以上问题已全部覆盖”"
  - "request-level/per-goal timing 元数据输出与文档口径一致"
  - "API/产品/架构/测试文档同步完成"
```
