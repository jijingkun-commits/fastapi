# 工作包说明

> WS 编号: WS-C04
> 名称: P1 wt-flow扩展与done_gate白名单
> 类型: parallel
> 对应 feature_id: P1-03

## 0. 关联与来源

- 对应 task_key: PP-20260228-AUTO-LARGE-TASK-HOST
- 对应 card_id: C04
- 来源主计划: `docs/内部参考/迭代需求/自动化大型任务开发_主机方案_implementation_plan.md`
- 来源并行计划: `docs/内部参考/任务拆解/2026-02-28_自动化大型任务开发_主机方案/parallel_plan.md`

## 1. 目标

- 本包目标: P1 wt-flow扩展与done_gate白名单 的可执行落地。
- 完成定义（DoD）:
  - wt-flow 新命令可用
  - 主仓 dirty 时 merge 路径 fail-fast 生效

### 1.1 功能机制

  - 新增 next/verify/list 子命令支撑串行推进
  - verify 仅允许白名单命令前缀执行
  - 主仓 dirty 默认 fail-fast，禁止自动污染主线

### 1.2 代码锚点

  - scripts/wt-flow.sh::cmd_create
  - scripts/wt-flow.sh::cmd_merge
  - scripts/wt-flow.sh::main

- 来源证据:
  - docs/内部参考/迭代需求/自动化大型任务开发设计方案.md#63-next-子命令

## 2. 文件边界

### 可修改（白名单）
  - scripts/wt-flow.sh

### 禁止修改（黑名单）
- 其他 card_id 白名单外文件

## 3. 串行门禁

- 前置卡: C03
- 解锁条件: 前置卡 done_gate 全部通过
- 本 WS 不得推进条件: 前置卡存在 TODO/IN_PROGRESS/BLOCKED

## 4. 测试与验收

- 验收命令:
  - bash scripts/wt-flow.sh status
  - bash scripts/wt-flow.sh guard

## 5. 风险与回滚

- 回滚锚点:
  - WT_FLOW_ALLOW_AUTOCOMMIT=0

## 6. card_export

```yaml
card_export:
  id: WS-C04
  card_id: C04
  feature_ids: ['P1-03']
  card_key: PP-20260228-AUTO-LARGE-TASK-HOST::WS-C04
  title: P1 wt-flow扩展与done_gate白名单
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  hard_depends_on: ['C03']
  depends_on: ['C03']
  file_whitelist:
  - scripts/wt-flow.sh
  mechanism_summary:
  - 新增 next/verify/list 子命令支撑串行推进
  - verify 仅允许白名单命令前缀执行
  - 主仓 dirty 默认 fail-fast，禁止自动污染主线
  code_anchor_refs:
  - scripts/wt-flow.sh::cmd_create
  - scripts/wt-flow.sh::cmd_merge
  - scripts/wt-flow.sh::main
  acceptance_checks:
  - bash scripts/wt-flow.sh status
  - bash scripts/wt-flow.sh guard
  rollback_anchors:
  - WT_FLOW_ALLOW_AUTOCOMMIT=0
  evidence_entry: docs/内部参考/迭代需求/自动化大型任务开发_主机方案_implementation_plan.md#p1-03-wt-flow-扩展与-done-gate-白名单
  done_gate:
  - wt-flow 新命令可用
  - 主仓 dirty 时 merge 路径 fail-fast 生效
```
