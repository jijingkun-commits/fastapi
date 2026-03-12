# `/jjk-imp` 项目覆盖模板（轻量）

> 仅用于覆盖全局模板差异：
> `/Users/jijingkun/.codex/engineering/templates/jjk_imp_templates.md`

## DB Migration 执行模板

```bash
bash scripts/db/run_dev_migration.sh
```

```bash
bash scripts/db/run_release_migration.sh --message "<message>"
```

## 证据回填模板

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
