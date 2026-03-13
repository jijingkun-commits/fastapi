# `/jjk-imp` 项目覆盖模板（implementation evidence）

## DB Migration 执行模板

```bash
bash scripts/db/run_dev_migration.sh
```

```bash
bash scripts/db/run_release_migration.sh --message "<message>"
```

## 证据回填模板

```yaml
implementation_evidence:
  task_id: T-01
  feature_id: P1-01
  design_item_refs: [D-01]
  requirement_ids: [FR-01]
  modified_modules:
    - module: <模块>
      change: <改了什么>
  deleted_items:
    - path_or_symbol: <删除对象>
      result: removed|retained_with_reason
      note: <说明>
  acceptance_cmd_results:
    - cmd: <command>
      exit_code: 0
      summary: <summary>
  mandatory_evidence:
    - <evidence>
```

```yaml
db_migration_evidence:
  db_migration_required: true
  mode: sync_database_only|alembic_versioned
  executed_cmds:
    - cmd: <command>
      exit_code: 0
      summary: <summary>
  migration_files: []
```
