# 用户个性化永久记忆与管理能力串行拆解计划（LLM异步判定）

> 计划 ID: PP-20260304-USER-MEMORY-LLM-ASYNC
> 主题: 用户个性化永久记忆与管理能力
> 输入来源: `workdocs/归档/正文/需求/用户个性化永久记忆与管理能力_requirements.md` / `workdocs/归档/正文/实施计划/用户个性化永久记忆与管理能力_implementation_plan.md`

## -1. 执行策略

- execution_mode: `serial`
- single_active_card: `true`
- card_order: `['C01', 'C02', 'C03', 'C04', 'C05', 'C06', 'C07', 'C08', 'C09', 'G01']`
- gate_contract:
  - mode: `as_cards`
  - gate_ids: `['G01']`
  - depends_on: `{'G01': ['C09']}`
- auto_done_policy:
  - implementation-card: `hard_gate`
  - inspection/question-card: `policy_gate`
- execution_contract:
  - delivery_mode: `one_shot`
  - execution_unit: `all_tasks`
  - commit_policy: `single_commit`
  - stop_boundary: `none`
  - stop_on_blocked: `true`

## 0. 输入与冻结

- 来源 requirements: `workdocs/归档/正文/需求/用户个性化永久记忆与管理能力_requirements.md`
- 来源 implementation_plan: `workdocs/归档/正文/实施计划/用户个性化永久记忆与管理能力_implementation_plan.md`
- 契约冻结：继承 planning_contract，不重命名 card_id/feature_id，不弱化 depends_on。

## 1. 卡片总览

| card_id | feature_ids | depends_on | task_mode | pr_id |
|---|---|---|---|---|
| C01 | P1-01 | 无 | implementation-card | PR-01 |
| C02 | P1-02 | C01 | implementation-card | PR-02 |
| C03 | P1-03 | C02 | implementation-card | PR-03 |
| C04 | P1-04 | C03 | implementation-card | PR-04 |
| C05 | P1-05 | C03 | implementation-card | PR-05 |
| C06 | P1-06 | C04,C05 | implementation-card | PR-06 |
| C07 | P1-07 | C06 | implementation-card | PR-07 |
| C08 | P1-08 | C06 | implementation-card | PR-08 |
| C09 | P1-09 | C02,C07,C08 | implementation-card | PR-09 |
| G01 | G-1 | C09 | inspection-card | PR-G01 |

## 2. 工作流说明

1. 串行单活卡推进，严格按 `card_order`。
2. `C01~C09` 为实现卡，`G01` 为门禁卡。
3. 每张卡必须通过 `acceptance_checks` 才可推进下一卡。

## 3. Gate 执行状态

- G01 状态：待执行
- G01 验收命令：
  - `python3 scripts/check_gate_contract_consistency.py --task-split-dir 2026-03-04_用户个性化永久记忆与管理能力`
  - `python3 scripts/docs_guard.py --strict`

## 4. mapping_checks

```yaml
mapping_checks:
  forward_check: PASS
  reverse_check: PASS
  orphan_features: []
  duplicate_features: []
  pr_mapping_check: PASS
  pr_mapping_errors: []
```

## 5. active_task_alignment

```yaml
active_task_alignment:
  task_key_match: true
  task_split_dir_match: true
  project_id_present: true
```
