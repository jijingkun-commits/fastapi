# OpenClaw迁移重建基线 串行拆解计划

> 计划 ID: PP-20260221-OPENCLAW-REBUILD-BASELINE
> 主题: openclaw迁移重建基线
> 输入来源: `docs/内部参考/迭代需求/openclaw迁移重建基线_requirements.md` / `docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md`

## -1. 执行策略

- execution_mode: `serial`
- single_active_card: `true`
- card_order: `[C01, C02, C03, C04, C05, C06, G01, G02, G03, G04]`
- auto_done_policy:
  - implementation-card: `hard_gate`
  - inspection/question-card: `policy_gate`
- 与 planning_contract 一致性: `PASS`

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
  - required: `done/result/interrupt/stopped`
  - optional: `metadata.version`
- 兼容策略: `stopped` 为增量事件，不破坏既有消费方
- 终态语义冻结（同一 `run_id`）:
  - `done` 与 `stopped` 互斥，二者仅允许其一
  - `interrupt` 为挂起事件，不与 `done/stopped` 同帧并发
  - cancel 路径收口为 `stopped`，正常完成收口为 `done`
- 事件顺序冻结（同一 `run_id`）:
  - 正常链路: `... -> result|status|tool_* -> done`
  - 取消链路: `... -> result|status|tool_* -> stopped`
  - HITL 链路: `... -> interrupt`（resume 后进入正常/取消链路）
- 协议机读文件: `docs/内部参考/任务拆解/2026-02-21_openclaw迁移重建基线/contracts/sse_events_v1.json`

## 1. seed 来源

- task_key: `PP-20260221-OPENCLAW-REBUILD-BASELINE`
- 来源: `plan`
- card_seed 来源: `openclaw迁移重建基线_implementation_plan.md::planning_contract`
- 推导依据与风险: 严格继承卡片依赖链；风险集中在 C00 前置事实漂移与 Gate 证据回填遗漏

### 1.1 功能机制包映射

| card_id | wave | feature_ids | 机制摘要 | 代码锚点 | 验证命令 | 回滚锚点 |
|---|---|---|---|---|---|---|
| C01 | P1 | P1-01,P1-02,P1-03,P1-04,P1-05 | run 状态模型、取消控制面与 run_id 全链路接线；取消后阻断 token 回灌并 drain 队列 | app/services/chat_service.py::stream | PYTHONPATH=. pytest tests/unit/test_run_control_service.py | ENABLE_RUN_CONTROL,ENABLE_SSE_STOPPED_EVENT |
| C02 | P2 | P2-01 | 引入 Tool Registry/Policy/Broker 首期治理链路；按 task_mode/requires_evidence 分层启用证据门禁 | app/ai/workflow/multi_agent_graph.py::_get_common_tools | PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py | ENABLE_TOOL_GOVERNANCE,TOOL_POLICY_FAIL_MODE |
| C03 | P3 | P3-01 | Skill 定义、版本、用户绑定三层解耦；支持用户级绑定、生效与回滚 | app/models/agent_skill.py::AgentSkill | PYTHONPATH=. pytest tests/unit/test_skill_service.py -k binding | ENABLE_SKILL_VERSIONING,ENABLE_USER_SKILL_BINDING |
| C04 | P4 | P4-01 | Hybrid recall + pre-compaction flush 分阶段落地（C04a recall MVP / C04b flush 增强）；用户隔离与降级路径保底 | app/services/user_preference_memory_service.py::build_user_preference_context | PYTHONPATH=. pytest tests/unit/test_user_preference_memory_service.py -k context | ENABLE_MEMORY_RECALL,ENABLE_PRE_COMPACTION_FLUSH |
| C05 | P5 | P5-01 | 恢复/隔离/观测增强与异常降级；插件能力后置接线，不阻塞主链 | app/ai/workflow/multi_agent_graph.py::_build_supervisor_fallback_handoff | PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py -k fallback | ENABLE_RUNTIME_RECOVERY,ENABLE_PLUGIN_REGISTRY |
| C06 | P6 | P6-01 | G-1~G-4 门禁收口与证据链复核；docs/code/test 三线收口 | docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md::11.2 | python3 scripts/docs_guard.py --strict | WAVE_ROLLBACK_DRILL_MATRIX |
| G01 | G1 | G-1 | 实测证据闭环 Gate（evidence 四元组可核验） | docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md::4.11 | python3 scripts/docs_guard.py --strict | WAVE_ROLLBACK_DRILL_MATRIX |
| G02 | G2 | G-2 | 复合任务编排 Gate（依赖链/作用域门禁一致） | docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md::7 | python3 scripts/docs_guard.py --strict | WAVE_ROLLBACK_DRILL_MATRIX |
| G03 | G3 | G-3 | 契约一致性 Gate（planning_contract/vk_cards/cron 对齐） | docs/内部参考/任务拆解/2026-02-21_openclaw迁移重建基线/vk_cards.json | python3 scripts/docs_guard.py --strict | WAVE_ROLLBACK_DRILL_MATRIX |
| G04 | G4 | G-4 | 回滚演练 Gate（矩阵记录闭环） | docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md::11.6 | python3 scripts/docs_guard.py --strict | WAVE_ROLLBACK_DRILL_MATRIX |

