# LangGraph v1 升级与 Agent API 收敛设计

> **文档类型**: 设计说明  
> **创建日期**: 2026-03-09  
> **更新日期**: 2026-03-09  
> **状态**: 已审批（`$jjk-plan` 输入基线）  
> **范围**: `pyproject.toml`, `requirements.txt`, `app/ai/workflow/multi_agent_graph.py`, `app/ai/agents/knowledge_agent.py`, `app/services/chat_service.py`, `app/db/postgres_checkpoint.py`

---

## 1. scope_contract
- 目标:
  - 将仓库后端 `LangGraph` 依赖收敛到官方当前稳定线 `1.0.10`，停止 `pyproject.toml` 与 `requirements.txt` 的版本漂移。
  - 按官方 v1 迁移指南，把生产路径中的 `create_react_agent` 收敛到 `create_agent`，避免仓内继续混用两套 Agent 入口。
  - 冻结多智能体图在 `interrupt / Command(resume=...) / subgraph persistence` 相关区域的最佳实践落点，后续实现时优先删减手工兜底逻辑，而不是继续叠兼容层。
- 范围:
  - Python 后端 `LangGraph` 版本与安装契约。
  - 生产路径中的预构建 Agent 构建入口：`supervisor`、`knowledge_agent`、相关测试与示例对齐。
  - `streaming wrapper` 依赖的 `agent.astream(..., stream_mode=["messages", "values", "custom"])` 契约。
  - 与迁移直接相关的图状态回读、子图持久化、消息回放 canonical 约束。
  - 设计文档与后续执行种子，不包含本轮业务实现。
- 边界:
  - 本轮不升级前端 `@langchain/langgraph` / `@langchain/langgraph-sdk`，因为当前前端主要消费 SDK 消息，不在 TS 侧自建图运行时。
  - 本轮不把现有 `StateGraph` 全面重写为 Functional API，仍以 Graph API 为唯一主路径。
  - 本轮 `create_agent` 收口仅针对预构建 Agent 入口，不替换 `create_todo_graph` / `create_data_graph` 这类 Graph factory。
  - 本轮不引入 `langgraph-supervisor` 作为新编排层；多智能体继续基于现有手工图与 tool/handoff 模式收敛。
  - 本轮不新增运行时兼容层、版本探测分支或双轨开关。
- 成功标准:
  - 后端 `LangGraph` 依赖源保持单版本一致，安装解析无漂移。
  - 生产代码中的 `create_react_agent` 使用点收敛为 0，统一走 `create_agent`。
  - `interrupt / resume / replay` 语义不变，且不新增消息顶层字段。
  - `streaming wrapper` 依赖的 `messages / values / custom` 三路分发契约保持可用。
  - 子图状态/消息预填充逻辑进入“可删除”治理范围，后续实现以净收敛为目标。

## 2. product_contract（PRD-Lite）
- target_users: AI 工作流维护者；后端开发者；QA / 验收人员。
- core_scenarios: 场景1，开发者升级依赖后，本地与 CI 安装出的 `LangGraph` 版本一致，不再出现两个真理源各写各的；场景2，`supervisor` 与 `knowledge_agent` 使用统一的 `create_agent` 入口，后续新增 Agent 不再纠结选哪套 API；场景3，用户执行需要确认的待办或工具链路时，`interrupt -> resume` 行为与当前一致，不因迁移破坏对话体验；场景4，多智能体子图回放与消息补发仍可工作，但允许在新版本能力确认后删除冗余手工回读逻辑。
- business_goals（含 KPI）: 依赖一致性，后端 `LangGraph` 版本漂移数 = 0（`pyproject.toml` 与 `requirements.txt` 完全一致）；API 一致性，生产路径 `create_react_agent` 引用数收敛到 0；运行稳定性，`interrupt / resume / replay` 定向回归通过率 = 100%；设计瘦身，迁移阶段禁止新增私有兼容 helper，后续实现以“删除或收敛现有兜底逻辑”为验收口径。
- non_goals: 本轮不做 LangGraph JS 运行时升级；本轮不做大图重写，不引入 Functional API 全量替换；本轮不新增多智能体产品能力，不改用户可见接口语义；本轮不把 `checkpointer busy` 通过新 fallback 吞掉，只允许继续定位和收敛根因。
- acceptance_gates: 版本升级后安装解析通过，且不引入新的依赖漂移；生产路径不再依赖 `create_react_agent`；`streaming wrapper` 仍能消费 `agent.astream(..., stream_mode=["messages", "values", "custom"])` 输出；`AIMessage` 的结构化运行时元数据仍只走 `additional_kwargs` 命名空间；任一实现步骤都不得引入“旧 API / 新 API 并存”的长期兼容层。
- release_constraints: 该方案先进入 `codex/langgraph` 分支实施，不在 `master` 直接落地；文档先行，计划与实现必须承接本设计文档，不允许另起一套口径；若迁移期出现不兼容，回退通过 Git 交付锚点完成，不额外引入运行时开关。

