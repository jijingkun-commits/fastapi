# chat-multi-session-concurrency 需求文档

> 更新时间：2026-03-09 00:35 +08:00
> 上游设计：`workdocs/归档/正文/设计/2026-03-06-chat-multi-session-concurrency-design.md`
> 文档目标：定义 WHAT（需求合同、验收门禁、追溯矩阵），供 `chat-multi-session-concurrency_implementation_plan.md` 承接

## 1. 需求范围与目标

### 1.1 核心目标

- 将聊天运行态从“全局单实例流”收敛为“按 `thread_id` 隔离的多会话并发运行态”。
- 固定停止语义为“用户取消目标 run”，确保跨会话不误停。
- 通过 `/chat/runs/active` 恢复刷新后的运行态，并在页面停留期间自动同步活跃会话状态。
- 侧边栏左侧以注意力状态表达会话变化：active run 显示旋转小圆圈；后台线程产生未读新回复时显示蓝点；已读且不在运行时不显示任何圆圈；未读状态仅保留当前页面会话，不跨刷新持久化。
- 将跨 worker 一致性真理源固定为 `t_chat_run`，不再依赖前端内存态或 worker 内存快照。
- 固定 P0 查询/索引口径：`user_id + active statuses` 直查 `t_chat_run`，服务层按 `last_activity_at 非空优先 -> effective_activity_time -> updated_at -> run_id` 排序。

### 1.2 范围

- 前端运行态：`web/src/providers/StreamContext.tsx`、`web/src/hooks/useSSEStream.ts`
- 前端交互与历史列表：`web/src/lib/backend.ts`、`web/src/components/chat/history/index.tsx`
- 后端 API / Service：`app/api/v1/endpoints/chat_api.py`、`app/services/run_control_service.py`
- 运行态模型与迁移：`app/models/chat_run.py`、`alembic/versions/*_add_last_activity_at_and_active_index_to_chat_run.py`
- 自动化验证：`tests/api/test_chat_api.py`、`tests/unit/test_run_control_service.py`、`web/e2e/chat-multi-session-concurrency.spec.cjs`

### 1.3 非范围

- 不做离线 token 事件回放。
- 不做多窗格同屏并发工作台。
- 不重构 LangGraph 业务节点编排。
- P0 不为 `t_chat_message` 增加 `run_id` 字段，不建立 run-to-message 硬关联。

## 2. requirements_contract（机读）

```yaml
requirements_contract:
  topic: "chat-multi-session-concurrency"
  status: approved
  design_source: workdocs/归档/正文/设计/2026-03-06-chat-multi-session-concurrency-design.md
  clarify_handoff_source: workdocs/归档/正文/设计/2026-03-06-chat-multi-session-concurrency-design.md#clarify_handoff_contract
  clarify_handoff_version: v2
  design_approved: true
  design_approval_evidence: "用户明确回复\"确认\""
  design_freeze_summary:
    design_actionable: true
    missing_blocks: []
    risk_level: medium
    risk_counterexamples_count: 5
    handoff_contract_ready: true
    product_contract_ready: true
    implementation_seed_count: 8
    semantic_frozen: true
    contract_source_decided: true
    handoff_seed_alignment_ok: true
    parallel_dependency_ready: true
    replay_canonical_field_set: true
  owner: "chat-runtime"
  approver: "jijingkun"
  updated_at: "2026-03-09 00:35 +08:00"
```

## 3. product_contract_matrix（PRD-Lite 承接）

