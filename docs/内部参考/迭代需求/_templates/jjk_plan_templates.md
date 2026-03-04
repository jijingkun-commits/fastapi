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
  design_approved: true
  owner: "<owner>"
  approver: "<approver>"
  updated_at: "YYYY-MM-DD HH:mm"
```

```yaml
fr_contract_matrix:
  - fr_id: FR-01
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
    rollback_anchor: ENABLE_XXX=false
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
    feature_id: P1-01
    pr_id: PR-01
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
    symbols:
      - build_intent_plan
    acceptance_cmds:
      - venv/bin/python -m pytest tests/unit/test_xxx.py -q
    rollback_point: 回退到 old_build_intent_plan
```

校验规则：

1. 每个 `task_id` 必须且仅能映射一个 `pr_id`。
2. `implementation_tasks[*].pr_id` 必须可回查 `task_to_pr_mapping`。
3. 缺少映射时，计划状态必须标注 `BLOCKED`，并阻断 `/jjk-vkplan`。

## 本项目强制追加字段（Execution Contract）

当用户明确要求“进入执行链”时，`<topic>_implementation_plan.md` 必须追加：

```yaml
execution_contract:
  delivery_mode: one_shot
  execution_unit: all_tasks
  commit_policy: single_commit
  stop_boundary: none
  stop_on_blocked: true
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