## 3. architecture_contract
- 模块边界与职责:
  - **依赖契约层**：`pyproject.toml`、`requirements.txt`
    - 只负责声明后端 Python 依赖与版本约束。
    - 不能把业务兼容性问题转嫁为松散版本范围。
  - **Agent 构建层**：`app/ai/workflow/multi_agent_graph.py`、`app/ai/agents/knowledge_agent.py`、`app/ai/agents/todo_agent.py`、`app/ai/middleware.py`
    - 只负责构建 Agent、注入工具、prompt/middleware 组合。
    - 预构建 Agent 入口统一收敛到 `create_agent`，并同步完成 `prompt -> system_prompt` 参数收口。
    - `create_todo_graph` / `create_data_graph` 继续作为 Graph factory，禁止把“统一 API”误做成“用 prebuilt agent 替掉子图”。
  - **图执行与持久化层**：`app/services/chat_service.py`、`app/db/postgres_checkpoint.py`
    - 负责 `interrupt`、`resume`、checkpoint、回放与流式事件。
    - 只处理图执行责任，不应为了旧 Agent API 再补桥接逻辑。
  - **消息回放/前端兼容层**：已有 `additional_kwargs` canonical 体系
    - 保持现有消息外形与 replay 语义。
    - 不新增顶层消息字段。
- 端到端数据流:
  1. 用户请求进入 `chat_service`。
  2. `chat_service` 获取编译后的图与 `checkpointer`。
  3. 图内部的 `supervisor / experts` 通过统一 Agent API 进行推理与 tool calling。
  4. `interrupt` 场景暂停图执行，状态落入 checkpoint。
  5. `Command(resume=...)` 恢复后继续走同一图语义，消息回放仍通过 `additional_kwargs` 相关字段归一。
- 状态生命周期:
  - `thread_id / run_id / checkpoint` 仍由 `LangGraph + AsyncPostgresSaver` 管理。
  - 业务状态 owner 不变：`MultiAgentState` / `TodoAgentState` 继续是图状态真理源。
  - 本方案冻结的 replay canonical 规则：
    - 现有结构化消息结果继续读 `AIMessage.additional_kwargs`。
    - 若迁移过程中需要新增 `LangGraph` 运行时结构化 trace，只允许写入 `AIMessage.additional_kwargs.langgraph_runtime`。
    - 历史字段如 `result_events`、`skill_runtime`、`router_result_v2` 继续可读；不新增新的顶层并存字段。
- 异常语义与降级策略:
  - 依赖解析失败：直接阻断交付，不以松版本范围掩盖。
  - Agent API 迁移失败：直接回退提交，不保留 `create_react_agent` 兼容桥。
  - `checkpointer busy`：保留现有统一错误处理责任，后续只允许做结构性收敛，不允许新增 fallback 层。
  - 子图状态回读：若新版持久化行为已足够，则以删除手工回读为目标；若证据不足，先保持现状，不猜测性删改。