```yaml
product_contract_matrix:
  target_users:
    - 重度聊天并行任务用户
    - 长耗时会话切换用户
  core_scenarios:
    - 会话A运行中并发提交会话B
    - 仅停止目标会话
    - 刷新后恢复运行态
    - 页面停留期间 active 会话状态自动同步
  business_goal_metrics:
    - 多会话并发完成率>=99.0%
    - 跨会话误停率=0
    - 刷新恢复时延P95<1s
    - 停留同步延迟P95<3s
  non_goals:
    - 离线 token 回放
    - 多窗格同屏
    - 调度算法重构
    - P0 不修改 t_chat_message 表结构
  acceptance_gates:
    - MSC-CL-001
    - MSC-CL-002
    - MSC-CL-003
    - MSC-CL-004
    - MSC-CL-005
    - MSC-CL-006
    - MSC-CL-007
    - MSC-CL-008
    - MSC-CL-009
  release_constraints:
    - ENABLE_CHAT_MULTI_SESSION_CONCURRENCY 默认 true，回退为 false
    - ENABLE_ACTIVE_RUNS_QUERY 默认 true，回退为 false
    - ENABLE_PER_USER_PARALLEL_GATE 默认 true，回退为 false
    - ENABLE_THREAD_ID_MATCH_CHECK 默认 true，回退为 false
```

## 4. fr_contract_matrix（字段级功能需求）

