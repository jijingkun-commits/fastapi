# 统一 `research_subagent` 一期实施计划

> 更新时间：2026-03-13
> 上游输入：`workdocs/需求/2026-03-13_research-subagent-phase1/requirements.md`、`workdocs/设计/2026-03-13_research-subagent-phase1/design.md`
> 当前模式：`core`（plan-only，不自动进入执行链）

## 1. 执行策略

这次按“先定 research 语义出口，再立统一执行单元，再收 Supervisor surface，最后补附件与展示保真”的顺序拆任务。原因是如果先改 Supervisor 或展示链路，但 `research` 还没有唯一语义出口和统一 contract，后面一定会重新返工。

依赖关系固定为：

1. `T-01` 必须先完成，因为它冻结 `research` 应该长在哪一层。
2. `T-02` 依赖 `T-01`，负责把统一 research 执行单元和 contract 立起来。
3. `T-03` 依赖 `T-01 + T-02`，负责把 Supervisor 的 research 双入口收口。
4. `T-04` 依赖 `T-01`，可以和 `T-02` 并行，负责把附件路由改成目标驱动。
5. `T-05` 依赖 `T-02 + T-03`，负责把 KB 图文展示保真接回现有 canonical display pipeline。
6. `T-06` 最后做，负责把稳定文档和追溯收口回真理源。

可并行项只有一组：`T-02` 和 `T-04`。其余任务都应该串行推进，避免 contract、route 和 display 三边再次长出平行口径。

## 2. 功能机制包

| feature_id | 目标 | 文件锚点 | 核心符号 | 风险点 | 验收主命令 |
|---|---|---|---|---|---|
| RS-01 | 在 intent 层新增 research 语义出口 | `app/ai/intent/goal_resolver.py` | `infer_primary_goal_kind`, `infer_primary_goal_bucket_from_text`, `resolve_runtime_goal_specs` | 又把 research 关键词主路由写回编排层 | `bash scripts/pytest_targeted.sh tests/unit/test_research_goal_resolver.py tests/unit/test_intent_layer_boundary.py -q` |
| RS-02 | 新增统一 stateless research 执行单元与 contract | `app/ai/agents/research_subagent.py`, `app/ai/protocol.py`, `app/ai/tools/ragflow_tool.py`, `app/ai/tools/chatTools.py` | `research_subagent`, `build_research_result_payload` | 只回纯文本摘要，导致图文/媒体能力丢失 | `bash scripts/pytest_targeted.sh tests/unit/test_research_subagent.py tests/unit/test_ragflow_tool.py tests/unit/test_research_dispatch_contract.py -q` |
| RS-03 | 收口 Supervisor 的 research surface | `app/ai/workflow/multi_agent_graph.py` | `_get_supervisor_tool_entries`, `research entry`, `dispatch routing` | simple query 路径被误伤，research 双入口没删干净 | `bash scripts/pytest_targeted.sh tests/unit/test_research_dispatch_contract.py tests/unit/test_multi_agent_tool_governance_runtime.py -q` |
| RS-04 | 让附件 route 改为目标驱动 | `app/ai/workflow/attachment_planning.py` | `build_attachment_planning_contract`, `render_attachment_planning_context` | “多附件/文档探针=research” 旧逻辑残留 | `bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_chat_service_human_attachment_persistence.py -q` |
| RS-05 | 保住 research 场景下的 KB 图文展示 | `app/services/chat_service.py`, `app/core/message_display_blocks.py`, `app/repositories/chat_repo.py` | `compile_message_display_blocks`, `display_blocks`, `kb_images` | research 结果进入 display pipeline 后只剩纯文本或 live/history 不一致 | `bash scripts/pytest_targeted.sh tests/unit/test_message_display_blocks.py tests/unit/test_chat_service_done_payload.py tests/unit/test_chat_repo_serialization.py tests/api/test_chat_api.py -q` |
| RS-06 | 同步稳定文档与追溯矩阵 | `docs/开发文档/架构设计/AI模块设计.md`, `docs/产品文档/聊天系统需求.md`, `workdocs/需求/...` | `research_subagent`, `traceability_matrix` | 过程文档定了，稳定真理源没同步 | `rg -n "research_subagent|knowledge_search|web_research|附件|图文展示" docs/开发文档/架构设计/AI模块设计.md docs/产品文档/聊天系统需求.md workdocs/需求/2026-03-13_research-subagent-phase1/requirements.md` |

## 3. implementation_tasks

