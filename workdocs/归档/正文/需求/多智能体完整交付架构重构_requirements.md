# 多智能体完整交付架构重构 — 需求基线

> 日期：2026-02-27
> 模式：`/jjk-plan core`
> 主题：多智能体完整交付架构重构
> 触发问题：复合问题（如“帮我查待办，再看嘉兴天气”）无法稳定做到“按用户问题顺序、完整覆盖、无内部术语泄露”的最终答复。

---

## 0. 现状深度分析（代码证据）

### 0.1 现象归纳

当前系统在复合请求上已经具备“多智能体串行执行”能力，但仍存在以下核心缺口：

1. 输出是“执行轨迹拼接”，不是“问题覆盖交付”。
2. 没有“必答项覆盖率”门禁，流程可在信息不完整时结束。
3. 内部状态字段与调度描述会渗透到用户可见文本。
4. `todo_list` 结构化结果在复合汇总场景中被降级为短摘要，损失可操作细节。

### 0.2 后端证据（FastAPI + LangGraph）

| 代码锚点 | 现状行为 | 直接影响 |
|---|---|---|
| `app/ai/workflow/multi_agent_graph.py::_build_direct_lookup_findings` | 直接从 ToolMessage 抽取天气/知识检索摘要，按文本去重 | 同类实时信息容易重复或噪声长文本进入最终答复 |
| `app/ai/workflow/multi_agent_graph.py::_build_multi_intent_summary_content` | 最终答复按“direct finding + 执行轨迹”拼接 | 用户问题顺序无法保证，且会带入内部调度话术 |
| `app/ai/workflow/multi_agent_graph.py::_extract_latest_visible_ai_excerpt` | 专家结果只保留最近可见 AI 文本片段 | 丢失结构化结果细节（例如待办列表明细） |
| `app/ai/workflow/multi_agent_graph.py::_should_mute_expert_text_output` | `multi_intent_mode` 下静默 todo/data 专家直出文本 | 用户看不到专家原始有用信息，依赖汇总质量 |
| `app/ai/workflow/todo_graph.py::_execute_query` | 实际产出 `data_type=todo_list` + `todos` 结构化数据 | 结构化数据可用，但在复合汇总时未被完整消费 |
| `app/services/chat_service.py::_slice_current_turn_messages` | done 补发场景按轮次切片；但多智能体汇总未使用同等“当前轮范围”语义 | 跨轮历史污染风险仍在汇总链路存在 |

### 0.3 前端证据（Next.js + SSE 消费）

| 代码锚点 | 现状行为 | 直接影响 |
|---|---|---|
| `web/src/hooks/useSSEStream.ts::storeStructuredResultToMessage` | result 事件会把 `data_type/data` 写入当前 AI 消息 `additional_kwargs` | 卡片能力具备，但要求后端持续提供结构化结果 |
| `web/src/components/chat/messages/ai.tsx` | 当 `data_type=todo_list` 且有 `todos` 时渲染 TodoListCard | 若后端最终只返回摘要文本，前端无法展示完整待办卡片 |
| `web/src/lib/backend.ts::dispatchSSEEvent` | 事件按 type 分发，但缺“最终交付摘要事件”的专门语义 | UI 难以区分“过程事件”与“最终答案” |

### 0.4 测试证据

| 测试锚点 | 已覆盖 | 缺口 |
|---|---|---|
| `tests/unit/test_multi_intent_queue_flow.py` | 覆盖 handoff 队列消费与 summarize 进入条件 | 未验证“最终答复是否完整覆盖用户问题槽位” |
| `tests/unit/test_multi_agent_streaming_helpers.py` | 覆盖 handoff_batch + direct lookup 进入 multi_intent_mode | 未验证“最终输出顺序/去重/禁止内部术语泄露” |
| `tests/unit/test_chat_service_done_payload.py` | 覆盖 done/result 事件字段冻结 | 未验证“复合任务最终答案与结构化结果一致性” |

---

## 1. 用户故事

### US-01（业务用户）
作为业务用户，我在一个请求中同时提出多个目标（如待办 + 天气），希望系统一次性按我的表达顺序完整回答，不需要我二次追问“还有一个问题没回答”。

### US-02（运营/客服）
作为运营同学，我希望最终答复不出现内部术语（如 `todo_expert`、`handoff`、`assign_to_*`），避免用户困惑并降低投诉成本。

