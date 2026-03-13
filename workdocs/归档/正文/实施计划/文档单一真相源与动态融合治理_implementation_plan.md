# 文档单一真相源与动态融合治理实施方案

> 更新时间：2026-03-08 14:35 +08:00
> 上游设计：`workdocs/归档/正文/设计/2026-03-08-doc-single-source-dynamic-governance-design.md`
> 对应需求：`workdocs/归档/正文/需求/文档单一真相源与动态融合治理_requirements.md`
> 文档目标：定义 HOW（implementation_tasks、PR 映射、执行合同、实施就绪度），供 `$jjk-imp` 直接承接

## 1. 目标与范围

### 1.1 实施目标

- 将文档治理规则从“有文档即可”升级为“主文档必须表达当前态”。
- 在不推倒整个文档体系的前提下，完成角色化守卫、主文档强门禁和三份代表性主文档融合治理。
- 为后续所有功能迭代建立可复用的文档治理真理源与执行合同。

### 1.2 实施范围

- 治理规则：`.cursor/rules/doc_sync.mdc`
- 文档守卫：`scripts/docs_guard.py`
- 主文档同步门禁：`scripts/check_doc_sync.sh`、`.githooks/pre-commit`、`.github/workflows/doc-sync.yml`
- 主文档治理样板：`docs/产品文档/聊天系统需求.md`、`docs/产品文档/管理后台需求.md`、`docs/开发文档/架构设计/AI模块设计.md`
- 文档索引：`docs/SUMMARY.md`
- 长期决策：`memory-bank.md`

### 1.3 非范围

- 不重写全部历史产品/架构文档。
- 不改测试报告、防屎山记录手册等历史型文档正文结构。
- 不在本轮引入并行拆卡与多 worktree 实施。

## 2. implementation_tasks（机读）

