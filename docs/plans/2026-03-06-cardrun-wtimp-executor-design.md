# CardRun 内置 WTImp 执行器设计说明（替换 imp-ws）

## 1. scope_contract
- 目标:
  - 将 `cardrun` 的 dispatch 执行器由 `jjk-imp-ws` 迁移为 `jjk-wtimp`，形成“串行编排 + 单卡隔离执行 + 证据化收口”的统一链路。
  - 消除当前“dispatch 仅 pending、不执行实现”的断点，确保每张卡在同一轮内可产出可审计执行证据。
  - 冻结可直接进入 `/jjk-plan` 的设计契约，避免继续并存“`imp-ws` 路径”与“`wtimp` 路径”导致行为分叉。
- 范围:
  - 调度与内核：`scripts/coder4/coder4_bootstrap_kernel.py`
  - git/worktree 收口：`scripts/coder4/wt-flow.sh`、`scripts/wt-flow.sh`
  - 执行命令契约：`.cursor/commands/jjk-cardrun.md`、`.cursor/commands/jjk-wtimp.md`
  - 技能镜像同步：`.agents/skills/jjk-cardrun/SKILL.md`、`.agents/skills/jjk-wtimp/SKILL.md`、关联主链文档
  - 回归测试：`tests/unit/` 下 dispatch/merge/evidence 相关测试
- 边界:
  - 不改动业务功能实现（仅改工程流执行链与证据契约）。
  - 不改动 VK API 业务语义（状态字段、任务模型保持不变）。
  - 不新增第二条并行收口路径（禁止“双 merge 主路径”）。
- 成功标准:
  - dispatch 动作不再只返回 `dispatch_pending`，而是进入 `wtimp` 执行并回填结构化证据。
  - `commit_sha` 缺失时在代码层 fail-fast，阻断进入后续推进。
  - `verify -> merge` 主路径保持唯一，杜绝双重 merge。
  - 兼容旧证据字段读取，新增 canonical 结构字段写入，保证可回放与可审计。

## 2. product_contract（PRD-Lite）
product_contract:
  target_users:
    - 平台工程负责人（维护 cardrun/coder4 工程流）
    - 任务执行代理维护者（维护 `jjk-*` 技能链）
    - 质量与验收负责人（依赖 ledger 证据判定）
  core_scenarios:
    - 串行卡片执行时，dispatch 自动调用 `wtimp` 完成单卡实现并返回提交证据。
    - 卡片收口时，仅存在一条 `verify -> merge` 路径，避免重复收口。
    - 出现缺失提交证据、上下文错配、映射缺失时，系统明确 fail-fast 并给可追踪错误码。
  business_goals:
    - KPI-1: dispatch 自动执行闭环率 `>= 95%`（不再停留 pending）
    - KPI-2: 无 `commit_sha` 仍推进到 merge 的事件数 `= 0`
    - KPI-3: 双重 merge 事故数 `= 0`
    - KPI-4: 失败轮次 100% 具备结构化阻断证据（可回溯）
  non_goals:
    - 本轮不重构 `jjk-plan/jjk-vkplan` 的卡片拆解算法。
    - 本轮不改造具体业务模块（AI、前端、数据库逻辑）。
    - 本轮不引入新的项目管理后端接口。
  acceptance_gates:
    - AG-01: `cardrun` 默认执行器切换为 `wtimp` 且可开关回退。
    - AG-02: dispatch 成功轮次必须输出 canonical `execution_evidence`，含 `executor_mode/commit_sha`。
    - AG-03: 缺失 `commit_sha` 命中 `CARDRUN_NO_COMMIT_EVIDENCE`，且状态不推进。
    - AG-04: `verify -> merge` 只执行一次，不存在重复 merge 日志。
    - AG-05: 文档链路（cardrun/wtimp/vkplan/create-pr）主链口径一致。
  release_constraints:
    - 项目未上线，优先消除结构性债务与执行不确定性。
    - 必须保留回退锚点（开关默认 `true`，回退时置 `false`）。

## 3. architecture_contract
- 模块边界与职责:

| 模块 | 职责 | 禁止事项 |
| --- | --- | --- |
| `cardrun`（调度层） | 选卡、串行纪律、错误码映射、下游执行器路由 | 禁止直接承担业务实现细节 |
| `bootstrap kernel`（决策层） | preflight/coverage/scope 判定，输出 action 与证据结构 | 禁止并存多套 dispatch 语义 |
| `wtimp executor`（执行层） | 单卡实现、提交、执行回执归档（executor mode） | 禁止重复执行 create/merge（由编排定义） |
| `wt-flow`（git 原子层） | worktree 生命周期、verify、merge、ahead 校验 | 禁止感知业务任务语义 |
| `ledger/state`（证据层） | 结构化记录尝试、失败原因、提交/合并证据 | 禁止写入非结构化自由文本作为唯一证据 |

- 端到端数据流:
  1. `cardrun` 触发 `kernel` 计算动作。
  2. 若动作为 `dispatch`，调用 `wtimp` 执行器模式（单卡上下文）。
  3. `wtimp` 完成实现与提交后回传 `commit_sha/subagent_id/ws_file`。
  4. `cardrun` 执行唯一主路径 `verify -> merge`。
  5. `kernel`/`ledger` 写入 canonical `execution_evidence` 与结果状态。

- 状态生命周期:
  - `missing -> todo -> inprogress -> inreview -> verified -> done`
  - 约束:
    - `dispatch` 必须落真实执行证据，不能仅 `pending`。
    - `verified` 只由 `wt-flow verify` 写入。
    - `done` 只由 `merge` 成功后写入。

- 异常语义（单策略冻结）:
  - `commit_sha` 缺失: 统一返回 `CARDRUN_NO_COMMIT_EVIDENCE` 并阻断推进。
  - 执行器失败: 统一返回 `CARDRUN_SUBAGENT_FAILED`，保留原始错误信息。
  - 上下文错配: 统一返回 `CARDRUN_CONTEXT_INVALID` 或 `WTIMP_CONTEXT_INVALID`。
  - 合同缺失: 统一返回 `CARDRUN_PR_MAPPING_MISSING`。

- 契约源唯一化:
  - 运行时执行器选择唯一来源：`_active_task.json.dispatch_executor`。
  - 代码读取策略：只读该字段；文档与技能文件为镜像说明，不作为运行时真理源。

- 回放归一（canonical 字段）:
  - canonical 结构字段：`execution_evidence`。
  - 字段集合：`executor_mode/subagent_id/ws_file/commit_sha/merge_sha/attempt_id`。
  - 迁移语义：读旧写新（读取历史平铺字段 `subagent_id/ws_file/commit_sha/merge_sha`，新写统一写入 `execution_evidence`，并保留旧字段一个版本窗口用于兼容）。

## 4. 最终方案（冻结）
- 方案描述:
  - `cardrun` 保持编排者身份不变；dispatch 下游执行器从 `imp-ws` 切至 `wtimp`。
  - `wtimp` 增加 `executor_mode=cardrun_dispatch`（或等价语义）：在该模式下执行“单卡实现 + commit 证据回传”，不重复接管主链 merge。
  - `verify -> merge` 仍由 `cardrun/wt-flow` 统一收口，确保状态机单入口。
  - `kernel` 增加 dispatch 执行分支并升级证据写入为 canonical `execution_evidence`。

- 关键决策:
  - KD-01: 执行器统一到 `wtimp`，淘汰 `imp-ws` 在 cardrun 主链的默认地位。
  - KD-02: merge 主路径唯一归属 `wt-flow`，禁止“双 merge”。
  - KD-03: `commit_sha` 由文档约束升级为代码门禁。
  - KD-04: 证据字段采用 canonical 嵌套对象，执行读旧写新迁移。

## 5. 决策权衡（仅放弃原因）
- 放弃路径: 仅在文档把 `imp-ws` 改名为 `wtimp`，不改执行语义。
  - 放弃原因: 无法解决 dispatch pending 断链与证据缺失问题。
- 放弃路径: 让 `wtimp` 完整接管 create/verify/merge。
  - 放弃原因: 与现有 `cardrun/wt-flow` 收口职责重叠，容易引入双重 merge。
