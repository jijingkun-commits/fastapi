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
