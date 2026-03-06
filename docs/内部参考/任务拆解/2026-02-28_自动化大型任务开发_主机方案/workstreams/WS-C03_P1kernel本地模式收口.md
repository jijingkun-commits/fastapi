# 工作包说明

> WS 编号: WS-C03
> 名称: P1 kernel本地模式收口
> 类型: parallel
> 对应 feature_id: P1-02

## 0. 关联与来源

- 对应 task_key: PP-20260228-AUTO-LARGE-TASK-HOST
- 对应 card_id: C03
- 来源主计划: `docs/内部参考/迭代需求/自动化大型任务开发_主机方案_implementation_plan.md`
- 来源并行计划: `docs/内部参考/任务拆解/2026-02-28_自动化大型任务开发_主机方案/parallel_plan.md`

## 1. 目标

- 本包目标: P1 kernel本地模式收口 的可执行落地。
- 完成定义（DoD）:
  - local-mode 路径不依赖 VK 读取
  - CARD_DONE 后可自动触发下一轮 wake

### 1.1 功能机制

  - load_context 在 local-mode 下只读取本地状态
  - seed/activate 写本地状态，不再依赖 VK API 写入
  - 卡片完成后 trigger_next_round 立即唤醒下一轮

### 1.2 代码锚点

  - scripts/coder4/coder4_bootstrap_kernel.py::build_kernel_context
  - scripts/coder4/coder4_bootstrap_kernel.py::apply_action
  - scripts/coder4/coder4_bootstrap_kernel.py::main

- 来源证据:
  - docs/内部参考/迭代需求/自动化大型任务开发_主机方案_implementation_plan.md#p1-02-kernel-本地模式收口

## 2. 文件边界

### 可修改（白名单）
  - scripts/coder4/coder4_bootstrap_kernel.py

### 禁止修改（黑名单）
- 其他 card_id 白名单外文件

## 3. 串行门禁

- 前置卡: C02
- 解锁条件: 前置卡 done_gate 全部通过
- 本 WS 不得推进条件: 前置卡存在 TODO/IN_PROGRESS/BLOCKED

## 4. 测试与验收

- 验收命令:
  - python3 scripts/coder4/coder4_bootstrap_kernel.py --local-mode --apply-bootstrap --active-task docs/内部参考/任务拆解/2026-02-28_自动化大型任务开发_主机方案/_active_task.json

## 5. 风险与回滚

- 回滚锚点:
  - DISABLE_AUTO_WAKE

## 6. card_export

```yaml
card_export:
  id: WS-C03
  card_id: C03
  feature_ids: ['P1-02']
  card_key: PP-20260228-AUTO-LARGE-TASK-HOST::WS-C03
  title: P1 kernel本地模式收口
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  hard_depends_on: ['C02']
  depends_on: ['C02']
  file_whitelist:
  - scripts/coder4/coder4_bootstrap_kernel.py
  mechanism_summary:
  - load_context 在 local-mode 下只读取本地状态
  - seed/activate 写本地状态，不再依赖 VK API 写入
  - 卡片完成后 trigger_next_round 立即唤醒下一轮
  code_anchor_refs:
  - scripts/coder4/coder4_bootstrap_kernel.py::build_kernel_context
  - scripts/coder4/coder4_bootstrap_kernel.py::apply_action
  - scripts/coder4/coder4_bootstrap_kernel.py::main
  acceptance_checks:
  - python3 scripts/coder4/coder4_bootstrap_kernel.py --local-mode --apply-bootstrap --active-task docs/内部参考/任务拆解/2026-02-28_自动化大型任务开发_主机方案/_active_task.json
  rollback_anchors:
  - DISABLE_AUTO_WAKE
  evidence_entry: docs/内部参考/迭代需求/自动化大型任务开发_主机方案_implementation_plan.md#p1-02-kernel-本地模式收口
  done_gate:
  - local-mode 路径不依赖 VK 读取
  - CARD_DONE 后可自动触发下一轮 wake
```
