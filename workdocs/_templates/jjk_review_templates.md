# `/jjk-review` 项目覆盖模板（轻量）

> 仅用于覆盖全局模板差异：
> `/Users/jijingkun/.codex/engineering/templates/jjk_review_templates.md`

## 审查清单补充段

```yaml
review_checklist:
  requirements_conformance: pass|warn|fail
  design_conformance: pass|warn|fail
  plan_conformance: pass|warn|fail
  architecture_conformance: pass|warn|fail
  touched_scope_architecture: improved|neutral|worse
  complexity_conformance: pass|warn|fail
  simplification_conformance: pass|warn|fail
  duplicate_cleanup_conformance: pass|warn|fail
  shrink_contract_conformance: pass|warn|fail
  db_migration_conformance: pass|warn|fail
  api_doc_sync_conformance: pass|warn|fail

architecture_review:
  touched_scope:
    entrypoints: []
    direct_dependencies: []
    replaced_or_neighbor_paths: []
  four_checks:
    module_boundaries: pass|warn|fail
    dependency_direction: pass|warn|fail
    state_ownership: pass|warn|fail
    error_handling: pass|warn|fail
  note: <这次触达范围的架构判断>

slimming_review:
  positive_cleanup: []
  remaining_debt_in_scope: []
  duplicate_logic: pass|warn|fail
  obsolete_paths: pass|warn|fail
  stale_fallbacks: pass|warn|fail
  unnecessary_wrappers: pass|warn|fail
  note: <本轮是否真正让 touched scope 更简洁>

agent_authoring_review:
  smell_ids_checked:
    - multi_decider_stack
    - keyword_primary_routing
    - dual_truth_design
    - speculative_fallback
    - missing_eval_evidence
  complexity_upgrade_evidence: pass|warn|fail
  real_task_eval_evidence: pass|warn|fail
  note: <命中 agent 相关任务时填写>
```
