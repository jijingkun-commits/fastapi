# context-engineering-unification 需求文档

> 更新时间：2026-03-11 18:45 +08:00  
> 上游设计：`workdocs/归档/正文/设计/2026-03-10-context-engineering-unification-design.md`
> 文档目标：定义 WHAT（需求合同、验收门禁、追溯矩阵），供 `context-engineering-unification_implementation_plan.md` 承接

## 1. 需求范围与目标

### 1.1 核心目标
- 将当前“`messages` 裁剪 + `system/skill` 后注入 + ToolMessage 首尾截断”的分散上下文处理，收敛为单一 `pre-model` context builder。
- 把所有真实进入模型的内容统一纳入 token 账本：`SUPERVISOR_PROMPT`、tool schema、`messages`、`system_context`、`skill_catalog_context`、`loaded_skill_registry` 派生摘要。
- 保持 `checkpointer` 为完整历史真相源，不把推理期压缩产物回写成长期历史。
- 对齐最新主干：`router blocked / replay recovery` 继续走结果式收口，不再回退到 `system_context` 的自然语言补齐提示。

### 1.2 范围
- 编排与上下文装配：`app/ai/workflow/multi_agent_graph.py`、`app/ai/context_engineering.py`
- 模型路由预算：`app/ai/llm_util.py`、`app/services/llm_scene_service.py`、`app/services/llm_config_service.py`
- 技能与系统上下文来源：`app/services/skill_service.py`、`app/services/response_policy_service.py`、`app/ai/state.py`
- 测试与文档：`tests/unit/test_multi_agent_context_budget.py`、`tests/unit/test_multi_agent_streaming_helpers.py`、`app/tests/test_skill_loader_tool.py`、相关设计与测试文档

### 1.3 非范围
- 不切换到官方 `create_supervisor` 或全量 built-in middleware 框架。
- 不更换当前模型供应商或后台模型路由机制。
- 不在本期引入长期记忆向量库新能力。
- 不先上摘要中间件作为主修复；摘要只作为 Phase B 兜底能力。

## 2. 机读需求合同（强制）

```yaml
requirements_contract:
  topic: "context-engineering-unification"
  status: "approved"
  design_source: workdocs/归档/正文/设计/2026-03-10-context-engineering-unification-design.md
  clarify_handoff_source: workdocs/归档/正文/设计/2026-03-10-context-engineering-unification-design.md#clarify_handoff_contract
  clarify_handoff_version: v2
  design_approved: true
  design_approval_evidence: "确认"
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
  owner: "ai-context-governance"
  approver: "jijingkun"
  updated_at: "2026-03-11 18:45"
```

## 3. 产品契约矩阵（PRD-Lite 承接）

```yaml
product_contract_matrix:
  target_users:
    - AI 聊天终端用户
    - 后台模型/技能运营管理员
    - 排障与性能治理开发者
  core_scenarios:
    - 长对话中主对话仍能稳定回答，不被旧工具输出和技能正文淹没
    - 多轮技能加载后，后续轮次按需复用必要约束，不再把整段技能正文无上限塞进 prompt
    - 多轮知识检索、图表、SQL 后，Supervisor 仍能聚焦本轮任务，不被旧 ToolMessage 污染
    - replay recovery / router blocked 场景继续采用结果式用户可见收口，不回退到 `system_context` 自然语言补齐提示
  business_goal_metrics:
    - 模型调用前上下文预算账本覆盖率 = 100%
    - `prompt_token_estimate` 与 `tool_schema_token_estimate` 产出率 = 100%
    - `loaded_skill_context` / `skill_catalog_context` 高成本样本可解释率 = 100%
    - 高成本技能上下文相对当前基线削减 >= 30%
  non_goals:
    - 不更换模型供应商
    - 不重做后台 LLM 管理台
    - 不切换整体 Graph 框架
    - 不直接引入向量长期记忆新能力
  acceptance_gates:
    - AG-01 单一 builder 成为唯一上下文装配入口
    - AG-02 `loaded_skill_registry` 成为技能正文唯一真相源，`loaded_skill_context` 不再直接注入
    - AG-03 `SUPERVISOR_PROMPT` 与 tool schema 必须进入分项 token 账本
    - AG-04 replay recovery / router blocked 不得回退到 `system_context` 自然语言补齐提示
    - AG-05 旧 ToolMessage 保留策略可测试、可观测、可回退
  release_constraints:
    - 项目未上线，以结构收敛和设计简洁为第一优先级
    - 新增开关默认开启（true）；仅用于回退，不作为长期双轨运行开关
```

