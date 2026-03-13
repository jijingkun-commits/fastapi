# WS-C06 C06 P2 TTL归档与过程文件裁剪

> WS 编号: `WS-C06`
> 对应卡片: `C06`
> 类型: `parallel`
> 对应 `feature_id`: `P2-ttl-archive`

## 0. 关联与来源

- 对应 `task_key`: `PP-20260306-workflow-gate-retirement`
- PR 归属: `PR-03` / `codex/workflow-gate-retirement-pr-03`

## 1. 目标

- 按生命周期 + TTL 归档过程文件
- 仅处理 `done/archived` 且 14 天未写入项
- 明确排除活跃任务与真理源文件

## 2. 测试与验收

- 最小测试集:
  - `cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode ttl-audit --task-split-dir workdocs/任务拆解 --ttl-days 14 --output -`
- 验收标准:
  - TTL 归档仅作用于 `done/archived`
  - 活跃任务与真理源文件零误伤

## 3. card_export（机读）

```yaml
card_export:
  id: WS-C06
  feature_id: P2-ttl-archive
  card_key: PP-20260306-workflow-gate-retirement::WS-C06
  title: C06 P2 TTL归档与过程文件裁剪
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  lane: lane-ttl-archive
  hard_depends_on: [C05]
  soft_depends_on: []
  depends_on: [C05]
  file_whitelist:
    - scripts/check_workflow_contract.py
    - workdocs/任务拆解
  mechanism_summary:
    - 按生命周期 + TTL 归档过程文件
    - 保护活跃任务与真理源
  acceptance_checks:
    - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode ttl-audit --task-split-dir workdocs/任务拆解 --ttl-days 14 --output -
  rollback_anchors:
    - WORKFLOW_ARTIFACT_TTL_CLEANUP_ENABLED=false
  evidence_entry: workdocs/归档/实施计划/workflow-gate-retirement_implementation_plan.md
  check_cmd:
    - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode ttl-audit --task-split-dir workdocs/任务拆解 --ttl-days 14 --output -
  done_gate:
    - TTL 归档仅作用于 done/archived
    - 活跃任务与真理源文件零误伤
  source_ws_file: workdocs/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C06_P2_TTL归档与过程文件裁剪.md
```
