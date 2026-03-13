# 调试报告：复合查询下 Tavily 摘要污染与 data handoff 退化

## 1. 问题现象与影响范围

- 现象 1：最终答复中的外部信息段直接出现 `alt=""`、`style="..."`、`#` 等网页残片，用户看到的正文像抓取源码。
- 现象 2：同轮复合问题里，Supervisor 已生成精确的 `assign_to_data_expert` 任务，但 data_expert 最终没有执行贷款 Top10 查询，反而返回澄清。
- 现象 3：即使没有产出 `sql_result`，系统仍把 data 目标记为已完成，最终答复可能错误显示“以上问题已全部覆盖”。
- 影响范围：`app/ai/workflow/multi_agent_graph.py` 的 handoff 规范化、Tavily 摘要规范化、deliverable/coverage 判定；相关回归测试为 `app/tests/test_handoff_detection.py`、`tests/unit/test_multi_agent_streaming_helpers.py`、`tests/unit/test_multi_intent_queue_flow.py`。

## 2. 根因证据链

### 根因 A：data handoff 被整句原问题覆盖

- 证据：`_augment_data_handoff_payload()` 旧逻辑只要当前轮存在用户输入，就把 `task_description` 改写成 `用户原始问题：<整句输入>`。
- 后果：对于“天气 + 贷款 Top10”复合问题，Supervisor 已经拆出的精确 data 任务被重新污染成混合意图，data_expert 容易走澄清而不是执行查询。
- 排除假设：不是 router 没委派，截图与复现实验都表明 `assign_to_data_expert` 已生成。

### 根因 B：Tavily 原始文本未做通用清洗

- 证据：`_summarize_tavily_tool_output()` 在非 JSON 文本分支直接走 `_normalize_tool_summary_text()`，不会移除 HTML 属性、markdown 头标记或网页碎片。
- 后果：`alt=`, `style=`, `#` 直接进入最终摘要。
- 排除假设：不是前端渲染问题，脏文本在后端最终 summary 阶段已存在。

### 根因 C：data.query success 判定过宽

- 证据：`_build_delivery_artifacts()` 旧逻辑对 data deliverable 采用 `summary or payload` 即 success；澄清文本也会变成 summary。
- 后果：没有 `sql_result` 结构化结果时，coverage 仍会错误判定通过。
- 排除假设：不是 coverage 计算器自身 bug，问题发生在 deliverable 构建阶段把状态写成了 `success`。

## 3. 修复内容

### 修复 1：保留精确 data handoff

- 文件：`app/ai/workflow/multi_agent_graph.py`
- 符号：`_should_keep_data_handoff_task_description()`、`_augment_data_handoff_payload()`
- 变更：当 handoff 自带的 `task_description` 已具备足够具体度时，直接透传给 data_expert；只有描述为空或明显过于泛化时才回落到 `用户原始问题`。

### 修复 2：Tavily 原始文本通用清洗

- 文件：`app/ai/workflow/multi_agent_graph.py`
- 符号：`_sanitize_tavily_text()`、`_summarize_tavily_tool_output()`
- 变更：对非 JSON Tavily 文本做 HTML 属性、标签、Markdown 残片、冗余符号的通用清洗，避免网页残片直出。

### 修复 3：data.query 只认结构化结果为完成

- 文件：`app/ai/workflow/multi_agent_graph.py`
- 符号：`_build_delivery_artifacts()`
- 变更：在 coverage reconcile 打开时，`data.query` 只有拿到 `sql_result` 结构化结果后才标记为 `success`；仅有澄清文本时标为 `pending`。

### 回归测试

- `app/tests/test_handoff_detection.py`
  - 新增：复合问题下保留精确 data task 的测试。
- `tests/unit/test_multi_agent_streaming_helpers.py`
  - 新增：Tavily 原始文本含网页噪声时的清洗测试。
- `tests/unit/test_multi_intent_queue_flow.py`
  - 新增：未产出 `sql_result` 时 data deliverable 必须为 `pending` 的测试。

## 4. 验证命令与结果

### 解释器解析

- 命令：`VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/repo_python.sh`
- 结果：`/Users/jijingkun/bojxAI/fastapi/venv/bin/python`

### RED：新增测试先失败

- 命令：
  - `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh app/tests/test_handoff_detection.py tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_multi_intent_queue_flow.py -q`
- 结果：3 个新增用例分别失败，定位到：
  - data handoff 仍混入“嘉兴天气”
  - Tavily 摘要仍包含 `alt=` / `style=`
  - data deliverable 仍被标记为 `success`

### GREEN：最小修复后通过

- 命令：
  - `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh app/tests/test_handoff_detection.py tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_multi_intent_queue_flow.py -q`
- 结果：`62 passed`

### 静态复现实验

- 结论：
  - handoff 保留为“查看 2025-06-30 贷款余额前10名客户...”
  - Tavily 摘要不再包含 `alt=` / `style=` / `#`
  - 没有 `sql_result` 时 `data.query.status=pending`，`coverage_pass=False`

