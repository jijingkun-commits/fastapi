# 上下文工程收口澄清设计说明

## 1. scope_contract
- 目标:
  - 把当前“消息裁剪、工具结果压缩、system/skill 上下注入分散处理”的状态，收敛为单一的上下文工程入口。
  - 保证所有实际进入模型的内容都能被统一预算、统一裁剪、统一观测，不再出现“trim 后又注入大段文本导致预算失真”。
  - 将 `SUPERVISOR_PROMPT` 与 tool schema / tool descriptions 也纳入 token 账本，避免只盯 `messages` 导致误判大头来源。
  - 对齐最新 `master`：沿用“router blocked / replay recovery 结果式收口，不再向 `system_context` 注入自然语言补齐提示”的现实语义。
  - 冻结一套可直接进入 `/jjk-plan` 的单方案设计，避免继续在 `multi_agent_graph.py` 中追加局部 helper 和局部补丁。
- 范围:
  - 后端编排：`app/ai/workflow/multi_agent_graph.py`
  - LLM 入口：`app/ai/llm_util.py`、`app/services/llm_scene_service.py`、`app/services/llm_config_service.py`
  - 上下文来源：`app/services/skill_service.py`、`app/services/response_policy_service.py`、`app/ai/state.py`
  - 测试与文档：`tests/unit/test_multi_agent_context_budget.py`、`tests/unit/test_multi_agent_streaming_helpers.py`、相关设计/测试文档
- 边界:
  - 不切换当前多智能体主架构（保留手写 LangGraph + `create_react_agent` 主链）。
  - 不把完整历史从 checkpoint 中删除或改写为摘要真相源。
  - 不在本轮引入第二套并行 prompt 管道，不新增“临时兼容层 builder”。
  - 不在编排层新增关键词词表、substring 语义裁剪规则。
- 成功标准:
  - 任意一次 Supervisor / Agent 调模型前，都能输出统一的上下文预算账本。
  - `messages + system_context + skill_catalog + loaded_skills + prompt + tool_schema` 被统一纳入单次调用预算。
  - `delivery_meta.context_budget_ledger` 至少能区分 `prompt_token_estimate`、`tool_schema_token_estimate`、`message_token_estimate` 与各类动态上下文消耗。
  - 老历史仍由 checkpointer 保存；推理态输入由统一 builder 临时生成。
  - 仅在统一预算后仍证据不足时，才进入摘要记忆阶段。

## 2. product_contract（PRD-Lite）
- target_users:
  - AI 聊天终端用户
  - 后台模型/技能运营管理员
  - 负责排障与性能治理的开发者
- core_scenarios:
  - 长对话中，主对话仍能稳定回答，不被旧工具输出和技能正文淹没。
  - 多轮技能加载后，后续轮次仍能用到必要技能约束，但不再把整段技能正文无上限塞进 prompt。
  - 多轮知识检索、图表、SQL 后，Supervisor 仍能聚焦本轮任务，不被旧 ToolMessage 污染。
  - replay recovery / router blocked 场景继续采用结果式用户可见收口，不回退到 `system_context` 自然语言补齐提示。
- business_goals（含可量化 KPI）:
  - 长对话场景下，模型调用前上下文超预算率下降到可观测且可解释（预算账本覆盖率 100%）。
  - 主对话场景中，因历史上下文噪音导致的错误路由/答非所问问题可定位，不再出现“为什么爆了但看不出来”的黑箱。
  - `loaded_skill_context` 与 `skill_catalog_context` 的 token 消耗具备分项观测，便于后续将高成本上下文削减至少 30%（以日志样本为基线）。
  - `SUPERVISOR_PROMPT` 与 tool schema 的 token 消耗具备独立分项观测，避免把固定 prompt/tool 成本误判为对话历史问题。
- non_goals:
  - 本轮不更换模型供应商，不重做后台 LLM 管理台。
  - 本轮不直接引入长期记忆向量库新能力。
  - 本轮不把整个系统切换到官方 `create_supervisor` 或全量 `middleware` 框架。
- acceptance_gates:
  - 统一 builder 成为单一上下文装配入口。
  - `loaded_skill_registry` 成为技能正文回放唯一真相源，`loaded_skill_context` 不再作为直接注入真相源。
  - 旧 ToolMessage 的保留策略可预测、可测试、可观测。
  - 设计能够拆成明确实现任务原子，且不依赖额外模糊决策。
