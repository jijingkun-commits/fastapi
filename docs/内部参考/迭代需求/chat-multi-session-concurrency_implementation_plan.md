# chat-multi-session-concurrency 实施计划

> 更新时间：2026-03-08 13:40 +08:00  
> 上游设计：`docs/plans/2026-03-06-chat-multi-session-concurrency-design.md`  
> 对应需求：`docs/内部参考/迭代需求/chat-multi-session-concurrency_requirements.md`

## 1. 实施概览

- 规划模式：`parallel`
- 交付目标：以“前端会话级运行态 + 后端 DB 真理源 + 测试闭环”三段式完成多会话并发落地，不引入缓存兜底与双真理源。
- 架构策略：前端先消除单实例运行态，再补后端 active query / cancel / 并发门禁，最后用测试与文档索引收口。
- 风险重点：全局流状态残留导致串会话、cancel thread 守卫缺失导致误停、`last_activity_at` 不落库导致刷新/排序失真、active query 继续走内存快照导致多 worker 不一致、hard cancel 长驻 `stopping` 导致侧边栏持续显示 `running` 与并发槽释放滞后。

## 2. implementation_tasks（机读）

```yaml
implementation_tasks:
  - task_id: T-01
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[0]
    feature_id: F1-front-session-runtime
    pr_id: PR-01
    phase: Phase-1
    change_type: modify
    owner: frontend-chat
    depends_on_tasks: [ROOT]
    risk_point: 若 StreamContext 仍保留全局单实例运行态，会继续出现跨会话 submit/stop 串扰
    rollback_point: ENABLE_CHAT_MULTI_SESSION_CONCURRENCY=false
    file_paths:
      - web/src/providers/StreamContext.tsx
    symbols:
      - StreamContextValue
    acceptance_cmds:
      - pnpm --dir web exec playwright test e2e/chat-multi-session-concurrency.spec.cjs
      - 真实链路 UAT：stop 后立即新开第 4 会话，不得出现 `3/3` 误拦截 --grep MSC-CL-001

  - task_id: T-02
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[1]
    feature_id: F1-front-session-runtime
    pr_id: PR-01
    phase: Phase-2
    change_type: modify
    owner: frontend-chat
    depends_on_tasks: [T-01]
    risk_point: 若 `useSSEStream` 不按 thread 分桶、active 空窗不保留本地 streaming，或新线程 init 后不立即入栏，页面停留期间状态仍会漂移
    rollback_point: ENABLE_CHAT_MULTI_SESSION_CONCURRENCY=false
    file_paths:
      - web/src/hooks/useSSEStream.ts
    symbols:
      - useSSEStream
    acceptance_cmds:
      - pnpm --dir web exec playwright test e2e/chat-multi-session-concurrency.spec.cjs
      - 真实链路 UAT：stop 后立即新开第 4 会话，不得出现 `3/3` 误拦截 --grep "MSC-CL-008|MSC-CL-010|MSC-CL-011"

  - task_id: T-03
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[2]
    feature_id: F1-front-session-runtime
    pr_id: PR-01
    phase: Phase-3
    change_type: modify
    owner: frontend-chat
    depends_on_tasks: [T-02]
    risk_point: 若前端 stop 不强制携带 `thread_id`，或 stop 后仍把 `stopping` 展示成 `running`，用户会误以为停止未生效且并发槽无法及时释放
    rollback_point: ENABLE_THREAD_ID_MATCH_CHECK=false
    file_paths:
      - web/src/lib/backend.ts
      - web/src/hooks/useSSEStream.ts
    symbols:
      - cancelRun
      - stop
    acceptance_cmds:
      - pnpm --dir web exec playwright test e2e/chat-multi-session-concurrency.spec.cjs
      - 真实链路 UAT：stop 后立即新开第 4 会话，不得出现 `3/3` 误拦截 --grep MSC-CL-002

  - task_id: T-04
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[3]
    feature_id: F2-active-runs-backend
    pr_id: PR-02
    phase: Phase-1
    change_type: modify
    owner: backend-chat
    depends_on_tasks: [ROOT]
    risk_point: 若 `/chat/runs/active` 返回字段、状态或排序口径不固定，前端刷新恢复会继续抖动和误判
    rollback_point: ENABLE_ACTIVE_RUNS_QUERY=false
    file_paths:
      - app/api/v1/endpoints/chat_api.py
    symbols:
      - list_active_runs
      - CancelRunRequest
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/api/test_chat_api.py -k active_runs_contract

  - task_id: T-05
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[4]
    feature_id: F2-active-runs-backend
    pr_id: PR-02
    phase: Phase-2
    change_type: modify
    owner: backend-chat
    depends_on_tasks: [T-04]
    risk_point: 若 RunControlService 仍以缓存或非原子计数实现 active query / parallel gate，或 hard cancel 不直接收口为 `stopped`，多 worker、并发门禁与 stop 释放槽都会失真
    rollback_point: ENABLE_PER_USER_PARALLEL_GATE=false
    file_paths:
      - app/services/run_control_service.py
    symbols:
      - list_active_runs_by_user
      - create_run
      - cancel_run
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_run_control_service.py -k run_control_active_query_gate

  - task_id: T-06
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[5]
    feature_id: F2-active-runs-backend
    pr_id: PR-02
    phase: Phase-3
    change_type: modify
    owner: backend-chat
    depends_on_tasks: [T-05]
    risk_point: 若 `last_activity_at` 不落库且缺少用户维度 active 索引，排序、黄灯提示与多 worker 恢复都会不稳定
    rollback_point: ENABLE_ACTIVE_RUNS_QUERY=false
    file_paths:
      - app/models/chat_run.py
      - alembic/versions/*_add_last_activity_at_and_active_index_to_chat_run.py
    symbols:
      - ChatRun.last_activity_at
      - ChatRun.__table_args__
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_run_control_service.py -k last_activity_persistence_and_sort

  - task_id: T-07
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[6]
    feature_id: F3-backend-test-closure
    pr_id: PR-03
    phase: Phase-1
    change_type: modify
    owner: test-backend
    depends_on_tasks: [T-05, T-06]
    risk_point: 若缺少 API / service 回归矩阵，错误码、幂等语义和多 worker 一致性会在重构中回退
    rollback_point: ENABLE_CHAT_MULTI_SESSION_CONCURRENCY=false
    file_paths:
      - tests/unit/test_run_control_service.py
      - tests/api/test_chat_api.py
    symbols:
      - test_active_runs
      - test_parallel_limit
      - test_cancel_thread_mismatch
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/api/test_chat_api.py -k multi_session_contract_matrix

  - task_id: T-08
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[7]
    feature_id: F4-frontend-e2e
    pr_id: PR-03
    phase: Phase-2
    change_type: add
    owner: test-frontend
    depends_on_tasks: [T-02, T-03, T-04, T-05]
    risk_point: 若缺少真实浏览器并发场景验证，前端恢复/轮询/停止隔离/停止释放并发槽仍可能只在 mock 场景成立
    rollback_point: ENABLE_CHAT_MULTI_SESSION_CONCURRENCY=false
    file_paths:
      - web/e2e/chat-multi-session-concurrency.spec.cjs
    symbols:
      - MSC-CL-001
      - MSC-CL-002
      - MSC-CL-003
      - MSC-CL-005
      - MSC-CL-010
      - MSC-CL-011
    acceptance_cmds:
      - pnpm --dir web exec playwright test e2e/chat-multi-session-concurrency.spec.cjs
      - 真实链路 UAT：stop 后立即新开第 4 会话，不得出现 `3/3` 误拦截
```