## 5. 风险、回滚点与后续建议

### 风险

- Tavily 非 JSON 文本目前做的是通用文本清洗，不依赖站点定制规则；可读性已明显改善，但仍可能保留部分站点名称类文本。
- data handoff 的“是否足够具体”使用结构化长度/数字/标点特征判断，避免在编排层引入关键词语义词表；极短但精确的 handoff 仍存在被回落到原问题的可能。

### 回滚点

- 回滚文件：`app/ai/workflow/multi_agent_graph.py`
- 回滚方式：回退本次 worktree 提交即可。
- 回归保护：上述 3 个新增测试会在回滚后重新失败。

### 后续建议

- 若后续仍出现 Tavily 摘要可读性不足，建议把天气/外部信息摘要规范化下沉到专门的 renderer/formatter 层，而不是继续在编排层堆叠站点词表。


## 6. 第二轮修复（2026-03-08 晚）

### 新增现象

- 现象 4：`sql_result` 为单行多列时，正文会把 `org_no/org_name/贷款余额` 直接串成一行，同时下方又渲染完整表格卡片，造成重复与样式冲突。
- 现象 5：外部信息最终答复仍保留 `天气/实时信息：标题：标题：内容` 的标签链，第一段回复冗长且可读性差。
- 现象 6：SQL 结果卡片前端使用 `mx-auto w-fit`，窄表会漂在正文中间，与消息流主排版不一致。

### 第二轮修复内容

- `app/ai/workflow/data_graph.py::_interpret_result`
  - 单行多列表格结果改为简明摘要：`查询完成，共返回 1 条记录，详见下方表格。`
  - 保留单列聚合结果的值级解释，不影响指标类直答。
- `app/ai/workflow/multi_agent_graph.py::_build_delivery_artifacts`
  - `external.lookup` 的 summary 不再预拼 `label：summary`，避免最终答复重复标签链。
- `app/ai/workflow/multi_agent_graph.py::_summarize_tavily_tool_output`
  - `results[]` 分支优先使用清洗后的 snippet，不再把 title 强行拼进最终摘要。
- `web/src/components/chat/messages/sql-result-table.tsx`
  - 卡片容器从 `mx-auto w-fit` 改为 `w-full max-w-full`；表格从 `w-max` 改为 `min-w-full`，与正文同层左对齐。

### 第二轮验证

- 后端定向回归：
  - `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh app/tests/test_data_graph_visualization.py app/tests/test_handoff_detection.py tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_multi_intent_queue_flow.py -q`
  - 结果：`75 passed`
- 前端静态校验：
  - `cd web && pnpm exec tsc --noEmit`
  - 结果：通过

## 7. 第三轮修复落地（2026-03-08 夜，data.query contract 收紧）

### 新确认的根因

- 根因 D：`data_expert` 子任务路径仍然看到整句复合问题，而不是只看到数据子任务输入。
- 根因 E：`data.query` handoff 在运行态没有强结构化合同；Supervisor prompt/tool schema 仍允许靠 `task_description` 委派，标准化阶段还会把文本回灌成执行输入。

### 本轮修复目标

- 为 `data.query` 固化 `pending_handoff.frame` 结构化合同（`query_text/metric/time_range/dimensions/query_shape/ranking`），并把 `query_text` 提升为唯一主输入。
- 多意图下 `data_expert` 只消费该子任务输入，不再把整句复合问题当作最新用户问题。
- `router_guard` 在 dispatch 前阻断缺失 `query_text` 或 TopN 排名字段不完整的 `data.query` handoff。

### 修复层级

- 修复层级 1：`assign_to_data_expert` 的 tool schema 与 Supervisor prompt 直接要求写 `frame.query_text`，不再要求 `task_description`。
- 修复层级 2：`multi_agent_graph` 只规范化/校验 `frame`，不再从用户原问题或 `task_description` 自动回填 data handoff。
- 修复层级 3：streaming wrapper 继续隔离 expert 输入消息视图，只把 data 子任务 query 送入 `data_expert`。
- 修复层级 4：`data_graph` 只消费 `frame`，不再把文本 handoff 作为主语义源。


## 9. 第五轮修复落地（2026-03-09 深夜，真实链路再收口）

### 新增根因

- 根因 I：`data_graph.analyze_data_intent()` 在 handoff 子任务路径下仍强依赖二次意图分析模型；上游模型账户异常时，data 子任务会被误降级成普通 `free_query`，随后继续走 SQL 生成并输出泛化错误文案。
- 根因 J：coverage 只保留 `goal_results(success-only)`，导致已失败但有证据的 goal 在最终答复中被统一写成“缺少可用结果”，真实失败原因被吞掉。
- 根因 K：缺少 Supervisor 摘要时，`external.lookup` 仍可能把 Tavily 天气网页正文中的站点导航噪声压缩成单行 summary，天气段格式继续劣化。

### 本轮修复

