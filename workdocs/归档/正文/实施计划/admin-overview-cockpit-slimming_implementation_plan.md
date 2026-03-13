# admin-overview-cockpit-slimming 实施方案

> 更新时间：2026-03-10 21:21 CST
> 上游设计：`workdocs/归档/正文/设计/2026-03-10-admin-overview-cockpit-slimming-design.md`
> 关联需求：`workdocs/归档/正文/需求/admin-overview-cockpit-slimming_requirements.md`

## 1. 实施概览

- 执行模式：`core + serial`，按“先文档冻结 -> 再后端 contract 收敛 -> 再前端页面收口 -> 最后测试与门禁”推进。
- 核心取舍：本轮不是增加新能力，而是删除重复块与占位块，所以优先收口 contract 和页面结构，而不是先修补局部卡片。
- 冲突说明：`$jjk-plan` 新规则要求 `acceptance_cmds[*]` 使用 `kind/cmd` 对象；但仓内 `clarify_plan` 既有校验器仍只接受字符串命令列表。为保证当前强门禁可通过，本文件的 `implementation_tasks.acceptance_cmds` 保持**字符串列表**，同时在 `acceptance_cmd_registry` 额外镜像结构化 `kind/cmd`，作为下游迁移桥。取舍理由：当前仓内 gate 是实际阻断器，更可验证；风险：后续需要统一两个 acceptance contract。

## 2. implementation_tasks（机读）

```yaml
implementation_tasks:
  - task_id: T-01
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[0]
    feature_id: P1-01
    phase: Phase-1
    change_type: modify
    owner: docs-governance
    pr_id: PR-01
    risk_point: 若需求/API/前端架构文档不先收敛，代码改完后会继续出现首页口径漂移
    rollback_point: revert:overview-doc-contract-freeze
    depends_on_tasks: [DESIGN-APPROVED]
    file_paths:
      - docs/产品文档/管理后台需求.md
      - docs/API文档/接口文档.md
      - docs/开发文档/架构设计/前端架构.md
    symbols:
      - admin_overview section
      - AdminOverviewCockpit section
    risk_tags: [contract, docs]
    mandatory_evidence: [docs_source_updated, slimming_contract_frozen]
    acceptance_cmds:
      - rg -n "总览驾驶舱|提问链路健康|告警概览|24h 流量趋势" docs/产品文档/管理后台需求.md docs/API文档/接口文档.md docs/开发文档/架构设计/前端架构.md

  - task_id: T-02
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[1]
    feature_id: P2-01
    phase: Phase-2
    change_type: refactor
    owner: admin-platform
    pr_id: PR-02
    risk_point: 后端 contract 若只删 UI 不删 schema/service，旧字段会继续漂移并污染 stream patch
    rollback_point: ENABLE_ADMIN_OVERVIEW_SLIM_V2=false
    depends_on_tasks: [T-01]
    file_paths:
      - app/services/admin_overview_query_service.py
      - app/schemas/admin_overview.py
      - app/api/v1/endpoints/admin_overview_api.py
    symbols:
      - AdminOverviewQueryService
      - AdminOverviewSnapshot
      - admin overview summary/trends/stream
    risk_tags: [contract, api]
    mandatory_evidence: [summary_contract_slimmed, api_contract_green]
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_admin_overview_query_service.py -q
      - bash scripts/pytest_targeted.sh tests/unit/test_admin_overview_query_service.py -q -k question
      - bash scripts/pytest_targeted.sh tests/unit/test_admin_overview_query_service.py -q -k alerts
      - bash scripts/pytest_targeted.sh tests/api/test_admin_overview_api.py -q -k freshness

  - task_id: T-03
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[2]
    feature_id: P3-01
    phase: Phase-3
    change_type: refactor
    owner: web-admin
    pr_id: PR-03
    risk_point: 前端若继续保留旧 badge 语义和旧卡片布局，会出现“预警 + 正常”双重表达和死字段渲染
    rollback_point: ENABLE_ADMIN_OVERVIEW_SLIM_V2=false
    depends_on_tasks: [T-02]
    file_paths:
      - web/src/types/admin-overview.ts
      - web/src/lib/admin-overview-api.ts
      - web/src/components/admin/overview/AdminOverviewCockpit.tsx
    symbols:
      - AdminOverviewSnapshot
      - normalizeSummaryPayload
      - AdminOverviewCockpit
    risk_tags: [contract, ui]
    mandatory_evidence: [ui_layout_slimmed, badge_conflict_removed]
    acceptance_cmds:
      - bash scripts/repo_python.sh >/dev/null && pnpm -C web exec tsc --noEmit
      - bash scripts/repo_python.sh >/dev/null && eval "$(bash scripts/vk_ports.sh --export)" && PLAYWRIGHT_BASE_URL="$VK_FRONTEND_BASE_URL" E2E_API_BASE="$VK_BACKEND_BASE_URL" PLAYWRIGHT_REUSE_EXISTING_SERVER=false pnpm -C web exec playwright test e2e/features/admin-overview.feature.cjs --project=chromium

  - task_id: T-04
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[3]
    feature_id: P4-01
    phase: Phase-4
    change_type: modify
    owner: qa-governance
    pr_id: PR-04
    risk_point: 如果不把测试、承接校验和规划门禁一起收口，文档与实现会再次失配
    rollback_point: revert:overview-plan-gates
    depends_on_tasks: [T-02, T-03]
    file_paths:
      - tests/unit/test_admin_overview_query_service.py
      - tests/api/test_admin_overview_api.py
      - web/e2e/features/admin-overview.feature.cjs
      - docs/开发文档/测试管理/管理后台测试案例.md
      - workdocs/归档/正文/需求/admin-overview-cockpit-slimming_requirements.md
      - workdocs/归档/正文/实施计划/admin-overview-cockpit-slimming_implementation_plan.md
    symbols:
      - test_admin_overview_query_service
      - test_admin_overview_api
      - AdminOverviewCockpit
      - clarify_plan gate
      - planning_temporal_gate
    risk_tags: [test, regression, scripted_flow]
    mandatory_evidence: [clarify_plan_alignment_json, planning_temporal_gate_json, scripted_flow]
    acceptance_cmds:
      - python3 scripts/check_workflow_contract.py --mode clarify_plan --requirements-path workdocs/归档/正文/需求/admin-overview-cockpit-slimming_requirements.md --implementation-path workdocs/归档/正文/实施计划/admin-overview-cockpit-slimming_implementation_plan.md --output workdocs/归档/报告/机读校验/admin-overview-cockpit-slimming_clarify_plan_alignment.json
      - python3 scripts/check_workflow_contract.py --mode planning_temporal_gate --implementation-path workdocs/归档/正文/实施计划/admin-overview-cockpit-slimming_implementation_plan.md --output workdocs/归档/报告/机读校验/admin-overview-cockpit-slimming_planning_temporal_gate.json
      - python3 scripts/docs_guard.py --strict
```

