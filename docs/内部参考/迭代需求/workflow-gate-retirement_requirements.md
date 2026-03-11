# workflow-gate-retirement 需求文档

> 更新时间：2026-03-06 20:43 +08:00  
> 上游设计：`docs/plans/2026-03-06-workflow-gate-retirement-design.md`  
> 文档目标：定义 WHAT（需求合同、验收门禁、追溯矩阵），供 `workflow-gate-retirement_implementation_plan.md` 承接

## 1. 需求范围与目标

### 1.1 核心目标

- 冻结并统一工程减法执行口径，禁止直接删除门禁脚本。
- 在保持旧命令兼容的前提下，建立统一门禁入口。
- 建立退役前调用观测证据与 TTL 归档边界，确保“可删可回退可审计”。
- 以阶段门禁驱动退役，保证 Clarify/Plan/VK/G01/IG01 主链路连续性。

### 1.2 范围

- 流程治理文档：`docs/内部参考/工程减法体检报告_2026-03-06.md`、`docs/内部参考/工程减法体检报告_2026-03-06_v3.md`
- 门禁统一入口：`scripts/check_workflow_contract.py`
- L1 兼容壳脚本：`check_clarify_plan_alignment.py`、`check_plan_vk_coverage.py`、`check_gate_contract_consistency.py`、`check_integration_gate.py`
- 流程引用迁移：`.cursor/commands/*`、`.agents/skills/*`、`docs/开发文档/*`
- 观测与归档：`logs/workflow-gate-usage.jsonl`（运行态观测）、`docs/内部参考/任务拆解/2026-03-06_工程减法治理/evidence/workflow-gate-usage-report.json`（提交证据）、`docs/内部参考/任务拆解/*`

### 1.3 非范围

- 不删除 `scripts/check_special_doc_sync.py`（L0 硬门禁）。
- 不删除 `coder4-idempotency.json`、`task-ledger.jsonl` 等运行态真理源。
- 不改造业务功能与数据模型。

## 2. 机读需求合同（强制）

```yaml
requirements_contract:
  topic: "workflow-gate-retirement"
  status: "approved"
  design_source: docs/plans/2026-03-06-workflow-gate-retirement-design.md
  clarify_handoff_source: docs/plans/2026-03-06-workflow-gate-retirement-design.md#clarify_handoff_contract
  clarify_handoff_version: v2
  design_approved: true
  design_approval_evidence: "用户明确回复“确认”"
  design_freeze_summary:
    design_actionable: true
    missing_blocks: []
    risk_level: medium
    risk_counterexamples_count: 3
    product_contract_ready: true
  owner: "workflow-governance"
  approver: "jijingkun"
  updated_at: "2026-03-06 20:43"
```

## 3. 产品契约矩阵（PRD-Lite 承接）

```yaml
product_contract_matrix:
  target_users:
    - workflow维护者（jjk-plan/jjk-vkplan/jjk-cardrun）
    - 门禁维护者（G01/IG01）
    - 文档治理与CI维护者
  core_scenarios:
    - 旧命令继续可用且不破链
    - 统一入口按mode输出与旧链路等价结果
    - 删除前可观测旧入口调用并可回退
  business_goal_metrics:
    - 迁移期间命令中断次数 = 0
    - 删除前 legacy 入口调用阻断 = 0
    - 主入口收敛到1个且旧入口仅兼容壳
  non_goals:
    - 不改L0硬门禁
    - 不改业务逻辑与数据模型
    - 不做全仓库无边界历史清理
  acceptance_gates:
    - AG-01 P0冻结完成且团队停用直接rm
    - AG-02 P1统一入口、wrapper与引用迁移完成
    - AG-03 P2观测与TTL边界达标
    - AG-04 P3删除后全量验收一次通过
```

## 4. FR 合同矩阵（字段级）

