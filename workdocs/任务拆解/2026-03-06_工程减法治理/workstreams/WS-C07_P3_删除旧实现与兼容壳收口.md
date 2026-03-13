# WS-C07 C07 P3 删除旧实现与兼容壳收口

> WS 编号: `WS-C07`
> 对应卡片: `C07`
> 类型: `parallel`
> 对应 `feature_id`: `P3-retire-legacy`

## 0. 关联与来源

- 对应 `task_key`: `PP-20260306-workflow-gate-retirement`
- PR 归属: `PR-04` / `codex/workflow-gate-retirement-pr-04`

## 1. 目标

- 在满足零调用与验收前提后删除旧实现
- 必要时保留极薄兼容壳
- 完成删除后的 pre-merge 收口放行

## 2. 测试与验收

- 最小测试集:
  - `cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode full-gate --task-split-dir workdocs/任务拆解/2026-03-06_工程减法治理 --baseline master --output -`
- 验收标准:
  - 旧实现删除或收敛为极薄兼容壳
  - 删除后 pre-merge 收口门禁通过

## 3. card_export（机读）

```yaml
card_export:
  id: WS-C07
  feature_id: P3-retire-legacy
  card_key: PP-20260306-workflow-gate-retirement::WS-C07
  title: C07 P3 删除旧实现与兼容壳收口
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  lane: lane-retire-legacy
  hard_depends_on: [C06]
  soft_depends_on: []
  depends_on: [C06]
  file_whitelist:
    - scripts
    - .cursor/commands
    - .agents/skills
    - docs
  mechanism_summary:
    - 删除旧实现或收敛为极薄兼容壳
    - 完成全链路回归验收
    - 确保可快速回退
  acceptance_checks:
    - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode full-gate --task-split-dir workdocs/任务拆解/2026-03-06_工程减法治理 --baseline master --output -
  rollback_anchors:
    - WORKFLOW_GATE_UNIFIED_ENABLED=false
  evidence_entry: workdocs/归档/正文/实施计划/workflow-gate-retirement_implementation_plan.md
  check_cmd:
    - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode full-gate --task-split-dir workdocs/任务拆解/2026-03-06_工程减法治理 --baseline master --output -
  done_gate:
    - 旧实现删除或收敛为极薄兼容壳
    - 删除后 pre-merge 收口门禁通过
  source_ws_file: workdocs/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C07_P3_删除旧实现与兼容壳收口.md
```
