# cardrun 内置 wtimp 执行器需求文档

> 更新时间：2026-03-06 20:18 +08:00
> 上游设计：`docs/plans/2026-03-06-cardrun-wtimp-executor-design.md`
> 文档目标：定义 WHAT（需求合同、验收与追溯），供 `cardrun内置wtimp执行器_implementation_plan.md` 承接

## 1. 需求范围与目标

### 1.1 核心目标

- 将 `cardrun` 的 dispatch 执行器统一切换到 `wtimp`。
- 保持 `verify -> merge` 唯一收口，避免双重 merge。
- 将 `commit_sha` 从“文档约束”升级为“代码门禁”。
- 建立 `execution_evidence` canonical 证据字段并提供读旧写新迁移语义。

### 1.2 范围

- 调度/决策：`scripts/coder4/coder4_bootstrap_kernel.py`
- 收口脚本：`scripts/coder4/wt-flow.sh`
- 执行契约文档：`jjk-cardrun`、`jjk-wtimp`、`jjk-vkplan`、`jjk-create-pr`
- 回归验证：dispatch/merge/evidence 相关单测

### 1.3 非范围

- 不改造业务模块（AI workflow、数据库、前端业务功能）。
- 不重构 `jjk-vkplan` 卡片拆解算法。
- 不新增第三套并行执行协议。

## 2. 机读需求合同（强制）

```yaml
requirements_contract:
  topic: "cardrun内置wtimp执行器"
  status: "approved"
  design_source: docs/plans/2026-03-06-cardrun-wtimp-executor-design.md
  clarify_handoff_source: docs/plans/2026-03-06-cardrun-wtimp-executor-design.md#clarify_handoff_contract
  clarify_handoff_version: v2
  design_approved: true
  design_approval_evidence: "用户回复：确认"
  design_freeze_summary:
    design_actionable: true
    missing_blocks: []
    risk_level: medium
    risk_counterexamples_count: 3
    product_contract_ready: true
  owner: "ai-workflow"
  approver: "jijingkun"
  updated_at: "2026-03-06 20:18"
```

## 3. 产品契约矩阵（PRD-Lite 承接）

```yaml
product_contract_matrix:
  target_users:
    - 平台工程负责人
    - 任务执行代理维护者
    - 质量与验收负责人
  core_scenarios:
    - cardrun dispatch 自动调用 wtimp 并返回提交证据
    - verify/merge 单路径收口
    - 缺失 commit 证据 fail-fast 阻断
  business_goal_metrics:
    - dispatch 自动执行闭环率 >= 95%
    - 无 commit_sha 仍推进到 merge 的事件数 = 0
    - 双重 merge 事故数 = 0
    - 失败轮次结构化阻断证据覆盖率 = 100%
  non_goals:
    - 不重构业务功能模块
    - 不变更 vkplan 拆解算法
  acceptance_gates:
    - AG-01 默认执行器切换到 wtimp 且支持开关回退
    - AG-02 dispatch 成功轮次包含 canonical execution_evidence
    - AG-03 commit_sha 缺失触发 CARDRUN_NO_COMMIT_EVIDENCE
    - AG-04 verify -> merge 只执行一次
    - AG-05 相关命令文档主链路口径一致
```

## 4. FR 合同矩阵（字段级）

```yaml
fr_contract_matrix:
  - fr_id: FR-01
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[0]
    user_value: dispatch 阶段可自动执行，不再仅 pending
    trigger: cardrun 判定 action=dispatch
    input_contract:
      required_fields: [action, card_id, ws_file, _active_task.dispatch_executor]
      source_of_truth: scripts/coder4/coder4_bootstrap_kernel.py
    output_contract:
      required_fields: [executor_mode, dispatch_result]
      consumer: task-ledger execution_evidence
    failure_semantics: 执行器调用失败返回 CARDRUN_SUBAGENT_FAILED
    observability_fields: [task_key, card_id, executor_mode, attempt_id]
    rollback_anchor: ENABLE_CARDRUN_WTIMP_EXECUTOR=false
    owner: ai-workflow

  - fr_id: FR-02
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[1]
    user_value: 提交证据缺失可在代码层阻断，避免伪完成
    trigger: dispatch 成功后进入证据门禁
    input_contract:
      required_fields: [commit_sha, action]
      source_of_truth: scripts/coder4/coder4_bootstrap_kernel.py
    output_contract:
      required_fields: [gate_passed]
      consumer: cardrun 状态推进
    failure_semantics: commit_sha 缺失返回 CARDRUN_NO_COMMIT_EVIDENCE
    observability_fields: [task_key, card_id, commit_sha, blocked_code]
    rollback_anchor: ENABLE_CARDRUN_DISPATCH_AUTORUN=false
    owner: ai-workflow

  - fr_id: FR-03
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[2]
    user_value: merge 路径单一，消除双重 merge 风险
    trigger: done_gate 进入 merge 前
    input_contract:
      required_fields: [card_status, merge_owner]
      source_of_truth: scripts/coder4/wt-flow.sh
    output_contract:
      required_fields: [merge_called_once]
      consumer: task-runner-state.merge_results
    failure_semantics: 命中双 merge 风险返回 CARDRUN_MERGE_FAILED
    observability_fields: [task_key, card_id, merge_owner, merge_count]
    rollback_anchor: ENABLE_CARDRUN_WTIMP_EXECUTOR=false
    owner: ai-workflow

  - fr_id: FR-04
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[3]
    user_value: 执行器来源唯一，避免配置漂移
    trigger: cardrun 初始化 dispatch 上下文
    input_contract:
      required_fields: [_active_task.dispatch_executor]
      source_of_truth: docs/内部参考/任务拆解/*/_active_task.json
    output_contract:
      required_fields: [executor_mode]
      consumer: scripts/coder4/coder4_bootstrap_kernel.py
    failure_semantics: 缺少执行器配置时返回 WTIMP_INPUT_INCOMPLETE
    observability_fields: [task_key, executor_mode, config_source]
    rollback_anchor: ENABLE_CARDRUN_WTIMP_EXECUTOR=false
    owner: ai-workflow

  - fr_id: FR-05
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[4]
    user_value: 执行证据可稳定回放与审计
    trigger: 写入 attempt 证据
    input_contract:
      required_fields: [execution_evidence.executor_mode, execution_evidence.commit_sha]
      source_of_truth: scripts/coder4/coder4_bootstrap_kernel.py
    output_contract:
      required_fields: [execution_evidence]
      consumer: task-ledger.jsonl / alignment checks
    failure_semantics: 缺失 canonical 字段返回 CLARIFY_REPLAY_CANONICAL_UNSET
    observability_fields: [attempt_id, executor_mode, commit_sha, migration_mode]
    rollback_anchor: ENABLE_CARDRUN_EXECUTION_EVIDENCE_V2=false
    owner: ai-workflow
```

