# 文档分层治理 Phase 2：task_split 机器契约与过程报告收口设计

> 文档版本：v1.1
> 更新时间：2026-03-11
> 设计状态：`approved`
> 关联方案：`workdocs/归档/正文/设计/2026-03-10-docs-governance-layering-design.md`

## 0. 结论先行

- `task_split` canonical 根目录冻结为 `workdocs/任务拆解/<task_split_dir>/`。
- `_active_task.json` / `vk_cards.json` 进入 `contracts/`；`preflight_status.json` / `consumption_report.json` / `gate_contract_report.json` / `sync/**` 进入 `reports/`。
- `.artifacts/` 只保留真实运行态，不再承载过程契约与过程报告。
- 兼容策略只保留“读旧入参 / 写新 canonical”，不保留 docs 旧路径文件、symlink、thin index、双写。
- 实现时必须同步更新目录说明与两张流程图，禁止只改脚本不改文档。

## 1. scope_contract

- 目标:
  - 在不破坏 `jjk-cardrun / wt-flow / coder4_* / workflow_contract_*` 的前提下，把 task_split 机器契约、过程报告、运行态彻底分层。
  - 删除旧 task_split 入口作为 task_split 机器 JSON 的存放点。
  - 收敛出共享 path resolver，消灭散落硬编码路径。
- 范围:
  - `workdocs/任务拆解/**`
  - `.artifacts/states/task_splits/**`
  - `scripts/coder4/wt-flow.sh`
  - `scripts/coder4/coder4_bootstrap_kernel.py`
  - `scripts/coder4/coder4_vk_sync.py`
  - `scripts/coder4/set_active_task.py`
  - `scripts/workflow_contract_gate_contract_impl.py`
  - `scripts/check_workflow_contract.py`
  - `scripts/docs_guard.py`
  - `.cursor/rules/doc_sync.mdc`
- 边界:
  - 不在本轮改 `jjk-clarify/jjk-plan` 产物路径契约。
  - 不把 task_split 私有文件搬到根级 `contracts/` / `reports/`。
  - 不长期保留双真理源。
- 成功标准:
  - docs 下 task_split 机器 JSON / 过程 JSON 清零。
  - `wt-flow`、`coder4_*`、`workflow_contract_*` 默认都从 `workdocs/任务拆解/**` 解析。
  - `docs_guard` / `doc_sync` 开始把 docs 下 task_split JSON 视为污染。

## 2. product_contract（PRD-Lite）

- target_users:
  - 仓库维护者
  - 计划 / 执行 / 验收链路的 AI 协作者
  - 需要追溯 task_split 证据链的评审者
- core_scenarios:
  - 新建 task_split 时写入 `workdocs/.../contracts/` 与 `workdocs/.../reports/`
  - `wt-flow` / `coder4_*` / `workflow_contract_*` 全部切到新 canonical 路径
  - docs 下不再承载 task_split 机器契约与过程报告 JSON
  - docs / workdocs / .artifacts / contracts / reports 边界最终简洁可解释
- business_goals:
  - `task_split_machine_json_under_docs = 0`
  - `task_split_canonical_root_count = 1`
  - `task_split_path_resolver_impl_count = 1`
  - `docs_guard_phase1_task_split_compat_exceptions = 0`
  - `task_split_runtime_under_artifacts = 100%`
- non_goals:
  - 不保留 docs 与 workdocs 双写
  - 不采用 symlink / thin index 维持 docs 旧路径
  - 不把 task_split 私有文件迁到根级 `contracts/` / `reports/`
  - 不把本轮扩大成全流程文档产物路径重构
- acceptance_gates:
  - AG-01 task_split canonical root 唯一且冻结
  - AG-02 contract / report / runtime 三层边界清晰
  - AG-03 docs 下 task_split 机器 JSON / 过程 JSON 清零并被阻断复发
  - AG-04 shared resolver 成为唯一路径 owner
  - AG-05 文档说明与两张流程图同步更新完成

## 3. architecture_contract

- 模块边界:
  - `docs/` 只放稳定真理源。
  - `workdocs/任务拆解/<task_split_dir>/` 只放过程正文、过程契约、过程报告。
  - `.artifacts/states/task_splits/<task_split_dir>/<task_key>/` 只放真实运行态。
  - 根级 `contracts/` 只放跨任务共享 schema；根级 `reports/` 只放仓库级汇总报告。
- 依赖方向:
  - `wt-flow / coder4_* / workflow_contract_* -> shared task_split resolver -> canonical paths`
  - `contracts -> reports -> .artifacts` 不反向依赖。
