# `/jjk-design` 项目覆盖模板（轻量）

> 仅用于覆盖全局模板差异：
> `/Users/jijingkun/.codex/engineering/templates/jjk_design_templates.md`

## 方案文档最小骨架

```markdown
# <Topic> Technical Design

## Meta
- topic:
- source_requirements:
- publish_design_doc: false

## Module Boundaries
- responsible:
- out_of_scope:

## Dependency Direction
- allowed:
- forbidden:

## State Ownership
- single_writer:
- read_only_consumers:

## Error Handling
- intercept_layer:
- transform_layer:
- log_layer:

## Change Map
### New Paths
- path:
  purpose:

### Modified Paths
- path:
  purpose:

### Replaced Responsibilities
- old_path:
  replaced_by:

## DB Migration Contract
- db_migration_required: true|false
- db_change_scope:
- db_migration_mode: sync_database_only|alembic_versioned
- release_migration_required: true|false
- db_rollback_strategy:

## Shrink Contract
- obsolete_paths:
- retained_paths:
- single_entry_owner:
- line_budget:

## Doc Sync Flags
- api_doc_required: true|false
- publish_design_doc: true|false
```
