# 工作包说明

> WS 编号: WS-C01
> 名称: P0 hooks互斥与幂等治理
> 类型: parallel
> 对应 feature_id: P0-02

## 0. 关联与来源

- 对应 task_key: PP-20260228-AUTO-LARGE-TASK-HOST
- 对应 card_id: C01
- 来源主计划: `docs/内部参考/迭代需求/自动化大型任务开发_主机方案_implementation_plan.md`
- 来源并行计划: `docs/内部参考/任务拆解/2026-02-28_自动化大型任务开发_主机方案/parallel_plan.md`

## 1. 目标

- 本包目标: P0 hooks互斥与幂等治理 的可执行落地。
- 完成定义（DoD）:
  - 并发触发时仅出现一个 RUN_LOCK_ACQUIRED
  - 120 秒内重复触发命中 SKIP_DUPLICATE_EVENT
  - docs_guard 严格校验通过

### 1.1 功能机制

  - 执行级互斥锁保证同一时间窗口仅一轮推进
  - 幂等键窗口过滤重复 wake/agent/cron 触发
  - 重复事件统一记录 SKIP_DUPLICATE_EVENT 并不阻断主链路

### 1.2 代码锚点

  - scripts/coder4_bootstrap_kernel.py::with_run_lock
  - scripts/coder4_bootstrap_kernel.py::build_idempotency_key
  - scripts/coder4_bootstrap_kernel.py::should_skip_duplicate

- 来源证据:
  - docs/内部参考/迭代需求/自动化大型任务开发_主机方案_implementation_plan.md#p0-02-触发互斥锁与幂等键

## 2. 文件边界

### 可修改（白名单）
  - scripts/coder4_bootstrap_kernel.py
  - docs/内部参考/迭代需求/自动化大型任务开发_全量打钩板清单.md

### 禁止修改（黑名单）
- 其他 card_id 白名单外文件

## 3. 串行门禁

- 前置卡: 无
- 解锁条件: 前置卡 done_gate 全部通过
- 本 WS 不得推进条件: 前置卡存在 TODO/IN_PROGRESS/BLOCKED

## 4. 测试与验收

- 验收命令:
  - python3 scripts/coder4_bootstrap_kernel.py --help
  - python3 scripts/docs_guard.py --strict

## 5. 风险与回滚

- 回滚锚点:
  - DISABLE_RUN_LOCK
  - DISABLE_IDEMPOTENCY_WINDOW

## 6. card_export

```yaml
card_export:
  id: WS-C01
  card_id: C01
  feature_ids: ['P0-02']
  card_key: PP-20260228-AUTO-LARGE-TASK-HOST::WS-C01
  title: P0 hooks互斥与幂等治理
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  hard_depends_on: []
  depends_on: []
  file_whitelist:
  - scripts/coder4_bootstrap_kernel.py
  - docs/内部参考/迭代需求/自动化大型任务开发_全量打钩板清单.md
  mechanism_summary:
  - 执行级互斥锁保证同一时间窗口仅一轮推进
  - 幂等键窗口过滤重复 wake/agent/cron 触发
  - 重复事件统一记录 SKIP_DUPLICATE_EVENT 并不阻断主链路
  code_anchor_refs:
  - scripts/coder4_bootstrap_kernel.py::with_run_lock
  - scripts/coder4_bootstrap_kernel.py::build_idempotency_key
  - scripts/coder4_bootstrap_kernel.py::should_skip_duplicate
  acceptance_checks:
  - python3 scripts/coder4_bootstrap_kernel.py --help
  - python3 scripts/docs_guard.py --strict
  rollback_anchors:
  - DISABLE_RUN_LOCK
  - DISABLE_IDEMPOTENCY_WINDOW
  evidence_entry: docs/内部参考/迭代需求/自动化大型任务开发_全量打钩板清单.md#1-p0-打钩板触发器切换--主机安全基线
  done_gate:
  - 并发触发时仅出现一个 RUN_LOCK_ACQUIRED
  - 120 秒内重复触发命中 SKIP_DUPLICATE_EVENT
  - docs_guard 严格校验通过
```
