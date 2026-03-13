# 实施方案（聊天多会话并发重分析）

## 0. 计划元信息

- topic: 聊天多会话并发重分析
- mode: parallel（plan-only）
- task_key: PP-20260304-CHAT-MULTI-SESSION
- design_source: `workdocs/归档/正文/设计/2026-03-04-chat-multi-session-concurrency-reanalysis-design.md`
- design_approved: true
- scope: 前端运行态重构 + 后端 active runs 查询面 + 停止隔离增强 + 并发门禁
- planning_note: 本文仅产出 WHAT+HOW 与机读契约，不自动触发实现链路

## 1. 输入来源清单（Superpowers 对齐桥接）

1. 设计文档（已审批）
   `workdocs/归档/正文/设计/2026-03-04-chat-multi-session-concurrency-reanalysis-design.md`
2. 历史并发设计参考
   `workdocs/归档/正文/设计/2026-03-01-chat-multi-session-concurrency-design.md`
3. 停止稳定性参考（防回归）
   `workdocs/归档/正文/实施计划/聊天停止后并发占用稳定性修复_implementation_plan.md`
4. 代码锚点
   `web/src/providers/StreamContext.tsx`
   `web/src/hooks/useSSEStream.ts`
   `web/src/components/chat/ChatInput.tsx`
   `web/src/components/chat/history/index.tsx`
   `web/src/lib/backend.ts`
   `app/api/v1/endpoints/chat_api.py`
   `app/services/run_control_service.py`

## 2. 架构影响与约束

### 2.1 模块边界
1. 会话运行态聚合策略归属前端 `StreamContext/useSSEStream`，禁止散落到组件各处临时状态。
2. run 列表查询与并发门禁归属后端 `run_control_service + chat_api`，禁止前端自行推断活跃态作为真理源。
3. 停止隔离校验归属 `chat_api cancel_run` 路径，不下沉到业务节点。

### 2.2 状态契约
1. `run_id` 是停止动作主键；`thread_id` 为隔离保护键（新客户端强制传，旧客户端兼容）。
2. 活跃态定义固定为 `status in {running, stopping}`。
3. `RuntimeBucket` 生命周期：运行中保留、结束后延时清理、上限淘汰。

### 2.3 路由闭环
1. 用户发送 -> `POST /chat/stream` -> `create_run` -> SSE 回调按 `thread_id` 入桶。
2. 用户停止 -> `POST /chat/runs/{run_id}/cancel` -> 可选 `thread_id` 校验 -> 状态转移。
3. 刷新恢复 -> `GET /chat/runs/active` -> 侧边栏徽标 + stop可用性恢复。

### 2.4 端到端时序约束
1. 非当前会话 SSE 回调不得更新当前会话 UI 主视图，只更新对应 bucket。
2. 切换会话时历史消息从 DB 拉取并与 bucket 合并（去重需兼容无 `message_id` 场景）。
3. cancel 失败需重试 1 次并给明确 toast，不得静默失败。

### 2.5 可测试性
1. 前端：hook/store 单测 + 侧边栏状态组件单测。
2. 后端：active runs 查询、thread guard、并发上限门禁单测/API 测试。
3. E2E：并发提交、停止隔离、刷新恢复、竞争场景回归。

## 3. SSE/跨端字段冻结清单

### 3.1 done 事件
- 必选字段：`thread_id`, `run_id`
- 可选字段：`message_id`, `meta.status`, `meta.reason`
- 消费方：`web/src/hooks/useSSEStream.ts`

### 3.2 result 事件
- 必选字段：`data_type`, `data`
- 可选字段：`message`
- 消费方：`web/src/hooks/useSSEStream.ts`

### 3.3 interrupt 事件
- 必选字段：`questions`（或等价可解析结构）
- 可选字段：`message`
- 消费方：`web/src/components/chat/ChatInput.tsx`

## 4. 功能机制包（Feature Packet）

