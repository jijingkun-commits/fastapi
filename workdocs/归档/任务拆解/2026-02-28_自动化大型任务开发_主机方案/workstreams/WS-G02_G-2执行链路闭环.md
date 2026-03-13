# 工作包说明

> WS 编号: WS-G02
> 名称: G-2 执行链路闭环
> 类型: gate
> 对应 feature_id: G-2

## 0. 关联与来源

- 对应 task_key: PP-20260228-AUTO-LARGE-TASK-HOST
- 对应 card_id: G02
- 来源主计划: `workdocs/归档/实施计划/自动化大型任务开发_主机方案_implementation_plan.md`
- 来源并行计划: `workdocs/归档/任务拆解/2026-02-28_自动化大型任务开发_主机方案/parallel_plan.md`

## 1. 目标

- 本包目标: G-2 执行链路闭环 的可执行落地。
- 完成定义（DoD）:
  - 链路闭环验证通过且无重复推进

### 1.1 功能机制

  - 验证 seed->activate->dispatch->done 全链路闭环
  - 核验单活串行策略与 done_gate 收口一致

### 1.2 代码锚点

  - scripts/coder4/coder4_bootstrap_kernel.py::decide_action
  - scripts/coder4/wt-flow.sh::main

- 来源证据:
  - workdocs/归档/实施计划/自动化大型任务开发_全量打钩板清单.md#24-p1-exit-gate必须全绿

## 2. 文件边界

### 可修改（白名单）
  - scripts/coder4/coder4_bootstrap_kernel.py
  - scripts/coder4/wt-flow.sh

### 禁止修改（黑名单）
- 其他 card_id 白名单外文件

## 3. 串行门禁

- 前置卡: G01
- 解锁条件: 前置卡 done_gate 全部通过
- 本 WS 不得推进条件: 前置卡存在 TODO/IN_PROGRESS/BLOCKED

## 4. 测试与验收

- 验收命令:
  - python3 scripts/coder4/coder4_bootstrap_kernel.py --local-mode --active-task workdocs/归档/任务拆解/2026-02-28_自动化大型任务开发_主机方案/contracts/_active_task.json

## 5. 风险与回滚

- 回滚锚点:
  - FREEZE_ON_CHAIN_FAIL

## 6. card_export

```yaml
card_export:
  id: WS-G02
  card_id: G02
  feature_ids: ['G-2']
  card_key: PP-20260228-AUTO-LARGE-TASK-HOST::WS-G02
  title: G-2 执行链路闭环
  type: gate
  task_mode: inspection-card
  merge_required: false
  execution_mode: serial
  hard_depends_on: ['G01']
  depends_on: ['G01']
  file_whitelist:
  - scripts/coder4/coder4_bootstrap_kernel.py
  - scripts/coder4/wt-flow.sh
  mechanism_summary:
  - 验证 seed->activate->dispatch->done 全链路闭环
  - 核验单活串行策略与 done_gate 收口一致
  code_anchor_refs:
  - scripts/coder4/coder4_bootstrap_kernel.py::decide_action
  - scripts/coder4/wt-flow.sh::main
  acceptance_checks:
  - python3 scripts/coder4/coder4_bootstrap_kernel.py --local-mode --active-task workdocs/归档/任务拆解/2026-02-28_自动化大型任务开发_主机方案/contracts/_active_task.json
  rollback_anchors:
  - FREEZE_ON_CHAIN_FAIL
  evidence_entry: workdocs/归档/实施计划/自动化大型任务开发_全量打钩板清单.md#24-p1-exit-gate必须全绿
  done_gate:
  - 链路闭环验证通过且无重复推进
```
