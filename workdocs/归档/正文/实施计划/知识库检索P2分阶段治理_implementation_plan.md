# 知识库检索P2分阶段治理_implementation_plan

> 文档日期：2026-03-01
> 文档定位：把“知识库检索 P2 分阶段治理”落成可执行工单级 HOW
> 执行模式：`serial`（plan-only，本轮不自动触发实施链路）

---

## 0. 输入来源清单

1. `workdocs/归档/正文/设计/2026-03-01-kb-retrieval-p2-phased-design.md`
2. `workdocs/归档/正文/需求/知识库检索P2分阶段治理_requirements.md`
3. `app/ai/tools/ragflow_tool.py`
4. `app/ai/workflow/multi_agent_graph.py`
5. `app/core/config.py`
6. `tests/unit/test_ragflow_tool.py`
7. `docs/API文档/外部服务集成.md`
8. `docs/开发文档/快速入门/生产部署手册.md`

---

## 0.1 设计审批门禁

设计文档已通过审批：

- 设计文档：`workdocs/归档/正文/设计/2026-03-01-kb-retrieval-p2-phased-design.md`
- 审批记录：`design_approved: true`
- 审批时间：`2026-03-01 16:05 CST`
- 审批轮次：`round-1`
- `DESIGN_APPROVAL_FALLBACK_ACK`: false

---

## 0.2 执行意图门禁

- 用户本轮目标：生成计划文档（`$jjk-plan`），未要求直接实施。
- 本轮策略：`plan-only`。
- `PLAN_EXECUTION_INTENT_REQUIRED`: true
- 下游命令需用户显式触发：`$jjk-vkplan` 或 `$jjk-imp`。

---

## 0.3 Superpowers 产物桥接

桥接结论：`SUPERPOWERS_ARTIFACT_UNALIGNED = false`

桥接关系：

1. `workdocs/归档/正文/设计/2026-03-01-kb-retrieval-p2-phased-design.md`（设计）
   -> 本文 `Feature Packet + implementation_tasks + planning_contract`
2. 设计中的阶段目标（S0-S5）
   -> 本文 `phase` 与 `card_order`
3. 设计中的统一门槛（相关性/错引）
   -> 本文 `done_gate` 与 `acceptance_checks`

---

## 0.4 Team 模式判定

- 任务规模：跨工具层、编排层、配置层、测试与文档层，属于大任务。
- 本轮实际执行：单代理文档规划（未启用 OMX Team 实时编排）。
- `TEAM_UNAVAILABLE_FALLBACK`: true
- 说明：本轮输出为统一主计划，后续可由 `$jjk-vkplan` 进入并行拆包。

---

## 1. 架构影响与约束（强制评审项）

### 1.1 模块边界

1. `app/ai/tools/ragflow_tool.py` 负责检索参数、候选整形与检索策略主逻辑。
2. `app/ai/workflow/multi_agent_graph.py` 负责推理前上下文预算与压缩协同，不承载检索策略细节。
3. `app/core/config.py` 负责运行时配置读取；策略默认值在配置层统一。
4. 测试只验证契约行为，不在测试中重写策略逻辑。

### 1.2 状态契约

1. 检索参数快照：`page_size/top_k/similarity_threshold/vector_weight`。
2. 候选状态：`raw_candidates -> dedup_candidates -> reranked_candidates -> selected_candidates`。
3. 引用一致性标识：`citation_mismatch`（布尔）。
4. 截断标识：`truncation_flag`（布尔）。

### 1.3 路由闭环

1. 用户 query 进入 `knowledge_search`。
2. 主路（原问）与扩展路（改写）进入检索器。
3. 候选融合重排后输出证据卡片。
4. Supervisor 按预算压缩并推理。
5. 回答输出携带来源，审计指标入日志。

### 1.4 端到端链路一致性