| feature_id | 目标与边界 | 触发条件与状态流转 | 代码锚点（文件+符号） | 关键数据契约 | 回滚锚点 | 验证命令 | 来源证据 |
|---|---|---|---|---|---|---|---|
| P1-01 | 前端会话级 RuntimeRegistry（按 thread 分桶） | submit -> init(run_id) -> token/status -> done/stop -> cleanup | `web/src/providers/StreamContext.tsx` `StreamContextValue`; `web/src/hooks/useSSEStream.ts` `useSSEStream` | `RuntimeBucket{isLoading,currentStatus,messages,interrupt,activeRunId,lastTokenAt}` | `ENABLE_CHAT_MULTI_SESSION_RUNTIME=false` | `cd /Users/jijingkun/bojxAI/fastapi/web && pnpm exec vitest run src/hooks/__tests__/useSSEStream.multi-session.test.ts` | 设计文档 3.2 |
| P1-02 | 输入区停止/提交改为会话作用域 | 当前会话 stop/submit 不影响其他会话 | `web/src/components/chat/ChatInput.tsx` `onStop`; `web/src/components/chat/index.tsx` `handleSubmit` | `submit(threadId, payload)` `stop(threadId)` | `ENABLE_CHAT_MULTI_SESSION_RUNTIME=false` | `cd /Users/jijingkun/bojxAI/fastapi/web && pnpm exec vitest run src/components/chat/__tests__/chat-input-thread-scope.test.tsx` | 设计文档 3.2.4 |
| P1-03 | 侧边栏运行态徽标 + 卡死预警 | active会话显示绿点；30秒无token且满足阶段条件显示黄点 | `web/src/components/chat/history/index.tsx` `ThreadItem`; `web/src/hooks/useSSEStream.ts` `lastTokenAt` | `badge_state`, `lastTokenAt`, `status_phase` | `ENABLE_CHAT_STALL_WARNING=false` | `cd /Users/jijingkun/bojxAI/fastapi/web && pnpm exec vitest run src/components/chat/history/__tests__/thread-runtime-badge.test.tsx` | 设计文档 3.2.4 |
| P2-01 | cancel 接口 thread_guard 兼容增强 | cancel(run_id) -> optional thread_id校验 -> 幂等返回 | `app/api/v1/endpoints/chat_api.py` `CancelRunRequest/cancel_run`; `app/services/run_control_service.py` `cancel_run` | `run_id(path)`, `thread_id?(body)`, `cancel_mode` | `ENABLE_CHAT_RUN_THREAD_GUARD=false` | `PYTHONPATH=. pytest tests/api/test_chat_api.py -k cancel_run_thread_guard -q` | 设计文档 3.4 |
| P2-02 | active runs 查询面补齐 | 页面加载 -> GET active runs -> 合并侧边栏状态 | `app/services/run_control_service.py` `list_active_runs_by_user`; `app/api/v1/endpoints/chat_api.py` `get_active_runs` | `run_id,thread_id,status,cancel_reason,cancel_mode,updated_at` | `ENABLE_CHAT_ACTIVE_RUN_RECOVERY=false` | `PYTHONPATH=. pytest tests/api/test_chat_api.py -k active_runs -q` | 设计文档 3.3 |
| P2-03 | 并发上限原子门禁 | create_run 前先做同用户互斥 + 活跃计数判定 | `app/services/run_control_service.py` `create_run`; `app/api/v1/endpoints/chat_api.py` 错误映射 | `MAX_PARALLEL_STREAMS_PER_USER` `active_count` | `ENABLE_CHAT_PARALLEL_LIMIT=false` | `PYTHONPATH=. pytest tests/unit/test_run_control_service.py -k parallel_limit -q` | 设计文档 3.5 |
| P3-01 | 可观测与降级闭环 | cancel失败/并发拒绝/恢复失败均产生日志和指标 | `app/api/v1/endpoints/chat_api.py`; `web/src/hooks/useSSEStream.ts` | `trace_id,user_id,thread_id,run_id,error_code,retry_count` | `ENABLE_CHAT_MULTI_SESSION_OBSERVABILITY=false` | `PYTHONPATH=. pytest tests/unit/test_run_control_service.py -k observability -q` | 设计文档 3.4.3/3.5.4 |

## 5. 最小代码样例（约束实现形态）

```typescript
// P1-01: 会话级运行态读取（伪代码）
const runtime = runtimeMap.get(threadId) ?? createDefaultRuntime();
runtime.activeRunId = runId;
runtime.lastTokenAt = Date.now();
runtimeMap.set(threadId, runtime);
```

