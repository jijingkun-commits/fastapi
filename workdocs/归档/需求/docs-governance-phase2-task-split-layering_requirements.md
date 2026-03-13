# 文档分层治理 Phase 2：task_split 分层收口需求文档

> 更新时间：2026-03-11 11:40 +08:00
> 上游设计：`workdocs/归档/设计/2026-03-11-docs-governance-phase2-task-split-layering-design.md`
> 文档目标：定义 WHAT（需求合同、验收门禁、追溯矩阵），供 `docs-governance-phase2-task-split-layering_implementation_plan.md` 承接

## 1. 需求范围与目标

### 1.1 核心目标
- 把 `task_split` 的 canonical 根目录冻结到 `workdocs/任务拆解/<task_split_dir>/`。
- 把机器契约、过程报告、真实运行态彻底拆开，避免 `docs/` 再承载机器 JSON。
- 让 `jjk-cardrun`、`wt-flow`、`coder4_*`、`workflow_contract_*` 全部改读同一套 canonical path。
- 用一次性迁移替代长期双写兼容，删掉 `docs/内部参考/任务拆解/**` 下的机器 JSON / 过程 JSON。
- 把文档同步和流程图更新升级成实现硬门禁。

### 1.2 范围
- `workdocs/归档/设计/2026-03-11-docs-governance-phase2-task-split-layering-design.md`
- `workdocs/任务拆解/**`
- `.artifacts/states/task_splits/**`
- `scripts/coder4/wt-flow.sh`
- `scripts/coder4/coder4_bootstrap_kernel.py`
- `scripts/coder4/coder4_vk_sync.py`
- `scripts/coder4/set_active_task.py`
- `scripts/workflow_contract_gate_contract_impl.py`
- `scripts/check_workflow_contract.py`
- `scripts/workflow_contract_clarify_plan_impl.py`
- `scripts/workflow_contract_plan_vk_coverage_impl.py`
- `scripts/coder4/check_integration_gate.py`
- `scripts/coder4/coder4_scope_guard.py`
- `scripts/check_gate_contract_consistency.py`
- `scripts/docs_guard.py`
- `.cursor/rules/doc_sync.mdc`
- `docs/README.md`
- `docs/SUMMARY.md`
- `workdocs/README.md`
- `workdocs/任务拆解/README.md`
- `docs/开发文档/流程与工具/文档治理基线清单.md`
- `memory-bank.md`

### 1.3 非范围
- 不在本轮改 `jjk-clarify` / `jjk-plan` 的产物路径契约。
- 不在本轮把历史设计归档再做二次主题重构；先统一收口到 `workdocs/归档/设计/**`。
- 不把 task_split 私有文件迁到根级 `contracts/` 或 `reports/`。
- 不为了兼容继续保留 docs 与 workdocs 的长期双真理源。
- 不改业务功能、数据库模型和接口语义。

## 2. 机读需求合同（强制）

```yaml
requirements_contract:
  topic: "docs-governance-phase2-task-split-layering"
  status: "approved"
  design_source: workdocs/归档/设计/2026-03-11-docs-governance-phase2-task-split-layering-design.md
  clarify_handoff_source: workdocs/归档/设计/2026-03-11-docs-governance-phase2-task-split-layering-design.md#clarify_handoff_contract
  clarify_handoff_version: v2
  design_approved: true
  design_approval_evidence: "用户回复“确认,这一套的变动一定要更新文档,把流程图写清楚”"
  design_freeze_summary:
    design_actionable: true
    missing_blocks: []
    risk_level: medium
    risk_counterexamples_count: 5
    product_contract_ready: true
  owner: "doc-governance"
  approver: "jijingkun"
  updated_at: "2026-03-11 11:15 +08:00"
```

## 3. 产品契约矩阵（PRD-Lite 承接）

