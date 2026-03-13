# 文档分层治理 Phase 2：task_split 分层收口实施方案

> 更新时间：2026-03-11 11:40 +08:00
> 上游设计：`workdocs/归档/正文/设计/2026-03-11-docs-governance-phase2-task-split-layering-design.md`
> 对应需求：`workdocs/归档/正文/需求/docs-governance-phase2-task-split-layering_requirements.md`
> 文档目标：定义 HOW（implementation_tasks、PR 映射、执行合同、实施就绪度），供 `$jjk-imp` 直接承接

## 0. 输入来源清单
- design：`workdocs/归档/正文/设计/2026-03-11-docs-governance-phase2-task-split-layering-design.md`
- requirements：`workdocs/归档/正文/需求/docs-governance-phase2-task-split-layering_requirements.md`
- Phase 1 requirements：`workdocs/归档/正文/需求/文档分层治理与信息架构收敛_requirements.md`
- Phase 1 implementation：`workdocs/归档/正文/实施计划/文档分层治理与信息架构收敛_implementation_plan.md`

## 1. 架构影响与执行约束

### 1.1 实施目标
- 先把路径解析收敛成单 owner，再切 writer、再切 reader、最后删旧 docs 文件和 compat 口子。
- `workdocs/任务拆解/<task_split_dir>/` 只保留过程正文、过程契约、过程报告；`.artifacts/` 只保留真实运行态。
- 本轮不接受长期双写；兼容只允许存在于 resolver 的“读旧入参”能力里。
- 文档同步不是收尾动作，而是和代码切换同批完成的门禁动作。

### 1.2 执行约束
- 默认 `core` 模式，不拆并行卡。
- 必须先做共享 resolver，禁止边改脚本边各自写一套 fallback。
- 必须同步更新目录说明与流程图：`docs/README.md`、`docs/SUMMARY.md`、`workdocs/README.md`、`workdocs/任务拆解/README.md`、`.cursor/rules/doc_sync.mdc`、`docs/开发文档/流程与工具/文档治理基线清单.md`。
- 旧 task_split 入口下的机器 JSON / 过程 JSON 在迁移 PR 内直接删除，不保留 symlink / thin index。
- 本轮不改业务代码，不扩散到根级 `contracts/` / `reports/`。

## 2. implementation_tasks（机读）

