# supervisor 主会话 state 归属与能力分层重构设计（冻结单方案）

> 设计目标：冻结“多轮对话最重要的 state 归谁、哪些能力该是 workflow、哪些能力该是 stateless subagent、哪些能力只该是 tool/service”的单方案。
>
> 外部最佳实践核验日期：2026-03-09。
> 参考来源：
> - OpenAI Agents SDK - Multi-agent / Orchestration：<https://openai.github.io/openai-agents-python/multi_agent/>
> - OpenAI Agents SDK - Handoffs：<https://openai.github.io/openai-agents-python/handoffs/>
> - OpenAI Agents SDK - Sessions：<https://openai.github.io/openai-agents-python/sessions/>
> - LangChain - Subagents：<https://docs.langchain.com/oss/python/langchain/multi-agent/subagents>
> - LangGraph - Use subgraphs：<https://docs.langchain.com/oss/python/langgraph/use-subgraphs>
> - LangGraph - Interrupts：<https://docs.langchain.com/oss/python/langgraph/interrupts>

## 1. `scope_contract`
```yaml
scope_contract:
  objective: "冻结本仓库 AI 主链的 state ownership 与能力分层：主会话 state 归 supervisor，todo/data 归 workflow，知识深研归 stateless subagent，原子能力归 tool/service。"
  scope:
    - "聊天主链：ChatService / RunControl / multi_agent_graph 的控制面职责。"
    - "Supervisor 的多轮会话上下文、路由与汇总职责。"
    - "todo_graph / data_graph 的状态边界与输入契约。"
    - "用户上传附件（CSV/Excel/JSON/PDF/TXT/图片/其他文档）后，由 supervisor 自主规划后续链路的端到端流程。"
    - "knowledge_search / web_search / file / vision / skill / memory 等能力的层级归类。"
    - "消息回放与运行态追踪所需的 canonical replay 字段冻结。"
  boundaries:
    - "本轮不直接改前端交互，不新增新的用户可见操作按钮。"
    - "本轮不修改数据库 schema，不重写 memory 存储模型。"
    - "本轮不立即实现完整 knowledge research agent，只冻结其目标形态与接入契约。"
    - "本轮不把 todo/data 继续包装成通用 stateless subagent。"
  success_criteria:
    - "主会话最重要 state 的 owner 被唯一冻结为 supervisor，而不是共享 messages。"
    - "todo/data 被唯一冻结为 workflow/subgraph，而不是通用 subagent。"
    - "知识深研类能力被唯一冻结为 stateless subagent；简单检索仍是 tool。"
    - "专家输入改为 contract-first：专家默认不再直接消费完整多轮 messages。"
    - "回放 canonical 字段唯一冻结，不再允许 replay contract 漫游。"
```

