# workflow-gate-retirement 串行拆解计划

> 计划 ID: `PP-20260306-workflow-gate-retirement`
> 主题: `工程减法治理`
> 输入来源: `docs/内部参考/迭代需求/workflow-gate-retirement_requirements.md` / `docs/内部参考/迭代需求/workflow-gate-retirement_implementation_plan.md`

## -1. 执行策略

- execution_mode: `serial`
- single_active_card: `true`
- card_order: `['C01', 'C02', 'C03', 'C04', 'C05', 'C06', 'C07', 'G01']`
- gate_contract:
  - mode: `as_cards`
  - gate_ids: `['G01']`
  - depends_on: `{'G01': ['C07']}`
- auto_done_policy:
  - implementation-card: `hard_gate`
  - inspection-card: `policy_gate`
- 与 planning_contract 一致性: `PASS`（继承 implementation_plan）

### -1.1 automation_contract

```yaml
automation_contract:
  source_of_truth: docs/内部参考/任务拆解/2026-03-06_工程减法治理/_active_task.json
  required_fields:
    - project_id
    - task_split_dir
    - task_key
    - execution_mode
    - single_active_card
    - auto_done_policy
    - preflight_required
  scope_match_rule:
    - title_contains_[task_key]
    - labels_contains_task_key
    - card_key_prefix_task_key
```

## 0. G0 协议冻结

- 冻结范围: `P0 -> P1 -> P2 -> P3 -> G01`
- required/optional: required=`card_id/feature_ids/task_ids/acceptance_checks/rollback_anchors`; optional=`example_refs/handoff_artifacts`
- 枚举与空值约束: `task_mode` 仅允许 `implementation-card|inspection-card`
- 单活卡语义: `serial` 模式下仅允许当前 `card_order` 首个未完成卡进入执行

## 1. seed 来源

- `task_key`: `PP-20260306-workflow-gate-retirement`
- 来源: `plan`
- `card_seed` 来源: `implementation_plan.planning_contract.cards`
- 推导依据与风险: 严格继承 `card_order/depends_on/gate_contract`，不重命名 `card_id/feature_id/task_id`

### 1.1 功能机制包映射（必填）

| card_id | wave | feature_ids | task_ids | 机制摘要 | 验证命令 |
|---|---|---|---|---|---|
| C01 | P0 | P0-freeze-governance | P0-FREEZE-COMMANDS | 冻结删除口径与 NO-GO 清单 | rg NO-GO |
| C02 | P1 | P1-unified-entry | P1-UNIFIED-ENTRY | 新建统一入口 `check_workflow_contract.py` | clarify_plan mode |
| C03 | P1 | P1-legacy-wrapper | P1-WRAPPER-L1 | 4 个 L1 旧脚本 wrapper 化 | legacy_wrapper_compat |
| C04 | P1 | P1-reference-migration | P1-REFERENCE-MIGRATION | 命令/技能/文档引用迁移 | rg legacy refs |
| C05 | P2 | P2-usage-observability | P2-OBSERVABILITY | usage 日志落盘与零调用判定 | usage-report |
| C06 | P2 | P2-ttl-archive | P2-TTL-ARCHIVE | TTL 归档边界与活跃保护 | ttl-audit |
| C07 | P3 | P3-retire-legacy | P3-RETIRE-LEGACY | 删除旧实现并保留必要兼容壳 | full-gate |
| G01 | Gate | G-01 | G01 | 下游执行前的 vkplan/cardrun 放行门禁 | clarify+coverage |

## 2. 目标与边界

- 目标: 在不放大单次上下文的前提下，把退役工程拆成可串行消费的卡片包
- 非目标: 本阶段不直接修改业务代码外的额外范围；不并行推进跨阶段卡片
- 约束: 禁止弱化 `depends_on`；禁止跳过 `G01` 直接进入批量执行

## 3. 架构冻结项

- 模块边界: `implementation_plan` 为任务/PR/执行契约源，`vk_cards.json` 为卡片消费源
- 状态契约: `_active_task.json` 仅维护 `task_key/task_split_dir/project_id` 作用域绑定
- 回退边界: 每张卡仅回滚本卡 `rollback_anchors`，禁止跨卡混退
- 证据语义: 每张卡必须将结果回填到 `evidence_entry` 指定位置

