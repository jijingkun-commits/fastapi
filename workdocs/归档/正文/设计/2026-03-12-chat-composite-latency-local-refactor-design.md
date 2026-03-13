# Chat Composite Latency Local Refactor Technical Design

## Meta

- topic: `chat-composite-latency-local-refactor`
- source_requirements: `docs/内部参考/迭代需求/chat-composite-latency-local-refactor_requirements.md`
- requirements_approved: `true`
- requirements_approval_evidence: `用户确认先走 B. 局部重构版`
- change_mode: `refactor`
- publish_design_doc: `false`
- api_doc_required: `true`
- best_practice_refs:
  - `LangGraph Streaming`: <https://docs.langchain.com/oss/python/langgraph/streaming>
  - `LangGraph Graph API / Send`: <https://docs.langchain.com/oss/python/langgraph/graph-api#send>
  - `MDN Server-Sent Events`: <https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events>
- related_internal_context:
  - `docs/plans/2026-03-10-composite-chat-latency-design.md`
  - `docs/开发文档/架构设计/AI模块设计.md`

## Context

当前耗时问题并不在 HTTP 建连或 SSE 建流，而是在图内执行链路：

1. 显式复合请求虽然能命中 `explicit_multi_goal_fast_path`，但后续仍表现为“拆 goals -> 搜索 -> handoff -> 子图分析 -> coverage -> final”的串行重活。
2. `todo + weather` 这种组合即使中途已拿到天气结果，也没有提前回流正文，用户只能空等到 `final_answer`。
3. `todo.query` 在子图内仍可能被整句复合原句重判成 `out_of_scope -> need_clarify`，把本应执行查询的时间消耗在错误澄清上。
4. coverage/final 收口本身不重，但如果继续按 summary/evidence 弱信号判 answered，会放大 correctness 风险。

本轮目标不是全量并行化，而是先把“体感最差”和“误澄清最贵”的两处局部收口掉。

## Option Analysis

| 方案 | 做法 | 优点 | 缺点 | 结论 |
|---|---|---|---|---|
| A. 全量 `Send` 并行重写 | 把显式复合请求整体改成 fan-out/fan-in | 理论总耗时上限最高 | 状态归属、resume、coverage、回放风险同步放大 | 本轮不选 |
| B. 局部重构版 | 保留主图拓扑，只局部修 preview、frozen todo.query、coverage 口径 | 改动集中、收益直接、风险最小 | 总时长上限不如真正并行 | 本轮采用 |
| C. 继续热点补分支 | 在现有热点文件继续加 if/else | 交付快 | 会继续长胖并放大语义漂移 | 不选 |

## module_boundaries

### 当前问题

- `multi_agent_graph.py` 既负责 fast lane，又承担 preview 回流和 coverage 收口，局部策略分支已经开始直接影响用户体感。
- `todo_graph.py` 同时承担 todo 领域语义与“整句原问题是否越界”的再裁决，导致 frozen `todo.query` 仍可能被推翻。
- `chat_service.py` 目前只做 SSE 生命周期转发，没有统一输出请求级/goal 级 timing 口径。

### 最终决策

1. `goal_resolver` 继续只负责显式复合识别、goal kind 冻结与 handoff contract。
2. `multi_agent_graph.py` 仍是本轮 composite delivery policy 的 single entry owner，但职责收紧为：
   - fast lane 目标预编译；
   - `external.lookup` preview 触发；
   - coverage/final 收口接线。
3. `todo_graph.py` 只负责 todo 领域执行；当 handoff 已冻结为 `todo.query` 时，不再拥有把它打成 `out_of_scope` 的权力。
4. `chat_service.py` 只负责请求级/goal 级 timing 的发射，不做复合问题语义判断。

### 禁止动作

- 禁止在 `chat_service`、API/router/controller 层新增复合问题语义分支。
- 禁止为了局部提速再引入第二套并行 runtime 或双轨执行框架。
- 禁止把 frozen `todo.query` 的语义裁决继续留给下游自由意图分析。

## dependency_direction

### 当前问题

- 当前依赖方向虽然名义上是 `goal_resolver -> workflow -> todo_graph`，但实际 `todo_graph` 仍会反向影响复合问题是否越界。
- coverage 口径散落在 deliverable 匹配和 final render 里，弱化了“goal 是否真的 answered”的单一判断源。

### 最终决策