- release_constraints:
  - 项目未上线，优先结构收敛与简单设计，不以兼容旧临时行为为优先。
  - 如果需要回退，只允许短期 feature anchor；稳定后必须删除，不得长期保留双轨逻辑。

## 3. architecture_contract

### 3.1 模块边界
- 当前问题:
  - `ToolMessage` 压缩、`trim_messages`、`system_context / skill_catalog_context / loaded_skill_context` 注入分散在 graph 与 service 之间，真正送给模型的输入没有单一真相源。
- 最终决策:
  - 新增独立模块 `app/ai/context_engineering.py` 作为唯一上下文装配入口，导出 `build_llm_input_context(...)`。
  - `multi_agent_graph` 只负责调用该 builder，不再自己维护预算拆分和注入顺序。
  - `skill_service` 负责提供结构化技能来源（manifest / registry），不负责决定最终 prompt 形态。
  - `response_policy_service` 继续负责生成系统策略文本，但最终是否注入、注入多少由 context builder 决定。
  - `context_engineering` 还负责汇总固定 `prompt` 与 tool schema 的 token 成本，并在需要时收敛本轮可见工具集。
- 禁止动作:
  - 禁止继续在 `multi_agent_graph.py` 新增私有上下文拼装 helper。
  - 禁止在 `app/services/**` 直接拼“最终要发给模型的大段文本”并绕过预算入口。

### 3.2 依赖方向
- 当前问题:
  - 预算逻辑依赖 `messages`，但 `system/skill` 上下文在 trim 后追加，形成反向穿透。
- 最终决策:
  - 依赖方向固定为：
    1. `LLMSceneService / LLMConfigService` 提供当前场景模型配置（含 `context_window`）
    2. `response_policy_service / skill_service / state` 提供上下文来源
    3. `context_engineering` 统一组装 `llm_input_messages`，并统计 `prompt/tool_schema/context_messages` 的分项 token
    4. `multi_agent_graph` / `create_react_agent` 只消费 builder 产物
  - 预算计算优先使用场景模型的 `context_window`，`MESSAGE_MAX_TOKENS` 仅作安全上限与无配置兜底，不再作为唯一预算源。
- 禁止动作:
  - 禁止由 service 层直接决定 prompt 预算。
  - 禁止 graph 在 builder 之后再次追加无预算约束的上下文。

### 3.3 状态归属
- 当前问题:
  - 完整历史保存在 checkpointer，但推理态输入、技能正文缓存、诊断字段的 owner 不清晰。
- 最终决策:
  - `checkpointer`：完整会话原始历史唯一真相源。
  - `messages`：当前会话原始消息状态，不在 Phase A 被直接摘要覆盖。
  - `skill_catalog_manifest`：技能目录的唯一结构化来源。
  - `loaded_skill_registry`：已加载技能正文的唯一结构化来源。
  - `loaded_skill_context`：降级为可选派生缓存，不再作为直接注入真相源。
  - `delivery_meta.context_budget_ledger`：本次调用的预算诊断唯一真相源，必须包含 `prompt/tool_schema/system/skills/messages/total` 分项。
  - `additional_kwargs.context_runtime`：未来若落地摘要/压缩产物时的消息级 canonical 字段。
- 禁止动作:
  - 禁止把压缩后的消息列表写回为长期历史真相源。
  - 禁止继续依赖 `loaded_skill_context` 文本回放技能版本。

### 3.4 错误处理责任
- 当前问题:
  - ToolMessage 压缩失败会回退原消息，但 system/skill 上下文过大时没有统一降级责任层。
  - 最新 `master` 已把 router blocked / replay recovery 的自然语言补齐提示从 `system_context` 中移除，改为结果式用户可见收口；设计必须沿用这条新语义，避免重新把补齐提示塞回系统上下文。
- 最终决策:
  - `context_engineering` 统一负责：预算不足判定、裁剪、降级、打点。
  - 上游 service 只负责提供源数据，不兜底 prompt 超长问题。
  - replay recovery / router blocked 的用户可见阻塞说明继续走结果式 AI 消息，不回退到 `system_context` 注入。
  - 模型调用失败不再触发第二轮“再拼一次 prompt 试试”的隐式 fallback。
- 禁止动作:
  - 禁止在多处散落“截断一下再试”的补丁分支。
  - 禁止把预算问题下沉到 provider 调用层解决。
  - 禁止恢复旧式 `【交付补齐提示】` system_context 注入路径。

