# SSE 流式协议规范（Composite Result Contract v1）

> **结论先行**：
> 1. 结构化结果只走 `event: result` 单通道；
> 2. 结构化结果输入 canonical 字段冻结为 `additional_kwargs.result_events[]`；最终展示 canonical 字段为 `message.content(blocks)`；
> 3. 可靠性最小集冻结为 `id + retry + heartbeat + Last-Event-ID`；
> 4. 文档过渡策略冻结为 `OpenAPI 3.1 + AsyncAPI 3.0`，并预留 `text/event-stream + itemSchema(oneOf)` 迁移位。

---

## 1. 协议总览

### 1.1 基础帧格式

```text
event: <event_type>
id: <event_id>            # 可选，可靠性场景必填
retry: <milliseconds>     # 可选，建议默认 5000
data: <json_payload>

```

### 1.2 事件职责矩阵

| 事件 | 职责 | 是否承载结构化业务数据 |
|---|---|---|
| `token` | 增量文本 | 否 |
| `status` | 阶段状态 | 否 |
| `result` | 结构化结果输入（卡片/表格/图片/图表） | **是（结构化输入唯一通道）** |
| `final_answer` | 最终正文 | 否 |
| `display_blocks` | 最终展示块快照（live canonical blocks） | **是（最终展示唯一快照）** |
| `interrupt` | 人审中断 | 否 |
| `done` | 生命周期收口（`thread_id/message_id/final_content?`） | 否 |
| `error` | 错误收口 | 否 |

> 前端渲染约束：`result` / `additional_kwargs.result_events[]` 仍是结构化结果输入 owner；live 展示统一消费 `display_blocks`，历史回放统一消费 `message.content(blocks)`。禁止再次回退到“正文字符串 + result_events + kb_images 共同决定 UI”的模式。

---

## 2. 契约源与过渡文档策略

### 2.1 单一契约源

| 层级 | 文件 | 角色 |
|---|---|---|
| 后端契约源 | `app/contracts/result_event_contract.py` | `ResultEventUnion` / `result_event_union` 定义 |
| Schema 产物 | `contracts/streaming/result-event.schema.json` | 跨端冻结产物 |
| 前端类型 | `web/src/types/generated/result-event.ts` | TS 生成类型 |
| 前端校验 | `web/src/lib/validators/result-event.ts` | 运行时 validator |

### 2.2 `asyncapi_transitional_contract`

- 当前生效：
  - REST：`docs/api/openapi.yaml`（OpenAPI 3.1）
  - SSE：`docs/api/streaming-events.asyncapi.yaml`（AsyncAPI 3.0）
- 目标态：迁移到 OAS 3.2 时，使用 `text/event-stream` 的 `itemSchema(oneOf)`。

---

## 3. `result_event_union`（结构化结果冻结）

`result` 事件数据面采用 `result_event_union`，已知类型 + 通用兜底：

| data_type | 语义 | 典型 data |
|---|---|---|
| `todo_list` | 待办卡片 | `{todos:[...]}` |
| `sql_result` | 表格查询结果 | `{columns:[...], rows:[...]}` |
| `image` | 图片结果 | `{url:"..."}` |
| `table` | 结构化表格 | `{headers:[...], rows:[...]}` |
| `chart` | 图表结果 | `{series:[...], options:{...}}` |
| `text` | 结构化文本 | `{text:"..."}` |
| `*`(unknown) | 未来扩展类型 | fallback 可见展示 |

> 兼容规则：未知 `data_type` 不可吞掉，前端必须 fallback 可见并打 warning。

---

## 4. SSE 可靠性最小集

### 4.1 `last_event_id_resume` 约定

- 客户端断线重连时，若保存了最近消费成功的 `event.id`，应通过 `Last-Event-ID` 头回传。
- 服务端可据此执行：
  1. 从下一个 `sequence_number` 继续；或
  2. 退化整轮重放（必须满足前端去重，不可重复渲染）。

### 4.2 去重与顺序

| 规则 | 说明 |
|---|---|
| 去重主键 | 优先 `event_id`，其次 `envelope.id` |
| 排序键 | `sequence_number`（或 `envelope.sequence_number`） |
| 顺序一致性 | 实时展示顺序 = 刷新回放顺序 = resume 补发顺序 |

### 4.3 heartbeat

- 长连接应发送注释心跳（如 `: heartbeat`）维持连接活性。
- 心跳默认间隔建议：`<= 15s`。

---

## 5. 回放 canonical：`read-old-write-new`

### 5.1 字段优先级（读取）

1. `additional_kwargs.result_events[]`（结构化输入 canonical）
2. `additional_kwargs.result_event`（过渡单值）
3. `additional_kwargs.data_type + additional_kwargs.data`（legacy）
4. `metadata` 历史兼容字段（只读兜底）

### 5.2 写回规则（新）

- 新写路径必须包含 `additional_kwargs.result_events[]`，且最终展示消息优先写 `content_type=multimodal` + `content=[blocks...]`。
- 兼容观察字段：`compat_source`（`result_events|result_event|data_type_data`）。
- 多结果场景必须按 `sequence_number` 保序。

---

## 6. `payload_budget_rules`（载荷预算）

| 场景 | 规则 | 风险控制 |
|---|---|---|
| 图片/图表 | SSE 仅传 URL/资产引用，不传 base64 二进制 | 防止长连接被大包拖垮 |
| 大表格 | 默认传预览行 + 导出链接/资产引用 | 控制 payload bytes |
| fallback 摘要 | 仅允许脱敏白名单字段 | 防止敏感字段外泄 |

---

## 7. `text_event_stream_itemSchema` 迁移位

为对齐 OAS 3.2 目标态，本文档冻结以下命名（当前由 AsyncAPI 表达，OpenAPI 侧保留迁移位）：

- `text_event_stream_itemSchema`：SSE 单帧事件 `oneOf` 模型名称。
- `result_event_union`：`result.data` 使用的联合类型名称。
- `display_blocks`：SSE live 最终展示快照事件名，`data.blocks` 为 canonical ordered content blocks。

---

## 8. 示例

### 8.1 result 事件

```text
event: result
id: evt_0009
retry: 5000
data: {"event":"result","data_type":"todo_list","data":{"todos":[{"id":1,"title":"提交周报"}]},"message":"找到 1 条待办","envelope":{"id":"evt_0009","source":"chat_service","specversion":"1.0","type":"result","sequence_number":9,"timestamp":"2026-03-08T07:20:00Z","thread_id":"th_1","run_id":"run_1"},"result_contract_version":"1.0.0"}

```

### 8.2 done 事件

```text
event: done
data: {"thread_id":"th_1","message_id":12345,"final_content":"已完成"}

```

---

## 9. 实施与验证入口

- 协议实现：`app/services/chat_service.py`、`app/ai/events.py`、`web/src/lib/backend.ts`、`web/src/hooks/useSSEStream.ts`
- 回放归一：`app/repositories/chat_repo.py`、`web/src/lib/message-normalizer.ts`
- 门禁入口：`scripts/contract/check_result_contract.sh`、`.github/workflows/contract-gate.yml`
