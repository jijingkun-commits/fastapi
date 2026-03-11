# 工作包说明

> WS 编号: WS-G03
> 名称: G-3 迁移一致性闭环
> 类型: gate
> 对应 feature_id: G-3

## 0. 关联与来源

- 对应 task_key: PP-20260228-AUTO-LARGE-TASK-HOST
- 对应 card_id: G03
- 来源主计划: `docs/内部参考/迭代需求/自动化大型任务开发_主机方案_implementation_plan.md`
- 来源并行计划: `workdocs/任务拆解/2026-02-28_自动化大型任务开发_主机方案/parallel_plan.md`

## 1. 目标

- 本包目标: G-3 迁移一致性闭环 的可执行落地。
- 完成定义（DoD）:
  - 迁移 checklist 与拆解契约双向校验 PASS

### 1.1 功能机制

  - 校验 payload 迁移 31 项映射完整性
  - 校验 planning_contract、parallel_plan、vk_cards 三方一致

### 1.2 代码锚点

  - docs/内部参考/迭代需求/自动化大型任务开发设计方案.md::附录 B.4
  - workdocs/任务拆解/2026-02-28_自动化大型任务开发_主机方案/contracts/vk_cards.json

- 来源证据:
  - docs/内部参考/迭代需求/自动化大型任务开发_全量打钩板清单.md#32-p2-exit-gate必须全绿

## 2. 文件边界

### 可修改（白名单）
  - docs/内部参考/迭代需求/自动化大型任务开发设计方案.md
  - workdocs/任务拆解/2026-02-28_自动化大型任务开发_主机方案/contracts/vk_cards.json

### 禁止修改（黑名单）
- 其他 card_id 白名单外文件

## 3. 串行门禁

- 前置卡: G02
- 解锁条件: 前置卡 done_gate 全部通过
- 本 WS 不得推进条件: 前置卡存在 TODO/IN_PROGRESS/BLOCKED

## 4. 测试与验收

- 验收命令:
  - grep -n "待迁移" docs/内部参考/迭代需求/自动化大型任务开发设计方案.md || true
  - python3 scripts/docs_guard.py --strict

## 5. 风险与回滚

- 回滚锚点:
  - ROLLBACK_TO_PLAN_IF_MISMATCH

## 6. card_export

```yaml
card_export:
  id: WS-G03
  card_id: G03
  feature_ids: ['G-3']
  card_key: PP-20260228-AUTO-LARGE-TASK-HOST::WS-G03
  title: G-3 迁移一致性闭环
  type: gate
  task_mode: inspection-card
  merge_required: false
  execution_mode: serial
  hard_depends_on: ['G02']
  depends_on: ['G02']
  file_whitelist:
  - docs/内部参考/迭代需求/自动化大型任务开发设计方案.md
  - workdocs/任务拆解/2026-02-28_自动化大型任务开发_主机方案/contracts/vk_cards.json
  mechanism_summary:
  - 校验 payload 迁移 31 项映射完整性
  - 校验 planning_contract、parallel_plan、vk_cards 三方一致
  code_anchor_refs:
  - docs/内部参考/迭代需求/自动化大型任务开发设计方案.md::附录 B.4
  - workdocs/任务拆解/2026-02-28_自动化大型任务开发_主机方案/contracts/vk_cards.json
  acceptance_checks:
  - grep -n "待迁移" docs/内部参考/迭代需求/自动化大型任务开发设计方案.md || true
  - python3 scripts/docs_guard.py --strict
  rollback_anchors:
  - ROLLBACK_TO_PLAN_IF_MISMATCH
  evidence_entry: docs/内部参考/迭代需求/自动化大型任务开发_全量打钩板清单.md#32-p2-exit-gate必须全绿
  done_gate:
  - 迁移 checklist 与拆解契约双向校验 PASS
```