### 3.5 端到端数据流
1. `chat_service` / graph 按 `scene_key` 解析当前模型。
2. `LLMSceneService` 返回场景模型代码，`LLMConfigService` 返回模型 `provider_code/context_window`。
3. `context_engineering.build_llm_input_context(...)` 收集：
   - 固定 `prompt` 模板（如 `SUPERVISOR_PROMPT`）
   - 本轮可见 tool definitions / schema
   - 原始 `messages`
   - `system_context`（仅保留运行时核心约束；不承载 router blocked / replay recovery 自然语言补齐提示）
   - `skill_catalog_manifest` 或其派生摘要
   - `loaded_skill_registry` 派生的技能摘要
4. builder 先估算 `prompt/tool_schema` 成本，再做工具结果筛选与压缩、动态上下文预算分配，输出：
   - `llm_input_messages`
   - `context_budget_ledger`
   - `context_runtime_flags`
   - `selected_tools_for_turn`
5. `multi_agent_graph` 将 `llm_input_messages` 交给 agent 推理，并把账本写入 `delivery_meta`；agent 创建阶段消费 `selected_tools_for_turn`。
6. router blocked / replay recovery 的用户可见阻塞说明继续由结果式 AI 消息或结果事件承担，不再作为 `system_context` 的膨胀来源。
6. 若后续引入摘要消息，统一通过 `additional_kwargs.context_runtime` 回放与恢复。

### 3.6 状态生命周期
- 原始状态:
  - `messages` 累积于 thread/checkpointer。
  - `skill_catalog_manifest` 按轮重建。
  - `loaded_skill_registry` 按会话累积。
- 推理态状态:
  - builder 每次按当前场景和预算临时生成 `llm_input_messages`。
  - 该输入不回写为长期状态。
- 观测状态:
  - `delivery_meta.context_budget_ledger` 记录分项消耗，至少包括：`prompt_token_estimate`、`tool_schema_token_estimate`、`system_token_estimate`、`skill_catalog_token_estimate`、`loaded_skill_token_estimate`、`message_token_estimate`、`total_token_estimate_before_send`。
  - 如有合成摘要消息，消息自身携带 `additional_kwargs.context_runtime`。

### 3.7 异常语义与降级策略
- 统一异常语义:
  - **预算不足时只做一种策略**：优先削减低优先级上下文（冗余 tool schema -> 旧 ToolMessage -> loaded skills 正文 -> skill catalog -> 历史消息 -> 非核心运行时系统提示），而不是“裁消息”和“裁 system/skill”并存无规则。
- 具体降级顺序:
  1. 先按本轮目标缩减可见工具集，减少 tool schema token；核心 handoff 工具与必需工具保留，非必需工具退出本轮。
  2. 清旧 ToolMessage 原文，仅保留最近成功结果摘要与必要错误信息。
  3. `loaded_skill_registry` 渲染为“技能名 + 用途 + 必要约束”摘要，禁止默认拼全文。
  4. `skill_catalog_manifest` 仅保留用户本轮可见且高相关的技能目录摘要。
  5. 历史消息使用 `trim_messages` 做最近窗口裁剪。
  6. 若以上仍超预算，再裁减非核心运行时 system augment（保留核心系统约束；router blocked / replay recovery 提示已不在这里，不再作为裁剪对象）。
  7. 若以上仍超预算，再进入摘要阶段（Phase B）。
- 错误可观测性:
  - 任一上下文来源被裁剪时，必须写入 ledger 与日志。
  - 若技能版本回源失败，统一记录 `replay_source=rehydrated` 与缺失告警，不伪造正文。
  - 若命中 replay recovery / router blocked，必须记录其结果式收口路径，避免后续误判为 system_context 膨胀。

## 4. 最终方案
- 方案描述:
  - 采用“**模型感知预算 + 单一 pre-model context builder + prompt/tool token 账本 + 工具结果优先去噪 + 延迟摘要**”的单方案。
  - 保留当前手写 LangGraph 主链，不切全量官方框架；但严格对齐官方 `pre_model_hook / context engineering` 思路，把所有模型输入在调用前统一构造。
  - 对齐最新 `master`：replay recovery / router blocked 继续走结果式收口，不回退到 `system_context` 自然语言补齐提示。
  - 第一阶段不直接引入 `SummarizationMiddleware`；先把预算闭环、prompt/tool schema 观测和 ToolMessage 治理收好。只有在统一预算后仍有质量/成本问题，再进入摘要阶段。
