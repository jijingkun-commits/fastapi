# workflow-gate-retirement 串行卡片包 自动生成总览

> 本文件由 `vk_cards.json` 自动生成，请勿手工维护为独立真理源。
> task_key: `PP-20260306-workflow-gate-retirement `
> task_split_dir: `2026-03-06_工程减法治理 `
> generated_at: `2026-03-08 12:29`

## 1. 执行策略

- execution_mode: `serial`
- single_active_card: `true`
- card_order: `C01, C02, C03, C04, C05, C06, C07, G01`
- gate_contract.mode: `as_cards`
- gate_contract.gate_ids: `G01`
- gate_contract.depends_on: `{"G01": ["C07"]}`
- auto_done_policy: `{"implementation-card": "hard_gate", "inspection-card": "policy_gate"}`
- execution_contract: `{"delivery_mode": "staged", "execution_unit": "per_task", "commit_policy": "per_pr", "stop_boundary": "per_task", "stop_on_blocked": true}`

## 2. 来源文件

- requirements: `workdocs/归档/正文/需求/workflow-gate-retirement_requirements.md`
- implementation_plan: `workdocs/归档/正文/实施计划/workflow-gate-retirement_implementation_plan.md`
- parallel_plan: `workdocs/任务拆解/2026-03-06_工程减法治理/parallel_plan.md`
- workstreams_count: `9`

## 3. automation_contract

```json
{
  "source_of_truth": "workdocs/任务拆解/2026-03-06_工程减法治理/contracts/_active_task.json",
  "required_fields": [
    "project_id",
    "task_split_dir",
    "task_key",
    "execution_mode",
    "single_active_card",
    "auto_done_policy",
    "preflight_required"
  ],
  "scope_match_rule": [
    "title_contains_[task_key]",
    "labels_contains_task_key",
    "card_key_prefix_task_key"
  ]
}
```

## 4. 预检与映射摘要

- preflight.card_id: `C00`
- preflight.feature_ids: `C00-PREFLIGHT`
- preflight.required_done_gate: `planning_contract 与 vk_cards card_order/gate_contract 一致, Gate 卡片化完整且字段齐全, active_task 作用域三元组已绑定`
- mapping_checks: `{"forward_check": "PASS", "reverse_check": "PASS", "orphan_features": [], "duplicate_features": [], "pr_mapping_check": "PASS", "pr_mapping_errors": [], "plan_consumption_check": "PASS", "missing_feature_ids": [], "missing_task_ids": [], "missing_task_id_fields": [], "empty_task_ids": [], "execution_contract_mismatch": [], "acceptance_mapping_missing": []}`

## 5. 卡片总览

| card_id | title | task_mode | depends_on | feature_ids | task_ids | pr_id | source_ws_file |
|---|---|---|---|---|---|---|---|
| C01 | C01 P0 冻结删除口径与执行清单 [PP-20260306-workflow-gate-retirement] | implementation-card | - | P0-freeze-governance | P0-FREEZE-COMMANDS | PR-01 | workdocs/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C01_P0_冻结删除口径与执行清单.md |
| C02 | C02 P1 统一入口 check_workflow_contract [PP-20260306-workflow-gate-retirement] | implementation-card | C01 | P1-unified-entry | P1-UNIFIED-ENTRY | PR-01 | workdocs/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C02_P1_统一入口check_workflow_contract.md |
| C03 | C03 P1 L1旧脚本 wrapper 兼容壳 [PP-20260306-workflow-gate-retirement] | implementation-card | C02 | P1-legacy-wrapper | P1-WRAPPER-L1 | PR-02 | workdocs/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C03_P1_L1旧脚本wrapper兼容壳.md |
| C04 | C04 P1 命令技能文档引用迁移 [PP-20260306-workflow-gate-retirement] | implementation-card | C03 | P1-reference-migration | P1-REFERENCE-MIGRATION | PR-02 | workdocs/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C04_P1_命令技能文档引用迁移.md |
| C05 | C05 P2 旧入口调用观测 [PP-20260306-workflow-gate-retirement] | implementation-card | C04 | P2-usage-observability | P2-OBSERVABILITY | PR-03 | workdocs/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C05_P2_旧入口调用观测.md |
| C06 | C06 P2 TTL归档与过程文件裁剪 [PP-20260306-workflow-gate-retirement] | implementation-card | C05 | P2-ttl-archive | P2-TTL-ARCHIVE | PR-03 | workdocs/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C06_P2_TTL归档与过程文件裁剪.md |
| C07 | C07 P3 删除旧实现与兼容壳收口 [PP-20260306-workflow-gate-retirement] | implementation-card | C06 | P3-retire-legacy | P3-RETIRE-LEGACY | PR-04 | workdocs/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C07_P3_删除旧实现与兼容壳收口.md |
| G01 | G01 全链路验收门禁 [PP-20260306-workflow-gate-retirement] | inspection-card | C07 | G-01 | G01 | PR-G01 | workdocs/任务拆解/2026-03-06_工程减法治理/workstreams/WS-G01_G01_全链路验收门禁.md |

## 6. Gate 状态

- 待执行

## 7. Workstreams 索引

- `workdocs/任务拆解/2026-03-06_工程减法治理/workstreams/WS-00_C00_预检门禁冻结.md`
- `workdocs/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C01_P0_冻结删除口径与执行清单.md`
- `workdocs/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C02_P1_统一入口check_workflow_contract.md`
- `workdocs/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C03_P1_L1旧脚本wrapper兼容壳.md`
- `workdocs/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C04_P1_命令技能文档引用迁移.md`
- `workdocs/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C05_P2_旧入口调用观测.md`
- `workdocs/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C06_P2_TTL归档与过程文件裁剪.md`
- `workdocs/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C07_P3_删除旧实现与兼容壳收口.md`
- `workdocs/任务拆解/2026-03-06_工程减法治理/workstreams/WS-G01_G01_全链路验收门禁.md`