## 2. 目标与边界

- 目标:
  1. 产出可被 OpenClaw 自动执行器消费的串行卡片。
  2. 保证 feature/card 映射一一对应，避免执行漂移。
  3. 将 Gate 证据入口和回滚锚点绑定到每张卡。
- 非目标:
  1. 本阶段不修改业务代码。
  2. 不新增第四类主文档。
- 约束:
  1. `execution_mode=serial` 单活推进。
  2. 不重命名 `card_id/feature_id`。
  3. `source_atoms_unmapped` 必须为空才能进入拆解。

## 3. 架构冻结项

- 模块边界: 运行时控制、工具治理、Skill治理、记忆链路、稳态恢复、发布收口分层推进。
- 状态契约: run_id/run_status、event_type、task_mode/requires_evidence、user_id 隔离字段。
- C00 前置冻结:
  - `t_chat_run` 表结构草案冻结（字段、索引、状态枚举）
  - `stopped/done/interrupt` 终态互斥与顺序语义冻结
  - `code_anchor_refs` 可解析校验通过（已存在文件必须可定位符号）
- 路由闭环: C00 -> C01 -> C02 -> C03 -> C04 -> C05 -> C06 -> G01 -> G02 -> G03 -> G04。
- 前后端链路时序: cancel API -> run_control -> workflow checkpoint -> SSE stopped -> 前端状态收口。

## 4. 工作包总览

| WS | 名称 | 类型 | 可并行 | 依赖 |
|---|---|---|---|---|
| WS-00 | C00 预检门禁冻结 | foundation | 否 | 无 |
| WS-C01 | P1 运行时可取消控制 | parallel | 否 | WS-00 |
| WS-C02 | P2 工具治理一期 | parallel | 否 | WS-C01 |
| WS-C03 | P3 Skill 多用户版本治理 | parallel | 否 | WS-C02 |
| WS-C04 | P4 记忆检索增强 | parallel | 否 | WS-C03 |
| WS-C05 | P5 稳态增强与插件后置接线 | parallel | 否 | WS-C02, WS-C04 |
| WS-C06 | P6 收口与回滚演练 | gate | 否 | WS-C01~WS-C05 |
| WS-G01 | G-1 实测证据闭环 | gate | 否 | WS-C06 |
| WS-G02 | G-2 复合任务编排 | gate | 否 | WS-G01 |
| WS-G03 | G-3 契约一致性 | gate | 否 | WS-G02 |
| WS-G04 | G-4 回滚演练 | gate | 否 | WS-G03 |

## 5. 合并策略

- 合并顺序: `C01 -> C02 -> C03 -> C04 -> C05 -> C06 -> G01 -> G02 -> G03 -> G04`
- 回归门禁: 每卡执行 `acceptance_checks`，并在 `evidence_entry` 回填证据。
- 回滚策略: 按 `rollback_anchors` 单卡回退，不跨卡混合回退。

## 6. FAIL_FAST 字段校验结果

- 校验字段: `feature_ids/mechanism_summary/code_anchor_refs/acceptance_checks/rollback_anchors/evidence_entry/task_mode/merge_required`
- 结果: `PASS`
- 缺失字段: `[]`

## 7. 双向覆盖校验结果

- forward: `PASS`（每张卡至少 1 个 feature）
- reverse: `PASS`（每个 feature 恰好映射 1 张实现卡）
- orphan: `PASS`（无遗漏 feature）
- duplicate: `PASS`（无重复漂移）

## 8. 看板导出索引

- task_key: `PP-20260221-OPENCLAW-REBUILD-BASELINE`
- 拆解目录 ID: `2026-02-21_openclaw迁移重建基线`
- cards: `C01~C06 + G01~G04`（C00 作为 preflight，不进入默认落卡）
- 默认列流转: `Backlog -> Doing -> Review -> Gate -> Done`
- single_active_card: `true`

## 9. 信息防丢失检查

- [x] 每个 `feature_id` 均落入某张卡（无遗漏）
- [x] 每张卡均有机制摘要 + 代码锚点 + 验收命令 + 回滚锚点
- [x] 每张卡均给出 `evidence_entry`
- [x] `done_gate` 与 implementation plan 主线一致，并补充多用户隔离与协议语义冻结门禁
- [x] 仅引用输入来源，不扩展额外计划来源
