# Codex Agent 写法治理（阶段一）实施计划

> 更新时间：2026-03-13
> 上游输入：`workdocs/需求/2026-03-13_codex-agent-governance-and-refactor/requirements.md`、`workdocs/设计/2026-03-13_codex-agent-governance-and-refactor/design.md`
> 当前模式：`core`（plan-only，不自动进入执行链）

## 1. 执行策略

这次按“先冻结规则入口，再补人类可读说明，再补审查门禁，最后补长期决策沉淀”来拆任务。原因很直接：如果先改 review、测试或 ADR，但规则入口还没立住，后面的文档和门禁都会缺唯一 owner。依赖上，`T-01` 必须先完成；`T-02` 和 `T-03` 可以在 `T-01` 之后并行；`T-04` 必须等 `T-03` 的 smell ID 和模板冻结后再做；`T-05` 最后做，因为它消费前面 4 个任务的最终结论。

并行点只有一个：`T-02` 与 `T-03`。其余步骤都需要先收口再往下走，避免把规则、模板和门禁写成三套口径。

## 2. 功能机制包

| feature_id | 目标 | 文件锚点 | 核心符号 | 风险点 | 验收主命令 |
|---|---|---|---|---|---|
| GOV-01 | 冻结 agent 写法规则入口与真理源 | `AGENTS.md`, `app/ai/AGENTS.md`, `.cursor/rules/agent_authoring.mdc` | `agent_authoring_route`, `smell_ids` | 根规则重新长胖或局部入口缺位 | `rg -n "agent_authoring|局部高信号|复杂度升级" AGENTS.md app/ai/AGENTS.md .cursor/rules/agent_authoring.mdc` |
| GOV-02 | 人类可读规范收口到正确位置 | `docs/README.md`, `docs/开发文档/规范/多智能体开发规范.md`, `docs/开发文档/架构设计/AI模块设计.md` | `agent_authoring_summary` | 规范文和架构文继续双写 | `rg -n "agent 写法|AI模块设计|规则分层" docs/README.md docs/开发文档/规范/多智能体开发规范.md docs/开发文档/架构设计/AI模块设计.md` |
| GOV-03 | review / verify 使用统一 smell checklist | `.cursor/commands/jjk-review.md`, `.cursor/commands/jjk-verify.md`, `workdocs/_templates/jjk_review_templates.md`, `workdocs/_templates/jjk_verify_templates.md` | `multi_decider_stack`, `keyword_primary_routing`, `missing_eval_evidence` | 规则有了，但审查阶段仍按旧口径做 | `rg -n "multi_decider_stack|keyword_primary_routing|missing_eval_evidence" .cursor/commands/jjk-review.md .cursor/commands/jjk-verify.md` |
| GOV-04 | 自动门禁冻结规则/模板/文档漂移 | `tests/unit/test_agent_governance_contract_docs.py`, `.github/workflows/agent-governance-gate.yml` | `governance_marker_freeze` | 规则回流只能靠人工发现 | `bash scripts/pytest_targeted.sh tests/unit/test_agent_governance_contract_docs.py` |
| GOV-05 | 长期决策索引和 ADR 收口 | `memory-bank.md`, `docs/内部参考/决策记录.md` | `active_decision_index`, `adr_entry` | 规则长期有效却不写回仓库记忆 | `rg -n "Codex Agent 写法治理|agent authoring|复杂度升级" memory-bank.md docs/内部参考/决策记录.md` |

## 3. implementation_tasks

