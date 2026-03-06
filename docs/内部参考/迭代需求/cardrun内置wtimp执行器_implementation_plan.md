# cardrun 内置 wtimp 执行器实施计划

> 更新时间：2026-03-06 20:22 +08:00
> 上游输入：`docs/plans/2026-03-06-cardrun-wtimp-executor-design.md`、`docs/内部参考/迭代需求/cardrun内置wtimp执行器_requirements.md`
> 当前模式：`core`（进入执行链）

## 0. 输入来源清单

- design: `docs/plans/2026-03-06-cardrun-wtimp-executor-design.md`
- requirements: `docs/内部参考/迭代需求/cardrun内置wtimp执行器_requirements.md`
- 关键代码入口:
  - `scripts/coder4/coder4_bootstrap_kernel.py`
  - `scripts/coder4/wt-flow.sh`
  - `scripts/wt-flow.sh`
- 关键规则入口:
  - `.cursor/commands/jjk-cardrun.md`
  - `.cursor/commands/jjk-wtimp.md`
  - `.cursor/commands/jjk-vkplan.md`
  - `.cursor/commands/jjk-create-pr.md`

## 1. 架构影响与执行约束

### 1.1 模块边界

- 调度层（cardrun）：选卡、串行纪律、执行器路由。
- 决策层（kernel）：preflight/coverage/scope 判定 + attempt 证据写入。
- 执行层（wtimp executor mode）：单卡实现与提交证据回传。
- 收口层（wt-flow）：verify/merge 原子操作与 fail-fast。

### 1.2 状态契约

- 状态机：`missing -> todo -> inprogress -> inreview -> verified -> done`
- `dispatch` 必须伴随可验证执行证据。
- `done` 仅允许由 merge 成功写入。

## 2. implementation_tasks（机读）

```yaml
implementation_tasks:
  - task_id: T-01
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[0]
    feature_id: P1-dispatch-executor-routing
    pr_id: PR-01
    phase: Phase-1
    change_type: modify
    owner: ai-workflow
    depends_on_tasks: [ROOT]
    risk_point: dispatch 分支新增执行器调用后可能影响既有 pending 语义
    file_paths:
      - scripts/coder4/coder4_bootstrap_kernel.py
    symbols:
      - parse_args
      - decide_action
      - apply_action
      - _derive_attempt_result
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest tests/unit/test_coder4_dispatch_executor.py -q
    rollback_point: ENABLE_CARDRUN_WTIMP_EXECUTOR=false

  - task_id: T-02
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[1]
    feature_id: P1-dispatch-evidence-gate
    pr_id: PR-01
    phase: Phase-1
    change_type: modify
    owner: ai-workflow
    depends_on_tasks: [T-01]
    risk_point: 证据门禁过严可能阻断合法无改动卡片
    file_paths:
      - scripts/coder4/coder4_bootstrap_kernel.py
      - .cursor/commands/jjk-cardrun.md
      - .agents/skills/jjk-cardrun/SKILL.md
    symbols:
      - record_attempt_evidence
      - execution_evidence
      - CARDRUN_NO_COMMIT_EVIDENCE
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest tests/unit/test_coder4_commit_evidence_gate.py -q
    rollback_point: ENABLE_CARDRUN_DISPATCH_AUTORUN=false

  - task_id: T-03
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[2]
    feature_id: P1-single-merge-path
    pr_id: PR-02
    phase: Phase-2
    change_type: modify
    owner: ai-workflow
    depends_on_tasks: [T-01, T-02]
    risk_point: wtimp/cardrun 收口职责边界调整引入双 merge 回归
    file_paths:
      - .cursor/commands/jjk-wtimp.md
      - .agents/skills/jjk-wtimp/SKILL.md
      - scripts/coder4/wt-flow.sh
    symbols:
      - 提交合并与清理
      - executor_mode
      - cmd_merge
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest tests/unit/test_coder4_single_merge_path.py -q
    rollback_point: ENABLE_CARDRUN_WTIMP_EXECUTOR=false

  - task_id: T-04
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[3]
    feature_id: P1-contract-source-singleton
    pr_id: PR-02
    phase: Phase-2
    change_type: modify
    owner: ai-workflow
    depends_on_tasks: [T-01]
    risk_point: 执行器配置来源切换导致旧任务目录未配置时失败
    file_paths:
      - scripts/coder4/coder4_bootstrap_kernel.py
      - docs/plans/2026-03-06-cardrun-wtimp-executor-design.md
      - docs/内部参考/任务拆解
    symbols:
      - dispatch_executor
      - resolve_active_task_path
      - run_alignment_check
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest tests/unit/test_coder4_executor_config_source.py -q
    rollback_point: ENABLE_CARDRUN_WTIMP_EXECUTOR=false

  - task_id: T-05
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[4]
    feature_id: P1-canonical-evidence-migration
    pr_id: PR-03
    phase: Phase-3
    change_type: modify
    owner: ai-workflow
    depends_on_tasks: [T-01, T-02]
    risk_point: 读旧写新兼容窗口处理不当导致历史轮次不可回放
    file_paths:
      - scripts/coder4/coder4_bootstrap_kernel.py
      - docs/内部参考/迭代需求/cardrun内置wtimp执行器方案与最小改造清单_20260306.md
    symbols:
      - execution_evidence
      - commit_sha
      - merge_sha
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest tests/unit/test_coder4_execution_evidence_migration.py -q
    rollback_point: ENABLE_CARDRUN_EXECUTION_EVIDENCE_V2=false

  - task_id: T-06
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[5]
    feature_id: P1-doc-chain-sync
    pr_id: PR-03
    phase: Phase-3
    change_type: modify
    owner: ai-workflow
    depends_on_tasks: [T-02, T-03, T-05]
    risk_point: 主链文档未同步导致 cardrun 与下游指令口径冲突
    file_paths:
      - .cursor/commands/jjk-vkplan.md
      - .agents/skills/jjk-vkplan/SKILL.md
      - .cursor/commands/jjk-create-pr.md
      - .agents/skills/jjk-create-pr/SKILL.md
    symbols:
      - 主链路
      - 输入前置
      - 推荐链路
    acceptance_cmds:
      - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_clarify_plan_alignment.py --requirements-path docs/内部参考/迭代需求/cardrun内置wtimp执行器_requirements.md --implementation-path docs/内部参考/迭代需求/cardrun内置wtimp执行器_implementation_plan.md --output -
    rollback_point: 回退上述文档到迁移前版本
```

