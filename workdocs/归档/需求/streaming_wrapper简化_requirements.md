# streaming_wrapper 分发架构简化 — 需求基线

> 日期: 2026-02-25
> 触发: 团队评审认定 streaming_wrapper 分发架构存在过度工程化

---

## 1. 背景

`multi_agent_graph.py` 中 streaming_wrapper 的分发架构在 2026-02-18 "去特殊化收敛"重构中引入了两层适配器（`StreamingProtocolAdapter` / `StreamingEventEmitterAdapter`）和大量只调用一次的辅助函数。团队评审结论：

- 两层适配器用字典模拟 Strategy Pattern，但全文件只有一个实现，无多态需求
- 最大函数参数数达 14 个，8 个参数在调用链中原封不动透传
- 存在 1 个死代码函数（`_handle_messages_mode_tool_call_chunks_noop`）
- streaming 相关定义共 27 个，其中 22 个只被调用一次

## 2. 用户故事

作为维护 AI 模块的开发者，我希望 streaming_wrapper 的分发代码结构清晰、参数精简，以便在新增子图或修改流式行为时能快速理解和安全修改。

## 3. 验收标准

### 功能性

| AC | 描述 |
|----|------|
| AC-01 | 移除两层适配器后，所有现有流式事件（token, thinking, tool_start, tool_end, status, result, kb_images, custom）仍正常到达前端 |
| AC-02 | 引入 `StreamingContext` dataclass 后，`_run_streaming_dispatch_loop` 参数数 ≤ 5 |
| AC-03 | 删除 `_handle_messages_mode_tool_call_chunks_noop` 后，无功能回归 |
| AC-04 | 所有现有单元测试（`test_multi_agent_streaming_helpers.py`）通过 |

### 异常/边界

| AC | 描述 |
|----|------|
| AC-05 | 子图发送非标准 custom chunk 时，仍被正确过滤（不崩溃） |
| AC-06 | `_should_mute_expert_text_output` 行为不变（data_expert 文本仍被静默） |

### 非功能

| AC | 描述 |
|----|------|
| AC-07 | streaming 相关函数/类定义数从 27 降至 ≤ 15 |
| AC-08 | 最大函数参数数从 14 降至 ≤ 5 |
| AC-09 | 净减少代码行数 ≥ 80 行 |

## 4. 非功能需求

- **性能**: 纯重构场景下，streaming 分发附加耗时增量 P95 ≤ 5ms。
- **安全**: 不涉及权限或数据变更，权限相关回归失败数必须为 0。
- **数据一致性**: 不涉及数据库，SSE 事件类型与关键字段兼容回归失败数必须为 0。

## 5. 关联测试

| TC 编号 | 描述 |
|---------|------|
| TC-SW-01 | `test_streaming_dispatch_loop_emits_messages_and_values` — 验证 messages/values/custom 三路分发 |
| TC-SW-02 | `test_execute_streaming_wrapper_returns_delta_messages` — 验证增量消息返回 |
| TC-SW-03 | `test_create_streaming_agent_wrapper_uses_module_stream_writer` — 验证 wrapper 工厂 |
| TC-SW-04 | 新增：验证移除适配器后直接调用 `AgentOutputParser` 和 `events.py` 函数的正确性 |

## 6. 约束

- 纯内部重构，不改变任何外部行为（SSE 事件格式、chat_service 消费逻辑）
- 不修改 `_should_mute_expert_text_output` 的行为（mute 粒度问题作为独立 issue 跟踪）
- 不修改 `data_graph.py`、`chat_service.py` 等其他文件

---

## 7. 文档关联

- 架构文档: `docs/开发文档/架构设计/AI模块设计.md`（streaming_wrapper 章节）
- 前序修复计划: `workdocs/归档/修复计划/fix_plan_data_query_display_20260225.md`