```yaml
fr_contract_matrix:
  - fr_id: FR-01
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[0]
    user_value: 统一执行口径，阻断误删
    trigger: 执行工程减法治理任务
    input_contract:
      required_fields: [report_v2_doc, report_v3_doc, no_go_table]
      source_of_truth: docs/内部参考/工程减法体检报告_2026-03-06.md
    output_contract:
      required_fields: [frozen_command_list, no_go_status]
      consumer: workflow维护者
    failure_semantics: 未冻结直接删除命令时返回 NO_GO_POLICY_VIOLATION
    observability_fields: [task_key, frozen_at, owner, no_go_status]
    rollback_anchor: WORKFLOW_GATE_UNIFIED_ENABLED=false
    owner: workflow-governance

  - fr_id: FR-02
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[1]
    user_value: 单入口统一门禁语义
    trigger: 调用 check_workflow_contract 统一入口
    input_contract:
      required_fields: [mode, input_paths]
      source_of_truth: scripts/check_workflow_contract.py
    output_contract:
      required_fields: [ok, exit_code, payload]
      consumer: 命令链路与CI
    failure_semantics: 参数非法返回 exit_code=2
    observability_fields: [mode, exit_code, duration_ms, task_key]
    rollback_anchor: WORKFLOW_GATE_UNIFIED_ENABLED=false
    owner: workflow-governance

  - fr_id: FR-03
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[2]
    user_value: 兼容旧命令，避免迁移中断
    trigger: 调用任意L1旧脚本入口
    input_contract:
      required_fields: [legacy_args, legacy_entry]
      source_of_truth: scripts/check_clarify_plan_alignment.py
    output_contract:
      required_fields: [delegated_mode, deprecation_notice, exit_code]
      consumer: 现有命令/技能调用方
    failure_semantics: wrapper透传统一入口错误并保留退出码
    observability_fields: [legacy_entry, delegated_mode, exit_code]
    rollback_anchor: WORKFLOW_GATE_DEPRECATION_ENFORCED=false
    owner: workflow-governance

  - fr_id: FR-04
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[3]
    user_value: 引用收敛，消除隐式旧入口依赖
    trigger: 维护命令/技能/文档入口
    input_contract:
      required_fields: [commands_docs, skills_docs, workflow_docs]
      source_of_truth: .cursor/commands
    output_contract:
      required_fields: [reference_migration_report]
      consumer: 文档治理与代码评审
    failure_semantics: 存在旧实现直连引用时返回 LEGACY_REFERENCE_REMAINING
    observability_fields: [legacy_ref_count, migrated_ref_count]
    rollback_anchor: WORKFLOW_GATE_DEPRECATION_ENFORCED=false
    owner: workflow-governance

  - fr_id: FR-05
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[4]
    user_value: 退役判定可证据化
    trigger: 进入退役前验证阶段
    input_contract:
      required_fields: [usage_logs]
      source_of_truth: logs/workflow-gate-usage.jsonl
    output_contract:
      required_fields: [legacy_call_count, last_call_at]
      evidence_artifact: docs/内部参考/任务拆解/2026-03-06_工程减法治理/evidence/workflow-gate-usage-report.json
      consumer: 退役审批人
    failure_semantics: 观测期发现旧入口调用返回 RETIREMENT_NOT_READY
    observability_fields: [legacy_call_count, last_call_at]
    rollback_anchor: WORKFLOW_GATE_UNIFIED_ENABLED=false
    owner: workflow-governance

  - fr_id: FR-06
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[5]
    user_value: 过程文件清理不破坏可追溯性
    trigger: 执行TTL归档
    input_contract:
      required_fields: [task_status, last_modified_at, ttl_days]
      source_of_truth: docs/内部参考/任务拆解/*/.state
    output_contract:
      required_fields: [archived_items, skipped_active_items, cleanup_report]
      consumer: 流程治理审计
    failure_semantics: 触碰活跃任务或真理源文件时返回 TTL_SCOPE_VIOLATION
    observability_fields: [archived_count, skipped_count, ttl_days]
    rollback_anchor: WORKFLOW_ARTIFACT_TTL_CLEANUP_ENABLED=false
    owner: workflow-governance
```

## 5. NFR 合同矩阵（数字阈值）

```yaml
nfr_contract_matrix:
  - nfr_id: NFR-01
    name: gate_entry_latency
    threshold: "统一入口执行P95 <= 30s"
    metric_source: workflow-gate-usage.jsonl.duration_ms
  - nfr_id: NFR-02
    name: legacy_compat_success_rate
    threshold: "wrapper兼容成功率 >= 99.5%"
    metric_source: workflow-gate-usage.jsonl.ok
  - nfr_id: NFR-03
    name: legacy_usage_observation_integrity
    threshold: "legacy 调用阻断判定准确率 = 100%"
    metric_source: usage-report聚合结果
  - nfr_id: NFR-04
    name: ttl_cleanup_safety
    threshold: "活跃任务误归档事件数 = 0"
    metric_source: ttl-audit报告与审计抽检
```

