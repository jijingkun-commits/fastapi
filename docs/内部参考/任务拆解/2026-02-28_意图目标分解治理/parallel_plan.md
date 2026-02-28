# 意图目标分解治理（D+B统一）串行拆解计划

> 计划 ID: PP-20260228-INTENT-DECOMPOSITION-DB
> 主题: 意图目标分解治理
> 输入来源: `docs/内部参考/迭代需求/意图目标分解治理_requirements.md` / `docs/内部参考/迭代需求/意图目标分解治理_implementation_plan.md`

## -1. 执行策略

- execution_mode: `serial`
- single_active_card: `true`
- card_order: `['C01', 'C02', 'C03', 'C04', 'C05', 'C06', 'C07', 'C08', 'G01', 'G02', 'G03']`
- gate_contract:
  - mode: `as_cards`
  - gate_ids: `['G01', 'G02', 'G03']`
  - depends_on: `{'G01': ['C05'], 'G02': ['G01'], 'G03': ['C08']}`
- auto_done_policy:
  - implementation-card: `hard_gate`
  - inspection/question-card: `policy_gate`
- 与 planning_contract 一致性: `PASS`（继承 `docs/内部参考/迭代需求/意图目标分解治理_implementation_plan.md#12.4`）

### -1.1 automation_contract

