# db-backed-progressive-skill-loading 实施计划

> 更新时间：2026-03-07 00:00 +08:00
> 上游设计：`workdocs/归档/正文/设计/2026-03-07-db-backed-progressive-skill-loading-design.md`
> 对应需求：`workdocs/归档/正文/需求/db-backed-progressive-skill-loading_requirements.md`

## 1. 实施概览
- 规划模式：`core`
- 交付目标：以单 PR、分阶段串行方式完成 Skill 主运行时切换，避免 catalog/schema/state/replay 在主干出现半切换状态。
- 架构策略：先固化 runtime catalog 与 metadata 真理源，再接入 loader tool 和 replay canonical，最后用测试/文档统一收口。
- 风险重点：双真理源回流、旧 `skill_context` 兼容旁路、tool load 未被模型触发、历史版本回放缺正文、配置切换后新旧路径并存。

## 2. implementation_tasks（机读）

```yaml
implementation_tasks:
  - task_id: T-01
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[0]
    feature_id: P1-runtime-catalog
    pr_id: PR-01
    phase: Phase-1
    change_type: modify
    owner: ai-runtime
    depends_on_tasks: [ROOT]
    risk_point: 若 runtime catalog 仍沿用检索结果拼接，会继续保留“后端替模型选 Skill”的旧根因
    rollback_point: SKILL_RUNTIME_MODE=hybrid_rag
    file_paths:
      - app/services/skill_service.py
      - app/ai/state.py
      - app/ai/workflow/multi_agent_graph.py
    symbols:
      - SkillService.build_skill_catalog_manifest
      - SkillService.format_skill_catalog_as_context
      - MultiAgentState.skill_catalog_manifest
      - MultiAgentState.skill_catalog_context
      - preprocess.skill_catalog_preload
    acceptance_cmds:
      - PYTHONPATH=. pytest app/tests/test_skill_catalog_manifest.py -q

  - task_id: T-02
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[1]
    feature_id: P1-skill-loader-tool
    pr_id: PR-01
    phase: Phase-2
    change_type: modify
    owner: agent-orchestration
    depends_on_tasks: [T-01]
    risk_point: 若 loader tool 与可见性校验不统一，模型会看到 catalog 但可加载错误版本或不可见 Skill
    rollback_point: ENABLE_PROGRESSIVE_SKILL_LOADING=false
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
      - app/services/skill_service.py
    symbols:
      - _create_load_skills_tool
      - _get_supervisor_tools
      - SkillService.load_skills_for_session
      - SkillService.validate_visible_skill_ids
      - ToolMessage.load_skills_result
    acceptance_cmds:
      - PYTHONPATH=. pytest app/tests/test_skill_loader_tool.py -q

  - task_id: T-03
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[2]
    feature_id: P1-session-canonical-trace
    pr_id: PR-01
    phase: Phase-3
    change_type: modify
    owner: chat-runtime
    depends_on_tasks: [T-02]
    risk_point: 若 `loaded_skill_registry` 与 `additional_kwargs.skill_runtime` 结构不统一，刷新/回放会重新退化成猜测旧 `skill_context`
    rollback_point: ENABLE_SKILL_RUNTIME_TRACE=false
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
      - app/ai/protocol.py
      - app/ai/state.py
      - app/repositories/chat_repo.py
    symbols:
      - additional_kwargs.skill_runtime
      - MultiAgentState.loaded_skill_registry
      - MultiAgentState.loaded_skill_context
      - build_skill_runtime_additional_kwargs_payload
      - skill_context(deprecated_compat)
    acceptance_cmds:
      - PYTHONPATH=. pytest app/tests/test_skill_runtime_replay.py -q

  - task_id: T-04
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[3]
    feature_id: P1-runtime-mode-switch
    pr_id: PR-01
    phase: Phase-4
    change_type: modify
    owner: config-governance
    depends_on_tasks: [T-01]
    risk_point: 若 `skill.runtime_mode` 与 `feature.enable_progressive_skill_loading` 语义重叠或默认值冲突，会重新长出双轨主路径
    rollback_point: feature.enable_progressive_skill_loading=false
    file_paths:
      - app/core/config_contract.py
      - app/services/skill_service.py
      - docs/API文档/接口文档.md
    symbols:
      - skill.runtime_mode
      - feature.enable_progressive_skill_loading
      - SkillService.resolve_runtime_mode
      - runtime_mode_switch_guard
    acceptance_cmds:
      - PYTHONPATH=. pytest app/tests/test_skill_runtime_mode_switch.py -q
      - python3 scripts/docs_guard.py --strict

  - task_id: T-05
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[4]
    feature_id: P1-catalog-metadata-contract
    pr_id: PR-01
    phase: Phase-5
    change_type: modify
    owner: skill-governance
    depends_on_tasks: [T-01]
    risk_point: 若 catalog metadata 仍写入 `t_agent_skills` 兼容表，后续 admin、import、runtime 会形成双真理源
    rollback_point: ENABLE_SKILL_CATALOG_METADATA_NORMALIZATION=false
    file_paths:
      - app/models/agent_skill.py
      - alembic/versions/*_add_progressive_skill_catalog_fields.py
      - app/api/v1/endpoints/skill_admin_api.py
      - app/services/skill_service.py
      - docs/内部参考/AI技能库.md
    symbols:
      - AgentSkillDefinition.catalog_path
      - AgentSkillDefinition.catalog_order
      - AgentSkillVersion.catalog_description
      - AgentSkillVersion.when_to_use
      - SkillMetadataUpdateRequest
      - SkillService.build_catalog_descriptor
      - metadata_truth_source_guard
    acceptance_cmds:
      - PYTHONPATH=. pytest app/tests/test_skill_admin_catalog_metadata.py -q

  - task_id: T-06
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[5]
    feature_id: P1-tests-and-docs
    pr_id: PR-01
    phase: Phase-6
    change_type: add
    owner: qa-governance
    depends_on_tasks: [T-02, T-03, T-04, T-05]
    risk_point: 若测试只覆盖 happy path，Skill loader 语义、回放 canonical、配置切换与 metadata 真理源会在后续重构中漂移
    rollback_point: 回退本次新增测试与文档并恢复 design 基线
    file_paths:
      - app/tests/test_skill_catalog_manifest.py
      - app/tests/test_skill_loader_tool.py
      - app/tests/test_skill_runtime_replay.py
      - app/tests/test_skill_runtime_mode_switch.py
      - app/tests/test_skill_admin_catalog_metadata.py
      - docs/内部参考/AI技能库.md
      - docs/API文档/接口文档.md
    symbols:
      - test_catalog_preload
      - test_loader_tool_visibility
      - test_runtime_replay_rehydrate
      - test_runtime_mode_switch_no_hybrid_fallback
      - test_catalog_metadata_truth_source
      - test_skill_runtime_read_old_write_new
    acceptance_cmds:
      - PYTHONPATH=. pytest app/tests/test_skill_catalog_manifest.py app/tests/test_skill_loader_tool.py app/tests/test_skill_runtime_replay.py app/tests/test_skill_runtime_mode_switch.py app/tests/test_skill_admin_catalog_metadata.py -q
      - python3 scripts/docs_guard.py --strict
```

