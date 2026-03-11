# ai-exam-generation-agent 需求文档

> 更新时间：2026-03-11 23:59 CST  
> 上游设计：`docs/plans/2026-03-11-ai-exam-generation-agent-design.md`  
> 文档目标：定义 WHAT（需求合同、验收门禁、追溯矩阵），供 `ai-exam-generation-agent_implementation_plan.md` 承接

## 0. 设计审批门禁状态

- 设计文档：`docs/plans/2026-03-11-ai-exam-generation-agent-design.md`
- 审批记录：`design_approved: true`
- 审批时间：`2026-03-11 23:59 CST`
- 审批轮次：`round-4`
- 审批证据：`用户明确指令：[$jjk-plan]；将该指令视为对当前 AI 出题智能体单方案的正式确认。`

## 0.1 执行意图门禁

- 用户本轮指令为“进入 jjk-plan”，未要求直接进入实现。
- 本文档与 implementation plan 输出模式为 `plan-only`。
- 本轮不自动触发 `$jjk-vkplan`、`$jjk-vktodo`、`$jjk-imp`。

## 1. 需求范围与目标

### 1.1 核心目标

- 提供一个**独立后台页**，让管理员基于指定知识库范围生成试卷 PDF。
- 将出题能力固定为**知识检索 -> 结构化组卷 -> 质量门禁 -> PDF 导出 -> MinIO 历史记录**的单一路径。
- 固定首期题型为**单选、多选、判断、简答**，并输出**答案 + 简短解析**。
- 将历史记录沉淀为**DB 任务快照 + MinIO 导出资产**，支持重复下载。
- 与现有 `chat/supervisor` 主链保持低耦合，不引入聊天入口、聊天状态或 supervisor 路由修改。

### 1.2 范围

- 后台页面：`web/src/app/admin/exam-generation/page.tsx`、`web/src/components/admin/ExamGenerationPanel.tsx`
- 后台 API：`app/api/v1/endpoints/exam_admin_api.py`
- 任务与状态：`exam_generation_job` 持久化模型与 repo
- 出题工作流：独立 `exam_generation_workflow`
- PDF 生成：HTML 模板 + CSS Paged Media + WeasyPrint
- 历史记录：任务快照结果 + MinIO `export` 资产回放
- 访问控制：后台管理员访问 + 单用户题量/并发限制

### 1.3 非范围

- 不接入聊天页或聊天 SSE 主链。
- 不做学生答题页、考试编排、自动阅卷。
- 不做模板管理中心、题目人工审核流、Word 导出。
- 不做按章节/标签/知识点树的复杂筛选界面。
- 不做知识库已有原题抽题与知识生成混合模式。

### 1.4 发布约束

- 新开关默认 `true`，回退时切到 `false`。
- V1 默认只允许后台管理员访问。
- V1 默认只允许查看本人创建的历史记录。
- V1 默认总题数上限 `<=100`，单用户并发运行任务数 `<=3`。
- 不允许把自然时间窗口、观察期成熟等写入阻断型验收门禁。

## 2. requirements_contract

```yaml
requirements_contract:
  topic: ai-exam-generation-agent
  status: approved
  design_source: docs/plans/2026-03-11-ai-exam-generation-agent-design.md
  clarify_handoff_source: docs/plans/2026-03-11-ai-exam-generation-agent-design.md#clarify_handoff_contract
  clarify_handoff_version: v2
  design_approved: true
  design_approval_evidence: "用户明确指令：[$jjk-plan]；将该指令视为对当前 AI 出题智能体单方案的正式确认。"
  design_freeze_summary:
    design_actionable: true
    missing_blocks: []
    risk_level: medium
    risk_counterexamples_count: 6
    handoff_contract_ready: true
    product_contract_ready: true
    implementation_seed_count: 8
    semantic_frozen: true
    contract_source_decided: true
    handoff_seed_alignment_ok: true
    parallel_dependency_ready: true
    replay_canonical_field_set: true
    blocking_issues: []
  owner: exam-platform
  approver: jijingkun
  updated_at: "2026-03-11 23:59 CST"
```

## 3. product_contract_matrix

