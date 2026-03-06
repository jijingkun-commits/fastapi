# workflow-gate-retirement 实施计划

> 更新时间：2026-03-06 20:43 +08:00  
> 上游输入：`docs/plans/2026-03-06-workflow-gate-retirement-design.md`、`docs/内部参考/迭代需求/workflow-gate-retirement_requirements.md`  
> 当前模式：`core`（进入执行链）

## 0. 输入来源清单

- design：`docs/plans/2026-03-06-workflow-gate-retirement-design.md`
- requirements：`docs/内部参考/迭代需求/workflow-gate-retirement_requirements.md`
- 关键脚本入口：
  - `scripts/check_workflow_contract.py`（新增）
  - `scripts/check_clarify_plan_alignment.py`
  - `scripts/check_plan_vk_coverage.py`
  - `scripts/check_gate_contract_consistency.py`
  - `scripts/check_integration_gate.py`
- 关键文档入口：
  - `.cursor/commands/*`
  - `.agents/skills/*`
  - `docs/开发文档/*`

## 1. 架构影响与执行约束

### 1.1 模块边界

- 治理层（P0）：冻结删除口径并建立 NO-GO 清单。
- 入口层（P1）：统一门禁入口承载契约与模式分发。
- 兼容层（P1）：L1 旧脚本保留 wrapper 语义并透传。
- 可观测层（P2）：旧入口调用日志与零调用判定。
- 退役层（P3）：达标后删除旧实现并完成验收。

### 1.2 状态契约

- 旧脚本状态：`active_impl -> wrapper -> zero_call_observed -> retired`
- 过程产物状态：`active -> done/archived -> ttl_eligible -> archived_trimmed`
- 回退原则：任一阶段失败均可回切到旧入口主链，禁止“删后补救”。

## 2. implementation_tasks（机读）

