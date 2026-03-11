# 知识库检索P2分阶段治理串行拆解计划

> 计划 ID: PP-20260301-KB-RETRIEVAL-P2  
> 主题: 知识库检索P2分阶段治理  
> 输入来源: `docs/内部参考/迭代需求/知识库检索P2分阶段治理_requirements.md` / `docs/内部参考/迭代需求/知识库检索P2分阶段治理_implementation_plan.md`

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
  - inspection/question-card: `policy_gate`
- 与 planning_contract 一致性: `PASS`
- TEAM 自动启用判定: `命中（cards>=8）`
- Team 能力状态: `TEAM_UNAVAILABLE_FALLBACK`（本轮降级单代理拆解）

### -1.1 automation_contract

```yaml
automation_contract:
  source_of_truth: workdocs/任务拆解/2026-03-01_知识库检索P2分阶段治理/contracts/_active_task.json
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

- 冻结范围: `done/result/interrupt`
- required/optional: required=`card_id/feature_ids/acceptance_checks/rollback_anchors`; optional=`example_refs/handoff_artifacts`
- 枚举与空值约束: `task_mode` 仅允许 `implementation-card|inspection-card|question-card`
- 协议机读文件: `workdocs/任务拆解/2026-03-01_知识库检索P2分阶段治理/contracts/sse_events_v1.json`

## 1. seed 来源

- `task_key`: `PP-20260301-KB-RETRIEVAL-P2`
- 来源: `plan`
- `card_seed` 来源: implementation_plan `planning_contract`
- 推导依据与风险: 严格继承 `card_order/depends_on/gate_contract`，不重命名 `card_id/feature_id`

### 1.1 功能机制包映射（必填）

| card_id | wave | feature_ids | 机制摘要 | 代码锚点 | 验证命令 | 回滚锚点 |
|---|---|---|---|---|---|---|
| C01 | S0 | P5-01 | 建立 KB 固定样本集并生成可复现基线分数；输出 relevance 与 citation 指标供后续阶段对比 | scripts/data/kb_offline_evaluation.py::evaluate_cases; tests/unit/test_kb_offline_evaluation.py::test_kb_offline_eval_summary | venv/bin/python scripts/data/kb_offline_evaluation.py --dry-run; venv/bin/python -m pytest -q tests/unit/test_kb_offline_evaluation.py | 暂停自动评测门禁，保留人工评审兜底 |
| C02 | S1 | P1-01,P1-02 | 显式区分 page_size 与 top_k 语义并配置化；补齐超时与错误降级路径，避免检索失败外抛 | app/ai/tools/ragflow_tool.py::_call_ragflow_retrieval; app/ai/tools/ragflow_tool.py::knowledge_search | venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k "payload or timeout" | 关闭 RAGFLOW_PAGE_SIZE 配置并回退旧 payload |
| C03 | S2 | P2-01,P2-02 | 同文档候选限额与重复片段去重；结果组装改为证据卡片，降低上下文噪声 | app/ai/tools/ragflow_tool.py::_dedup_and_cap_candidates; app/ai/tools/ragflow_tool.py::_format_retrieval_results | venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k "dedup or evidence" | 关闭去重与文档限额开关 |
| C04 | S2 | P2-03 | 工具结果压缩与检索输出长度协同；记录 truncation_flag 作为质量诊断字段 | app/ai/workflow/multi_agent_graph.py::_truncate_tool_message_text; app/ai/workflow/multi_agent_graph.py::_prepare_messages_for_supervisor_inference | venv/bin/python -m pytest -q tests/unit/test_multi_agent_streaming_helpers.py -k tool_message | 回退 SUPERVISOR_TOOL_MESSAGE 配置与压缩逻辑 |
| C05 | S3 | P3-01,P3-02 | 原问主路 + 扩展路并行召回；多路候选融合排序并保留可解释分数 | app/ai/tools/ragflow_tool.py::_build_retrieval_queries; app/ai/tools/ragflow_tool.py::_merge_and_rerank_candidates | venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k "rewrite or rerank" | 关闭 query rewrite 开关，仅保留原问主路 |
| C06 | S4 | P4-01 | 根据 query 领域判定构建 metadata_condition；路由失败可回退全库检索路径 | app/ai/tools/ragflow_tool.py::_build_metadata_condition | venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k metadata | 关闭领域路由与 metadata 过滤开关 |
| C07 | S5 | P5-02 | 检索日志字段扩展并支持灰度指标追踪；补齐运行手册、文档与索引同步 | app/ai/tools/ragflow_tool.py::_build_retrieval_log; app/ai/workflow/multi_agent_graph.py::_prepare_messages_for_supervisor_inference | venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k retrieval_log; python3 scripts/docs_guard.py --strict | 回退日志扩展并关闭灰度策略开关 |
| G01 | Gate | G-1 | 统一放行标准：相关性@5 >= 80%，错误引用率 <= 5%；未达标阻断进入下游落卡与实施 | scripts/data/kb_offline_evaluation.py::evaluate_cases; docs/内部参考/迭代需求/知识库检索P2分阶段治理_implementation_plan.md::planning_contract | venv/bin/python scripts/data/kb_offline_evaluation.py --stage gate; python3 scripts/docs_guard.py --strict | 冻结放量并回退到上一稳定阶段配置 |

## 2. 目标与边界

- 目标: 将 `/jjk-plan` 主计划拆解为可落卡、可执行、可追溯卡片，并继承 PR 映射契约
- 非目标: 本阶段不直接实施代码改造，不修改需求语义
- 约束: 禁止重命名 `card_id/feature_id`，禁止弱化 `depends_on`

## 3. 架构冻结项

- 模块边界: 检索策略集中在 `ragflow_tool`；预算协同在 `multi_agent_graph`
- 状态契约: 参数快照、候选阶段状态、截断标识、引用一致性
- 路由闭环: 原问主路 -> 扩展路 -> 融合重排 -> 证据卡片 -> 推理
- 前后端链路时序: 先检索后组装，推理阶段仅消费裁剪后上下文

## 4. 工作包总览

| WS | 名称 | 类型 | 负责人 | 可并行 | 依赖 |
|----|------|------|--------|--------|------|
| WS-00 | C00 预检门禁冻结 | Foundation | 待定 | 否 | 无 |
| WS-C01 | C01 S0 离线评测与基线冻结 | Foundation | 待定 | 否 | 无 |
| WS-C02 | C02 S1 检索契约修正 | Backend | 待定 | 否 | C01 |
| WS-C03 | C03 S2 候选去重与证据卡片 | Backend | 待定 | 否 | C02 |
| WS-C04 | C04 S2 编排预算协同 | Backend | 待定 | 否 | C03 |
| WS-C05 | C05 S3 查询改写与融合重排 | Backend | 待定 | 否 | C04 |
| WS-C06 | C06 S4 领域路由与过滤 | Backend | 待定 | 否 | C05 |
| WS-C07 | C07 S5 灰度可观测与文档收口 | Fullstack | 待定 | 否 | C06 |
| WS-G01 | G01 Gate 统一质量门禁 | Gate | 待定 | 否 | C07 |

## 5. 冲突矩阵（互不干涉）

| 资源 | Owner WS | 其他 WS 是否可改 | 规则 |
|------|----------|------------------|------|
| `app/ai/tools/ragflow_tool.py` | WS-C02~WS-C06 | 否 | 串行独占写 |
| `app/ai/workflow/multi_agent_graph.py` | WS-C04/WS-C07 | 否 | 串行独占写 |
| `scripts/data/kb_offline_evaluation.py` | WS-C01/WS-G01 | 否 | 评测脚本单写入权 |
| `docs/SUMMARY.md` | WS-C07 | 否 | 文档收口专用 |

## 6. 依赖图与里程碑

- 依赖图: `C01 -> C02 -> C03 -> C04 -> C05 -> C06 -> C07 -> G01`
- 里程碑:
  1. M1: 基线评测可复现
  2. M2: 参数契约与候选清洗稳定
  3. M3: 改写融合与路由过滤达标
  4. M4: 灰度放量与质量门禁通过

## 7. 合并策略

- 合并顺序: 按 `card_order` 串行推进
- 回归门禁: 每卡 `acceptance_checks` 全绿后才进入下一卡
- 回滚策略: 优先使用卡级 `rollback_anchors`，禁止跨卡混退

## 8. 看板导出索引

- `task_key`: `PP-20260301-KB-RETRIEVAL-P2`
- 拆解目录 ID: `2026-03-01_知识库检索P2分阶段治理`
- WS 总数: `9`（含 `WS-00` 与 `WS-G01`）
- Gate 总数: `1`
- 默认列流转: `Backlog -> Doing -> Review -> Gate -> Done`
- 卡片 ID 规则: `<task_key>::<WS-ID>`
- 卡片标题规则: `<CARD-ID> <标题> [<task_key>]`

## 9. Gate 执行状态

### 9.1 WS-G01 结果

- `offline_eval`: 待执行
- `docs_guard`: 待执行

### 9.2 WS-G01 预期动作

1. 执行统一样本集评测并产出指标报告
2. 核验“人工相关性@5 >= 80%”与“错误引用率 <= 5%”
3. 若未达标则冻结推进并回退上一稳定阶段

## 10. 信息防丢失检查

- [x] 每个 `feature_id` 均落入某张卡
- [x] 每张卡包含机制摘要 + 代码锚点 + 验证命令 + 回滚锚点
- [x] 每张实现卡具备 PR 映射字段
- [x] Gate 已实体化并进入 `card_order`
- [x] `task_to_pr_mapping` 与卡片字段一致

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