```mermaid
flowchart LR
    A["User Query"] --> B["knowledge_search (ragflow_tool)"]
    B --> C["RAGFlow retrieval"]
    C --> D["候选去重/重排/限额"]
    D --> E["证据卡片组装"]
    E --> F["Supervisor 预算压缩"]
    F --> G["LLM Answer + Citation"]
    G --> H["可观测日志与评估"]
```

### 1.5 可测试性

1. 参数契约单测：请求 payload 正确性。
2. 候选处理单测：去重、限额、融合排序。
3. 编排协同单测：上下文长度与截断行为。
4. 离线评测：统一样本集指标对比。

---

## 2. 方案决策

| 方案 | 优点 | 缺点 | 成本 | 推荐度 |
|---|---|---|---|---|
| 仅参数调优 | 快速 | 难解决结构性问题 | 低 | ⭐⭐⭐ |
| 分阶段治理（参数+策略+评估） | 可验证、可回滚、可持续优化 | 需要维护评测资产 | 中 | ⭐⭐⭐⭐⭐ |
| 先全量重建知识库 | 上限高 | 周期长，短期收益慢 | 高 | ⭐⭐⭐⭐ |

结论：采用“分阶段治理”，并且每阶段设置人工闸门。

---

## 3. 功能机制包总表（Feature Packet）

| feature_id | phase | 目标与边界 | 触发条件与状态流转 | 代码锚点 | 关键字段 | 回滚锚点 | 验证命令 | 来源证据 |
|---|---|---|---|---|---|---|---|---|
| P1-01 | S1 | 参数契约化（`page_size/top_k` 解耦） | 请求进入 -> 参数归一化 -> 发起检索 | `app/ai/tools/ragflow_tool.py` `_call_ragflow_retrieval` | `page_size/top_k` | 关闭新参数开关 | `venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k payload` | 设计文档 §1.1 |
| P1-02 | S1 | 请求稳健性（超时/失败降级） | API 异常 -> 降级响应 -> 记录日志 | `ragflow_tool.py` `knowledge_search` | `timeout/error_type` | 回退旧异常处理路径 | `venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k timeout` | 设计文档 §7 |
| P2-01 | S2 | 候选去重与文档限额 | raw -> dedup -> doc_cap -> selected | `ragflow_tool.py` `_dedup_and_cap_candidates`（新增） | `document_id/max_chunks_per_doc` | 关闭去重限额开关 | `venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k dedup` | 设计文档 §4 |
| P2-02 | S2 | 证据卡片化组装 | selected -> evidence_cards -> result_text | `ragflow_tool.py` `_format_retrieval_results` | `evidence_card/context_chars` | 回退旧拼接模式 | `venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k evidence` | 设计文档 §4.2 |
| P2-03 | S2 | 编排层预算协同 | tool_message -> compact -> inference | `app/ai/workflow/multi_agent_graph.py` `_truncate_tool_message_text` | `truncation_flag` | 回退旧预算配置 | `venv/bin/python -m pytest -q tests/unit/test_multi_agent_streaming_helpers.py -k tool_message` | 设计文档 §1.1 |
| P3-01 | S3 | 查询改写主副路 | 原问 -> 扩展问生成 -> 多路检索 | `app/ai/tools/ragflow_tool.py` `_build_retrieval_queries`（新增） | `query_variants` | 关闭改写开关，仅主路 | `venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k rewrite` | 设计文档 §4.2 |
| P3-02 | S3 | 多路融合重排 | 多路候选 -> 融合 -> 综合分排序 | `ragflow_tool.py` `_merge_and_rerank_candidates`（新增） | `route_weight/final_score` | 回退单路策略 | `venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k rerank` | 设计文档 §4.2 |
| P4-01 | S4 | 领域路由与 metadata 过滤 | query -> domain -> metadata_condition -> retrieval | `ragflow_tool.py` `_build_metadata_condition`（新增） | `domain/metadata_condition` | 关闭路由过滤 | `venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k metadata` | 设计文档 §4.2 |
| P5-01 | S0/S5 | 离线评测框架 | 样本集 -> 批跑 -> 指标汇总 | `scripts/data/kb_offline_evaluation.py`（新增） | `avg_relevance/error_citation_rate` | 回退人工评审兜底 | `venv/bin/python scripts/data/kb_offline_evaluation.py --dry-run` | 设计文档 §14 |
| P5-02 | S5 | 灰度与回滚运行手册 | 放量 -> 监控 -> 触发回滚 | `workdocs/归档/正文/实施计划/知识库检索P2分阶段治理_implementation_plan.md` | `rollout_stage` | 一键切回 S2/S4 配置 | `python3 scripts/docs_guard.py --strict` | 设计文档 §17 |

