# 测试资产治理与单元测试收口实施计划

> 更新时间：2026-03-13
> 上游输入：`workdocs/需求/2026-03-13_test-asset-governance-and-right-sizing/requirements.md`、`workdocs/设计/2026-03-13_test-asset-governance-and-right-sizing/design.md`
> 当前模式：`core`（plan-only，不自动进入执行链）

## 1. 执行策略

这次按“先冻结文档口径和角色判断，再迁脚本型资产，再迁正式回归，再删兼容壳和弱断言，最后补治理门禁”来拆任务。原因很直接：如果先改 `pyproject.toml` 或直接删文件，但文档和 canonical owner 还没冻结，后面的每一步都会重新引入口径漂移。依赖上，`T-01` 必须先完成；`T-02` 和 `T-03` 都依赖 `T-01`，但彼此可以并行；`T-04` 必须等 `T-02/T-03` 基本完成后再做；`T-05` 最后做，因为它消费前面任务的最终收口结果。

唯一推荐并行的是 `T-02` 与 `T-03`。其余步骤都应该串行推进，避免“旧入口没清完、默认入口先切了”的中间态失控。

## 2. 功能机制包

| feature_id | 目标 | 文件锚点 | 核心符号 | 风险点 | 验收主命令 |
|---|---|---|---|---|---|
| TEST-GOV-01 | 冻结测试资产角色与文档真理源口径 | `docs/开发文档/测试管理/测试用例库.md`, `docs/开发文档/测试管理/测试指南与环境配置.md`, `docs/开发文档/测试管理/脚本链路证据注册表.md` | `formal_regression`, `scripted_flow`, `compatibility_entry` | 角色未冻结就开始迁移，导致文档与执行继续打架 | `rg -n "formal_regression|scripted_flow|compatibility_entry|canonical" docs/开发文档/测试管理/测试用例库.md docs/开发文档/测试管理/测试指南与环境配置.md docs/开发文档/测试管理/脚本链路证据注册表.md` |
| TEST-GOV-02 | 脚本型链路验证退出默认 pytest 发现路径 | `app/tests/test_chat.py`, `app/tests/test_complex_scenario.py`, `app/tests/test_minio_connection.py`, `tests/test_*.py`, `scripts/verify/` | `scripted_flow_relocation`, `runtime_prerequisites`, `expected_artifact` | 脚本迁出后没人知道怎么跑或看什么结果 | `rg -n "scripts/verify|前置条件|期望产物|失败判定" docs/开发文档/测试管理/脚本链路证据注册表.md docs/开发文档/测试管理/测试指南与环境配置.md` |
| TEST-GOV-03 | 正式回归收敛到 `tests/**` canonical suite | `app/tests/**`, `tests/unit/**`, `tests/api/**`, `tests/integration/**` | `canonical_suite`, `formal_regression_owner` | `app/tests` 和 `tests` 长期双主入口并存 | `bash scripts/pytest_targeted.sh --collect-only -q tests` |
| TEST-GOV-04 | 退役重复兼容壳并处理弱断言资产 | `tests/unit/test_todo_graph_semantic_guard.py`, `app/tests/test_todo_multiround.py` | `single_entry_owner`, `machine_observable_pass_fail` | 重复收集和打印式测试继续混进正式回归 | `bash scripts/pytest_targeted.sh --collect-only -q tests/unit/test_todo_nodes.py` |
| TEST-GOV-05 | 收口 pytest 默认入口并补防回流门禁 | `pyproject.toml`, `tests/unit/test_test_asset_governance_contract.py` | `testpaths`, `return_not_none_guard`, `governance_contract` | 当前问题收掉了，但后续又从新文件回流 | `bash scripts/pytest_targeted.sh tests/unit/test_test_asset_governance_contract.py -q` |

## 3. implementation_tasks

