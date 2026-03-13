# 实施方案（聊天停止后并发占用稳定性修复）

## 0. 计划元信息
- topic: 聊天停止后并发占用稳定性修复
- mode: core（plan-only）
- task_key: CHAT-STABILITY-20260302
- 计划目标: 按方案 C（先止血、后连接池治理）完成稳定性修复，保持现有 API 与业务语义不变。

## 1. 输入来源清单（Superpowers 对齐桥接）

1. 设计文档（已审批）
   `workdocs/归档/正文/设计/2026-03-02-chat-stop-checkpointer-stability-design.md`
2. 既有实施基线
   `workdocs/归档/正文/实施计划/聊天断页续跑与强停止_implementation_plan.md`
3. 既有设计参考
   `workdocs/归档/正文/设计/2026-03-01-chat-session-continuation-design.md`
4. 并发会话设计参考
   `workdocs/归档/正文/设计/2026-03-01-chat-multi-session-concurrency-design.md`
5. 关键代码锚点
   `app/services/chat_service.py`
   `app/db/postgres_checkpoint.py`
   `app/ai/workflow/multi_agent_graph.py`

## 2. 架构影响与约束

### 2.1 模块边界
1. 运行时收口策略归属 `chat_service`，不下沉到业务工具层。
2. checkpointer 连接生命周期归属 `db/postgres_checkpoint.py`，禁止在业务节点各自持有独立连接策略。
3. `multi_agent_graph` 仅负责消费统一 checkpointer 获取接口，不复制连接管理逻辑。

### 2.2 状态契约
1. 保持 `thread_id` / `run_id` 为唯一运行态锚点。
2. 不新增前后端协议字段，不改 `done/stopped/error` 的语义。
3. 取消态与断连态分流仍由 run_control 语义主导，避免重复状态写入。

### 2.3 路由闭环
1. `stream` 与 `resume` 收口路径统一遵循“先判定运行态，再决定是否回读状态”的策略。
2. `cancel_checkpoint` 保持幂等，不向上抛出破坏性异常。

### 2.4 端到端链路
1. stop/cancel 请求不改变前端调用方式。
2. 后端收口改造不影响历史消息落库流程与反馈能力。

### 2.5 可测试性
1. 单测覆盖停止后重试、取消流收口、resume 取消后终态一致。
2. 预留并发会话回归验证入口（后续可接 E2E）。

## 3. 功能机制包（Feature Packet）

| feature_id | 目标与边界 | 触发条件与状态流转 | 代码锚点 | 关键契约字段 | 回滚锚点 | 验证命令 | 来源证据 |
|---|---|---|---|---|---|---|---|
| P0-01 | 止血：断连/取消收口保护，不让后续 run 被污染 | stop/disconnect -> 收口守卫 -> 安全结束/错误可恢复 | `app/services/chat_service.py` `stream`/`sse_resume_stream` | `thread_id` `run_id` `status` | 回退到现有收口逻辑（仅保留原始行为） | `venv/bin/python -m pytest tests/unit/test_chat_service_disconnect_continue.py tests/unit/test_chat_service_cancel_stream.py -q` | 2026-03-02 线上日志 busy 堆叠 |
| P1-01 | 治根：checkpointer 并发安全连接管理（池化） | get_checkpointer 并发访问 -> 池化连接 -> 安全复用 | `app/db/postgres_checkpoint.py` `get_checkpointer` `close_checkpointer` | `checkpointer instance` `pool lifecycle` | 回退单连接模式 | `venv/bin/python -m pytest tests/unit/test_chat_service_resume_after_cancel.py -q` | `workdocs/归档/正文/设计/2026-03-02-chat-stop-checkpointer-stability-design.md` |
| P1-02 | 取消检查路径一致性，避免冲突扩大 | cancel_run -> cancel_checkpoint -> 状态读取/降级 | `app/ai/workflow/multi_agent_graph.py` `cancel_checkpoint` | `run_id` `thread_id` | 回退到旧 cancel_checkpoint 逻辑 | `venv/bin/python -m pytest tests/unit/test_chat_stop_cancel_semantics.py -q` | `workdocs/归档/正文/实施计划/聊天断页续跑与强停止_implementation_plan.md` |
| P1-03 | 可观测增强：分阶段日志与故障分类 | stream/resume/cancel_checkpoint 报错 -> 分类日志 | `app/services/chat_service.py` `app/db/postgres_checkpoint.py` | `stage` `run_id` `thread_id` | 关闭新增日志分支 | `venv/bin/python -m pytest tests/unit/test_events_contract.py -q` | 线上故障排查闭环要求 |