## 2. product_contract
```yaml
product_contract:
  target_users:
    - "AI 主链与工作流维护者"
    - "未来在本仓库继续迭代对话能力的后端研发"
    - "最终对话终端用户（间接受益）"
  core_scenarios:
    - "S1：用户连续多轮和系统对话时，主上下文由 supervisor 连续持有，不被 todo/data 局部流程污染。"
    - "S2：用户进入待办确认/澄清/恢复流程时，todo 只维护本领域流程状态，不反向主导整轮会话。"
    - "S3：用户进入问数澄清/SQL 安全检查/重试流程时，data 只维护本领域查询状态。"
    - "S4：用户上传附件后，系统先由 supervisor 结合用户目标、附件清单、轻量预检结果自主规划，而不是仅按文件类型硬路由。"
    - "S5：当附件用于数据统计/清洗/可视化时，规划结果应进入 data workflow。"
    - "S6：当附件用于文档总结/证据归纳/跨来源研究时，规划结果应进入 research subagent 或 direct tool。"
    - "S7：interrupt / resume / cancel 后，系统仍能以 supervisor 的主会话状态继续接话。"
  business_goals:
    - "G1：冻结单一主会话 owner，避免状态 owner 漂移。"
    - "G2：减少上下文串味与消息污染，降低后续 agent 设计复杂度。"
    - "G3：为后续 /jjk-plan 提供稳定的 capability layering 基线。"
    - "G4：保证人机闭环流程（todo/data）与研究型能力（kb/web）采用不同且正确的抽象。"
    - "G5：为‘用户上传附件后请求处理’提供单一规划口径：由 supervisor 基于目标 + 附件事实自主决策，而不是靠文件类型或 prompt hint 直接定路由。"
  business_goal_metrics:
    - "M1：主对话连续性由 supervisor 唯一负责，设计口径不再出现共享 owner。"
    - "M2：todo/data 的专家输入契约不再以完整 `messages` 为默认真理源。"
    - "M3：知识研究类能力具备独立 contract，可在单次隔离上下文中运行。"
    - "M4：replay canonical 字段唯一化，历史兼容口径明确为读旧写新。"
  non_goals:
    - "本轮不重写整个 multi_agent_graph。"
    - "本轮不把所有 direct tool 都改造成 agent。"
    - "本轮不处理前端 UI 文案与交互细节重构。"
    - "本轮不引入额外 DB 表来保存 conversation state。"
  acceptance_gates:
    - "AG1：architecture_contract 明确 supervisor / workflow / subagent / tool / service 五层边界。"
    - "AG2：clarify_handoff_contract 覆盖全部 requirement_seeds 与 implementation_seeds。"
    - "AG3：replay canonical 字段被唯一冻结为 `additional_kwargs.router_result_v2.conversation_state`。"
    - "AG4：todo/data 不再被设计为通用 stateless subagent。"
    - "AG5：knowledge_search 继续保留 tool 形态，knowledge research 才是 subagent。"
    - "AG6：上传附件场景统一先进入 supervisor planning，再基于 attachment contract 决定 direct tool / data workflow / research subagent / todo workflow。"
  release_constraints:
    - "系统尚未上线，以设计合理、边界清晰、最小心智负担为最高优先级。"
    - "任何后续实现不得通过 fallback/兼容层继续掩盖 state owner 不清的问题。"
```

- target_users: AI 主链与工作流维护者；后端研发；终端用户（间接受益）
- core_scenarios: supervisor 持有主会话；待办 workflow 管理确认闭环；问数 workflow 管理查询澄清；附件先规划再路由；interrupt/resume 回 supervisor
- business_goals: 主会话 owner 唯一化；上下文串味归零；附件硬路由归零；研究能力与流程能力分层清晰
- non_goals: 不重写全链；不改 DB schema；不把所有能力都 agent 化；不新增 conversation_state 持久化表
- acceptance_gates: AG1 五层边界清晰；AG2 clarify_handoff_contract 完整；AG3 replay canonical 唯一；AG4 待办与问数流程为 workflow；AG5 knowledge_search 保持 tool；AG6 附件统一 supervisor planning