```python
# P2-01: cancel thread_guard（伪代码）
if payload.thread_id is not None and payload.thread_id != snapshot.thread_id:
    raise HTTPException(status_code=400, detail="thread_id mismatch")
```

```python
# P2-03: 并发门禁（伪代码，按数据库方言选择用户级互斥）
with user_mutex(user_id):
    active_count = query_active_count(user_id)
    if active_count >= limit:
        raise ConcurrencyLimitExceeded
    create_run(...)
```

## 6. 工单级任务包（Implementation Tasks）

```yaml
implementation_tasks:
  - task_id: T-01
    feature_id: P1-01
    pr_id: PR-01
    phase: Phase-1
    file_paths:
      - web/src/providers/StreamContext.tsx
      - web/src/hooks/useSSEStream.ts
    symbols:
      - StreamContextValue
      - useSSEStream
    change_type: modify
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi/web && pnpm exec vitest run src/hooks/__tests__/useSSEStream.multi-session.test.ts
    rollback_point: ENABLE_CHAT_MULTI_SESSION_RUNTIME=false

  - task_id: T-02
    feature_id: P1-02
    pr_id: PR-01
    phase: Phase-1
    file_paths:
      - web/src/components/chat/index.tsx
      - web/src/components/chat/ChatInput.tsx
      - web/src/lib/backend.ts
    symbols:
      - handleSubmit
      - ChatInput
      - cancelRun
    change_type: modify
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi/web && pnpm exec vitest run src/components/chat/__tests__/chat-input-thread-scope.test.tsx
    rollback_point: ENABLE_CHAT_MULTI_SESSION_RUNTIME=false

  - task_id: T-03
    feature_id: P1-03
    pr_id: PR-02
    phase: Phase-2
    file_paths:
      - web/src/components/chat/history/index.tsx
      - web/src/hooks/useSSEStream.ts
    symbols:
      - ThreadItem
      - useSSEStream
    change_type: modify
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi/web && pnpm exec vitest run src/components/chat/history/__tests__/thread-runtime-badge.test.tsx
    rollback_point: ENABLE_CHAT_STALL_WARNING=false

  - task_id: T-04
    feature_id: P2-01
    pr_id: PR-03
    phase: Phase-2
    file_paths:
      - app/api/v1/endpoints/chat_api.py
      - app/services/run_control_service.py
      - app/schemas/chat.py
    symbols:
      - CancelRunRequest
      - cancel_run
      - RunControlService.cancel_run
    change_type: modify
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/api/test_chat_api.py -k cancel_run_thread_guard -q
    rollback_point: ENABLE_CHAT_RUN_THREAD_GUARD=false

  - task_id: T-05
    feature_id: P2-02
    pr_id: PR-03
    phase: Phase-2
    file_paths:
      - app/services/run_control_service.py
      - app/api/v1/endpoints/chat_api.py
    symbols:
      - list_active_runs_by_user
      - get_active_runs
    change_type: add
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/api/test_chat_api.py -k active_runs -q
    rollback_point: ENABLE_CHAT_ACTIVE_RUN_RECOVERY=false

  - task_id: T-06
    feature_id: P2-02
    pr_id: PR-04
    phase: Phase-3
    file_paths:
      - web/src/providers/Thread.tsx
      - web/src/components/chat/history/index.tsx
    symbols:
      - refreshThreads
      - ThreadHistory
    change_type: modify
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi/web && pnpm exec vitest run src/components/chat/history/__tests__/thread-history-active-runs.test.tsx
    rollback_point: ENABLE_CHAT_ACTIVE_RUN_RECOVERY=false

  - task_id: T-07
    feature_id: P2-03
    pr_id: PR-04
    phase: Phase-3
    file_paths:
      - app/services/run_control_service.py
      - app/api/v1/endpoints/chat_api.py
      - tests/unit/test_run_control_service.py
    symbols:
      - create_run
      - ConcurrencyLimitExceeded
      - test_parallel_limit
    change_type: modify
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/unit/test_run_control_service.py -k parallel_limit -q
    rollback_point: ENABLE_CHAT_PARALLEL_LIMIT=false

  - task_id: T-08
    feature_id: P3-01
    pr_id: PR-05
    phase: Phase-4
    file_paths:
      - app/api/v1/endpoints/chat_api.py
      - web/src/hooks/useSSEStream.ts
      - tests/api/test_chat_api.py
    symbols:
      - cancel_run
      - stop
      - test_cancel_retry_and_toast_contract
    change_type: modify
    acceptance_cmds:
      - PYTHONPATH=. pytest tests/api/test_chat_api.py -k observability -q
    rollback_point: ENABLE_CHAT_MULTI_SESSION_OBSERVABILITY=false
```