## 4. 最终方案
- 方案描述:
  - 采用“**版本先对齐，API 再收口，最后清理冗余状态逻辑**”的单方案。
  - 该方案严格基于官方最佳实践冻结：
    1. 依赖线：Python `LangGraph` 收敛到 `1.0.10`；`requirements.txt` 与 `pyproject.toml` 不再各写各的。
    2. Agent 线：官方 v1 迁移文档已不再推荐 `create_react_agent`，因此生产路径统一迁移到 `create_agent`。
    3. 多智能体线：继续使用 Graph API + tool/handoff + subgraph，不引入 `langgraph-supervisor` 新层。
    4. 持久化线：利用 `1.0.9/1.0.10` 对 sequential interrupt handling、`ParentCommand` bubbling、subgraph persistence 的修复，评估删除现有手工补丁的可能性。
- 关键决策:
  - **决策1：Graph API 继续作为唯一主路径**
    - 理由：仓库已经深度依赖 `StateGraph`、子图、`interrupt` 与 `Command(PARENT/resume)`；此类复杂多智能体场景更适合继续使用 Graph API，而不是为“看起来更现代”强改成 Functional API。
  - **决策2：生产 Agent 统一到 `create_agent`**
    - 理由：仓内已经存在 `create_agent` 实践（如 `todo_agent` / middleware），继续混用旧入口只会增加维护面。
  - **决策3：暂不升级前端 LangGraph JS 包**
    - 理由：当前前端主要消费 SDK 消息与 UI 组件，不在 TS 侧自建 `StateGraph`，现在升级收益小、噪音大。
  - **决策4：不引入新兼容层，只做结构收敛**
    - 理由：项目未上线，优先删除历史负担，而不是为旧 API 续命。
  - **决策5：回放 canonical 字段冻结在 `additional_kwargs` 命名空间**
    - 理由：仓库已有 `result_events`、`skill_runtime`、`router_result_v2` 体系，继续加顶层字段会扩大回放复杂度。

### 4.1 代码分析补充
- `app/ai/workflow/multi_agent_graph.py:4792` 的 `_run_streaming_dispatch_loop` 强依赖 `agent.astream(..., stream_mode=["messages", "values", "custom"])`；所以迁移验收不能只看 agent 能否创建，还要看 wrapper 三路分发是否保持。
- `app/ai/workflow/multi_agent_graph.py:5966` 与 `app/ai/agents/knowledge_agent.py:56` 现在都还在用 `create_react_agent`，但 `app/ai/middleware.py:10` 与 `app/ai/examples/advanced_agent_demo.py:259` 已经采用 `create_agent + system_prompt`；这说明仓库已具备新 API 实践，缺的是统一，不是能力。
- `app/ai/agents/knowledge_agent.py:23` 仍把返回类型和注释绑定到 `CompiledStateGraph/create_react_agent`，迁移时要顺手把文档、类型提示和参数命名一并收口，否则代码已迁移、注释还停留在旧语义。
- `app/ai/agents/todo_agent.py:35` 目前已经存在 `use_graph=True/False` 双路径；后续迁移必须避免再扩散出第三条兼容路径。

## 5. 决策权衡（仅放弃原因）
- 放弃路径: 立即把所有图改成 Functional API
  - 放弃原因: 当前仓库的核心复杂度在多智能体图状态、handoff、checkpoint 与 replay，不在图定义语法。现在重写只会扩大变更面。
- 放弃路径: 引入 `langgraph-supervisor` 包替换现有 supervisor 图
  - 放弃原因: 现有仓库是深度定制的 supervisor 编排，直接替换会把“升级 LangGraph”变成“重做多智能体架构”。
- 放弃路径: 同步升级前端 `@langchain/langgraph*`
  - 放弃原因: 当前前端没有自建 TS 图运行时，收益不成比例。
- 放弃路径: 保留 `create_react_agent` 作为过渡兼容入口
  - 放弃原因: 会形成长期双轨，后续每次加 Agent 都要再判断一遍“该用哪套 API”。

## 6. requirement_seeds
- design_item: D-01
  fr_id: FR-LG-01
  trigger: 开发者安装依赖或 CI 初始化 Python 运行时
  input_contract:
    required_fields: [pyproject.toml, requirements.txt]
    optional_fields: [venv_path]
    defaults:
      venv_path: venv
  output_contract:
    required_fields: [langgraph_version, dependency_drift]
  failure_semantics: 解析失败即阻断交付；禁止通过放宽版本范围继续推进
  observability_fields: [langgraph_version, langchain_version, resolver_python]
  rollback_anchor: ENABLE_LANGGRAPH_1_0_10=true
  acceptance_cmd_ref: 先执行 `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/repo_python.sh` 获取解释器，再执行 `<python> -m pip install --dry-run 'langchain==1.0.8' 'langgraph==1.0.10' 'langchain-openai==1.0.3' 'langgraph-checkpoint-postgres>=2.0.0'`
