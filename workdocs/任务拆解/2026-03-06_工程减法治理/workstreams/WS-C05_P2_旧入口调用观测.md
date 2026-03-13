# WS-C05 C05 P2 旧入口调用观测

> WS 编号: `WS-C05`
> 对应卡片: `C05`
> 类型: `parallel`
> 对应 `feature_id`: `P2-usage-observability`

## 0. 关联与来源

- 对应 `task_key`: `PP-20260306-workflow-gate-retirement`
- PR 归属: `PR-03` / `codex/workflow-gate-retirement-pr-03`

## 1. 目标

- 为旧入口调用建立运行态日志台账
- 支持 legacy 调用聚合判定
- 为退役放行导出可提交证据

## 2. 测试与验收

- 最小测试集:
  - `cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode usage-report --log-path logs/workflow-gate-usage.jsonl --report-output workdocs/任务拆解/2026-03-06_工程减法治理/evidence/workflow-gate-usage-report.json`
- 验收标准:
  - `workdocs/任务拆解/2026-03-06_工程减法治理/evidence/workflow-gate-usage-report.json` 已生成
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
    - workdocs/任务拆解/2026-03-06_工程减法治理/evidence/workflow-gate-usage-report.json
  mechanism_summary:
    - 旧入口 usage 运行日志落盘
    - 支持 legacy 调用聚合
  acceptance_checks:
    - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode usage-report --log-path logs/workflow-gate-usage.jsonl --report-output workdocs/任务拆解/2026-03-06_工程减法治理/evidence/workflow-gate-usage-report.json
  rollback_anchors:
    - WORKFLOW_GATE_UNIFIED_ENABLED=false
  evidence_entry: workdocs/归档/实施计划/workflow-gate-retirement_implementation_plan.md
  check_cmd:
    - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode usage-report --log-path logs/workflow-gate-usage.jsonl --report-output workdocs/任务拆解/2026-03-06_工程减法治理/evidence/workflow-gate-usage-report.json
  done_gate:
    - workdocs/任务拆解/2026-03-06_工程减法治理/evidence/workflow-gate-usage-report.json 已生成
    - 支持 legacy 调用聚合判定
  source_ws_file: workdocs/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C05_P2_旧入口调用观测.md
```