```yaml
product_contract_matrix:
  target_users:
    - 仓库维护者
    - 计划 / 执行 / 验收链路的 AI 协作者
    - 需要追溯 task_split 证据链的评审者
  core_scenarios:
    - 新建 task_split 时，机器契约写入 `workdocs/.../contracts/`，过程报告写入 `workdocs/.../reports/`
    - `wt-flow`、`coder4_*`、`workflow_contract_*` 只依赖 canonical root，不再各自拼旧路径
    - docs 区只看得到稳定文档，不再撞见 `_active_task.json`、`vk_cards.json` 这类机器文件
    - 实现完成后，目录边界图与执行链流转图同步更新
  business_goal_metrics:
    - task_split_machine_json_under_docs = 0
    - task_split_canonical_root_count = 1
    - task_split_path_resolver_impl_count = 1
    - docs_guard_phase1_task_split_compat_exceptions = 0
    - task_split_runtime_under_artifacts = 100%
  non_goals:
    - 不保留 docs 与 workdocs 的长期双写
    - 不采用 symlink / thin index 维持 docs 旧路径继续可见
    - 不把 task_split 文件塞进根级 contracts / reports
    - 不把本轮目标扩大为全流程文档产物路径统一改造
  acceptance_gates:
    - AG-01 task_split canonical root 唯一并冻结为 `workdocs/任务拆解/<task_split_dir>`
    - AG-02 contract / report / runtime 三层边界清晰且不重叠
    - AG-03 docs 下 task_split 机器 JSON / 过程 JSON 清零，guard 阻断复发
    - AG-04 所有关键消费者统一依赖 shared resolver
    - AG-05 文档说明与两张流程图同步更新完成
```

## 4. FR 合同矩阵（字段级）

```yaml
fr_contract_matrix:
  - fr_id: FR-01
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[0]
    mapped_business_goal_metrics: [task_split_canonical_root_count = 1]
    user_value: 所有人都知道 task_split 到底该从哪儿读
    trigger: 新建 / 读取 / 校验 task_split
    input_contract:
      required_fields: [task_split_dir_or_path]
      source_of_truth: scripts/task_split_paths.py
    output_contract:
      required_fields: [canonical_task_split_dir, contracts_dir, reports_dir, runtime_state_dir]
      consumer: wt-flow / coder4_* / workflow_contract_*
    failure_semantics: 无法解析 canonical root 时 fail-fast
    observability_fields: [raw_input, canonical_task_split_dir, legacy_input_used]
    rollback_anchor: TASK_SPLIT_PATHS_V2=false
    owner: doc-governance

  - fr_id: FR-02
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[1]
    mapped_business_goal_metrics: [task_split_machine_json_under_docs = 0]
    user_value: task_split 机器契约和过程报告不再混在一个目录里
    trigger: 写入或迁移 task_split 产物
    input_contract:
      required_fields: [task_split_dir, artifact_type]
      source_of_truth: workdocs/任务拆解
    output_contract:
      required_fields: [contracts_path, reports_path]
      consumer: planning / sync / review / verify
    failure_semantics: 机器契约落在 task 根目录或 docs 旧路径时直接违规
    observability_fields: [artifact_type, target_path]
    rollback_anchor: TASK_SPLIT_CONTRACT_REPORT_SPLIT=false
    owner: doc-governance

  - fr_id: FR-03
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[2]
    mapped_business_goal_metrics: [task_split_runtime_under_artifacts = 100%]
    user_value: 真正会变的运行态只进 `.artifacts`
    trigger: 执行 task_split 运行链路
    input_contract:
      required_fields: [task_split_dir, task_key, runtime_file]
      source_of_truth: .artifacts/states/task_splits
    output_contract:
      required_fields: [runtime_state_path]
      consumer: coder4 runtime / audit
    failure_semantics: 运行态文件落入 workdocs/docs 时视为污染并阻断
    observability_fields: [task_split_dir, task_key, runtime_state_path]
    rollback_anchor: TASK_SPLIT_RUNTIME_OUTSIDE_WORKDOCS=false
    owner: doc-governance

  - fr_id: FR-04
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[3]
    mapped_business_goal_metrics: [task_split_path_resolver_impl_count = 1]
    user_value: 脚本只认一套 path resolver
    trigger: 修改任一 task_split 消费脚本
    input_contract:
      required_fields: [consumer_script, task_split_locator]
      source_of_truth: scripts/task_split_paths.py
    output_contract:
      required_fields: [canonical_paths_used]
      consumer: 工程维护者
    failure_semantics: 继续新增私有路径拼接逻辑时视为结构回退
    observability_fields: [consumer_script, canonical_paths_used]
    rollback_anchor: TASK_SPLIT_SHARED_RESOLVER_SINGLE_OWNER=false
    owner: doc-governance

  - fr_id: FR-05
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[4]
    mapped_business_goal_metrics: [docs_guard_phase1_task_split_compat_exceptions = 0]
    user_value: docs 真正恢复成稳定区
    trigger: docs_guard / doc_sync 扫描 docs
    input_contract:
      required_fields: [file_path, file_name]
      source_of_truth: docs/内部参考/任务拆解
    output_contract:
      required_fields: [is_blocked, violation_reason]
      consumer: 文档守卫 / review / CI
    failure_semantics: docs 下出现 task_split 机器 JSON / 过程 JSON 时直接报错
    observability_fields: [file_path, file_name, violation_reason]
    rollback_anchor: DOC_TASK_SPLIT_JSON_IN_DOCS_BLOCK=false
    owner: doc-governance

  - fr_id: FR-06
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[5]
    mapped_business_goal_metrics: [task_split_canonical_root_count = 1]
    user_value: planning / review / verify / gate 检查说的是同一套路径语言
    trigger: 运行 workflow contract 检查
    input_contract:
      required_fields: [parallel_plan_md, contracts_vk_cards_json, reports_json]
      source_of_truth: workdocs/任务拆解/<task_split_dir>
    output_contract:
      required_fields: [ok, canonical_task_split_dir, files]
      consumer: check_workflow_contract / legacy_wrapper_compat
    failure_semantics: 任一 checker 仍只认 docs 旧 task_split 根时视为桥接未完成
    observability_fields: [mode, canonical_task_split_dir, files]
    rollback_anchor: TASK_SPLIT_WORKFLOW_CONTRACT_UNIFY=false
    owner: doc-governance

  - fr_id: FR-07
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[6]
    mapped_business_goal_metrics: [task_split_machine_json_under_docs = 0]
    user_value: 根级 `contracts/` / `reports/` 保持简洁
    trigger: 新增 contract / report 文件
    input_contract:
      required_fields: [file_path, file_role]
      source_of_truth: contracts / reports / workdocs/任务拆解
    output_contract:
      required_fields: [root_boundary_valid]
      consumer: 文档与工程维护者
    failure_semantics: task_split 私有文件进入根级 `contracts/` / `reports/` 时直接阻断
    observability_fields: [file_path, file_role]
    rollback_anchor: TASK_SPLIT_ROOT_BOUNDARY_FREEZE=false
    owner: doc-governance
```