```yaml
product_contract_matrix:
  - bg_id: BG-01
    target_users: [后台管理员, 教研/培训运营]
    core_scenario: 在独立后台页中完成选知识库、改模板、生成并下载试卷
    business_goal_metric: generation_success_rate>=90%
    acceptance_gates: [A-01, A-02, A-03, A-05]
    release_constraint: 不接入聊天主链

  - bg_id: BG-02
    target_users: [后台管理员, 业务负责人]
    core_scenario: 生成的题目可追溯到知识证据，且未通过质量门禁的题单不得导出
    business_goal_metric: evidence_coverage_rate=100%
    acceptance_gates: [A-04, A-05]
    release_constraint: 质量门禁先于 PDF 导出

  - bg_id: BG-03
    target_users: [后台管理员]
    core_scenario: 生成结果进入历史记录，可重复下载，不会“下完就丢”
    business_goal_metric: history_replay_success_rate>=99%
    acceptance_gates: [A-06, A-07]
    release_constraint: PDF 统一保存到现有 MinIO

  - bg_id: BG-04
    target_users: [后台管理员]
    core_scenario: 多数据集选择时优先级和冲突语义明确，不出现黑盒静默择一
    business_goal_metric: dataset_conflict_silent_override_rate=0%
    acceptance_gates: [A-02, A-04]
    release_constraint: 按用户勾选顺序作为优先级

  - bg_id: BG-05
    target_users: [系统管理员]
    core_scenario: 后台入口具备明确权限与限流，不因滥用拖垮系统
    business_goal_metric: unauthorized_access_success_rate=0%
    acceptance_gates: [A-08]
    release_constraint: 单用户并发运行任务数<=3
```

## 4. fr_contract_matrix

```yaml
fr_contract_matrix:
  - fr_id: FR-EXAM-ADMIN-PAGE
    seed_ref: clarify_handoff_contract.required.requirement_seeds[0]
    summary: 提供独立后台页面，支持模板编辑、数据集选择、提交生成、状态展示
    business_goal_metrics: [generation_success_rate>=90%]
    acceptance_gates: [A-01]

  - fr_id: FR-EXAM-DATASET-SELECTION
    seed_ref: clarify_handoff_contract.required.requirement_seeds[1]
    summary: 用户必须显式选择一个或多个 dataset；多数据集按勾选顺序确定优先级
    business_goal_metrics: [dataset_conflict_silent_override_rate=0%]
    acceptance_gates: [A-02, A-04]

  - fr_id: FR-EXAM-TEMPLATE-EDIT
    seed_ref: clarify_handoff_contract.required.requirement_seeds[2]
    summary: 后台页先加载默认模板，用户可编辑单选/多选/判断/简答题量、难度、分值与标题
    business_goal_metrics: [generation_success_rate>=90%]
    acceptance_gates: [A-03]

  - fr_id: FR-EXAM-KNOWLEDGE-TO-QUESTION
    seed_ref: clarify_handoff_contract.required.requirement_seeds[3]
    summary: 系统基于知识证据生成题目、答案与简短解析，不假定知识库中已有原题
    business_goal_metrics: [evidence_coverage_rate=100%]
    acceptance_gates: [A-04]

  - fr_id: FR-EXAM-PDF-WITH-ANSWERS
    seed_ref: clarify_handoff_contract.required.requirement_seeds[4]
    summary: 生成单个 PDF，包含试卷正文、答案与简短解析，并保证答案区单独分页
    business_goal_metrics: [pdf_pagination_blocker_count=0]
    acceptance_gates: [A-05]

  - fr_id: FR-EXAM-QUALITY-GATE
    seed_ref: design.requirement_seeds[D-05A]
    summary: 题目必须通过题型合法、答案合法、证据存在、去重、覆盖度检查后才能导出
    business_goal_metrics: [quality_gate_false_pass_rate=0%]
    acceptance_gates: [A-04, A-05]

  - fr_id: FR-EXAM-DIRECT-DOWNLOAD
    seed_ref: clarify_handoff_contract.required.requirement_seeds[5]
    summary: 任务成功后可以直接下载生成 PDF
    business_goal_metrics: [download_ready_after_success_rate=100%]
    acceptance_gates: [A-06]

  - fr_id: FR-EXAM-ACCESS-POLICY
    seed_ref: design.requirement_seeds[D-06A]
    summary: 仅后台管理员可访问；默认只允许查看本人记录；题量与并发必须受控
    business_goal_metrics: [unauthorized_access_success_rate=0%]
    acceptance_gates: [A-08]

  - fr_id: FR-EXAM-HISTORY-REPLAY
    seed_ref: clarify_handoff_contract.required.requirement_seeds[6]
    summary: 历史记录可查看、可回放、可重复下载；资产缺失时必须明确提示不可用
    business_goal_metrics: [history_replay_success_rate>=99%]
    acceptance_gates: [A-07]
```

