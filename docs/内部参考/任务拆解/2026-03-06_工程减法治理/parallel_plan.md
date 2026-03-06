# 并行计划书（工程减法治理）

> 计划 ID: PP-20260306-ENGINEERING-LEAN-GOV
> 主题: 工程减法治理（依赖驱动退役）
> 输入来源:
> - `docs/内部参考/工程减法体检报告_2026-03-06.md`
> - `docs/内部参考/工程减法体检报告_2026-03-06_v3.md`
> - `docs/内部参考/工程减法治理看板模板_2026-03-06.md`

## 0. 执行契约

```yaml
planning_contract:
  task_key: PP-20260306-ENGINEERING-LEAN-GOV
  task_split_dir: 2026-03-06_工程减法治理
  execution_mode: serial
  single_active_card: true
  preflight_required: C00
  gate_contract:
    mode: as_cards
    gate_ids: [G01]
    depends_on:
      G01: [C04]
  cards: [C01, C02, C03, C04, G01]
  task_to_pr_mapping:
    C01: PR-GOV-001
    C02: PR-GOV-002
    C03: PR-GOV-003
    C04: PR-GOV-004
    G01: PR-GOV-G01
  product_contract_summary:
    target_users: [研发负责人, 自动化维护者]
    core_scenarios: [工程减法治理落地, 可回退退役流程]
    business_goal_metrics: [降低冗余脚本认知负担, 降低误删风险]
    non_goals: [本轮不重写业务功能, 不调整线上服务]
    acceptance_gates: [NO-GO 生效, 验收矩阵可执行]
  design_approved: true
  approved_at: 2026-03-06
  approved_round: 1
  approval_evidence: docs/内部参考/工程减法体检报告_2026-03-06_v3.md

execution_contract:
  delivery_mode: card_only
  execution_unit: single_card
  commit_policy: per_card
  stop_boundary: hard_gate
  stop_on_blocked: true
```

## 1. implementation_tasks

```yaml
implementation_tasks:
  - task_id: C01
    feature_ids: [P0-01]
    phase: P0
    change_type: governance
    owner: platform-governance
    pr_id: PR-GOV-001
    risk_point: 基线统计口径漂移
    rollback_point: 回滚治理基线文档
    depends_on_tasks: []
    file_paths:
      - docs/内部参考/工程减法体检报告_2026-03-06_v3.md
    symbols:
      - baseline_snapshot
    acceptance_cmds:
      - rg -n "核验基线" docs/内部参考/工程减法体检报告_2026-03-06_v3.md

  - task_id: C02
    feature_ids: [P0-02]
    phase: P0
    change_type: governance
    owner: platform-governance
    pr_id: PR-GOV-002
    risk_point: 依赖台账漏项
    rollback_point: 回滚 scripts_manifest
    depends_on_tasks: [C01]
    file_paths:
      - docs/内部参考/工程减法治理看板模板_2026-03-06.md
    symbols:
      - scripts_manifest
    acceptance_cmds:
      - rg -n "owner|trigger|replacement" docs/内部参考/工程减法治理看板模板_2026-03-06.md

  - task_id: C03
    feature_ids: [P0-03]
    phase: P0
    change_type: governance
    owner: platform-governance
    pr_id: PR-GOV-003
    risk_point: NO-GO 未阻断高风险动作
    rollback_point: 回滚冻结段落
    depends_on_tasks: [C02]
    file_paths:
      - docs/内部参考/工程减法体检报告_2026-03-06.md
    symbols:
      - no_go_gate
    acceptance_cmds:
      - rg -n "NO-GO|冻结执行" docs/内部参考/工程减法体检报告_2026-03-06.md

  - task_id: C04
    feature_ids: [P0-04]
    phase: P0
    change_type: governance
    owner: platform-governance
    pr_id: PR-GOV-004
    risk_point: 验收命令不可执行
    rollback_point: 回滚验收矩阵文档
    depends_on_tasks: [C03]
    file_paths:
      - docs/内部参考/工程减法体检报告_2026-03-06_v3.md
    symbols:
      - acceptance_matrix
    acceptance_cmds:
      - rg -n "验收矩阵" docs/内部参考/工程减法体检报告_2026-03-06_v3.md

  - task_id: G01
    feature_ids: [G0-01]
    phase: G0
    change_type: gate
    owner: platform-governance
    pr_id: PR-GOV-G01
    risk_point: 卡片链路可建卡但不可执行
    rollback_point: 回退到仅文档治理
    depends_on_tasks: [C04]
    file_paths:
      - docs/内部参考/任务拆解/2026-03-06_工程减法治理/vk_cards.json
    symbols:
      - gate_contract
    acceptance_cmds:
      - python3 scripts/coder4/coder4_vk_sync.py --active-task docs/内部参考/任务拆解/2026-03-06_工程减法治理/_active_task.json --sync-all --dry-run
```

## 2. 卡片顺序

- `C01 -> C02 -> C03 -> C04 -> G01`

## 3. 备注

- 本任务包可直接被 create-only 建卡消费。
- 若要进入 `jjk-cardrun`，建议再补 requirements 文档并执行 `check_plan_vk_coverage.py`。
