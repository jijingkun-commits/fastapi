# 工作包说明

> WS 编号: WS-G04
> 名称: G-4 回滚演练
> 类型: gate-inspection
> 对应 feature_id: G-4

## 0. 关联与来源

- 对应 task_key: PP-20260221-OPENCLAW-REBUILD-BASELINE
- 对应 card_id: G04
- hard_depends_on: G03
- 来源主计划: `docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md`
- 来源卡片清单: `docs/内部参考/任务拆解/2026-02-21_openclaw迁移重建基线/vk_cards.json`

## 1. 目标

- 复核 `WAVE_ROLLBACK_DRILL_MATRIX` 记录完整性。
- 复核 Gate 收口后的发布前回滚可执行性。
- 产出可追溯证据并回填到 `evidence_entry` 指定位置。

### 1.1 复核范围

- 矩阵链路：`迁移执行波次_implementation_plan.md` 第 `11.6` 节，检查 `P1~P6` 回滚矩阵字段完整性与无占位符。
- Gate 链路：`迁移执行波次_implementation_plan.md` 第 `11.5` 节 `G-4` 状态口径与“下一步”发布前演练动作。
- 收口链路：`openclaw迁移重建基线_implementation_plan.md` 第 `4.11` 节，检查回滚锚点是否绑定 `WAVE_ROLLBACK_DRILL_MATRIX` 与 `docs_guard` 验证命令。

### 1.2 代码/文档锚点

- docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md::11.6
- docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md::4.11

- 来源证据：
  - docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md#11.6

## 2. 文件边界

### 可修改（白名单）

- docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md
- docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md
- docs/内部参考/任务拆解/2026-02-21_openclaw迁移重建基线/vk_cards.json
- docs/内部参考/任务拆解/2026-02-21_openclaw迁移重建基线/workstreams/WS-G04_G4_回滚演练.md
- docs/SUMMARY.md

### 禁止修改（黑名单）

- 运行时实现代码与非本卡相关测试文件。

## 3. 串行门禁

- 前置卡：G03
- 解锁条件：G03 完成并通过契约一致性复核。
- 本 WS 不得推进条件：G03 处于 `TODO/IN_PROGRESS/IN_REVIEW/BLOCKED`。
- 串行保护要求：Gate 链保持 `G01 -> G02 -> G03 -> G04`，不得破坏 `single_active_card=true`。

## 4. 测试与验收

- 验收命令：
  - python3 scripts/docs_guard.py --strict

- 人工复核清单：
  - `11.6 WAVE_ROLLBACK_DRILL_MATRIX` 含 `P1~P6` 全量 6 行，且每行四要素完整（组合回滚锚点/演练批次/恢复结果/证据链接）。
  - `11.5` 中 `G-4` 状态为已通过，且下一步仍固定为发布前回滚演练清单。
  - `4.11` 已声明回滚锚点 `WAVE_ROLLBACK_DRILL_MATRIX`，并绑定 `python3 scripts/docs_guard.py --strict`。

## 5. 风险与回滚

- 回滚锚点：
  - WAVE_ROLLBACK_DRILL_MATRIX

- 回滚动作：
  - 回退 `11.6` 矩阵与 `11.6.1` 复核记录增量。
  - 回退 `4.11` 中与 Gate 回滚口径相关的增量。

## 6. card_export

```yaml
card_export:
  id: WS-G04
  card_id: G04
  feature_ids: [G-4]
  card_key: PP-20260221-OPENCLAW-REBUILD-BASELINE::WS-G04
  title: G-4 回滚演练
  type: gate-inspection
  task_mode: inspection-card
  merge_required: false
  execution_mode: serial
  hard_depends_on: [G03]
  depends_on: [G03]
  file_whitelist:
  - docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md
  - docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md
  - docs/内部参考/任务拆解/2026-02-21_openclaw迁移重建基线/vk_cards.json
  - docs/内部参考/任务拆解/2026-02-21_openclaw迁移重建基线/workstreams/WS-G04_G4_回滚演练.md
  - docs/SUMMARY.md
  mechanism_summary:
  - 复核 WAVE_ROLLBACK_DRILL_MATRIX 记录完整性
  - 复核 Gate 收口后的发布前回滚可执行性
  code_anchor_refs:
  - docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md::11.6
  - docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md::4.11
  acceptance_checks:
  - python3 scripts/docs_guard.py --strict
  rollback_anchors:
  - WAVE_ROLLBACK_DRILL_MATRIX
  evidence_entry: docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md#11.6
  done_gate:
  - G-4 回滚演练通过（WAVE_ROLLBACK_DRILL_MATRIX 有可核验记录）
  - python3 scripts/docs_guard.py --strict 通过
```