---

## 4. Feature Packet 详情（含最小代码样例）

### 4.1 P1-01 参数契约化

1. 目标：让“返回条数”和“候选深度”语义明确。
2. 边界：不改变原有 dataset 选择逻辑。
3. 状态流转：读取配置 -> 参数归一化 -> 请求发送。
4. 最小代码样例：

```python
payload = {
    "question": query,
    "dataset_ids": dataset_ids,
    "page_size": page_size,
    "top_k": top_k,
}
```

### 4.2 P2-01 候选去重与文档限额

1. 目标：降低重复候选对上下文预算的侵占。
2. 边界：不改写原始证据内容，仅改排序与选择。
3. 状态流转：按文档分桶 -> 去重 -> 限额 -> 汇总。
4. 最小代码样例：

```python
for doc_id, rows in grouped.items():
    kept.extend(sorted(rows, key=lambda x: x["similarity"], reverse=True)[:max_chunks_per_doc])
```

### 4.3 P2-02 证据卡片化

1. 目标：以短证据卡片替代整段原文堆叠。
2. 边界：图片占位符协议保持兼容。
3. 状态流转：selected -> card -> format -> return。
4. 最小代码样例：

```python
card = {
    "source": source_name,
    "score": score,
    "snippet": snippet[:320],
}
```

### 4.4 P3-01 查询改写

1. 目标：提升模糊问句命中。
2. 边界：原问主路不可丢失。
3. 状态流转：原问 -> 扩展问 -> 多路并发检索。
4. 最小代码样例：

```python
query_variants = [raw_query, *expand_terms(raw_query)]
```

### 4.5 P3-02 多路融合重排

1. 目标：兼顾语义召回与精确词命中。
2. 边界：排序可解释，保留分数字段。
3. 状态流转：route_scores -> final_score -> sort。
4. 最小代码样例：

```python
item["final_score"] = 0.6 * item["similarity"] + 0.4 * item["route_weight"]
```

### 4.6 P4-01 领域路由与过滤

1. 目标：减少跨域噪声文档。
2. 边界：路由失败可回退全库。
3. 状态流转：domain_detect -> metadata_condition -> retrieval。
4. 最小代码样例：

```python
if domain is None:
    metadata_condition = None
```

### 4.7 P5-01 评测闭环

1. 目标：让效果改进可量化。
2. 边界：不替代线上监控。
3. 状态流转：样本加载 -> 执行 -> 打分 -> 报告输出。
4. 最小代码样例：

```python
summary["avg_relevance"] = round(sum(scores) / len(scores), 4)
```

---

## 5. 测试策略（推荐，TDD 前置）

显式 TC 覆盖补齐：`TC-KB-01`、`TC-KB-02`、`TC-KB-03`、`TC-KB-04`、`TC-KB-05`、`TC-KB-06`、`TC-KB-07`、`TC-KB-08`。

```yaml
test_strategy:
  - feature_id: P1-01
    test_cases:
      - TC-KB-01-01: page_size 生效并控制返回条数
      - TC-KB-01-02: top_k 仅影响候选深度
    test_first: true
  - feature_id: P2-01
    test_cases:
      - TC-KB-02-01: 同文档重复 chunk 去重
      - TC-KB-02-02: 单文档候选上限生效
    test_first: true
  - feature_id: P3-01
    test_cases:
      - TC-KB-03-01: 改写失败时回退原问主路
    test_first: true
  - feature_id: P4-01
    test_cases:
      - TC-KB-04-01: 路由失败回退全库检索
    test_first: false
```

