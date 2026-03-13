# 文档分层治理与信息架构收敛实施方案

> 更新时间：2026-03-10 21:44 +08:00
> 上游设计：`workdocs/归档/设计/2026-03-10-docs-governance-layering-design.md`
> 对应需求：`workdocs/归档/需求/文档分层治理与信息架构收敛_requirements.md`
> 文档目标：定义 HOW（implementation_tasks、PR 映射、执行合同、实施就绪度），供 `$jjk-imp` 直接承接

## 0. 输入来源清单

- design：`workdocs/归档/设计/2026-03-10-docs-governance-layering-design.md`
- requirements：`workdocs/归档/需求/文档分层治理与信息架构收敛_requirements.md`
- 既有治理方案：`workdocs/归档/设计/2026-03-08-doc-single-source-dynamic-governance-design.md`
- 既有实施方案：`workdocs/归档/实施计划/文档单一真相源与动态融合治理_implementation_plan.md`

## 1. 架构影响与执行约束

### 1.1 实施目标

- 先冻结目录角色，再收口格式、同步和迁移顺序。
- 在不引入版本化和新站点工具的前提下，把文档治理从“正文当前态”升级到“目录分层 + 状态归属 + 门禁协同”。
- 保持现有 `2026-03-08` 文档治理方案有效，同时为其补上目录层面的上位约束。
- 本轮交付定义为 `Phase 1`：稳定导航收口、真实运行态外迁、迁移期兼容口径冻结。

### 1.2 执行约束

- 本轮默认 `core` 模式，不拆并行卡。
- 不直接改业务代码，只处理文档结构、守卫规则和长期决策。
- `docs/` 的终局只承接稳定真理源；本轮 `Phase 1` 允许 `docs/内部参考/迭代需求/`、`docs/内部参考/任务拆解/` 继续作为迁移期旧过程路径存在，但不再作为主导航入口；历史方案设计统一沉到 `workdocs/归档/设计/`。
- 未上线阶段禁止稳定区新增 `v2/v3/日期补丁` 命名。

### 1.3 Phase 1 边界

- 本轮只收口稳定导航、真实运行态外迁和 `Phase 1` 门禁，不直接改动 `jjk-cardrun` / `wt-flow` / `coder4_*` 的 `task_split` 读取根目录。
- `_active_task.json`、`vk_cards.json`、`preflight_status.json`、`consumption_report.json` 等 `task_split` 机器契约/过程报告 JSON 暂不强迁，以避免破坏现有执行链。
- `Phase 2` 再把上述机器契约与过程报告迁到 `workdocs/**`，并同步改造工作流脚本。

## 2. implementation_tasks（机读）