## 3. task_to_pr_mapping（机读）

```yaml
planning_contract:
  task_to_pr_mapping:
    - task_id: T-01
      pr_id: PR-01
      pr_branch: codex/db-backed-progressive-skill-loading-phase-a
      pr_depends_on: []
      pr_subject: "Phase A 基础：runtime catalog 与状态壳落地"
      acceptance_cmds:
        - PYTHONPATH=. pytest app/tests/test_skill_catalog_manifest.py -q
      rollback_point: SKILL_RUNTIME_MODE=hybrid_rag
    - task_id: T-02
      pr_id: PR-01
      pr_branch: codex/db-backed-progressive-skill-loading-phase-a
      pr_depends_on: []
      pr_subject: "Phase A 基础：load_skills 固定工具与可见性校验"
      acceptance_cmds:
        - PYTHONPATH=. pytest app/tests/test_skill_loader_tool.py -q
      rollback_point: ENABLE_PROGRESSIVE_SKILL_LOADING=false
    - task_id: T-03
      pr_id: PR-01
      pr_branch: codex/db-backed-progressive-skill-loading-phase-a
      pr_depends_on: []
      pr_subject: "Phase A 基础：session/replay canonical 收敛"
      acceptance_cmds:
        - PYTHONPATH=. pytest app/tests/test_skill_runtime_replay.py -q
      rollback_point: ENABLE_SKILL_RUNTIME_TRACE=false
    - task_id: T-04
      pr_id: PR-01
      pr_branch: codex/db-backed-progressive-skill-loading-phase-a
      pr_depends_on: []
      pr_subject: "Phase A 基础：runtime mode 开关与接口文档同步"
      acceptance_cmds:
        - PYTHONPATH=. pytest app/tests/test_skill_runtime_mode_switch.py -q
        - python3 scripts/docs_guard.py --strict
      rollback_point: feature.enable_progressive_skill_loading=false
    - task_id: T-05
      pr_id: PR-01
      pr_branch: codex/db-backed-progressive-skill-loading-phase-a
      pr_depends_on: []
      pr_subject: "Phase A 基础：catalog metadata 真理源与管理面收敛"
      acceptance_cmds:
        - PYTHONPATH=. pytest app/tests/test_skill_admin_catalog_metadata.py -q
      rollback_point: ENABLE_SKILL_CATALOG_METADATA_NORMALIZATION=false
    - task_id: T-06
      pr_id: PR-01
      pr_branch: codex/db-backed-progressive-skill-loading-phase-a
      pr_depends_on: []
      pr_subject: "Phase A 收口：专项测试、文档与规划门禁通过"
      acceptance_cmds:
        - PYTHONPATH=. pytest app/tests/test_skill_catalog_manifest.py app/tests/test_skill_loader_tool.py app/tests/test_skill_runtime_replay.py app/tests/test_skill_runtime_mode_switch.py app/tests/test_skill_admin_catalog_metadata.py -q
        - python3 scripts/check_workflow_contract.py --mode clarify_plan --requirements-path workdocs/归档/正文/需求/db-backed-progressive-skill-loading_requirements.md --implementation-path workdocs/归档/正文/实施计划/db-backed-progressive-skill-loading_implementation_plan.md --output -
      rollback_point: 回退本次新增测试与文档并恢复 design 基线
  execution_mode: core
  strict_single_active_card: true
  task_key: PP-20260307-db-progressive-skill-loading
```

