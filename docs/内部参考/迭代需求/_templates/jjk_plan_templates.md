# `/jjk-plan` 项目覆盖模板（轻量）

> 仅用于覆盖全局模板差异：
> `/Users/jijingkun/.codex/engineering/templates/jjk_plan_templates.md`

## 项目覆盖段（按需填写）

```markdown
### 覆盖: <topic-or-domain>
- 覆盖原因:
- 覆盖字段:
- 与全局模板差异:
- implementation_tasks 差异:
- implementation_readiness 差异:
```

## 本项目强制追加字段（Requirements Contract）

当输出 `<topic>_requirements.md` 时，至少追加以下结构：

```yaml
requirements_contract:
  topic: "<主题>"
  status: draft
  design_source: docs/plans/YYYY-MM-DD-<topic>-design.md
  clarify_handoff_source: docs/plans/YYYY-MM-DD-<topic>-design.md#clarify_handoff_contract
  clarify_handoff_version: v2
  design_approved: true
  design_approval_evidence: "<用户明确确认原话>"
  design_freeze_summary:
    design_actionable: true
    missing_blocks: []
    risk_level: low
    risk_counterexamples_count: 2
  owner: "<owner>"
  approver: "<approver>"
  updated_at: "YYYY-MM-DD HH:mm"
```

```yaml
fr_contract_matrix:
  - fr_id: FR-01
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[0]  # v1 兼容: clarify_handoff_contract.requirement_seeds[0]
    user_value: 简要价值说明
    trigger: 触发条件
    input_contract:
      required_fields: [field_a, field_b]
      source_of_truth: app/ai/state.py
    output_contract:
      required_fields: [result_x, result_y]
      consumer: app/services/chat_service.py
    failure_semantics: 失败时返回口径
    observability_fields: [metric_a, metric_b]
    rollback_anchor: ENABLE_XXX=false（默认 true，回退时置 false）
    owner: ai-workflow
```

```yaml
traceability_matrix:
  - design_item: D-01
    fr_id: FR-01
    feature_id: P1-01
    task_id: T-01
    tc_id: TC-XXX-01
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_xxx.py -q
    evidence_entry: docs/内部参考/迭代需求/<topic>_implementation_plan.md
```

校验规则：

1. 每个 `FR-*` 必须具备：`trigger/input_contract/output_contract/failure_semantics/observability_fields/rollback_anchor/owner`。
2. 每个 `NFR-*` 必须含数字阈值（例如 `P50/P95`、错误率、恢复时长），禁止仅写“显著提升/明显下降”。
3. 每个 `TC-*` 必须在 `traceability_matrix` 映射到唯一 `task_id` 与 `acceptance_cmd_ref`。
4. 当 `requirements_contract.status` 为 `draft/草稿` 时，`implementation_readiness.implementation_ready` 必须为 `false`。
5. 新增开关默认值必须写为开启（`true`）；除非用户明确要求灰度，禁止采用“默认关闭 + 灰度放量”口径。
6. `design_approval_evidence` 必须非空，缺失时标记 `DESIGN_APPROVAL_EVIDENCE_MISSING`。
7. `design_freeze_summary.design_actionable` 必须为 `true` 且 `missing_blocks=[]`，否则标记 `DESIGN_NOT_ACTIONABLE`。
8. `design_freeze_summary.risk_counterexamples_count` 必须 `>=2`，否则标记 `DESIGN_RISK_EXAMPLES_INSUFFICIENT`。
9. 禁止在机读 YAML 中出现旧协议字段：`intent_plan`、`validate_intent_plan_contract`、`legacy_json_object`；出现即标记 `PLAN_FORBIDDEN_PROTOCOL_FIELD_DETECTED`。

## 本项目强制追加字段（Task -> PR 映射）

当输出 `<topic>_implementation_plan.md` 时，至少追加以下结构：

```yaml
planning_contract:
  task_to_pr_mapping:
    - task_id: T-01
      pr_id: PR-01
      pr_branch: codex/<topic>-pr-01
      pr_depends_on: []
      pr_subject: "P1 核心改造：意图计划主链"
      acceptance_cmds:
        - venv/bin/python -m pytest tests/unit/test_xxx.py -q
      rollback_point: 关闭 <feature_flag> 并回退 <symbol>
```

```yaml
implementation_tasks:
  - task_id: T-01
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[0]  # v1 兼容: clarify_handoff_contract.implementation_seeds[0]
    feature_id: P1-01
    pr_id: PR-01
    phase: Phase-1
    change_type: modify
    owner: ai-workflow
    depends_on_tasks: []
    risk_point: 状态迁移一致性风险
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
    symbols:
      - build_active_goals
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_xxx.py -q
    rollback_point: 回退到 old_build_active_goals
```

校验规则：

1. 每个 `task_id` 必须且仅能映射一个 `pr_id`。
2. `implementation_tasks[*].pr_id` 必须可回查 `task_to_pr_mapping`。
3. 每个 `implementation_tasks[*]` 必须包含：`source_seed_ref/phase/change_type/owner/depends_on_tasks/risk_point/file_paths/symbols/acceptance_cmds/rollback_point`。
4. 缺少映射或必填字段时，计划状态必须标注 `BLOCKED`，并阻断 `/jjk-vkplan`。
5. `source_seed_ref` 缺失或无法回查 design 中 `clarify_handoff_contract` 时，必须标记 `CLARIFY_PLAN_BRIDGE_BROKEN`。
6. 若任意任务缺少上述细节字段，必须标记 `PLAN_IMPLEMENTATION_DETAIL_INSUFFICIENT`，并禁止进入执行链。
7. 若 `clarify_handoff_contract` 中 `implementation_seeds` 为轻量输入（仅 `task_id/file_paths/symbols/change_type`），必须在 `implementation_tasks` 层补齐 `acceptance_cmds/rollback_point/pr_id/phase/depends_on_tasks`。

## 本项目强制追加字段（Execution Contract）

当用户明确要求“进入执行链”时，`<topic>_implementation_plan.md` 必须追加：

```yaml
execution_contract:
  delivery_mode: one_shot
  execution_unit: all_tasks
  commit_policy: single_commit
  stop_boundary: none
  stop_on_blocked: true
  source_seed_ref: clarify_handoff_contract.required.execution_chain_seed.execution_contract_hint  # v1 兼容: clarify_handoff_contract.execution_chain_seed.execution_contract_hint
```

```yaml
implementation_readiness:
  implementation_ready: true
  blocked_by: []
  next_step: /jjk-imp
  execution_contract_ready: true
```

默认继承规则：

1. `core` 模式默认 `one_shot + all_tasks + single_commit + stop_boundary=none`。
2. `parallel` 模式默认 `staged + per_pr + per_pr + stop_boundary=per_pr`。

校验规则：

1. `execution_contract` 缺失时，必须标记 `EXECUTION_CONTRACT_MISSING`。
2. `delivery_mode=one_shot` 时，`stop_boundary` 只能是 `none`。
3. `delivery_mode=staged` 时，`stop_boundary` 必须与 `execution_unit` 对齐（`per_pr` 或 `per_task`）。
4. `commit_policy=single_commit` 仅允许与 `delivery_mode=one_shot` 组合。
