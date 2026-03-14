# AI 模块设计：待办协作契约
> 更新时间：2026-03-13

> **用途**: 聚焦 Todo Graph、待办协作节点、确认闭环与跨图交互约束。
> **入口说明**: 当前文档为 AI 架构权威源的专题正文；总览与阅读路径见 [AI模块设计](AI模块设计.md)。

## 文档导航
- 总览入口：[AI模块设计.md](AI模块设计.md)
- 多智能体与状态契约：[AI模块设计_多智能体与状态契约.md](AI模块设计_多智能体与状态契约.md)
- 待办协作契约：[AI模块设计_待办协作契约.md](AI模块设计_待办协作契约.md)
- 工具、事件与流式协议：[AI模块设计_工具事件与流式协议.md](AI模块设计_工具事件与流式协议.md)
- 问数语义层与结果增强：[AI模块设计_问数语义层与结果增强.md](AI模块设计_问数语义层与结果增强.md)
- 跨 Agent 意图与运行时契约：[AI模块设计_跨Agent意图与运行时契约.md](AI模块设计_跨Agent意图与运行时契约.md)

---

## 📋 Todo Graph 架构

> **详细设计文档**: [待办Agent设计](./待办Agent设计.md)

**文件**: `app/ai/workflow/todo_graph.py`

Todo Graph 在当前口径下是一个独立的 `todo_workflow` StateGraph，采用**意图驱动 + contract-first** 架构，支持多轮确认、冲突检测与 handoff contract 消费。

### 核心节点

| 节点 | 职责 |
|-----|------|
| `analyze_intent` | LLM 分析用户意图，提取待办信息；接收 `config` 参数，当前端传入 `current_todo_id` 时注入选中待办上下文辅助意图判断；对超出待办能力范围的输入返回能力边界提示 |
| `clarify` | 信息不完整时生成追问 |
| `resolve` | 模糊标识 → 具体 todo_id |
| `confirm` + `wait_confirm` | 确认流程 (使用 `interrupt()`) |
| `execute` | 执行 CRUD 操作 |

### 节点流程图

```
analyze → route_next → [clarify|conflict|resolve|execute]
                          │
                    route_after_resolve
                          │
                [clarify|confirm|execute]
                          │
                    wait_confirm → execute → END
```

### 节点函数 -> 事件契约（2026-02 严格切换）

#### Todo Graph（含增强节点与解析节点）

| 节点函数 | 应发事件（目标） | 说明 |
|-----|----------------|------|
| `analyze_intent` | 无（状态内决策） | 超范围输入只设置状态，不发送结构化事件 |
| `clarify_node` | `clarification` | 使用 `emit_clarification` 主动引导用户补充信息 |
| `conflict_detection_node` | 无（文本消息） | 冲突提示通过 AI 文本消息表达 |
| `resolve_entity` | 无（状态更新） | 仅做实体解析与路由状态变更 |
| `ask_confirmation` | 不发 `confirmation` | 沿用 `additional_kwargs.operation + interrupt` 的 HITL 流程 |
| `wait_for_confirmation` | `interrupt`（LangGraph 内建） | 通过 `interrupt()` 暂停并等待用户决策 |
| `execute_operation` | `result`（由 Supervisor 包装器统一发） | 节点返回 `AIMessage.additional_kwargs(data_type,data)`，由上层转为 `result` |

#### Data Graph

| 节点函数 | 应发事件（目标） | 说明 |
|-----|----------------|------|
| `analyze_data_intent` | 无 | 意图分析，非 UI 事件节点 |
| `metric_resolve` | 无 | 模板匹配，不直接发事件；若用户请求 TopN/排名/维度而模板仅支持总量聚合，自动降级到下一层 |
| `training_sql_resolve` | 无 | 检索训练 SQL；若命中 SQL 不满足 TopN/维度语义，跳过该候选并回退通用 RAG |
| `schema_retrieve` | 无 | 检索 schema |
| `sql_generate` | 无 | 生成 SQL |
| `sql_safety_check` | 无 | 安全校验 |
| `sql_execute` | `status` / `result` / `error` | 查询执行阶段负责结构化输出和状态反馈，`sql_result.data` 可选携带 `chart` 规格（前端图+表并存） |
| `clarify_node` | 无（文本消息） | 保持轻量，不扩展事件协议面 |