---

## 6. 工单级任务包（Implementation Tasks）

```yaml
implementation_tasks:
  - task_id: T-01
    feature_id: P1-01
    pr_id: PR-01
    phase: S1
    file_paths:
      - app/ai/tools/ragflow_tool.py
      - app/core/config.py
    symbols:
      - _call_ragflow_retrieval
      - knowledge_search
    change_type: modify
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k payload
    rollback_point: 关闭 RAGFLOW_PAGE_SIZE 配置并回退旧 payload 结构

  - task_id: T-02
    feature_id: P1-02
    pr_id: PR-01
    phase: S1
    file_paths:
      - app/ai/tools/ragflow_tool.py
    symbols:
      - knowledge_search
    change_type: modify
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k timeout
    rollback_point: 回退异常分支到当前稳定版本

  - task_id: T-03
    feature_id: P2-01
    pr_id: PR-02
    phase: S2
    file_paths:
      - app/ai/tools/ragflow_tool.py
      - tests/unit/test_ragflow_tool.py
    symbols:
      - _dedup_and_cap_candidates
    change_type: add
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k dedup
    rollback_point: 关闭去重策略开关并回退单路原始排序

  - task_id: T-04
    feature_id: P2-02
    pr_id: PR-02
    phase: S2
    file_paths:
      - app/ai/tools/ragflow_tool.py
    symbols:
      - _format_retrieval_results
    change_type: modify
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k evidence
    rollback_point: 回退到当前 result_text 拼接格式

  - task_id: T-05
    feature_id: P2-03
    pr_id: PR-03
    phase: S2
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
      - tests/unit/test_multi_agent_streaming_helpers.py
    symbols:
      - _truncate_tool_message_text
      - _prepare_messages_for_supervisor_inference
    change_type: modify
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_multi_agent_streaming_helpers.py -k tool_message
    rollback_point: 回退 SUPERVISOR_TOOL_MESSAGE_* 配置并恢复原压缩逻辑

  - task_id: T-06
    feature_id: P3-01
    pr_id: PR-04
    phase: S3
    file_paths:
      - app/ai/tools/ragflow_tool.py
      - tests/unit/test_ragflow_tool.py
    symbols:
      - _build_retrieval_queries
    change_type: add
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k rewrite
    rollback_point: 关闭 query rewrite 开关，仅保留原问

  - task_id: T-07
    feature_id: P3-02
    pr_id: PR-04
    phase: S3
    file_paths:
      - app/ai/tools/ragflow_tool.py
      - tests/unit/test_ragflow_tool.py
    symbols:
      - _merge_and_rerank_candidates
    change_type: add
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k rerank
    rollback_point: 回退到单路 similarity 排序

  - task_id: T-08
    feature_id: P4-01
    pr_id: PR-05
    phase: S4
    file_paths:
      - app/ai/tools/ragflow_tool.py
      - tests/unit/test_ragflow_tool.py
    symbols:
      - _build_metadata_condition
    change_type: add
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k metadata
    rollback_point: 关闭领域路由与 metadata 过滤

  - task_id: T-09
    feature_id: P5-01
    pr_id: PR-06
    phase: S0
    file_paths:
      - scripts/data/kb_offline_evaluation.py
      - tests/fixtures/kb_offline_eval_cases.json
    symbols:
      - evaluate_cases
      - calc_relevance_score
    change_type: add
    acceptance_cmds:
      - venv/bin/python scripts/data/kb_offline_evaluation.py --dry-run
    rollback_point: 保留人工评审兜底路径并暂停自动评测门禁

  - task_id: T-10
    feature_id: P5-01
    pr_id: PR-06
    phase: S0
    file_paths:
      - tests/unit/test_kb_offline_evaluation.py
    symbols:
      - test_kb_offline_eval_summary
    change_type: add
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_kb_offline_evaluation.py
    rollback_point: 保留脚本，禁用 CI 强校验

  - task_id: T-11
    feature_id: P5-02
    pr_id: PR-07
    phase: S5
    file_paths:
      - app/ai/tools/ragflow_tool.py
      - app/ai/workflow/multi_agent_graph.py
    symbols:
      - _build_retrieval_log
      - _prepare_messages_for_supervisor_inference
    change_type: modify
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k retrieval_log
    rollback_point: 回退新增日志字段并关闭灰度指标告警

  - task_id: T-12
    feature_id: P5-02
    pr_id: PR-07
    phase: S5
    file_paths:
      - docs/API文档/外部服务集成.md
      - docs/开发文档/快速入门/生产部署手册.md
      - docs/SUMMARY.md
    symbols:
      - RAG 参数说明章节
    change_type: modify
    acceptance_cmds:
      - python3 scripts/docs_guard.py --strict
    rollback_point: 回退文档变更并保留旧配置说明
```