## 5. nfr_contract_matrix

```yaml
nfr_contract_matrix:
  - nfr_id: NFR-01
    category: capacity
    statement: 单次总题数上限必须小于等于 100
    threshold: total_question_count<=100
    acceptance_gate: A-08

  - nfr_id: NFR-02
    category: concurrency
    statement: 单用户同时运行中的生成任务数必须小于等于 3
    threshold: active_exam_jobs_per_user<=3
    acceptance_gate: A-08

  - nfr_id: NFR-03
    category: traceability
    statement: 每道题证据覆盖率必须为 100%
    threshold: evidence_coverage_rate=100%
    acceptance_gate: A-04

  - nfr_id: NFR-04
    category: quality
    statement: 质量门禁误放行率必须为 0%
    threshold: quality_gate_false_pass_rate=0%
    acceptance_gate: A-04

  - nfr_id: NFR-05
    category: pagination
    statement: PDF 分页 blocker 数量必须为 0
    threshold: pdf_pagination_blocker_count=0
    acceptance_gate: A-05

  - nfr_id: NFR-06
    category: replay
    statement: 历史记录重复下载成功率必须大于等于 99%
    threshold: history_replay_success_rate>=99%
    acceptance_gate: A-07
```

## 6. acceptance_gates

```yaml
acceptance_gates:
  - gate_id: A-01
    summary: 存在独立后台页入口，且不依赖聊天入口
  - gate_id: A-02
    summary: 用户必须显式选择 dataset，且多数据集优先级语义明确
  - gate_id: A-03
    summary: 默认模板可编辑，且题型固定为单选/多选/判断/简答
  - gate_id: A-04
    summary: 每道题存在证据，且题单必须通过质量门禁
  - gate_id: A-05
    summary: PDF 含试卷、答案、简短解析，且答案区分页正确
  - gate_id: A-06
    summary: 任务成功后可直接下载 PDF
  - gate_id: A-07
    summary: 历史记录可查看、可重复下载，资产缺失可见失败态
  - gate_id: A-08
    summary: 后台权限与限流生效
```

## 7. traceability_matrix

