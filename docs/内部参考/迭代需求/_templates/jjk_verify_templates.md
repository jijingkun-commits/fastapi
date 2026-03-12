# `/jjk-verify` 项目覆盖模板（轻量）

> 仅用于覆盖全局模板差异：
> `/Users/jijingkun/.codex/engineering/templates/jjk_verify_templates.md`

## DB Migration 验收段

```yaml
db_migration_result:
  required: true|false
  sync_database_proven: true|false
  alembic_revision_present: true|false
  upgrade_head_proven: true|false
  verdict: pass|warn|fail
```