## 3. `architecture_contract`
```yaml
architecture_contract:
  module_boundaries:
    - module: "app/services/chat_service.py + app/services/run_control_service.py"
      responsibility: "控制面；负责 stream、interrupt/resume/cancel、human message 进入主图、对外 SSE 生命周期。"
      not_responsible:
        - "决定 todo/data 的领域语义"
        - "持有 todo/data 的局部流程状态"
    - module: "app/ai/workflow/multi_agent_graph.py::supervisor"
      responsibility: "主会话 owner；负责理解当前轮、多轮承接、路由、补齐、汇总、最终对外答复。"
      not_responsible:
        - "持有 todo/data 的内部执行细节"
        - "直接承担知识深研的大上下文阅读"
    - module: "app/ai/workflow/todo_graph.py"
      responsibility: "todo workflow；负责 pending_operation、确认、澄清、interrupt 后恢复与执行。"
      not_responsible:
        - "主会话连续性"
        - "知识研究或网页研究"
    - module: "app/ai/workflow/data_graph.py"
      responsibility: "data workflow；负责数据库查询与 uploaded data 的结构化分析（统计、清洗、聚合、可视化）。"
      not_responsible:
        - "主会话连续性"
        - "非数据研究型任务"
    - module: "future knowledge_research_subagent / document_research_subagent"
      responsibility: "单次隔离上下文中的重资料检索、文档阅读、去噪、证据归纳、摘要产出。"
      not_responsible:
        - "跨轮保存业务状态"
        - "直接接管主会话"
    - module: "app/ai/tools/* + app/services/memory_* + app/services/skill_service.py"
      responsibility: "原子能力与后台状态服务；工具做一次性动作，service 做持久化/治理/装配。"
      not_responsible:
        - "直接主导对话编排"
        - "伪装成主会话 agent"

  dependency_direction:
    - "chat_service/run_control -> multi_agent_graph(supervisor)"
    - "supervisor -> todo_workflow | data_workflow | knowledge_research_subagent | direct tools"
    - "todo_workflow -> todo_tools + repositories/services"
    - "data_workflow -> data_query_tools + sql_policy + repositories/services"
    - "knowledge_research_subagent -> retrieval/search/file/vision tools"
    - "memory services / skill service / repositories 不得反向依赖 supervisor 的语义判定"

  end_to_end_dataflow:
    - "用户输入先进入 supervisor 主会话；supervisor 维护本轮 turn_act、session_frame、active goals、pending user action。"
    - "当命中 todo/data 时，supervisor 只投影最小 expert_input_contract 到对应 workflow。"
    - "当用户上传附件时，supervisor 先执行 attachment planning：基于 `user_goal + attachment_manifest + lightweight_probe` 判断附件扮演的数据源、证据源、上下文源或任务载体角色。"
    - "规划结果只允许四类：`direct_tool`、`data_workflow`、`research_subagent`、`todo_workflow`；若一轮存在多目标，可生成 mixed plan。"
    - "当规划结果为 `data_workflow` 时，data workflow 在 `analysis_mode=file_analysis|db_query|hybrid` 下运行；file_analysis 首步必须是 attachment ingest / dataset profile，而不是直接套 SQL 链。"
    - "当规划结果为 `research_subagent` 时，附件仅作为 research task 的输入工件，不转交主会话控制权。"
    - "workflow/subagent 只维护各自局部状态，并返回结构化结果给 supervisor。"
    - "当命中重资料问题时，supervisor 调用 stateless research subagent；subagent 在隔离上下文中完成检索与归纳，只返回 summary + evidence。"
    - "最终用户可见答复始终由 supervisor/final_composer 收口。"

  state_lifecycle:
    persistent_state_owner:
      supervisor_conversation_state:
        owner: "supervisor"
        fields:
          - "messages（证据源，不等于专家输入真理源）"
          - "turn_act"
          - "session_frame"
          - "clarify_fsm_state"
          - "clarify_round"
          - "decomposed_goals"
          - "delivery_meta"
          - "coverage_report"
      workflow_local_state:
        shared_attachment_facts:
          owner: "supervisor planning contract"
          fields:
            - "attachment_manifest"
            - "selected_attachment_ids"
            - "lightweight_probe"
            - "attachment_role"
            - "analysis_mode"
            - "planning_route"
        todo_owner_fields:
          - "pending_operation"
          - "user_confirmed"
          - "pending_clarifications"
          - "draft_todos"
          - "current_todo_id"
        data_owner_fields:
          - "query_context"
          - "generated_sql"
          - "pending_sql"
          - "sql_approved"
          - "clarification_needed"
          - "sql_history"
      world_state:
        owner: "repositories / memory services / db"
        fields:
          - "todo records"
          - "memory documents / chunks"
          - "user preferences"
          - "skill registry / catalog"
    transient_state_owner:
      research_subagent_run_state:
        owner: "single research call"
        lifecycle: "single run only; no cross-turn durable ownership"
      attachment_planning_state:
        owner: "supervisor"
        lifecycle: "single turn planning result, persisted only as conversation snapshot / route evidence"
      routing_transients:
        owner: "supervisor"
        fields:
          - "pending_handoff"
          - "handoff_queue"
          - "completed_handoffs"
          - "handoff_execution_trace"

  replay_canonical:
    canonical_field: "AIMessage.additional_kwargs.router_result_v2.conversation_state"
    semantics:
      write_new: "supervisor 输出用户可见 AIMessage 时，统一写入 conversation_state snapshot。"
      read_old: "历史消息若仅有 `router_result_v2` 且缺少 `conversation_state`，按 partial snapshot 处理，不阻断回放。"
      forbidden:
        - "新增第二套 replay 顶层字段"
        - "继续让 workflow 自定义并行 message additional_kwargs 真理源"
    required_snapshot_fields:
      - "owner=supervisor"
      - "turn_act"
      - "active_goal_ids"
      - "active_workflow"
      - "pending_user_action"
      - "session_frame_slots"

  error_handling:
    - "主会话连续性异常、路由异常、覆盖缺口异常：统一回流 supervisor。"
    - "todo/data 内部澄清、确认、SQL 安全或重试异常：由各自 workflow 收口，再返回 supervisor。"
    - "research subagent 证据不足或检索失败：返回 structured insufficiency，不直接输出用户最终答复。"
    - "memory/skill/db 一致性异常：由 service 层记录和降级，不越权决定对话策略。"

  attachment_planning_contract:
    decision_order:
      - "user_goal（用户真正要系统做什么）"
      - "conversation_state（当前是否存在待确认/待恢复的人机闭环）"
      - "attachment_manifest（附件客观元数据）"
      - "lightweight_probe（附件轻量预检事实）"
      - "available_capabilities（当前可调用 workflow/subagent/tool）"
    attachment_manifest_min_fields:
      - "attachment_id"
      - "name"
      - "mime"
      - "size_bytes"
      - "uri"
      - "derived_kind"
    lightweight_probe_contract:
      common_fields:
        - "attachment_id"
        - "probe_status"
        - "summary"
      optional_by_kind:
        tabular:
          - "sheet_names"
          - "column_names"
          - "row_count_estimate"
          - "sample_types"
        document:
          - "title"
          - "page_count"
          - "section_hints"
          - "ocr_needed"
        image:
          - "vision_hint"
          - "ocr_hint"
          - "chart_like"
    planning_result_contract:
      required_fields:
        - "route"
        - "selected_attachment_ids"
        - "attachment_roles"
        - "planner_reason"
      optional_fields:
        - "analysis_mode"
        - "execution_items"
        - "requires_user_confirmation"
    route_semantics:
      direct_tool: "单附件、单动作、无需局部流程状态；例如读文件、看图、提取文本。"
      data_workflow: "目标是统计/清洗/聚合/可视化/文件+数据库混合分析，需要数据流程状态。"
      research_subagent: "目标是总结、对比、证据归纳、跨来源研究；附件是研究输入，不拥有主会话。"
      todo_workflow: "目标是从附件中提炼待办、进入确认/澄清/恢复的人机闭环。"
      mixed: "同一轮存在多个子目标，由 supervisor 持有 `execution_items[]` 执行计划并协调，最终统一答复。"
    routing_principles:
      - "文件类型只提供能力提示，不直接决定唯一路由。"
      - "先按用户目标定 route，再按附件事实定 attachment_role。"
      - "需要中断/确认/恢复时优先 workflow；只做一次性读取或研究时优先 tool/subagent。"
      - "mixed 只能由 supervisor 持有执行计划，子能力不互相接管主对话。"
      - "todo_workflow 允许消费附件，但仅限‘从附件中提炼待办/进入确认闭环’场景。"

  semantic_freeze:
    - "最重要的多轮会话 state owner 唯一冻结为 supervisor。"
    - "messages 是跨轮证据源，不是 workflow/subagent 的默认输入真理源。"
    - "todo/data 唯一冻结为 workflow/subgraph，不是通用 stateless subagent。"
    - "附件类型本身不是路由真理源；真正的路由真理源是 supervisor 规划结果。"
    - "knowledge_search/web_search 是 tool；knowledge/web/document research 才是 stateless subagent。"
```