## 4. planning_contract 摘要
- 执行模式：`core`，不走并行拆卡；原因是 schema、state、tool、replay 互相耦合，半切换状态风险高于并行收益。
- PR 策略：所有 `task_id` 归并到单一 `PR-01`，以 `single_commit` 收口，避免主干出现“catalog 已上、replay 未上”的中间态。
- 阶段顺序：`T-01` 打底运行态目录，`T-02/T-03` 完成显式加载与 canonical，`T-04/T-05` 收敛开关与真理源，`T-06` 统一补测试和文档。
- 阻断策略：任一阶段未通过专项验收，不进入下一阶段；但不允许引入依赖自然时间成熟、TTL 到期或排班成熟的阻断条件。

## 5. execution_contract（机读）

```yaml
execution_contract:
  delivery_mode: staged
  execution_unit: all_tasks
  commit_policy: single_commit
  stop_boundary: none
  stop_on_blocked: true
  source_seed_ref: clarify_handoff_contract.required.execution_chain_seed.execution_contract_hint
```

## 6. implementation_readiness（机读）

```yaml
implementation_readiness:
  implementation_ready: true
  blocked_by: []
  next_step: /jjk-imp
  execution_contract_ready: true
```

## 7. TC 覆盖映射

```yaml
tc_execution_mapping:
  - tc_id: TC-01
    task_id: T-01
    pr_id: PR-01
  - tc_id: TC-02
    task_id: T-02
    pr_id: PR-01
  - tc_id: TC-03
    task_id: T-03
    pr_id: PR-01
  - tc_id: TC-04
    task_id: T-04
    pr_id: PR-01
  - tc_id: TC-05
    task_id: T-05
    pr_id: PR-01
  - tc_id: TC-06
    task_id: T-06
    pr_id: PR-01
```

## 8. 实施补充说明
- `T-01` 与 `T-05` 的顺序不可互换：必须先让 runtime catalog 以 definition/version 为目标形态构建，再把 metadata 真理源正式落盘与开放管理面，否则会出现“先建字段但 runtime 仍读旧表”的双轨状态。
- `T-03` 必须在 `T-02` 之后：只有 loader tool 固定下来，`additional_kwargs.skill_runtime` 才有稳定 producer，避免 replay 结构反复重写。
- `T-04` 不得通过“默认关闭 progressive loader”规避主链切换；若需回退，统一通过关闭开关或切回 `skill.runtime_mode=hybrid_rag` 实现。
- `T-06` 的门禁不仅是测试通过，还包括规划对齐门禁通过；未生成或未通过 alignment 报告时，不得宣称 implementation ready。