- `data_graph` 在 handoff 路径下对 `pending_handoff.frame` 做 short-circuit 解析：`frame.query_text` 存在时，不再调用二次意图分析模型。
- handoff 之外若意图分析模型不可用，`data_graph` 直接产出稳定失败文案并停止继续 SQL 生成，禁止伪装成 `free_query`。
- `coverage_report` 新增 `goal_attempts`，最终答复渲染未完成 goal 时优先读取失败尝试证据。
- `data.query` deliverable 不再写 `pending`；无结构化结果时改为 `failed/missing`，并把失败文案写入 payload。
- `external.lookup` 在没有 Supervisor 摘要时，直接把 Tavily 天气网页结果提炼成 `payload.display_markdown`，不再回显 `台风路径/空间天气/图片/专题` 这类站点噪声。

### 回归

- `tests/unit/test_data_graph_clarify_guard.py`：新增 handoff frame short-circuit 与模型不可用稳定失败用例。
- `tests/unit/test_multi_intent_queue_flow.py`：新增 `goal_attempts` 最终答复用例与天气网页结果富文本规整用例。
- `tests/unit/test_multi_intent_coverage_reconcile.py`：coverage 缺口状态由 `pending` 收紧为 contract 合法的 `missing`。

## 8. 第四轮补充证据（2026-03-09，截图与日志对齐）

### 新增根因

- 根因 F：Supervisor 在真实运行时仍会先按旧 schema 调用 `assign_to_data_expert(task_description=...)`；工具报错后，模型自修复把 `frame.query_text` 错写成 SQL，导致后续 data 子任务标题、图表元数据和语义解析被 SQL 文本污染。
- 根因 G：`external.lookup` 最终汇总优先读取 Tavily 原始 tool 内容，而不是 Supervisor 已生成的干净天气摘要，因此最终答复仍出现 `| Mostly dry ...` 这类脏文本。
- 根因 H：data 子任务隔离用的 synthetic `HumanMessage(query_text)` 若泄漏到主消息序列，会污染后续 turn 的会话历史，使 decompose/supervisor 误把内部子任务当成用户真实发言。

### 本轮修复

- 在 `router_guard` 为 `data.query` 新增 `query_text_sql_like` 合同校验：`frame.query_text` 必须是自然语言，禁止 `SELECT/WITH`。
- Router 阻断后补充明确修复提示，要求 Supervisor 重试时写自然语言 `frame.query_text`，而不是 SQL。
- `external.lookup` 交付构建优先提取 `supervisor_excerpt` 中的干净摘要，不再优先拼原始 Tavily 文本。
- 外部信息交付新增 `payload.display_markdown`，最终答复渲染时保留天气段换行与 Markdown 格式，不再被 summary 规范化压平成单行。
- `data_expert` synthetic `HumanMessage` 增加 internal `name`，并沿用后处理过滤规则，避免误落库为用户消息。

### 回归

- `tests/unit/test_router_ignores_intent_plan_runtime.py`：新增 SQL-like `query_text` 阻断用例。
- `tests/unit/test_multi_agent_streaming_helpers.py`：新增 internal handoff message name 断言。
- `tests/unit/test_multi_intent_queue_flow.py`：新增 `external.lookup` 优先 Supervisor 摘要用例。


## 10. 第六轮修复落地（2026-03-09 凌晨，data goal compiler 收口）

### 新增根因

- 根因 L：即使 `data.query` 的运行态 contract 已收紧到 `frame.query_text`，Supervisor 在真实链路里仍可能先打一条无效 `assign_to_data_expert(turn_act_hint only)`，再补第二条结构化 handoff，导致主链路仍受自由 tool call 干扰。
- 根因 M：`external.lookup` 的天气提炼此前在命中首个“可清洗但不可结构化”的结果时就提前返回，后续更好的天气结果没有机会参与选择。

### 本轮修复

- `multi_agent_graph` 新增 data goal compiler：当当前 pending goal 为 `data.query` 时，直接基于 `user_query + current_goal + session_frame` 生成 canonical `pending_handoff.frame`，并以 `dispatch_reason=compiled_data_goal_frame` 派发给 `data_expert`。
- decompose_goals 命中的 `data.query` 正常路径不再依赖 Supervisor 自由 `assign_to_data_expert` tool call；即使本轮没有 data handoff tool 消息，也可自动进入 data_expert。
- `external.lookup` 的 Tavily 天气结果改为“两阶段选择”：先扫描前 3 个候选中的可结构化天气结果；仅当都无法结构化时，才回落到天气摘要块 fallback。
- 天气 fallback 即使只有一句摘要，也统一包装成 `城市天气：
- 摘要：...`，不再平铺标题与站点正文。

### 回归

- `tests/unit/test_multi_agent_streaming_helpers.py`：新增“无 Supervisor data tool call 也能自动编译 data.query handoff”用例。
- `tests/unit/test_multi_agent_streaming_helpers.py`：新增“复合问题中 data 子任务 query_text 不得带天气子句”用例。
- `tests/unit/test_multi_intent_queue_flow.py`：新增“先扫全量天气候选再 fallback”与“天气摘要 fallback 也必须保持天气块格式”用例。