1. `goal_resolver` 只向 `multi_agent_graph` 输出结构化 goals 与 frozen handoff contract。
2. `multi_agent_graph` 只消费 `goal_resolver` 的 contract，并向 `todo_graph/data_graph` 下发已冻结执行意图。
3. `todo_graph` 不再反向推翻 frozen `todo.query`，只在 contract 缺失或不完整时才回退到 clarify/guard。
4. coverage/final composer 先读标准化 goal outcome，再决定 answered 与最终收口文案。

### 禁止动作

- 禁止 `todo_graph` 根据整句用户原问题重新裁决 frozen `todo.query` 是否属于待办域。
- 禁止 `final_composer` 直接以 summary 非空作为 answered 依据。
- 禁止在编排层继续扩散“天气/股价/汇率”这类散装关键词特判。

## state_ownership

### 当前问题

- `decomposed_goals` 已经存在，但“goal 是否已回答”的口径还没被收敛成单一 owner。
- request-level 与 per-goal timing 没有统一结构化出口，导致耗时分析还得靠手工对日志。

### 最终决策

1. `decomposed_goals` 继续是唯一目标状态源，owner 保持 `preprocess/goal_resolver`。
2. 本轮不新增大而全的新 runtime state 模块；局部标准化的 goal outcome 口径先收敛在 `multi_agent_graph` 的 composite delivery policy 区域。
3. `pending_handoff.frame.todo_action` 视为 frozen todo contract，一旦存在 `query`，下游只执行不重判。
4. `chat_service.stream` 与 `resume` 负责输出 request timing；若本轮补充 goal timing，则必须与请求级 timing 共用同一 meta builder。

### 禁止动作

- 禁止新建第二套“活动 goals 真理源”。
- 禁止 worker 级别 state 先引入，再与现有 `handoff_queue` 双轨共存。
- 禁止 timing 元数据只补 `stream` 主链路而遗漏 `resume`，除非文档显式限定范围。

## error_handling

### 当前问题

- 当前最贵的一段错误路径，是 frozen `todo.query` 误入 `out_of_scope -> need_clarify`。
- 当前 coverage 一旦把 attempt 误看成 answered，就会在 final answer 里错宣称“已全部覆盖”。

### 最终决策

1. 对 frozen `todo.query`，`out_of_scope` 不再有否决权；真正缺少业务信息时才允许进入 clarify。
2. preview 获取失败不阻断主链，只回退到现有最终收口路径。
3. coverage 只把真实 answered 的 must_answer goals 计入 answered_goals；`clarify_needed / failed / pending` 一律视为未完成。
4. final answer 若存在缺口，必须显式说明未完成目标，不得输出“以上问题已全部覆盖”。

### 禁止动作

- 禁止把错误澄清包装成成功交付。
- 禁止为了“先给用户点东西”而提前回流不可消费的中间状态正文。
- 禁止用泛化摘要掩盖未完成 goal。

## Change Map

### new_paths

- `none`
  - reason: 本轮优先局部重构，不新增生产模块；测试文件可按需新增。

### modified_paths

- `app/ai/workflow/multi_agent_graph.py`
  - purpose: 把 fast lane preview 条件从“data 才触发”收敛到“有 external.lookup 且已有可见结果即可触发”，并统一 answered 判定输入。
- `app/ai/workflow/todo_graph.py`
  - purpose: 让 frozen `todo.query` 直通执行，不再被整句复合原句误打成 `out_of_scope -> need_clarify`。
- `app/services/chat_service.py`
  - purpose: 输出请求级/goal 级 timing meta，不参与复合语义裁决。
- `docs/API文档/接口文档.md`
  - purpose: 若时延元数据对外可见，需同步 SSE meta 契约。
- `docs/产品文档/聊天系统需求.md`
  - purpose: 同步显式复合提问的可见时延与 coverage 正确性口径。
- `docs/开发文档/架构设计/AI模块设计.md`
  - purpose: 同步本轮局部重构边界，而不是宣称已进入全量并行图。

### replaced_responsibilities

- `app/ai/workflow/multi_agent_graph.py` 中 “`fast_lane_source == explicit_multi_goal_fast_path` 且必须包含 `data` bucket 才允许 external preview” 的旧门槛
  - replaced_by: “显式复合 + `external.lookup` 已拿到用户可见结果即可 preview”