```yaml
implementation_tasks:
  - task_id: T-01
    feature_id: RS-01
    design_item_refs: [D-01-research-goal-bucket]
    requirement_ids: [FR-01, FR-02, FR-03, NFR-04]
    goal: 在 intent/resolver 层引入稳定的 research 语义出口，让 research 的判定不再依赖编排层启发式。
    file_paths:
      - app/ai/intent/goal_resolver.py
      - tests/unit/test_intent_layer_boundary.py
      - tests/unit/test_research_goal_resolver.py
    symbols:
      - infer_primary_goal_kind
      - infer_primary_goal_bucket_from_text
      - resolve_runtime_goal_specs
      - split_composite_query
    module_changes:
      - 为 research 型请求补充独立的 goal kind / bucket，不再把它们统统塞进 external/general。
      - 保持语义判定留在 intent 层，禁止把 research 关键词路由下沉到 multi_agent_graph。
      - 为单次 knowledge/web 查询与多来源 research 请求建立清晰升级边界。
    deletion_actions:
      - 删除“research 靠 Supervisor 编排层补判断”的潜在路径。
    risk_tags: [intent, routing, contract]
    mandatory_evidence: [research_bucket_visible, simple_vs_research_boundary_visible, no_orchestration_keyword_route]
    acceptance_cmds:
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh tests/unit/test_research_goal_resolver.py tests/unit/test_intent_layer_boundary.py -q
      - kind: scripted_flow
        cmd: rg -n "research" app/ai/intent/goal_resolver.py

  - task_id: T-02
    feature_id: RS-02
    design_item_refs: [D-02-unified-research-subagent]
    requirement_ids: [FR-03, FR-04, FR-07, NFR-01, NFR-03, NFR-05]
    goal: 新增一个统一的、无跨轮状态的 research 执行单元，并把 research result contract 扩展为可承载媒体引用。
    file_paths:
      - app/ai/agents/research_subagent.py
      - app/ai/protocol.py
      - app/ai/tools/ragflow_tool.py
      - app/ai/tools/chatTools.py
      - tests/unit/test_research_subagent.py
      - tests/unit/test_ragflow_tool.py
      - tests/unit/test_research_dispatch_contract.py
    symbols:
      - research_subagent
      - build_research_result_payload
      - knowledge_research
      - web_research
    module_changes:
      - 新增统一 research_subagent executor，内部编排 knowledge/web research sources。
      - 扩展 research payload，至少增加 `media_refs` 或等价能力字段。
      - `knowledge_research` / `web_research` 退化为内部 source provider 或兼容 helper，不再是首选 surface。
    deletion_actions:
      - 删除 research 只回 `summary/evidence/insufficiency` 的旧单薄 contract。
    risk_tags: [contract, executor, media]
    mandatory_evidence: [research_executor_created, research_payload_v2_ready, source_provider_split_clean]
    acceptance_cmds:
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh tests/unit/test_research_subagent.py tests/unit/test_ragflow_tool.py tests/unit/test_research_dispatch_contract.py -q
      - kind: scripted_flow
        cmd: rg -n "media_refs|research_subagent|build_research_result_payload" app/ai/agents/research_subagent.py app/ai/protocol.py app/ai/tools/ragflow_tool.py app/ai/tools/chatTools.py

  - task_id: T-03
    feature_id: RS-03
    design_item_refs: [D-03-supervisor-surface-cleanup]
    requirement_ids: [FR-02, FR-03, FR-07, NFR-01, NFR-03]
    goal: 把 Supervisor 的 research 双入口收口成单一执行入口，同时保留单点查询的 atomic tool 快路径。
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
      - tests/unit/test_research_dispatch_contract.py
      - tests/unit/test_multi_agent_tool_governance_runtime.py
    symbols:
      - _get_supervisor_tool_entries
      - _get_runtime_visible_supervisor_tools
      - research dispatch entry
    module_changes:
      - 保留 `knowledge_search` 与 `search_tool` 作为 atomic tool。
      - 移除 `knowledge_research/web_research` 作为 Supervisor 首选 surface 的平行入口。
      - 接上统一 research_subagent dispatch。
    deletion_actions:
      - 删除 Supervisor 直连双 research tool surface。
    risk_tags: [supervisor, surface_cleanup, governance]
    mandatory_evidence: [single_research_surface, atomic_tools_retained, dispatch_contract_updated]
    acceptance_cmds:
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh tests/unit/test_research_dispatch_contract.py tests/unit/test_multi_agent_tool_governance_runtime.py -q
      - kind: scripted_flow
        cmd: rg -n "knowledge_research|web_research|research_subagent|knowledge_search|search_tool" app/ai/workflow/multi_agent_graph.py

  - task_id: T-04
    feature_id: RS-04
    design_item_refs: [D-04-attachment-route-agnostic]
    requirement_ids: [FR-01, FR-06, NFR-04]
    goal: 把附件 planning 从“附件数量/文档探针驱动”改成“用户真实目标驱动”，让附件继续 route-agnostic。
    file_paths:
      - app/ai/workflow/attachment_planning.py
      - tests/unit/test_multi_agent_streaming_helpers.py
      - tests/unit/test_chat_service_human_attachment_persistence.py
    symbols:
      - build_attachment_planning_contract
      - render_attachment_planning_context
      - attachment_roles
    module_changes:
      - research route 必须由 goal bucket 命中决定，不能只看附件数或 has_document_probe。
      - 保持附件可进入 direct_tool / data_workflow / todo_workflow / research_subagent / mixed。
      - 保持附件角色 contract 可解释。
    deletion_actions:
      - 删除“多附件/文档探针=research”默认分支。
    risk_tags: [planning, attachment, route]
    mandatory_evidence: [goal_led_attachment_route, attachment_roles_stable, no_attachment_count_shortcut]
    acceptance_cmds:
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_chat_service_human_attachment_persistence.py -q
      - kind: scripted_flow
        cmd: rg -n "planning_route|research_subagent|attachment_roles" app/ai/workflow/attachment_planning.py

  - task_id: T-05
    feature_id: RS-05
    design_item_refs: [D-05-research-media-preservation]
    requirement_ids: [FR-04, FR-05, NFR-02]
    goal: 让 research 结果中的知识库图片引用继续复用现有 canonical display pipeline，保证 live 和 history 不退化。
    file_paths:
      - app/services/chat_service.py
      - app/core/message_display_blocks.py
      - app/repositories/chat_repo.py
      - tests/unit/test_message_display_blocks.py
      - tests/unit/test_chat_service_done_payload.py
      - tests/unit/test_chat_repo_serialization.py
      - tests/api/test_chat_api.py
    symbols:
      - compile_message_display_blocks
      - _build_display_blocks_payload
      - kb_images
      - result_events
    module_changes:
      - research media refs 适配进现有 `display_blocks` / history blocks 编译链路。
      - 保持 KB 图片 `[IMG-N] + kb_images` 的现有 canonical owner，不再另造图片协议。
      - 确保 research 结果即使图片失败也保留文本和证据降级。
    deletion_actions:
      - 删除“research 结果只能是纯文本总结”的默认展示假设。
    risk_tags: [display, history, kb_images]
    mandatory_evidence: [live_history_same_blocks, kb_images_preserved, text_fallback_kept]
    acceptance_cmds:
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh tests/unit/test_message_display_blocks.py tests/unit/test_chat_service_done_payload.py tests/unit/test_chat_repo_serialization.py tests/api/test_chat_api.py -q
      - kind: scripted_flow
        cmd: rg -n "display_blocks|kb_images|compile_message_display_blocks" app/services/chat_service.py app/core/message_display_blocks.py app/repositories/chat_repo.py

  - task_id: T-06
    feature_id: RS-06
    design_item_refs: [D-06-doc-sync]
    requirement_ids: [FR-01, FR-03, FR-05, FR-06, FR-07]
    goal: 把 research_subagent 一期的稳定结论同步回产品与架构真理源，并补全需求追溯矩阵。
    file_paths:
      - docs/开发文档/架构设计/AI模块设计.md
      - docs/产品文档/聊天系统需求.md
      - workdocs/需求/2026-03-13_research-subagent-phase1/requirements.md
    symbols:
      - research_subagent architecture
      - attachment planning route
      - traceability_matrix
    module_changes:
      - AI 模块设计补 research_subagent 的正式架构落点与 owner 边界。
      - 聊天系统需求补研究路由、图文展示和附件 route-agnostic 产品合同。
      - requirements 回填完整 `traceability_matrix`。
    deletion_actions:
      - 删除过程文档和稳定文档之间的平行口径。
    risk_tags: [doc_sync, traceability]
    mandatory_evidence: [stable_docs_synced, traceability_complete]
    acceptance_cmds:
      - kind: scripted_flow
        cmd: rg -n "research_subagent|knowledge_search|web_research|附件|图文展示" docs/开发文档/架构设计/AI模块设计.md docs/产品文档/聊天系统需求.md workdocs/需求/2026-03-13_research-subagent-phase1/requirements.md
```

## 4. db_migration_plan

```yaml
db_migration_plan:
  db_migration_required: false
  dev_migration_cmd: none
  release_migration_cmd: none
  mandatory_evidence: []
```

## 5. execution_contract

```yaml
execution_contract:
  preferred_mode: core
  execution_contract_ready: true
  delivery_mode: staged
  execution_unit: per_task
  commit_policy: single_commit
  stop_boundary: per_task
  temporal_gate_forbidden: true
  context_verified: true
  design_source: workdocs/设计/2026-03-13_research-subagent-phase1/design.md
  requirements_source: workdocs/需求/2026-03-13_research-subagent-phase1/requirements.md
```

## 6. implementation_readiness

```yaml
implementation_readiness:
  implementation_ready: true
  execution_contract_ready: true
  requirements_ready: true
  traceability_ready: true
  blocking_issue_count: 0
  readiness_note: approved_design_can_split_into_six_tasks
```