## 4. `best_practice_basis`

| 来源 | 冻结出的最佳实践 | 对本仓库的直接结论 |
|---|---|---|
| OpenAI Multi-agent | manager / agents-as-tools 适合主控保留对话 | `supervisor` 应持有主会话 |
| OpenAI Handoffs | handoff 默认会带会话历史，适合“换接待员” | 不能把 `todo/data` 默认按 handoff=subagent 设计 |
| OpenAI Sessions | 同一 session 会继承历史 | 想做隔离就不能让研究型能力复用主会话记忆 |
| LangChain Subagents | subagent 更适合 stateless、重上下文任务 | knowledge/web/document research 适合新建 stateless subagent |
| LangGraph Subgraphs | 不同状态 schema / 私有状态适合 subgraph | `todo_graph` / `data_graph` 应按 workflow/subgraph 建模 |
| LangGraph Interrupts | 需要 HITL 的流程更像 workflow | `todo` 明确命中，`data` 部分命中 |
| OpenAI Code Interpreter | 文件型任务适合先读取/执行/迭代分析，而不是只靠提示词猜 | 附件处理应先形成 attachment facts，再由 supervisor 规划去向 |

## 5. `requirement_seeds`

| fr_id | design_item | trigger | input_contract | output_contract | failure_semantics | observability_fields | rollback_anchor | acceptance_cmd_ref |
|---|---|---|---|---|---|---|---|---|
| FR-01 | supervisor_conversation_state_owner | 任意多轮用户输入进入主链 | `prompt + thread_id + current state` | `conversation_state(owner=supervisor)` | owner 不明即 `NO_GO` | `turn_id, active_goal_ids, active_workflow, pending_user_action` | `revert:T01~T02` | `rg -n "session_frame|turn_act|clarify_fsm_state|clarify_round" app/ai/state.py app/ai/workflow/multi_agent_graph.py` |
| FR-02 | workflow_local_state_isolation | 路由到 todo/data | `expert_input_contract + workflow local state` | `workflow_result + local state delta` | workflow 读取全量 messages 视为违规 | `target_workflow, contract_version, state_owner` | `revert:T03~T04` | `rg -n "recent_messages|filtered_messages|pending_operation|pending_sql" app/ai/workflow/todo_graph.py app/ai/workflow/data_graph.py` |
| FR-03 | research_subagent_stateless_pattern | 命中重资料知识/网页/文档研究 | `research_task_contract` | `summary + evidence + insufficiency` | 不得持久化跨轮 scratchpad | `research_task_id, source_count, citation_count` | `revert:T05` | `rg -n "knowledge_search|search_tool|read_uploaded_file|analyze_image" app/ai/workflow/multi_agent_graph.py app/ai/tools` |
| FR-04 | contract_first_expert_input | supervisor 需要调用 workflow/subagent | `selected facts + constraints + output schema` | `expert_input_contract` | 不允许默认透传完整多轮对话 | `contract_id, source_fields, target_agent` | `revert:T03~T05` | `rg -n "pending_handoff|frame|task_description|query_text" app/ai/workflow/multi_agent_graph.py` |
| FR-05 | replay_canonical_single_source | supervisor 写 AIMessage additional_kwargs | `router_result_v2 + conversation snapshot` | `additional_kwargs.router_result_v2.conversation_state` | 多 canonical 并存视为阻断 | `replay_source, canonical_field, snapshot_version` | `revert:T02` | `rg -n "router_result_v2|additional_kwargs" app/ai/workflow/multi_agent_graph.py app/ai/protocol.py` |
| FR-06 | final_answer_owned_by_supervisor | 任意 workflow/subagent 完成后 | `workflow/subagent result` | `supervisor final answer` | 专家直接兜底主答复视为违规 | `final_answer_owner, coverage_pass, summarized_by` | `revert:T02~T05` | `rg -n "final_composer|summarize|postprocess|final_answer" app/ai/workflow/multi_agent_graph.py` |
| FR-07 | attachment_supervisor_planning | 用户上传任意附件并提出处理请求 | `user_goal + attachment_manifest + lightweight_probe` | `attachment_plan(route=direct_tool|data_workflow|research_subagent|todo_workflow|mixed)` | 不得按文件类型硬编码唯一去向，也不得把 prompt hint 当唯一契约 | `attachment_count, selected_attachment_ids, attachment_role, planning_route` | `revert:T05~T08` | `rg -n "attachments|read_uploaded_file|file_processing|data_analysis|analyze_image" app/services/chat_service.py app/ai/prompts app/ai/workflow` |