```yaml
implementation_tasks:
  - task_id: T01
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[0]
    feature_id: F1-stable-navigation-entrypoints
    pr_id: PR-01
    phase: Phase-1
    change_type: modify
    owner: doc-governance
    depends_on_tasks: [ROOT]
    risk_point: 如果主导航仍同时暴露稳定区和过程区，读者仍会从入口走错
    rollback_point: 回退 docs/README.md 与 docs/SUMMARY.md 到治理前入口
    risk_tags: [contract, docs]
    mandatory_evidence: [stable_nav_only, docs_guard_clean]
    file_paths:
      - docs/README.md
      - docs/SUMMARY.md
    symbols:
      - stable_navigation
      - role_entrypoints
    acceptance_cmds:
      - PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/docs_guard.py --strict

  - task_id: T02
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[1]
    feature_id: F2-process-layer-rehome
    pr_id: PR-01
    phase: Phase-2
    change_type: refactor
    owner: doc-governance
    depends_on_tasks: [T01]
    risk_point: 如果目录角色未收敛，过程文档会继续和稳定文档混写
    rollback_point: 回退 workdocs 新目录与过程文档迁移口径
    risk_tags: [structure, migration]
    mandatory_evidence: [process_layer_dirs_present, internal_ref_scope_frozen]
    file_paths:
      - docs/plans
      - docs/内部参考/迭代需求
      - docs/内部参考/任务拆解
      - workdocs/需求
      - workdocs/设计
      - workdocs/任务拆解
    symbols:
      - process_layer_rehome
      - internal_reference_reduction
    acceptance_cmds:
      - test -d workdocs/需求 && test -d workdocs/设计 && test -d workdocs/任务拆解

  - task_id: T03
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[2]
    feature_id: F3-runtime-artifact-rehome
    pr_id: PR-02
    phase: Phase-3
    change_type: refactor
    owner: doc-governance
    depends_on_tasks: [T02]
    risk_point: 真实运行态若继续写入 docs，目录会继续被锁文件和状态文件污染，且 `Phase 1` 边界无法成立
    rollback_point: 回退 .artifacts 路径切换，恢复旧路径只读兼容
    risk_tags: [artifact, path_migration]
    mandatory_evidence: [artifact_dirs_present, docs_runtime_artifact_zero]
    file_paths:
      - .artifacts/runs
      - .artifacts/states
      - .artifacts/generated
      - docs/内部参考/任务拆解
    symbols:
      - runtime_artifact_rehome
      - phase1_runtime_cleanup
    acceptance_cmds:
      - test -d .artifacts/runs && test -d .artifacts/states && test -d .artifacts/generated && test -z "$(find docs -type f | rg "[.](jsonl|lock)$|/[.]state/" || true)"

  - task_id: T04
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[3]
    feature_id: F4-doc-role-guard-and-sync-gate
    pr_id: PR-02
    phase: Phase-4
    change_type: modify
    owner: doc-governance
    depends_on_tasks: [T01, T02, T03]
    risk_point: 守卫若分不清真实运行态与迁移期 `task_split` 契约，会把 `Phase 2` 目标误写成 `Phase 1` 强约束
    rollback_point: 回退 docs_guard 与 doc_sync 角色化策略
    risk_tags: [contract, scripted_flow]
    mandatory_evidence: [doc_role_guard_clean, doc_sync_gate_updated, phase1_runtime_guard]
    file_paths:
      - scripts/docs_guard.py
      - .cursor/rules/doc_sync.mdc
      - scripts/check_doc_sync.sh
    symbols:
      - doc_role_guard
      - stable_nav_guard
      - runtime_pollution_guard
      - phase1_compat_guard
      - main_doc_sync_gate
    acceptance_cmds:
      - bash scripts/check_doc_sync.sh --diff-range origin/master...HEAD
      - rg -n "chat-multi-session-concurrency|langgraph-v1-adoption|workflow-gate-retirement" docs workdocs
      - test -z "$(find docs/产品文档 docs/开发文档 docs/API文档 contracts -type f | rg -v '测试报告|归档备份|防屎山记录手册' | rg '(_v[0-9]+|[-_ ]v[0-9]+|\d{4}-\d{2}-\d{2})' || true)"
      - PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/docs_guard.py --strict

  - task_id: T05
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[4]
    feature_id: F5-governance-checklists
    pr_id: PR-03
    phase: Phase-5
    change_type: modify
    owner: doc-governance
    depends_on_tasks: [T02, T03, T04]
    risk_point: 若流程清单不更新，团队会继续按旧目录习惯写文档
    rollback_point: 回退治理基线与月度校准清单的分层口径
    risk_tags: [docs, rule_sync]
    mandatory_evidence: [governance_checklist_updated]
    file_paths:
      - docs/开发文档/流程与工具/文档治理基线清单.md
      - docs/开发文档/流程与工具/文档月度校准清单.md
    symbols:
      - docs_governance_baseline
      - docs_governance_monthly_checklist
    acceptance_cmds:
      - rg -n "目录结构|内容格式|内容同步|迁移收口" docs/开发文档/流程与工具/文档治理基线清单.md docs/开发文档/流程与工具/文档月度校准清单.md

  - task_id: T06
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[5]
    feature_id: F6-decision-and-alignment-closeout
    pr_id: PR-03
    phase: Phase-6
    change_type: modify
    owner: doc-governance
    depends_on_tasks: [T04, T05]
    risk_point: 如果长期决策和规划对齐报告不落地，下游会再次退回临时性整理
    rollback_point: 回退 memory-bank 新增决策与本轮 planning artifacts
    risk_tags: [contract, scripted_flow]
    mandatory_evidence: [memory_bank_updated, clarify_plan_alignment_json, planning_temporal_gate_json, scripted_flow]
    file_paths:
      - memory-bank.md
      - workdocs/归档/需求/文档分层治理与信息架构收敛_requirements.md
      - workdocs/归档/实施计划/文档分层治理与信息架构收敛_implementation_plan.md
      - workdocs/归档/机读校验/文档分层治理与信息架构收敛_clarify_plan_alignment.json
      - workdocs/归档/机读校验/文档分层治理与信息架构收敛_planning_temporal_gate.json
    symbols:
      - docs_governance_decision_record
      - clarify_plan_alignment
      - planning_temporal_gate
    acceptance_cmds:
      - rg -n "文档分层治理与信息架构收敛" memory-bank.md
      - PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/check_workflow_contract.py --mode clarify_plan --requirements-path workdocs/归档/需求/文档分层治理与信息架构收敛_requirements.md --implementation-path workdocs/归档/实施计划/文档分层治理与信息架构收敛_implementation_plan.md --output workdocs/归档/机读校验/文档分层治理与信息架构收敛_clarify_plan_alignment.json
      - PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/check_workflow_contract.py --mode planning_temporal_gate --implementation-path workdocs/归档/实施计划/文档分层治理与信息架构收敛_implementation_plan.md --output workdocs/归档/机读校验/文档分层治理与信息架构收敛_planning_temporal_gate.json
```