- 关键决策:
  - 决策1：预算以 **场景绑定模型的 `context_window`** 为主，环境变量上限为辅。
  - 决策2：`loaded_skill_registry` 是技能正文的唯一真相源，`loaded_skill_context` 不再直接注入。
  - 决策3：旧 ToolMessage 优先清理与摘要，不再单靠首尾截断硬顶。
  - 决策4：统一 builder 输出 `delivery_meta.context_budget_ledger`，让“为什么超长/裁了什么”变成可观测事实。
  - 决策5：`SUPERVISOR_PROMPT` 与 tool schema 是一等预算项，必须单独计量，不再默认并入“系统上下文成本”。
  - 决策6：摘要是第二阶段能力，不作为本轮主修复。

## 5. 决策权衡（仅放弃原因）
- 放弃路径:
  - 继续维持当前做法：trim messages 后再拼 `system_context / loaded_skill_context`。
- 放弃原因:
  - 预算不闭环，无法解释实际输入成本；长对话和多技能场景下会继续失控。
- 放弃路径:
  - 先把 `MESSAGE_MAX_TOKENS` 调大/调小，观察效果。
- 放弃原因:
  - 这是表层调参，不解决“谁进入 prompt、按什么顺序被删”的根因。
- 放弃路径:
  - 立刻切换到官方 `create_supervisor` + 全量 built-in middleware。
- 放弃原因:
  - 当前项目是手写多智能体主链，直接切栈改动过大，和“设计简洁、渐进收敛”目标冲突。
- 放弃路径:
  - 先上摘要中间件，老历史直接汇总替换。
- 放弃原因:
  - 在工具结果和技能正文仍大量污染上下文时，摘要会掩盖根因，调试更难。

## 6. requirement_seeds（字段级需求原子）
```yaml
requirement_seeds:
  - design_item: D-01
    fr_id: FR-CONTEXT-BUDGET-MODEL-AWARE
    trigger: 任意 Supervisor / Agent 模型调用前
    input_contract:
      required_fields: [scene_key, messages, prompt_template, tool_definitions]
      optional_fields: [model_id, system_context, skill_catalog_manifest, loaded_skill_registry]
      defaults:
        model_id: ""
    output_contract:
      required_fields: [llm_input_messages, context_budget_ledger]
      optional_fields: [context_runtime_flags, selected_tools_for_turn]
    failure_semantics: 无法解析场景模型时回退到环境变量预算上限，并记录 fallback 来源
    observability_fields: [scene_key, model_code, provider_code, context_window, token_budget, prompt_token_estimate, tool_schema_token_estimate]
    rollback_anchor: ENABLE_CONTEXT_BUILDER_V1=false
    acceptance_cmd_ref: bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_context_budget.py tests/unit/test_multi_agent_streaming_helpers.py

  - design_item: D-02
    fr_id: FR-TOOL-CONTEXT-EDITING
    trigger: 会话包含 ToolMessage 或本轮可见工具集过大且准备进入下一次推理
    input_contract:
      required_fields: [messages, tool_definitions]
      optional_fields: [tool_context_policy, tool_budget_policy]
      defaults: {}
    output_contract:
      required_fields: [edited_messages]
      optional_fields: [tool_compaction_stats, selected_tools_for_turn, tool_schema_token_estimate]
    failure_semantics: 上下文编辑失败时回退到现有压缩策略，并明确记录 fallback 原因
    observability_fields: [tool_message_count, truncated_tool_message_count, removed_tool_message_count, selected_tool_count, tool_schema_token_estimate]
    rollback_anchor: ENABLE_TOOL_CONTEXT_EDIT_V1=false
    acceptance_cmd_ref: bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py

  - design_item: D-03
    fr_id: FR-SKILL-CONTEXT-CANONICALIZATION
    trigger: 会话已加载技能且需要后续轮次复用
    input_contract:
      required_fields: [loaded_skill_registry]
      optional_fields: [skill_catalog_manifest, loaded_skill_context]
      defaults: {}
    output_contract:
      required_fields: [budgeted_skill_context]
      optional_fields: [replay_source, missing_skills]
    failure_semantics: 版本回源失败时读旧写新，输出可观测降级提示，不直接拼接旧缓存全文
    observability_fields: [loaded_skill_count, missing_skill_count, loaded_skill_tokens]
    rollback_anchor: ENABLE_SKILL_CONTEXT_CANONICAL_V1=false
    acceptance_cmd_ref: bash scripts/pytest_targeted.sh app/tests/test_skill_loader_tool.py tests/unit/test_multi_agent_streaming_helpers.py

  - design_item: D-04
    fr_id: FR-CONTEXT-SUMMARY-PHASE-B
    trigger: 统一预算后仍超阈值或长会话质量下降
    input_contract:
      required_fields: [messages, context_budget_ledger]
      optional_fields: [summary_policy]
      defaults: {}
    output_contract:
      required_fields: [summary_message_or_summary_state]
      optional_fields: [context_runtime]
    failure_semantics: 摘要失败时保留当前 builder 路径，不阻断主回答
    observability_fields: [summary_trigger_reason, summary_chars_before, summary_chars_after]
    rollback_anchor: ENABLE_CONTEXT_SUMMARY_V1=false
    acceptance_cmd_ref: bash scripts/pytest_targeted.sh tests/unit/test_context_summary_builder.py
```

