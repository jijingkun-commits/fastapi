# 工作包说明

> WS 编号: WS-G01
> 名称: G-1 实测证据闭环
> 类型: inspection
> 对应 feature_id: G-1

## 0. 关联与来源

- 对应 task_key: PP-20260221-OPENCLAW-REBUILD-BASELINE
- 对应 card_id: G01
- 来源主计划: `docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md`
- 来源并行计划: `workdocs/任务拆解/2026-02-21_openclaw迁移重建基线/parallel_plan.md`

## 1. 目标

- 本包目标: G-1 实测证据闭环的最终核验与留痕固化。
- 完成定义（DoD）:
  - evidence 四元组 `task_id/turn_id/process_id/status` 全量回填并可核验
  - 证据绑定关系满足 `target_task_id == evidence_task_id`
  - `python3 scripts/docs_guard.py --strict` 通过

### 1.1 功能机制

  - 固化并核验 evidence 四元组（`task_id/turn_id/process_id/status`）
  - 复核证据绑定 `target_task_id == evidence_task_id`
  - 若绑定不一致或四元组缺失，保持阻断并返回 `BLOCKED_EVIDENCE_GAP`

### 1.2 代码锚点

  - docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md::4.11
  - docs/开发文档/工作流/Coder4自动执行总控手册.md::7
  - scripts/docs_guard.py::check_g01_evidence_binding

- 来源证据:
  - docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md#4.11

## 2. 文件边界

### 可修改（白名单）
  - docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md
  - docs/开发文档/工作流/Coder4自动执行总控手册.md
  - docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md
  - workdocs/任务拆解/2026-02-21_openclaw迁移重建基线/parallel_plan.md
  - workdocs/任务拆解/2026-02-21_openclaw迁移重建基线/contracts/vk_cards.json
  - workdocs/任务拆解/2026-02-21_openclaw迁移重建基线/workstreams/WS-G01_G1_实测证据闭环.md
  - docs/SUMMARY.md
  - scripts/docs_guard.py

### 禁止修改（黑名单）
- 其他 card_id 对应白名单外文件

## 3. 串行门禁

- 前置卡: C06
- 解锁条件: C06 `done_gate` 全部通过
- 本 WS 不得推进条件: C06 仍处于 `TODO/IN_PROGRESS/BLOCKED`

## 4. 测试与验收

- 验收命令:
  - python3 scripts/docs_guard.py --strict

## 5. 风险与回滚

- 回滚锚点:
  - WAVE_ROLLBACK_DRILL_MATRIX

## 6. 执行证据（四元组与绑定）

### 6.1 证据四元组实测记录

| target_task_id | evidence_task_id | bind_result | task_id | turn_id | process_id | status |
|---|---|---|---|---|---|---|
| `PP-20260221-OPENCLAW-REBUILD-BASELINE::WS-G01` | `PP-20260221-OPENCLAW-REBUILD-BASELINE::WS-G01` | 一致（PASS） | `PP-20260221-OPENCLAW-REBUILD-BASELINE::WS-G01` | `TURN-20260225-G01-001` | `DOCS_GUARD_STRICT_20260225` | 通过（PASS） |

### 6.2 证据绑定复核结论

1. `target_task_id` 与 `evidence_task_id` 一致，绑定通过。
2. 证据四元组全部非空且状态收口为 `PASS`。

## 7. card_export

```yaml
card_export:
  id: WS-G01
  card_id: G01
  feature_ids: [G-1]
  card_key: PP-20260221-OPENCLAW-REBUILD-BASELINE::WS-G01
  title: G-1 实测证据闭环
  type: inspection
  task_mode: inspection-card
  merge_required: false
  execution_mode: serial
  hard_depends_on: [C06]
  depends_on: [C06]
  file_whitelist:
  - docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md
  - docs/开发文档/工作流/Coder4自动执行总控手册.md
  - docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md
  - workdocs/任务拆解/2026-02-21_openclaw迁移重建基线/parallel_plan.md
  - workdocs/任务拆解/2026-02-21_openclaw迁移重建基线/contracts/vk_cards.json
  - workdocs/任务拆解/2026-02-21_openclaw迁移重建基线/workstreams/WS-G01_G1_实测证据闭环.md
  - docs/SUMMARY.md
  - scripts/docs_guard.py
  mechanism_summary:
  - 固化并核验 evidence 四元组（task_id/turn_id/process_id/status）
  - 复核证据绑定 target_task_id == evidence_task_id
  code_anchor_refs:
  - docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md::4.11
  - docs/开发文档/工作流/Coder4自动执行总控手册.md::7
  acceptance_checks:
  - python3 scripts/docs_guard.py --strict
  rollback_anchors:
  - WAVE_ROLLBACK_DRILL_MATRIX
  evidence_entry: docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md#4.11
  done_gate:
  - evidence 四元组 task_id/turn_id/process_id/status 回填并核验通过
  - target_task_id == evidence_task_id 复核通过
  - python3 scripts/docs_guard.py --strict 通过
```