## 3. task_to_pr_mapping（机读）

```yaml
task_to_pr_mapping:
  - task_id: T01
    pr_id: PR-01
    pr_branch: codex/docs-governance-layering-pr-01
    pr_depends_on: []
    pr_subject: "稳定导航与过程层骨架"
    acceptance_cmds:
      - PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/docs_guard.py --strict
    rollback_point: 回退 docs 主导航入口

  - task_id: T02
    pr_id: PR-01
    pr_branch: codex/docs-governance-layering-pr-01
    pr_depends_on: []
    pr_subject: "稳定导航与过程层骨架"
    acceptance_cmds:
      - test -d workdocs/需求 && test -d workdocs/设计 && test -d workdocs/任务拆解
    rollback_point: 回退 workdocs 目录与过程层收敛规则

  - task_id: T03
    pr_id: PR-02
    pr_branch: codex/docs-governance-layering-pr-02
    pr_depends_on: [PR-01]
    pr_subject: "运行态迁移与 Phase 1 角色化守卫"
    acceptance_cmds:
      - test -d .artifacts/runs && test -d .artifacts/states && test -d .artifacts/generated && test -z "$(find docs -type f | rg "[.](jsonl|lock)$|/[.]state/" || true)"
    rollback_point: 回退 .artifacts 路径切换

  - task_id: T04
    pr_id: PR-02
    pr_branch: codex/docs-governance-layering-pr-02
    pr_depends_on: [PR-01]
    pr_subject: "运行态迁移与 Phase 1 角色化守卫"
    acceptance_cmds:
      - bash scripts/check_doc_sync.sh --diff-range origin/master...HEAD
      - rg -n "chat-multi-session-concurrency|langgraph-v1-adoption|workflow-gate-retirement" docs workdocs
      - test -z "$(find docs/产品文档 docs/开发文档 docs/API文档 contracts -type f | rg -v '测试报告|归档备份|防屎山记录手册' | rg '(_v[0-9]+|[-_ ]v[0-9]+|\d{4}-\d{2}-\d{2})' || true)"
      - PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/docs_guard.py --strict
    rollback_point: 回退 docs_guard 与 doc_sync 角色化门禁

  - task_id: T05
    pr_id: PR-03
    pr_branch: codex/docs-governance-layering-pr-03
    pr_depends_on: [PR-01, PR-02]
    pr_subject: "治理清单与长期决策收口"
    acceptance_cmds:
      - rg -n "目录结构|内容格式|内容同步|迁移收口" docs/开发文档/流程与工具/文档治理基线清单.md docs/开发文档/流程与工具/文档月度校准清单.md
    rollback_point: 回退治理基线与月度校准清单改写

  - task_id: T06
    pr_id: PR-03
    pr_branch: codex/docs-governance-layering-pr-03
    pr_depends_on: [PR-01, PR-02]
    pr_subject: "治理清单与长期决策收口"
    acceptance_cmds:
      - rg -n "文档分层治理与信息架构收敛" memory-bank.md
      - PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/check_workflow_contract.py --mode clarify_plan --requirements-path workdocs/归档/需求/文档分层治理与信息架构收敛_requirements.md --implementation-path workdocs/归档/实施计划/文档分层治理与信息架构收敛_implementation_plan.md --output workdocs/归档/机读校验/文档分层治理与信息架构收敛_clarify_plan_alignment.json
      - PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/check_workflow_contract.py --mode planning_temporal_gate --implementation-path workdocs/归档/实施计划/文档分层治理与信息架构收敛_implementation_plan.md --output workdocs/归档/机读校验/文档分层治理与信息架构收敛_planning_temporal_gate.json
    rollback_point: 回退长期决策与 planning artifacts
```

