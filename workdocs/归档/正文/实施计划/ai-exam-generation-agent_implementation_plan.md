# ai-exam-generation-agent 实施计划

> 更新时间：2026-03-11 23:59 CST
> 上游设计：`workdocs/归档/正文/设计/2026-03-11-ai-exam-generation-agent-design.md`
> 需求文档：`workdocs/归档/正文/需求/ai-exam-generation-agent_requirements.md`
> 文档目标：定义 HOW（任务拆解、PR 承接、执行合同与实施就绪状态）

## 1. 实施策略结论

- 执行模式采用 `core + serial`，原因是本能力虽为独立模块，但 `API/任务表/工作流/PDF/前端历史页` 在语义上强耦合，串行更容易控制质量门禁和结果 canonical。
- 任务分 4 波次：
  1. **基础契约与后台 API**
  2. **任务表与服务编排**
  3. **工作流、质量门禁与 PDF 导出**
  4. **前端、测试、文档与规划收口**
- 下游推荐直接进入 `$jjk-imp`，无需再拆 `$jjk-vkplan`。

## 2. implementation_tasks

```yaml
implementation_tasks:
  - task_id: T01
    feature_id: F1-admin-api-and-access
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[0]
    phase: Phase-1
    pr_id: PR-01
    change_type: new_feature
    owner: exam-platform
    depends_on_tasks: [DESIGN-APPROVED]
    risk_point: 若后台入口直接复用聊天 API 或权限校验缺位，会破坏低耦合目标并放大误用风险
    risk_tags: [contract]
    mandatory_evidence: [admin_api_surface_frozen, access_policy_denied_visible]
    rollback_point: feature.enable_exam_generation_admin=false
    file_paths:
      - app/api/v1/endpoints/exam_admin_api.py
      - app/api/v1/router.py
      - docs/API文档/接口文档.md
    symbols:
      - exam_admin_router
      - create_job
      - get_job
      - list_jobs
      - download_export
      - access_policy
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/api/test_exam_admin_api.py -q -k "create_job or list_jobs or access_policy"
        kind: api
      - bash scripts/pytest_targeted.sh tests/api/test_exam_admin_api.py -q -k download_export
        kind: api

  - task_id: T02
    feature_id: F2-contract-and-template
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[1]
    phase: Phase-1
    pr_id: PR-01
    change_type: new_feature
    owner: exam-platform
    depends_on_tasks: [T01]
    risk_point: 若模板合同与 Paper Contract 不统一，前后端和 PDF 渲染会长出双轨字段
    risk_tags: [contract]
    mandatory_evidence: [template_contract_single_source, paper_contract_schema_green]
    rollback_point: feature.enable_exam_generation_template=true
    file_paths:
      - app/schemas/exam_generation.py
      - docs/开发文档/架构设计/AI模块设计.md
    symbols:
      - PaperTemplateRequest
      - PaperContract
      - ExamGenerationResult
      - ExamQualityReport
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_exam_generation_contracts.py -q
        kind: unit
      - bash scripts/pytest_targeted.sh tests/api/test_exam_admin_api.py -q -k template
        kind: api

  - task_id: T03
    feature_id: F3-job-persistence-and-history
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[2]
    phase: Phase-2
    pr_id: PR-02
    change_type: new_feature
    owner: exam-platform
    depends_on_tasks: [T02]
    risk_point: 若任务快照与 MinIO 资产引用不落库，历史记录将不可回放且下载不可追溯
    risk_tags: [chat_db, migration]
    mandatory_evidence: [chat_db_write_read, chat_db_job_snapshot_roundtrip, minio_export_binding_present]
    rollback_point: feature.enable_exam_generation_job_persist=false
    file_paths:
      - app/models/exam_generation_job.py
      - app/repositories/exam_generation_job_repo.py
      - alembic/versions/<new_revision>.py
    symbols:
      - ExamGenerationJob
      - result_payload
      - request_snapshot
      - minio_object_key
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_exam_generation_job_repo.py -q
        kind: chat_db
      - bash scripts/pytest_targeted.sh tests/api/test_exam_admin_api.py -q -k history
        kind: api

  - task_id: T04
    feature_id: F4-service-orchestration-and-policy
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[3]
    phase: Phase-2
    pr_id: PR-02
    change_type: new_feature
    owner: exam-platform
    depends_on_tasks: [T03]
    risk_point: 若服务层同时承担过多路由/校验/渲染逻辑，会重新长出难以维护的大服务
    risk_tags: [contract, chat_db]
    mandatory_evidence: [chat_db_write_read, access_policy_limit_enforced, template_snapshot_roundtrip]
    rollback_point: feature.enable_exam_generation_access_policy=false
    file_paths:
      - app/services/exam_generation_service.py
      - app/services/exam_template_service.py
    symbols:
      - create_job
      - run_job
      - list_jobs
      - build_default_template
      - enforce_access_policy
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_exam_generation_service.py -q -k "create_job or access_policy or template"
        kind: unit
      - bash scripts/pytest_targeted.sh tests/unit/test_exam_generation_service.py -q -k job_snapshot
        kind: chat_db

  - task_id: T05
    feature_id: F5-workflow-and-quality-gate
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[4]
    phase: Phase-3
    pr_id: PR-03
    change_type: new_feature
    owner: ai-runtime
    depends_on_tasks: [T04]
    risk_point: 若多数据集优先级、冲突语义与质量门禁未收敛，系统会输出看似成功但不可用的题单
    risk_tags: [agent_contract, quality_gate]
    mandatory_evidence: [dataset_priority_resolved, evidence_coverage_100, quality_gate_blocks_invalid_paper]
    rollback_point: feature.enable_exam_generation_quality_gate=false
    file_paths:
      - app/ai/workflow/exam_generation_workflow.py
      - app/ai/tools/ragflow_tool.py
    symbols:
      - generate_paper_contract
      - retrieve_exam_evidence
      - resolve_dataset_priority
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_exam_generation_workflow.py -q
        kind: unit
      - bash scripts/pytest_targeted.sh tests/unit/test_exam_generation_service.py -q -k "quality_gate or dataset_priority or conflict"
        kind: integration

  - task_id: T06
    feature_id: F6-pdf-render-and-export
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[5]
    phase: Phase-3
    pr_id: PR-03
    change_type: new_feature
    owner: exam-platform
    depends_on_tasks: [T05]
    risk_point: 若 PDF 渲染在质量门禁前执行或分页规则不稳定，会生成不可打印的半成品导出
    risk_tags: [render_contract, asset_export]
    mandatory_evidence: [pdf_pagination_clean, answer_section_page_break, export_asset_downloadable]
    rollback_point: feature.enable_exam_generation_pdf=false
    file_paths:
      - app/services/pdf_render_service.py
      - app/templates/exam_pdf/base.html
      - app/templates/exam_pdf/styles.css
      - pyproject.toml
    symbols:
      - render_exam_pdf
      - quality_gate_before_render
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_pdf_render_service.py -q
        kind: unit
      - bash scripts/pytest_targeted.sh tests/unit/test_exam_generation_service.py -q -k pdf_export
        kind: integration

  - task_id: T07
    feature_id: F7-admin-ui-and-history
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[6]
    phase: Phase-4
    pr_id: PR-04
    change_type: new_feature
    owner: frontend-admin
    depends_on_tasks: [T03, T04, T06]
    risk_point: 若前端把历史记录或下载状态保存在本地内存而不是读 canonical，会导致刷新后状态漂移
    risk_tags: [ui_contract, replay_contract]
    mandatory_evidence: [history_list_replay_consistent, direct_download_visible, question_limit_hint_visible]
    rollback_point: feature.enable_exam_generation_admin=false
    file_paths:
      - web/src/app/admin/exam-generation/page.tsx
      - web/src/components/admin/ExamGenerationPanel.tsx
      - web/src/lib/backend.ts
    symbols:
      - ExamGenerationPage
      - ExamHistoryList
      - submitExamJob
      - downloadExamExport
      - questionLimitHint
    acceptance_cmds:
      - pnpm --dir web test -- --runInBand ExamGenerationPanel
        kind: unit
      - pnpm --dir web exec playwright test e2e/admin-exam-generation.spec.cjs
        kind: e2e

  - task_id: T08
    feature_id: F8-tests-docs-and-planning-gates
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[7]
    phase: Phase-4
    pr_id: PR-04
    change_type: new_feature
    owner: qa-governance
    depends_on_tasks: [T01, T02, T03, T04, T05, T06, T07]
    risk_point: 若测试与文档只覆盖 happy path，质量门禁、多数据集冲突、历史回放与权限限流会在后续演进中漂移
    risk_tags: [docs_sync, regression_gate]
    mandatory_evidence: [clarify_plan_alignment, temporal_gate_clean, docs_guard_clean]
    rollback_point: revert:exam-generation-docs-and-tests
    file_paths:
      - tests/unit/test_exam_generation_service.py
      - tests/unit/test_pdf_render_service.py
      - tests/unit/test_exam_admin_api.py
      - docs/开发文档/测试管理/<new_doc>.md
    symbols:
      - service_contract_tests
      - pagination_tests
      - api_tests
      - quality_gate_tests
      - access_policy_tests
    acceptance_cmds:
      - bash scripts/pytest_targeted.sh tests/unit/test_exam_generation_service.py tests/unit/test_pdf_render_service.py -q
        kind: unit
      - bash scripts/pytest_targeted.sh tests/api/test_exam_admin_api.py -q
        kind: api
      - pnpm --dir web exec playwright test e2e/admin-exam-generation.spec.cjs
        kind: e2e
      - python3 scripts/docs_guard.py --strict
        kind: integration
```