## 4. FR 合同矩阵（字段级）

```yaml
fr_contract_matrix:
  - fr_id: FR-01
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[0]
    business_goal_refs:
      - 模型调用前上下文预算账本覆盖率 = 100%
      - `prompt_token_estimate` 与 `tool_schema_token_estimate` 产出率 = 100%
    user_value: 让排障和性能治理看到“真正进模型的内容到底是谁在吃 token”
    trigger: 任意 Supervisor / Agent 模型调用前
    input_contract:
      required_fields: [scene_key, messages, prompt_template, tool_definitions]
      source_of_truth: app/ai/context_engineering.py
    output_contract:
      required_fields: [llm_input_messages, context_budget_ledger]
      optional_fields: [context_runtime_flags, selected_tools_for_turn]
      consumer: app/ai/workflow/multi_agent_graph.py
    failure_semantics: 无法解析场景模型时回退到环境变量预算上限，并记录 fallback 来源；不得静默跳过账本
    observability_fields: [scene_key, model_code, provider_code, context_window, token_budget, prompt_token_estimate, tool_schema_token_estimate]
    rollback_anchor: ENABLE_CONTEXT_BUILDER_V1=false
    owner: ai-context-runtime

  - fr_id: FR-02
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[1]
    business_goal_refs:
      - 高成本技能上下文相对当前基线削减 >= 30%
      - `prompt_token_estimate` 与 `tool_schema_token_estimate` 产出率 = 100%
    user_value: 让模型只看到本轮真正需要的工具和工具结果，减少噪音
    trigger: 会话包含 ToolMessage 或本轮可见工具集过大且准备进入下一次推理
    input_contract:
      required_fields: [messages, tool_definitions]
      source_of_truth: app/ai/context_engineering.py
    output_contract:
      required_fields: [edited_messages]
      optional_fields: [tool_compaction_stats, selected_tools_for_turn, tool_schema_token_estimate]
      consumer: app/ai/workflow/multi_agent_graph.py
    failure_semantics: 上下文编辑失败时回退到现有压缩策略，并记录 fallback 原因；不得重建旧式 system_context 补齐提示
    observability_fields: [tool_message_count, truncated_tool_message_count, removed_tool_message_count, selected_tool_count, tool_schema_token_estimate]
    rollback_anchor: ENABLE_TOOL_CONTEXT_EDIT_V1=false
    owner: ai-orchestration

  - fr_id: FR-03
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[2]
    business_goal_refs:
      - 高成本技能上下文相对当前基线削减 >= 30%
      - `loaded_skill_context` / `skill_catalog_context` 高成本样本可解释率 = 100%
    user_value: 在保留技能能力的同时，避免技能全文把 prompt 顶满
    trigger: 会话已加载技能且需要后续轮次复用
    input_contract:
      required_fields: [loaded_skill_registry]
      optional_fields: [skill_catalog_manifest, loaded_skill_context]
      source_of_truth: app/services/skill_service.py
    output_contract:
      required_fields: [budgeted_skill_context]
      optional_fields: [replay_source, missing_skills]
      consumer: app/ai/context_engineering.py
    failure_semantics: 版本回源失败时读旧写新，输出可观测降级提示，不直接拼接旧缓存全文
    observability_fields: [loaded_skill_count, missing_skill_count, loaded_skill_token_estimate, replay_source]
    rollback_anchor: ENABLE_SKILL_CONTEXT_CANONICAL_V1=false
    owner: skill-runtime

  - fr_id: FR-04
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[3]
    business_goal_refs:
      - 模型调用前上下文预算账本覆盖率 = 100%
      - replay recovery / router blocked 场景继续采用结果式用户可见收口
    user_value: 在超预算或补齐失败时，用户看到统一、可解释、不会继续污染 prompt 的结果式收口
    trigger: 统一预算后仍超阈值或长会话质量下降
    input_contract:
      required_fields: [messages, context_budget_ledger]
      optional_fields: [summary_policy]
      source_of_truth: app/ai/context_engineering.py
    output_contract:
      required_fields: [summary_message_or_summary_state]
      optional_fields: [context_runtime]
      consumer: app/ai/workflow/multi_agent_graph.py
    failure_semantics: 摘要失败时保留当前 builder 路径，不阻断主回答；router blocked / replay recovery 仍走结果式消息
    observability_fields: [summary_trigger_reason, summary_chars_before, summary_chars_after, replay_recovery_result_mode]
    rollback_anchor: ENABLE_CONTEXT_SUMMARY_V1=false
    owner: ai-context-runtime
```