- 放弃路径: 维持平铺证据字段，不做 canonical 归一。
  - 放弃原因: 回放与审计会持续出现字段漂移，难以稳定验证。

## 6. risk_rollback_contract
risk_rollback_contract:
  key_risks:
    - risk_id: R-01
      description: dispatch 已执行成功但证据回填失败，导致“实际有提交、状态判定缺证据”。
      counterexample: executor 成功返回，ledger 写入异常，`commit_sha` 缺失。
      impact: 卡片被误阻断，需人工补证据。
      verify_cmd: "venv/bin/python -m pytest tests/unit/test_coder4_dispatch_executor.py -q"
    - risk_id: R-02
      description: cardrun 与 wtimp 均触发 merge，出现双重收口。
      counterexample: executor mode 未禁用 merge，随后 cardrun 又执行一次 `wt-flow merge`。
      impact: 状态错乱、重复日志、潜在冲突。
      verify_cmd: "venv/bin/python -m pytest tests/unit/test_coder4_single_merge_path.py -q"
    - risk_id: R-03
      description: 旧字段兼容读取缺失，历史轮次回放失败。
      counterexample: 历史 attempt 仅含平铺字段，新代码仅读 `execution_evidence`。
      impact: 审计链断裂。
      verify_cmd: "venv/bin/python -m pytest tests/unit/test_coder4_execution_evidence_migration.py -q"
  rollback_anchors:
    - key: ENABLE_CARDRUN_WTIMP_EXECUTOR
      default: true
      rollback: false
      effect: 回退到旧执行器路由（`imp-ws`）
    - key: ENABLE_CARDRUN_DISPATCH_AUTORUN
      default: true
      rollback: false
      effect: 回退为 dispatch 仅决策不自动执行
    - key: ENABLE_CARDRUN_EXECUTION_EVIDENCE_V2
      default: true
      rollback: false
      effect: 回退为旧平铺证据字段写入