## 3. task_to_pr_mapping

```yaml
planning_contract:
  task_to_pr_mapping:
    - task_id: T01
      pr_id: PR-01
      pr_branch: codex/ai-exam-generation-pr-01
      pr_depends_on: []
      pr_subject: "P1 后台 API、模板合同与访问策略入口"
      acceptance_cmds:
        - bash scripts/pytest_targeted.sh tests/api/test_exam_admin_api.py -q -k "create_job or list_jobs or access_policy or template"
      rollback_point: feature.enable_exam_generation_admin=false

    - task_id: T02
      pr_id: PR-01
      pr_branch: codex/ai-exam-generation-pr-01
      pr_depends_on: []
      pr_subject: "P1 模板/Paper Contract 合同与架构文档同步"
      acceptance_cmds:
        - bash scripts/pytest_targeted.sh tests/unit/test_exam_generation_contracts.py -q
      rollback_point: feature.enable_exam_generation_template=true

    - task_id: T03
      pr_id: PR-02
      pr_branch: codex/ai-exam-generation-pr-02
      pr_depends_on: [PR-01]
      pr_subject: "P2 任务表、历史记录与 MinIO 资产绑定"
      acceptance_cmds:
        - bash scripts/pytest_targeted.sh tests/unit/test_exam_generation_job_repo.py -q
        - bash scripts/pytest_targeted.sh tests/api/test_exam_admin_api.py -q -k history
      rollback_point: feature.enable_exam_generation_job_persist=false

    - task_id: T04
      pr_id: PR-02
      pr_branch: codex/ai-exam-generation-pr-02
      pr_depends_on: [PR-01]
      pr_subject: "P2 服务编排、模板快照与访问限流"
      acceptance_cmds:
        - bash scripts/pytest_targeted.sh tests/unit/test_exam_generation_service.py -q -k "create_job or access_policy or template or job_snapshot"
      rollback_point: feature.enable_exam_generation_access_policy=false

    - task_id: T05
      pr_id: PR-03
      pr_branch: codex/ai-exam-generation-pr-03
      pr_depends_on: [PR-02]
      pr_subject: "P3 出题工作流、多数据集优先级与质量门禁"
      acceptance_cmds:
        - bash scripts/pytest_targeted.sh tests/unit/test_exam_generation_workflow.py -q
        - bash scripts/pytest_targeted.sh tests/unit/test_exam_generation_service.py -q -k "quality_gate or dataset_priority or conflict"
      rollback_point: feature.enable_exam_generation_quality_gate=false

    - task_id: T06
      pr_id: PR-03
      pr_branch: codex/ai-exam-generation-pr-03
      pr_depends_on: [PR-02]
      pr_subject: "P3 PDF 渲染、分页规则与导出资产"
      acceptance_cmds:
        - bash scripts/pytest_targeted.sh tests/unit/test_pdf_render_service.py -q
        - bash scripts/pytest_targeted.sh tests/unit/test_exam_generation_service.py -q -k pdf_export
      rollback_point: feature.enable_exam_generation_pdf=false

    - task_id: T07
      pr_id: PR-04
      pr_branch: codex/ai-exam-generation-pr-04
      pr_depends_on: [PR-02, PR-03]
      pr_subject: "P4 后台页面、历史回放与下载交互"
      acceptance_cmds:
        - pnpm --dir web test -- --runInBand ExamGenerationPanel
        - pnpm --dir web exec playwright test e2e/admin-exam-generation.spec.cjs
      rollback_point: feature.enable_exam_generation_admin=false

    - task_id: T08
      pr_id: PR-04
      pr_branch: codex/ai-exam-generation-pr-04
      pr_depends_on: [PR-01, PR-02, PR-03]
      pr_subject: "P4 测试矩阵、文档同步与规划门禁收口"
      acceptance_cmds:
        - bash scripts/pytest_targeted.sh tests/unit/test_exam_generation_service.py tests/unit/test_pdf_render_service.py -q
        - bash scripts/pytest_targeted.sh tests/api/test_exam_admin_api.py -q
        - pnpm --dir web exec playwright test e2e/admin-exam-generation.spec.cjs
        - 先执行 `bash scripts/repo_python.sh` 获取解释器，再执行 `<PYTHON_BIN> scripts/check_workflow_contract.py --mode clarify_plan --requirements-path workdocs/归档/正文/需求/ai-exam-generation-agent_requirements.md --implementation-path workdocs/归档/正文/实施计划/ai-exam-generation-agent_implementation_plan.md --output workdocs/归档/报告/机读校验/ai-exam-generation-agent_clarify_plan_alignment.json`
        - 先执行 `bash scripts/repo_python.sh` 获取解释器，再执行 `<PYTHON_BIN> scripts/check_workflow_contract.py --mode planning_temporal_gate --implementation-path workdocs/归档/正文/实施计划/ai-exam-generation-agent_implementation_plan.md --output workdocs/归档/报告/机读校验/ai-exam-generation-agent_planning_temporal_gate.json`
      rollback_point: revert:exam-generation-docs-and-tests
  execution_mode: serial
  strict_single_active_card: true
  card_order: [C01, C02, C03, C04, C05, C06, C07, C08]
  cards:
    - card_id: C01
      task_id: T01
      wave: P1
      depends_on: []
      risk_tags: [contract]
      mandatory_evidence: [admin_api_surface_frozen, access_policy_denied_visible]
    - card_id: C02
      task_id: T02
      wave: P1
      depends_on: [C01]
      risk_tags: [contract]
      mandatory_evidence: [template_contract_single_source, paper_contract_schema_green]
    - card_id: C03
      task_id: T03
      wave: P2
      depends_on: [C02]
      risk_tags: [chat_db, migration]
      mandatory_evidence: [chat_db_write_read, chat_db_job_snapshot_roundtrip, minio_export_binding_present]
    - card_id: C04
      task_id: T04
      wave: P2
      depends_on: [C03]
      risk_tags: [contract, chat_db]
      mandatory_evidence: [chat_db_write_read, access_policy_limit_enforced, template_snapshot_roundtrip]
    - card_id: C05
      task_id: T05
      wave: P3
      depends_on: [C04]
      risk_tags: [agent_contract, quality_gate]
      mandatory_evidence: [dataset_priority_resolved, evidence_coverage_100, quality_gate_blocks_invalid_paper]
    - card_id: C06
      task_id: T06
      wave: P3
      depends_on: [C05]
      risk_tags: [render_contract, asset_export]
      mandatory_evidence: [pdf_pagination_clean, answer_section_page_break, export_asset_downloadable]
    - card_id: C07
      task_id: T07
      wave: P4
      depends_on: [C03, C04, C06]
      risk_tags: [ui_contract, replay_contract]
      mandatory_evidence: [history_list_replay_consistent, direct_download_visible, question_limit_hint_visible]
    - card_id: C08
      task_id: T08
      wave: P4
      depends_on: [C01, C02, C03, C04, C05, C06, C07]
      risk_tags: [docs_sync, regression_gate]
      mandatory_evidence: [clarify_plan_alignment, temporal_gate_clean, docs_guard_clean]
```

