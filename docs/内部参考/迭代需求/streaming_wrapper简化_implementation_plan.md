# streaming_wrapper 分发架构简化 — 实施方案

> 日期: 2026-02-25
> 需求基线: `streaming_wrapper简化_requirements.md`
> 涉及文件: `app/ai/workflow/multi_agent_graph.py`（主），`tests/unit/test_multi_agent_streaming_helpers.py`（测试）

---

## 1. 架构影响与约束

### 模块边界

所有改动限定在 `multi_agent_graph.py` 的 streaming_wrapper 分发层。不涉及：
- Workflow 层（`data_graph.py`, `chat_graph.py`）
- Service 层（`chat_service.py`）
- 事件协议层（`app/ai/events.py`）
- 前端

### 状态契约

`StreamingContext` dataclass 仅封装已有的局部变量，不引入新的状态字段。所有字段的生命周期与当前完全一致（在 `_execute_streaming_wrapper` 中创建，在 dispatch loop 结束后丢弃）。

### 可测试性

现有 3 个单元测试覆盖 streaming_wrapper 的核心路径。重构后需更新测试中的 mock 方式（从 adapter dict 改为直接 patch 模块函数）。

---

## 2. 功能机制包总表

### F-01: 引入 `StreamingContext` dataclass，消灭参数爆炸

- **feature_id**: F-01
- **目标**: 将 8 个在调用链中原封不动透传的参数封装为一个上下文对象
- **不做**: 不改变任何运行时行为，不新增状态字段
- **触发条件**: 重构启动
- **代码锚点**:
  - 定义位置: `app/ai/workflow/multi_agent_graph.py` — 在 `StreamingProtocolAdapter` 原位置（line 77）新增 `StreamingContext`
  - 消费方: `_dispatch_messages_mode_chunk` (line 1281), `_dispatch_values_mode_chunk` (line 1355), `_dispatch_custom_mode_chunk` (line 1337), `_run_streaming_dispatch_loop` (line 1456), 以及所有 `_emit_*` / `_handle_*` 辅助函数
- **关键数据结构**:
  ```python
  @dataclass
  class StreamingContext:
      writer: Any
      node_name: str
      state: Dict[str, Any]
      collected_content: list[str]
      kb_images: Dict[str, str]
      emitted_message_ids: set
      sent_tool_call_ids: set
  ```
- **回滚锚点**: git revert 单次 commit
- **验证命令**: `.venv/bin/python -m pytest tests/unit/test_multi_agent_streaming_helpers.py -v`
- **来源证据**: 团队评审 — 架构师和简化专家一致认为参数爆炸是"看起来乱"的最大来源

### F-02: 移除 `StreamingProtocolAdapter`，直接调用 `AgentOutputParser`

- **feature_id**: F-02
- **目标**: 删除 `StreamingProtocolAdapter` TypedDict 和 `_build_streaming_protocol_adapter` 函数，所有调用点改为直接调用 `AgentOutputParser` 的静态方法
- **不做**: 不改变解析逻辑本身
- **触发条件**: F-01 完成后
- **代码锚点**:
  - 删除: `StreamingProtocolAdapter` (line 77-84), `_build_streaming_protocol_adapter` (line 98-106)
  - 修改: `_dispatch_values_mode_chunk` 中 `protocol_adapter["extract_all_handoffs_from_messages"]` → `AgentOutputParser.extract_all_handoffs_from_messages`
  - 修改: `_emit_kb_images_from_delta_messages` 中 `protocol_adapter["parse_kb_images"]` → `AgentOutputParser.parse_kb_images`
  - 修改: `_execute_streaming_wrapper` (line 1571) 中删除 adapter 构建调用
- **回滚锚点**: git revert
- **验证命令**: `.venv/bin/python -m pytest tests/unit/test_multi_agent_streaming_helpers.py -v`
- **来源证据**: `_build_streaming_protocol_adapter` 只在 line 1586 调用一次，永远传入 `AgentOutputParser`，无多态需求

### F-03: 移除 `StreamingEventEmitterAdapter`，直接调用 `events.py` 函数

- **feature_id**: F-03
- **目标**: 删除 `StreamingEventEmitterAdapter` TypedDict 和 `_build_streaming_event_emitter_adapter` 函数，所有调用点改为直接调用 `app/ai/events.py` 中的 `emit_token`, `emit_result` 等函数
- **不做**: 不改变事件格式
- **触发条件**: F-01 完成后（可与 F-02 并行）
- **代码锚点**:
  - 删除: `StreamingEventEmitterAdapter` (line 86-96), `_build_streaming_event_emitter_adapter` (line 109-144)
  - 修改: 所有 `event_emitter_adapter["emit_token"](writer, ...)` → `emit_token(writer, ...)`
  - 修改: 所有 `event_emitter_adapter["emit_result"](writer, payload, node=...)` → `emit_result(writer, data_type=..., data=..., message=..., node=...)`（注意 payload 解包）
  - 修改: `_create_streaming_agent_wrapper` (line 1675) 中删除 adapter 构建调用