---

## 7. 任务与 PR 映射契约（Task -> PR）

```yaml
task_to_pr_mapping:
  - task_id: T-01
    pr_id: PR-01
    pr_branch: codex/kb-retrieval-p2-pr-01
    pr_depends_on: []
    pr_subject: "S1 参数契约化与稳健性改造"
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k "payload or timeout"
    rollback_point: 关闭新参数配置并回退 payload

  - task_id: T-02
    pr_id: PR-01
    pr_branch: codex/kb-retrieval-p2-pr-01
    pr_depends_on: []
    pr_subject: "S1 参数契约化与稳健性改造"
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k timeout
    rollback_point: 回退异常降级分支

  - task_id: T-03
    pr_id: PR-02
    pr_branch: codex/kb-retrieval-p2-pr-02
    pr_depends_on: [PR-01]
    pr_subject: "S2 候选去重与文档限额"
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k dedup
    rollback_point: 关闭去重限额开关

  - task_id: T-04
    pr_id: PR-02
    pr_branch: codex/kb-retrieval-p2-pr-02
    pr_depends_on: [PR-01]
    pr_subject: "S2 候选去重与文档限额"
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k evidence
    rollback_point: 回退旧结果拼接

  - task_id: T-05
    pr_id: PR-03
    pr_branch: codex/kb-retrieval-p2-pr-03
    pr_depends_on: [PR-02]
    pr_subject: "S2 编排层预算协同"
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_multi_agent_streaming_helpers.py -k tool_message
    rollback_point: 回退工具消息压缩策略

  - task_id: T-06
    pr_id: PR-04
    pr_branch: codex/kb-retrieval-p2-pr-04
    pr_depends_on: [PR-03]
    pr_subject: "S3 查询改写与多路召回融合"
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k rewrite
    rollback_point: 关闭改写开关

  - task_id: T-07
    pr_id: PR-04
    pr_branch: codex/kb-retrieval-p2-pr-04
    pr_depends_on: [PR-03]
    pr_subject: "S3 查询改写与多路召回融合"
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k rerank
    rollback_point: 回退单路排序

  - task_id: T-08
    pr_id: PR-05
    pr_branch: codex/kb-retrieval-p2-pr-05
    pr_depends_on: [PR-04]
    pr_subject: "S4 领域路由与过滤"
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k metadata
    rollback_point: 关闭路由过滤

  - task_id: T-09
    pr_id: PR-06
    pr_branch: codex/kb-retrieval-p2-pr-06
    pr_depends_on: []
    pr_subject: "S0 离线评测框架与样本基线"
    acceptance_cmds:
      - venv/bin/python scripts/data/kb_offline_evaluation.py --dry-run
    rollback_point: 暂停自动评测门禁

  - task_id: T-10
    pr_id: PR-06
    pr_branch: codex/kb-retrieval-p2-pr-06
    pr_depends_on: []
    pr_subject: "S0 离线评测框架与样本基线"
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_kb_offline_evaluation.py
    rollback_point: 移除 CI 强依赖

  - task_id: T-11
    pr_id: PR-07
    pr_branch: codex/kb-retrieval-p2-pr-07
    pr_depends_on: [PR-05, PR-06]
    pr_subject: "S5 灰度可观测与运行闸门"
    acceptance_cmds:
      - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k retrieval_log
    rollback_point: 回退日志字段扩展

  - task_id: T-12
    pr_id: PR-07
    pr_branch: codex/kb-retrieval-p2-pr-07
    pr_depends_on: [PR-05, PR-06]
    pr_subject: "S5 灰度可观测与运行闸门"
    acceptance_cmds:
      - python3 scripts/docs_guard.py --strict
    rollback_point: 回退文档与索引更新
```

