# 问数助手查询结果展示问题修复计划

> 日期: 2026-02-25
> 触发场景: 用户查询"查询2025年6月30日贷款余额前10名的客户"

---

## 1. 问题摘要

| 项目 | 内容 |
|------|------|
| 问题描述 | 问数助手查询结果存在三个问题：实时对话不展示数据表格、文案矛盾、权限配置缺失 |
| 严重程度 | P0（实时表格不展示）+ P1（权限缺失）+ P2（文案 Bug） |

### 问题清单

| # | 问题 | 严重度 | 类型 |
|---|------|--------|------|
| 1 | 实时对话时 SQL 结果表格不展示，刷新页面后历史消息能看到 | P0 | 流式事件丢失 |
| 2 | 金融市场部 staff 不应有权查询贷款明细表 | P1 | 权限配置缺失 |
| 3 | "共返回 10 条记录（已展示前 100 条）"文案矛盾 | P2 | 硬编码 Bug |

---

## 2. 根因分析

### 问题 1：实时对话 SQL 结果表格不展示（P0）

**根因链**：

1. `data_graph` 的 `sql_execute` 节点通过 `get_stream_writer()` 发送 `result` 事件（`emit_result`）
2. `data_graph` 作为子图被 `multi_agent_graph.py` 的 `streaming_wrapper` 调用
3. `streaming_wrapper` 内部用 `agent.astream(stream_mode=["messages", "values"])` 消费子图（line 1458-1461）
4. **子图的 `get_stream_writer()` 写入的 custom event 不会冒泡到 `streaming_wrapper` 的 `["messages", "values"]` 流中**
5. 同时 `_should_mute_expert_text_output` 对 `data_expert` 返回 `True`（line 784），messages 模式的 token 也被静默
6. 结果：`chat_service.py` 的 `full_answer` 为空，触发"补充发送非流式响应"逻辑（line 638-650），只发了纯文本 `token` 事件
7. 前端只收到文本，没有收到 `sql_result` 结构化数据，无法渲染 `SqlResultTable`

**证据**：日志 `补充发送非流式响应: 查询完成，共返回 10 条记录（已展示前 100 条）。` 证明 `result` 事件未到达 `chat_service.py`。

**刷新后能看到的原因**：`_postprocess` 保存的 AIMessage 带有完整的 `additional_kwargs`（含 `sql_result` 数据），历史消息从数据库加载时前端能正确渲染。

### 问题 2：贷款表权限缺失（P1）

**根因**：`t_data_permission_table` 中 `staff` 角色对 `fdmdata.*` 配置了 `allow_access=true`（通配），没有针对贷款表的单独限制。行级过滤只加了 `dept_cd = user.dept_code`，允许查询但限制了数据范围。

**现状**：金融市场部 staff（dept_code=00808）查贷款表时，SQL 被重写为 `WHERE dept_cd = '00808'`，只能看到本部门管户的贷款数据。但业务上金融市场部不应有权查看贷款明细。

### 问题 3：文案硬编码（P2）

**根因**：`data_graph.py:3999-4000`

```python
elif row_count <= 5:
    return f"查询完成，共返回 {row_count} 条记录。"
else:
    return f"查询完成，共返回 {row_count} 条记录（已展示前 100 条）。"
```

`row_count > 5` 时硬编码"已展示前 100 条"，不管实际行数。

---

## 3. 修复方案

### 3.1 问题 1 修复：streaming_wrapper 转发子图 custom events

**核心思路**：在 `streaming_wrapper` 的 `_run_streaming_dispatch_loop` 中加入 `"custom"` 模式，将子图的 custom events 通过顶层 writer 转发。

#### 涉及文件

#### [app/ai/workflow/multi_agent_graph.py](file:///Users/jijingkun/bojxAI/fastapi/app/ai/workflow/multi_agent_graph.py)
- [x] 修改点 1: `_run_streaming_dispatch_loop` 的 `agent.astream` 调用，`stream_mode` 从 `["messages", "values"]` 改为 `["messages", "values", "custom"]`（line 1461）
- [x] 修改点 2: 新增 `_dispatch_custom_mode_chunk` 专用分发函数（line 1337），与 messages/values 的 dispatcher 对称，含结构验证和 debug 日志
- [x] 修改点 3: dispatch loop 中 `mode == "custom"` 分支调用 `_dispatch_custom_mode_chunk`（line 1495）