## 7. TC -> Task 追溯映射

| tc_id | feature_id | task_id | acceptance_cmd |
|---|---|---|---|
| TC-MSC-001 | P1-01 | T-01 | `cd /Users/jijingkun/bojxAI/fastapi/web && pnpm exec vitest run src/hooks/__tests__/useSSEStream.multi-session.test.ts` |
| TC-MSC-002 | P2-01 | T-04 | `PYTHONPATH=. pytest tests/api/test_chat_api.py -k cancel_run_thread_guard -q` |
| TC-MSC-003 | P2-02 | T-05 | `PYTHONPATH=. pytest tests/api/test_chat_api.py -k active_runs -q` |
| TC-MSC-004 | P1-02 | T-02 | `cd /Users/jijingkun/bojxAI/fastapi/web && pnpm exec vitest run src/components/chat/__tests__/chat-input-thread-scope.test.tsx` |
| TC-MSC-005 | P2-03 | T-07 | `PYTHONPATH=. pytest tests/unit/test_run_control_service.py -k parallel_limit -q` |
| TC-MSC-006 | P1-03 | T-03 | `cd /Users/jijingkun/bojxAI/fastapi/web && pnpm exec vitest run src/components/chat/history/__tests__/thread-runtime-badge.test.tsx` |
| TC-MSC-007 | P1-02 | T-02 | `cd /Users/jijingkun/bojxAI/fastapi/web && pnpm exec vitest run src/components/chat/__tests__/chat-input-thread-scope.test.tsx` |
| TC-MSC-008 | P2-02 | T-06 | `cd /Users/jijingkun/bojxAI/fastapi/web && pnpm exec vitest run src/components/chat/history/__tests__/thread-history-active-runs.test.tsx` |
| TC-MSC-009 | P2-01 | T-04 | `PYTHONPATH=. pytest tests/api/test_chat_api.py -k cancel_run_thread_guard -q` |
| TC-MSC-010 | P3-01 | T-08 | `PYTHONPATH=. pytest tests/api/test_chat_api.py -k observability -q` |

## 8. 并行拆解种子（card_seed）

```yaml
task_key: PP-20260304-CHAT-MULTI-SESSION
card_seed:
  - card_id: C01
    title: 前端运行态分桶与会话作用域API
    feature_ids: [P1-01, P1-02]
    hard_depends_on: []
    soft_depends_on: []
    file_scope:
      - web/src/providers/StreamContext.tsx
      - web/src/hooks/useSSEStream.ts
      - web/src/components/chat/index.tsx
      - web/src/components/chat/ChatInput.tsx
    owner_fields: [frontend, runtime]
    check_cmd:
      - cd /Users/jijingkun/bojxAI/fastapi/web && pnpm exec vitest run src/hooks/__tests__/useSSEStream.multi-session.test.ts
    done_gate:
      - 会话级提交与停止能力可用

  - card_id: C02
    title: 侧边栏运行态徽标与预警
    feature_ids: [P1-03]
    hard_depends_on: [C01]
    soft_depends_on: []
    file_scope:
      - web/src/components/chat/history/index.tsx
      - web/src/providers/Thread.tsx
    owner_fields: [frontend, ui]
    check_cmd:
      - cd /Users/jijingkun/bojxAI/fastapi/web && pnpm exec vitest run src/components/chat/history/__tests__/thread-runtime-badge.test.tsx
    done_gate:
      - 运行态徽标和卡死预警准确

  - card_id: C03
    title: 后端取消隔离与active runs查询
    feature_ids: [P2-01, P2-02]
    hard_depends_on: []
    soft_depends_on: [C01]
    file_scope:
      - app/api/v1/endpoints/chat_api.py
      - app/services/run_control_service.py
      - app/schemas/chat.py
    owner_fields: [backend, run-control]
    check_cmd:
      - PYTHONPATH=. pytest tests/api/test_chat_api.py -k "cancel_run_thread_guard or active_runs" -q
    done_gate:
      - 停止隔离和恢复查询可用

  - card_id: C04
    title: 并发门禁与观测闭环
    feature_ids: [P2-03, P3-01]
    hard_depends_on: [C03]
    soft_depends_on: [C02]
    file_scope:
      - app/services/run_control_service.py
      - app/api/v1/endpoints/chat_api.py
      - tests/unit/test_run_control_service.py
    owner_fields: [backend, observability]
    check_cmd:
      - PYTHONPATH=. pytest tests/unit/test_run_control_service.py -k "parallel_limit or observability" -q
    done_gate:
      - 并发上限与日志观测闭环完成
```