## 5. NFR 合同矩阵（数字阈值）

```yaml
nfr_contract_matrix:
  - nfr_id: NFR-01
    name: task_split_machine_json_under_docs
    threshold: "0"
    metric_source: docs_task_split_json_scan
  - nfr_id: NFR-02
    name: task_split_canonical_root_count
    threshold: "1"
    metric_source: shared_task_split_resolver.owner_count
  - nfr_id: NFR-03
    name: task_split_path_resolver_impl_count
    threshold: "1"
    metric_source: repo_search.resolve_task_split_dir_owners
  - nfr_id: NFR-04
    name: docs_guard_phase1_task_split_compat_exceptions
    threshold: "0"
    metric_source: docs_guard.phase1_task_split_compat_allowlist
  - nfr_id: NFR-05
    name: task_split_runtime_under_artifacts
    threshold: "100%"
    metric_source: runtime_state_path_audit
```

## 6. 测试用例编号（TC）

```yaml
test_case_matrix:
  - tc_id: TC-DGP2-01
    covers: [FR-01, FR-04, NFR-02, NFR-03]
    acceptance_cmd_ref: rg -n "workdocs/任务拆解|canonical_task_split_dir|legacy_input_used" scripts/task_split_paths.py scripts/coder4/wt-flow.sh scripts/coder4/coder4_bootstrap_kernel.py scripts/coder4/coder4_vk_sync.py
  - tc_id: TC-DGP2-02
    covers: [FR-02]
    acceptance_cmd_ref: rg -n "workdocs/任务拆解/_active_task.json|contracts/_active_task.json|reports/preflight_status.json" scripts/coder4/set_active_task.py
  - tc_id: TC-DGP2-03
    covers: [FR-03, NFR-05]
    acceptance_cmd_ref: find docs/内部参考/任务拆解 -type f | rg -q '(_active_task|vk_cards|preflight_status|consumption_report|gate_contract_report|vktodo_create_result|vksync_status)\.json$' && exit 1 || exit 0
  - tc_id: TC-DGP2-04
    covers: [FR-06]
    acceptance_cmd_ref: rg -n "contracts/vk_cards.json|reports/preflight_status.json|reports/consumption_report.json|reports/gate_contract_report.json|reports/sync" scripts/check_workflow_contract.py scripts/workflow_contract_gate_contract_impl.py scripts/workflow_contract_clarify_plan_impl.py scripts/workflow_contract_plan_vk_coverage_impl.py scripts/coder4/check_integration_gate.py scripts/coder4/coder4_scope_guard.py scripts/check_gate_contract_consistency.py
  - tc_id: TC-DGP2-05
    covers: [FR-05, FR-07, NFR-01, NFR-04]
    acceptance_cmd_ref: PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/docs_guard.py --strict
  - tc_id: TC-DGP2-06
    covers: [FR-05]
    acceptance_cmd_ref: rg -n "目录边界图|执行链流转图|workdocs/任务拆解/.+/contracts|reports/preflight_status.json|docs 不再承载 task_split 机器 JSON" docs/README.md docs/SUMMARY.md workdocs/README.md workdocs/任务拆解/README.md docs/开发文档/流程与工具/文档治理基线清单.md .cursor/rules/doc_sync.mdc
  - tc_id: TC-DGP2-07
    covers: [FR-06]
    acceptance_cmd_ref: PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/check_workflow_contract.py --mode clarify_plan --requirements-path workdocs/归档/需求/docs-governance-phase2-task-split-layering_requirements.md --implementation-path workdocs/归档/实施计划/docs-governance-phase2-task-split-layering_implementation_plan.md --output workdocs/归档/机读校验/docs-governance-phase2-task-split-layering_clarify_plan_alignment.json
  - tc_id: TC-DGP2-08
    covers: [FR-06]
    acceptance_cmd_ref: PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/check_workflow_contract.py --mode planning_temporal_gate --implementation-path workdocs/归档/实施计划/docs-governance-phase2-task-split-layering_implementation_plan.md --output workdocs/归档/机读校验/docs-governance-phase2-task-split-layering_planning_temporal_gate.json
```