## 6. 测试用例编号（TC）

- `TC-WG-01`: P0 删除口径冻结与 NO-GO 生效
- `TC-WG-02`: 统一入口 `--mode` 行为等价
- `TC-WG-03`: 4 个 L1 wrapper 参数兼容与透传
- `TC-WG-04`: 命令/技能/文档引用迁移收敛
- `TC-WG-05`: legacy 调用阻断判定
- `TC-WG-06`: TTL 归档边界与活跃保护
- `TC-WG-07`: 删除旧实现后全量门禁验收

## 7. 追溯矩阵（机读）

```yaml
traceability_matrix:
  - design_item: D-01 冻结删除口径
    fr_id: FR-01
    feature_id: P0-freeze-governance
    task_id: P0-FREEZE-COMMANDS
    tc_id: TC-WG-01
    acceptance_cmd_ref: rg -n "NO-GO|rm scripts/check_\\*\\.py" docs/内部参考/工程减法体检报告_2026-03-06.md docs/内部参考/工程减法体检报告_2026-03-06_v3.md
    evidence_entry: docs/内部参考/迭代需求/workflow-gate-retirement_implementation_plan.md

  - design_item: D-02 统一门禁入口
    fr_id: FR-02
    feature_id: P1-unified-entry
    task_id: P1-UNIFIED-ENTRY
    tc_id: TC-WG-02
    acceptance_cmd_ref: python3 scripts/check_workflow_contract.py --mode clarify_plan --requirements-path docs/内部参考/迭代需求/workflow-gate-retirement_requirements.md --implementation-path docs/内部参考/迭代需求/workflow-gate-retirement_implementation_plan.md --output -
    evidence_entry: docs/内部参考/迭代需求/workflow-gate-retirement_implementation_plan.md

  - design_item: D-03 L1 wrapper 兼容壳
    fr_id: FR-03
    feature_id: P1-legacy-wrapper
    task_id: P1-WRAPPER-L1
    tc_id: TC-WG-03
    acceptance_cmd_ref: python3 scripts/check_workflow_contract.py --mode legacy_wrapper_compat --task-split-dir docs/内部参考/任务拆解/2026-03-06_工程减法治理 --output -
    evidence_entry: docs/内部参考/迭代需求/workflow-gate-retirement_implementation_plan.md

  - design_item: D-04 引用迁移收敛
    fr_id: FR-04
    feature_id: P1-reference-migration
    task_id: P1-REFERENCE-MIGRATION
    tc_id: TC-WG-04
    acceptance_cmd_ref: rg -n "check_workflow_contract.py|check_clarify_plan_alignment.py|check_plan_vk_coverage.py|check_gate_contract_consistency.py|check_integration_gate.py" .cursor/commands .agents/skills docs/开发文档
    evidence_entry: docs/内部参考/迭代需求/workflow-gate-retirement_implementation_plan.md

  - design_item: D-05 调用观测判定
    fr_id: FR-05
    feature_id: P2-usage-observability
    task_id: P2-OBSERVABILITY
    tc_id: TC-WG-05
    acceptance_cmd_ref: python3 scripts/check_workflow_contract.py --mode usage-report --log-path logs/workflow-gate-usage.jsonl --report-output docs/内部参考/任务拆解/2026-03-06_工程减法治理/evidence/workflow-gate-usage-report.json
    evidence_entry: docs/内部参考/迭代需求/workflow-gate-retirement_implementation_plan.md

  - design_item: D-06 TTL归档边界
    fr_id: FR-06
    feature_id: P2-ttl-archive
    task_id: P2-TTL-ARCHIVE
    tc_id: TC-WG-06
    acceptance_cmd_ref: python3 scripts/check_workflow_contract.py --mode ttl-audit --task-split-dir docs/内部参考/任务拆解 --ttl-days 14 --output -
    evidence_entry: docs/内部参考/迭代需求/workflow-gate-retirement_implementation_plan.md

  - design_item: D-07 删除旧实现并验收
    fr_id: FR-05
    feature_id: P3-retire-legacy
    task_id: P3-RETIRE-LEGACY
    tc_id: TC-WG-07
    acceptance_cmd_ref: python3 scripts/check_workflow_contract.py --mode full-gate --task-split-dir docs/内部参考/任务拆解/2026-03-06_工程减法治理 --baseline master --output -
    evidence_entry: docs/内部参考/迭代需求/workflow-gate-retirement_implementation_plan.md
```