## 9. 机读规划契约（planning_contract）

```yaml
planning_contract:
  execution_mode: parallel
  card_order: [C01, C02, C03, C04, G01]
  strict_single_active_card: false
  auto_done_policy:
    implementation-card: hard_gate
    inspection/question-card: policy_gate
  gate_contract:
    mode: as_cards
    gate_ids: [G01]
    depends_on:
      G01: [C02, C04]
  cards:
    - card_id: C01
      wave: P1
      feature_ids: [P1-01, P1-02]
      depends_on: []
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - submit/stop 按thread_id作用域运行
      acceptance_checks:
        - cd /Users/jijingkun/bojxAI/fastapi/web && pnpm exec vitest run src/hooks/__tests__/useSSEStream.multi-session.test.ts
      evidence_entry: workdocs/归档/正文/实施计划/聊天多会话并发重分析_implementation_plan.md

    - card_id: C02
      wave: P1
      feature_ids: [P1-03]
      depends_on: [C01]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - 运行态徽标与卡死预警规则正确
      acceptance_checks:
        - cd /Users/jijingkun/bojxAI/fastapi/web && pnpm exec vitest run src/components/chat/history/__tests__/thread-runtime-badge.test.tsx
      evidence_entry: workdocs/归档/正文/实施计划/聊天多会话并发重分析_implementation_plan.md

    - card_id: C03
      wave: P2
      feature_ids: [P2-01, P2-02]
      depends_on: []
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - cancel thread_guard 与 active runs API 完成
      acceptance_checks:
        - PYTHONPATH=. pytest tests/api/test_chat_api.py -k "cancel_run_thread_guard or active_runs" -q
      evidence_entry: workdocs/归档/正文/实施计划/聊天多会话并发重分析_implementation_plan.md

    - card_id: C04
      wave: P2
      feature_ids: [P2-03, P3-01]
      depends_on: [C03]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - 并发上限与观测闭环通过
      acceptance_checks:
        - PYTHONPATH=. pytest tests/unit/test_run_control_service.py -k "parallel_limit or observability" -q
      evidence_entry: workdocs/归档/正文/实施计划/聊天多会话并发重分析_implementation_plan.md

    - card_id: G01
      wave: Gate
      feature_ids: [G-1]
      depends_on: [C02, C04]
      task_mode: inspection-card
      merge_required: false
      done_gate:
        - 文档索引与门禁检查通过
      acceptance_checks:
        - python3 scripts/docs_guard.py --strict
      evidence_entry: workdocs/归档/正文/实施计划/聊天多会话并发重分析_implementation_plan.md

  task_to_pr_mapping:
    - task_id: T-01
      pr_id: PR-01
      pr_branch: codex/chat-multi-session-pr-01
      pr_depends_on: []
      pr_subject: "P1 前端运行态分桶与会话级submit/stop"
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi/web && pnpm exec vitest run src/hooks/__tests__/useSSEStream.multi-session.test.ts
      rollback_point: ENABLE_CHAT_MULTI_SESSION_RUNTIME=false

    - task_id: T-02
      pr_id: PR-01
      pr_branch: codex/chat-multi-session-pr-01
      pr_depends_on: []
      pr_subject: "P1 输入区会话作用域绑定"
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi/web && pnpm exec vitest run src/components/chat/__tests__/chat-input-thread-scope.test.tsx
      rollback_point: ENABLE_CHAT_MULTI_SESSION_RUNTIME=false

    - task_id: T-03
      pr_id: PR-02
      pr_branch: codex/chat-multi-session-pr-02
      pr_depends_on: [PR-01]
      pr_subject: "P1 侧边栏运行态徽标与卡死预警"
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi/web && pnpm exec vitest run src/components/chat/history/__tests__/thread-runtime-badge.test.tsx
      rollback_point: ENABLE_CHAT_STALL_WARNING=false

    - task_id: T-04
      pr_id: PR-03
      pr_branch: codex/chat-multi-session-pr-03
      pr_depends_on: []
      pr_subject: "P2 cancel thread_guard 兼容增强"
      acceptance_cmds:
        - PYTHONPATH=. pytest tests/api/test_chat_api.py -k cancel_run_thread_guard -q
      rollback_point: ENABLE_CHAT_RUN_THREAD_GUARD=false

    - task_id: T-05
      pr_id: PR-03
      pr_branch: codex/chat-multi-session-pr-03
      pr_depends_on: []
      pr_subject: "P2 active runs 查询接口"
      acceptance_cmds:
        - PYTHONPATH=. pytest tests/api/test_chat_api.py -k active_runs -q
      rollback_point: ENABLE_CHAT_ACTIVE_RUN_RECOVERY=false

    - task_id: T-06
      pr_id: PR-04
      pr_branch: codex/chat-multi-session-pr-04
      pr_depends_on: [PR-03]
      pr_subject: "P2 前端刷新恢复 active runs 状态"
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi/web && pnpm exec vitest run src/components/chat/history/__tests__/thread-history-active-runs.test.tsx
      rollback_point: ENABLE_CHAT_ACTIVE_RUN_RECOVERY=false

    - task_id: T-07
      pr_id: PR-04
      pr_branch: codex/chat-multi-session-pr-04
      pr_depends_on: [PR-03]
      pr_subject: "P2 并发上限原子门禁"
      acceptance_cmds:
        - PYTHONPATH=. pytest tests/unit/test_run_control_service.py -k parallel_limit -q
      rollback_point: ENABLE_CHAT_PARALLEL_LIMIT=false

    - task_id: T-08
      pr_id: PR-05
      pr_branch: codex/chat-multi-session-pr-05
      pr_depends_on: [PR-04]
      pr_subject: "P3 可观测与降级闭环"
      acceptance_cmds:
        - PYTHONPATH=. pytest tests/api/test_chat_api.py -k observability -q
      rollback_point: ENABLE_CHAT_MULTI_SESSION_OBSERVABILITY=false
```