## 7. requirement_seeds（字段级需求原子）
```yaml
requirement_seeds:
  - design_item: D-01
    fr_id: FR-CARDRUN-EXECUTOR-ROUTING
    trigger: cardrun 进入 dispatch
    input_contract:
      required_fields: [action, card_id, ws_file, _active_task.dispatch_executor]
      optional_fields: [executor_override]
      defaults:
        _active_task.dispatch_executor: wtimp
    output_contract:
      required_fields: [executor_mode, dispatch_result]
      optional_fields: [subagent_id, ws_file]
    failure_semantics: 执行器不可用时返回 CARDRUN_SUBAGENT_FAILED
    observability_fields: [task_key, card_id, executor_mode, attempt_id]
    rollback_anchor: ENABLE_CARDRUN_WTIMP_EXECUTOR=false
    acceptance_cmd_ref: venv/bin/python -m pytest tests/unit/test_coder4_dispatch_executor.py -q

  - design_item: D-02
    fr_id: FR-CARDRUN-COMMIT-EVIDENCE-GATE
    trigger: dispatch 执行完成，进入证据校验
    input_contract:
      required_fields: [commit_sha, action=dispatch]
      optional_fields: [merge_sha]
      defaults: {}
    output_contract:
      required_fields: [gate_passed]
      optional_fields: [blocked_code]
    failure_semantics: commit_sha 缺失时返回 CARDRUN_NO_COMMIT_EVIDENCE 并阻断状态推进
    observability_fields: [task_key, card_id, commit_sha, blocked_code]
    rollback_anchor: ENABLE_CARDRUN_DISPATCH_AUTORUN=false
    acceptance_cmd_ref: venv/bin/python -m pytest tests/unit/test_coder4_commit_evidence_gate.py -q

  - design_item: D-03
    fr_id: FR-CARDRUN-SINGLE-MERGE-PATH
    trigger: 卡片进入 done_gate 收口
    input_contract:
      required_fields: [card_status=verified, merge_owner=wt_flow]
      optional_fields: [executor_mode]
      defaults:
        merge_owner: wt_flow
    output_contract:
      required_fields: [merge_called_once]
      optional_fields: [merge_commit]
    failure_semantics: 命中双 merge 风险时返回 CARDRUN_MERGE_FAILED 并停止
    observability_fields: [task_key, card_id, merge_owner, merge_count]
    rollback_anchor: ENABLE_CARDRUN_WTIMP_EXECUTOR=false
    acceptance_cmd_ref: venv/bin/python -m pytest tests/unit/test_coder4_single_merge_path.py -q

  - design_item: D-04
    fr_id: FR-CARDRUN-CONTRACT-SOURCE-SINGLETON
    trigger: 初始化 dispatch 上下文
    input_contract:
      required_fields: [_active_task.dispatch_executor]
      optional_fields: [legacy_executor_fields]
      defaults:
        _active_task.dispatch_executor: wtimp
    output_contract:
      required_fields: [executor_mode]
      optional_fields: [legacy_read_hit]
    failure_semantics: 缺失配置且无默认值时返回 WTIMP_INPUT_INCOMPLETE
    observability_fields: [task_key, executor_mode, config_source]
    rollback_anchor: ENABLE_CARDRUN_WTIMP_EXECUTOR=false
    acceptance_cmd_ref: venv/bin/python -m pytest tests/unit/test_coder4_executor_config_source.py -q

  - design_item: D-05
    fr_id: FR-CARDRUN-EVIDENCE-CANONICAL-FIELD
    trigger: 记录 attempt 证据
    input_contract:
      required_fields: [execution_evidence.executor_mode, execution_evidence.commit_sha]
      optional_fields: [subagent_id, ws_file, merge_sha]
      defaults: {}
    output_contract:
      required_fields: [execution_evidence]
      optional_fields: [legacy_flat_fields]
    failure_semantics: canonical 字段缺失时返回 CLARIFY_REPLAY_CANONICAL_UNSET 并阻断审批下游
    observability_fields: [attempt_id, executor_mode, commit_sha, migration_mode]
    rollback_anchor: ENABLE_CARDRUN_EXECUTION_EVIDENCE_V2=false
    acceptance_cmd_ref: venv/bin/python -m pytest tests/unit/test_coder4_execution_evidence_migration.py -q
```

## 8. implementation_seeds（轻量任务原子）
```yaml
implementation_seeds:
  - task_id: T-01
    feature_id: P1-dispatch-executor-routing
    blocked_by: []
    file_paths:
      - scripts/coder4/coder4_bootstrap_kernel.py
    symbols:
      - parse_args
      - decide_action
      - apply_action
      - _derive_attempt_result
    change_type: modify

  - task_id: T-02
    feature_id: P1-wtimp-executor-mode
    blocked_by: [T-01]
    file_paths:
      - .cursor/commands/jjk-wtimp.md
      - .agents/skills/jjk-wtimp/SKILL.md
    symbols:
      - 执行流程-创建隔离 worktree
      - 执行流程-提交合并清理
      - executor_mode
    change_type: modify

  - task_id: T-03
    feature_id: P1-cardrun-single-merge-path
    blocked_by: [T-01, T-02]
    file_paths:
      - .cursor/commands/jjk-cardrun.md
      - .agents/skills/jjk-cardrun/SKILL.md
      - scripts/coder4/wt-flow.sh
    symbols:
      - 主控调度子代理
      - done_gate + merge 收口
      - cmd_merge
    change_type: modify

  - task_id: T-04
    feature_id: P1-doc-chain-sync
    blocked_by: [T-03]
    file_paths:
      - .cursor/commands/jjk-vkplan.md
      - .agents/skills/jjk-vkplan/SKILL.md
      - .cursor/commands/jjk-create-pr.md
      - .agents/skills/jjk-create-pr/SKILL.md
    symbols:
      - 主链路
      - 输入前置
      - 推荐链路
    change_type: modify

  - task_id: T-05
    feature_id: P1-canonical-evidence-migration
    blocked_by: [T-01]
    file_paths:
      - scripts/coder4/coder4_bootstrap_kernel.py
      - docs/内部参考/迭代需求/cardrun内置wtimp执行器方案与最小改造清单_20260306.md
    symbols:
      - record_attempt_evidence
      - execution_evidence
      - read_old_write_new
    change_type: modify

  - task_id: T-06
    feature_id: P1-regression-tests
    blocked_by: [T-01, T-03, T-05]
    file_paths:
      - tests/unit/test_coder4_dispatch_executor.py
      - tests/unit/test_coder4_commit_evidence_gate.py
      - tests/unit/test_coder4_single_merge_path.py
      - tests/unit/test_coder4_execution_evidence_migration.py
    symbols:
      - dispatch_executor_path
      - commit_evidence_gate
      - single_merge_guard
      - evidence_migration
    change_type: add
```

