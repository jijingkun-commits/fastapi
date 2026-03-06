# WS-C03 C03 P1 L1旧脚本 wrapper 兼容壳

> WS 编号: `WS-C03`
> 对应卡片: `C03`
> 类型: `parallel`
> 对应 `feature_id`: `P1-legacy-wrapper`

## 0. 关联与来源

- 对应 `task_key`: `PP-20260306-workflow-gate-retirement`
- PR 归属: `PR-02` / `codex/workflow-gate-retirement-pr-02`
- PR 依赖: `[PR-01]`

## 1. 目标

- 将 4 个 L1 脚本降为 wrapper
- 保留参数兼容与退出码透传
- 输出 deprecation 提示而不吞错

## 2. 文件边界

### 可修改（白名单）
- `scripts/check_workflow_contract.py`
- `scripts/check_clarify_plan_alignment.py`
- `scripts/check_plan_vk_coverage.py`
- `scripts/check_gate_contract_consistency.py`
- `scripts/check_integration_gate.py`

## 3. 测试与验收

- 最小测试集:
  - `cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode legacy_wrapper_compat --task-split-dir docs/内部参考/任务拆解/2026-03-06_工程减法治理 --output -`
- 验收标准:
  - 4 个 L1 旧脚本改为 wrapper
  - 旧命令参数兼容且退出码透传

## 4. card_export（机读）

```yaml
card_export:
  id: WS-C03
  feature_id: P1-legacy-wrapper
  card_key: PP-20260306-workflow-gate-retirement::WS-C03
  title: C03 P1 L1旧脚本 wrapper 兼容壳
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  lane: lane-wrapper
  hard_depends_on: [C02]
  soft_depends_on: []
  depends_on: [C02]
  file_whitelist:
    - scripts/check_workflow_contract.py
    - scripts/check_clarify_plan_alignment.py
    - scripts/check_plan_vk_coverage.py
    - scripts/check_gate_contract_consistency.py
    - scripts/check_integration_gate.py
  mechanism_summary:
    - 4 个 L1 旧脚本 wrapper 化
    - 统一入口承载 legacy_wrapper_compat 自检
    - 参数兼容与退出码透传
    - 输出 deprecation 提示
  code_anchor_refs:
    - scripts/check_workflow_contract.py::MODE_REGISTRY
    - scripts/check_workflow_contract.py::run_mode
    - scripts/check_clarify_plan_alignment.py::main
    - scripts/check_plan_vk_coverage.py::main
    - scripts/check_gate_contract_consistency.py::main
    - scripts/check_integration_gate.py::main
  acceptance_checks:
    - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode legacy_wrapper_compat --task-split-dir docs/内部参考/任务拆解/2026-03-06_工程减法治理 --output -
  rollback_anchors:
    - WORKFLOW_GATE_DEPRECATION_ENFORCED=false
  evidence_entry: docs/内部参考/迭代需求/workflow-gate-retirement_implementation_plan.md
  check_cmd:
    - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode legacy_wrapper_compat --task-split-dir docs/内部参考/任务拆解/2026-03-06_工程减法治理 --output -
  done_gate:
    - 4 个 L1 旧脚本改为 wrapper
    - 旧命令参数兼容且退出码透传
  source_ws_file: docs/内部参考/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C03_P1_L1旧脚本wrapper兼容壳.md
```
