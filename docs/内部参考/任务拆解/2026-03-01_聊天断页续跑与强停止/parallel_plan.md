# 聊天断页续跑与强停止串行拆解计划

> 计划 ID: PP-20260301-CHAT-RUN-STOP  
> 主题: 聊天断页续跑与强停止  
> 输入来源: `docs/内部参考/迭代需求/聊天断页续跑与强停止_requirements.md` / `docs/内部参考/迭代需求/聊天断页续跑与强停止_implementation_plan.md`

## -1. 执行策略

- execution_mode: `serial`
- single_active_card: `true`
- card_order: `['C01', 'C02', 'C03', 'G01']`
- gate_contract:
  - mode: `as_cards`
  - gate_ids: `['G01']`
  - depends_on: `{'G01': ['C03']}`
- auto_done_policy:
  - implementation-card: `hard_gate`
  - inspection/question-card: `policy_gate`
- 与 planning_contract 一致性: `PASS`（继承 implementation_plan）

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
- required/optional: required=`card_id/feature_ids/acceptance_checks/rollback_anchors`; optional=`example_refs/handoff_artifacts`
- 枚举与空值约束: `task_mode` 仅允许 `implementation-card|inspection-card|question-card`
- 协议机读文件: `docs/内部参考/任务拆解/2026-03-01_聊天断页续跑与强停止/contracts/sse_events_v1.json`

## 1. seed 来源

- `task_key`: `PP-20260301-CHAT-RUN-STOP`
- 来源: `plan`
- `card_seed` 来源: implementation_plan planning_contract
- 推导依据与风险: 严格继承 `card_order/depends_on/gate_contract`，不重命名 `card_id/feature_id`

### 1.1 功能机制包映射（必填）

| card_id | wave | feature_ids | 机制摘要 | 代码锚点 | 验证命令 | 回滚锚点 |
|---|---|---|---|---|---|---|
| C01 | P1 | P1-01,P1-02 | run_id 合同升级 + cancelRun API | backend.ts/message.ts | eslint | 回退契约扩展 |
| C02 | P2 | P1-02,P1-03 | 强停止 + disconnect/cancel 解耦 | useSSEStream/chat_service | playwright+pytest | 回退 stop 与 stream 语义 |
| C03 | P3 | P1-04,P1-05 | 最近会话自动回显 + 失败收口 | chat_repo/chat_api/LoginCard | pytest+playwright | 回退 latest_thread 与跳转逻辑 |
| G01 | Gate | G-1 | 全链路硬门禁 | docs_guard/_active_task | docs_guard+pytest | 阻断 vktodo 执行 |

## 2. 目标与边界

- 目标: 生成可执行卡片并绑定 PR 归属，确保 stop 强语义与断页续跑不冲突
- 非目标: 本阶段不直接改业务代码；不新增第四类主文档
- 约束: 禁止重命名 card_id/feature_id；禁止弱化 depends_on

## 3. 架构冻结项

- 模块边界: run 控制归后端裁决，前端负责触发与状态回显
- 状态契约: `thread_id/run_id/status` 为主链关键字段
- 路由闭环: submit -> init(run_id) -> stop(cancel) / close(disconnect)
- 前后端时序: 先 cancel API 再本地 abort；断页不触发 cancel

## 4. 工作包总览

| WS | 名称 | 类型 | 负责人 | 可并行 | 依赖 |
|----|------|------|--------|--------|------|
| WS-00 | C00 预检门禁冻结 | Foundation | 待定 | 否 | 无 |
| WS-C01 | C01 P1 合同升级（run_id 与 cancelRun） | Frontend | 待定 | 否 | 无 |
| WS-C02 | C02 P2 强停止与断连语义解耦 | Fullstack | 待定 | 否 | C01 |
| WS-C03 | C03 P3 最近会话回显与收口 | Fullstack | 待定 | 否 | C02 |
| WS-G01 | G01 Gate 全链路验收门禁 | Gate | 待定 | 否 | C03 |

## 5. 冲突矩阵（互不干涉）

| 资源 | Owner WS | 其他 WS 是否可改 | 规则 |
|------|----------|------------------|------|
| `web/src/hooks/useSSEStream.ts` | WS-C02/WS-C03 | 否 | 串行独占写 |
| `app/services/chat_service.py` | WS-C02 | 否 | 运行时语义单卡改造 |
| `app/api/v1/endpoints/chat_api.py` | WS-C02/WS-C03 | 否 | API 契约变更同卡收敛 |
| `docs/内部参考/迭代需求/聊天断页续跑与强停止_implementation_plan.md` | WS-C03/WS-G01 | 否 | Gate 证据回填专用 |

## 6. 依赖图与里程碑

- 依赖图: `C01 -> C02 -> C03 -> G01`
- 里程碑:
  1. M1: run_id 契约与 cancel API 打通
  2. M2: stop 强语义与断连续跑改造完成
  3. M3: 最近会话回显与回归收口
  4. M4: Gate 验收通过

## 7. 合并策略

- 合并顺序: 按 `card_order` 串行推进
- 回归门禁: 每卡 acceptance_checks 全绿后再合并
- 回滚策略: 优先卡级回滚锚点，禁止跨卡混退

## 8. 看板导出索引

- `task_key`: `PP-20260301-CHAT-RUN-STOP`
- 拆解目录 ID: `2026-03-01_聊天断页续跑与强停止`
- WS 总数: `5`（含 `WS-00`）
- Gate 总数: `1`
- 默认列流转: `Backlog -> Doing -> Review -> Gate -> Done`
- 卡片 ID 规则: `<task_key>::<WS-ID>`
- 卡片标题规则: `<CARD-ID> <标题> [<task_key>]`

## 9. Gate 执行状态

### 9.1 WS-G01 结果

- `pytest`: 待执行
- `docs_guard`: 待执行
### 9.2 WS-G01 预期动作

1. 执行 stop 语义与断连续跑关键回归
2. 执行 `docs_guard --strict`
3. 校验 active_task 作用域三元组一致

## 10. 信息防丢失检查

- [x] 每个 feature_id 均落入某张卡
- [x] 每张卡含机制摘要 + 代码锚点
- [x] 每张卡含可执行 acceptance_checks
- [x] Gate 已实体化为独立卡片
- [x] PR 映射与 implementation_plan 一致

## 11. mapping_checks（机读）

```yaml
mapping_checks:
  forward_check: PASS
  reverse_check: PASS
  orphan_features: []
  duplicate_features: []
  pr_mapping_check: PASS
  pr_mapping_errors: []
```

## 12. active_task_alignment（机读）

```yaml
active_task_alignment:
  task_key_match: true
  task_split_dir_match: true
  project_id_present: true
```