#### Supervisor（多智能体主图）

| 节点函数 | 应发事件（目标） | 说明 |
|-----|----------------|------|
| `_preprocess_multimodal` | `status` | 护栏、技能加载、图片分析状态；图片完成后发送 `phase=generating` |
| `streaming_wrapper` | `token` / `thinking` / `tool_start` / `tool_end` / `result` / `kb_images` | 核心统一事件出口 |
| `_evaluate_expert_work` | `status` | 协调继续执行时的提示 |
| `_postprocess` | 无 | 仅负责持久化与清理 |
| `ChatService done` | `done`（仅生命周期） | 严禁携带结构化数据 |

- 2026-03-10 起，知识库检索这类“独立预构建 Agent 入口”统一使用 `langchain.agents.create_agent`；Supervisor 由于仍依赖运行时工具可见性裁剪与自定义 `ToolNode`，继续保留 `create_react_agent`。
- `knowledge_search` / `search_tool` / `read_uploaded_file` / `analyze_image` 继续保留 atomic tool；只有统一 `research_subagent` 这类“单次研究任务入口”才视为 stateless research subagent，由它在内部编排 knowledge/web source provider，结果合同固定为 `summary + evidence + insufficiency`，并允许附带 `media_refs`。
- 本轮只收口可独立迁移的预构建 Agent API，不改 `create_todo_graph` / `create_data_graph` 等 Graph factory，也不重写当前多智能体主图的 runtime gating 结构。
- `interrupt / resume / replay` 与 `agent.astream(..., stream_mode=["messages", "values", "custom"])` 相关契约保持不变，迁移层只改安全边界内的 Agent 构建入口，不改运行时状态归属。

#### Supervisor 上下文预算治理（2026-02）

- `streaming_wrapper` 在进入 `trim_messages` 前，先对超长 `ToolMessage` 做推理态压缩（仅压缩送模内容，原始消息仍保留在 checkpoint / 对话表）。
- 消息裁剪从“按条数”升级为“按 token 预算”：使用 `count_tokens_approximately` 估算消息 token，避免单条超长工具输出挤占整轮上下文。
- 预算公式：`max(MESSAGE_MAX_TOKENS * 0.85, 1024)`；在高噪声场景（如知识库返回长文）可稳定保留最近用户意图与路由指令。
- 目标：降低“上一轮工具长文本污染下一轮路由”的概率，确保问数/待办委派判断更多依据当前轮输入。

#### Supervisor 模型异常降级策略（2026-02）

- 当 `supervisor` 在 `streaming_wrapper` 中遇到模型配额/订阅/权限类错误（如 `403`、`SUBSCRIPTION_NOT_FOUND`、`Insufficient Balance`）时，不再向用户透传 `[System Error: ...]`。
- 若最新用户输入命中待办语义（如“查询我的待办列表”），系统会构造 `pending_handoff` 并降级路由到 `todo_expert` 继续执行，优先保障待办链路可用性。
- 若不满足待办降级条件，则返回稳定的用户友好提示（如“模型服务当前不可用……”），避免暴露底层异常细节。

#### 去特殊化收敛（2026-02-18）