## 7. implementation_seeds（轻量任务原子）
```yaml
implementation_seeds:
  - task_id: T-01
    feature_id: P1-context-builder
    blocked_by: []
    file_paths:
      - app/ai/context_engineering.py
      - app/ai/workflow/multi_agent_graph.py
      - tests/unit/test_multi_agent_context_budget.py
      - tests/unit/test_multi_agent_streaming_helpers.py
    symbols:
      - build_llm_input_context
      - ContextBudgetLedger
      - _prepare_streaming_inference_state
    change_type: create_or_modify

  - task_id: T-02
    feature_id: P1-model-aware-budget
    blocked_by: [T-01]
    file_paths:
      - app/ai/llm_util.py
      - app/services/llm_scene_service.py
      - app/services/llm_config_service.py
      - app/ai/context_engineering.py
      - app/ai/workflow/multi_agent_graph.py
    symbols:
      - get_scene_llm
      - resolve_model_code
      - get_model_config
      - resolve_context_window_budget
      - SUPERVISOR_PROMPT
      - _get_supervisor_tools
    change_type: modify

  - task_id: T-03
    feature_id: P1-tool-context-editing
    blocked_by: [T-01]
    file_paths:
      - app/ai/context_engineering.py
      - app/ai/workflow/multi_agent_graph.py
      - tests/unit/test_multi_agent_streaming_helpers.py
    symbols:
      - edit_tool_messages_for_context
      - build_retrieval_digest
      - _compact_tool_message_for_inference
    change_type: modify

  - task_id: T-04
    feature_id: P1-skill-context-canonical
    blocked_by: [T-01]
    file_paths:
      - app/services/skill_service.py
      - app/ai/state.py
      - app/ai/context_engineering.py
      - app/tests/test_skill_loader_tool.py
    symbols:
      - build_loaded_skill_context_from_registry
      - loaded_skill_registry
      - loaded_skill_context
      - additional_kwargs.context_runtime
    change_type: modify

  - task_id: T-05
    feature_id: P1-doc-and-observability
    blocked_by: [T-01, T-02, T-03, T-04]
    file_paths:
      - docs/开发文档/测试管理/测试报告/README.md
      - workdocs/归档/正文/设计/2026-03-10-context-engineering-unification-design.md
      - app/ai/context_engineering.py
      - tests/unit/test_multi_agent_context_budget.py
    symbols:
      - context_budget_ledger
      - delivery_meta.context_budget_ledger
    change_type: modify
```

## 8. execution_chain_seed
```yaml
execution_chain_seed:
  preferred_mode: core
  task_key: PP-20260310-context-engineering-unification
  card_seed:
    - T-01
    - T-02
    - T-03
    - T-04
    - T-05
  execution_contract_hint:
    delivery_mode: staged
    execution_unit: all_tasks
    commit_policy: single_commit
    stop_boundary: none
```