```yaml
implementation_tasks:
  - task_id: T01
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[0]
    feature_id: F1-governance-rule-freeze
    pr_id: PR-01
    phase: Phase-1
    change_type: modify
    owner: doc-governance
    depends_on_tasks: [ROOT]
    risk_point: 若规则文本未冻结，后续脚本与主文档治理会继续漂移
    rollback_point: 回退主文档角色策略与 touch-once merge 规则定义
    risk_tags: [contract, rule_sync]
    mandatory_evidence: [rule_text_frozen, workflow_policy_updated]
    file_paths:
      - .cursor/rules/doc_sync.mdc
      - docs/开发文档/流程与工具/开发工作流.md
    symbols:
      - main_doc_role_policy
      - touch_once_merge_policy
    acceptance_cmds:
      - rg -n "主文档|当前态|触达即融合|增量需求" .cursor/rules/doc_sync.mdc docs/开发文档/流程与工具/开发工作流.md
      - 先执行 `bash scripts/repo_python.sh` 获取解释器，再执行 `<PYTHON_BIN> scripts/docs_guard.py --strict`

  - task_id: T02
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[1]
    feature_id: F2-doc-role-guard
    pr_id: PR-01
    phase: Phase-2
    change_type: modify
    owner: doc-governance
    depends_on_tasks: [T01]
    risk_point: 若角色识别不清，历史型文档会被误伤或主文档继续漏检
    rollback_point: 回退 current_state 文档规则与 doc_role 识别逻辑
    risk_tags: [contract, scripted_flow]
    mandatory_evidence: [docs_guard_pass, doc_role_manifest_verified, scripted_flow]
    file_paths:
      - scripts/docs_guard.py
    symbols:
      - current_state_doc_checks
      - doc_role_manifest
      - legacy_allowlist
    acceptance_cmds:
      - 先执行 `bash scripts/repo_python.sh` 获取解释器，再执行 `<PYTHON_BIN> scripts/docs_guard.py --strict`

  - task_id: T03
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[2]
    feature_id: F3-main-doc-sync-gate
    pr_id: PR-01
    phase: Phase-3
    change_type: modify
    owner: doc-governance
    depends_on_tasks: [T01, T02]
    risk_point: 若门禁仍只检查“有没有 docs 变更”，过程文档替代主文档的问题会继续发生
    rollback_point: 回退主文档强门禁，恢复旧版仅提示式检查
    risk_tags: [contract, scripted_flow]
    mandatory_evidence: [doc_sync_fail_fast_verified, ci_gate_updated, scripted_flow]
    file_paths:
      - scripts/check_doc_sync.sh
      - .githooks/pre-commit
      - .github/workflows/doc-sync.yml
    symbols:
      - main_doc_sync_gate
    acceptance_cmds:
      - bash scripts/check_doc_sync.sh --diff-range origin/master...HEAD

  - task_id: T04
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[3]
    feature_id: F4-main-doc-merge-migration
    pr_id: PR-01
    phase: Phase-4
    change_type: modify
    owner: doc-governance
    depends_on_tasks: [T01, T02, T03]
    risk_point: 若融合时误删历史事实，会导致主文档短了但过程证据没有承接
    rollback_point: 回退三份主文档的融合改写，恢复治理前版本
    risk_tags: [contract, scripted_flow]
    mandatory_evidence: [main_doc_merge_diff, docs_guard_pass, summary_updated, scripted_flow]
    file_paths:
      - docs/产品文档/聊天系统需求.md
      - docs/产品文档/管理后台需求.md
      - docs/开发文档/架构设计/AI模块设计.md
      - docs/SUMMARY.md
    symbols:
      - current_state_sections
      - architecture_current_state_sections
      - docs_summary_entries
    acceptance_cmds:
      - rg -n "增量需求|实现进展" docs/产品文档/聊天系统需求.md docs/产品文档/管理后台需求.md docs/开发文档/架构设计/AI模块设计.md
      - rg -n 更新时间： docs/产品文档 docs/开发文档/架构设计 docs/API文档 --glob \*.md
      - 先执行 `bash scripts/repo_python.sh` 获取解释器，再执行 `<PYTHON_BIN> scripts/docs_guard.py --strict`

  - task_id: T05
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[4]
    feature_id: F5-memory-bank-decision
    pr_id: PR-01
    phase: Phase-5
    change_type: modify
    owner: doc-governance
    depends_on_tasks: [T04]
    risk_point: 若长期决策不入 memory-bank，后续代理仍会退回增量堆叠习惯
    rollback_point: 回退本轮长期决策记录，恢复 memory-bank 治理前状态
    risk_tags: [contract]
    mandatory_evidence: [memory_bank_updated]
    file_paths:
      - memory-bank.md
    symbols:
      - active_decision_index
      - decision_record_doc_dynamic_merge
    acceptance_cmds:
      - rg -n "文档单一真相源与动态融合治理|主文档只表达当前态" memory-bank.md

  - task_id: T06
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[5]
    feature_id: F6-plan-alignment-and-gate
    pr_id: PR-01
    phase: Phase-6
    change_type: add
    owner: doc-governance
    depends_on_tasks: [T01, T02, T03, T04, T05]
    risk_point: 若规划桥接和 temporal gate 不过，下游执行会带着不稳定契约进入实施
    rollback_point: 删除本轮 planning artifacts 与对齐报告
    risk_tags: [contract, scripted_flow]
    mandatory_evidence: [clarify_plan_alignment_json, planning_temporal_gate_json, scripted_flow]
    file_paths:
      - workdocs/归档/正文/需求/文档单一真相源与动态融合治理_requirements.md
      - workdocs/归档/正文/实施计划/文档单一真相源与动态融合治理_implementation_plan.md
    symbols:
      - clarify_plan_alignment
      - planning_temporal_gate
    acceptance_cmds:
      - 先执行 `bash scripts/repo_python.sh` 获取解释器，再执行 `<PYTHON_BIN> scripts/check_workflow_contract.py --mode clarify_plan --requirements-path workdocs/归档/正文/需求/文档单一真相源与动态融合治理_requirements.md --implementation-path workdocs/归档/正文/实施计划/文档单一真相源与动态融合治理_implementation_plan.md --output workdocs/归档/报告/机读校验/文档单一真相源与动态融合治理_clarify_plan_alignment.json`
      - 先执行 `bash scripts/repo_python.sh` 获取解释器，再执行 `<PYTHON_BIN> scripts/check_workflow_contract.py --mode planning_temporal_gate --implementation-path workdocs/归档/正文/实施计划/文档单一真相源与动态融合治理_implementation_plan.md --output workdocs/归档/报告/机读校验/文档单一真相源与动态融合治理_planning_temporal_gate.json`
```

## 3. task_to_pr_mapping（机读）