## 4. 最小代码样例（约束实现形态）

```python
# P0-01: stream/resume 收口守卫（伪代码）
if client_disconnected or run_cancelled:
    skip_state_readback = True
if not skip_state_readback:
    snapshot = await graph.aget_state(config)
```

```python
# P1-01: checkpointer 池化（伪代码）
async with init_lock:
    if pool is None:
        pool = AsyncConnectionPool(...)
    if checkpointer is None:
        checkpointer = AsyncPostgresSaver(conn=pool)
        await checkpointer.setup()
return checkpointer
```

```python
# P1-02: cancel_checkpoint 幂等降级（伪代码）
try:
    snapshot = await checkpointer.aget(...)
except Exception:
    log_warning(...)
    return False
```

## 5. 测试策略（TDD 前置推荐）

```yaml
test_strategy:
  - feature_id: P0-01
    test_cases:
      - CHAT-STAB-TC-001: 停止后立即重试，后续请求可恢复
      - CHAT-STAB-TC-003: resume 与 cancel 交叉，终态一致
    test_first: true
  - feature_id: P1-01
    test_cases:
      - CHAT-STAB-TC-004: 连续 stop 压测下无持续 busy
    test_first: false
  - feature_id: P1-02
    test_cases:
      - CHAT-STAB-TC-002: 双会话并发停止隔离
    test_first: false
```

## 6. 工单级任务包（Implementation Tasks）

```yaml
implementation_tasks:
  - task_id: T-01
    feature_id: P0-01
    pr_id: PR-01
    phase: Phase-0
    file_paths:
      - app/services/chat_service.py
    symbols:
      - ChatService.stream
      - sse_resume_stream
    change_type: modify
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_chat_service_disconnect_continue.py tests/unit/test_chat_service_cancel_stream.py -q
    rollback_point: 回退 stream/resume 收口守卫逻辑

  - task_id: T-02
    feature_id: P1-01
    pr_id: PR-02
    phase: Phase-1
    file_paths:
      - app/db/postgres_checkpoint.py
      - app/main.py
    symbols:
      - get_checkpointer
      - close_checkpointer
      - lifespan
    change_type: modify
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_chat_service_resume_after_cancel.py -q
    rollback_point: 回退 checkpointer 单连接实现

  - task_id: T-03
    feature_id: P1-02
    pr_id: PR-02
    phase: Phase-1
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
    symbols:
      - cancel_checkpoint
    change_type: modify
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_chat_stop_cancel_semantics.py -q
    rollback_point: 回退 cancel_checkpoint 降级分支

  - task_id: T-04
    feature_id: P1-03
    pr_id: PR-03
    phase: Phase-2
    file_paths:
      - app/services/chat_service.py
      - app/db/postgres_checkpoint.py
      - tests/unit/test_chat_service_done_payload.py
    symbols:
      - ChatService.stream
      - ChatService._save_conversation_fallback
    change_type: modify
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_events_contract.py tests/unit/test_chat_service_done_payload.py -q
    rollback_point: 关闭新增观测日志与错误分类输出
```

## 7. PR 映射契约（task_to_pr_mapping）

```yaml
planning_contract:
  task_to_pr_mapping:
    - task_id: T-01
      pr_id: PR-01
      pr_branch: codex/chat-stop-stability-pr-01
      pr_depends_on: []
      pr_subject: "P0 止血：停止后收口守卫，避免持续 busy"
      acceptance_cmds:
        - venv/bin/python -m pytest tests/unit/test_chat_service_disconnect_continue.py tests/unit/test_chat_service_cancel_stream.py -q
      rollback_point: 回退 chat_service 收口守卫
    - task_id: T-02
      pr_id: PR-02
      pr_branch: codex/chat-stop-stability-pr-02
      pr_depends_on:
        - PR-01
      pr_subject: "P1 治根：checkpointer 连接池化与生命周期治理"
      acceptance_cmds:
        - venv/bin/python -m pytest tests/unit/test_chat_service_resume_after_cancel.py tests/unit/test_chat_stop_cancel_semantics.py -q
      rollback_point: 回退 postgres_checkpoint 池化改造
    - task_id: T-03
      pr_id: PR-02
      pr_branch: codex/chat-stop-stability-pr-02
      pr_depends_on:
        - PR-01
      pr_subject: "P1 治根：cancel_checkpoint 幂等降级一致性"
      acceptance_cmds:
        - venv/bin/python -m pytest tests/unit/test_chat_stop_cancel_semantics.py -q
      rollback_point: 回退 cancel_checkpoint 新分支
    - task_id: T-04
      pr_id: PR-03
      pr_branch: codex/chat-stop-stability-pr-03
      pr_depends_on:
        - PR-02
      pr_subject: "P2 收口：可观测增强与回归补齐"
      acceptance_cmds:
        - venv/bin/python -m pytest tests/unit/test_events_contract.py tests/unit/test_chat_service_done_payload.py -q
      rollback_point: 回退日志分类与新增回归测试
```