## 7. 追溯矩阵（机读）

```yaml
traceability_matrix:
  - task_id: T01
    fr_id: FR-01
    nfr_ids: [NFR-02, NFR-03]
    acceptance_cmd_ref: rg -n "workdocs/任务拆解|canonical_task_split_dir|legacy_input_used" scripts/task_split_paths.py scripts/coder4/wt-flow.sh scripts/coder4/coder4_bootstrap_kernel.py scripts/coder4/coder4_vk_sync.py
  - task_id: T02
    fr_id: FR-02
    nfr_ids: []
    acceptance_cmd_ref: rg -n "workdocs/任务拆解/_active_task.json|contracts/_active_task.json|reports/preflight_status.json" scripts/coder4/set_active_task.py
  - task_id: T03
    fr_id: FR-06
    nfr_ids: [NFR-02]
    acceptance_cmd_ref: rg -n "contracts/vk_cards.json|reports/preflight_status.json|reports/consumption_report.json|reports/gate_contract_report.json|reports/sync" scripts/check_workflow_contract.py scripts/workflow_contract_gate_contract_impl.py scripts/workflow_contract_clarify_plan_impl.py scripts/workflow_contract_plan_vk_coverage_impl.py scripts/coder4/check_integration_gate.py scripts/coder4/coder4_scope_guard.py scripts/check_gate_contract_consistency.py
  - task_id: T04
    fr_id: FR-03
    nfr_ids: [NFR-01, NFR-05]
    acceptance_cmd_ref: find docs/内部参考/任务拆解 -type f | rg -q '(_active_task|vk_cards|preflight_status|consumption_report|gate_contract_report|vktodo_create_result|vksync_status)\.json$' && exit 1 || exit 0
  - task_id: T05
    fr_id: FR-05
    nfr_ids: [NFR-04]
    acceptance_cmd_ref: rg -n "目录边界图|执行链流转图|workdocs/任务拆解/.+/contracts|reports/preflight_status.json|docs 不再承载 task_split 机器 JSON" docs/README.md docs/SUMMARY.md workdocs/README.md workdocs/任务拆解/README.md docs/开发文档/流程与工具/文档治理基线清单.md .cursor/rules/doc_sync.mdc
  - task_id: T06
    fr_id: FR-07
    nfr_ids: [NFR-01]
    acceptance_cmd_ref: PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/check_workflow_contract.py --mode clarify_plan --requirements-path workdocs/归档/需求/docs-governance-phase2-task-split-layering_requirements.md --implementation-path workdocs/归档/实施计划/docs-governance-phase2-task-split-layering_implementation_plan.md --output workdocs/归档/机读校验/docs-governance-phase2-task-split-layering_clarify_plan_alignment.json
```