## 3. task_to_pr_mapping（机读）

```yaml
task_to_pr_mapping:
  - task_id: T-01
    pr_id: PR-01
    pr_branch: codex/chat-multi-session-pr-01
    pr_depends_on: []
    pr_subject: "前端会话级 RuntimeBucket 基座"
    acceptance_cmds:
      - pnpm --dir web exec playwright test e2e/chat-multi-session-concurrency.spec.cjs
      - 真实链路 UAT：stop 后立即新开第 4 会话，不得出现 `3/3` 误拦截 --grep MSC-CL-001
    rollback_point: ENABLE_CHAT_MULTI_SESSION_CONCURRENCY=false

  - task_id: T-02
    pr_id: PR-01
    pr_branch: codex/chat-multi-session-pr-01
    pr_depends_on: []
    pr_subject: "前端 active 条件轮询与会话级流状态"
    acceptance_cmds:
      - pnpm --dir web exec playwright test e2e/chat-multi-session-concurrency.spec.cjs
      - 真实链路 UAT：stop 后立即新开第 4 会话，不得出现 `3/3` 误拦截 --grep MSC-CL-008
    rollback_point: ENABLE_CHAT_MULTI_SESSION_CONCURRENCY=false

  - task_id: T-03
    pr_id: PR-01
    pr_branch: codex/chat-multi-session-pr-01
    pr_depends_on: []
    pr_subject: "前端 cancel 强制 thread_id 契约"
    acceptance_cmds:
      - pnpm --dir web exec playwright test e2e/chat-multi-session-concurrency.spec.cjs
      - 真实链路 UAT：stop 后立即新开第 4 会话，不得出现 `3/3` 误拦截 --grep MSC-CL-002
    rollback_point: ENABLE_THREAD_ID_MATCH_CHECK=false

  - task_id: T-04
    pr_id: PR-02
    pr_branch: codex/chat-multi-session-pr-02
    pr_depends_on: []
    pr_subject: "active runs API 响应契约"
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/api/test_chat_api.py -k active_runs_contract
    rollback_point: ENABLE_ACTIVE_RUNS_QUERY=false

  - task_id: T-05
    pr_id: PR-02
    pr_branch: codex/chat-multi-session-pr-02
    pr_depends_on: []
    pr_subject: "RunControlService active 查询与并发门禁"
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_run_control_service.py -k run_control_active_query_gate
    rollback_point: ENABLE_PER_USER_PARALLEL_GATE=false

  - task_id: T-06
    pr_id: PR-02
    pr_branch: codex/chat-multi-session-pr-02
    pr_depends_on: []
    pr_subject: "chat_run last_activity_at 与 active 索引迁移"
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_run_control_service.py -k last_activity_persistence_and_sort
    rollback_point: ENABLE_ACTIVE_RUNS_QUERY=false

  - task_id: T-07
    pr_id: PR-03
    pr_branch: codex/chat-multi-session-pr-03
    pr_depends_on: [PR-02]
    pr_subject: "后端契约回归矩阵补齐"
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/api/test_chat_api.py -k multi_session_contract_matrix
    rollback_point: ENABLE_CHAT_MULTI_SESSION_CONCURRENCY=false

  - task_id: T-08
    pr_id: PR-03
    pr_branch: codex/chat-multi-session-pr-03
    pr_depends_on: [PR-01, PR-02]
    pr_subject: "前端多会话并发 E2E"
    acceptance_cmds:
      - pnpm --dir web exec playwright test e2e/chat-multi-session-concurrency.spec.cjs
      - 真实链路 UAT：stop 后立即新开第 4 会话，不得出现 `3/3` 误拦截
    rollback_point: ENABLE_CHAT_MULTI_SESSION_CONCURRENCY=false
```

