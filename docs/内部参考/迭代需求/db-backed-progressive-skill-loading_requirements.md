# db-backed-progressive-skill-loading 需求文档

> 更新时间：2026-03-07 00:00 +08:00  
> 上游设计：`docs/plans/2026-03-07-db-backed-progressive-skill-loading-design.md`  
> 文档目标：定义 WHAT（需求合同、验收门禁、追溯矩阵），供 `db-backed-progressive-skill-loading_implementation_plan.md` 承接

## 1. 需求范围与目标

### 1.1 核心目标

- 将聊天主运行时从“后端 hybrid 检索 + 静默注入 `skill_context`”收敛到“catalog 预装 + `load_skills` 显式加载”的单一机制。
- 保留数据库治理层（`definition/version/binding`）作为 Skill 运行时真理源，不回退到文件直读模式。
- 将会话态与回放态显式拆分为 `skill_catalog_manifest / loaded_skill_registry / additional_kwargs.skill_runtime`，消除状态散落。
- 在不引入新 Skill 资源表的前提下，完成 Phase A 的目录 metadata、加载工具、配置开关、回放 canonical 与测试收口。

### 1.2 范围

- Skill 运行时：`app/services/skill_service.py`、`app/ai/workflow/multi_agent_graph.py`、`app/ai/state.py`、`app/ai/protocol.py`
- Skill 治理模型：`app/models/agent_skill.py`、`alembic/versions/*_add_progressive_skill_catalog_fields.py`
- 管理面与配置：`app/api/v1/endpoints/skill_admin_api.py`、`app/core/config_contract.py`
- 文档与测试：`docs/API文档/接口文档.md`、`docs/内部参考/AI技能库.md`、`app/tests/test_skill_*.py`

### 1.3 非范围

- 不把每个 Skill 变成独立 tool，不引入 tool 数量与 skill 数量一一对应的运行时结构。
- 不在本期引入 Phase B 资源树能力，不新增 `t_agent_skill_resources` 等新表。
- 不保留 hybrid/vector/FTS 作为聊天主链路的默认命中决策。
- 不做 Skill 自动训练、自动改写、自动发布或自动回滚。

## 2. 机读需求合同（强制）

```yaml
requirements_contract:
  topic: "db-backed-progressive-skill-loading"
  status: "approved"
  design_source: docs/plans/2026-03-07-db-backed-progressive-skill-loading-design.md
  clarify_handoff_source: docs/plans/2026-03-07-db-backed-progressive-skill-loading-design.md#clarify_handoff_contract
  clarify_handoff_version: v2
  design_approved: true
  design_approval_evidence: "用户回复“接受”“好的”，确认第一期继续采用 progressive loader 单方案，并补齐 schema 真理源、会话状态壳、additional_kwargs.skill_runtime 三项实现契约；Phase A 持久化字段最小集冻结为 catalog_path/catalog_order/catalog_description/when_to_use。"
  design_freeze_summary:
    design_actionable: true
    missing_blocks: []
    risk_level: medium
    risk_counterexamples_count: 5
    handoff_contract_ready: true
    product_contract_ready: true
    implementation_seed_count: 6
    semantic_frozen: true
    contract_source_decided: true
    handoff_seed_alignment_ok: true
    parallel_dependency_ready: true
    replay_canonical_field_set: true
  owner: "ai-runtime-governance"
  approver: "jijingkun"
  updated_at: "2026-03-07 00:00"
```

## 3. 产品契约矩阵（PRD-Lite 承接）

```yaml
product_contract_matrix:
  target_users:
    - 平台管理员（维护 Skill 内容、版本、模板与用户覆盖）
    - 终端用户（在聊天中获得与问题强相关的 Skill 能力增强）
    - Agent 运行时（以固定工具协议稳定调用 Skill 加载能力）
  core_scenarios:
    - 聊天会话进入首轮 LLM 调用前预装 Skill 描述目录
    - LLM 判断需要某个 Skill 后显式调用 `load_skills` 加载正文并继续推理
    - 用户切换绑定版本后，新会话只看到该用户生效版本的目录与正文
    - 管理员发布/回滚 Skill 版本后，无需改代码即可影响后续会话的可见目录与加载内容
  business_goal_metrics:
    - 聊天主路径 100% 使用统一 Skill Loader 机制
    - 90% 以上命中会话可追溯 `catalog_visible_count / loaded_skill_ids / effective_versions`
    - 默认会话首轮仅注入目录描述，不预装 Skill 全文
    - 多租户用户隔离正确率 = 100%
    - 单用户可见 Skill 数量基线 < 20，Phase A 不引入热路径预筛
  non_goals:
    - 不把 Skill 直接编译为真正业务工具
    - 不做 Skill 自动训练、自动 embedding 更新闭环
    - 不保留 runtime hybrid 检索作为聊天主路径
    - 不引入新的 Skill 数据表
    - 不要求保留聊天主链路向量索引依赖
  acceptance_gates:
    - AG-01 无论是否命中 Skill，LLM 首轮都能看到同一结构的 Skill 描述目录
    - AG-02 命中 Skill 时必须经 `load_skills` 显式加载，不允许后端静默替模型选择
    - AG-03 非法 `skill_id` 返回结构化错误，不得 silent fallback 到其他 Skill
    - AG-04 会话回放能够还原当时加载的 Skill 版本，即使不持久化 Skill 全文
```