---

## 8. planning_contract（供 `$jjk-vkplan` 消费）

```yaml
planning_contract:
  execution_mode: serial
  strict_single_active_card: true
  auto_done_policy:
    implementation-card: hard_gate
    inspection-card: policy_gate
    question-card: policy_gate
  card_order: [C01, C02, C03, C04, C05, C06, C07, G01]
  gate_contract:
    mode: as_cards
    gate_ids: [G01]
    depends_on:
      G01: [C07]
  cards:
    - card_id: C01
      wave: S0
      feature_ids: [P5-01]
      depends_on: []
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - 离线样本集与评测脚本可运行
      acceptance_checks:
        - venv/bin/python scripts/data/kb_offline_evaluation.py --dry-run
      evidence_entry: workdocs/归档/正文/实施计划/知识库检索P2分阶段治理_implementation_plan.md

    - card_id: C02
      wave: S1
      feature_ids: [P1-01, P1-02]
      depends_on: [C01]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - 参数契约修正完成且回归通过
      acceptance_checks:
        - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k "payload or timeout"
      evidence_entry: workdocs/归档/正文/实施计划/知识库检索P2分阶段治理_implementation_plan.md

    - card_id: C03
      wave: S2
      feature_ids: [P2-01, P2-02]
      depends_on: [C02]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - 候选去重与文档限额生效
      acceptance_checks:
        - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k "dedup or evidence"
      evidence_entry: workdocs/归档/正文/实施计划/知识库检索P2分阶段治理_implementation_plan.md

    - card_id: C04
      wave: S2
      feature_ids: [P2-03]
      depends_on: [C03]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - 编排层压缩协同回归通过
      acceptance_checks:
        - venv/bin/python -m pytest -q tests/unit/test_multi_agent_streaming_helpers.py -k tool_message
      evidence_entry: workdocs/归档/正文/实施计划/知识库检索P2分阶段治理_implementation_plan.md

    - card_id: C05
      wave: S3
      feature_ids: [P3-01, P3-02]
      depends_on: [C04]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - 改写与多路融合可开关控制
      acceptance_checks:
        - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k "rewrite or rerank"
      evidence_entry: workdocs/归档/正文/实施计划/知识库检索P2分阶段治理_implementation_plan.md

    - card_id: C06
      wave: S4
      feature_ids: [P4-01]
      depends_on: [C05]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - 领域路由过滤稳定
      acceptance_checks:
        - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k metadata
      evidence_entry: workdocs/归档/正文/实施计划/知识库检索P2分阶段治理_implementation_plan.md

    - card_id: C07
      wave: S5
      feature_ids: [P5-02]
      depends_on: [C06]
      task_mode: implementation-card
      merge_required: true
      done_gate:
        - 灰度监控与回滚手册就绪
      acceptance_checks:
        - python3 scripts/docs_guard.py --strict
      evidence_entry: workdocs/归档/正文/实施计划/知识库检索P2分阶段治理_implementation_plan.md

    - card_id: G01
      wave: Gate
      feature_ids: [G-1]
      depends_on: [C07]
      task_mode: inspection-card
      merge_required: false
      done_gate:
        - 人工相关性@5 >= 80%
        - 错误引用率 <= 5%
      acceptance_checks:
        - venv/bin/python scripts/data/kb_offline_evaluation.py --stage gate
        - python3 scripts/docs_guard.py --strict
      evidence_entry: workdocs/归档/正文/实施计划/知识库检索P2分阶段治理_implementation_plan.md

  task_to_pr_mapping:
    - task_id: T-01
      pr_id: PR-01
      pr_branch: codex/kb-retrieval-p2-pr-01
      pr_depends_on: []
      pr_subject: "S1 参数契约化与稳健性改造"
      acceptance_cmds:
        - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k "payload or timeout"
      rollback_point: 关闭新参数配置并回退 payload
    - task_id: T-02
      pr_id: PR-01
      pr_branch: codex/kb-retrieval-p2-pr-01
      pr_depends_on: []
      pr_subject: "S1 参数契约化与稳健性改造"
      acceptance_cmds:
        - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k timeout
      rollback_point: 回退异常降级分支
    - task_id: T-03
      pr_id: PR-02
      pr_branch: codex/kb-retrieval-p2-pr-02
      pr_depends_on: [PR-01]
      pr_subject: "S2 候选去重与文档限额"
      acceptance_cmds:
        - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k dedup
      rollback_point: 关闭去重限额开关
    - task_id: T-04
      pr_id: PR-02
      pr_branch: codex/kb-retrieval-p2-pr-02
      pr_depends_on: [PR-01]
      pr_subject: "S2 候选去重与文档限额"
      acceptance_cmds:
        - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k evidence
      rollback_point: 回退旧结果拼接
    - task_id: T-05
      pr_id: PR-03
      pr_branch: codex/kb-retrieval-p2-pr-03
      pr_depends_on: [PR-02]
      pr_subject: "S2 编排层预算协同"
      acceptance_cmds:
        - venv/bin/python -m pytest -q tests/unit/test_multi_agent_streaming_helpers.py -k tool_message
      rollback_point: 回退工具消息压缩策略
    - task_id: T-06
      pr_id: PR-04
      pr_branch: codex/kb-retrieval-p2-pr-04
      pr_depends_on: [PR-03]
      pr_subject: "S3 查询改写与多路召回融合"
      acceptance_cmds:
        - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k rewrite
      rollback_point: 关闭改写开关
    - task_id: T-07
      pr_id: PR-04
      pr_branch: codex/kb-retrieval-p2-pr-04
      pr_depends_on: [PR-03]
      pr_subject: "S3 查询改写与多路召回融合"
      acceptance_cmds:
        - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k rerank
      rollback_point: 回退单路排序
    - task_id: T-08
      pr_id: PR-05
      pr_branch: codex/kb-retrieval-p2-pr-05
      pr_depends_on: [PR-04]
      pr_subject: "S4 领域路由与过滤"
      acceptance_cmds:
        - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k metadata
      rollback_point: 关闭路由过滤
    - task_id: T-09
      pr_id: PR-06
      pr_branch: codex/kb-retrieval-p2-pr-06
      pr_depends_on: []
      pr_subject: "S0 离线评测框架与样本基线"
      acceptance_cmds:
        - venv/bin/python scripts/data/kb_offline_evaluation.py --dry-run
      rollback_point: 暂停自动评测门禁
    - task_id: T-10
      pr_id: PR-06
      pr_branch: codex/kb-retrieval-p2-pr-06
      pr_depends_on: []
      pr_subject: "S0 离线评测框架与样本基线"
      acceptance_cmds:
        - venv/bin/python -m pytest -q tests/unit/test_kb_offline_evaluation.py
      rollback_point: 移除 CI 强依赖
    - task_id: T-11
      pr_id: PR-07
      pr_branch: codex/kb-retrieval-p2-pr-07
      pr_depends_on: [PR-05, PR-06]
      pr_subject: "S5 灰度可观测与运行闸门"
      acceptance_cmds:
        - venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k retrieval_log
      rollback_point: 回退日志字段扩展
    - task_id: T-12
      pr_id: PR-07
      pr_branch: codex/kb-retrieval-p2-pr-07
      pr_depends_on: [PR-05, PR-06]
      pr_subject: "S5 灰度可观测与运行闸门"
      acceptance_cmds:
        - python3 scripts/docs_guard.py --strict
      rollback_point: 回退文档与索引更新
```

