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
  source: implementation_plan.execution_contract
  inherit_without_override: true
  required_fields: [delivery_mode, execution_unit, commit_policy, stop_boundary, stop_on_blocked]
```

执行契约继承规则：

1. `/jjk-vkplan` 必须原样继承 `implementation_plan.execution_contract`，禁止默认补齐。
2. 若缺失或字段不一致，必须输出 `VKPLAN_EXECUTION_CONTRACT_MISMATCH` 并阻断 `/jjk-cardrun`（以及依赖其结果的下游执行）。
3. 并行拆解阶段只允许“展开为卡片维度执行数据”，不允许改写执行语义。

## 本项目强制追加字段（卡片任务与 PR 归属）

当输出 `vk_cards.json` 时，每张可执行卡必须具备 PR 映射字段：

```yaml
vk_cards:
  cards:
    - card_id: WS-01
      task_ids: [T-01]
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
  plan_consumption_check: PASS
  missing_feature_ids: []
  missing_task_ids: []
  missing_task_id_fields: []
  empty_task_ids: []
  execution_contract_mismatch: []
  acceptance_mapping_missing: []
```

校验规则：

1. `cards[*].pr_id` 必须可回查 `implementation_plan.task_to_pr_mapping`。
2. 禁止“卡片存在但无 PR 归属”。
3. 若出现映射冲突或缺失，必须输出 `VKPLAN_PR_MAPPING_BROKEN` 并阻断 `/jjk-cardrun`。
4. 若 `missing_feature_ids` 或 `missing_task_ids` 非空，必须输出 `VKPLAN_CONSUMPTION_GAP` 并阻断下游。
5. 若 `execution_contract_mismatch` 非空，必须输出 `VKPLAN_EXECUTION_CONTRACT_MISMATCH` 并阻断下游。
6. 若 `acceptance_mapping_missing` 非空，必须输出 `VKPLAN_ACCEPTANCE_MAPPING_BROKEN` 并阻断下游。
7. 若 `missing_task_id_fields` 或 `empty_task_ids` 非空，必须输出 `VKPLAN_TASK_IDS_REQUIRED` 并阻断下游。
