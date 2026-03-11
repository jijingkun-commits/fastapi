# 工作包说明

> WS 编号: WS-C06
> 名称: P6 收口与回滚演练
> 类型: parallel
> 对应 feature_id: P6-01

## 0. 关联与来源

- 对应 task_key: PP-20260221-OPENCLAW-REBUILD-BASELINE
- 对应 card_id: C06
- 来源主计划: `docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md`
- 来源并行计划: `workdocs/任务拆解/2026-02-21_openclaw迁移重建基线/parallel_plan.md`

## 1. 目标

- 本包目标: P6 收口与回滚演练 的可执行落地。
- 完成定义（DoD）:
  - G-1~G-4 全部通过
  - docs/code/test 三线收口完成
  - 各 Wave 回滚锚点组合演练通过

### 1.1 功能机制

  - G-1~G-4 门禁收口与证据链复核
  - docs/code/test 三线收口
  - 波次级回滚锚点组合演练

### 1.2 代码锚点

  - docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md::11.2
  - docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md::11.5
  - scripts/docs_guard.py::main

- 来源证据:
  - docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md#4.11

## 2. 文件边界

### 可修改（白名单）
  - docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md
  - docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md
  - docs/SUMMARY.md
  - scripts/docs_guard.py

### 禁止修改（黑名单）
- 其他 card_id 对应白名单外文件

## 3. 串行门禁

- 前置卡: C01, C02, C03, C04, C05
- 解锁条件: 前置卡 `done_gate` 全部通过
- 本 WS 不得推进条件: 前置卡存在 `TODO/IN_PROGRESS/BLOCKED`

## 4. 测试与验收

- 验收命令:
  - python3 scripts/docs_guard.py --strict

## 5. 风险与回滚

- 回滚锚点:
  - WAVE_ROLLBACK_DRILL_MATRIX

## 6. card_export

```yaml
card_export:
  id: WS-C06
  card_id: C06
  feature_ids: [P6-01]
  card_key: PP-20260221-OPENCLAW-REBUILD-BASELINE::WS-C06
  title: P6 收口与回滚演练
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  hard_depends_on: [C01, C02, C03, C04, C05]
  depends_on: [C01, C02, C03, C04, C05]
  file_whitelist:
  - docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md
  - docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md
  - docs/SUMMARY.md
  - scripts/docs_guard.py
  mechanism_summary:
  - G-1~G-4 门禁收口与证据链复核
  - docs/code/test 三线收口
  - 波次级回滚锚点组合演练
  code_anchor_refs:
  - docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md::11.2
  - docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md::11.5
  - scripts/docs_guard.py::main
  acceptance_checks:
  - python3 scripts/docs_guard.py --strict
  rollback_anchors:
  - WAVE_ROLLBACK_DRILL_MATRIX
  evidence_entry: docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md#4.11
  done_gate:
  - G-1~G-4 全部通过
  - docs/code/test 三线收口完成
  - 各 Wave 回滚锚点组合演练通过
```
