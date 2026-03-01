# 并行计划书（模板）

> 计划 ID: PP-YYYYMMDD-XXX  
> 主题: <需求主题>  
> 输入来源: `docs/内部参考/迭代需求/<topic>_requirements.md` / `docs/内部参考/迭代需求/<topic>_implementation_plan.md`

## -1. 执行策略（新增）

- execution_mode: `serial | parallel`
- single_active_card: `true | false`
- card_order: `[]`（serial 模式必填）
- gate_contract:
  - mode: `as_cards | inline_only`
  - gate_ids: `[]`
  - depends_on: `{}`
- auto_done_policy:
  - implementation-card: `manual_gate | hard_gate`
  - inspection/question-card: `policy_gate`
- 说明：若 implementation_plan 中存在 `planning_contract`，此处必须与其一致。
- 说明：`gate_contract.mode=as_cards` 时，Gate 必须实体化为独立卡片并进入 `card_order`，禁止仅保留文档门禁描述。

### -1.1 automation_contract（新增，供自动执行器读取）

```yaml
automation_contract:
  source_of_truth: docs/内部参考/任务拆解/<task_split_dir>/_active_task.json
  active_index: docs/内部参考/任务拆解/_active_task.json
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

- 冻结范围：`done/result/interrupt`
- required/optional：
- 枚举与空值约束：
- 兼容策略：
- 协议机读文件：`contracts/sse_events_v1.json`

## 1. seed 来源

- `task_key`:
- 来源：`plan` / `vkplan 推导`
- `card_seed` 来源：
- 推导依据与风险：

### 1.1 功能机制包映射（必填）

| card_id | wave | feature_ids | 机制摘要 | 代码锚点 | 验证命令 | 回滚锚点 |
|---|---|---|---|---|---|---|
| C01 | P1 | P1-01,P1-02,P1-03,P1-04,P1-05 |  |  |  |  |

## 2. 目标与边界

- 目标：
- 非目标：
- 约束（架构/性能/合规）：

## 3. 架构冻结项（并行前必须确认）

- 模块边界：
- 状态契约（关键字段 canonical + 来源优先级）：
- 路由闭环（分析→消歧→确认→执行）：
- 前后端链路时序：

## 4. 工作包总览

> 建议先按“并行交付层”与“串行门禁层”分组，避免把回归和终稿文档放到并行阶段。

| WS | 名称 | 类型 | 负责人 | 可并行 | 依赖 |
|----|------|------|--------|--------|------|
| WS-00 | G0 协议冻结 | Foundation |  | 否 | 无 |
| WS-01 |  | Backend |  | 是 | WS-00 |
| WS-02 |  | Frontend |  | 是 | WS-00 |
| WS-G1 | 集成回归门禁 | Gate |  | 否 | WS-01, WS-02 |
| WS-G2 | 文档终稿门禁 | Gate |  | 否 | WS-G1 |

> serial 模式建议：`WS-C01 ... WS-C06` 映射 card 链路；Gate 作为 C 卡内门禁或串行尾卡。
> 若 `gate_contract.mode=as_cards`，必须把 `G01...Gn` 作为尾部独立卡片写入 `card_order`。

## 5. 冲突矩阵（互不干涉）

| 资源 | Owner WS | 其他 WS 是否可改 | 规则 |
|------|----------|------------------|------|
| 文件: `app/ai/workflow/todo_graph.py` | WS-01 | 否 | 单所有者 |
| 字段: `pending_operation.data.title` | WS-01 | 否 | 单写入权 |
| 接口: `/api/v1/chat/stream` | WS-02 | 只读 | 契约冻结 |

## 6. 依赖图与里程碑

- 依赖图：
- 里程碑：

## 7. 合并策略

- 合并顺序：并行交付层 -> 串行门禁层
- 回归门禁：
- 回滚策略：

## 8. 串行回退说明（若触发）

- 是否触发：
- 触发原因：
- 串行执行路线：

## 9. 看板导出索引

- `task_key`:
- 拆解目录 ID:
- WS 总数:
- Gate 总数:
- 默认列流转：`Backlog -> Doing -> Review -> Gate -> Done`
- 卡片 ID 规则：`<task_key>::<WS-ID>`
- 卡片标题规则：`<WS-ID> <标题> [<task_key>]`
- serial 建议顺序：`C01,C02,...,C06,G01,G02,G03,G04`（示例）

### 9.1 机读增强字段（必填）

`vk_cards.json.cards[*]` 必须包含：

1. `feature_ids`
2. `mechanism_summary`
3. `code_anchor_refs`
4. `example_refs`
5. `acceptance_checks`
6. `rollback_anchors`
7. `evidence_entry`
8. `task_mode`
9. `merge_required`

## 10. Gate 执行状态

### 10.1 WS-G1 结果

- `pytest`：
- `tsc`：
- `lint`：
- `docs_guard`：

### 10.2 WS-G2 预期动作

1.
2.
3.

## 11. Gate 收口结果

1. `WS-G1` 已执行：
2. `WS-G2` 已执行：
3. Gate 结论：

## 12. 信息防丢失检查（新增）

- [ ] 每个 `feature_id` 均落入某个 WS（无遗漏）
- [ ] 每个 WS 都有机制摘要 + 代码锚点 + 最小样例引用
- [ ] 每张卡都有可执行 `acceptance_checks`
- [ ] 卡片 `DoD` 与 `implementation_plan` 的 `done_gate` 一致
- [ ] `output/**` 仅作为证据引用，未直接复制长文
- [ ] 若 `implementation_plan` 出现 Gate（如 `G-1~G-4`），`planning_contract.gate_contract` 已显式声明
- [ ] 若 `gate_contract.mode=as_cards`，所有 `gate_ids` 已完整进入 `card_order` 且都存在对应卡片定义
- [ ] 若 Gate 契约不完整，本次计划标记 `BLOCKED`（FAIL_FAST），不得进入 `/jjk-vkplan`
