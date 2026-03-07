# WS-C05 C05 P2 旧入口调用观测

> WS 编号: `WS-C05`
> 对应卡片: `C05`
> 类型: `parallel`
> 对应 `feature_id`: `P2-usage-observability`

## 0. 关联与来源

- 对应 `task_key`: `PP-20260306-workflow-gate-retirement`
- PR 归属: `PR-03` / `codex/workflow-gate-retirement-pr-03`

## 1. 目标

- 为旧入口调用建立日志台账
- 支持 legacy 调用聚合判定
- 为退役放行提供证据源

## 2. 测试与验收

- 最小测试集:
  - `cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode usage-report --output logs/workflow-gate-usage.jsonl`
- 验收标准:
  - `workflow-gate-usage` 日志开始落盘
  - 支持 legacy 调用聚合判定

## 3. card_export（机读）

```yaml
card_export:
  id: WS-C05
  feature_id: P2-usage-observability
  card_key: PP-20260306-workflow-gate-retirement::WS-C05
  title: C05 P2 旧入口调用观测
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  lane: lane-observability
  hard_depends_on: [C04]
  soft_depends_on: []
  depends_on: [C04]
  file_whitelist:
    - scripts/check_workflow_contract.py
    - logs/workflow-gate-usage.jsonl
  mechanism_summary:
    - 旧入口 usage 日志落盘
    - 支持 legacy 调用聚合
  acceptance_checks:
    - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode usage-report --output logs/workflow-gate-usage.jsonl
  rollback_anchors:
    - WORKFLOW_GATE_UNIFIED_ENABLED=false
  evidence_entry: docs/内部参考/迭代需求/workflow-gate-retirement_implementation_plan.md
  check_cmd:
    - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode usage-report --output logs/workflow-gate-usage.jsonl
  done_gate:
    - workflow-gate-usage 日志开始落盘
    - 支持 legacy 调用聚合判定
  source_ws_file: docs/内部参考/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C05_P2_旧入口调用观测.md
```