```yaml
task_to_pr_mapping:
  - task_id: T01
    pr_id: PR-01
    pr_branch: codex/doc-governance-core
    pr_depends_on: []
    pr_subject: "文档治理核心规则、门禁与主文档融合收口"
    acceptance_cmds:
      - rg -n "主文档|当前态|触达即融合|增量需求" .cursor/rules/doc_sync.mdc docs/开发文档/流程与工具/开发工作流.md
    rollback_point: 回退文档治理核心规则与工作流口径

  - task_id: T02
    pr_id: PR-01
    pr_branch: codex/doc-governance-core
    pr_depends_on: []
    pr_subject: "文档治理核心规则、门禁与主文档融合收口"
    acceptance_cmds:
      - 先执行 `bash scripts/repo_python.sh` 获取解释器，再执行 `<PYTHON_BIN> scripts/docs_guard.py --strict`
    rollback_point: 回退 docs_guard 角色识别与 current_state 检查

  - task_id: T03
    pr_id: PR-01
    pr_branch: codex/doc-governance-core
    pr_depends_on: []
    pr_subject: "文档治理核心规则、门禁与主文档融合收口"
    acceptance_cmds:
      - bash scripts/check_doc_sync.sh --diff-range origin/master...HEAD
    rollback_point: 回退主文档同步强门禁

  - task_id: T04
    pr_id: PR-01
    pr_branch: codex/doc-governance-core
    pr_depends_on: []
    pr_subject: "文档治理核心规则、门禁与主文档融合收口"
    acceptance_cmds:
      - 先执行 `bash scripts/repo_python.sh` 获取解释器，再执行 `<PYTHON_BIN> scripts/docs_guard.py --strict`
    rollback_point: 回退三份主文档融合改写与 SUMMARY 更新

  - task_id: T05
    pr_id: PR-01
    pr_branch: codex/doc-governance-core
    pr_depends_on: []
    pr_subject: "文档治理核心规则、门禁与主文档融合收口"
    acceptance_cmds:
      - rg -n "文档单一真相源与动态融合治理|主文档只表达当前态" memory-bank.md
    rollback_point: 回退 memory-bank 新增决策记录

  - task_id: T06
    pr_id: PR-01
    pr_branch: codex/doc-governance-core
    pr_depends_on: []
    pr_subject: "文档治理核心规则、门禁与主文档融合收口"
    acceptance_cmds:
      - 先执行 `bash scripts/repo_python.sh` 获取解释器，再执行 `<PYTHON_BIN> scripts/check_workflow_contract.py --mode clarify_plan --requirements-path workdocs/归档/正文/需求/文档单一真相源与动态融合治理_requirements.md --implementation-path workdocs/归档/正文/实施计划/文档单一真相源与动态融合治理_implementation_plan.md --output workdocs/归档/报告/机读校验/文档单一真相源与动态融合治理_clarify_plan_alignment.json`
      - 先执行 `bash scripts/repo_python.sh` 获取解释器，再执行 `<PYTHON_BIN> scripts/check_workflow_contract.py --mode planning_temporal_gate --implementation-path workdocs/归档/正文/实施计划/文档单一真相源与动态融合治理_implementation_plan.md --output workdocs/归档/报告/机读校验/文档单一真相源与动态融合治理_planning_temporal_gate.json`
    rollback_point: 删除 planning 对齐与 temporal gate 报告
```

## 4. planning_contract（机读）

```yaml
planning_contract:
  topic: 文档单一真相源与动态融合治理
  source_seed_ref: clarify_handoff_contract.required.execution_chain_seed
  execution_mode: core
  task_key: PP-20260308-doc-single-source-dynamic-governance
  task_to_pr_mapping:
    - task_id: T01
      pr_id: PR-01
    - task_id: T02
      pr_id: PR-01
    - task_id: T03
      pr_id: PR-01
    - task_id: T04
      pr_id: PR-01
    - task_id: T05
      pr_id: PR-01
    - task_id: T06
      pr_id: PR-01
```

## 5. execution_contract（机读）

```yaml
execution_contract:
  preferred_mode: core
  execution_contract_ready: true
  delivery_mode: one_shot
  execution_unit: all_tasks
  commit_policy: single_commit
  stop_boundary: none
  stop_on_blocked: true
  temporal_gate_forbidden: true
  context_verified: true
  source_seed_ref: clarify_handoff_contract.required.execution_chain_seed.execution_contract_hint
```

## 6. implementation_readiness（机读）

```yaml
implementation_readiness:
  implementation_ready: true
  execution_contract_ready: true
  requirements_ready: true
  traceability_ready: true
  blocked_by: []
  next_step: $jjk-imp
  readiness_note: approved_design_and_core_mode_plan_ready
```

## 7. 风险、回退与实施顺序

1. `T01 -> T02 -> T03` 必须先完成，因为不先收紧规则与门禁，后续主文档治理无法稳定收口。
2. `T04` 必须晚于门禁落地，否则会出现“改完三份主文档但守卫还不会检查”的半治理状态。
3. `T05` 只在 `T04` 后执行，因为长期决策必须基于已落地的治理策略，而不是空口约定。
4. `T06` 最后执行，用来证明 clarify->plan 桥接与 temporal gate 都已通过。
5. 本轮任何阶段若出现“需要再新增一套补充段规则”的冲动，都视为结构回退信号，应回到设计重审而不是 patch。

## 8. TC 覆盖映射

```yaml
tc_execution_mapping:
  - tc_id: TC-DSG-01
    task_id: T01
    pr_id: PR-01
  - tc_id: TC-DSG-02
    task_id: T02
    pr_id: PR-01
  - tc_id: TC-DSG-03
    task_id: T04
    pr_id: PR-01
  - tc_id: TC-DSG-04
    task_id: T04
    pr_id: PR-01
  - tc_id: TC-DSG-05
    task_id: T04
    pr_id: PR-01
  - tc_id: TC-DSG-06
    task_id: T02
    pr_id: PR-01
  - tc_id: TC-DSG-07
    task_id: T03
    pr_id: PR-01
  - tc_id: TC-DSG-08
    task_id: T06
    pr_id: PR-01
```