- 状态归属:
  - `_active_task.json` / `vk_cards.json` 归 `contracts/`
  - `preflight_status.json` / `consumption_report.json` / `gate_contract_report.json` / `sync/**` 归 `reports/`
  - `task-runner-state.json` / `jsonl` / `lock` / `attempt_*` 归 `.artifacts/`
- 错误处理责任:
  - shared resolver 负责读旧入参并归一到 canonical path。
  - writers 只写新路径。
  - docs_guard / doc_sync 负责阻断 docs 下 task_split JSON 复发。

## 4. requirement_seeds

- D-01-task-split-canonical-root
- D-02-contract-report-split
- D-03-runtime-outside-workdocs
- D-04-shared-resolver-single-owner
- D-05-docs-hard-cut
- D-06-workflow-contract-unify
- D-07-root-boundary-freeze

## 5. implementation_seeds

- task_id: T01
  file_paths: [scripts/task_split_paths.py, scripts/coder4/wt-flow.sh, scripts/coder4/coder4_bootstrap_kernel.py, scripts/coder4/coder4_vk_sync.py]
  symbols: [task_split_locator, canonical_task_split_dir, legacy_input_alias]
  change_type: refactor
- task_id: T02
  file_paths: [scripts/coder4/set_active_task.py, workdocs/任务拆解]
  symbols: [task_split_contract_writer, active_task_index, status_source_of_truth]
  change_type: refactor
- task_id: T03
  file_paths: [scripts/workflow_contract_gate_contract_impl.py, scripts/check_workflow_contract.py, scripts/workflow_contract_clarify_plan_impl.py, scripts/workflow_contract_plan_vk_coverage_impl.py, scripts/coder4/check_integration_gate.py, scripts/coder4/coder4_scope_guard.py, scripts/check_gate_contract_consistency.py]
  symbols: [workflow_contract_reader, canonical_contract_paths]
  change_type: refactor
- task_id: T04
  file_paths: [workdocs/任务拆解, docs/内部参考/任务拆解]
  symbols: [task_split_file_migration, path_reference_rewrite]
  change_type: refactor
- task_id: T05
  file_paths: [scripts/docs_guard.py, .cursor/rules/doc_sync.mdc, docs/README.md, docs/SUMMARY.md, workdocs/README.md, workdocs/任务拆解/README.md, docs/开发文档/流程与工具/文档治理基线清单.md]
  symbols: [docs_task_split_block, phase2_boundary_text, phase2_flow_diagram]
  change_type: modify
- task_id: T06
  file_paths: [memory-bank.md]
  symbols: [phase2_decision_record, legacy_alias_cleanup_plan]
  change_type: modify

## 6. design_freeze_summary

```yaml
design_freeze_summary:
  design_actionable: true
  missing_blocks: []
  risk_level: medium
  risk_counterexamples_count: 5
  handoff_contract_ready: true
  product_contract_ready: true
  implementation_seed_count: 6
  semantic_frozen: true
  contract_source_decided: true
  handoff_seed_alignment_ok: true
  parallel_dependency_ready: true
  replay_canonical_field_set: true
  blocking_issues: []
```

## 7. clarify_handoff_contract

