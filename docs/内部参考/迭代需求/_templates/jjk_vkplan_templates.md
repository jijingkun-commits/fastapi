# `/jjk-vkplan` 项目覆盖模板（轻量）

> 仅用于覆盖全局模板差异：
> `/Users/jijingkun/.codex/engineering/templates/jjk_vkplan_templates.md`

## 项目覆盖段（按需填写）

```markdown
### 覆盖: <topic-or-domain>
- 覆盖原因:
- vk_cards 字段差异:
- mapping_checks 差异:
- gate_cards 差异:
- active_task_alignment 差异:
```

## 本项目默认覆盖（串行主干状态）

```yaml
vk_cards:
  done_definition: verify_passed_and_merged
  execution_mode: serial

  cards:
    - task_mode: implementation-card
      merge_required: true

gate_cards:
  - card_id: G01
    task_mode: inspection-card
    merge_required: false
  - card_id: IG01
    task_mode: inspection-card
    merge_required: false

execution_contract:
  delivery_mode: staged
  execution_unit: per_card
  commit_policy: per_card
  merge_policy: per_card_to_master
  stop_boundary: per_card
  stop_on_blocked: true
```

## 本项目强制追加字段（卡片 PR 归属）

当输出 `vk_cards.json` 时，每张可执行卡必须具备 PR 映射字段：

```yaml
vk_cards:
  cards:
    - card_id: WS-01
      task_id: T-01
      feature_ids: [P1-01]
      pr_id: PR-01
      pr_branch: codex/<topic>-pr-01
      pr_depends_on: []
      pr_subject: "P1 核心改造：意图计划主链"
```

并在校验结果中追加：

```yaml
mapping_checks:
  pr_mapping_check: PASS
  pr_mapping_errors: []
```

校验规则：

1. `cards[*].pr_id` 必须可回查 `implementation_plan.task_to_pr_mapping`。
2. 禁止“卡片存在但无 PR 归属”。
3. 若出现映射冲突或缺失，必须输出 `VKPLAN_PR_MAPPING_BROKEN` 并阻断 `/jjk-vktodo`。
