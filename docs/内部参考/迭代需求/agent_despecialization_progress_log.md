# Agent 去特殊化收敛进展日志

> 文档状态：持续回填  
> 首次创建：2026-02-18  
> 来源主计划：`docs/内部参考/迭代需求/agent_despecialization_implementation_plan.md`

---

## 1. 维护规则

1. 本文档仅记录批次进展与验证结果，不重复主计划中的稳定策略。
2. 每次 `/imp` 完成后，追加“结构收敛里程碑 + 测试验证 + 当前状态”。
3. 若结论影响风险、回滚或验收标准，需同步回填主计划。

---

## 2. 持续收敛进展（2026-02-18，Batch-8 ~ Batch-20）

### 2.1 结构收敛里程碑

1. **Batch-8（协议依赖收敛）**
   - 新增 `StreamingProtocolAdapter`，将 `parse_kb_images / should_filter_content / extract_latest_handoff_from_messages` 从 `streaming_wrapper` 直连改为适配注入。

2. **Batch-9（事件出口收敛）**
   - 新增 `StreamingEventEmitterAdapter`，统一注入 `emit_token / emit_thinking / emit_tool_start / emit_tool_end / emit_status`。
   - `messages/values` dispatcher 与异常兜底从散落函数参数改为单一适配器契约。

3. **Batch-10（结果/图片事件收敛）**
   - 将 `emit_result / emit_kb_images` 纳入 `StreamingEventEmitterAdapter`，`values` 分支不再直连事件函数。

4. **Batch-11（事件载荷 schema 收敛）**
   - 新增 `StreamingToolStartPayload / StreamingResultPayload / StreamingKbImagesPayload`。
   - 新增 payload builder（tool/result/kb_images），统一“先构造标准载荷，再发射事件”。

5. **Batch-12（协议共享化落点）**
   - `StreamingToolStartPayload/StreamingResultPayload/StreamingKbImagesPayload` 与 payload builder 已上提到 `app/ai/protocol.py`，并由 `multi_agent_graph` 直接复用，避免 workflow 内重复定义。

6. **Batch-13（跨图共享协议接线）**
   - `data_graph.sql_execute` 的 `emit_result` 改为先走 `build_streaming_result_payload_from_fields` 再发射，统一结构化结果载荷入口。
   - `todo_graph.execute_operation` 的 `additional_kwargs` 构造改为复用 `build_streaming_result_payload_from_fields`，对齐多图结构化返回契约。

7. **Batch-14（工具层共享协议接线）**
   - `chatTools.fig_inter` 的图片流式 `emit_result` 改为先复用 `build_streaming_result_payload_from_fields` 统一构造 `image` 载荷，再发射事件。
   - 新增工具层 helper（`_emit_fig_image_result_event`）承接协议构造与事件发送，减少 workflow 外路径的字段拼装分支。

8. **Batch-15（问数回放载荷收敛）**
   - `data_graph.sql_execute` 的 `create_ai_message.additional_kwargs` 改为通过 `_build_sql_result_additional_kwargs` 构建，并在 helper 内复用 `build_streaming_result_payload_from_fields`。
   - 同步新增回归测试，确保 `sql_result` 的 `data_type/data` 与 `total_rows/sql_source/iterations/permission_scope` 等字段稳定。

9. **Batch-16（待办确认回放载荷收敛）**
   - `todo_graph.ask_confirmation` 的 `create_ai_message.additional_kwargs` 改为通过 `build_operation_additional_kwargs_payload` 构建，统一 `operation` 载荷归一化。
   - `todo_graph` 中恢复取消草稿链路对 `operation` 的读取改为 `extract_operation_from_ai_message`，减少 `additional_kwargs.get("operation")` 散落分支。
   - 清理未使用的 `confirmation_data`/`display_args` 影子构造逻辑，保留实际生效链路。

10. **Batch-17（待办确认 operation builder 收敛）**
   - `todo_graph.ask_confirmation` 的 `operation_data` 构建改为 `_build_todo_operation_payload` 统一承接。
   - `target_task` 与 `diff` 的分支拼装分别下沉为 `_build_todo_operation_target_task` 与 `_build_todo_operation_diff`，减少确认节点分支复杂度。
   - 新增 helper 单测覆盖 `update/delete` 场景，固定 `target_task/diff` 结构契约。

11. **Batch-18（回放载荷 schema 入口统一）**
   - `app/ai/protocol.py` 新增 `build_result_additional_kwargs_payload` / `build_operation_additional_kwargs_payload` / `extract_operation_from_ai_message`，统一 additional_kwargs 归一化与读取入口。
   - `data_graph` 与 `todo_graph` 改为复用协议层入口，减少工作流内部重复 schema 校验逻辑。
   - 新增协议层与工作流联动测试，覆盖 result/operation 的构建与提取回归。

12. **Batch-19（问数降级策略表驱动）**
   - `data_graph.sql_execute` 的空结果降级分支改为 `_SQL_EMPTY_RESULT_FALLBACK_POLICY` 表驱动。
   - `route_after_execute` 的 fallback 路由改为 `_EXECUTE_FALLBACK_ROUTE_MAP`，集中管理 `training/schema` 目标映射。
   - 补充降级策略解析与路由回归测试，确保行为与现有链路一致。

13. **收口评估（Batch-19 完成后）**
   - 新增专题评估报告：`docs/内部参考/迭代需求/agent_despecialization_evaluation_report.md`。
   - 结论：专题进入维护态，后续按增量规则回填。

14. **Batch-20（不必要特殊处理清理）**
   - 删除 `data_graph._build_sql_result_additional_kwargs` 与 `todo_graph._build_todo_result_additional_kwargs` 中不可达/弱约束 fallback 拼装分支，改为协议层校验失败时返回空载荷。
   - 删除 `todo_graph` 末尾 `_get_user_id_from_state` 的兼容重绑定别名，避免同名函数语义被后置覆盖。
   - 目标：从“结构收敛”进一步进入“冗余特殊分支删除”。

### 2.2 测试与验证

1. 已新增并维护 `tests/unit/test_multi_agent_streaming_helpers.py`：
   - 覆盖协议适配、事件适配、payload builder、messages/values dispatcher、异常兜底、wrapper 工厂。
2. 持续回归命令（每批次执行）：
   - `./venv/bin/python -m py_compile app/ai/workflow/multi_agent_graph.py tests/unit/test_multi_agent_streaming_helpers.py`
   - `./venv/bin/python -m pytest tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_multi_agent_context_budget.py tests/unit/test_multi_agent_fallback.py tests/unit/test_llm_scene_enforcement.py -q`
   - `./venv/bin/python scripts/docs_guard.py --strict`

### 2.3 当前状态与下一步

1. 当前状态：`streaming_wrapper` 与跨图回放载荷已收敛到协议层统一入口，`todo_graph` 确认载荷完成 builder 化，`data_graph` 降级路由完成表驱动化。
2. 收口建议：
   - 本专题“去特殊化收敛”可进入维护态；后续仅按新增需求增量回填。
   - 若继续演进，优先做前后端共享事件 schema（统一类型定义与校验）。