## 5. NFR 合同矩阵（数值阈值）

```yaml
nfr_contract_matrix:
  - nfr_id: NFR-01
    requirement: `delivery_meta.context_budget_ledger` 缺失率 = 0
    owner: observability
  - nfr_id: NFR-02
    requirement: `prompt_token_estimate` 与 `tool_schema_token_estimate` 产出率 = 100%
    owner: ai-context-runtime
  - nfr_id: NFR-03
    requirement: `selected_tools_for_turn` 数量 <= 本轮可见工具数量，且 tool schema 超预算样本告警覆盖率 = 100%
    owner: ai-orchestration
  - nfr_id: NFR-04
    requirement: replay recovery / router blocked 回退到 `system_context` 自然语言补齐提示的命中率 = 0
    owner: replay-governance
  - nfr_id: NFR-05
    requirement: `loaded_skill_context` 直接全文注入的默认命中率 = 0
    owner: skill-runtime
  - nfr_id: NFR-06
    requirement: 长对话高成本样本中，`prompt + tool_schema + dynamic_context` 分项可解释率 = 100%
    owner: ai-context-governance
```

## 6. 追溯矩阵（设计 -> FR -> Feature -> Task -> TC）

```yaml
traceability_matrix:
  - design_item: D-01
    fr_id: FR-01
    feature_id: P1-context-builder
    task_id: T-01
    tc_id: TC-CEU-01
    acceptance_cmd_ref: bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_context_budget.py
    evidence_entry: workdocs/归档/正文/实施计划/context-engineering-unification_implementation_plan.md

  - design_item: D-01
    fr_id: FR-01
    feature_id: P1-model-aware-budget
    task_id: T-02
    tc_id: TC-CEU-02
    acceptance_cmd_ref: bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_context_budget.py -k model_aware_budget
    evidence_entry: workdocs/归档/正文/实施计划/context-engineering-unification_implementation_plan.md

  - design_item: D-02
    fr_id: FR-02
    feature_id: P1-tool-context-editing
    task_id: T-03
    tc_id: TC-CEU-03
    acceptance_cmd_ref: bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py -k tool_message
    evidence_entry: workdocs/归档/正文/实施计划/context-engineering-unification_implementation_plan.md

  - design_item: D-03
    fr_id: FR-03
    feature_id: P1-skill-context-canonical
    task_id: T-04
    tc_id: TC-CEU-04
    acceptance_cmd_ref: bash scripts/pytest_targeted.sh app/tests/test_skill_loader_tool.py tests/unit/test_multi_agent_streaming_helpers.py -k skill_context
    evidence_entry: workdocs/归档/正文/实施计划/context-engineering-unification_implementation_plan.md

  - design_item: D-04
    fr_id: FR-04
    feature_id: P1-doc-and-observability
    task_id: T-05
    tc_id: TC-CEU-05
    acceptance_cmd_ref: /Users/jijingkun/.codex/worktrees/4620/fastapi/venv/bin/python scripts/check_workflow_contract.py --mode clarify_plan --requirements-path workdocs/归档/正文/需求/context-engineering-unification_requirements.md --implementation-path workdocs/归档/正文/实施计划/context-engineering-unification_implementation_plan.md --output workdocs/归档/报告/机读校验/context-engineering-unification_clarify_plan_alignment.json
    evidence_entry: workdocs/归档/正文/实施计划/context-engineering-unification_implementation_plan.md
```