## 3. acceptance_cmd_registry（结构化镜像，供下游迁移）

```yaml
acceptance_cmd_registry:
  - task_id: T-01
    acceptance_cmds:
      - kind: scripted_flow
        cmd: rg -n "总览驾驶舱|提问链路健康|告警概览|24h 流量趋势" docs/产品文档/管理后台需求.md docs/API文档/接口文档.md docs/开发文档/架构设计/前端架构.md
  - task_id: T-02
    acceptance_cmds:
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh tests/unit/test_admin_overview_query_service.py -q
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh tests/unit/test_admin_overview_query_service.py -q -k question
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh tests/unit/test_admin_overview_query_service.py -q -k alerts
      - kind: api
        cmd: bash scripts/pytest_targeted.sh tests/api/test_admin_overview_api.py -q -k freshness
  - task_id: T-03
    acceptance_cmds:
      - kind: typecheck
        cmd: bash scripts/repo_python.sh >/dev/null && pnpm -C web exec tsc --noEmit
      - kind: e2e
        cmd: bash scripts/repo_python.sh >/dev/null && eval "$(bash scripts/vk_ports.sh --export)" && PLAYWRIGHT_BASE_URL="$VK_FRONTEND_BASE_URL" E2E_API_BASE="$VK_BACKEND_BASE_URL" PLAYWRIGHT_REUSE_EXISTING_SERVER=false pnpm -C web exec playwright test e2e/features/admin-overview.feature.cjs --project=chromium
  - task_id: T-04
    acceptance_cmds:
      - kind: integration
        cmd: python3 scripts/check_workflow_contract.py --mode clarify_plan --requirements-path workdocs/归档/正文/需求/admin-overview-cockpit-slimming_requirements.md --implementation-path workdocs/归档/正文/实施计划/admin-overview-cockpit-slimming_implementation_plan.md --output workdocs/归档/报告/机读校验/admin-overview-cockpit-slimming_clarify_plan_alignment.json
      - kind: integration
        cmd: python3 scripts/check_workflow_contract.py --mode planning_temporal_gate --implementation-path workdocs/归档/正文/实施计划/admin-overview-cockpit-slimming_implementation_plan.md --output workdocs/归档/报告/机读校验/admin-overview-cockpit-slimming_planning_temporal_gate.json
      - kind: scripted_flow
        cmd: python3 scripts/docs_guard.py --strict
```

## 4. task_to_pr_mapping（机读）