```yaml
implementation_tasks:
  - task_id: T-01
    feature_id: GOV-01
    design_item_refs: [D-01, D-04, D-05]
    requirement_ids: [FR-01, FR-04, FR-05, NFR-01, NFR-02, NFR-03]
    goal: 冻结仓库级路由、app/ai 局部入口和 Layer2 agent 专项规则，让 Codex 默认能命中同一套 agent 写法口径。
    file_paths:
      - AGENTS.md
      - app/ai/AGENTS.md
      - .cursor/rules/agent_authoring.mdc
      - CLAUDE.md
      - scripts/sync_rules_to_cc.py
    symbols:
      - agent_authoring_route
      - local_ai_governance
      - smell_ids
      - sync_rules_to_cc
    module_changes:
      - 根 AGENTS.md 只新增 agent 专项路由入口，不吸纳细则全文。
      - 新增 app/ai/AGENTS.md，承载 5 到 7 条局部高信号规则。
      - 新增 .cursor/rules/agent_authoring.mdc，承载 smell IDs、复杂度升级门槛、contract-first 约束与 eval 要求。
      - 运行同步脚本，更新 CLAUDE 镜像与命令镜像。
    deletion_actions:
      - 禁止继续把 agent 细则直接扩写回根 AGENTS.md。
    risk_tags: [contract, rule_sync, structure]
    mandatory_evidence: [agent_rule_route_present, local_ai_agents_present, smell_ids_frozen, claude_sync_clean]
    acceptance_cmds:
      - kind: scripted_flow
        cmd: rg -n "agent_authoring|局部高信号|复杂度升级" AGENTS.md app/ai/AGENTS.md .cursor/rules/agent_authoring.mdc
      - kind: scripted_flow
        cmd: python3 scripts/sync_rules_to_cc.py --skip-codex-prompts

  - task_id: T-02
    feature_id: GOV-02
    design_item_refs: [D-02, D-05]
    requirement_ids: [FR-02, FR-05, NFR-02, NFR-05]
    goal: 把“以后怎么写 agent”和“系统现在怎么跑”分开放到正确文档层，减少人类阅读误导。
    file_paths:
      - docs/README.md
      - docs/开发文档/规范/多智能体开发规范.md
      - docs/开发文档/架构设计/AI模块设计.md
    symbols:
      - agent_authoring_summary
      - runtime_architecture_source_link
      - ai_collaboration_layering
    module_changes:
      - docs/README.md 补 agent 专项规则承载层说明。
      - 多智能体开发规范改成稳定规则摘要，不再承载运行态架构大段描述。
      - AI 模块设计文档补一条对规范文档的反向指向，明确运行态真理源。
    deletion_actions:
      - 删除 docs/开发文档/规范/多智能体开发规范.md 中错误承载的旧架构概览章节。
    risk_tags: [docs, structure]
    mandatory_evidence: [rules_layering_visible, runtime_architecture_source_single, old_overview_removed]
    acceptance_cmds:
      - kind: scripted_flow
        cmd: rg -n "agent 写法|规则分层|AI模块设计" docs/README.md docs/开发文档/规范/多智能体开发规范.md docs/开发文档/架构设计/AI模块设计.md

  - task_id: T-03
    feature_id: GOV-03
    design_item_refs: [D-03, D-06, D-07]
    requirement_ids: [FR-03, FR-06, FR-07, NFR-01, NFR-04, NFR-05]
    goal: 让 review 和 verify 在 agent 相关任务里统一检查复杂度升级证据、smell IDs 和真实样本要求。
    file_paths:
      - .cursor/commands/jjk-review.md
      - .cursor/commands/jjk-verify.md
      - workdocs/_templates/jjk_review_templates.md
      - workdocs/_templates/jjk_verify_templates.md
      - .agents/skills/jjk-review/SKILL.md
      - .agents/skills/jjk-verify/SKILL.md
    symbols:
      - multi_decider_stack
      - keyword_primary_routing
      - dual_truth_design
      - speculative_fallback
      - missing_eval_evidence
    module_changes:
      - jjk-review 增加 agent smell checklist 与 severity 判断。
      - jjk-verify 增加复杂度升级证据和 eval evidence 检查项。
      - review / verify 模板补统一 smell ID、例外条件和证据槽位。
      - 运行镜像同步，更新对应 SKILL.md。
    deletion_actions:
      - 废弃“只靠 review 评论临时命名坏味道”的路径。
    risk_tags: [contract, review_gate, rule_sync]
    mandatory_evidence: [smell_checklist_present, eval_evidence_gate_present, mirror_sync_clean]
    acceptance_cmds:
      - kind: scripted_flow
        cmd: rg -n "multi_decider_stack|keyword_primary_routing|missing_eval_evidence|复杂度升级证据" .cursor/commands/jjk-review.md .cursor/commands/jjk-verify.md workdocs/_templates/jjk_review_templates.md workdocs/_templates/jjk_verify_templates.md
      - kind: scripted_flow
        cmd: python3 scripts/sync_rules_to_cc.py --skip-codex-prompts

  - task_id: T-04
    feature_id: GOV-04
    design_item_refs: [D-04, D-06, D-07]
    requirement_ids: [FR-04, FR-06, FR-07, NFR-03, NFR-04]
    goal: 新增 agent governance drift gate，让规则文件、模板和关键 smell ID 发生漂移时能被自动阻断。
    file_paths:
      - tests/unit/test_agent_governance_contract_docs.py
      - .github/workflows/agent-governance-gate.yml
      - tests/unit/test_semantic_keyword_boundary_gate.py
    symbols:
      - governance_marker_freeze
      - agent_governance_gate
      - semantic_keyword_boundary
    module_changes:
      - 新增测试，冻结规则文件、模板和 smell ID 的关键 marker。
      - 新增 workflow，只在 agent 治理相关文档/规则/模板/测试变更时触发。
      - 复用现有 test_semantic_keyword_boundary_gate.py，不另造第二套关键词边界门禁。
    deletion_actions:
      - 不新增第二套与现有 semantic keyword gate 重复的边界测试。
    risk_tags: [contract, ci, test]
    mandatory_evidence: [governance_drift_gate_green, semantic_boundary_gate_reused]
    acceptance_cmds:
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh tests/unit/test_agent_governance_contract_docs.py
      - kind: unit
        cmd: bash scripts/pytest_targeted.sh tests/unit/test_semantic_keyword_boundary_gate.py
      - kind: scripted_flow
        cmd: rg -n "agent-governance-gate|test_agent_governance_contract_docs" .github/workflows/agent-governance-gate.yml

  - task_id: T-05
    feature_id: GOV-05
    design_item_refs: [D-02, D-07]
    requirement_ids: [FR-02, FR-07]
    goal: 把阶段一治理结论写回长期决策索引和 ADR，避免规则只停留在过程文档里。
    file_paths:
      - memory-bank.md
      - docs/内部参考/决策记录.md
    symbols:
      - active_decision_index
      - codex_agent_authoring_adr
    module_changes:
      - memory-bank.md 新增 ACTIVE 决策摘要。
      - 决策记录补完整背景、决策、后果和失效条件。
    deletion_actions:
      - 不再把长期默认写法只留在 workdocs 过程材料里。
    risk_tags: [docs, contract]
    mandatory_evidence: [memory_bank_updated, adr_updated]
    acceptance_cmds:
      - kind: scripted_flow
        cmd: rg -n "Codex Agent 写法治理|agent authoring|复杂度升级" memory-bank.md docs/内部参考/决策记录.md
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
  design_source: workdocs/设计/2026-03-13_codex-agent-governance-and-refactor/design.md
  requirements_source: workdocs/需求/2026-03-13_codex-agent-governance-and-refactor/requirements.md
```

## 6. implementation_readiness

```yaml
implementation_readiness:
  implementation_ready: true
  execution_contract_ready: true
  requirements_ready: true
  traceability_ready: true
  blocking_issue_count: 0
  readiness_note: approved_design_can_split_into_five_tasks
```