```yaml
implementation_tasks:
  - task_id: T01
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[0]
    feature_id: F1-task-split-shared-resolver
    pr_id: PR-01
    phase: Phase-1
    change_type: refactor
    owner: doc-governance
    depends_on_tasks: [ROOT]
    risk_point: 如果共享 resolver 不先落地，后续 consumer 会继续各改各的路径，结构不会真的收敛
    rollback_point: 回退 shared resolver 引入，但不恢复 docs 旧文件双写
    risk_tags: [contract, structure]
    mandatory_evidence: [canonical_path_resolver_single_owner, legacy_input_alias_documented]
    file_paths:
      - scripts/task_split_paths.py
      - scripts/coder4/wt-flow.sh
      - scripts/coder4/coder4_bootstrap_kernel.py
      - scripts/coder4/coder4_vk_sync.py
    symbols:
      - task_split_locator
      - canonical_task_split_dir
      - legacy_input_alias
    acceptance_cmds:
      - rg -n "workdocs/任务拆解|canonical_task_split_dir|legacy_input_used" scripts/task_split_paths.py scripts/coder4/wt-flow.sh scripts/coder4/coder4_bootstrap_kernel.py scripts/coder4/coder4_vk_sync.py

  - task_id: T02
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[1]
    feature_id: F2-task-split-writer-cutover
    pr_id: PR-01
    phase: Phase-2
    change_type: refactor
    owner: doc-governance
    depends_on_tasks: [T01]
    risk_point: writer 如果还继续写 docs 旧路径，后面的迁移和 guard 收紧都会变成假动作
    rollback_point: 回退 writer 到 resolver 兼容读旧，但不恢复 docs 旧路径写入
    risk_tags: [migration, contract]
    mandatory_evidence: [canonical_active_task_writer, canonical_status_source_of_truth]
    file_paths:
      - scripts/coder4/set_active_task.py
      - workdocs/任务拆解
    symbols:
      - task_split_contract_writer
      - active_task_index
      - status_source_of_truth
    acceptance_cmds:
      - rg -n "workdocs/任务拆解/_active_task.json|contracts/_active_task.json|reports/preflight_status.json" scripts/coder4/set_active_task.py

  - task_id: T03
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[2]
    feature_id: F3-workflow-readers-unify
    pr_id: PR-02
    phase: Phase-3
    change_type: refactor
    owner: doc-governance
    depends_on_tasks: [T01]
    risk_point: checker / gate / scope_guard 如果还沿用旧 sibling 结构，执行链会半新半旧
    rollback_point: 回退 reader 对 shared resolver 的接入，但不恢复 docs 旧文件
    risk_tags: [contract, scripted_flow]
    mandatory_evidence: [canonical_contract_paths, workflow_reader_unified, scripted_flow]
    file_paths:
      - scripts/workflow_contract_gate_contract_impl.py
      - scripts/check_workflow_contract.py
      - scripts/workflow_contract_clarify_plan_impl.py
      - scripts/workflow_contract_plan_vk_coverage_impl.py
      - scripts/coder4/check_integration_gate.py
      - scripts/coder4/coder4_scope_guard.py
      - scripts/check_gate_contract_consistency.py
    symbols:
      - workflow_contract_reader
      - canonical_contract_paths
      - legacy_wrapper_compat
    acceptance_cmds:
      - rg -n "contracts/vk_cards.json|reports/preflight_status.json|reports/consumption_report.json|reports/gate_contract_report.json|reports/sync" scripts/check_workflow_contract.py scripts/workflow_contract_gate_contract_impl.py scripts/workflow_contract_clarify_plan_impl.py scripts/workflow_contract_plan_vk_coverage_impl.py scripts/coder4/check_integration_gate.py scripts/coder4/coder4_scope_guard.py scripts/check_gate_contract_consistency.py

  - task_id: T04
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[3]
    feature_id: F4-task-split-file-migration
    pr_id: PR-02
    phase: Phase-4
    change_type: refactor
    owner: doc-governance
    depends_on_tasks: [T02, T03]
    risk_point: 文件迁移不彻底时，docs 会继续残留旧 JSON，guard 也无法真正收口
    rollback_point: 回退文件搬迁批次，但保留 resolver 的读旧入参兼容
    risk_tags: [migration, artifact]
    mandatory_evidence: [docs_task_split_json_zero, workdocs_contracts_reports_present]
    file_paths:
      - workdocs/任务拆解
      - docs/内部参考/任务拆解
    symbols:
      - task_split_file_migration
      - path_reference_rewrite
      - contracts_reports_split
    acceptance_cmds:
      - find docs/内部参考/任务拆解 -type f | rg -q '(_active_task|vk_cards|preflight_status|consumption_report|gate_contract_report|vktodo_create_result|vksync_status)\.json$' && exit 1 || exit 0

  - task_id: T05
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[4]
    feature_id: F5-docs-guard-and-flow-diagrams
    pr_id: PR-03
    phase: Phase-5
    change_type: modify
    owner: doc-governance
    depends_on_tasks: [T04]
    risk_point: 如果说明文档和流程图不更新，团队会继续按旧目录理解执行链，后面还会写回 docs 旧路径
    rollback_point: 回退文档说明与 guard 文本，但不恢复 docs 旧 JSON 兼容
    risk_tags: [docs, rule_sync]
    mandatory_evidence: [phase2_boundary_text, phase2_flow_diagram, docs_guard_strict_clean]
    file_paths:
      - scripts/docs_guard.py
      - .cursor/rules/doc_sync.mdc
      - docs/README.md
      - docs/SUMMARY.md
      - workdocs/README.md
      - workdocs/任务拆解/README.md
      - docs/开发文档/流程与工具/文档治理基线清单.md
    symbols:
      - docs_task_split_block
      - phase2_boundary_text
      - phase2_flow_diagram
    acceptance_cmds:
      - rg -n "目录边界图|执行链流转图|workdocs/任务拆解/.+/contracts|reports/preflight_status.json|docs 不再承载 task_split 机器 JSON" docs/README.md docs/SUMMARY.md workdocs/README.md workdocs/任务拆解/README.md docs/开发文档/流程与工具/文档治理基线清单.md .cursor/rules/doc_sync.mdc
      - PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/docs_guard.py --strict

  - task_id: T06
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[5]
    feature_id: F6-decision-record-and-plan-closeout
    pr_id: PR-03
    phase: Phase-6
    change_type: modify
    owner: doc-governance
    depends_on_tasks: [T05]
    risk_point: 如果长期决策、对齐报告和规划门禁结果不落地，下游执行还会回到口头约定
    rollback_point: 回退 memory-bank 与 planning artifacts，不回退 canonical path 冻结结论
    risk_tags: [contract, scripted_flow]
    mandatory_evidence: [memory_bank_updated, clarify_plan_alignment_json, planning_temporal_gate_json, scripted_flow]
    file_paths:
      - memory-bank.md
      - workdocs/归档/正文/需求/docs-governance-phase2-task-split-layering_requirements.md
      - workdocs/归档/正文/实施计划/docs-governance-phase2-task-split-layering_implementation_plan.md
      - workdocs/归档/报告/机读校验/docs-governance-phase2-task-split-layering_clarify_plan_alignment.json
      - workdocs/归档/报告/机读校验/docs-governance-phase2-task-split-layering_planning_temporal_gate.json
    symbols:
      - phase2_decision_record
      - clarify_plan_alignment
      - planning_temporal_gate
    acceptance_cmds:
      - PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/check_workflow_contract.py --mode clarify_plan --requirements-path workdocs/归档/正文/需求/docs-governance-phase2-task-split-layering_requirements.md --implementation-path workdocs/归档/正文/实施计划/docs-governance-phase2-task-split-layering_implementation_plan.md --output workdocs/归档/报告/机读校验/docs-governance-phase2-task-split-layering_clarify_plan_alignment.json
      - PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/check_workflow_contract.py --mode planning_temporal_gate --implementation-path workdocs/归档/正文/实施计划/docs-governance-phase2-task-split-layering_implementation_plan.md --output workdocs/归档/报告/机读校验/docs-governance-phase2-task-split-layering_planning_temporal_gate.json
```