## 4. tc_task_mapping（机读）

```yaml
tc_task_mapping:
  - tc_id: TC-DGL-01
    task_id: T01
    pr_id: PR-01
    acceptance_cmd_ref: PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/docs_guard.py --strict
  - tc_id: TC-DGL-02
    task_id: T03
    pr_id: PR-02
    acceptance_cmd_ref: test -d .artifacts/runs && test -d .artifacts/states && test -d .artifacts/generated && test -z "$(find docs -type f | rg "[.](jsonl|lock)$|/[.]state/" || true)"
  - tc_id: TC-DGL-03
    task_id: T04
    pr_id: PR-02
    acceptance_cmd_ref: rg -n "chat-multi-session-concurrency|langgraph-v1-adoption|workflow-gate-retirement" docs workdocs
  - tc_id: TC-DGL-04
    task_id: T05
    pr_id: PR-03
    acceptance_cmd_ref: rg -n "目录结构|内容格式|内容同步|迁移收口" docs/开发文档/流程与工具/文档治理基线清单.md docs/开发文档/流程与工具/文档月度校准清单.md
  - tc_id: TC-DGL-05
    task_id: T04
    pr_id: PR-02
    acceptance_cmd_ref: test -z "$(find docs/产品文档 docs/开发文档 docs/API文档 contracts -type f | rg -v '测试报告|归档备份|防屎山记录手册' | rg '(_v[0-9]+|[-_ ]v[0-9]+|\d{4}-\d{2}-\d{2})' || true)"
```

## 5. planning_contract（机读）

```yaml
planning_contract:
  topic: 文档分层治理与信息架构收敛
  source_seed_ref: clarify_handoff_contract.required.execution_chain_seed
  execution_mode: core
  task_key: PP-20260310-docs-governance-layering
  task_to_pr_mapping:
    - task_id: T01
      pr_id: PR-01
    - task_id: T02
      pr_id: PR-01
    - task_id: T03
      pr_id: PR-02
    - task_id: T04
      pr_id: PR-02
    - task_id: T05
      pr_id: PR-03
    - task_id: T06
      pr_id: PR-03
```

## 6. execution_contract（机读）

```yaml
execution_contract:
  preferred_mode: core
  execution_contract_ready: true
  delivery_mode: staged
  execution_unit: per_task
  commit_policy: single_commit
  stop_boundary: per_task
  stop_on_blocked: true
  source_seed_ref: clarify_handoff_contract.required.execution_chain_seed.execution_contract_hint
```

## 7. implementation_readiness（机读）

```yaml
implementation_readiness:
  implementation_ready: true
  blocked_by: []
  next_step: /jjk-imp
  execution_contract_ready: true
```