```yaml
fr_contract_matrix:
  - fr_id: FR-01
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[0]
    business_goal_refs:
      - 多会话并发完成率>=99.0%
      - 跨会话误停率=0
    user_value: 用户可在单页内按会话并行推进多个 run，且提交不会跨会话串扰
    trigger: 会话A处于 running 时，用户在会话B发起新问题
    input_contract:
      required_fields: [user_id, thread_id, prompt]
      optional_fields: [idempotency_key]
      source_of_truth: app/services/run_control_service.py
    output_contract:
      required_fields: [run_id, thread_id, status]
      optional_fields: [created_at]
      consumer: web/src/hooks/useSSEStream.ts
    failure_semantics: 同 thread 重复提交返回 409 active_run_exists；跨 thread 提交仅受用户并发上限约束
    observability_fields: [user_id, thread_id, run_id, status, trace_id]
    rollback_anchor: ENABLE_CHAT_MULTI_SESSION_CONCURRENCY=true
    owner: frontend-chat

  - fr_id: FR-02
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[1]
    business_goal_refs:
      - 刷新恢复时延P95<1s
      - 停留同步延迟P95<3s
    user_value: 刷新后仍能看到当前用户全部 active run，并在页面停留期间自动同步状态；侧边栏左侧状态列区分 `running/unread/none`，其中 `running` 显示旋转小圆圈，`unread` 显示蓝点，进入线程后清除未读标记；新线程在服务端返回 `thread_id` 后必须立即出现在历史栏
    trigger: 页面冷启动，或 active_count>0 / 本地仍有 streaming 线程时周期轮询 `/chat/runs/active`
    input_contract:
      required_fields: [jwt_token]
      optional_fields: [poll_interval_seconds]
      source_of_truth: app/api/v1/endpoints/chat_api.py
    output_contract:
      required_fields: [items.run_id, items.thread_id, items.status, items.updated_at, items.last_activity_at, active_count, poll_hint_seconds, server_time]
      optional_fields: []
      consumer: web/src/components/chat/history/index.tsx
    failure_semantics: 查询失败返回 503 并触发 5s/10s 退避；连续3次失败后仅显示轻提示，不隐式改写列表语义
    observability_fields: [user_id, active_count, active_runs_query_latency_ms, active_poll_consecutive_failures]
    rollback_anchor: ENABLE_ACTIVE_RUNS_QUERY=true
    owner: backend-chat

  - fr_id: FR-03
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[2]
    business_goal_refs:
      - 跨会话误停率=0
      - 停留同步延迟P95<3s
    user_value: 用户的停止动作只能命中目标 run，且前端能立即得到最新状态回写；`hard cancel` 被接受后当前线程应立即退出运行态展示
    trigger: 用户点击 stop，客户端携带 `run_id + thread_id` 请求 cancel
    input_contract:
      required_fields: [run_id, thread_id]
      optional_fields: []
      source_of_truth: app/api/v1/endpoints/chat_api.py
    output_contract:
      required_fields: [accepted, idempotent, run_id, thread_id, status]
      optional_fields: [reason]
      consumer: web/src/lib/backend.ts
    failure_semantics: 400 仅用于 thread_id_required/thread_id_mismatch；403/404 分别表示无权限与 run 不存在；terminal/stopping 视为幂等成功，不返回 409；`hard cancel` 成功返回的最新状态固定收口为 `stopped`
    observability_fields: [user_id, run_id, thread_id, status, cancel_reason, cancel_mode]
    rollback_anchor: ENABLE_THREAD_ID_MATCH_CHECK=true
    owner: backend-chat

  - fr_id: FR-04
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[3]
    business_goal_refs:
      - 多会话并发完成率>=99.0%
      - 跨会话误停率=0
    user_value: 同一会话不会并发启动两个 active run，避免同线程状态覆盖与消息串写
    trigger: `create_run` 前检查同 `thread_id` active run
    input_contract:
      required_fields: [user_id, thread_id]
      optional_fields: []
      source_of_truth: app/services/run_control_service.py
    output_contract:
      required_fields: [status_code, error_code, active_run_id]
      optional_fields: []
      consumer: app/api/v1/endpoints/chat_api.py
    failure_semantics: 命中同线程冲突时固定返回 409 active_run_exists，不做隐式替换
    observability_fields: [user_id, thread_id, active_run_id, trace_id]
    rollback_anchor: ENABLE_PER_USER_PARALLEL_GATE=true
    owner: backend-chat

  - fr_id: FR-05
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[4]
    business_goal_refs:
      - 多会话并发完成率>=99.0%
      - 停留同步延迟P95<3s
    user_value: 单用户并发量被硬性限制在可控范围内，避免把运行态与资源占满
    trigger: `create_run` 前统计当前用户 active run 数量
    input_contract:
      required_fields: [user_id]
      optional_fields: []
      source_of_truth: app/services/run_control_service.py
    output_contract:
      required_fields: [status_code, error_code, active_count]
      optional_fields: [limit]
      consumer: app/api/v1/endpoints/chat_api.py
    failure_semantics: 超限固定返回 429 parallel_limit_exceeded；P0 默认 limit=3
    observability_fields: [user_id, active_count, limit, rejected_reason]
    rollback_anchor: ENABLE_PER_USER_PARALLEL_GATE=true
    owner: backend-chat

  - fr_id: FR-06
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[5]
    business_goal_refs:
      - 刷新恢复时延P95<1s
      - 停留同步延迟P95<3s
    user_value: 结构化结果在刷新、回放和前端渲染时使用同一 canonical 字段，不再依赖多字段猜测
    trigger: SSE result / final_answer 落库与前端回放
    input_contract:
      required_fields: [message.additional_kwargs]
      optional_fields: [message.metadata]
      source_of_truth: app/repositories/chat_repo.py
    output_contract:
      required_fields: [canonical_payload]
      optional_fields: [legacy_metadata_fallback]
      consumer: web/src/hooks/useSSEStream.ts
    failure_semantics: 写入统一走 `additional_kwargs`；读取时若缺失可降级读 `metadata`
    observability_fields: [thread_id, message_id, replay_source]
    rollback_anchor: ENABLE_CHAT_MULTI_SESSION_CONCURRENCY=true
    owner: chat-runtime
```

## 5. nfr_contract_matrix（数值阈值）

```yaml
nfr_contract_matrix:
  - nfr_id: NFR-01
    requirement: `/chat/runs/active` 成功轮询间隔固定为 2s；失败退避仅允许 5s 或 10s；active 接口短暂空窗时若本地仍在 streaming，不得清除 running 指示
    owner: backend-chat
  - nfr_id: NFR-02
    requirement: stale hint 阈值固定为 60s；低于阈值不得展示黄灯提示
    owner: frontend-chat
  - nfr_id: NFR-03
    requirement: `last_activity_at` 流式节流写入频率 <= 1次/2s/每run
    owner: backend-chat
  - nfr_id: NFR-04
    requirement: 单用户 active run 上限固定为 3；P0 不得分页
    owner: backend-chat
  - nfr_id: NFR-05
    requirement: active 接口返回状态集合只允许 `running`、`stopping` 两种
    owner: backend-chat
  - nfr_id: NFR-06
    requirement: RuntimeBucketRegistry 终态保留 30s，最多保留 10 个 bucket
    owner: frontend-chat
```