## 9. execution_chain_seed
```yaml
execution_chain_seed:
  preferred_mode: core
  task_key: PP-20260306-cardrun-wtimp-executor
  card_seed:
    - T-01
    - T-02
    - T-03
    - T-04
    - T-05
    - T-06
  execution_contract_hint:
    delivery_mode: staged
    execution_unit: all_tasks
    commit_policy: per_pr
    stop_boundary: per_pr
```

## 10. 一致性自检（机读）
```yaml
clarify_consistency_check:
  product_contract_ready: true
  semantic_frozen: true
  contract_source_decided: true
  handoff_seed_alignment_ok: true
  parallel_dependency_ready: true
  replay_canonical_field_set: true
  fail_fast_codes: []
```

## 11. 设计冻结回执（机读）
```yaml
design_freeze_summary:
  design_actionable: true
  missing_blocks: []
  risk_level: medium
  risk_counterexamples_count: 3
  handoff_contract_ready: true
  product_contract_ready: true
  implementation_seed_count: 6
  semantic_frozen: true
  contract_source_decided: true
  handoff_seed_alignment_ok: true
  parallel_dependency_ready: true
  replay_canonical_field_set: true
  blocking_issues: []
```

## 12. clarify_handoff_contract（机读）
```yaml
clarify_handoff_contract:
  version: v2
  topic: "cardrun-wtimp-executor-integration"
  design_source: "docs/plans/2026-03-06-cardrun-wtimp-executor-design.md"
  handoff_ready: true
  required:
    product_contract_summary:
      target_users:
        - 平台工程负责人
        - 任务执行代理维护者
        - 质量与验收负责人
      core_scenarios:
        - cardrun dispatch 自动执行并回填提交证据
        - verify/merge 单一路径收口
        - 缺证据时明确阻断
      business_goal_metrics:
        - dispatch 自动执行闭环率 >=95%
        - 无 commit_sha 仍推进到 merge 的事件数 =0
        - 双重 merge 事故数 =0
      non_goals:
        - 不改造业务模块逻辑
        - 不重写 vkplan 拆解算法
      acceptance_gates:
        - AG-01 默认执行器切换为 wtimp 且可回退
        - AG-02 dispatch 成功必须输出 canonical execution_evidence
        - AG-03 commit_sha 缺失必须阻断
    requirement_seeds:
      - design_item: D-01
        fr_id: FR-CARDRUN-EXECUTOR-ROUTING
        trigger: cardrun 进入 dispatch
        input_contract:
          required_fields: [action, card_id, ws_file, _active_task.dispatch_executor]
          optional_fields: [executor_override]
          defaults:
            _active_task.dispatch_executor: wtimp
        output_contract:
          required_fields: [executor_mode, dispatch_result]
          optional_fields: [subagent_id, ws_file]
        failure_semantics: 执行器不可用时返回 CARDRUN_SUBAGENT_FAILED
        observability_fields: [task_key, card_id, executor_mode, attempt_id]
        rollback_anchor: ENABLE_CARDRUN_WTIMP_EXECUTOR=false
        acceptance_cmd_ref: venv/bin/python -m pytest tests/unit/test_coder4_dispatch_executor.py -q
      - design_item: D-02
        fr_id: FR-CARDRUN-COMMIT-EVIDENCE-GATE
        trigger: dispatch 执行完成，进入证据校验
        input_contract:
          required_fields: [commit_sha, action=dispatch]
          optional_fields: [merge_sha]
          defaults: {}
        output_contract:
          required_fields: [gate_passed]
          optional_fields: [blocked_code]
        failure_semantics: commit_sha 缺失时返回 CARDRUN_NO_COMMIT_EVIDENCE 并阻断状态推进
        observability_fields: [task_key, card_id, commit_sha, blocked_code]
        rollback_anchor: ENABLE_CARDRUN_DISPATCH_AUTORUN=false
        acceptance_cmd_ref: venv/bin/python -m pytest tests/unit/test_coder4_commit_evidence_gate.py -q
      - design_item: D-03
        fr_id: FR-CARDRUN-SINGLE-MERGE-PATH
        trigger: 卡片进入 done_gate 收口
        input_contract:
          required_fields: [card_status=verified, merge_owner=wt_flow]
          optional_fields: [executor_mode]
          defaults:
            merge_owner: wt_flow
        output_contract:
          required_fields: [merge_called_once]
          optional_fields: [merge_commit]
        failure_semantics: 命中双 merge 风险时返回 CARDRUN_MERGE_FAILED 并停止
        observability_fields: [task_key, card_id, merge_owner, merge_count]
        rollback_anchor: ENABLE_CARDRUN_WTIMP_EXECUTOR=false
        acceptance_cmd_ref: venv/bin/python -m pytest tests/unit/test_coder4_single_merge_path.py -q
      - design_item: D-04
        fr_id: FR-CARDRUN-CONTRACT-SOURCE-SINGLETON
        trigger: 初始化 dispatch 上下文
        input_contract:
          required_fields: [_active_task.dispatch_executor]
          optional_fields: [legacy_executor_fields]
          defaults:
            _active_task.dispatch_executor: wtimp
        output_contract:
          required_fields: [executor_mode]
          optional_fields: [legacy_read_hit]
        failure_semantics: 缺失配置且无默认值时返回 WTIMP_INPUT_INCOMPLETE
        observability_fields: [task_key, executor_mode, config_source]
        rollback_anchor: ENABLE_CARDRUN_WTIMP_EXECUTOR=false
        acceptance_cmd_ref: venv/bin/python -m pytest tests/unit/test_coder4_executor_config_source.py -q
      - design_item: D-05
        fr_id: FR-CARDRUN-EVIDENCE-CANONICAL-FIELD
        trigger: 记录 attempt 证据
        input_contract:
          required_fields: [execution_evidence.executor_mode, execution_evidence.commit_sha]
          optional_fields: [subagent_id, ws_file, merge_sha]
          defaults: {}
        output_contract:
          required_fields: [execution_evidence]
          optional_fields: [legacy_flat_fields]
        failure_semantics: canonical 字段缺失时返回 CLARIFY_REPLAY_CANONICAL_UNSET 并阻断审批下游
        observability_fields: [attempt_id, executor_mode, commit_sha, migration_mode]
        rollback_anchor: ENABLE_CARDRUN_EXECUTION_EVIDENCE_V2=false
        acceptance_cmd_ref: venv/bin/python -m pytest tests/unit/test_coder4_execution_evidence_migration.py -q
    implementation_seeds:
      - task_id: T-01
        feature_id: P1-dispatch-executor-routing
        blocked_by: []
        file_paths: [scripts/coder4/coder4_bootstrap_kernel.py]
        symbols: [parse_args, decide_action, apply_action, _derive_attempt_result]
        change_type: modify
      - task_id: T-02
        feature_id: P1-wtimp-executor-mode
        blocked_by: [T-01]
        file_paths: [.cursor/commands/jjk-wtimp.md, .agents/skills/jjk-wtimp/SKILL.md]
        symbols: [执行流程-创建隔离 worktree, 执行流程-提交合并清理, executor_mode]
        change_type: modify
      - task_id: T-03
        feature_id: P1-cardrun-single-merge-path
        blocked_by: [T-01, T-02]
        file_paths: [.cursor/commands/jjk-cardrun.md, .agents/skills/jjk-cardrun/SKILL.md, scripts/coder4/wt-flow.sh]
        symbols: [主控调度子代理, done_gate + merge 收口, cmd_merge]
        change_type: modify
      - task_id: T-04
        feature_id: P1-doc-chain-sync
        blocked_by: [T-03]
        file_paths: [.cursor/commands/jjk-vkplan.md, .agents/skills/jjk-vkplan/SKILL.md, .cursor/commands/jjk-create-pr.md, .agents/skills/jjk-create-pr/SKILL.md]
        symbols: [主链路, 输入前置, 推荐链路]
        change_type: modify
      - task_id: T-05
        feature_id: P1-canonical-evidence-migration
        blocked_by: [T-01]
        file_paths: [scripts/coder4/coder4_bootstrap_kernel.py, docs/内部参考/迭代需求/cardrun内置wtimp执行器方案与最小改造清单_20260306.md]
        symbols: [record_attempt_evidence, execution_evidence, read_old_write_new]
        change_type: modify
      - task_id: T-06
        feature_id: P1-regression-tests
        blocked_by: [T-01, T-03, T-05]
        file_paths: [tests/unit/test_coder4_dispatch_executor.py, tests/unit/test_coder4_commit_evidence_gate.py, tests/unit/test_coder4_single_merge_path.py, tests/unit/test_coder4_execution_evidence_migration.py]
        symbols: [dispatch_executor_path, commit_evidence_gate, single_merge_guard, evidence_migration]
        change_type: add
    execution_chain_seed:
      preferred_mode: core
      task_key: PP-20260306-cardrun-wtimp-executor
      card_seed: [T-01, T-02, T-03, T-04, T-05, T-06]
      execution_contract_hint:
        delivery_mode: staged
        execution_unit: all_tasks
        commit_policy: per_pr
        stop_boundary: per_pr
    alignment_contract:
      strict_match: true
      requirement_seed_ids: [D-01, D-02, D-03, D-04, D-05]
      implementation_task_ids: [T-01, T-02, T-03, T-04, T-05, T-06]
      card_seed_ids: [T-01, T-02, T-03, T-04, T-05, T-06]
  extended:
    observability_hints:
      - 每轮必须记录 executor_mode 与 attempt_id
      - merge 阶段记录 merge_count，确保单次调用
      - 证据迁移记录 migration_mode=read_old_write_new
    risk_counterexample_map:
      - risk_id: R-01
        counterexample: executor 成功但 ledger 写入失败
        verify_cmd: venv/bin/python -m pytest tests/unit/test_coder4_dispatch_executor.py -q
      - risk_id: R-02
        counterexample: wtimp 与 cardrun 双重 merge
        verify_cmd: venv/bin/python -m pytest tests/unit/test_coder4_single_merge_path.py -q
      - risk_id: R-03
        counterexample: 旧 attempt 字段无法被新读取路径识别
        verify_cmd: venv/bin/python -m pytest tests/unit/test_coder4_execution_evidence_migration.py -q
    assumptions:
      - 当前仓库继续使用 `wt-flow` 作为 merge 唯一入口
      - `_active_task.json` 可安全扩展 `dispatch_executor` 字段
      - 本轮先完成设计冻结，后续由 /jjk-plan 细化实现计划
  requirement_seeds: [D-01, D-02, D-03, D-04, D-05]
  implementation_seeds: [T-01, T-02, T-03, T-04, T-05, T-06]
  execution_chain_seed:
    preferred_mode: core
    task_key: PP-20260306-cardrun-wtimp-executor
```

## 13. 审批记录
- design_approved: false
- approved_at: ""
- approved_round: ""
- approval_evidence: ""
- approval_mode: pending
- go_no_go: NO_GO
- blocking_issues: []

## 14. 执行备注（机读）
```yaml
execution_notes:
  fallback:
    brainstorming: false
    team: false
  template:
    missing: false
    source: "docs/内部参考/迭代需求/_templates/jjk_clarify_templates.md"
  question_mode: "package"
  degrade_reason: ""
  alternative_tool: ""
  verification: "基于现有 cardrun/wtimp/wt-flow/kernel 文档与源码证据完成冻结设计"
```