## 4. 工作包总览

| WS | 名称 | 类型 | 可并行 | 依赖 |
|---|---|---|---|---|
| WS-00 | C00 预检门禁冻结 | Foundation | 否 | 无 |
| WS-C01 | P0 冻结删除口径与执行清单 | Governance | 否 | 无 |
| WS-C02 | P1 统一入口 `check_workflow_contract.py` | Backend | 否 | C01 |
| WS-C03 | P1 L1 旧脚本 wrapper 兼容壳 | Backend | 否 | C02 |
| WS-C04 | P1 命令/技能/文档引用迁移 | Docs | 否 | C03 |
| WS-C05 | P2 旧入口调用观测 | Backend | 否 | C04 |
| WS-C06 | P2 TTL 归档与过程文件裁剪 | Backend | 否 | C05 |
| WS-C07 | P3 删除旧实现与兼容壳收口 | Backend | 否 | C06 |
| WS-G01 | G01 全链路验收门禁 | Gate | 否 | C07 |

## 5. 冲突矩阵（互不干涉）

| 资源 | Owner WS | 其他 WS 是否可改 | 规则 |
|---|---|---|---|
| `scripts/check_workflow_contract.py` | WS-C02/WS-C05/WS-C06/WS-C07 | 否 | 串行独占写 |
| `scripts/check_clarify_plan_alignment.py` 等 L1 旧脚本 | WS-C03 | 否 | wrapper 阶段独占写 |
| `.cursor/commands/*` `.agents/skills/*` `docs/开发文档/*` | WS-C04 | 否 | 引用迁移集中收口 |
| `docs/内部参考/任务拆解/2026-03-06_工程减法治理/*` | WS-G01 | 否 | Gate 证据专用 |

## 6. 依赖图与里程碑

- 依赖图: `C01 -> C02 -> C03 -> C04 -> C05 -> C06 -> C07 -> G01`
- 里程碑:
  1. M1: P0 冻结删除口径完成
  2. M2: P1 统一入口 + wrapper + 引用迁移完成
  3. M3: P2 usage 观测与 TTL 归档边界完成
  4. M4: P3 删除旧实现并通过 G01 放行

## 7. 合并策略

- 合并顺序: 按 `card_order` 串行推进
- 回归门禁: 每卡 `acceptance_checks` 全绿后再进入下一卡
- 回滚策略: 优先卡级回滚锚点，禁止跨卡混退

## 8. 看板导出索引

- `task_key`: `PP-20260306-workflow-gate-retirement`
- 拆解目录 ID: `2026-03-06_工程减法治理`
- WS 总数: `9`（含 `WS-00` 与 `WS-G01`）
- Gate 总数: `1`
- 默认列流转: `Backlog -> Doing -> Review -> Gate -> Done`
- 卡片 ID 规则: `<task_key>::<WS-ID>`
- 卡片标题规则: `<CARD-ID> <标题> [<task_key>]`

## 9. Gate 执行状态

### 9.1 WS-G01 结果

- `check_clarify_plan_alignment`: 待执行
- `check_plan_vk_coverage`: 待执行

### 9.2 WS-G01 预期动作

1. 确认 `implementation_plan` 与 `vk_cards.json` 一致
2. 执行 `check_plan_vk_coverage.py`
3. 校验 `_active_task.json` 作用域三元组一致

## 10. 信息防丢失检查

- [x] 每个 `feature_id` 均落入某张卡
- [x] 每张卡含 `task_ids`、机制摘要与代码锚点
- [x] 每张卡含可执行 `acceptance_checks`
- [x] Gate 已实体化为独立卡片
- [x] PR 映射与 `implementation_plan` 一致

## 11. mapping_checks（机读）

```yaml
mapping_checks:
  forward_check: PASS
  reverse_check: PASS
  orphan_features: []
  duplicate_features: []
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

## 12. active_task_alignment（机读）

```yaml
active_task_alignment:
  task_key_match: true
  task_split_dir_match: true
  project_id_present: true
```