## 6. `implementation_seeds`

| task_id | blocked_by | file_paths | symbols | change_type | acceptance_cmds |
|---|---|---|---|---|---|
| T01 | [] | `app/ai/state.py`,`docs/开发文档/架构设计/AI模块设计.md` | `BaseAgentState`,`MultiAgentState`,`状态分层说明` | refactor | `rg -n "messages|session_frame|turn_act|pending_operation|pending_sql" app/ai/state.py docs/开发文档/架构设计/AI模块设计.md` |
| T02 | [T01] | `app/ai/workflow/multi_agent_graph.py`,`app/ai/protocol.py` | `router_result_v2`,`conversation_state replay snapshot`,`_build_expert_inference_messages` | refactor | `bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_multi_agent_context_budget.py -q` |
| T03 | [T02] | `app/ai/workflow/todo_graph.py`,`app/ai/workflow/todo_intent_helpers.py` | `analyze_intent`,`filter_messages_for_todo`,`todo expert input contract` | refactor | `bash scripts/pytest_targeted.sh tests/unit/test_todo_handoff_observation.py tests/unit/test_todo_nodes.py -q` |
| T04 | [T02] | `app/ai/workflow/data_graph.py` | `_extract_handoff_context`,`create_data_graph`,`data expert input contract` | refactor | `bash scripts/pytest_targeted.sh tests/unit/test_data_graph_pending_handoff_state.py tests/unit/test_data_graph_clarify_guard.py -q` |
| T05 | [T02] | `app/ai/workflow/multi_agent_graph.py`,`app/ai/tools/ragflow_tool.py`,`app/ai/tools/chatTools.py` | `knowledge/web research dispatch contract` | new_feature | `rg -n "knowledge_search|search_tool|research" app/ai/workflow/multi_agent_graph.py app/ai/tools` |
| T06 | [T01,T02,T03,T04,T05] | `docs/开发文档/架构设计/AI模块设计.md`,`docs/开发文档/架构设计/待办Agent设计.md` | `capability layering sections` | modify | `rg -n "workflow|subagent|tool|service|conversation_state" docs/开发文档/架构设计/AI模块设计.md docs/开发文档/架构设计/待办Agent设计.md` |
| T07 | [T02,T03,T04] | `tests/unit/test_multi_agent_streaming_helpers.py`,`tests/unit/test_todo_handoff_observation.py`,`tests/unit/test_data_graph_pending_handoff_state.py` | `contract-first regressions` | modify | `bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_todo_handoff_observation.py tests/unit/test_data_graph_pending_handoff_state.py -q` |
| T08 | [T02,T04,T05] | `app/services/chat_service.py`,`app/ai/workflow/multi_agent_graph.py`,`docs/开发文档/架构设计/附件系统设计.md` | `attachment_manifest contract`,`attachment planning`,`planning_route` | refactor | `rg -n "attachments|read_uploaded_file|attachment_manifest|planning_route|lightweight_probe" app/services/chat_service.py app/ai/workflow/multi_agent_graph.py docs/开发文档/架构设计/附件系统设计.md` |