## 6. traceability_matrix（设计 -> FR -> Feature -> Task -> TC）

```yaml
traceability_matrix:
  - design_item: RS-001
    fr_id: FR-01
    feature_id: F1-front-session-runtime
    task_id: T-01
    tc_id: MSC-CL-001
    acceptance_cmd_ref: pnpm --dir web exec playwright test e2e/chat-multi-session-concurrency.spec.cjs --grep MSC-CL-001
    evidence_entry: workdocs/归档/正文/实施计划/chat-multi-session-concurrency_implementation_plan.md

  - design_item: RS-001
    fr_id: FR-01
    feature_id: F1-front-session-runtime
    task_id: T-02
    tc_id: MSC-CL-008
    acceptance_cmd_ref: pnpm --dir web exec playwright test e2e/chat-multi-session-concurrency.spec.cjs --grep MSC-CL-008
    evidence_entry: workdocs/归档/正文/实施计划/chat-multi-session-concurrency_implementation_plan.md

  - design_item: RS-003
    fr_id: FR-03
    feature_id: F1-front-session-runtime
    task_id: T-03
    tc_id: MSC-CL-006
    acceptance_cmd_ref: pnpm --dir web exec playwright test e2e/chat-multi-session-concurrency.spec.cjs --grep MSC-CL-002
    evidence_entry: workdocs/归档/正文/实施计划/chat-multi-session-concurrency_implementation_plan.md

  - design_item: RS-002
    fr_id: FR-02
    feature_id: F2-active-runs-backend
    task_id: T-04
    tc_id: MSC-CL-003
    acceptance_cmd_ref: bash scripts/pytest_targeted.sh tests/api/test_chat_api.py -k active_runs_contract
    evidence_entry: workdocs/归档/正文/实施计划/chat-multi-session-concurrency_implementation_plan.md

  - design_item: RS-004
    fr_id: FR-04
    feature_id: F2-active-runs-backend
    task_id: T-05
    tc_id: MSC-CL-005
    acceptance_cmd_ref: bash scripts/pytest_targeted.sh tests/unit/test_run_control_service.py -k run_control_active_query_gate
    evidence_entry: workdocs/归档/正文/实施计划/chat-multi-session-concurrency_implementation_plan.md

  - design_item: RS-002
    fr_id: FR-02
    feature_id: F2-active-runs-backend
    task_id: T-06
    tc_id: MSC-CL-009
    acceptance_cmd_ref: bash scripts/pytest_targeted.sh tests/unit/test_run_control_service.py -k last_activity_persistence_and_sort
    evidence_entry: workdocs/归档/正文/实施计划/chat-multi-session-concurrency_implementation_plan.md

  - design_item: RS-003
    fr_id: FR-03
    feature_id: F3-backend-test-closure
    task_id: T-07
    tc_id: MSC-CL-004
    acceptance_cmd_ref: bash scripts/pytest_targeted.sh tests/api/test_chat_api.py -k multi_session_contract_matrix
    evidence_entry: workdocs/归档/正文/实施计划/chat-multi-session-concurrency_implementation_plan.md

  - design_item: RS-001
    fr_id: FR-01
    feature_id: F4-frontend-e2e
    task_id: T-08
    tc_id: MSC-CL-001
    acceptance_cmd_ref: pnpm --dir web exec playwright test e2e/chat-multi-session-concurrency.spec.cjs
    evidence_entry: workdocs/归档/正文/实施计划/chat-multi-session-concurrency_implementation_plan.md
```