#### [tests/unit/test_multi_agent_streaming_helpers.py](file:///Users/jijingkun/bojxAI/fastapi/tests/unit/test_multi_agent_streaming_helpers.py)
- [x] 修改点 4: 3 处 `stream_mode` 断言从 `["messages", "values"]` 更新为 `["messages", "values", "custom"]`

#### [app/services/chat_service.py](file:///Users/jijingkun/bojxAI/fastapi/app/services/chat_service.py)
- [x] 修改点 3: 确认"补充发送非流式响应"逻辑（line 638）在 `result` 事件正常到达后不再触发（`full_answer` 不为空时自动跳过，无需额外修改）

### 3.2 问题 2 修复：贷款表权限配置

**核心思路**：在 `t_data_permission_table` 中为 `staff` 角色添加贷款表的 `allow_access=false` 规则，使精确规则覆盖通配规则。

#### 涉及文件/操作

- [ ] 数据库变更: 在 `t_data_permission_table` 插入 `staff` 角色对 `fdmdata.f_mid_loan_k_tb` 的 `allow_access=false` 记录
- [ ] 确认: 需要与业务方确认哪些角色可以查贷款表（如 `analyst`、`head_president` 等）
- [ ] 确认: 是否还有其他贷款相关表需要限制（如 `f_mid_loan_tb` 等）

**注意**：此修改需要业务方确认具体的权限矩阵，不能仅凭技术判断。

### 3.3 问题 3 修复：文案动态化

#### [app/ai/workflow/data_graph.py](file:///Users/jijingkun/bojxAI/fastapi/app/ai/workflow/data_graph.py)
- [x] 修改点: line 4000，将硬编码 100 改为动态计算

```python
# 修改前
return f"查询完成，共返回 {row_count} 条记录（已展示前 100 条）。"

# 修改后
display_limit = min(row_count, 100)
if row_count > display_limit:
    return f"查询完成，共返回 {row_count} 条记录（已展示前 {display_limit} 条）。"
else:
    return f"查询完成，共返回 {row_count} 条记录。"
```

---

## 4. 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| streaming_wrapper 加入 custom 模式后可能收到非预期的 chunk | 其他子图的 custom events 也会被转发 | 转发时检查 chunk 结构，只转发合法的 event dict |
| 贷款表权限变更影响已有用户 | 之前能查的用户突然不能查 | 提前通知业务方，灰度发布 |
| `_should_mute_expert_text_output` 静默了 data_expert 的 token | result 事件转发后，文本仍被静默，但 result 事件的 message 字段会被 chat_service 收集到 full_answer | 确认 result 事件到达后"补充发送"逻辑不再触发 |

---

## 5. 验证计划

### 手动验证

1. 实时对话输入"查询2025年6月30日贷款余额前10名的客户"
   - 预期：实时看到 SQL 结果表格（不需要刷新）
   - 预期：文案显示"共返回 10 条记录"（不带"已展示前 100 条"）
2. 用 staff 角色查询贷款表
   - 预期：返回权限拒绝提示（配置权限后）
3. 查询返回超过 100 条的场景
   - 预期：文案显示"共返回 N 条记录（已展示前 100 条）"

### 单元测试

- [x] `test_interpret_result_display_limit`: 验证 `_interpret_result` 在不同行数下的文案
- [x] `test_run_streaming_dispatch_loop_filters_invalid_custom_chunks`: 验证 custom events 能通过 streaming_wrapper 转发

---

## 6. 实施建议

| 优先级 | 修复项 | 预计工作量 |
|--------|--------|-----------|
| 1 (最高) | 问题 1: streaming_wrapper 转发 custom events | 小（改 2 处） |
| 2 | 问题 3: 文案动态化 | 极小（改 1 行） |
| 3 | 问题 2: 贷款表权限配置 | 需业务确认后执行 |

建议问题 1 和问题 3 一起修复，问题 2 等业务方确认权限矩阵后再执行。

---

## 7. 文档关联

- [x] 需求文档: `docs/产品文档/问数助手需求.md`
- [x] 测试案例: `docs/开发文档/测试管理/问数引擎测试案例.md`
- [x] 架构文档: `docs/开发文档/架构设计/AI模块设计.md`（streaming 架构）