- design_item: D-02
  fr_id: FR-LG-02
  trigger: 系统构建 `supervisor` 或 `knowledge_agent`
  input_contract:
    required_fields: [model, tools, prompt]
    optional_fields: [middleware, checkpointer]
    defaults:
      middleware: []
  output_contract:
    required_fields: [agent_api_mode, agent_name]
  failure_semantics: agent 构建失败直接阻断，不保留 `create_react_agent` fallback
  observability_fields: [agent_name, agent_api_mode, tool_count]
  rollback_anchor: ENABLE_CREATE_AGENT_MIGRATION=true
  acceptance_cmd_ref: bash scripts/pytest_targeted.sh app/tests/test_model_switch.py app/tests/test_complex_scenario.py -q
- design_item: D-03
  fr_id: FR-LG-03
  trigger: 图执行进入 `interrupt / resume / subgraph replay`
  input_contract:
    required_fields: [thread_id, run_id, checkpoint, messages]
    optional_fields: [user_id]
    defaults:
      user_id: null
  output_contract:
    required_fields: [resume_semantics_unchanged, replay_canonical_field]
  failure_semantics: 任何 replay 语义漂移都视为阻断；禁止通过新增消息顶层字段绕过
  observability_fields: [thread_id, run_id, checkpoint_backend, replay_canonical_field]
  rollback_anchor: ENABLE_LANGGRAPH_REPLAY_CANONICAL=true
  acceptance_cmd_ref: bash scripts/pytest_targeted.sh app/ai/test_stream_modes.py app/tests/test_complex_scenario.py -q
- design_item: D-04
  fr_id: FR-LG-04
  trigger: 迁移后评估现有子图状态预填充与 busy 兜底逻辑
  input_contract:
    required_fields: [subgraph_state_reader, emitted_message_registry]
    optional_fields: [busy_error_handler]
    defaults:
      busy_error_handler: current
  output_contract:
    required_fields: [cleanup_candidate_list, delete_or_keep_decision]
  failure_semantics: 若缺少证据，则保持现状；若有证据，则优先删除冗余逻辑
  observability_fields: [subgraph_state_read_count, busy_error_count, duplicate_emit_count]
  rollback_anchor: ENABLE_SUBGRAPH_PREFILL_CLEANUP=true
  acceptance_cmd_ref: bash scripts/pytest_targeted.sh app/tests/test_complex_scenario.py -q

## 7. implementation_seeds
- task_id: T-01
  feature_id: P1-langgraph-version-alignment
  blocked_by: []
  file_paths:
    - pyproject.toml
    - requirements.txt
  symbols:
    - project.dependencies.langgraph
    - requirements.langgraph
  change_type: modify
- task_id: T-02
  feature_id: P1-agent-api-convergence
  blocked_by: [T-01]
  file_paths:
    - app/ai/workflow/multi_agent_graph.py
    - app/ai/agents/knowledge_agent.py
    - app/ai/middleware.py
    - app/ai/agents/todo_agent.py
  symbols:
    - create_react_agent
    - create_agent
    - supervisor_agent
    - knowledge_agent
  change_type: modify
- task_id: T-03
  feature_id: P1-test-and-example-convergence
  blocked_by: [T-02]
  file_paths:
    - app/ai/test_stream_modes.py
    - app/ai/test_tool_calls.py
    - app/ai/examples/advanced_agent_demo.py
  symbols:
    - create_react_agent
    - create_agent
  change_type: modify
- task_id: T-04
  feature_id: P1-subgraph-persistence-cleanup
  blocked_by: [T-02]
  file_paths:
    - app/ai/workflow/multi_agent_graph.py
    - app/services/chat_service.py
    - app/db/postgres_checkpoint.py
  symbols:
    - agent.aget_state
    - graph.aget_state
    - is_checkpointer_busy_error
    - _record_emitted_message_id
  change_type: modify