## 4. planning_contract 摘要

- `T01~T02` 先冻结后台 API、模板合同与入口权限，避免后面工作流和前端建立在漂移输入上。
- `T03~T04` 固定任务表、历史记录 canonical、MinIO 资产绑定、题量/并发限制，再向上承接业务流程。
- `T05~T06` 统一收口出题工作流、质量门禁、PDF 渲染与导出。
- `T07` 在后端 canonical 稳定后再做后台页和历史回放，避免前端反复改协议。
- `T08` 最后统一补测试矩阵、文档同步与规划门禁，作为实施前最终收口。

## 5. execution_contract

```yaml
execution_contract:
  preferred_mode: core
  delivery_mode: staged
  execution_unit: per_pr
  commit_policy: per_pr
  stop_boundary: per_pr
  stop_on_blocked: true
  execution_contract_ready: true
  source_seed_ref: clarify_handoff_contract.required.execution_chain_seed.execution_contract_hint
```

## 6. implementation_readiness

```yaml
implementation_readiness:
  implementation_ready: true
  blocked_by: []
  next_step: /jjk-imp
  execution_contract_ready: true
```


## 7. tc_execution_mapping

```yaml
tc_execution_mapping:
  - tc_id: TC-01
    task_id: T01
    pr_id: PR-01
  - tc_id: TC-02
    task_id: T05
    pr_id: PR-03
  - tc_id: TC-03
    task_id: T02
    pr_id: PR-01
  - tc_id: TC-04
    task_id: T05
    pr_id: PR-03
  - tc_id: TC-05
    task_id: T06
    pr_id: PR-03
  - tc_id: TC-06
    task_id: T05
    pr_id: PR-03
  - tc_id: TC-07
    task_id: T07
    pr_id: PR-04
  - tc_id: TC-08
    task_id: T04
    pr_id: PR-02
  - tc_id: TC-09
    task_id: T03
    pr_id: PR-02
  - tc_id: TC-10
    task_id: T07
    pr_id: PR-04
  - tc_id: TC-11
    task_id: T08
    pr_id: PR-04
```