```yaml
task_to_pr_mapping:
  - task_id: T-01
    pr_id: PR-01
    pr_branch: codex/admin-overview-slimming-pr-01
    pr_depends_on: []
    pr_subject: "P1 文档真理源收敛：首页精简合同冻结"
    acceptance_cmds:
      - rg -n "总览驾驶舱|提问链路健康|告警概览|24h 流量趋势" docs/产品文档/管理后台需求.md docs/API文档/接口文档.md docs/开发文档/架构设计/前端架构.md
    rollback_point: revert:overview-doc-contract-freeze

  - task_id: T-02
    pr_id: PR-02
    pr_branch: codex/admin-overview-slimming-pr-02
    pr_depends_on: [PR-01]
    pr_subject: "P2 后端 contract 收敛：删除重复首页块与占位字段"
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_admin_overview_query_service.py -q
      - bash scripts/pytest_targeted.sh tests/api/test_admin_overview_api.py -q -k freshness
    rollback_point: ENABLE_ADMIN_OVERVIEW_SLIM_V2=false

  - task_id: T-03
    pr_id: PR-03
    pr_branch: codex/admin-overview-slimming-pr-03
    pr_depends_on: [PR-02]
    pr_subject: "P3 前端收口：新首页布局与 badge 语义简化"
    acceptance_cmds:
      - bash scripts/repo_python.sh >/dev/null && pnpm -C web exec tsc --noEmit
      - bash scripts/repo_python.sh >/dev/null && eval "$(bash scripts/vk_ports.sh --export)" && PLAYWRIGHT_BASE_URL="$VK_FRONTEND_BASE_URL" E2E_API_BASE="$VK_BACKEND_BASE_URL" PLAYWRIGHT_REUSE_EXISTING_SERVER=false pnpm -C web exec playwright test e2e/features/admin-overview.feature.cjs --project=chromium
    rollback_point: ENABLE_ADMIN_OVERVIEW_SLIM_V2=false

  - task_id: T-04
    pr_id: PR-04
    pr_branch: codex/admin-overview-slimming-pr-04
    pr_depends_on: [PR-02, PR-03]
    pr_subject: "P4 测试与门禁收口：承接校验、规划门禁、文档门禁"
    acceptance_cmds:
      - python3 scripts/check_workflow_contract.py --mode clarify_plan --requirements-path workdocs/归档/正文/需求/admin-overview-cockpit-slimming_requirements.md --implementation-path workdocs/归档/正文/实施计划/admin-overview-cockpit-slimming_implementation_plan.md --output workdocs/归档/报告/机读校验/admin-overview-cockpit-slimming_clarify_plan_alignment.json
      - python3 scripts/check_workflow_contract.py --mode planning_temporal_gate --implementation-path workdocs/归档/正文/实施计划/admin-overview-cockpit-slimming_implementation_plan.md --output workdocs/归档/报告/机读校验/admin-overview-cockpit-slimming_planning_temporal_gate.json
      - python3 scripts/docs_guard.py --strict
    rollback_point: revert:overview-plan-gates
```

## 5. planning_contract（机读）

```yaml
planning_contract:
  execution_mode: serial
  strict_single_active_card: true
  card_order: [C01, C02, C03, C04]
  compatibility_note: implementation_tasks.acceptance_cmds 保持字符串列表以兼容当前 clarify_plan gate；结构化 kind/cmd 镜像见 acceptance_cmd_registry
  cards:
    - card_id: C01
      task_id: T-01
      wave: P1
      depends_on: []
    - card_id: C02
      task_id: T-02
      wave: P2
      depends_on: [C01]
    - card_id: C03
      task_id: T-03
      wave: P3
      depends_on: [C02]
    - card_id: C04
      task_id: T-04
      wave: P4
      depends_on: [C02, C03]
```

## 6. execution_contract（机读）

```yaml
execution_contract:
  preferred_mode: core
  execution_contract_ready: true
  delivery_mode: staged
  execution_unit: all_tasks
  commit_policy: single_commit
  stop_boundary: per_task
  temporal_gate_forbidden: true
  context_verified: true
  design_source: workdocs/归档/正文/设计/2026-03-10-admin-overview-cockpit-slimming-design.md
  requirements_source: workdocs/归档/正文/需求/admin-overview-cockpit-slimming_requirements.md
```

## 7. implementation_readiness（机读）

```yaml
implementation_readiness:
  implementation_ready: true
  execution_contract_ready: true
  requirements_ready: true
  traceability_ready: true
  blocked_by: []
  next_step: /jjk-imp
  readiness_note: approved_design_and_hydrated_tasks
```

## 8. tc_execution_mapping

```yaml
tc_execution_mapping:
  - tc_id: TC-01
    task_id: T-01
    pr_id: PR-01
  - tc_id: TC-02
    task_id: T-02
    pr_id: PR-02
  - tc_id: TC-03
    task_id: T-02
    pr_id: PR-02
  - tc_id: TC-04
    task_id: T-02
    pr_id: PR-02
  - tc_id: TC-05
    task_id: T-02
    pr_id: PR-02
  - tc_id: TC-06
    task_id: T-03
    pr_id: PR-03
  - tc_id: TC-07
    task_id: T-03
    pr_id: PR-03
  - tc_id: TC-08
    task_id: T-04
    pr_id: PR-04
```