### US-03（研发）
作为研发，我希望多智能体系统的“执行层”和“交付层”解耦：内部可以多 worker 并行/串行，但对外只有单一稳定答复出口，且可通过覆盖率门禁自动判定是否答全。

### US-04（质量保障）
作为 QA，我希望每一轮都有可机读的“问题合同 -> 交付物 -> 覆盖率报告”链路，支持自动化回归与线上问题回放。

---

## 2. 目标与范围

### 2.1 目标

1. 建立“交付导向”架构：从“路由完成”升级为“问题完整覆盖后再回答”。
2. 建立统一交付合同：`intent_plan`、`deliverables`、`coverage_report`、`final_answer`。
3. 建立唯一对外出口：最终只由 Composer 输出用户可见答案。
4. 建立覆盖率门禁：`must_answer` 未满足时禁止直接结束。

### 2.2 范围内

1. `multi_agent_graph` 的架构重构（拆分 Planner/Executor/Coverage/Composer）。
2. SSE 协议扩展（过程事件与最终交付事件分层）。
3. 前端消息渲染分层（过程可视化 vs 最终答复）。
4. chat_db 增量持久化（交付物与覆盖率留痕）。

### 2.3 范围外

1. 不改变数据分析 SQL 能力核心逻辑（`data_graph` 算法本身保持）。
2. 不改变待办业务规则（创建/查询/更新/完成/删除语义保持）。
3. 不在本次重构中引入新的第三业务域专家（仅重构编排与交付层）。

---

## 3. 验收标准

### 3.1 功能性（Happy Path）

| AC 编号 | 验收标准 |
|---|---|
| AC-FULL-001 | 对复合请求（至少 2 个目标）生成有序且原子化的 `intent_plan`；天气、知识库、画图、待办等独立诉求不得再合并成同一个粗粒度 goal |
| AC-FULL-002 | 每个 goal 执行完成后必须产出绑定 `goal_id` 的结构化 `deliverable`，禁止用 bucket 级汇总结果代替多个独立 goal 的交付 |
| AC-FULL-003 | `coverage_report.pass=true` 前不得发送最终 `done` 完成态；`coverage_report` 只允许按 `goal_id` 判定，不得按 `kind bucket` 猜测覆盖 |
| AC-FULL-004 | 最终用户可见答复严格按 `intent_plan.order` 输出，不受内部执行顺序影响；图表型 goal 的正文与结构化 `result(image)` 必须一致 |
| AC-FULL-005 | 最终答复中不得出现内部调度词（`handoff`、`*_expert`、`assign_to_*`）；不得出现“已全部覆盖”但实际仍有原子 goal 缺失的误报 |
| AC-FULL-006 | `todo.query` 场景最终答复可回溯到 `todos` 结构化数据（含数量与条目摘要）；`todo.query` handoff 默认不得混入天气/知识库等外部观察摘要，只有 handoff 任务描述明确要求“结合外部结果回复/汇总”时，才允许以结构化 `tool_observations` 附带必要观察 |
| AC-FULL-007 | `weather.current` 场景最终答复包含城市、日期、天气、温度范围与数据时间戳；若同轮还包含知识库检索，不得因天气富文本存在而吞掉知识库结果 |
| AC-FULL-008 | `knowledge.lookup` 与 `chart.render` 必须作为独立 goal 进入最终答复，不能只停留在过程事件或前端附加卡片中 |

### 3.2 异常/边界

| AC 编号 | 验收标准 |
|---|---|
| AC-EDGE-001 | 单个原子 goal 失败时，`coverage_report.pass=false`，系统进入恢复规划或输出“部分完成”并显式列出缺项 |
| AC-EDGE-002 | 同类工具结果重复输入时，最终答复只保留一条去重结果，但不得误伤其他 goal 的独立结果 |
| AC-EDGE-003 | 跨轮会话下，当前轮交付计算不得误用历史轮次 deliverables，也不得把上一轮 result 卡片误算为本轮 goal 已完成 |
| AC-EDGE-004 | 用户取消 run 后，不得继续发出新的最终答案事件 |
| AC-EDGE-005 | `current_todo_id` 缺失时，待办补充类请求须走澄清，不得误改任务；`todo.query` 默认不得因外部问题混入而退化为 out_of_scope 拒答，但在明确“结合外部结果回复”的查询场景下仍应保留必要 observation |

### 3.3 性能/稳定性