- 移除 `create_multi_agent_graph` 中未接线的 `_classify_intent` 与 `route_by_intent` 影子分支，避免“定义存在但不参与图执行”的路径误导。
- `supervisor_should_continue` 的可路由目标改为由统一常量映射驱动（`AgentType -> workflow node`），不再散落字符串字面量判断。
- `get_scene_llm` 契约收敛为仅接受 `scene_key`，旧 `scene` 参数兼容入口已下线，调用点全部对齐场景键。
- `streaming_wrapper` 的 `values` 分支已按子职责抽取 helper 并接线：`handoff` 增量返回构建、`kb_images` 提取、`tool_start` 发射、文本补发去重判定、文本/结果发送，减少大段内联分支。
- `streaming_wrapper` 的 `messages` 分支完成第一阶段拆分：消息 ID 预填充、`ToolMessage` 处理（`tool_end`/`kb_images`）、token 发送与 thinking 发送拆至独立 helper，降低单分支圈复杂度。
- `streaming_wrapper` 的上下文准备与收尾返回完成抽取：消息裁剪+上下文注入整合为 `_prepare_streaming_inference_state`，结束态增量返回整合为 `_build_streaming_delta_return`，降低主函数流程长度。
- `streaming_wrapper` 的双模式事件循环完成 dispatcher 抽取：`messages`、`values`、`custom` 三种 stream mode 分别收敛到 `_dispatch_messages_mode_chunk` / `_dispatch_values_mode_chunk` / `_dispatch_custom_mode_chunk`，主循环仅保留分发与状态衔接。`custom` 分支（2026-02-25）透传子图通过 `get_stream_writer()` 发送的结构化事件（如 `data_graph` 的 `emit_result`），使实时对话能展示 SQL 结果表格。custom 事件在子图内已完成格式化，中间层直接透传。
- `streaming_wrapper` 的运行编排与异常兜底完成抽取：`_run_streaming_dispatch_loop` 统一承接流循环编排，`_handle_streaming_wrapper_exception` 统一承接 supervisor 降级与用户友好报错。
- `streaming_wrapper` 工厂上提为模块级：`_create_streaming_agent_wrapper` 与 `_execute_streaming_wrapper` 从 `create_multi_agent_graph` 闭包中拆出，支持后续以可注入 orchestrator 方式复用。
- `streaming_wrapper` 协议解析与事件发射简化（2026-02-26）：移除 `StreamingProtocolAdapter` / `StreamingEventEmitterAdapter` 两层适配器及其构建函数，所有调用点改为直接调用 `AgentOutputParser` 静态方法和 `app/ai/events.py` 的 `emit_*` 函数。引入 `StreamingContext` dataclass 封装 7 个共享参数（`writer/node_name/state/collected_content/kb_images/emitted_message_ids/sent_tool_call_ids`），消除参数爆炸（最大参数数从 14 降至 6）。同时删除 `_handle_messages_mode_tool_call_chunks_noop` 死代码。`StreamingToolStartPayload/StreamingResultPayload/StreamingKbImagesPayload` 与 builder 仍保留在 `app/ai/protocol.py` 作为共享协议定义。
- 共享载荷协议已向其他工作流扩展：`data_graph.sql_execute` 的 `emit_result` 与 `todo_graph.execute_operation` 的 `additional_kwargs` 均复用 `build_streaming_result_payload_from_fields`，减少跨图的结构化结果字段拼装差异。
- 共享载荷协议已向工具层扩展：`chatTools.fig_inter` 的图片流式结果事件改为复用 `build_streaming_result_payload_from_fields` 构造 `image` 载荷，消除工具层手工拼装 `emit_result` 字段分支。
- 共享载荷协议进一步收敛到问数消息回放路径：`data_graph.sql_execute` 的 `create_ai_message.additional_kwargs` 改为复用 `_build_sql_result_additional_kwargs`（内部调用 `build_streaming_result_payload_from_fields`），减少同节点“流式事件载荷 vs 历史消息载荷”的双份字段定义。
- 共享载荷协议继续收敛到待办确认回放路径：`todo_graph.ask_confirmation` 的 `create_ai_message.additional_kwargs` 改为复用 `build_operation_additional_kwargs_payload`，并将 `operation` 提取逻辑统一为 `extract_operation_from_ai_message`，减少“写入/读取 operation 载荷”双份散落分支。
- 待办确认载荷构造进一步收敛：`todo_graph.ask_confirmation` 的 `operation_data`（`target_task/diff`）改为由 `_build_todo_operation_payload` 及子 helper 统一构建，清理分支内联字段拼装并降低确认节点圈复杂度。
- 回放载荷 schema 校验入口已统一到 `app/ai/protocol.py`：`build_result_additional_kwargs_payload` / `build_operation_additional_kwargs_payload` / `extract_operation_from_ai_message`，`data_graph` 与 `todo_graph` 共用同一归一化规则。
- 问数空结果降级策略从分支内联改为表驱动：`_SQL_EMPTY_RESULT_FALLBACK_POLICY` 与 `_EXECUTE_FALLBACK_ROUTE_MAP` 统一管理 `metric→training→schema` 路由与提示文案，减少硬编码判断分支。
- 不必要 fallback 已清理：`data_graph._build_sql_result_additional_kwargs` 与 `todo_graph._build_todo_result_additional_kwargs` 中不可达/弱约束回退分支已删除，改为协议层校验失败时返回空载荷，避免“静默拼装半结构数据”。
- 不必要兼容覆盖已清理：删除 `todo_graph` 末尾对 `_get_user_id_from_state` 的“向后兼容别名重绑定”，避免同名函数被后置覆盖导致语义漂移。
- 本批次拆分遵循“只重构结构不改语义”：Pre/Post 节点行为与事件协议不变，仍保持现有运行链路兼容。
- 本批次不改变 Pre/Post 节点行为，仅做结构收敛，保证线上语义稳定。