## 8. 机读执行契约（planning_contract）

```yaml
planning_contract:
  execution_mode: serial
  card_order: [C01, C02, C03]
  strict_single_active_card: true
  auto_done_policy:
    implementation-card: hard_gate
    inspection/question-card: policy_gate
  gate_contract:
    mode: none
    gate_ids: []
    depends_on: {}
  cards:
    - card_id: C01
      wave: P0
      feature_ids: [P0-01]
      depends_on: []
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - stop/disconnect 收口守卫生效且无持续 busy
      acceptance_checks:
        - venv/bin/python -m pytest tests/unit/test_chat_service_disconnect_continue.py tests/unit/test_chat_service_cancel_stream.py -q
      evidence_entry: workdocs/归档/正文/实施计划/聊天停止后并发占用稳定性修复_implementation_plan.md
    - card_id: C02
      wave: P1
      feature_ids: [P1-01, P1-02]
      depends_on: [C01]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - checkpointer 池化接入并通过 cancel/resume 回归
      acceptance_checks:
        - venv/bin/python -m pytest tests/unit/test_chat_service_resume_after_cancel.py tests/unit/test_chat_stop_cancel_semantics.py -q
      evidence_entry: workdocs/归档/正文/实施计划/聊天停止后并发占用稳定性修复_implementation_plan.md
    - card_id: C03
      wave: P2
      feature_ids: [P1-03]
      depends_on: [C02]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - 可观测日志齐全且回归测试通过
      acceptance_checks:
        - venv/bin/python -m pytest tests/unit/test_events_contract.py tests/unit/test_chat_service_done_payload.py -q
        - python3 scripts/docs_guard.py --strict
      evidence_entry: workdocs/归档/正文/实施计划/聊天停止后并发占用稳定性修复_implementation_plan.md
  task_to_pr_mapping:
    - task_id: T-01
      pr_id: PR-01
      pr_branch: codex/chat-stop-stability-pr-01
      pr_depends_on: []
      pr_subject: "P0 止血：停止后收口守卫，避免持续 busy"
      acceptance_cmds:
        - venv/bin/python -m pytest tests/unit/test_chat_service_disconnect_continue.py tests/unit/test_chat_service_cancel_stream.py -q
      rollback_point: 回退 chat_service 收口守卫
    - task_id: T-02
      pr_id: PR-02
      pr_branch: codex/chat-stop-stability-pr-02
      pr_depends_on:
        - PR-01
      pr_subject: "P1 治根：checkpointer 连接池化与生命周期治理"
      acceptance_cmds:
        - venv/bin/python -m pytest tests/unit/test_chat_service_resume_after_cancel.py tests/unit/test_chat_stop_cancel_semantics.py -q
      rollback_point: 回退 postgres_checkpoint 池化改造
    - task_id: T-03
      pr_id: PR-02
      pr_branch: codex/chat-stop-stability-pr-02
      pr_depends_on:
        - PR-01
      pr_subject: "P1 治根：cancel_checkpoint 幂等降级一致性"
      acceptance_cmds:
        - venv/bin/python -m pytest tests/unit/test_chat_stop_cancel_semantics.py -q
      rollback_point: 回退 cancel_checkpoint 新分支
    - task_id: T-04
      pr_id: PR-03
      pr_branch: codex/chat-stop-stability-pr-03
      pr_depends_on:
        - PR-02
      pr_subject: "P2 收口：可观测增强与回归补齐"
      acceptance_cmds:
        - venv/bin/python -m pytest tests/unit/test_events_contract.py tests/unit/test_chat_service_done_payload.py -q
      rollback_point: 回退日志分类与新增回归测试
```

## 9. 执行契约（execution_contract）

```yaml
execution_contract:
  delivery_mode: one_shot
  execution_unit: all_tasks
  commit_policy: single_commit
  stop_boundary: none
  stop_on_blocked: true
```