## 3. task_to_pr_mapping（机读）

```yaml
planning_contract:
  task_to_pr_mapping:
    - task_id: T-01
      pr_id: PR-01
      pr_branch: codex/cardrun-wtimp-pr-01
      pr_depends_on: []
      pr_subject: "dispatch 执行器路由 + commit 证据门禁"
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest tests/unit/test_coder4_dispatch_executor.py -q
        - cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest tests/unit/test_coder4_commit_evidence_gate.py -q
      rollback_point: ENABLE_CARDRUN_WTIMP_EXECUTOR=false

    - task_id: T-02
      pr_id: PR-01
      pr_branch: codex/cardrun-wtimp-pr-01
      pr_depends_on: []
      pr_subject: "dispatch 执行器路由 + commit 证据门禁"
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest tests/unit/test_coder4_dispatch_executor.py -q
        - cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest tests/unit/test_coder4_commit_evidence_gate.py -q
      rollback_point: ENABLE_CARDRUN_DISPATCH_AUTORUN=false

    - task_id: T-03
      pr_id: PR-02
      pr_branch: codex/cardrun-wtimp-pr-02
      pr_depends_on: [PR-01]
      pr_subject: "wtimp executor mode 与单 merge 收口"
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest tests/unit/test_coder4_single_merge_path.py -q
      rollback_point: ENABLE_CARDRUN_WTIMP_EXECUTOR=false

    - task_id: T-04
      pr_id: PR-02
      pr_branch: codex/cardrun-wtimp-pr-02
      pr_depends_on: [PR-01]
      pr_subject: "wtimp executor mode 与单 merge 收口"
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest tests/unit/test_coder4_executor_config_source.py -q
      rollback_point: ENABLE_CARDRUN_WTIMP_EXECUTOR=false

    - task_id: T-05
      pr_id: PR-03
      pr_branch: codex/cardrun-wtimp-pr-03
      pr_depends_on: [PR-01, PR-02]
      pr_subject: "证据 canonical 迁移 + 文档链路同步"
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest tests/unit/test_coder4_execution_evidence_migration.py -q
      rollback_point: ENABLE_CARDRUN_EXECUTION_EVIDENCE_V2=false

    - task_id: T-06
      pr_id: PR-03
      pr_branch: codex/cardrun-wtimp-pr-03
      pr_depends_on: [PR-01, PR-02]
      pr_subject: "证据 canonical 迁移 + 文档链路同步"
      acceptance_cmds:
        - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_clarify_plan_alignment.py --requirements-path docs/内部参考/迭代需求/cardrun内置wtimp执行器_requirements.md --implementation-path docs/内部参考/迭代需求/cardrun内置wtimp执行器_implementation_plan.md --output -
      rollback_point: 回退文档链路口径变更
```

## 4. tc_task_mapping（机读）

```yaml
tc_task_mapping:
  - tc_id: TC-CW-01
    task_id: T-01
    pr_id: PR-01
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest tests/unit/test_coder4_dispatch_executor.py -q
  - tc_id: TC-CW-02
    task_id: T-02
    pr_id: PR-01
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest tests/unit/test_coder4_commit_evidence_gate.py -q
  - tc_id: TC-CW-03
    task_id: T-03
    pr_id: PR-02
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest tests/unit/test_coder4_single_merge_path.py -q
  - tc_id: TC-CW-04
    task_id: T-04
    pr_id: PR-02
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest tests/unit/test_coder4_executor_config_source.py -q
  - tc_id: TC-CW-05
    task_id: T-05
    pr_id: PR-03
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest tests/unit/test_coder4_execution_evidence_migration.py -q
  - tc_id: TC-CW-06
    task_id: T-06
    pr_id: PR-03
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/check_clarify_plan_alignment.py --requirements-path docs/内部参考/迭代需求/cardrun内置wtimp执行器_requirements.md --implementation-path docs/内部参考/迭代需求/cardrun内置wtimp执行器_implementation_plan.md --output -
```

## 5. execution_contract（机读）

```yaml
execution_contract:
  delivery_mode: staged
  execution_unit: per_pr
  commit_policy: per_pr
  stop_boundary: per_pr
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