## 4. planning_contract（供 `$jjk-imp` 直接消费）

```yaml
planning_contract:
  topic: chat-multi-session-concurrency
  source_seed_ref: clarify_handoff_contract.required.execution_chain_seed
  execution_mode: serial
  task_key: PP-20260306-chat-multi-session-concurrency
  card_order: [C01, C02, C03, G01]
  direct_execution_reason: 改造量可在单会话内按三波次串行收口，无需再拆 vk 卡
  strict_single_active_card: true
  auto_done_policy:
    implementation-card: hard_gate
    inspection-card: policy_gate
  gate_contract:
    mode: as_cards
    gate_ids: [G01]
    depends_on:
      G01: [C03]
  cards:
    - card_id: C01
      wave: P1
      feature_ids: [F1-front-session-runtime]
      task_ids: [T-01, T-02, T-03]
      depends_on: []
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - 前端运行态按 thread_id 分桶，submit/stop 均绑定会话作用域
      acceptance_checks:
        - pnpm --dir web exec playwright test e2e/chat-multi-session-concurrency.spec.cjs
      - 真实链路 UAT：stop 后立即新开第 4 会话，不得出现 `3/3` 误拦截 --grep MSC-CL-001
        - pnpm --dir web exec playwright test e2e/chat-multi-session-concurrency.spec.cjs
      - 真实链路 UAT：stop 后立即新开第 4 会话，不得出现 `3/3` 误拦截 --grep MSC-CL-008
        - pnpm --dir web exec playwright test e2e/chat-multi-session-concurrency.spec.cjs
      - 真实链路 UAT：stop 后立即新开第 4 会话，不得出现 `3/3` 误拦截 --grep MSC-CL-002
      evidence_entry: docs/内部参考/迭代需求/chat-multi-session-concurrency_implementation_plan.md

    - card_id: C02
      wave: P2
      feature_ids: [F2-active-runs-backend]
      task_ids: [T-04, T-05, T-06]
      depends_on: []
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - `/chat/runs/active`、并发门禁、`last_activity_at` 与 active 索引全部收口到 `t_chat_run`
      acceptance_checks:
        - bash scripts/pytest_targeted.sh tests/api/test_chat_api.py -k active_runs_contract
        - bash scripts/pytest_targeted.sh tests/unit/test_run_control_service.py -k run_control_active_query_gate
        - bash scripts/pytest_targeted.sh tests/unit/test_run_control_service.py -k last_activity_persistence_and_sort
      evidence_entry: docs/内部参考/迭代需求/chat-multi-session-concurrency_implementation_plan.md

    - card_id: C03
      wave: P3
      feature_ids: [F3-backend-test-closure, F4-frontend-e2e]
      task_ids: [T-07, T-08]
      depends_on: [C01, C02]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - API / service / E2E 回归矩阵覆盖设计验收门禁
      acceptance_checks:
        - bash scripts/pytest_targeted.sh tests/api/test_chat_api.py -k multi_session_contract_matrix
        - pnpm --dir web exec playwright test e2e/chat-multi-session-concurrency.spec.cjs
      - 真实链路 UAT：stop 后立即新开第 4 会话，不得出现 `3/3` 误拦截
      evidence_entry: docs/内部参考/迭代需求/chat-multi-session-concurrency_implementation_plan.md

    - card_id: G01
      wave: Gate
      feature_ids: [G-01]
      task_ids: []
      depends_on: [C03]
      task_mode: inspection-card
      merge_required: false
      done_gate:
        - clarify->plan 对齐校验、temporal gate 校验、docs 索引校验全部通过
      acceptance_checks:
        - python3 scripts/check_workflow_contract.py --mode clarify_plan --requirements-path docs/内部参考/迭代需求/chat-multi-session-concurrency_requirements.md --implementation-path docs/内部参考/迭代需求/chat-multi-session-concurrency_implementation_plan.md --output docs/内部参考/迭代需求/chat-multi-session-concurrency_clarify_plan_alignment.json
        - python3 scripts/check_workflow_contract.py --mode planning_temporal_gate --implementation-path docs/内部参考/迭代需求/chat-multi-session-concurrency_implementation_plan.md --output docs/内部参考/迭代需求/chat-multi-session-concurrency_planning_temporal_gate.json
        - python3 scripts/docs_guard.py --strict
      evidence_entry: docs/内部参考/迭代需求/chat-multi-session-concurrency_implementation_plan.md
```

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

## 7. 风险、回滚与观测

1. 风险：前端仍残留全局运行态入口。  
   缓解：`T-01~T-03` 合并到同一 PR，避免半切换。
2. 风险：active query 语义与 DB 索引不一致。  
   缓解：`T-04~T-06` 统一归属 `PR-02`，接口、服务、模型/迁移同批收口。
3. 风险：只做单测不做真实浏览器验证。  
   缓解：`T-08` 必须在 `C03` 中与后端矩阵一起完成，不允许跳过。

## 8. 下游说明

1. 当前规划已收敛为串行直执模式，下一步命令固定为 `$jjk-imp`。
2. 本文保留 `card_id` 仅作为实现波次分组，不再要求进入 `$jjk-vkplan`。
3. 若实现阶段发现设计缺口，应回到 `docs/plans/2026-03-06-chat-multi-session-concurrency-design.md` 先修 design，再回补本计划。
