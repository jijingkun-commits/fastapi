# WS-C01 C01 P0 冻结删除口径与执行清单

> WS 编号: `WS-C01`
> 对应卡片: `C01`
> 类型: `parallel`
> 对应 `feature_id`: `P0-freeze-governance`

## 0. 关联与来源

- 对应 `task_key`: `PP-20260306-workflow-gate-retirement`
- 来源主计划: `docs/内部参考/迭代需求/workflow-gate-retirement_implementation_plan.md`
- 来源并行计划: `docs/内部参考/任务拆解/2026-03-06_工程减法治理/parallel_plan.md`
- card_key: `PP-20260306-workflow-gate-retirement::WS-C01`
- PR 归属: `PR-01` / `codex/workflow-gate-retirement-pr-01`

## 1. 目标

- 冻结原报告中的直接删除口径
- 统一团队执行基线到 `v3`
- 形成不可误解的 `NO-GO` 清单

## 2. 文件边界

### 可修改（白名单）
- `docs/内部参考/工程减法体检报告_2026-03-06.md`
- `docs/内部参考/工程减法体检报告_2026-03-06_v3.md`
- `docs/内部参考/工程减法治理看板模板_2026-03-06.md`

## 3. 测试与验收

- 最小测试集:
  - `cd /Users/jijingkun/bojxAI/fastapi && rg -n "NO-GO|rm scripts/check_\*\.py" docs/内部参考/工程减法体检报告_2026-03-06.md docs/内部参考/工程减法体检报告_2026-03-06_v3.md`
- 验收标准:
  - `NO-GO` 文案明确
  - 团队不再执行 `rm scripts/check_*.py`

## 4. card_export（机读）

```yaml
card_export:
  id: WS-C01
  feature_id: P0-freeze-governance
  card_key: PP-20260306-workflow-gate-retirement::WS-C01
  title: C01 P0 冻结删除口径与执行清单
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  lane: lane-governance
  hard_depends_on: []
  soft_depends_on: []
  depends_on: []
  file_whitelist:
    - docs/内部参考/工程减法体检报告_2026-03-06.md
    - docs/内部参考/工程减法体检报告_2026-03-06_v3.md
    - docs/内部参考/工程减法治理看板模板_2026-03-06.md
  mechanism_summary:
    - 冻结 rm 删除口径
    - 统一 NO-GO 执行清单
    - 用 v3 口径替代直接删除建议
  code_anchor_refs:
    - docs/内部参考/工程减法体检报告_2026-03-06.md::3.1
    - docs/内部参考/工程减法体检报告_2026-03-06_v3.md::6
  acceptance_checks:
    - cd /Users/jijingkun/bojxAI/fastapi && rg -n "NO-GO|rm scripts/check_\*\.py" docs/内部参考/工程减法体检报告_2026-03-06.md docs/内部参考/工程减法体检报告_2026-03-06_v3.md
  rollback_anchors:
    - WORKFLOW_GATE_UNIFIED_ENABLED=false
  evidence_entry: docs/内部参考/迭代需求/workflow-gate-retirement_implementation_plan.md
  check_cmd:
    - cd /Users/jijingkun/bojxAI/fastapi && rg -n "NO-GO|rm scripts/check_\*\.py" docs/内部参考/工程减法体检报告_2026-03-06.md docs/内部参考/工程减法体检报告_2026-03-06_v3.md
  done_gate:
    - NO-GO 删除口径冻结完成
    - 团队停用 rm scripts/check_*.py
  source_ws_file: docs/内部参考/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C01_P0_冻结删除口径与执行清单.md
```