- **回滚锚点**: git revert
- **验证命令**: `.venv/bin/python -m pytest tests/unit/test_multi_agent_streaming_helpers.py -v`
- **来源证据**: `_build_streaming_event_emitter_adapter` 只在 line 1679 调用一次，无多态需求

### F-04: 删除 `_handle_messages_mode_tool_call_chunks_noop` 死代码

- **feature_id**: F-04
- **目标**: 删除这个 noop 函数及其调用点
- **不做**: 无
- **触发条件**: 独立，可最先执行
- **代码锚点**:
  - 删除: `_handle_messages_mode_tool_call_chunks_noop` (line 1263-1278)
  - 修改: `_dispatch_messages_mode_chunk` (line 1327) 中删除调用
- **回滚锚点**: git revert
- **验证命令**: `.venv/bin/python -m pytest tests/unit/test_multi_agent_streaming_helpers.py -v`
- **来源证据**: 函数名含 `noop`，内部遍历 tool_call_chunks 后 `pass`，重构残留

---

## 3. 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 移除适配器后 mock 方式变化导致测试失败 | 测试需更新 | 测试中改用 `monkeypatch.setattr` patch 模块级函数 |
| `emit_result` payload 解包格式不匹配 | result 事件丢失 | F-03 中逐个检查 `_emit_result_with_schema` 的 payload 解包逻辑，确保直接调用时参数对齐 |
| `StreamingContext` 引入后遗漏某个消费方 | 运行时 AttributeError | grep 所有 `protocol_adapter` / `event_emitter_adapter` / `writer` / `node_name` 引用，确保全部迁移 |

---

## 4. 验证计划

### 单元测试

- 现有 3 个测试覆盖核心路径（TC-SW-01、TC-SW-02、TC-SW-03）
- 显式 TC 覆盖补齐：`TC-SW-01`、`TC-SW-02`、`TC-SW-03`、`TC-SW-04`。
- 新增 TC-SW-04: 验证移除适配器后直接调用的正确性

### 手动验证

1. 启动后端，发送问数查询（如"查询2025年6月30日贷款余额前10名"）
2. 验证实时对话中 SQL 结果表格正常展示
3. 验证 token 流式输出正常
4. 验证 thinking 事件正常（如启用深度思考）

---

## 5. 实施建议

| 优先级 | Feature | 工作量 | 依赖 |
|--------|---------|--------|------|
| 1（最先） | F-04: 删除 noop 死代码 | 极小 | 无 |
| 2 | F-01: 引入 StreamingContext | 中 | 无 |
| 3 | F-02: 移除 ProtocolAdapter | 低 | F-01 |
| 3 | F-03: 移除 EventEmitterAdapter | 低 | F-01 |

建议按 F-04 → F-01 → F-02+F-03 顺序执行，每步独立 commit，便于回滚。

---

## 6. 预期效果

| 指标 | 当前 | 目标 |
|------|------|------|
| streaming 相关函数/类 | 27 | ≤ 15 |
| 最大函数参数数 | 14 | ≤ 5 |
| 净减少代码行数 | — | ≥ 80 |

---

## 7. 架构影响与约束（补充）

### 路由闭环

不涉及意图路由，纯内部重构。

### 端到端链路

SSE 事件格式不变，`chat_service.py` 消费逻辑不变，前端无需改动。

---

## 8. 文档关联

- 需求基线: `docs/内部参考/迭代需求/streaming_wrapper简化_requirements.md`
- 架构文档: `docs/开发文档/架构设计/AI模块设计.md`（streaming_wrapper 章节）
- 前序修复计划: `docs/内部参考/迭代需求/fix_plan_data_query_display_20260225.md`

---

## 9. 机读契约

```yaml
planning_contract:
  execution_mode: serial
  card_order: [C01, C02, C03, C04]
  strict_single_active_card: true
  auto_done_policy:
    implementation-card: hard_gate
  cards:
    - card_id: C01
      title: "删除 noop 死代码"
      feature_ids: [F-04]
      depends_on: []
      done_gate:
        - _handle_messages_mode_tool_call_chunks_noop 函数及调用已删除
        - tests green
    - card_id: C02
      title: "引入 StreamingContext dataclass"
      feature_ids: [F-01]
      depends_on: [C01]
      done_gate:
        - StreamingContext 定义存在
        - _run_streaming_dispatch_loop 参数数 <= 5
        - tests green
    - card_id: C03
      title: "移除 StreamingProtocolAdapter"
      feature_ids: [F-02]
      depends_on: [C02]
      done_gate:
        - StreamingProtocolAdapter 和 _build_streaming_protocol_adapter 已删除
        - 所有调用点改为直接调用 AgentOutputParser
        - tests green
    - card_id: C04
      title: "移除 StreamingEventEmitterAdapter"
      feature_ids: [F-03]
      depends_on: [C02]
      done_gate:
        - StreamingEventEmitterAdapter 和 _build_streaming_event_emitter_adapter 已删除
        - 所有调用点改为直接调用 events.py 函数
        - tests green
```