### 智能特性

| 特性 | 说明 |
|-----|------|
| 渐进式策略 | 多轮对话后自动给默认值 |
| 快速模式 | 检测关键词跳过确认 |
| 实体解析 | 模糊匹配用户指定的待办 |
| 指代消歧 | 用户仅输入"项目汇报那个"等无动作指代表达时，优先结合上下文自动判定；简单场景一次确认，复杂场景多轮消歧 |
| 取消后补充恢复 | 创建确认阶段若用户先拒绝，随后以补充轮继续输入细节（`SUPPLEMENT`/`CORRECTION`），在无目标待办 ID 且历史会话帧 `todo_action=create` 时系统优先恢复 `create` 并重新进入确认；恢复判定不依赖 handoff 文案中的“更新/创建”措辞，避免误入 `update` 的目标 ID 追问 |
| 提取字段归一化 | 统一将 `target_ref/target_title/new_due_date/new_priority/new_category/new_description` 映射为执行链路可消费的 canonical 字段 |
| 选中待办上下文 | 前端选中待办后，`analyze_intent` 从 DB 加载该待办完整信息注入 prompt，辅助 LLM 将用户消息关联到具体待办（支持 update/complete/delete），并自动注入 `todo_id` |
| 能力边界兜底 | 当输入明显属于天气/新闻/问数/知识库/绘图等非待办请求时，不触发待办查询并返回引导文案；但若已存在待办锚点（`current_todo_id` 或 handoff `todo_id/todo_action=update`）且用户表达“补充外部信息”，则按待办 `update` 处理 |

#### 指代消歧与自适应确认规则

- **无动作指代默认策略**：当输入只包含目标（如"项目汇报那个"）但未出现明确动作词时，系统先尝试匹配目标待办；唯一命中默认按 `update` 进入确认流程（用户可改口为完成/删除）。
- **多候选场景**：若命中多个待办，`resolve_entity` 返回候选列表，支持用户使用"第 X 个"、"ID 为 XX"或直接补充标题片段继续消歧。
- **不可判定场景**：若无法命中目标，进入澄清分支并要求补充动作或更完整标题，避免重复固定追问文案。

#### 提取字段归一化（Canonicalization）

`analyze_intent` 在路由前执行字段归一化，确保 `pending_operation.data` 稳定使用以下字段：

- `title`
- `due_date`
- `priority`
- `category`
- `description`

同时保留原始别名字段用于兼容历史日志与排障。

### 工具调用架构 (ADR-001)

**决策**: 不采用 LangGraph `ToolNode`，使用自定义 `execute_operation` 节点

| 维度 | ToolNode 模式 | 当前实现 |
|------|---------------|----------|
| 工具调用触发 | LLM 生成 `tool_calls` | `analyze_intent` 构造 `pending_operation` |
| 用户确认 | 无内置支持 | `ask_confirmation` + `wait_for_confirmation` |
| 结果格式 | 标准 `ToolMessage(content)` | 自定义 `ToolResult(data_type, data, message)` |

**选择理由**: 需要在工具执行前插入确认、冲突检测、参数补全等业务逻辑。

> 更多详情（状态定义、路由逻辑、配置管理、提示词策略等）请参阅 [待办Agent设计](./待办Agent设计.md)

---