```yaml
implementation_tasks:
  - task_id: T-01
    feature_id: TEST-GOV-01
    design_item_refs: [D-01]
    requirement_ids: [FR-01, FR-05, FR-07, NFR-01, NFR-04, NFR-05]
    goal: 冻结测试资产三类角色和文档 owner，让后续迁移都以同一套 canonical 口径为准。
    file_paths:
      - docs/开发文档/测试管理/测试用例库.md
      - docs/开发文档/测试管理/测试指南与环境配置.md
      - docs/开发文档/测试管理/脚本链路证据注册表.md
      - docs/产品文档/待办助手需求.md
      - docs/产品文档/问数助手需求.md
      - workdocs/需求/2026-03-13_test-asset-governance-and-right-sizing/requirements.md
    symbols:
      - formal_regression
      - scripted_flow
      - compatibility_entry
      - canonical_owner
      - traceability_matrix
    module_changes:
      - 在测试用例库中明确三类资产角色、canonical owner 和风险矩阵入口。
      - 在测试指南中区分正式回归命令与脚本型验证命令。
      - 在脚本链路证据注册表中补齐脚本型资产的前置条件、执行命令、期望产物和失败判定。
      - 更新受影响产品文档，避免继续把问题文件路径当成唯一测试入口。
      - 回填 requirements.traceability_matrix，形成需求到设计、任务、UAT 的完整链路。
    deletion_actions:
      - 删除产品文档和测试指南里“默认把脚本型文件当正式 pytest 入口”的表述。
    risk_tags: [docs, contract, traceability]
    mandatory_evidence: [asset_roles_visible, scripted_flow_registry_synced, product_docs_canonicalized, requirements_traceability_backfilled]
    acceptance_cmds:
      - kind: scripted_flow
        cmd: rg -n "formal_regression|scripted_flow|compatibility_entry|canonical" docs/开发文档/测试管理/测试用例库.md docs/开发文档/测试管理/测试指南与环境配置.md docs/开发文档/测试管理/脚本链路证据注册表.md
      - kind: scripted_flow
        cmd: rg -n "TODO-TC-004|QS-TC-001|脚本型链路验证|正式回归" docs/产品文档/待办助手需求.md docs/产品文档/问数助手需求.md docs/开发文档/测试管理/测试指南与环境配置.md

  - task_id: T-02
    feature_id: TEST-GOV-02
    design_item_refs: [D-02]
    requirement_ids: [FR-03, FR-05, NFR-05]
    goal: 把脚本型链路验证从默认 pytest 发现路径剥离出来，同时保留独立执行价值和证据链。
    file_paths:
      - app/tests/test_chat.py
      - app/tests/test_complex_scenario.py
      - app/tests/test_minio_connection.py
      - tests/test_ask_data_flow.py
      - tests/test_shortcuts.py
      - tests/test_todo_complex_flow.py
      - tests/test_todo_comprehensive_suite.py
      - tests/test_todo_e2e_real.py
      - tests/test_vanna_retrieval.py
      - scripts/verify/chat_stream_smoke.py
      - scripts/verify/todo_complex_scenario.py
      - scripts/verify/minio_connection.py
      - scripts/verify/ask_data_flow.py
      - scripts/verify/todo_shortcuts.py
      - scripts/verify/todo_complex_flow.py
      - scripts/verify/todo_comprehensive_suite.py
      - scripts/verify/todo_e2e_real.py
      - scripts/verify/vanna_retrieval.py
    symbols:
      - scripted_flow_relocation
      - preconditions
      - expected_artifact
      - failure_judgement
    module_changes:
      - 将脚本型 `test_*.py` 文件迁入 `scripts/verify/`，退出默认 pytest 发现路径。
      - 统一脚本文件命名和入口说明，使其不再冒充正式回归。
      - 为每条脚本型资产补全前置条件、期望产物和失败判定。
    deletion_actions:
      - 删除原 `app/tests`、`tests/` 下脚本型 `test_*.py` 文件的正式发现角色。
    risk_tags: [scripted_flow, external_dependency, docs]
    mandatory_evidence: [scripted_files_moved, verify_commands_documented, default_discovery_cleaned]
    acceptance_cmds:
      - kind: scripted_flow
        cmd: rg -n "scripts/verify/|前置条件|期望产物|失败判定" docs/开发文档/测试管理/脚本链路证据注册表.md docs/开发文档/测试管理/测试指南与环境配置.md
      - kind: scripted_flow
        cmd: rg -n "^if __name__ == \"__main__\":|def test_" scripts/verify/*.py

  - task_id: T-03
    feature_id: TEST-GOV-03
    design_item_refs: [D-03]
    requirement_ids: [FR-01, FR-06, NFR-01, NFR-06]
    goal: 把仍有价值的 `app/tests` 正式回归迁入 `tests/unit|api|integration`，让正式回归有唯一 canonical 主入口。
    file_paths:
      - app/tests/test_data_agent.py
      - app/tests/test_handoff_detection.py
      - app/tests/test_health.py
      - app/tests/test_middlewares.py
      - app/tests/test_skill_loader_tool.py
      - app/tests/test_skill_catalog_manifest.py
      - app/tests/test_skill_runtime_mode_switch.py
      - app/tests/test_skill_runtime_replay.py
      - app/tests/test_todo_db_integration.py
      - app/tests/test_todo_graph_integration.py
      - app/tests/test_user.py
      - tests/unit/test_data_agent.py
      - tests/unit/test_handoff_detection.py
      - tests/unit/test_health.py
      - tests/unit/test_middlewares.py
      - tests/unit/test_skill_loader_tool.py
      - tests/unit/test_skill_catalog_manifest.py
      - tests/unit/test_skill_runtime_mode_switch.py
      - tests/unit/test_skill_runtime_replay.py
      - tests/integration/test_todo_db_integration.py
      - tests/integration/test_todo_graph_integration.py
      - tests/api/test_user.py
    symbols:
      - canonical_suite
      - formal_regression_owner
      - suite_layering
    module_changes:
      - 将活跃正式回归按语义层级迁移到 `tests/unit`、`tests/api`、`tests/integration`。
      - 更新共享 fixture 和导入方式，确保迁移后仍能通过 canonical suite 执行。
      - 收掉 `app/tests` 作为默认正式回归主入口的职责。
    deletion_actions:
      - 删除迁移完成后 `app/tests` 中对应正式回归文件。
    risk_tags: [suite_layout, regression, import]
    mandatory_evidence: [canonical_regressions_moved, app_tests_main_role_removed, migrated_suite_collects]
    acceptance_cmds:
      - kind: scripted_flow
        cmd: bash scripts/repo_python.sh
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh --collect-only -q tests
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh tests/unit/test_data_agent.py tests/unit/test_handoff_detection.py tests/unit/test_health.py tests/unit/test_middlewares.py tests/unit/test_skill_loader_tool.py tests/unit/test_skill_catalog_manifest.py tests/unit/test_skill_runtime_mode_switch.py tests/unit/test_skill_runtime_replay.py tests/integration/test_todo_db_integration.py tests/integration/test_todo_graph_integration.py tests/api/test_user.py -q

  - task_id: T-04
    feature_id: TEST-GOV-04
    design_item_refs: [D-04]
    requirement_ids: [FR-02, FR-04, NFR-02, NFR-03]
    goal: 清除重复兼容壳和弱断言 pytest 资产，让正式回归只留下有清晰失败语义的入口。
    file_paths:
      - tests/unit/test_todo_graph_semantic_guard.py
      - tests/unit/test_todo_nodes.py
      - app/tests/test_todo_multiround.py
      - tests/unit/test_todo_multiround_contract.py
      - scripts/verify/todo_multiround.py
    symbols:
      - single_entry_owner
      - machine_observable_pass_fail
      - weak_assertion_cleanup
    module_changes:
      - 删除 `tests/unit/test_todo_graph_semantic_guard.py` 这类只承载重复 owner 的兼容壳。
      - 将 `app/tests/test_todo_multiround.py` 中弱断言测试重写为真正 contract test，或降级到 `scripts/verify/`。
      - 明确 `tests/unit/test_todo_nodes.py` 作为待办语义相关 canonical owner。
    deletion_actions:
      - 删除重复收集入口。
      - 删除或降级返回布尔值、仅打印日志的 pytest 测试。
    risk_tags: [duplicate_owner, weak_assertion, contract]
    mandatory_evidence: [compat_shell_removed, weak_pytests_reworked, todo_owner_singleton]
    acceptance_cmds:
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh --collect-only -q tests/unit/test_todo_nodes.py
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh tests/unit/test_todo_nodes.py -q
      - kind: scripted_flow
        cmd: rg -n "return all\\(|print\\(|if __name__ == \"__main__\":" tests/unit/test_todo_multiround_contract.py scripts/verify/todo_multiround.py

  - task_id: T-05
    feature_id: TEST-GOV-05
    design_item_refs: [D-05]
    requirement_ids: [FR-02, FR-06, FR-07, NFR-02, NFR-03, NFR-06]
    goal: 在完成收口后切换默认 pytest 入口，并补一条轻量治理门禁，防止脚本型资产和弱断言回流。
    file_paths:
      - pyproject.toml
      - tests/unit/test_test_asset_governance_contract.py
      - docs/开发文档/测试管理/测试指南与环境配置.md
    symbols:
      - testpaths
      - return_not_none_guard
      - governance_contract
    module_changes:
      - 将 `tool.pytest.ini_options.testpaths` 收敛到 `tests`。
      - 新增轻量 contract test，静态检查默认入口、重复兼容壳和典型弱测试回流。
      - 更新测试指南，确保默认命令和 canonical suite 口径一致。
    deletion_actions:
      - 删除 `app/tests` 在默认正式回归命令中的主入口地位。
    risk_tags: [config, governance_gate, regression]
    mandatory_evidence: [testpaths_canonicalized, governance_contract_green, default_commands_synced]
    acceptance_cmds:
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh tests/unit/test_test_asset_governance_contract.py -q
      - kind: scripted_flow
        cmd: rg -n 'testpaths = \\["tests"\\]' pyproject.toml
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh --collect-only -q tests
```

## 4. db_migration_plan

```yaml
db_migration_plan:
  db_migration_required: false
  dev_migration_cmd: none
  release_migration_cmd: none
  mandatory_evidence: []
```

## 5. execution_contract

```yaml
execution_contract:
  preferred_mode: core
  execution_contract_ready: true
  delivery_mode: staged
  execution_unit: per_task
  commit_policy: single_commit
  stop_boundary: per_task
  temporal_gate_forbidden: true
  context_verified: true
  design_source: workdocs/设计/2026-03-13_test-asset-governance-and-right-sizing/design.md
  requirements_source: workdocs/需求/2026-03-13_test-asset-governance-and-right-sizing/requirements.md
```

## 6. implementation_readiness

```yaml
implementation_readiness:
  implementation_ready: true
  execution_contract_ready: true
  requirements_ready: true
  traceability_ready: true
  blocking_issue_count: 0
  readiness_note: can_execute_in_five_staged_tasks
```
