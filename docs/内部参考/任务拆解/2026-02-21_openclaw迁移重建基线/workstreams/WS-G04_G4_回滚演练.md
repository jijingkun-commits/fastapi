# 工作包说明

> WS 编号: WS-G04
> 名称: G-4 回滚演练
> 类型: gate
> 对应 feature_id: G-4

## 0. 关联与来源

- 对应 task_key: PP-20260221-OPENCLAW-REBUILD-BASELINE
- 对应 card_id: G04
- 来源主计划: `docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md`
- 来源并行计划: `docs/内部参考/任务拆解/2026-02-21_openclaw迁移重建基线/parallel_plan.md`

## 1. 目标

- 本包目标: 完成回滚演练 Gate，确保回滚矩阵记录可核验且与发布口径一致。
- 完成定义（DoD）:
  - G-4 回滚演练通过
  - `python3 scripts/docs_guard.py --strict` 通过

### 1.1 功能机制

  - 复核 `WAVE_ROLLBACK_DRILL_MATRIX` 记录完整性
  - 复核 Gate 收口后的发布前回滚可执行性

### 1.2 代码锚点

  - docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md::11.6
  - docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md::4.11

- 来源证据:
  - docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md#11.6

## 2. 文件边界

### 可修改（白名单）
  - docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md
  - docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md
  - docs/内部参考/任务拆解/2026-02-21_openclaw迁移重建基线/vk_cards.json

### 禁止修改（黑名单）
- 其他 card_id 对应白名单外文件

## 3. 串行门禁

- 前置卡: G03
- 解锁条件: G03 `done_gate` 全部通过
- 本 WS 不得推进条件: G03 存在 `TODO/IN_PROGRESS/BLOCKED`

## 4. 测试与验收

- 验收命令:
  - python3 scripts/docs_guard.py --strict

## 5. 风险与回滚

- 回滚锚点:
  - WAVE_ROLLBACK_DRILL_MATRIX

## 6. card_export

```yaml
card_export:
  id: WS-G04
  card_id: G04
  feature_ids: [G-4]
  card_key: PP-20260221-OPENCLAW-REBUILD-BASELINE::WS-G04
  title: G-4 回滚演练
  type: gate
  task_mode: inspection-card
  merge_required: false
  execution_mode: serial
  hard_depends_on: [G03]
  depends_on: [G03]
  file_whitelist:
  - docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md
  - docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md
  - docs/内部参考/任务拆解/2026-02-21_openclaw迁移重建基线/vk_cards.json
  mechanism_summary:
  - WAVE_ROLLBACK_DRILL_MATRIX 记录完整性与可核验性复核
  - Gate 收口后发布前回滚可执行性复核
  code_anchor_refs:
  - docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md::11.6
  - docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md::4.11
  acceptance_checks:
  - python3 scripts/docs_guard.py --strict
  rollback_anchors:
  - WAVE_ROLLBACK_DRILL_MATRIX
  evidence_entry: docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md#11.6
  done_gate:
  - G-4 回滚演练通过
  - python3 scripts/docs_guard.py --strict 通过
```
