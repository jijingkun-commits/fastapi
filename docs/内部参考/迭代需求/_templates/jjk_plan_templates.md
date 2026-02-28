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
