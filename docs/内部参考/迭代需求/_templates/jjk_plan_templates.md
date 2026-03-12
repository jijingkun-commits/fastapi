# `/jjk-plan` 项目覆盖模板（requirements + design -> implementation_plan + uat_cases）

## `implementation_plan.md` 推荐骨架

```yaml
execution_strategy:
  summary: <为什么这样拆任务>

implementation_tasks:
  - task_id: T-01
    feature_id: P1-01
    design_item_refs: [D-01]
    requirement_ids: [FR-01]
    goal: <本任务目标>
    phase: Phase-1
    change_type: create|modify|delete|refactor
    owner: <owner>
    risk_point: <主要风险>
    rollback_point: <回滚点>
    depends_on_tasks: []
    file_paths: []
    symbols: []
    module_changes:
      - module: <模块>
        action: <改什么>
    deletion_actions:
      - path_or_symbol: <删除对象>
        reason: <删除原因>
    acceptance_cmds:
      - <命令>
    risk_tags: []
    mandatory_evidence: []
    db_migration_cmds: []

acceptance_cmd_registry:
  - task_id: T-01
    acceptance_cmds:
      - kind: unit|api|integration|e2e|scripted_flow|chat_db|data_db
        cmd: <命令>

task_to_pr_mapping:
  - task_id: T-01
    pr_id: PR-01
    pr_branch: codex/<branch>
    pr_depends_on: []
    pr_subject: <一句话主题>
    acceptance_cmds:
      - <命令>
    rollback_point: <回滚点>

planning_contract:
  execution_mode: serial|parallel
  strict_single_active_card: true|false
  card_order: [C01]

execution_contract:
  preferred_mode: core|vkplan
  execution_contract_ready: true
  delivery_mode: staged|single
  execution_unit: all_tasks|per_task
  commit_policy: single_commit|per_task_commit
  stop_boundary: per_task|per_card
  design_source: docs/内部参考/迭代需求/<topic>_design.md
  requirements_source: docs/内部参考/迭代需求/<topic>_requirements.md

tc_execution_mapping:
  - tc_id: TC-01
    task_id: T-01
    pr_id: PR-01

db_migration_plan:
  db_migration_required: true|false
  release_migration_required: true|false
  tasks: []
```

## `uat_cases.md` 推荐骨架

```yaml
uat_cases:
  - case_id: UAT-01
    requirement_ids: [FR-01]
    design_item_refs: [D-01]
    task_ids: [T-01]
    user_role: <角色>
    preconditions:
      - <前置条件>
    steps:
      - <用户步骤 1>
      - <用户步骤 2>
    expected_results:
      - <预期结果>
    evidence_type: [screenshot,response,db]
    blocking_level: high|medium|low
```

## `requirements.md` 原位回填的 `traceability_matrix`

```yaml
traceability_matrix:
  - design_item: D-01
    fr_id: FR-01
    bg_id: BG-01
    feature_id: P1-01
    task_id: T-01
    tc_id: TC-01
    acceptance_cmd_ref: <命令引用>
```