- `app/ai/workflow/todo_graph.py` 中 frozen `todo.query` 仍会落入 `_is_out_of_scope_for_todo + LLM intent reclassification` 的旧路径
  - replaced_by: frozen query contract-first execution
- `app/ai/workflow/multi_agent_graph.py::_can_match_deliverable_for_coverage`
  - replaced_by: 基于 goal outcome 的 answered 判定
- `app/ai/workflow/multi_agent_graph.py::_can_render_goal_attempt`
  - replaced_by: coverage/final composer 对 attempt 与 outcome 的分层消费

## Runtime Design Details

### 1. Preview 提前回流

- 保留现有 `preprocess fast lane`。
- 触发条件从“显式复合 + data bucket”收紧为“显式复合 + 存在 external goal + 已拿到可直答结果”。
- 用户可见正文仍走现有 `token/custom` 通道；`status/tool_start/handoff` 不计入首个可见正文。

### 2. Frozen todo.query 直通

- 当 `pending_handoff.frame.todo_action == query` 时，todo 子链路优先执行 query contract。
- 只有 contract 缺失、不完整或无目标时，才允许回退到意图分析/clarify。
- 该决策只覆盖 frozen `todo.query`，不顺带改变 `create/update/delete/complete` 其他路径。

### 3. Coverage 与 Final 收口

- answered 判定先做最小 goal outcome 归一：
  - `answered`
  - `clarify_needed`
  - `failed`
  - `pending`
- `coverage_pass=true` 的必要条件是：所有 `must_answer` goals 均为 `answered`。
- `final_answer` 仍是唯一最终正文出口；若存在缺口，按用户 goal 顺序显式标注未完成目标。

### 4. Timing 观测

- request-level:
  - `first_event_at_ms`
  - `first_visible_at_ms`
  - `final_answer_at_ms`
  - `done_at_ms`
- 若本轮补充 goal-level timing，字段固定为：
  - `goal_started_at_ms`
  - `goal_first_visible_at_ms`
  - `goal_terminal_at_ms`
  - `goal_terminal_status`
- `stream` 与 `resume` 必须使用同一套 meta builder；若无法同轮完成，则视为设计漂移。

## DB Migration Contract

- db_migration_required: `false`
- db_change_scope: `none`
- db_migration_mode: `sync_database_only`
- release_migration_required: `false`
- db_rollback_strategy: `not_applicable`

## Shrink Contract

- obsolete_paths:
  - `app/ai/workflow/multi_agent_graph.py` 中 “仅 `data` bucket 才允许 external preview” 的条件分支
  - `app/ai/workflow/todo_graph.py` 中 frozen `todo.query` 继续落入 `out_of_scope -> need_clarify` 的旧路径
  - `app/ai/workflow/multi_agent_graph.py::_can_match_deliverable_for_coverage`
  - `app/ai/workflow/multi_agent_graph.py::_can_render_goal_attempt`
- retained_paths:
  - `app/ai/intent/goal_resolver.py`：唯一保留理由是“显式复合 goal/handoff 语义入口”
  - `app/ai/workflow/multi_agent_graph.py::_preprocess_multimodal`：唯一保留理由是“fast lane 入口与 preview 编排 owner”
  - `app/ai/workflow/multi_agent_graph.py::_final_composer_node`：唯一保留理由是“最终答复 single entry owner”
  - `app/ai/workflow/todo_graph.py::analyze_intent`：唯一保留理由是“未冻结 todo 请求的领域语义入口”
  - `app/services/chat_service.py::stream`：唯一保留理由是“请求级时延发射 owner”
- single_entry_owner: `app/ai/workflow/multi_agent_graph.py`
- line_budget: `added<=deleted`

说明：

- 本轮不是“先搭一个新 runtime owner 再慢慢迁”，而是优先在现有热点内部做减法收口。
- 若实现阶段需要新增第二个生产 owner 文件或明显超出 `line_budget`，必须回退重新评审，输出 `IMP_PLAN_DRIFT_DETECTED`。

## Doc Sync Flags

- api_doc_required: `true`
- publish_design_doc: `false`
- required_doc_sync_targets:
  - `docs/API文档/接口文档.md`
  - `docs/产品文档/聊天系统需求.md`
  - `docs/开发文档/架构设计/AI模块设计.md`
  - `docs/开发文档/测试管理/聊天系统测试案例.md`
  - `docs/开发文档/测试管理/测试用例库.md`