## 3. task_to_pr_mapping（机读）

```yaml
task_to_pr_mapping:
  - task_id: T01
    pr_id: PR-01
    pr_branch: codex/docs-governance-phase2-task-split-pr-01
    pr_depends_on: []
    pr_subject: "shared resolver 与 writer 切换基座"
    acceptance_cmds:
      - rg -n "workdocs/任务拆解|canonical_task_split_dir|legacy_input_used" scripts/task_split_paths.py scripts/coder4/wt-flow.sh scripts/coder4/coder4_bootstrap_kernel.py scripts/coder4/coder4_vk_sync.py
    rollback_point: 回退 shared resolver 引入
  - task_id: T02
    pr_id: PR-01
    pr_branch: codex/docs-governance-phase2-task-split-pr-01
    pr_depends_on: []
    pr_subject: "shared resolver 与 writer 切换基座"
    acceptance_cmds:
      - rg -n "workdocs/任务拆解/_active_task.json|contracts/_active_task.json|reports/preflight_status.json" scripts/coder4/set_active_task.py
    rollback_point: 回退 writer 到旧接口读兼容
  - task_id: T03
    pr_id: PR-02
    pr_branch: codex/docs-governance-phase2-task-split-pr-02
    pr_depends_on: [PR-01]
    pr_subject: "reader/checker 收口与文件迁移"
    acceptance_cmds:
      - rg -n "contracts/vk_cards.json|reports/preflight_status.json|reports/consumption_report.json|reports/gate_contract_report.json|reports/sync" scripts/check_workflow_contract.py scripts/workflow_contract_gate_contract_impl.py scripts/workflow_contract_clarify_plan_impl.py scripts/workflow_contract_plan_vk_coverage_impl.py scripts/coder4/check_integration_gate.py scripts/coder4/coder4_scope_guard.py scripts/check_gate_contract_consistency.py
    rollback_point: 回退 reader 对 shared resolver 的接入
  - task_id: T04
    pr_id: PR-02
    pr_branch: codex/docs-governance-phase2-task-split-pr-02
    pr_depends_on: [PR-01]
    pr_subject: "reader/checker 收口与文件迁移"
    acceptance_cmds:
      - find docs/内部参考/任务拆解 -type f | rg -q '(_active_task|vk_cards|preflight_status|consumption_report|gate_contract_report|vktodo_create_result|vksync_status)\.json$' && exit 1 || exit 0
    rollback_point: 回退文件迁移批次
  - task_id: T05
    pr_id: PR-03
    pr_branch: codex/docs-governance-phase2-task-split-pr-03
    pr_depends_on: [PR-01, PR-02]
    pr_subject: "文档门禁、流程图与长期决策收口"
    acceptance_cmds:
      - rg -n "目录边界图|执行链流转图|workdocs/任务拆解/.+/contracts|reports/preflight_status.json|docs 不再承载 task_split 机器 JSON" docs/README.md docs/SUMMARY.md workdocs/README.md workdocs/任务拆解/README.md docs/开发文档/流程与工具/文档治理基线清单.md .cursor/rules/doc_sync.mdc
      - PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/docs_guard.py --strict
    rollback_point: 回退 Phase 2 文档说明与 guard 文本
  - task_id: T06
    pr_id: PR-03
    pr_branch: codex/docs-governance-phase2-task-split-pr-03
    pr_depends_on: [PR-01, PR-02]
    pr_subject: "文档门禁、流程图与长期决策收口"
    acceptance_cmds:
      - PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/check_workflow_contract.py --mode clarify_plan --requirements-path workdocs/归档/正文/需求/docs-governance-phase2-task-split-layering_requirements.md --implementation-path workdocs/归档/正文/实施计划/docs-governance-phase2-task-split-layering_implementation_plan.md --output workdocs/归档/报告/机读校验/docs-governance-phase2-task-split-layering_clarify_plan_alignment.json
      - PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/check_workflow_contract.py --mode planning_temporal_gate --implementation-path workdocs/归档/正文/实施计划/docs-governance-phase2-task-split-layering_implementation_plan.md --output workdocs/归档/报告/机读校验/docs-governance-phase2-task-split-layering_planning_temporal_gate.json
    rollback_point: 回退 planning artifacts 与长期决策回填
```