## 5. NFR 合同矩阵（数字阈值）

```yaml
nfr_contract_matrix:
  - nfr_id: NFR-01
    name: dispatch_execute_latency
    threshold: "P95 <= 8s"
    metric_source: task-ledger round duration
  - nfr_id: NFR-02
    name: evidence_write_completeness
    threshold: "execution_evidence 字段完整率 = 100%"
    metric_source: task-ledger schema check
  - nfr_id: NFR-03
    name: single_merge_path_integrity
    threshold: "merge_count_per_card <= 1"
    metric_source: merge log + state merge_results
```

## 6. 测试用例编号（TC）

- `TC-CW-01`: dispatch 走 wtimp 执行器并产出证据
- `TC-CW-02`: commit_sha 缺失触发阻断
- `TC-CW-03`: merge 主路径单次调用
- `TC-CW-04`: 执行器配置源唯一读取
- `TC-CW-05`: execution_evidence 读旧写新迁移
- `TC-CW-06`: 文档主链路同步一致

## 7. 追溯矩阵（机读）

```yaml
traceability_matrix:
  - design_item: D-01 dispatch 执行器路由
    fr_id: FR-01
    feature_id: P1-dispatch-executor-routing
    task_id: T-01
    tc_id: TC-CW-01
    acceptance_cmd_ref: venv/bin/python -m pytest tests/unit/test_coder4_dispatch_executor.py -q
    evidence_entry: docs/内部参考/迭代需求/cardrun内置wtimp执行器_implementation_plan.md

  - design_item: D-02 commit 证据门禁
    fr_id: FR-02
    feature_id: P1-dispatch-evidence-gate
    task_id: T-02
    tc_id: TC-CW-02
    acceptance_cmd_ref: venv/bin/python -m pytest tests/unit/test_coder4_commit_evidence_gate.py -q
    evidence_entry: docs/内部参考/迭代需求/cardrun内置wtimp执行器_implementation_plan.md

  - design_item: D-03 单收口 merge
    fr_id: FR-03
    feature_id: P1-single-merge-path
    task_id: T-03
    tc_id: TC-CW-03
    acceptance_cmd_ref: venv/bin/python -m pytest tests/unit/test_coder4_single_merge_path.py -q
    evidence_entry: docs/内部参考/迭代需求/cardrun内置wtimp执行器_implementation_plan.md

  - design_item: D-04 契约源唯一化
    fr_id: FR-04
    feature_id: P1-contract-source-singleton
    task_id: T-04
    tc_id: TC-CW-04
    acceptance_cmd_ref: venv/bin/python -m pytest tests/unit/test_coder4_executor_config_source.py -q
    evidence_entry: docs/内部参考/迭代需求/cardrun内置wtimp执行器_implementation_plan.md

  - design_item: D-05 证据 canonical 迁移
    fr_id: FR-05
    feature_id: P1-canonical-evidence-migration
    task_id: T-05
    tc_id: TC-CW-05
    acceptance_cmd_ref: venv/bin/python -m pytest tests/unit/test_coder4_execution_evidence_migration.py -q
    evidence_entry: docs/内部参考/迭代需求/cardrun内置wtimp执行器_implementation_plan.md

  - design_item: D-06 文档主链口径一致
    fr_id: FR-03
    feature_id: P1-doc-chain-sync
    task_id: T-06
    tc_id: TC-CW-06
    acceptance_cmd_ref: python3 scripts/check_clarify_plan_alignment.py --requirements-path docs/内部参考/迭代需求/cardrun内置wtimp执行器_requirements.md --implementation-path docs/内部参考/迭代需求/cardrun内置wtimp执行器_implementation_plan.md --output -
    evidence_entry: docs/内部参考/迭代需求/cardrun内置wtimp执行器_implementation_plan.md
```