```yaml
implementation_tasks:
  - task_id: P0-FREEZE-COMMANDS
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[0]
    feature_id: P0-freeze-governance
    pr_id: PR-01
    phase: Phase-0
    change_type: docs_update
    owner: workflow-governance
    depends_on_tasks: [ROOT]
    risk_point: 冻结口径传播不一致导致团队仍执行直接删除命令
    file_paths:
      - docs/内部参考/工程减法体检报告_2026-03-06.md
      - docs/内部参考/工程减法体检报告_2026-03-06_v3.md
      - docs/内部参考/工程减法治理看板模板_2026-03-06.md
    symbols:
      - NO_GO_SECTION
      - phase_plan_table
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && rg -n "NO-GO|rm scripts/check_\\*\\.py" docs/内部参考/工程减法体检报告_2026-03-06.md docs/内部参考/工程减法体检报告_2026-03-06_v3.md
    rollback_point: WORKFLOW_GATE_UNIFIED_ENABLED=false

  - task_id: P1-UNIFIED-ENTRY
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[1]
    feature_id: P1-unified-entry
    pr_id: PR-01
    phase: Phase-1
    change_type: add
    owner: workflow-governance
    depends_on_tasks: [P0-FREEZE-COMMANDS]
    risk_point: mode分发不完整会导致门禁语义不一致
    file_paths:
      - scripts/check_workflow_contract.py
    symbols:
      - parse_args
      - MODE_REGISTRY
      - run_mode
      - main
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode clarify_plan --requirements-path docs/内部参考/迭代需求/workflow-gate-retirement_requirements.md --implementation-path docs/内部参考/迭代需求/workflow-gate-retirement_implementation_plan.md --output -
    rollback_point: WORKFLOW_GATE_UNIFIED_ENABLED=false

  - task_id: P1-WRAPPER-L1
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[2]
    feature_id: P1-legacy-wrapper
    pr_id: PR-02
    phase: Phase-1
    change_type: refactor
    owner: workflow-governance
    depends_on_tasks: [P1-UNIFIED-ENTRY]
    risk_point: wrapper参数透传差异导致旧命令行为漂移
    file_paths:
      - scripts/check_clarify_plan_alignment.py
      - scripts/check_plan_vk_coverage.py
      - scripts/check_gate_contract_consistency.py
      - scripts/check_integration_gate.py
    symbols:
      - main
      - parse_args
      - wrapper_notice
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode legacy_wrapper_compat --task-split-dir docs/内部参考/任务拆解/2026-03-06_工程减法治理 --output -
    rollback_point: WORKFLOW_GATE_DEPRECATION_ENFORCED=false

  - task_id: P1-REFERENCE-MIGRATION
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[3]
    feature_id: P1-reference-migration
    pr_id: PR-02
    phase: Phase-1
    change_type: refactor
    owner: workflow-governance
    depends_on_tasks: [P1-WRAPPER-L1]
    risk_point: 命令/技能/文档遗漏迁移将保留隐式旧入口调用
    file_paths:
      - .cursor/commands
      - .agents/skills
      - docs/开发文档
    symbols:
      - legacy_script_refs
      - primary_entry
      - deprecation_notice
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && rg -n "check_workflow_contract.py|check_clarify_plan_alignment.py|check_plan_vk_coverage.py|check_gate_contract_consistency.py|check_integration_gate.py" .cursor/commands .agents/skills docs/开发文档
    rollback_point: WORKFLOW_GATE_DEPRECATION_ENFORCED=false

  - task_id: P2-OBSERVABILITY
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[4]
    feature_id: P2-usage-observability
    pr_id: PR-03
    phase: Phase-2
    change_type: add
    owner: workflow-governance
    depends_on_tasks: [P1-REFERENCE-MIGRATION]
    risk_point: 观测字段不完整会导致零调用判定失真
    file_paths:
      - scripts/check_workflow_contract.py
      - logs/workflow-gate-usage.jsonl
    symbols:
      - emit_usage_log
      - usage_record_schema_v1
      - aggregate_usage_window
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode usage-report --window-days 7 --output logs/workflow-gate-usage.jsonl
    rollback_point: WORKFLOW_GATE_UNIFIED_ENABLED=false

  - task_id: P2-TTL-ARCHIVE
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[5]
    feature_id: P2-ttl-archive
    pr_id: PR-03
    phase: Phase-2
    change_type: refactor
    owner: workflow-governance
    depends_on_tasks: [P2-OBSERVABILITY]
    risk_point: TTL归档边界实现不当会误触活跃任务文件
    file_paths:
      - scripts/check_workflow_contract.py
      - docs/内部参考/任务拆解
    symbols:
      - ttl_archive_runner
      - should_archive_entry
      - archive_audit_report
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode ttl-audit --task-split-dir docs/内部参考/任务拆解 --ttl-days 14 --output -
    rollback_point: WORKFLOW_ARTIFACT_TTL_CLEANUP_ENABLED=false

  - task_id: P3-RETIRE-LEGACY
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[6]
    feature_id: P3-retire-legacy
    pr_id: PR-04
    phase: Phase-3
    change_type: delete_or_thin_wrapper
    owner: workflow-governance
    depends_on_tasks: [P2-TTL-ARCHIVE]
    risk_point: 删除窗口判断错误会造成链路中断或验收失败
    file_paths:
      - scripts
      - .cursor/commands
      - .agents/skills
      - docs
    symbols:
      - legacy_l1_impl
      - deprecation_wrapper
      - retirement_guard
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode full-gate --task-split-dir docs/内部参考/任务拆解/2026-03-06_工程减法治理 --baseline master --output -
    rollback_point: WORKFLOW_GATE_UNIFIED_ENABLED=false
```

## 3. task_to_pr_mapping（机读）

