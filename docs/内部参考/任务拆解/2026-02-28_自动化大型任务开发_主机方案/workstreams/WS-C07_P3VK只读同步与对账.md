# 工作包说明

> WS 编号: WS-C07
> 名称: P3 VK只读同步与对账
> 类型: parallel
> 对应 feature_id: P3-01

## 0. 关联与来源

- 对应 task_key: PP-20260228-AUTO-LARGE-TASK-HOST
- 对应 card_id: C07
- 来源主计划: `docs/内部参考/迭代需求/自动化大型任务开发_主机方案_implementation_plan.md`
- 来源并行计划: `docs/内部参考/任务拆解/2026-02-28_自动化大型任务开发_主机方案/parallel_plan.md`

## 1. 目标

- 本包目标: P3 VK只读同步与对账 的可执行落地。
- 完成定义（DoD）:
  - VK 断连演练时主链路不中断
  - 全量同步任务可完成状态对账

### 1.1 功能机制

  - 状态变更后异步 fire-and-forget 推送 VK
  - 同步失败只记录告警，不阻断执行链路
  - 每小时全量对账保证最终一致性

### 1.2 代码锚点

  - scripts/coder4/coder4_vk_sync.py::sync_to_vk
  - scripts/coder4/coder4_vk_sync.py::sync_all_cards
  - scripts/coder4/coder4_bootstrap_kernel.py::_try_sync_vk

- 来源证据:
  - docs/内部参考/迭代需求/自动化大型任务开发_主机方案_implementation_plan.md#p3-01-vk-只读同步与全量对账

## 2. 文件边界

### 可修改（白名单）
  - scripts/coder4/coder4_vk_sync.py

### 禁止修改（黑名单）
- 其他 card_id 白名单外文件

## 3. 串行门禁

- 前置卡: C06
- 解锁条件: 前置卡 done_gate 全部通过
- 本 WS 不得推进条件: 前置卡存在 TODO/IN_PROGRESS/BLOCKED

## 4. 测试与验收

- 验收命令:
  - python3 scripts/coder4/coder4_vk_sync.py --dry-run

## 5. 风险与回滚

- 回滚锚点:
  - DISABLE_VK_SYNC

## 6. card_export

```yaml
card_export:
  id: WS-C07
  card_id: C07
  feature_ids: ['P3-01']
  card_key: PP-20260228-AUTO-LARGE-TASK-HOST::WS-C07
  title: P3 VK只读同步与对账
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  hard_depends_on: ['C06']
  depends_on: ['C06']
  file_whitelist:
  - scripts/coder4/coder4_vk_sync.py
  mechanism_summary:
  - 状态变更后异步 fire-and-forget 推送 VK
  - 同步失败只记录告警，不阻断执行链路
  - 每小时全量对账保证最终一致性
  code_anchor_refs:
  - scripts/coder4/coder4_vk_sync.py::sync_to_vk
  - scripts/coder4/coder4_vk_sync.py::sync_all_cards
  - scripts/coder4/coder4_bootstrap_kernel.py::_try_sync_vk
  acceptance_checks:
  - python3 scripts/coder4/coder4_vk_sync.py --dry-run
  rollback_anchors:
  - DISABLE_VK_SYNC
  evidence_entry: docs/内部参考/迭代需求/自动化大型任务开发_主机方案_implementation_plan.md#p3-01-vk-只读同步与全量对账
  done_gate:
  - VK 断连演练时主链路不中断
  - 全量同步任务可完成状态对账
```
