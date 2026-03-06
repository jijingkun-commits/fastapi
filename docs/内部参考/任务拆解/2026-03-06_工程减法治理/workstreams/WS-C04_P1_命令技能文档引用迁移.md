# WS-C04 C04 P1 命令技能文档引用迁移

> WS 编号: `WS-C04`
> 对应卡片: `C04`
> 类型: `parallel`
> 对应 `feature_id`: `P1-reference-migration`

## 0. 关联与来源

- 对应 `task_key`: `PP-20260306-workflow-gate-retirement`
- PR 归属: `PR-02` / `codex/workflow-gate-retirement-pr-02`

## 1. 目标

- 将 `.cursor/commands` 引用迁移到统一入口
- 将 `.agents/skills` 引用迁移到统一入口
- 将 `docs/开发文档` 的旧入口描述收敛

## 2. 测试与验收

- 最小测试集:
  - `cd /Users/jijingkun/bojxAI/fastapi && rg -n "check_workflow_contract.py|check_clarify_plan_alignment.py|check_plan_vk_coverage.py|check_gate_contract_consistency.py|check_integration_gate.py" .cursor/commands .agents/skills docs/开发文档`
- 验收标准:
  - 命令/技能/文档引用完成迁移
  - 不再直接依赖旧实现脚本

## 3. card_export（机读）

```yaml
card_export:
  id: WS-C04
  feature_id: P1-reference-migration
  card_key: PP-20260306-workflow-gate-retirement::WS-C04
  title: C04 P1 命令技能文档引用迁移
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  lane: lane-doc-migration
  hard_depends_on: [C03]
  soft_depends_on: []
  depends_on: [C03]
  file_whitelist:
    - .cursor/commands
    - .agents/skills
    - docs/开发文档
  mechanism_summary:
    - 迁移命令引用
    - 迁移技能引用
    - 迁移开发文档引用
  acceptance_checks:
    - cd /Users/jijingkun/bojxAI/fastapi && rg -n "check_workflow_contract.py|check_clarify_plan_alignment.py|check_plan_vk_coverage.py|check_gate_contract_consistency.py|check_integration_gate.py" .cursor/commands .agents/skills docs/开发文档
  rollback_anchors:
    - WORKFLOW_GATE_DEPRECATION_ENFORCED=false
  evidence_entry: docs/内部参考/迭代需求/workflow-gate-retirement_implementation_plan.md
  check_cmd:
    - cd /Users/jijingkun/bojxAI/fastapi && rg -n "check_workflow_contract.py|check_clarify_plan_alignment.py|check_plan_vk_coverage.py|check_gate_contract_consistency.py|check_integration_gate.py" .cursor/commands .agents/skills docs/开发文档
  done_gate:
    - 命令 技能 文档引用完成迁移
    - 不再直接依赖旧实现脚本
  source_ws_file: docs/内部参考/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C04_P1_命令技能文档引用迁移.md
```