## 9. risk_rollback_contract
- 关键风险（>=2）:
  - R-01：统一 builder 改变 system/skill 注入顺序，导致回答风格或工具选择发生回归。
    - 反例：之前依赖全文技能正文的场景，在摘要化后不再触发正确技能。
  - R-02：模型感知预算读取失败，预算回退到环境变量上限，导致不同场景表现不一致。
    - 反例：后台已切换到大窗口模型，但 builder 仍按旧上限裁剪。
  - R-03：ToolMessage 清理过猛，丢失本轮仍需依赖的工具结果。
    - 反例：上一轮检索结果中的引用 ID 未保留，导致本轮无法继续引用证据。
  - R-04：`loaded_skill_context` 降级后，历史回放链路仍有旧字段读取依赖。
    - 反例：刷新页面后只剩旧缓存文本，registry 回源未接通，技能约束消失。
  - R-05：实现上下文收口时错误恢复旧式 `system_context` 补齐提示，和最新 `master` 的结果式收口语义冲突。
    - 反例：router blocked 再次把 `【交付补齐提示】` 注入 prompt，导致 token 膨胀和用户可见文案双写。
- 回退锚点（默认开关 true，回退 false）:
  - `ENABLE_CONTEXT_BUILDER_V1=true`
  - `ENABLE_TOOL_CONTEXT_EDIT_V1=true`
  - `ENABLE_SKILL_CONTEXT_CANONICAL_V1=true`
  - `ENABLE_CONTEXT_SUMMARY_V1=true`
- 回退策略:
  - 若 P1 builder 回退：切回现有 `_prepare_streaming_inference_state` 路径，但保留日志账本字段，便于继续比对。
  - 若 ToolMessage 清理回退：仅回退到现有首尾截断策略，不恢复多处散落拼装。
  - 若技能正文 canonical 化回退：允许短期读取旧 `loaded_skill_context`，但必须保留 registry 作为最终真相源。

## 10. 最佳实践对齐结论（官方）
- 对齐来源:
  - LangChain 官方 `Context engineering`：强调单次调用前统一构造输入，而不是只裁消息。
  - LangChain 官方 `Built-in middleware`：推荐用中间件/预模型阶段处理上下文编辑、摘要、模型选择。
  - LangChain 官方 `Short-term memory`：强调线程状态保留与模型输入分离。
  - LangGraph Supervisor 参考：主控只消费必要上下文，默认不把子链全量过程当作主 prompt。
- 本方案吸收的实践:
  - 吸收“pre-model 统一装配”而非“节点内分散裁剪”。
  - 吸收“工具上下文优先去噪”而非“一上来就摘要全部历史”。
  - 吸收“完整历史持久化，推理态输入临时生成”的状态分层。
- 明确不直接照搬的实践:
  - 不直接切换到官方整套 `middleware`/`create_supervisor`，因为当前项目主链是手写 Graph，切栈成本高。
  - 不先上 Prompt Caching/Anthropic 专属优化，因为当前设计目标是 provider-agnostic 的上下文治理。

## 11. 设计冻结回执（机读）
```yaml
design_freeze_summary:
  design_actionable: true
  missing_blocks: []
  risk_level: medium
  risk_counterexamples_count: 5
  handoff_contract_ready: true
  product_contract_ready: true
  implementation_seed_count: 5
  semantic_frozen: true
  contract_source_decided: true
  handoff_seed_alignment_ok: true
  parallel_dependency_ready: true
  replay_canonical_field_set: true
  blocking_issues: []
```