## 4. FR 合同矩阵（字段级）

```yaml
fr_contract_matrix:
  - fr_id: FR-01
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[0]
    business_goal_refs:
      - 聊天主路径 100% 使用统一 Skill Loader 机制
      - 默认会话首轮仅注入目录描述，不预装 Skill 全文
    user_value: 让模型先看到“可用 Skill 目录”而不是被后端静默注入正文
    trigger: 聊天会话进入首轮 LLM 调用前
    input_contract:
      required_fields: [user_id, messages]
      optional_fields: [thread_id, trace_id]
      source_of_truth: app/services/skill_service.py
    output_contract:
      required_fields: [skill_catalog_manifest, skill_catalog_context]
      optional_fields: [catalog_version, visible_skill_count]
      consumer: app/ai/workflow/multi_agent_graph.py
    failure_semantics: 目录构建失败允许本轮无 catalog 继续，但必须记录结构化告警，不得偷偷切回 hybrid 注入
    observability_fields: [user_id, trace_id, visible_skill_count, catalog_build_source, catalog_version]
    rollback_anchor: SKILL_RUNTIME_MODE=hybrid_rag
    owner: ai-runtime

  - fr_id: FR-02
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[1]
    business_goal_refs:
      - 聊天主路径 100% 使用统一 Skill Loader 机制
      - 90% 以上命中会话可追溯 `loaded_skill_ids / effective_versions`
    user_value: 模型可以显式决定按需加载哪个 Skill，避免后端越权替模型命中
    trigger: LLM 在对话中调用 `load_skills`
    input_contract:
      required_fields: [skill_ids]
      optional_fields: [reason]
      source_of_truth: app/ai/workflow/multi_agent_graph.py
    output_contract:
      required_fields: [loaded_skills]
      optional_fields: [errors, truncated_count]
      consumer: ToolMessage 与会话状态
    failure_semantics: 非法、不可见、已禁用或超量的 `skill_id` 必须返回结构化错误；不得用其他 Skill 替代
    observability_fields: [user_id, trace_id, requested_skill_ids, loaded_skill_ids, effective_versions, truncated_count]
    rollback_anchor: ENABLE_PROGRESSIVE_SKILL_LOADING=false
    owner: agent-orchestration

  - fr_id: FR-03
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[2]
    business_goal_refs:
      - 90% 以上命中会话可追溯 `loaded_skill_ids / effective_versions`
      - 会话回放能够还原当时加载的 Skill 版本
    user_value: 已加载 Skill 的会话态与回放态一致，刷新/恢复后不会丢失版本语义
    trigger: Skill 被成功加载并进入当前会话
    input_contract:
      required_fields: [loaded_skill_ids, effective_versions]
      optional_fields: [loaded_from_cache, truncated_flags]
      source_of_truth: app/ai/protocol.py
    output_contract:
      required_fields: [additional_kwargs.skill_runtime]
      optional_fields: [loaded_skill_context, replay_source]
      consumer: 回放恢复与前端消息归一层
    failure_semantics: 缺少 canonical 字段视为实现失败，禁止宣称 replay 一致
    observability_fields: [thread_id, trace_id, loaded_skill_ids, effective_versions, catalog_version, replay_source]
    rollback_anchor: ENABLE_SKILL_RUNTIME_TRACE=false
    owner: chat-runtime

  - fr_id: FR-04
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[3]
    business_goal_refs:
      - 聊天主路径 100% 使用统一 Skill Loader 机制
      - 多租户用户隔离正确率 = 100%
    user_value: 管理后台仍可调试 Skill 命中，但不会再影响聊天主路径决策
    trigger: 管理后台搜索或调试 Skill 命中效果
    input_contract:
      required_fields: [query]
      optional_fields: [user_id, mode]
      source_of_truth: app/services/skill_service.py
    output_contract:
      required_fields: [debug_candidates]
      optional_fields: [score_breakdown, retrieval_log]
      consumer: app/api/v1/endpoints/skill_admin_api.py
    failure_semantics: 仅影响后台调试，不影响聊天主路径；主路径不得读取该结果决定正文注入
    observability_fields: [query_hash, mode, candidate_count, runtime_source_mode]
    rollback_anchor: ENABLE_SKILL_ADMIN_SEARCH=true
    owner: admin-governance

  - fr_id: FR-05
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[4]
    business_goal_refs:
      - 默认会话首轮仅注入目录描述，不预装 Skill 全文
      - 单用户可见 Skill 数量基线 < 20，Phase A 不引入热路径预筛
    user_value: 首轮目录文案真正表达“什么时候该用这个 Skill”，让模型更容易主动触发 loader
    trigger: Skill 导入/同步到数据库，或 catalog 构建前
    input_contract:
      required_fields: [name, description, content]
      optional_fields: [trigger_phrases, scope]
      source_of_truth: app/models/agent_skill.py
    output_contract:
      required_fields: [catalog_description]
      optional_fields: [when_to_use]
      consumer: SkillService.build_catalog_descriptor
    failure_semantics: 无法生成派生目录描述时回退原始 `description`，但不得阻断 Skill 上线；不得改由兼容表承载新 metadata
    observability_fields: [skill_id, description_source, description_length, derived_catalog_description, metadata_truth_source]
    rollback_anchor: ENABLE_SKILL_CATALOG_METADATA_NORMALIZATION=false
    owner: skill-governance
```

