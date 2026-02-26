# 工作包说明

> WS 编号: WS-G02
> 名称: G-2 复合任务编排
> 类型: gate-inspection
> 对应 feature_id: G-2

## 0. 关联与来源

- 对应 task_key: PP-20260221-OPENCLAW-REBUILD-BASELINE
- 对应 card_id: G02
- hard_depends_on: G01
- 来源主计划: `docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md`
- 来源卡片清单: `docs/内部参考/任务拆解/2026-02-21_openclaw迁移重建基线/vk_cards.json`

## 1. 目标

- 复核 `hard_depends_on` 链路在文档、卡片与看板的一致性。
- 复核 `single_active_card=true` 的串行约束未被破坏。
- 产出可追溯证据并回填到 `evidence_entry` 指定位置。

### 1.1 复核范围

- 文档链路：`openclaw迁移重建基线_implementation_plan.md` 第 6/7 节的依赖与 planning_contract 口径。
- 卡片链路：`vk_cards.json` 的 `G02` 字段集（`task_mode/merge_required/hard_depends_on/acceptance_checks`）。
- 看板链路：真实看板卡描述中机器字段与文档字段一致（`card_id=G02`、`hard_depends_on=[G01]`）。

### 1.2 代码/文档锚点

- docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md::6
- docs/内部参考/任务拆解/2026-02-21_openclaw迁移重建基线/vk_cards.json

- 来源证据：
  - docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md#7

## 2. 文件边界

### 可修改（白名单）

- docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md
- docs/内部参考/任务拆解/2026-02-21_openclaw迁移重建基线/vk_cards.json
- docs/内部参考/任务拆解/2026-02-21_openclaw迁移重建基线/workstreams/WS-G02_G2_复合任务编排.md
- docs/SUMMARY.md

### 禁止修改（黑名单）

- 运行时实现代码与非本卡相关测试文件。

## 3. 串行门禁

- 前置卡：G01
- 解锁条件：G01 已完成并完成 `hard_depends_on` 口径回填。
- 本 WS 不得推进条件：G01 处于 `TODO/IN_PROGRESS/IN_REVIEW/BLOCKED`。
- 串行保护要求：`card_order` 维持 `C01~C06` 不变，避免破坏 `single_active_card=true` 的主链执行。

## 4. 测试与验收

- 验收命令：
  - python3 scripts/docs_guard.py --strict

- 人工复核清单：
  - 文档/卡片/看板中的 `hard_depends_on=[G01]` 一致。
  - 文档/卡片中的 `single_active_card=true` 一致。
  - `inspection-card` 与 `merge_required=false` 口径一致。

## 5. 风险与回滚

- 回滚锚点：
  - WAVE_ROLLBACK_DRILL_MATRIX

- 回滚动作：
  - 回退 `implementation_plan` 第 6/7 节与 `vk_cards.json` 中 G02 相关增量。

## 6. card_export

```yaml
card_export:
  id: WS-G02
  card_id: G02
  feature_ids: [G-2]
  card_key: PP-20260221-OPENCLAW-REBUILD-BASELINE::WS-G02
  title: G-2 复合任务编排
  type: gate-inspection
  task_mode: inspection-card
  merge_required: false
  execution_mode: serial
  hard_depends_on: [G01]
  depends_on: [G01]
  file_whitelist:
  - docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md
  - docs/内部参考/任务拆解/2026-02-21_openclaw迁移重建基线/vk_cards.json
  - docs/内部参考/任务拆解/2026-02-21_openclaw迁移重建基线/workstreams/WS-G02_G2_复合任务编排.md
  - docs/SUMMARY.md
  mechanism_summary:
  - 复核 hard_depends_on 链路在文档、卡片与看板的一致性
  - 复核 single_active_card 串行约束未被破坏
  code_anchor_refs:
  - docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md::6
  - docs/内部参考/任务拆解/2026-02-21_openclaw迁移重建基线/vk_cards.json
  acceptance_checks:
  - python3 scripts/docs_guard.py --strict
  rollback_anchors:
  - WAVE_ROLLBACK_DRILL_MATRIX
  evidence_entry: docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md#7
  done_gate:
  - G01 完成后触发 G02 复核
  - hard_depends_on 链路在文档、卡片、看板一致
  - single_active_card 维持 true 且未出现并发激活破坏
```