---


### 8.1 C04 / T-05 实施证据（2026-03-03）

| card_id | task_id | pr_id | 代码改动 | 关键诊断字段 | 验证命令 | 结果 | 回滚锚点 |
|---|---|---|---|---|---|---|---|
| C04 | T-05 | PR-03 | `app/ai/workflow/multi_agent_graph.py` 增加 ToolMessage 压缩诊断写回；`tests/unit/test_multi_agent_streaming_helpers.py` 增加 `truncation_flag` 回归 | `truncation_flag`、`tool_message_count`、`tool_message_chars_before`、`tool_message_chars_after` | `venv/bin/python -m pytest -q tests/unit/test_multi_agent_streaming_helpers.py -k tool_message`（实际执行：`/Users/jijingkun/bojxAI/fastapi/venv/bin/python -m pytest -q tests/unit/test_multi_agent_streaming_helpers.py -k tool_message`） | PASS（5 passed） | 回退 SUPERVISOR_TOOL_MESSAGE 配置与压缩逻辑 |


### 8.2 C07 / T-11,T-12 实施证据（2026-03-04）

| card_id | task_id | pr_id | 代码改动 | 关键诊断字段 | 验证命令 | 结果 | 回滚锚点 |
|---|---|---|---|---|---|---|---|
| C07 | T-11 | PR-07 | `app/ai/tools/ragflow_tool.py` 新增 `_build_retrieval_log` 与灰度字段（`rollout.stage/traffic_percent/rollback_target_stage`）；`app/ai/workflow/multi_agent_graph.py` 在 `_prepare_messages_for_supervisor_inference` 与 `delivery_meta` 增加检索链路诊断字段 | `route_ids`、`selected_document_ids`、`retrieval_tool_message_count`、`retrieval_truncated_tool_message_count`、`ragflow_rollout_stage`、`ragflow_rollout_traffic_percent` | `venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k retrieval_log`（工作树无 `venv`，实际执行：`/Users/jijingkun/bojxAI/fastapi/venv/bin/python -m pytest -q tests/unit/test_ragflow_tool.py -k retrieval_log`） | PASS（2 passed） | 回退日志字段扩展并关闭灰度策略开关 |
| C07 | T-12 | PR-07 | `docs/API文档/外部服务集成.md` 补齐 RAG 参数章节与检索观测字段；`docs/开发文档/快速入门/生产部署手册.md` 增加 S5 灰度放量与回滚 Runbook；`docs/SUMMARY.md` 同步迭代索引入口 | `RAGFLOW_ROLLOUT_STAGE`、`RAGFLOW_ROLLOUT_TRAFFIC_PERCENT`、`RAGFLOW_ENABLE_ROLLBACK_SWITCH` | `python3 scripts/docs_guard.py --strict` | PASS（errors=0, warnings=0） | 回退文档索引变更 |


## 9. implementation_readiness（机读结论）

```yaml
implementation_readiness:
  implementation_ready: true
  blocked_by: []
  next_step: $jjk-vkplan
  execution_intent_required: true
```

说明：

1. 计划已达到工单级 HOW，可进入拆卡阶段。
2. 因本轮为 `plan-only`，不自动进入实施链路。
3. 需用户显式发出下一步指令（推荐：`$jjk-vkplan`）。