## 7. `execution_chain_seed`

```yaml
execution_chain_seed:
  preferred_mode: core
  task_key: PP-20260309-supervisor-conversation-state-ownership
  card_seed: [T01, T02, T03, T04, T05, T06, T07, T08]
  execution_contract_hint:
    delivery_mode: staged
    execution_unit: per_task
    commit_policy: per_pr
    stop_boundary: per_pr
```

## 8. `risk_rollback_contract`

| risk_id | 关键风险 | 触发信号 | 回退锚点（代码） | 回退动作 |
|---|---|---|---|---|
| R01 | 过度引入新 state 结构，导致当前主链更复杂 | 新增字段显著多于删除字段 | `T01~T02` | 回退新增结构，优先复用现有 `session_frame/turn_act/router_result_v2` |
| R02 | todo/data 收口后行为回归，澄清或确认链断裂 | `todo/data targeted tests` 失败 | `T03~T04` | 回退 contract-first 改动，恢复上一版输入裁剪逻辑，再单独补契约 |
| R03 | knowledge research 设计过度工程化，拖慢主线 | T05 无法在单 PR 中收口 | `T05` | 暂缓 research subagent 实现，仅保留设计与接口占位 |
| R04 | replay canonical 迁移导致历史回放不兼容 | 历史消息缺少新字段即报错 | `T02` | 维持 `router_result_v2` 兼容读取，严格执行“读旧写新” |