- task_id: T-05
  feature_id: P1-docs-and-regression
  blocked_by: [T-01, T-02, T-03, T-04]
  file_paths:
    - workdocs/归档/正文/设计/2026-03-09-langgraph-v1-adoption-design.md
    - app/tests/test_complex_scenario.py
    - app/tests/test_model_switch.py
    - app/ai/test_stream_modes.py
  symbols:
    - design_freeze_summary
    - test_interrupt_resume
    - test_agent_build_path
  change_type: modify

## 8. execution_chain_seed
- preferred_mode: core
- task_key: PP-20260309-langgraph-v1-adoption
- card_seed:
  - T-01
  - T-02
  - T-03
  - T-04
  - T-05
- execution_contract_hint:
  - delivery_mode: staged
  - execution_unit: all_tasks
  - commit_policy: single_commit
  - stop_boundary: none

## 9. risk_rollback_contract
- 关键风险（>=2）:
  - risk_id: R-01
    risk: `create_agent` 替换后，`supervisor` 现有 tool/handoff 行为与旧入口不完全等价
    counterexample: `Command(graph=Command.PARENT)` 或 tool calling 语义变化，导致 handoff 链路断裂
    mitigation: 先做生产路径最小收口，再跑 `interrupt / resume / complex scenario` 定向回归
    rollback_anchor: ENABLE_CREATE_AGENT_MIGRATION=true
  - risk_id: R-02
    risk: 新版 subgraph persistence 行为与现有手工状态预填充逻辑叠加，反而造成重复消息或误判
    counterexample: 子图 checkpoint 已能恢复完整消息，但仓内仍再次预填充，导致重复 emit
    mitigation: 先加证据再删逻辑；不做猜测性清理
    rollback_anchor: ENABLE_SUBGRAPH_PREFILL_CLEANUP=true
  - risk_id: R-03
    risk: 迁移时新增结构化 trace 字段破坏前端回放或 SSE 对齐
    counterexample: 新增顶层字段后，前端 `message-normalizer` / replay 分支出现解析漂移
    mitigation: 统一约束“新增结构化元数据只写 `additional_kwargs.langgraph_runtime`”
    rollback_anchor: ENABLE_LANGGRAPH_REPLAY_CANONICAL=true
  - risk_id: R-04
    risk: `create_agent` 虽能创建 Agent，但 `_create_streaming_agent_wrapper` 依赖的 `astream(messages|values|custom)` 契约不完全等价
    counterexample: wrapper 只能收到部分模式，导致 tool_start / values 补发 / custom 事件分发错位
    mitigation: 固定跑 stream mode 契约回归；若不等价，直接阻断实现，不新增兼容层
    rollback_anchor: ENABLE_CREATE_AGENT_MIGRATION=true
- 回退锚点（默认开关 true，回退 false）:
  - ENABLE_LANGGRAPH_1_0_10=true
  - ENABLE_CREATE_AGENT_MIGRATION=true
  - ENABLE_LANGGRAPH_REPLAY_CANONICAL=true
  - ENABLE_SUBGRAPH_PREFILL_CLEANUP=true

## 10. 官方依据
- `LangGraph` v1 迁移指南：官方明确建议从 `langgraph.prebuilt.create_react_agent` 迁移到 `langchain.agents.create_agent`。
- `LangGraph` Release `1.0.9`：修复 sequential interrupt handling。
- `LangGraph` Release `1.0.10`：修复 `ParentCommand` bubbling 与 subgraph persistence 相关问题。
- 官方 Graph API / multi-agent 资料：复杂多智能体协调继续以 graph + handoff/tool 模式为主，而不是为了语法新旧强改运行形态。