## 10. 执行契约（execution_contract）

```yaml
execution_contract:
  delivery_mode: staged
  execution_unit: per_pr
  commit_policy: per_pr
  stop_boundary: per_pr
  stop_on_blocked: true
```

## 11. 实施就绪状态（implementation_readiness）

```yaml
implementation_readiness:
  implementation_ready: true
  blocked_by: []
  next_step: /jjk-vkplan
  execution_contract_ready: true
```

## 12. 风险、回滚与观测

1. 风险：前端分桶状态内存泄漏。
   缓解：结束态延迟清理 + 上限淘汰 + 内存观测指标。
2. 风险：并发门禁实现与数据库方言不一致。
   缓解：按 `DATABASE_URL` 选择用户级互斥实现，预留降级分支。
3. 风险：旧客户端不传 `thread_id` 与新契约冲突。
   缓解：后端“传入时强校验、未传保持兼容”策略。

## 13. 文档分层与引用关系

1. 本文是主计划（WHAT->HOW 可执行桥接）。
2. 设计真理源为 `workdocs/归档/正文/设计/2026-03-04-chat-multi-session-concurrency-reanalysis-design.md`。
3. 后续 `$jjk-vkplan` 仅细化卡片，不改写本文的 `feature_id/task_id/card_id/dependency` 硬依赖。