## 10. 实施就绪状态（implementation_readiness）

```yaml
implementation_readiness:
  implementation_ready: true
  blocked_by: []
  next_step: /jjk-imp
  execution_contract_ready: true
```

## 11. 回滚与风险

1. 风险：池化改造后若初始化时序处理不当，可能导致首次请求抖动。
   缓解：采用初始化锁并保留单连接回滚分支。
2. 风险：止血守卫若范围过大，可能影响 interrupt 可见性。
   缓解：仅在断连/取消态触发，正常态保留原行为。
3. 风险：回归覆盖不足导致隐性回归。
   缓解：将 stop/disconnect/resume 三条链路纳入必测命令。

## 12. 实施回填（$jjk-imp）

### 12.1 任务完成记录

1. T-01（P0-01）
   - changed_files:
     - `app/services/chat_service.py`
     - `tests/unit/test_chat_service_disconnect_continue.py`
   - acceptance_cmds:
     - `venv/bin/python -m pytest tests/unit/test_chat_service_disconnect_continue.py tests/unit/test_chat_service_cancel_stream.py -q`
   - result: passed

2. T-02（P1-01）
   - changed_files:
     - `app/db/postgres_checkpoint.py`
     - `app/main.py`
     - `tests/unit/test_postgres_checkpointer_pooling.py`
   - acceptance_cmds:
     - `venv/bin/python -m pytest tests/unit/test_chat_service_resume_after_cancel.py tests/unit/test_chat_stop_cancel_semantics.py -q`
   - result: passed

3. T-03（P1-02）
   - changed_files:
     - `app/ai/workflow/multi_agent_graph.py`
   - acceptance_cmds:
     - `venv/bin/python -m pytest tests/unit/test_chat_stop_cancel_semantics.py -q`
   - result: passed

4. T-04（P1-03）
   - changed_files:
     - `app/services/chat_service.py`
     - `tests/unit/test_chat_service_done_payload.py`
   - acceptance_cmds:
     - `venv/bin/python -m pytest tests/unit/test_events_contract.py tests/unit/test_chat_service_done_payload.py -q`
   - result: passed

### 12.2 一次性回归证据

- command:
  `./venv/bin/python -m pytest tests/unit/test_postgres_checkpointer_pooling.py tests/unit/test_chat_service_disconnect_continue.py tests/unit/test_chat_service_cancel_stream.py tests/unit/test_chat_service_resume_after_cancel.py tests/unit/test_chat_stop_cancel_semantics.py tests/unit/test_events_contract.py tests/unit/test_chat_service_done_payload.py -q`
- result: `19 passed`

### 12.3 文档门禁状态

- command: `python3 scripts/docs_guard.py --strict`
- result: warning（`summary_missing_doc workdocs/归档/正文/设计/2026-03-02-supervisor-refactor-remove-planner-design.md`）
- note: 该问题属于仓库全局文档索引缺口，与本次“聊天停止后并发占用稳定性修复”实现范围无关，不作为本任务阻塞项。

### 12.4 pr_ready_manifest

```yaml
pr_ready_manifest:
  - task_id: T-01
    pr_id: PR-01
    card_id: C01
    changed_files:
      - app/services/chat_service.py
      - tests/unit/test_chat_service_disconnect_continue.py
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_chat_service_disconnect_continue.py tests/unit/test_chat_service_cancel_stream.py -q
    rollback_point: 回退 chat_service 收口守卫逻辑

  - task_id: T-02
    pr_id: PR-02
    card_id: C02
    changed_files:
      - app/db/postgres_checkpoint.py
      - app/main.py
      - tests/unit/test_postgres_checkpointer_pooling.py
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_chat_service_resume_after_cancel.py tests/unit/test_chat_stop_cancel_semantics.py -q
    rollback_point: 回退 postgres_checkpoint 单连接实现

  - task_id: T-03
    pr_id: PR-02
    card_id: C02
    changed_files:
      - app/ai/workflow/multi_agent_graph.py
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_chat_stop_cancel_semantics.py -q
    rollback_point: 回退 cancel_checkpoint busy 降级分支

  - task_id: T-04
    pr_id: PR-03
    card_id: C03
    changed_files:
      - app/services/chat_service.py
      - tests/unit/test_chat_service_done_payload.py
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_events_contract.py tests/unit/test_chat_service_done_payload.py -q
    rollback_point: 回退错误分类文案与日志分支
```
