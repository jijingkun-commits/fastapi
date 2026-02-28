# 工作包说明

> WS 编号: WS-C02
> 名称: P1 状态文件原子写与锁保护
> 类型: parallel
> 对应 feature_id: P1-01

## 0. 关联与来源

- 对应 task_key: PP-20260228-AUTO-LARGE-TASK-HOST
- 对应 card_id: C02
- 来源主计划: `docs/内部参考/迭代需求/自动化大型任务开发_主机方案_implementation_plan.md`
- 来源并行计划: `docs/内部参考/任务拆解/2026-02-28_自动化大型任务开发_主机方案/parallel_plan.md`

## 1. 目标

- 本包目标: P1 状态文件原子写与锁保护 的可执行落地。
- 完成定义（DoD）:
  - 状态文件中断写入后仍可恢复并解析
  - 并发写场景无 JSON 损坏

### 1.1 功能机制

  - task-runner-state 使用 write-to-temp + rename 原子写入
  - 写入前后增加文件锁避免并发覆盖
  - 写入失败可回退 .bak 保障状态可恢复

### 1.2 代码锚点

  - scripts/coder4_bootstrap_kernel.py::atomic_write_json
  - scripts/coder4_bootstrap_kernel.py::load_local_state
  - scripts/coder4_bootstrap_kernel.py::update_local_card_status

- 来源证据:
  - docs/内部参考/迭代需求/自动化大型任务开发设计方案.md#46-原子写入实现

## 2. 文件边界

### 可修改（白名单）
  - scripts/coder4_bootstrap_kernel.py
  - .omc/state/task-runner-state.json

### 禁止修改（黑名单）
- 其他 card_id 白名单外文件

## 3. 串行门禁

- 前置卡: C01
- 解锁条件: 前置卡 done_gate 全部通过
- 本 WS 不得推进条件: 前置卡存在 TODO/IN_PROGRESS/BLOCKED

## 4. 测试与验收

- 验收命令:
  - python3 scripts/coder4_bootstrap_kernel.py --local-mode --active-task docs/内部参考/任务拆解/_active_task.json
  - python3 scripts/docs_guard.py --strict

## 5. 风险与回滚

- 回滚锚点:
  - task-runner-state.json.bak

## 6. card_export

```yaml
card_export:
  id: WS-C02
  card_id: C02
  feature_ids: ['P1-01']
  card_key: PP-20260228-AUTO-LARGE-TASK-HOST::WS-C02
  title: P1 状态文件原子写与锁保护
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  hard_depends_on: ['C01']
  depends_on: ['C01']
  file_whitelist:
  - scripts/coder4_bootstrap_kernel.py
  - .omc/state/task-runner-state.json
  mechanism_summary:
  - task-runner-state 使用 write-to-temp + rename 原子写入
  - 写入前后增加文件锁避免并发覆盖
  - 写入失败可回退 .bak 保障状态可恢复
  code_anchor_refs:
  - scripts/coder4_bootstrap_kernel.py::atomic_write_json
  - scripts/coder4_bootstrap_kernel.py::load_local_state
  - scripts/coder4_bootstrap_kernel.py::update_local_card_status
  acceptance_checks:
  - python3 scripts/coder4_bootstrap_kernel.py --local-mode --active-task docs/内部参考/任务拆解/_active_task.json
  - python3 scripts/docs_guard.py --strict
  rollback_anchors:
  - task-runner-state.json.bak
  evidence_entry: docs/内部参考/迭代需求/自动化大型任务开发_主机方案_implementation_plan.md#p1-01-状态文件原子写与锁保护
  done_gate:
  - 状态文件中断写入后仍可恢复并解析
  - 并发写场景无 JSON 损坏
```