| AC 编号 | 验收标准 |
|---|---|
| AC-PERF-001 | 对“双目标复合请求”，P95 端到端延迟较现网基线增幅 ≤ 20% |
| AC-PERF-002 | 覆盖率校验节点（Coverage Gate）单次执行耗时 P95 ≤ 300ms |
| AC-STAB-001 | 关键路径异常可回滚到旧汇总模式（feature flag），服务不中断 |
| AC-STAB-002 | 每轮交付日志具备可回放最小证据链（plan/task/deliverable/coverage） |

---

## 4. 非功能需求

### 4.1 性能

1. 编排层新增节点不得引入指数级重试。
2. 同一 `goal_id` 的任务在同轮最多执行一次（幂等键约束）。

### 4.2 安全

1. 用户可见文本禁止泄露内部任务参数与路由决策字段。
2. 保持 `user_id` 维度的数据隔离，不跨用户读取待办或交付历史。

### 4.3 数据一致性

1. `intent_plan`、`deliverables`、`coverage_report` 必须属于同一 `thread_id + run_id + turn_id`。
2. 若最终答复生成失败，前序结构化交付可保留但须标记为未完成轮次。

### 4.4 双数据库约束（@dual-database）

1. 本次重构新增持久化仅允许落在 `chat_db`（`DATABASE_URL`）。
2. `data_db`（`ANALYTICS_DATABASE_URL`）仍保持只读分析角色，不新增写入表。
3. `fdmdata.*` / `sdmdata.*` 查询路径保持由 data_expert 与 `analytics_engine` 负责。

---

## 5. OpenClaw 对标约束

对标来源：`/Users/jijingkun/bojxAI/bot/openclaw/docs/pi.md`。

1. 对齐点：工具管线、策略过滤、流式事件与会话守护应保持“统一入口 + 可治理”。
2. 差异点（需在实现方案中先声明再处理）：
   - OpenClaw 以单会话 Agent Loop 为主；本项目已是 Supervisor + 专家子图模式。
   - 本项目必须额外实现“问题覆盖门禁”，而不仅是工具执行安全。
3. 结论：保留多 worker 执行边界，但用户视角强制单一答复人格。

---

## 6. 关联测试（预留 TC 编号）

### 6.1 单元测试

| TC 编号 | 目标 |
|---|---|
| TC-FULL-UT-001 | Planner 能把“天气 + 画图 + 知识库 + 待办”拆为 4 个有序原子 goal |
| TC-FULL-UT-002 | Direct tool 与 expert 结果都能归一化为绑定 `goal_id` 的 `deliverable envelope` |
| TC-FULL-UT-003 | Coverage Gate 能识别 missing/failed goals，且不再因粗粒度 bucket 误判全覆盖 |
| TC-FULL-UT-004 | Composer 输出顺序严格遵循 `goal.order` |
| TC-FULL-UT-005 | Composer 输出不含内部术语 |

### 6.2 集成测试

| TC 编号 | 目标 |
|---|---|
| TC-FULL-IT-001 | “查待办 + 看天气”一次完成且完整覆盖 |
| TC-FULL-IT-002 | “看天气 + 查待办”顺序反转场景仍按用户表达输出 |
| TC-FULL-IT-003 | 单目标失败时输出部分完成并标缺项 |
| TC-FULL-IT-004 | 跨轮消息下当前轮覆盖率不受历史污染 |

### 6.3 端到端/协议测试

| TC 编号 | 目标 |
|---|---|
| TC-FULL-E2E-001 | SSE 新事件（plan/task/coverage/final）与旧事件兼容 |
| TC-FULL-E2E-002 | 前端只将 `final_answer` 作为最终正文呈现，过程事件不污染正文 |
| TC-FULL-E2E-003 | 取消 run 后无 final_answer 漏发 |

---

## 7. 约束与风险前置

1. 本次为全局重构，必须分阶段发布与灰度开关，禁止一次性硬切。
2. `multi_agent_graph.py` 当前体量较大，需先模块化拆分再演进功能。
3. 与既有 `result` 卡片协议兼容是高风险点，必须保留旧字段并增量扩展。
4. 若覆盖率门禁策略过严，可能造成“可回答但被拦截”；需提供可观测调参项。

---

## 8. 文档关联

1. 架构：`docs/开发文档/架构设计/AI模块设计.md`
2. API：`docs/API文档/接口文档.md`
3. 现有基线：
   - `workdocs/归档/正文/实施计划/openclaw迁移重建基线_implementation_plan.md`
   - `workdocs/归档/正文/实施计划/迁移执行波次_implementation_plan.md`