## 9. `design_freeze_summary`

```yaml
design_freeze_summary:
  design_actionable: true
  missing_blocks: []
  risk_level: medium
  risk_counterexamples_count: 4
  handoff_contract_ready: true
  product_contract_ready: true
  implementation_seed_count: 8
  semantic_frozen: true
  contract_source_decided: true
  handoff_seed_alignment_ok: true
  parallel_dependency_ready: true
  replay_canonical_field_set: true
  blocking_issues: []
```

## 10. `clarify_handoff_contract`

```yaml
clarify_handoff_contract:
  version: v2
  topic: "supervisor 主会话 state 归属、能力分层与附件规划"
  design_source: "workdocs/归档/正文/设计/2026-03-09-supervisor-conversation-state-ownership-design.md"
  handoff_ready: true
  required:
    product_contract_summary:
      target_users:
        - "AI 主链与工作流维护者"
        - "本仓库后续迭代研发"
        - "终端用户（间接受益）"
      core_scenarios:
        - "supervisor 唯一持有主会话 state"
        - "待办与问数 workflow 只管理局部状态"
        - "knowledge/web research 作为 stateless subagent 隔离运行"
        - "interrupt/resume 后仍由 supervisor 承接主会话"
      business_goal_metrics:
        - "主会话 owner 唯一化"
        - "expert input 改为 contract-first"
        - "research ability 隔离上下文运行"
        - "replay canonical 唯一化"
      non_goals:
        - "不重写全链"
        - "不改 DB schema"
        - "不把所有能力 agent 化"
      acceptance_gates:
        - "conversation_state owner=supervisor"
        - "待办与问数流程=workflow"
        - "knowledge_search=tool"
        - "research=subagent"
        - "router_result_v2.conversation_state=唯一 replay canonical"
    requirement_seeds:
      - design_item: "supervisor_conversation_state_owner"
        fr_id: "FR-01"
      - design_item: "workflow_local_state_isolation"
        fr_id: "FR-02"
      - design_item: "research_subagent_stateless_pattern"
        fr_id: "FR-03"
      - design_item: "contract_first_expert_input"
        fr_id: "FR-04"
      - design_item: "replay_canonical_single_source"
        fr_id: "FR-05"
      - design_item: "final_answer_owned_by_supervisor"
        fr_id: "FR-06"
      - design_item: "attachment_supervisor_planning"
        fr_id: "FR-07"
    implementation_seeds:
      - task_id: "T01"
        file_paths: ["app/ai/state.py", "docs/开发文档/架构设计/AI模块设计.md"]
        symbols: ["BaseAgentState", "MultiAgentState", "状态分层说明"]
        change_type: "refactor"
      - task_id: "T02"
        file_paths: ["app/ai/workflow/multi_agent_graph.py", "app/ai/protocol.py"]
        symbols: ["router_result_v2", "conversation_state replay snapshot", "_build_expert_inference_messages"]
        change_type: "refactor"
      - task_id: "T03"
        file_paths: ["app/ai/workflow/todo_graph.py", "app/ai/workflow/todo_intent_helpers.py"]
        symbols: ["analyze_intent", "filter_messages_for_todo"]
        change_type: "refactor"
      - task_id: "T04"
        file_paths: ["app/ai/workflow/data_graph.py"]
        symbols: ["_extract_handoff_context", "create_data_graph"]
        change_type: "refactor"
      - task_id: "T05"
        file_paths: ["app/ai/workflow/multi_agent_graph.py", "app/ai/tools/ragflow_tool.py", "app/ai/tools/chatTools.py"]
        symbols: ["knowledge/web research dispatch contract"]
        change_type: "new_feature"
      - task_id: "T06"
        file_paths: ["docs/开发文档/架构设计/AI模块设计.md", "docs/开发文档/架构设计/待办Agent设计.md"]
        symbols: ["capability layering sections"]
        change_type: "modify"
      - task_id: "T07"
        file_paths: ["tests/unit/test_multi_agent_streaming_helpers.py", "tests/unit/test_todo_handoff_observation.py", "tests/unit/test_data_graph_pending_handoff_state.py"]
        symbols: ["contract-first regressions"]
        change_type: "modify"
      - task_id: "T08"
        file_paths: ["app/services/chat_service.py", "app/ai/workflow/multi_agent_graph.py", "docs/开发文档/架构设计/附件系统设计.md"]
        symbols: ["attachment_manifest contract", "attachment planning", "planning_route"]
        change_type: "refactor"
    execution_chain_seed:
      preferred_mode: core
      task_key: "PP-20260309-supervisor-conversation-state-ownership"
      card_seed: ["T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08"]
      execution_contract_hint:
        delivery_mode: staged
        execution_unit: per_task
        commit_policy: per_pr
        stop_boundary: per_pr
    alignment_contract:
      strict_match: true
      requirement_seed_ids: ["FR-01", "FR-02", "FR-03", "FR-04", "FR-05", "FR-06", "FR-07"]
      implementation_task_ids: ["T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08"]
      card_seed_ids: ["T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08"]
  extended:
    observability_hints:
      - "保留 turn_id / active_goal_ids / active_workflow / pending_user_action 追踪字段"
      - "workflow 与 research dispatch 都要输出 contract_version"
    risk_counterexample_map:
      - risk_id: "R01"
        counterexample: "为 conversation_state 再加第二份 top-level replay 字段"
      - risk_id: "R02"
        counterexample: "todo 继续直接吃 recent_messages[-5:] 作为默认真理源"
      - risk_id: "R03"
        counterexample: "knowledge_search 直接升级成跨轮有状态专家"
      - risk_id: "R04"
        counterexample: "历史 router_result_v2 缺 conversation_state 时直接报错"
    assumptions:
      - "现有 `session_frame/turn_act/clarify_*` 足以承载主会话结构化状态，不先新建 DB 真理源。"
      - "`router_result_v2` 继续作为 replay 单一 message canonical 字段。"
      - "附件的第一层决策由 supervisor planning 完成；research/data/todo/direct_tool 只是规划结果。"
    - "mixed 被显式允许，但 `execution_items[]` 的 owner 仍是 supervisor。"
    - "todo_workflow 允许消费附件，但目标必须是待办提炼、确认、恢复等闭环任务。"
      - "research subagent 首期只覆盖 knowledge/web/document heavy 场景。"
```

## 11. `clarify_consistency_check`

```yaml
clarify_consistency_check:
  clarify_phase: approval
  current_round: 6
  question_mode: package
  open_questions_count: 0
  product_contract_ready: true
  semantic_frozen: true
  contract_source_decided: true
  handoff_seed_alignment_ok: true
  parallel_dependency_ready: true
  replay_canonical_field_set: true
  fail_fast_codes: []
```

## 12. `execution_notes`

```yaml
execution_notes:
  fallback:
    brainstorming: false
    team: false
  template:
    missing: false
    source: ".agents/skills/jjk-clarify/SKILL.md"
  question_mode: "package"
  degrade_reason: ""
  alternative_tool: ""
  verification: "已完成 clarify/approval；用户以‘好的’确认冻结方案，可进入 jjk-plan。"
```

## 13. 审批记录

- design_approved: true
- approved_at: 2026-03-10 10:04 CST
- approved_round: round-6
- approval_evidence: "好的"
- approval_mode: approved
- go_no_go: GO
- blocking_issues: []

## 14. 审批动作（完成）

- 审批结果：已于 2026-03-10 10:04 CST 完成审批。
- 下游状态：可进入 `$jjk-plan`。
