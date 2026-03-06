# WS-C02 C02 P1 统一入口 check_workflow_contract

> WS 编号: `WS-C02`
> 对应卡片: `C02`
> 类型: `parallel`
> 对应 `feature_id`: `P1-unified-entry`

## 0. 关联与来源

- 对应 `task_key`: `PP-20260306-workflow-gate-retirement`
- PR 归属: `PR-01` / `codex/workflow-gate-retirement-pr-01`
- PR 依赖: `[]`

## 1. 目标

- 新建统一入口 `scripts/check_workflow_contract.py`
- 建立 `--mode` 分发机制
- 统一退出码与结构化结果

## 2. 文件边界

### 可修改（白名单）
- `scripts/check_workflow_contract.py`

## 3. 测试与验收

- 最小测试集:
  - `cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode clarify_plan --requirements-path docs/内部参考/迭代需求/workflow-gate-retirement_requirements.md --implementation-path docs/内部参考/迭代需求/workflow-gate-retirement_implementation_plan.md --output -`
- 验收标准:
  - `clarify_plan` 模式可跑
  - 统一入口能作为唯一推荐入口

## 4. card_export（机读）

```yaml
card_export:
  id: WS-C02
  feature_id: P1-unified-entry
  card_key: PP-20260306-workflow-gate-retirement::WS-C02
  title: C02 P1 统一入口 check_workflow_contract
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  lane: lane-unified-entry
  hard_depends_on: [C01]
  soft_depends_on: []
  depends_on: [C01]
  file_whitelist:
    - scripts/check_workflow_contract.py
  mechanism_summary:
    - 新增统一入口脚本
    - 聚合 4 个 L1 门禁模式
    - 统一退出码与结构化输出
  code_anchor_refs:
    - scripts/check_workflow_contract.py::parse_args
    - scripts/check_workflow_contract.py::MODE_REGISTRY
    - scripts/check_workflow_contract.py::run_mode
  acceptance_checks:
    - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode clarify_plan --requirements-path docs/内部参考/迭代需求/workflow-gate-retirement_requirements.md --implementation-path docs/内部参考/迭代需求/workflow-gate-retirement_implementation_plan.md --output -
  rollback_anchors:
    - WORKFLOW_GATE_UNIFIED_ENABLED=false
  evidence_entry: docs/内部参考/迭代需求/workflow-gate-retirement_implementation_plan.md
  check_cmd:
    - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode clarify_plan --requirements-path docs/内部参考/迭代需求/workflow-gate-retirement_requirements.md --implementation-path docs/内部参考/迭代需求/workflow-gate-retirement_implementation_plan.md --output -
  done_gate:
    - check_workflow_contract 统一入口可执行
    - clarify_plan 模式输出等价结果
  source_ws_file: docs/内部参考/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C02_P1_统一入口check_workflow_contract.md
```
