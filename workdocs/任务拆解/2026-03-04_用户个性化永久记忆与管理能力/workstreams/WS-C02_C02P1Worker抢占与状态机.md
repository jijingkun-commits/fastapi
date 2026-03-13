# C02 P1 Worker抢占与状态机

> WS 编号: WS-C02  
> 类型: parallel  
> 对应 feature_id: P1-02

## 0. 关联与来源

- 对应 `task_key`: `PP-20260304-USER-MEMORY-LLM-ASYNC`
- 来源主计划：`workdocs/归档/实施计划/用户个性化永久记忆与管理能力_implementation_plan.md`
- 来源并行计划：`workdocs/任务拆解/2026-03-04_用户个性化永久记忆与管理能力/parallel_plan.md`

## 1. 目标

- 本包目标：Worker 使用 SKIP LOCKED 抢占 pending 任务
- 完成定义（DoD）：Worker 使用 SKIP LOCKED 抢占 pending 任务; failed 按退避重试并进入 dead_letter

### 1.1 功能机制

- 触发条件：当前卡被 `card_order` 激活。
- 输入：上游依赖卡状态与本卡代码锚点。
- 输出：本卡 `acceptance_checks` 全部通过并回填证据。
- 状态流转：Backlog -> Doing -> Review -> Done。

### 1.2 代码锚点与样例

- 代码锚点：
  - `app/services/memory_intent_worker_service.py::run_once`
  - `app/repositories/user_memory_intent_job_repo.py::claim_pending`

```python
# 伪代码：执行本卡机制并输出可验证结果
result = execute_c02()
assert result.ok
```

## 2. 文件边界

### 可修改（白名单）
- `app/services/memory_intent_worker_service.py`
- `app/repositories/user_memory_intent_job_repo.py`

### 禁止修改（黑名单）
- 不在本卡代码锚点中的跨卡文件

## 3. 状态与契约

- 依赖卡：C01
- task_mode：`implementation-card`
- merge_required：`true`
- 外部契约：`planning_contract` 与 `vk_cards` 一致

## 4. 实施步骤

1. 拉取并确认依赖卡状态。
2. 完成机制点并补测试。
3. 执行验收命令并回填证据。

## 5. 测试与验收

- 验收命令：
- `venv/bin/python -m pytest tests/unit/test_memory_intent_worker_service.py -q`

- 对应 implementation plan `done_gate`：`workdocs/归档/实施计划/用户个性化永久记忆与管理能力_implementation_plan.md` 中 `C02` 段。
- 证据回填位置：`workdocs/归档/实施计划/用户个性化永久记忆与管理能力_implementation_plan.md`

## 6. 风险与回滚

- 主要风险：跨卡依赖未满足导致误推进。
- 回滚点：
- 停止 worker 调度入口

## 7. card_export（机读）

```yaml
card_export:
  id: WS-C02
  card_id: C02
  feature_ids: ["P1-02"]
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  hard_depends_on: ["C01"]
  acceptance_checks:
    - venv/bin/python -m pytest tests/unit/test_memory_intent_worker_service.py -q
  rollback_anchors:
    - 停止 worker 调度入口
  evidence_entry: workdocs/归档/实施计划/用户个性化永久记忆与管理能力_implementation_plan.md
  pr_id: PR-02
  pr_branch: codex/user-memory-async-pr-02
  pr_depends_on: ["PR-01"]
  pr_subject: "worker 抢占与状态机"
```
