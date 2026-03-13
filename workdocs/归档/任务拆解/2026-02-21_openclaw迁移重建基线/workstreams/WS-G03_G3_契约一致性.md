# 工作包说明

> WS 编号: WS-G03
> 名称: G-3 契约一致性
> 类型: inspection-card
> 对应 feature_id: G-3

## 0. 关联与来源

- 对应 task_key: PP-20260221-OPENCLAW-REBUILD-BASELINE
- 对应 card_id: G03
- hard_depends_on: G02
- 来源主计划: `workdocs/归档/正文/实施计划/openclaw迁移重建基线_implementation_plan.md`
- 来源并行计划: `workdocs/归档/任务拆解/2026-02-21_openclaw迁移重建基线/parallel_plan.md`
- 来源卡片清单: `workdocs/归档/任务拆解/2026-02-21_openclaw迁移重建基线/contracts/vk_cards.json`

## 1. 目标

- 对齐 `planning_contract / gate_contract / card_order` 三方口径。
- 对齐 `parallel_plan` 与 `vk_cards` 的 Gate 卡定义，消除字段漂移。
- 在不改变主实现链（`C01~C06`）的前提下，保证 inspection 链可被自动执行器稳定消费。

### 1.1 复核范围

- contract 口径：`implementation_plan.md` 第 7 节中的 `planning_contract` 与 `gate_contract`。
- 执行口径：`parallel_plan.md` 第 `-1` 节中的 `card_order` 与 Gate 工作包总览。
- 看板口径：`vk_cards.json` 的 `card_order` 与 `G01/G02/G03` 卡片定义字段集。

### 1.2 代码/文档锚点

- workdocs/归档/正文/实施计划/openclaw迁移重建基线_implementation_plan.md::7
- workdocs/归档/任务拆解/2026-02-21_openclaw迁移重建基线/parallel_plan.md
- workdocs/归档/任务拆解/2026-02-21_openclaw迁移重建基线/contracts/vk_cards.json

- 来源证据：
  - workdocs/归档/任务拆解/2026-02-21_openclaw迁移重建基线/parallel_plan.md#-1

## 2. 文件边界

### 可修改（白名单）

- workdocs/归档/正文/实施计划/openclaw迁移重建基线_implementation_plan.md
- workdocs/归档/任务拆解/2026-02-21_openclaw迁移重建基线/parallel_plan.md
- workdocs/归档/任务拆解/2026-02-21_openclaw迁移重建基线/contracts/vk_cards.json
- workdocs/归档/任务拆解/2026-02-21_openclaw迁移重建基线/workstreams/WS-G03_G3_契约一致性.md
- docs/SUMMARY.md

### 禁止修改（黑名单）

- 运行时实现代码与非 Gate 卡文档。

## 3. 串行门禁

- 前置卡：G02
- 解锁条件：G02 完成并通过 `hard_depends_on`/`single_active_card` 复核。
- 本 WS 不得推进条件：G02 处于 `TODO/IN_PROGRESS/IN_REVIEW/BLOCKED`。
- 串行保护要求：`card_order` 固定为 `C01~C06 + G01~G03`，不得出现跨链并发激活。

## 4. 测试与验收

- 验收命令：
  - python3 scripts/docs_guard.py --strict

- 人工复核清单：
  - `planning_contract` 与 `gate_contract` 的 Gate 卡定义一致。
  - `parallel_plan.card_order` 与 `vk_cards.card_order` 一致。
  - `G01/G02/G03` 在 `parallel_plan` 与 `vk_cards` 的字段口径一致（依赖、任务模式、回滚锚点、证据入口）。

## 5. 风险与回滚

- 回滚锚点：
  - WAVE_ROLLBACK_DRILL_MATRIX

- 回滚动作：
  - 回退 `implementation_plan` 第 7 节 contract 变更。
  - 回退 `parallel_plan` 与 `vk_cards` 中 Gate 卡定义增量。

## 6. card_export

```yaml
card_export:
  id: WS-G03
  card_id: G03
  feature_ids: [G-3]
  card_key: PP-20260221-OPENCLAW-REBUILD-BASELINE::WS-G03
  title: G-3 契约一致性
  type: inspection-card
  task_mode: inspection-card
  merge_required: false
  execution_mode: serial
  hard_depends_on: [G02]
  depends_on: [G02]
  file_whitelist:
  - workdocs/归档/正文/实施计划/openclaw迁移重建基线_implementation_plan.md
  - workdocs/归档/任务拆解/2026-02-21_openclaw迁移重建基线/parallel_plan.md
  - workdocs/归档/任务拆解/2026-02-21_openclaw迁移重建基线/contracts/vk_cards.json
  - workdocs/归档/任务拆解/2026-02-21_openclaw迁移重建基线/workstreams/WS-G03_G3_契约一致性.md
  - docs/SUMMARY.md
  mechanism_summary:
  - 对齐 planning_contract / gate_contract / card_order
  - 对齐 parallel_plan 与 vk_cards 的 Gate 卡定义
  code_anchor_refs:
  - workdocs/归档/正文/实施计划/openclaw迁移重建基线_implementation_plan.md::7
  - workdocs/归档/任务拆解/2026-02-21_openclaw迁移重建基线/parallel_plan.md
  - workdocs/归档/任务拆解/2026-02-21_openclaw迁移重建基线/contracts/vk_cards.json
  acceptance_checks:
  - python3 scripts/docs_guard.py --strict
  rollback_anchors:
  - WAVE_ROLLBACK_DRILL_MATRIX
  evidence_entry: workdocs/归档/任务拆解/2026-02-21_openclaw迁移重建基线/parallel_plan.md#-1
  done_gate:
  - planning_contract / gate_contract / card_order 三方口径一致
  - parallel_plan 与 vk_cards 的 Gate 卡定义一致
  - python3 scripts/docs_guard.py --strict 通过
```