```yaml
automation_contract:
  source_of_truth: docs/内部参考/任务拆解/_active_task.json
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

- 冻结范围: `done/result/interrupt/stopped`
- required/optional:
  - required: `thread_id/message_id/run_id`
  - optional: `metadata/version`
- 枚举与空值约束: `task_mode` 只允许 `implementation-card|inspection-card|question-card`
- 兼容策略: 新字段只增不删，旧消费方可忽略未知字段
- 协议机读文件: `docs/内部参考/任务拆解/2026-02-28_意图目标分解治理/contracts/sse_events_v1.json`

## 1. seed 来源

- `task_key`: `PP-20260228-INTENT-DECOMPOSITION-DB`
- 来源: `plan`
- `card_seed` 来源: `docs/内部参考/迭代需求/意图目标分解治理_implementation_plan.md::planning_contract`
- 推导依据与风险: 严格继承 card_order/depends_on，不重命名 card_id/feature_id

### 1.1 功能机制包映射（必填）

| card_id | wave | feature_ids | 机制摘要 | 代码锚点 | 验证命令 | 回滚锚点 |
|---|---|---|---|---|---|---|
| C01 | P1 | P1-01,P1-02 | 分层契约 + 模型主判定 | multi_agent_graph/chat_service | pytest intent layer + model primary | ENABLE_INTENT_LAYERING |
| C02 | P1 | P1-03 | fallback 触发网关收敛 | multi_agent_graph | pytest fallback gate | ENABLE_INTENT_FALLBACK_GATE |
| C03 | P1 | P1-04 | 运行时证据对账 | multi_agent_graph | pytest coverage reconcile | ENABLE_COVERAGE_RECONCILE |
| C04 | P1 | P1-05 | SSE 双口径展示 | multi_agent_graph/chat_service | pytest chat sse status | ENABLE_SSE_INTENT_GOAL_STATUS_V2 |
| C05 | P1 | P1-06 | 灰度指标与回滚开关 | config_resolver/multi_agent_graph | pytest shadow metrics | ENABLE_INTENT_SHADOW_COMPARE |
| C06 | P2 | P2-01,P2-02 | 策略路由 + Tool Calling 主路径 | multi_agent_graph/llm_util | pytest planner router + tool_call | PLANNER_DISABLE_TOOL_CALL |
| C07 | P2 | P2-03,P2-04 | json_object + text_parse 降级链 | multi_agent_graph | pytest json/text fallback | PLANNER_DISABLE_JSON_OBJECT |
| C08 | P2 | P2-05 | reason_code 统一观测 | multi_agent_graph/chat_service | pytest reason codes | PLANNER_REASON_CODE_VERBOSE |
| G01 | G-1 | G-1 | 契约一致性门禁 | docs_guard | docs_guard strict | WAVE_ROLLBACK_DRILL_MATRIX |
| G02 | G-2 | G-2 | 灰度稳定性门禁 | shadow metrics | pytest shadow metrics | INTENT_MODE=heuristic_only |
| G03 | G-3 | P2-06 | D+B 文档收口门禁 | AI模块设计/防屎山手册 | docs_guard strict | revert D+B docs section commit |

## 2. 目标与边界

- 目标:
  1. 生成可直接供 `/jjk-vktodo` 消费的 `vk_cards.json`。
  2. 保证 D+B 卡片链路在串行模式下可执行。
  3. 将 Gate 以独立卡片纳入 card_order 统一门禁。
- 非目标:
  1. 本阶段不直接实施代码改动。
  2. 不新增第四类主文档。
- 约束（架构/性能/合规）:
  1. 不重命名 `card_id/feature_id`。
  2. 不弱化 `depends_on` 硬依赖。

## 3. 架构冻结项（并行前必须确认）

- 模块边界: planner/router/coverage/composer 分层责任不可越层。
- 状态契约: `intent_plan/fallback_meta/coverage_report` 为主字段。
- 路由闭环: `tool_call -> json_object -> text_parse -> heuristic_fallback`。
- 前后端链路时序: `plan_ready -> coverage_check -> final_answer -> done`。

## 4. 工作包总览

| WS | 名称 | 类型 | 负责人 | 可并行 | 依赖 |
|----|------|------|--------|--------|------|
| WS-00 | C00 预检门禁冻结 | Foundation | 待定 | 否 | 无 |
| WS-C01 | C01 P1 控制面与语义面分层契约落地 | Backend | 否 | 无 |
| WS-C02 | C02 P1 fallback触发网关与规则兜底收敛 | Backend | 否 | C01 |
| WS-C03 | C03 P1 运行时证据对账与覆盖率收敛 | Backend | 否 | C02 |
| WS-C04 | C04 P1 SSE展示口径升级 | Backend | 否 | C03 |
| WS-C05 | C05 P1 观测指标灰度与回滚开关 | Backend | 否 | C04 |
| WS-C06 | C06 P2 策略路由与ToolCalling主路径 | Backend | 否 | C05 |
| WS-C07 | C07 P2 json_object与text_parse降级链路 | Backend | 否 | C06 |
| WS-C08 | C08 P2 reason_code标准化与观测统一 | Backend | 否 | C07 |
| WS-G01 | G01 G-1 契约一致性门禁 | Gate | 否 | C05 |
| WS-G02 | G02 G-2 灰度稳定性门禁 | Gate | 否 | G01 |
| WS-G03 | G03 G-3 D+B文档收口门禁 | Gate | 否 | C08 |

## 5. 冲突矩阵（互不干涉）

| 资源 | Owner WS | 其他 WS 是否可改 | 规则 |
|------|----------|------------------|------|
| `app/ai/workflow/multi_agent_graph.py` | WS-C01/WS-C06/WS-C07/WS-C08 | 否 | 单卡串行独占 |
| `app/services/chat_service.py` | WS-C01/WS-C04/WS-C08 | 否 | 单卡串行独占 |
| `docs/内部参考/迭代需求/意图目标分解治理_implementation_plan.md` | WS-G01/WS-G03 | 否 | Gate 卡独占 |

## 6. 依赖图与里程碑

- 依赖图: `C01 -> C02 -> C03 -> C04 -> C05 -> C06 -> C07 -> C08 -> G03`，并行 Gate 支路 `C05 -> G01 -> G02`。
- 里程碑:
  1. M1: P1 完成（C01~C05）
  2. M2: D+B 兼容链完成（C06~C08）
  3. M3: 三道 Gate 完成（G01~G03）

## 7. 合并策略

- 合并顺序: 按 `card_order` 串行。
- 回归门禁: 每卡 `acceptance_checks` 必过且 evidence 回填。
- 回滚策略: 卡级回滚锚点优先，禁止跨卡回滚。

## 8. 看板导出索引

- `task_key`: `PP-20260228-INTENT-DECOMPOSITION-DB`
- 拆解目录 ID: `2026-02-28_意图目标分解治理`
- WS 总数: `12`（含 `WS-00`）
- Gate 总数: `3`
- 默认列流转: `Backlog -> Doing -> Review -> Gate -> Done`
- 卡片 ID 规则: `<task_key>::<WS-ID>`
- 卡片标题规则: `<CARD-ID> <标题> [<task_key>]`

## 9. Gate 执行状态

### 9.1 WS-G1 结果

- `pytest`: 待执行
- `tsc`: N/A
- `lint`: N/A
- `docs_guard`: 待执行

### 9.2 WS-G2 预期动作

1. 跑 `tests/integration/test_intent_shadow_metrics.py`。
2. 回填灰度窗口指标证据。
3. 标记是否满足放量门禁。

## 10. 信息防丢失检查

- [x] 每个 `feature_id` 均落入某张卡
- [x] 每张卡含机制摘要 + 代码锚点 + 最小样例引用
- [x] 每张卡含可执行 `acceptance_checks`
- [x] 卡片 `DoD` 与 implementation plan `done_gate` 对齐
- [x] `gate_contract.mode=as_cards` 且 gate_ids 全量实体化