## 5. NFR 合同矩阵（数值阈值）

```yaml
nfr_contract_matrix:
  - nfr_id: NFR-01
    requirement: 单用户可见 Skill 数量基线 <= 20；超过 20 必须记录 `skill_catalog_over_budget` 告警
    owner: ai-runtime
  - nfr_id: NFR-02
    requirement: 单次 `load_skills` 请求的 `skill_ids` 数量 <= 3
    owner: agent-orchestration
  - nfr_id: NFR-03
    requirement: 同一会话内同一 `skill_id + version` 重复加载次数 = 0
    owner: chat-runtime
  - nfr_id: NFR-04
    requirement: 多租户错误版本命中率 = 0
    owner: skill-governance
  - nfr_id: NFR-05
    requirement: `additional_kwargs.skill_runtime` 缺失率 = 0
    owner: chat-runtime
  - nfr_id: NFR-06
    requirement: 历史版本回放缺失时 `replay_skill_version_missing` 观测记录完整率 = 100%
    owner: observability
```

## 6. 追溯矩阵（设计 -> FR -> Feature -> Task -> TC）

```yaml
traceability_matrix:
  - design_item: D-01
    fr_id: FR-01
    feature_id: P1-runtime-catalog
    task_id: T-01
    tc_id: TC-01
    acceptance_cmd_ref: PYTHONPATH=. pytest app/tests/test_skill_catalog_manifest.py -q
    evidence_entry: docs/内部参考/迭代需求/db-backed-progressive-skill-loading_implementation_plan.md

  - design_item: D-02
    fr_id: FR-02
    feature_id: P1-skill-loader-tool
    task_id: T-02
    tc_id: TC-02
    acceptance_cmd_ref: PYTHONPATH=. pytest app/tests/test_skill_loader_tool.py -q
    evidence_entry: docs/内部参考/迭代需求/db-backed-progressive-skill-loading_implementation_plan.md

  - design_item: D-03
    fr_id: FR-03
    feature_id: P1-session-canonical-trace
    task_id: T-03
    tc_id: TC-03
    acceptance_cmd_ref: PYTHONPATH=. pytest app/tests/test_skill_runtime_replay.py -q
    evidence_entry: docs/内部参考/迭代需求/db-backed-progressive-skill-loading_implementation_plan.md

  - design_item: D-04
    fr_id: FR-04
    feature_id: P1-runtime-mode-switch
    task_id: T-04
    tc_id: TC-04
    acceptance_cmd_ref: PYTHONPATH=. pytest app/tests/test_skill_runtime_mode_switch.py -q
    evidence_entry: docs/内部参考/迭代需求/db-backed-progressive-skill-loading_implementation_plan.md

  - design_item: D-05
    fr_id: FR-05
    feature_id: P1-catalog-metadata-contract
    task_id: T-05
    tc_id: TC-05
    acceptance_cmd_ref: PYTHONPATH=. pytest app/tests/test_skill_admin_catalog_metadata.py -q
    evidence_entry: docs/内部参考/迭代需求/db-backed-progressive-skill-loading_implementation_plan.md

  - design_item: D-03
    fr_id: FR-03
    feature_id: P1-tests-and-docs
    task_id: T-06
    tc_id: TC-06
    acceptance_cmd_ref: PYTHONPATH=. pytest app/tests/test_skill_catalog_manifest.py app/tests/test_skill_loader_tool.py app/tests/test_skill_runtime_replay.py app/tests/test_skill_runtime_mode_switch.py app/tests/test_skill_admin_catalog_metadata.py -q
    evidence_entry: docs/内部参考/迭代需求/db-backed-progressive-skill-loading_implementation_plan.md
```
