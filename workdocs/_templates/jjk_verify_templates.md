# `/jjk-verify` 项目覆盖模板（verify report）

## `verify_report.md` 推荐骨架

```yaml
verify_summary:
  verdict: PASS|WARN|FAIL
  topic: <topic>
  design_source: workdocs/设计/<topic>/design.md

requirement_coverage:
  - fr_id: FR-01
    design_items: [D-01]
    task_ids: [T-01]
    uat_cases: [UAT-01]
    evidence: [<evidence>]
    verdict: pass|warn|fail

design_conformance:
  module_change_plan: pass|warn|fail
  deletion_plan: pass|warn|fail
  shrink_contract: pass|warn|fail
  db_migration_contract: pass|warn|fail

review_consumption:
  review_report_present: true|false
  review_verdict: PASS|CONDITIONAL_PASS|BLOCKED|unknown
  review_findings_closed: pass|warn|fail
  architecture_conformance: pass|warn|fail
  touched_scope_architecture: improved|neutral|worse|unknown
  complexity_conformance: pass|warn|fail
  simplification_conformance: pass|warn|fail
  duplicate_cleanup_conformance: pass|warn|fail
  unresolved_review_findings: []
  note: <verify 如何消费 review 结论>

traceability_chain:
  complete: true|false
  broken_links: []

db_migration_result:
  required: true|false
  sync_database_proven: true|false
  alembic_revision_present: true|false
  upgrade_head_proven: true|false
  verdict: pass|warn|fail

agent_governance_result:
  smell_ids_closed: pass|warn|fail
  real_task_eval_verified: true|false
  complexity_upgrade_evidence_verified: true|false
  missing_eval_evidence: present|absent
  note: <命中 agent 相关任务时填写>
```
