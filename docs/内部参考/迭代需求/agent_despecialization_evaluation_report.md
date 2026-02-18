# 评估报告（Agent 去特殊化收敛）

> 评估日期：2026-02-18  
> 评估范围：Batch-8 ~ Batch-19（含收口批次）  
> 对应基线：`docs/内部参考/迭代需求/agent_despecialization_requirements.md`  
> 对应方案：`docs/内部参考/迭代需求/agent_despecialization_implementation_plan.md`  
> 对应进展：`docs/内部参考/迭代需求/agent_despecialization_progress_log.md`

---

## 1. 评估结论（摘要）

1. 本专题“去特殊化收敛”主目标已达成，建议进入**维护态**。
2. `agent` 关键链路已从“工作流内散落拼装”收敛到“协议层统一入口 + 工作流 builder”。
3. 剩余“特殊处理”主要集中在问数域业务复杂度（`data_graph`），而非 Agent 协议/事件散落。

---

## 2. 达成项核对

### 2.1 协议层统一入口

已上提并统一到 `app/ai/protocol.py`：

- `build_streaming_*_payload`（事件层）
- `build_result_additional_kwargs_payload`（结果回放）
- `build_operation_additional_kwargs_payload`（确认回放）
- `extract_operation_from_ai_message`（确认回放读取）

### 2.2 工作流接线完成度

1. `multi_agent_graph`：事件发射、协议解析、schema 适配已完成。
2. `data_graph`：
   - 流式 `result` 载荷统一；
   - 回放 `additional_kwargs` 已切协议层入口；
   - 空结果降级策略已表驱动（`metric → training → schema`）。
3. `todo_graph`：
   - 执行结果与确认回放载荷均切协议层入口；
   - `operation_data`（`target_task/diff`）已 builder 化；
   - 取消后恢复链路读取逻辑统一。
4. `chatTools`：`fig_inter` 图片结果事件已切共享载荷入口。

---

## 3. 量化检查

### 3.1 结构化回放手工拼装点

- `app/ai/workflow` 与 `app/ai/tools` 下 `additional_kwargs={...}` 手工拼装点：**0 处**（本轮扫描）。

### 3.2 协议入口使用情况

- `build_result_additional_kwargs_payload`：`data_graph`、`todo_graph` 已接线。
- `build_operation_additional_kwargs_payload`：`todo_graph` 已接线。
- `extract_operation_from_ai_message`：`todo_graph` 已接线。

### 3.3 剩余高复杂度热点（关键词密度扫描）

> 该项用于“观察复杂业务分支”，不等于必须继续重构。

1. `app/ai/workflow/data_graph.py`
2. `app/ai/workflow/todo_graph.py`
3. `app/ai/workflow/multi_agent_graph.py`

---

## 4. 风险与边界

1. `data_graph` 的“降级/重写/权限”分支仍多，属于问数业务复杂性，不建议为“去特殊化”而过度抽象。
2. 现阶段继续大规模重构收益递减，且会提高问数回归成本。
3. 后续新增能力应优先走协议层入口，避免回归到 workflow 内散落拼装。

---

## 5. 建议后续策略（维护态）

1. 增量规则：新增结构化回放字段时，先改 `app/ai/protocol.py` 再接线。
2. 门禁规则：保留 `tests/unit/test_multi_agent_streaming_helpers.py` 作为协议层回归主闸。
3. 文档规则：每次协议层改动同步回填：
   - `docs/开发文档/架构设计/AI模块设计.md`
   - `docs/开发文档/架构设计/防屎山记录手册.md`
   - `docs/内部参考/迭代需求/agent_despecialization_progress_log.md`

---

## 6. 验证记录

本轮收口验证命令（已执行通过）：

1. `./venv/bin/python -m py_compile app/ai/protocol.py app/ai/workflow/data_graph.py app/ai/workflow/todo_graph.py tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_data_graph_semantic_guard.py tests/unit/test_todo_nodes.py`
2. `./venv/bin/python -m pytest tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_data_graph_semantic_guard.py tests/unit/test_todo_nodes.py tests/unit/test_chat_tools_streaming_payload.py tests/unit/test_multi_agent_context_budget.py tests/unit/test_multi_agent_fallback.py tests/unit/test_llm_scene_enforcement.py -q`
3. `./venv/bin/python scripts/docs_guard.py --strict`

---

## 7. 最终结论

`Agent 去特殊化收敛`专题达到“可收口”标准：

- 协议入口统一；
- 工作流散落拼装已清；
- 回归与文档门禁通过；
- 后续按维护态增量治理即可。