```yaml
planning_contract:
  task_to_pr_mapping:
    - task_id: P0-FREEZE-COMMANDS
      pr_id: PR-01
      pr_branch: codex/workflow-gate-retirement-pr-01
      pr_depends_on: []
      pr_subject: "P0冻结口径 + P1统一入口骨架"
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && rg -n "NO-GO|rm scripts/check_\\*\\.py" docs/内部参考/工程减法体检报告_2026-03-06.md docs/内部参考/工程减法体检报告_2026-03-06_v3.md
        - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode clarify_plan --requirements-path docs/内部参考/迭代需求/workflow-gate-retirement_requirements.md --implementation-path docs/内部参考/迭代需求/workflow-gate-retirement_implementation_plan.md --output -
      rollback_point: WORKFLOW_GATE_UNIFIED_ENABLED=false

    - task_id: P1-UNIFIED-ENTRY
      pr_id: PR-01
      pr_branch: codex/workflow-gate-retirement-pr-01
      pr_depends_on: []
      pr_subject: "P0冻结口径 + P1统一入口骨架"
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode clarify_plan --requirements-path docs/内部参考/迭代需求/workflow-gate-retirement_requirements.md --implementation-path docs/内部参考/迭代需求/workflow-gate-retirement_implementation_plan.md --output -
      rollback_point: WORKFLOW_GATE_UNIFIED_ENABLED=false

    - task_id: P1-WRAPPER-L1
      pr_id: PR-02
      pr_branch: codex/workflow-gate-retirement-pr-02
      pr_depends_on: [PR-01]
      pr_subject: "P1 wrapper兼容与引用迁移"
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode legacy_wrapper_compat --task-split-dir docs/内部参考/任务拆解/2026-03-06_工程减法治理 --output -
      rollback_point: WORKFLOW_GATE_DEPRECATION_ENFORCED=false

    - task_id: P1-REFERENCE-MIGRATION
      pr_id: PR-02
      pr_branch: codex/workflow-gate-retirement-pr-02
      pr_depends_on: [PR-01]
      pr_subject: "P1 wrapper兼容与引用迁移"
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && rg -n "check_workflow_contract.py|check_clarify_plan_alignment.py|check_plan_vk_coverage.py|check_gate_contract_consistency.py|check_integration_gate.py" .cursor/commands .agents/skills docs/开发文档
      rollback_point: WORKFLOW_GATE_DEPRECATION_ENFORCED=false

    - task_id: P2-OBSERVABILITY
      pr_id: PR-03
      pr_branch: codex/workflow-gate-retirement-pr-03
      pr_depends_on: [PR-01, PR-02]
      pr_subject: "P2调用观测与TTL归档"
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode usage-report --window-days 7 --output logs/workflow-gate-usage.jsonl
      rollback_point: WORKFLOW_GATE_UNIFIED_ENABLED=false

    - task_id: P2-TTL-ARCHIVE
      pr_id: PR-03
      pr_branch: codex/workflow-gate-retirement-pr-03
      pr_depends_on: [PR-01, PR-02]
      pr_subject: "P2调用观测与TTL归档"
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode ttl-audit --task-split-dir docs/内部参考/任务拆解 --ttl-days 14 --output -
      rollback_point: WORKFLOW_ARTIFACT_TTL_CLEANUP_ENABLED=false

    - task_id: P3-RETIRE-LEGACY
      pr_id: PR-04
      pr_branch: codex/workflow-gate-retirement-pr-04
      pr_depends_on: [PR-01, PR-02, PR-03]
      pr_subject: "P3删除旧实现与全量验收"
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode full-gate --task-split-dir docs/内部参考/任务拆解/2026-03-06_工程减法治理 --baseline master --output -
      rollback_point: WORKFLOW_GATE_UNIFIED_ENABLED=false
```

## 4. tc_task_mapping（机读）

```yaml
tc_task_mapping:
  - tc_id: TC-WG-01
    task_id: P0-FREEZE-COMMANDS
    pr_id: PR-01
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && rg -n "NO-GO|rm scripts/check_\\*\\.py" docs/内部参考/工程减法体检报告_2026-03-06.md docs/内部参考/工程减法体检报告_2026-03-06_v3.md
  - tc_id: TC-WG-02
    task_id: P1-UNIFIED-ENTRY
    pr_id: PR-01
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode clarify_plan --requirements-path docs/内部参考/迭代需求/workflow-gate-retirement_requirements.md --implementation-path docs/内部参考/迭代需求/workflow-gate-retirement_implementation_plan.md --output -
  - tc_id: TC-WG-03
    task_id: P1-WRAPPER-L1
    pr_id: PR-02
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode legacy_wrapper_compat --task-split-dir docs/内部参考/任务拆解/2026-03-06_工程减法治理 --output -
  - tc_id: TC-WG-04
    task_id: P1-REFERENCE-MIGRATION
    pr_id: PR-02
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && rg -n "check_workflow_contract.py|check_clarify_plan_alignment.py|check_plan_vk_coverage.py|check_gate_contract_consistency.py|check_integration_gate.py" .cursor/commands .agents/skills docs/开发文档
  - tc_id: TC-WG-05
    task_id: P2-OBSERVABILITY
    pr_id: PR-03
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode usage-report --window-days 7 --output logs/workflow-gate-usage.jsonl
  - tc_id: TC-WG-06
    task_id: P2-TTL-ARCHIVE
    pr_id: PR-03
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode ttl-audit --task-split-dir docs/内部参考/任务拆解 --ttl-days 14 --output -
  - tc_id: TC-WG-07
    task_id: P3-RETIRE-LEGACY
    pr_id: PR-04
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_workflow_contract.py --mode full-gate --task-split-dir docs/内部参考/任务拆解/2026-03-06_工程减法治理 --baseline master --output -
```

## 5. execution_contract（机读）

```yaml
execution_contract:
  delivery_mode: staged
  execution_unit: per_task
  commit_policy: per_pr
  stop_boundary: per_task
  stop_on_blocked: true
  source_seed_ref: clarify_handoff_contract.required.execution_chain_seed.execution_contract_hint
```

## 6. implementation_readiness（机读）

```yaml
implementation_readiness:
  implementation_ready: true
  blocked_by: []
  next_step: /jjk-imp
  execution_contract_ready: true
```