## 12. 承接契约（机读）
```yaml
clarify_handoff_contract:
  version: v2
  topic: "context-engineering-unification"
  design_source: "workdocs/归档/正文/设计/2026-03-10-context-engineering-unification-design.md"
  handoff_ready: true
  required:
    product_contract_summary:
      target_users:
        - AI 聊天终端用户
        - 后台模型/技能运营管理员
        - 排障开发者
      core_scenarios:
        - 长对话中主对话稳定回答
        - 多轮技能加载后按需复用必要约束
        - 多轮工具调用后主控不被旧工具结果污染
      business_goal_metrics:
        - 预算账本覆盖率 100%
        - prompt/tool/schema/skill/system 分项 token 可观测
        - 高成本技能上下文可削减至少 30%
      non_goals:
        - 不更换模型供应商
        - 不切换整体 Graph 框架
        - 不直接引入向量长期记忆新能力
      acceptance_gates:
        - 单一 builder 成为唯一上下文装配入口
        - loaded_skill_registry 成为技能正文唯一真相源
        - ToolMessage 保留策略可测试可观测
    requirement_seeds:
      - design_item: D-01
        fr_id: FR-CONTEXT-BUDGET-MODEL-AWARE
        trigger: 任意 Supervisor / Agent 模型调用前
        input_contract:
          required_fields: [scene_key, messages, prompt_template, tool_definitions]
          optional_fields: [model_id, system_context, skill_catalog_manifest, loaded_skill_registry]
          defaults:
            model_id: ""
        output_contract:
          required_fields: [llm_input_messages, context_budget_ledger]
          optional_fields: [context_runtime_flags, selected_tools_for_turn]
        failure_semantics: 无法解析场景模型时回退到环境变量预算上限，并记录 fallback 来源
        observability_fields: [scene_key, model_code, provider_code, context_window, token_budget, prompt_token_estimate, tool_schema_token_estimate]
        rollback_anchor: ENABLE_CONTEXT_BUILDER_V1=false
        acceptance_cmd_ref: bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_context_budget.py tests/unit/test_multi_agent_streaming_helpers.py
      - design_item: D-02
        fr_id: FR-TOOL-CONTEXT-EDITING
        trigger: 会话包含 ToolMessage 或本轮可见工具集过大且准备进入下一次推理
        input_contract:
          required_fields: [messages, tool_definitions]
          optional_fields: [tool_context_policy, tool_budget_policy]
          defaults: {}
        output_contract:
          required_fields: [edited_messages]
          optional_fields: [tool_compaction_stats, selected_tools_for_turn, tool_schema_token_estimate]
        failure_semantics: 上下文编辑失败时回退到现有压缩策略，并明确记录 fallback 原因
        observability_fields: [tool_message_count, truncated_tool_message_count, removed_tool_message_count, selected_tool_count, tool_schema_token_estimate]
        rollback_anchor: ENABLE_TOOL_CONTEXT_EDIT_V1=false
        acceptance_cmd_ref: bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py
      - design_item: D-03
        fr_id: FR-SKILL-CONTEXT-CANONICALIZATION
        trigger: 会话已加载技能且需要后续轮次复用
        input_contract:
          required_fields: [loaded_skill_registry]
          optional_fields: [skill_catalog_manifest, loaded_skill_context]
          defaults: {}
        output_contract:
          required_fields: [budgeted_skill_context]
          optional_fields: [replay_source, missing_skills]
        failure_semantics: 版本回源失败时读旧写新，输出可观测降级提示，不直接拼接旧缓存全文
        observability_fields: [loaded_skill_count, missing_skill_count, loaded_skill_tokens]
        rollback_anchor: ENABLE_SKILL_CONTEXT_CANONICAL_V1=false
        acceptance_cmd_ref: bash scripts/pytest_targeted.sh app/tests/test_skill_loader_tool.py tests/unit/test_multi_agent_streaming_helpers.py
      - design_item: D-04
        fr_id: FR-CONTEXT-SUMMARY-PHASE-B
        trigger: 统一预算后仍超阈值或长会话质量下降
        input_contract:
          required_fields: [messages, context_budget_ledger]
          optional_fields: [summary_policy]
          defaults: {}
        output_contract:
          required_fields: [summary_message_or_summary_state]
          optional_fields: [context_runtime]
        failure_semantics: 摘要失败时保留当前 builder 路径，不阻断主回答
        observability_fields: [summary_trigger_reason, summary_chars_before, summary_chars_after]
        rollback_anchor: ENABLE_CONTEXT_SUMMARY_V1=false
        acceptance_cmd_ref: bash scripts/pytest_targeted.sh tests/unit/test_context_summary_builder.py
    implementation_seeds:
      - task_id: T-01
        feature_id: P1-context-builder
        blocked_by: []
        file_paths:
          - app/ai/context_engineering.py
          - app/ai/workflow/multi_agent_graph.py
          - tests/unit/test_multi_agent_context_budget.py
          - tests/unit/test_multi_agent_streaming_helpers.py
        symbols:
          - build_llm_input_context
          - ContextBudgetLedger
          - _prepare_streaming_inference_state
        change_type: create_or_modify
      - task_id: T-02
        feature_id: P1-model-aware-budget
        blocked_by: [T-01]
        file_paths:
          - app/ai/llm_util.py
          - app/services/llm_scene_service.py
          - app/services/llm_config_service.py
          - app/ai/context_engineering.py
        symbols:
          - get_scene_llm
          - resolve_model_code
          - get_model_config
          - resolve_context_window_budget
        change_type: modify
      - task_id: T-03
        feature_id: P1-tool-context-editing
        blocked_by: [T-01]
        file_paths:
          - app/ai/context_engineering.py
          - app/ai/workflow/multi_agent_graph.py
          - tests/unit/test_multi_agent_streaming_helpers.py
        symbols:
          - edit_tool_messages_for_context
          - build_retrieval_digest
          - _compact_tool_message_for_inference
        change_type: modify
      - task_id: T-04
        feature_id: P1-skill-context-canonical
        blocked_by: [T-01]
        file_paths:
          - app/services/skill_service.py
          - app/ai/state.py
          - app/ai/context_engineering.py
          - app/tests/test_skill_loader_tool.py
        symbols:
          - build_loaded_skill_context_from_registry
          - loaded_skill_registry
          - loaded_skill_context
          - additional_kwargs.context_runtime
        change_type: modify
      - task_id: T-05
        feature_id: P1-doc-and-observability
        blocked_by: [T-01, T-02, T-03, T-04]
        file_paths:
          - docs/开发文档/测试管理/测试报告/README.md
          - workdocs/归档/正文/设计/2026-03-10-context-engineering-unification-design.md
          - app/ai/context_engineering.py
          - tests/unit/test_multi_agent_context_budget.py
        symbols:
          - context_budget_ledger
          - delivery_meta.context_budget_ledger
        change_type: modify
    execution_chain_seed:
      preferred_mode: core
      task_key: PP-20260310-context-engineering-unification
      card_seed: [T-01, T-02, T-03, T-04, T-05]
      execution_contract_hint:
        delivery_mode: staged
        execution_unit: all_tasks
        commit_policy: single_commit
        stop_boundary: none
    alignment_contract:
      strict_match: true
      requirement_seed_ids: [D-01, D-02, D-03, D-04]
      implementation_task_ids: [T-01, T-02, T-03, T-04, T-05]
      card_seed_ids: [T-01, T-02, T-03, T-04, T-05]
  extended:
    observability_hints:
      - 将 `delivery_meta.context_budget_ledger` 与场景模型信息一起落日志
      - 对 skill/system/history/tool 四类上下文分别记录 token 估算
      - 记录 fallback 来源，避免预算失真黑箱
    risk_counterexample_map:
      - risk_id: R-01
        counterexample: 技能摘要化后未命中原本依赖全文正文的路由场景
        verify_cmd: bash scripts/pytest_targeted.sh app/tests/test_skill_loader_tool.py tests/unit/test_multi_agent_streaming_helpers.py
      - risk_id: R-02
        counterexample: 场景模型切换后 context_window 未更新，仍按旧预算裁剪
        verify_cmd: bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_context_budget.py
      - risk_id: R-03
        counterexample: 清理 ToolMessage 后丢失引用证据，导致下一轮回答失真
        verify_cmd: bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py
      - risk_id: R-04
        counterexample: 历史回放只剩旧 `loaded_skill_context`，registry 回源失败
        verify_cmd: bash scripts/pytest_targeted.sh app/tests/test_skill_loader_tool.py
      - risk_id: R-05
        counterexample: router blocked / replay recovery 被重新塞回 `system_context`，与最新 master 的结果式收口语义冲突
        verify_cmd: bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_response_policy_service.py
    assumptions:
      - 当前后台模型路由表是实际生效入口，环境变量 provider 仅作兜底
      - `response_policy_service` 仍可在 Phase A 继续输出文本型 system_context，但不再承载 router blocked / replay recovery 自然语言补齐提示
      - 最新 `master` 已将 replay recovery / router blocked 收口为结果式用户可见消息，本设计沿用该语义
      - 摘要阶段可延后到 Phase B，不影响 Phase A 上下文收口
```

## 13. 一致性自检（机读）
```yaml
clarify_consistency_check:
  clarify_phase: approval
  current_round: 3
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

## 14. 外部参考
- LangChain Context engineering: https://docs.langchain.com/oss/python/langchain/context-engineering
- LangChain Built-in middleware: https://docs.langchain.com/oss/python/langchain/middleware/built-in
- LangChain Short-term memory: https://docs.langchain.com/oss/python/langchain/short-term-memory
- LangGraph Supervisor reference: https://reference.langchain.com/python/langgraph-supervisor/supervisor/create_supervisor
- Anthropic Long context prompting: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/long-context-tips


## 15. 审批记录
- design_approved: true
- approved_at: 2026-03-11 18:26
- approved_round: 3
- approval_evidence: 确认
- approval_mode: approved
- go_no_go: GO
- blocking_issues: []