```yaml
clarify_handoff_contract:
  version: v2
  topic: "docs-governance-phase2-task-split-layering"
  design_source: workdocs/归档/正文/设计/2026-03-11-docs-governance-phase2-task-split-layering-design.md
  handoff_ready: true
  required:
    product_contract_summary:
      target_users:
        - 仓库维护者
        - 计划 / 执行 / 验收链路的 AI 协作者
        - 需要追溯 task_split 证据链的评审者
      core_scenarios:
        - 新建 task_split 时写入 `workdocs/.../contracts/` 与 `workdocs/.../reports/`
        - `wt-flow` / `coder4_*` / `workflow_contract_*` 全部切到新 canonical 路径
        - docs 下不再承载 task_split 机器契约与过程报告 JSON
      business_goal_metrics:
        - task_split_machine_json_under_docs = 0
        - task_split_canonical_root_count = 1
        - task_split_path_resolver_impl_count = 1
        - docs_guard_phase1_task_split_compat_exceptions = 0
        - task_split_runtime_under_artifacts = 100%
      non_goals:
        - 不保留 docs 与 workdocs 双写
        - 不采用 symlink / thin index 维持 docs 旧路径
        - 不把 task_split 私有文件迁到根级 `contracts/` / `reports/`
      acceptance_gates: [AG-01, AG-02, AG-03, AG-04, AG-05]
    requirement_seeds:
      - requirement_id: D-01-task-split-canonical-root
        summary: task_split canonical root 唯一为 workdocs/任务拆解/<task_split_dir>
      - requirement_id: D-02-contract-report-split
        summary: 机器契约与过程报告拆成 contracts / reports
      - requirement_id: D-03-runtime-outside-workdocs
        summary: 真实运行态只进 .artifacts
      - requirement_id: D-04-shared-resolver-single-owner
        summary: 所有脚本共用一套 task_split resolver
      - requirement_id: D-05-docs-hard-cut
        summary: docs 下 task_split 机器 JSON / 过程 JSON 清零
      - requirement_id: D-06-workflow-contract-unify
        summary: planning / verify / review 统一读取新 canonical path
      - requirement_id: D-07-root-boundary-freeze
        summary: 根级 contracts / reports 不承载 task_split 私有文件
    implementation_seeds:
      - task_id: T01
        feature_id: DOC-P2-01
        blocked_by: []
        file_paths:
          - scripts/task_split_paths.py
          - scripts/coder4/wt-flow.sh
          - scripts/coder4/coder4_bootstrap_kernel.py
          - scripts/coder4/coder4_vk_sync.py
        symbols: [task_split_locator, canonical_task_split_dir, legacy_input_alias]
        change_type: refactor
      - task_id: T02
        feature_id: DOC-P2-02
        blocked_by: [T01]
        file_paths:
          - scripts/coder4/set_active_task.py
          - workdocs/任务拆解
        symbols: [task_split_contract_writer, active_task_index, status_source_of_truth]
        change_type: refactor
      - task_id: T03
        feature_id: DOC-P2-03
        blocked_by: [T01]
        file_paths:
          - scripts/workflow_contract_gate_contract_impl.py
          - scripts/check_workflow_contract.py
          - scripts/workflow_contract_clarify_plan_impl.py
          - scripts/workflow_contract_plan_vk_coverage_impl.py
          - scripts/coder4/check_integration_gate.py
          - scripts/coder4/coder4_scope_guard.py
          - scripts/check_gate_contract_consistency.py
        symbols: [workflow_contract_reader, canonical_contract_paths]
        change_type: refactor
      - task_id: T04
        feature_id: DOC-P2-04
        blocked_by: [T02, T03]
        file_paths:
          - workdocs/任务拆解
          - docs/内部参考/任务拆解
        symbols: [task_split_file_migration, path_reference_rewrite]
        change_type: refactor
      - task_id: T05
        feature_id: DOC-P2-05
        blocked_by: [T04]
        file_paths:
          - scripts/docs_guard.py
          - .cursor/rules/doc_sync.mdc
          - docs/README.md
          - docs/SUMMARY.md
          - workdocs/README.md
          - workdocs/任务拆解/README.md
          - docs/开发文档/流程与工具/文档治理基线清单.md
        symbols: [docs_task_split_block, phase2_boundary_text, phase2_flow_diagram]
        change_type: modify
      - task_id: T06
        feature_id: DOC-P2-06
        blocked_by: [T05]
        file_paths:
          - memory-bank.md
        symbols: [phase2_decision_record, legacy_alias_cleanup_plan]
        change_type: modify
    execution_chain_seed:
      preferred_mode: core
      task_key: PP-20260311-docs-governance-phase2-task-split-layering
      card_seed: [T01, T02, T03, T04, T05, T06]
      execution_contract_hint:
        delivery_mode: staged
        execution_unit: per_task
        commit_policy: single_commit
        stop_boundary: per_task
    alignment_contract:
      strict_match: true
      requirement_seed_ids:
        - D-01-task-split-canonical-root
        - D-02-contract-report-split
        - D-03-runtime-outside-workdocs
        - D-04-shared-resolver-single-owner
        - D-05-docs-hard-cut
        - D-06-workflow-contract-unify
        - D-07-root-boundary-freeze
      implementation_task_ids: [T01, T02, T03, T04, T05, T06]
      card_seed_ids: [T01, T02, T03, T04, T05, T06]
```

## 8. clarify_consistency_check

```yaml
clarify_consistency_check:
  clarify_phase: approval
  current_round: 2
  question_mode: single
  open_questions_count: 0
  product_contract_ready: true
  semantic_frozen: true
  contract_source_decided: true
  handoff_seed_alignment_ok: true
  parallel_dependency_ready: true
  replay_canonical_field_set: true
  fail_fast_codes: []
```

## 9. 审批记录

- design_approved: true
- approved_at: 2026-03-11T11:15:00+08:00
- approved_round: v1.1-approval-2026-03-11
- approval_evidence: 用户回复“确认,这一套的变动一定要更新文档,把流程图写清楚”
- approval_mode: approved
- go_no_go: GO