## 4. tc_task_mapping（机读）

```yaml
tc_task_mapping:
  - tc_id: TC-DGP2-01
    task_id: T01
    pr_id: PR-01
    acceptance_cmd_ref: rg -n "workdocs/任务拆解|canonical_task_split_dir|legacy_input_used" scripts/task_split_paths.py scripts/coder4/wt-flow.sh scripts/coder4/coder4_bootstrap_kernel.py scripts/coder4/coder4_vk_sync.py
  - tc_id: TC-DGP2-02
    task_id: T02
    pr_id: PR-01
    acceptance_cmd_ref: rg -n "workdocs/任务拆解/_active_task.json|contracts/_active_task.json|reports/preflight_status.json" scripts/coder4/set_active_task.py
  - tc_id: TC-DGP2-03
    task_id: T03
    pr_id: PR-02
    acceptance_cmd_ref: rg -n "contracts/vk_cards.json|reports/preflight_status.json|reports/consumption_report.json|reports/gate_contract_report.json|reports/sync" scripts/check_workflow_contract.py scripts/workflow_contract_gate_contract_impl.py scripts/workflow_contract_clarify_plan_impl.py scripts/workflow_contract_plan_vk_coverage_impl.py scripts/coder4/check_integration_gate.py scripts/coder4/coder4_scope_guard.py scripts/check_gate_contract_consistency.py
  - tc_id: TC-DGP2-04
    task_id: T04
    pr_id: PR-02
    acceptance_cmd_ref: find docs/内部参考/任务拆解 -type f | rg -q '(_active_task|vk_cards|preflight_status|consumption_report|gate_contract_report|vktodo_create_result|vksync_status)\.json$' && exit 1 || exit 0
  - tc_id: TC-DGP2-05
    task_id: T05
    pr_id: PR-03
    acceptance_cmd_ref: rg -n "目录边界图|执行链流转图|workdocs/任务拆解/.+/contracts|reports/preflight_status.json|docs 不再承载 task_split 机器 JSON" docs/README.md docs/SUMMARY.md workdocs/README.md workdocs/任务拆解/README.md docs/开发文档/流程与工具/文档治理基线清单.md .cursor/rules/doc_sync.mdc
  - tc_id: TC-DGP2-06
    task_id: T06
    pr_id: PR-03
    acceptance_cmd_ref: PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/check_workflow_contract.py --mode clarify_plan --requirements-path workdocs/归档/正文/需求/docs-governance-phase2-task-split-layering_requirements.md --implementation-path workdocs/归档/正文/实施计划/docs-governance-phase2-task-split-layering_implementation_plan.md --output workdocs/归档/报告/机读校验/docs-governance-phase2-task-split-layering_clarify_plan_alignment.json
  - tc_id: TC-DGP2-07
    task_id: T06
    pr_id: PR-03
    acceptance_cmd_ref: PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/check_workflow_contract.py --mode clarify_plan --requirements-path workdocs/归档/正文/需求/docs-governance-phase2-task-split-layering_requirements.md --implementation-path workdocs/归档/正文/实施计划/docs-governance-phase2-task-split-layering_implementation_plan.md --output workdocs/归档/报告/机读校验/docs-governance-phase2-task-split-layering_clarify_plan_alignment.json
  - tc_id: TC-DGP2-08
    task_id: T06
    pr_id: PR-03
    acceptance_cmd_ref: PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/check_workflow_contract.py --mode planning_temporal_gate --implementation-path workdocs/归档/正文/实施计划/docs-governance-phase2-task-split-layering_implementation_plan.md --output workdocs/归档/报告/机读校验/docs-governance-phase2-task-split-layering_planning_temporal_gate.json
```

## 5. planning_contract（机读）

```yaml
planning_contract:
  topic: docs-governance-phase2-task-split-layering
  source_seed_ref: clarify_handoff_contract.required.execution_chain_seed
  execution_mode: core
  task_key: PP-20260311-docs-governance-phase2-task-split-layering
  task_to_pr_mapping:
    - task_id: T01
      pr_id: PR-01
    - task_id: T02
      pr_id: PR-01
    - task_id: T03
      pr_id: PR-02
    - task_id: T04
      pr_id: PR-02
    - task_id: T05
      pr_id: PR-03
    - task_id: T06
      pr_id: PR-03
```

## 6. execution_contract（机读）

```yaml
execution_contract:
  preferred_mode: core
  execution_contract_ready: true
  delivery_mode: staged
  execution_unit: per_task
  commit_policy: single_commit
  stop_boundary: per_task
  stop_on_blocked: true
  source_seed_ref: clarify_handoff_contract.required.execution_chain_seed.execution_contract_hint
```

## 7. implementation_readiness（机读）

```yaml
implementation_readiness:
  implementation_ready: true
  blocked_by: []
  next_step: /jjk-imp
```