```yaml
traceability_matrix:
  - design_item: D-01
    fr_id: FR-EXAM-ADMIN-PAGE
    bg_id: BG-01
    feature_id: F1-admin-api-and-access
    task_id: T01
    tc_id: TC-01
    acceptance_cmd_ref: 'bash scripts/pytest_targeted.sh tests/api/test_exam_admin_api.py -q -k "create_job or list_jobs or access_policy"'
    evidence_entry: docs/内部参考/迭代需求/ai-exam-generation-agent_implementation_plan.md

  - design_item: D-02
    fr_id: FR-EXAM-DATASET-SELECTION
    bg_id: BG-04
    feature_id: F5-workflow-and-quality-gate
    task_id: T05
    tc_id: TC-02
    acceptance_cmd_ref: 'bash scripts/pytest_targeted.sh tests/unit/test_exam_generation_service.py -q -k "quality_gate or dataset_priority or conflict"'
    evidence_entry: docs/内部参考/迭代需求/ai-exam-generation-agent_implementation_plan.md

  - design_item: D-03
    fr_id: FR-EXAM-TEMPLATE-EDIT
    bg_id: BG-01
    feature_id: F2-contract-and-template
    task_id: T02
    tc_id: TC-03
    acceptance_cmd_ref: 'bash scripts/pytest_targeted.sh tests/unit/test_exam_generation_contracts.py -q'
    evidence_entry: docs/内部参考/迭代需求/ai-exam-generation-agent_implementation_plan.md

  - design_item: D-04
    fr_id: FR-EXAM-KNOWLEDGE-TO-QUESTION
    bg_id: BG-02
    feature_id: F5-workflow-and-quality-gate
    task_id: T05
    tc_id: TC-04
    acceptance_cmd_ref: 'bash scripts/pytest_targeted.sh tests/unit/test_exam_generation_workflow.py -q'
    evidence_entry: docs/内部参考/迭代需求/ai-exam-generation-agent_implementation_plan.md

  - design_item: D-05
    fr_id: FR-EXAM-PDF-WITH-ANSWERS
    bg_id: BG-01
    feature_id: F6-pdf-render-and-export
    task_id: T06
    tc_id: TC-05
    acceptance_cmd_ref: 'bash scripts/pytest_targeted.sh tests/unit/test_pdf_render_service.py -q'
    evidence_entry: docs/内部参考/迭代需求/ai-exam-generation-agent_implementation_plan.md

  - design_item: D-05A
    fr_id: FR-EXAM-QUALITY-GATE
    bg_id: BG-02
    feature_id: F5-workflow-and-quality-gate
    task_id: T05
    tc_id: TC-06
    acceptance_cmd_ref: 'bash scripts/pytest_targeted.sh tests/unit/test_exam_generation_service.py -q -k "quality_gate or dataset_priority or conflict"'
    evidence_entry: docs/内部参考/迭代需求/ai-exam-generation-agent_implementation_plan.md

  - design_item: D-06
    fr_id: FR-EXAM-DIRECT-DOWNLOAD
    bg_id: BG-03
    feature_id: F7-admin-ui-and-history
    task_id: T07
    tc_id: TC-07
    acceptance_cmd_ref: 'pnpm --dir web exec playwright test e2e/admin-exam-generation.spec.cjs'
    evidence_entry: docs/内部参考/迭代需求/ai-exam-generation-agent_implementation_plan.md

  - design_item: D-06A
    fr_id: FR-EXAM-ACCESS-POLICY
    bg_id: BG-05
    feature_id: F4-service-orchestration-and-policy
    task_id: T04
    tc_id: TC-08
    acceptance_cmd_ref: 'bash scripts/pytest_targeted.sh tests/unit/test_exam_generation_service.py -q -k "create_job or access_policy or template"'
    evidence_entry: docs/内部参考/迭代需求/ai-exam-generation-agent_implementation_plan.md

  - design_item: D-07
    fr_id: FR-EXAM-HISTORY-REPLAY
    bg_id: BG-03
    feature_id: F3-job-persistence-and-history
    task_id: T03
    tc_id: TC-09
    acceptance_cmd_ref: 'bash scripts/pytest_targeted.sh tests/unit/test_exam_generation_job_repo.py -q'
    evidence_entry: docs/内部参考/迭代需求/ai-exam-generation-agent_implementation_plan.md

  - design_item: D-07
    fr_id: FR-EXAM-HISTORY-REPLAY
    bg_id: BG-03
    feature_id: F7-admin-ui-and-history
    task_id: T07
    tc_id: TC-10
    acceptance_cmd_ref: 'pnpm --dir web exec playwright test e2e/admin-exam-generation.spec.cjs'
    evidence_entry: docs/内部参考/迭代需求/ai-exam-generation-agent_implementation_plan.md

  - design_item: D-05A
    fr_id: FR-EXAM-QUALITY-GATE
    bg_id: BG-02
    feature_id: F8-tests-docs-and-planning-gates
    task_id: T08
    tc_id: TC-11
    acceptance_cmd_ref: 'bash scripts/pytest_targeted.sh tests/unit/test_exam_generation_service.py tests/unit/test_pdf_render_service.py -q'
    evidence_entry: docs/内部参考/迭代需求/ai-exam-generation-agent_implementation_plan.md
```
