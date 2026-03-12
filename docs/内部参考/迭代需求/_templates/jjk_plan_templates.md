# `/jjk-plan` 项目覆盖模板（requirements + design -> implementation_plan + uat_cases）

> 仅用于覆盖全局模板差异：
> `/Users/jijingkun/.codex/engineering/templates/jjk_plan_templates.md`

## `implementation_plan.md` 最小骨架

```yaml
execution_strategy:
  summary: <为什么这样拆任务>

task_breakdown:
  - task_id: TASK-001
    goal: <本任务目标>
    file_paths: []
    symbols: []
    depends_on: []
    change_type: modify|create|delete|refactor
    acceptance_cmds:
      - kind: unit|api|scripted_flow|e2e|db
        cmd: <命令>
    rollback_point: <回滚点>
    risk_tags: []
    mandatory_evidence: []
    db_migration_cmds: []

db_migration_plan:
  db_migration_required: true|false
  release_migration_required: true|false
  tasks:
    - task_id: TASK-DB-001
      mode: sync_database_only|alembic_versioned
      cmds:
        - cmd: bash scripts/db/run_dev_migration.sh
        - cmd: bash scripts/db/run_release_migration.sh --message "<message>" --skip-upgrade
        - cmd: bash scripts/db/run_release_migration.sh --upgrade-only
```

## `uat_cases.md` 最小骨架

```yaml
uat_cases:
  - case_id: UAT-001
    requirement_ids: [FR-001]
    user_role: <角色>
    preconditions:
      - DB migration 已执行（命中时）
    steps:
      - <用户步骤 1>
      - <用户步骤 2>
    expected_results:
      - <预期结果>
    evidence_type: [screenshot,response,db]
    blocking_level: high|medium|low
```

## DB Migration 命令模板

```bash
bash scripts/db/run_dev_migration.sh
```

```bash
bash scripts/db/run_release_migration.sh --message "<message>"
```