## 11. 设计冻结回执（机读）
```yaml
design_freeze_summary:
  design_actionable: true
  missing_blocks: []
  risk_level: medium
  risk_counterexamples_count: 4
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
  topic: "langgraph-v1-adoption"
  design_source: workdocs/归档/正文/设计/2026-03-09-langgraph-v1-adoption-design.md
  handoff_ready: true
  required:
    product_contract_summary:
      target_users:
        - AI 工作流维护者
        - 后端开发者
        - QA / 验收人员
      core_scenarios:
        - 统一后端 LangGraph 版本
        - 统一生产 Agent API
        - 保持 interrupt/resume/replay 语义稳定
      business_goal_metrics:
        - 后端 LangGraph 版本漂移数=0
        - 生产路径 create_react_agent 引用数=0
        - interrupt/resume/replay 定向回归通过率=100%
      non_goals:
        - 不升级前端 LangGraph JS 运行时
        - 不做 Functional API 全量重写
        - 不引入 langgraph-supervisor 替换现有图
      acceptance_gates:
        - 版本安装解析通过且无漂移
        - 生产路径不再依赖 create_react_agent
        - 新增结构化元数据只写入 additional_kwargs 命名空间
    requirement_seeds:
      - design_item: D-01
        fr_id: FR-LG-01
        trigger: 开发者安装依赖或 CI 初始化 Python 运行时
        input_contract:
          required_fields: [pyproject.toml, requirements.txt]
          optional_fields: [venv_path]
          defaults:
            venv_path: venv
        output_contract:
          required_fields: [langgraph_version, dependency_drift]
        failure_semantics: 解析失败即阻断交付；禁止通过放宽版本范围继续推进
        observability_fields: [langgraph_version, langchain_version, resolver_python]
        rollback_anchor: ENABLE_LANGGRAPH_1_0_10=true
        acceptance_cmd_ref: 先执行 `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/repo_python.sh` 获取解释器，再执行 `<python> -m pip install --dry-run 'langchain==1.0.8' 'langgraph==1.0.10' 'langchain-openai==1.0.3' 'langgraph-checkpoint-postgres>=2.0.0'`
      - design_item: D-02
        fr_id: FR-LG-02
        trigger: 系统构建 supervisor 或 knowledge_agent
        input_contract:
          required_fields: [model, tools, prompt]
          optional_fields: [middleware, checkpointer]
          defaults:
            middleware: []
        output_contract:
          required_fields: [agent_api_mode, agent_name]
        failure_semantics: agent 构建失败直接阻断，不保留 create_react_agent fallback
        observability_fields: [agent_name, agent_api_mode, tool_count]
        rollback_anchor: ENABLE_CREATE_AGENT_MIGRATION=true
        acceptance_cmd_ref: bash scripts/pytest_targeted.sh app/tests/test_model_switch.py app/tests/test_complex_scenario.py -q
      - design_item: D-03
        fr_id: FR-LG-03
        trigger: 图执行进入 interrupt / resume / subgraph replay
        input_contract:
          required_fields: [thread_id, run_id, checkpoint, messages]
          optional_fields: [user_id]
          defaults:
            user_id: null
        output_contract:
          required_fields: [resume_semantics_unchanged, replay_canonical_field]
        failure_semantics: 任何 replay 语义漂移都视为阻断；禁止通过新增消息顶层字段绕过
        observability_fields: [thread_id, run_id, checkpoint_backend, replay_canonical_field]
        rollback_anchor: ENABLE_LANGGRAPH_REPLAY_CANONICAL=true
        acceptance_cmd_ref: bash scripts/pytest_targeted.sh app/ai/test_stream_modes.py app/tests/test_complex_scenario.py -q
      - design_item: D-04
        fr_id: FR-LG-04
        trigger: 迁移后评估现有子图状态预填充与 busy 兜底逻辑
        input_contract:
          required_fields: [subgraph_state_reader, emitted_message_registry]
          optional_fields: [busy_error_handler]
          defaults:
            busy_error_handler: current
        output_contract:
          required_fields: [cleanup_candidate_list, delete_or_keep_decision]
        failure_semantics: 若缺少证据，则保持现状；若有证据，则优先删除冗余逻辑
        observability_fields: [subgraph_state_read_count, busy_error_count, duplicate_emit_count]
        rollback_anchor: ENABLE_SUBGRAPH_PREFILL_CLEANUP=true
        acceptance_cmd_ref: bash scripts/pytest_targeted.sh app/tests/test_complex_scenario.py -q
    implementation_seeds:
      - task_id: T-01
        feature_id: P1-langgraph-version-alignment
        blocked_by: []
        file_paths:
          - pyproject.toml
          - requirements.txt
        symbols:
          - project.dependencies.langgraph
          - requirements.langgraph
        change_type: modify
      - task_id: T-02
        feature_id: P1-agent-api-convergence
        blocked_by: [T-01]
        file_paths:
          - app/ai/workflow/multi_agent_graph.py
          - app/ai/agents/knowledge_agent.py
          - app/ai/middleware.py
          - app/ai/agents/todo_agent.py
        symbols:
          - create_react_agent
          - create_agent
          - supervisor_agent
          - knowledge_agent
        change_type: modify
      - task_id: T-03
        feature_id: P1-test-and-example-convergence
        blocked_by: [T-02]
        file_paths:
          - app/ai/test_stream_modes.py
          - app/ai/test_tool_calls.py
          - app/ai/examples/advanced_agent_demo.py
        symbols:
          - create_react_agent
          - create_agent
        change_type: modify
      - task_id: T-04
        feature_id: P1-subgraph-persistence-cleanup
        blocked_by: [T-02]
        file_paths:
          - app/ai/workflow/multi_agent_graph.py
          - app/services/chat_service.py
          - app/db/postgres_checkpoint.py
        symbols:
          - agent.aget_state
          - graph.aget_state
          - is_checkpointer_busy_error
          - _record_emitted_message_id
        change_type: modify
      - task_id: T-05
        feature_id: P1-docs-and-regression
        blocked_by: [T-01, T-02, T-03, T-04]
        file_paths:
          - workdocs/归档/正文/设计/2026-03-09-langgraph-v1-adoption-design.md
          - app/tests/test_complex_scenario.py
          - app/tests/test_model_switch.py
          - app/ai/test_stream_modes.py
        symbols:
          - design_freeze_summary
          - test_interrupt_resume
          - test_agent_build_path
        change_type: modify
    execution_chain_seed:
      preferred_mode: core
      task_key: PP-20260309-langgraph-v1-adoption
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
      - 记录安装解析所使用的 python_bin 与 langgraph_version
      - 记录 agent_api_mode=create_agent 与 agent_name/tool_count
      - 记录 subgraph_state_read_count、duplicate_emit_count、busy_error_count
      - 记录新增 runtime trace 仅写 additional_kwargs.langgraph_runtime
    risk_counterexample_map:
      - risk_id: R-01
        counterexample: create_agent 收口后 handoff 行为不等价
        verify_cmd: bash scripts/pytest_targeted.sh app/tests/test_model_switch.py app/tests/test_complex_scenario.py -q
      - risk_id: R-02
        counterexample: 子图持久化升级后仍保留手工预填充导致重复消息
        verify_cmd: bash scripts/pytest_targeted.sh app/tests/test_complex_scenario.py -q
      - risk_id: R-03
        counterexample: 新增运行时元数据字段破坏 replay 或前端 SSE 解析
        verify_cmd: bash scripts/pytest_targeted.sh app/ai/test_stream_modes.py -q
    assumptions:
      - 当前生产多智能体主路径继续以 Python Graph API 为中心，不切换到 Functional API
      - 现有前端只消费 SDK 消息，不依赖 TS 侧 Graph 运行时
      - 当前仓库已有 additional_kwargs canonical 习惯，可承载新增 LangGraph trace
  requirement_seeds: [D-01, D-02, D-03, D-04]
  implementation_seeds: [T-01, T-02, T-03, T-04, T-05]
  execution_chain_seed:
    preferred_mode: core
    task_key: PP-20260309-langgraph-v1-adoption
    card_seed: [T-01, T-02, T-03, T-04, T-05]
```


## 13. 审批记录
- design_approved: true
- approved_at: "2026-03-10T09:49:11+08:00"
- approved_round: "round-2"
- approval_evidence: "用户明确指令：先帮我 /jjk-plan；将该指令视为对当前 LangGraph 单方案的正式确认。"
- approval_mode: approved
- go_no_go: GO
- blocking_issues: []

## 14. clarify_consistency_check（机读）
```yaml
clarify_consistency_check:
  clarify_phase: approval
  current_round: 2
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
