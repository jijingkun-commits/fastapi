# workflow-gate-retirement 设计说明

## 1. scope_contract
- 目标：在不破坏主干工程流的前提下，完成 L1 门禁脚本退役，形成可观测、可回退、可审计的减法闭环。
- 范围：
  - 冻结直接删除口径，统一执行口径到 `工程减法体检报告_2026-03-06_v3.md`。
  - 新增统一入口 `scripts/check_workflow_contract.py`，聚合 4 个 L1 门禁能力。
  - 将 4 个 L1 旧脚本改为 wrapper，保持参数兼容并输出 deprecation 提示。
  - 迁移 `.cursor/commands/*`、`.agents/skills/*`、文档中的旧脚本引用到统一入口。
  - 增加旧入口调用观测与 legacy 调用阻断判定。
  - 对过程文件执行生命周期 + TTL 归档，仅处理 `done/archived` 且 14 天无写入条目。
- 边界：
  - 不删除 `scripts/check_special_doc_sync.py`（L0 硬门禁）。
  - 不删除 `coder4-idempotency.json`、`task-ledger.jsonl` 等运行态真理源。
  - 不改业务功能逻辑，不引入新的任务系统。
- 成功标准：
  - 团队不再执行 `rm scripts/check_*.py`。
  - 旧命令可继续使用且行为等价（参数、退出码、关键输出）。
  - 删除前确认旧入口未检出 legacy 调用阻断。
  - 阶段验收矩阵（Clarify/Plan/VK/G01/IG01）一次通过。

## 2. product_contract（PRD-Lite）
- target_users：
  - workflow 维护者（`jjk-plan` / `jjk-vkplan` / `jjk-cardrun`）。
  - 门禁维护者（G01 / IG01）。
  - 文档治理与 CI 维护者。
- core_scenarios：
  - 调用方继续使用旧命令，链路不中断。
  - 调用方使用统一入口按模式执行门禁，结论与旧链路等价。
  - 退役期间可追踪调用、可执行回退、可证明门禁未降级。
- business_goals（KPI）：
  - 命令连续性：迁移期间命令中断次数 = 0。
  - 退役确定性：删除旧实现前 legacy 入口调用阻断 = 0。
  - 治理收敛度：主入口收敛到 1 个（统一入口），旧入口仅兼容壳。
- non_goals：
  - 本轮不做 L0 硬门禁重构。
  - 本轮不变更业务域模型/API 协议。
  - 本轮不做全仓库无差别历史文件清理。
- acceptance_gates：
  - P0 冻结删除口径并发布 NO-GO 执行清单。
  - P1 统一入口上线并完成 wrapper 与引用迁移。
  - P2 旧入口调用观测与 TTL 归档满足边界。
  - P3 删除旧实现后全量验收通过。
- release_constraints：
  - 项目未上线，以设计合理性优先，不接受“先删后补”。
  - 任一阶段失败必须可快速回退。

## 3. architecture_contract
- 模块边界与职责：
  - `scripts/check_workflow_contract.py`：单一门禁契约源，负责参数解析、模式分发、结构化输出、退出码归一。
  - `scripts/check_clarify_plan_alignment.py` / `scripts/check_plan_vk_coverage.py` / `scripts/check_gate_contract_consistency.py` / `scripts/check_integration_gate.py`：迁移期兼容壳，仅做参数透传 + 提示。
  - `full-gate` 用于 C07 的 pre-merge 收口校验；`integration_gate` 仅用于 G01 / post-merge 的主干可见性校验。
  - `logs/workflow-gate-usage.jsonl`：旧入口观测台账，作为退役 GO/NO-GO 判定证据。
  - `docs/内部参考/任务拆解/*/.state/*`：运行态证据域，仅按生命周期 + TTL 定向归档。
- 端到端数据流：
  - 命令/技能/文档入口 -> 旧脚本 wrapper（可选）-> 统一入口（`--mode`）-> 对应门禁执行 -> 结果输出与日志记录。
- 状态生命周期：
  - legacy 脚本：`active_impl -> wrapper -> zero_call_observed -> retired`。
  - 过程产物：`active -> done/archived -> ttl_eligible -> archived_trimmed`。
- 异常语义与降级策略（语义唯一）：
  - 参数非法/缺失：统一 `exit_code=2`。
  - 门禁失败：统一 `exit_code=1`，结构化结果 `ok=false`。
  - wrapper 禁止吞错，必须透传统一入口退出码。
  - 回放 canonical 字段固定为 `payload`；历史字段并存时采用“读旧写新”。
- 单一契约源冻结：
  - 契约源唯一机制为“统一入口脚本 + 结构化输出 schema”；旧脚本仅保留兼容壳，不再承担契约定义职责。

## 4. 最终方案
- 方案描述：
  - 采用四阶段退役：`Phase 0 冻结删除 -> Phase 1 统一入口与 wrapper -> Phase 2 调用观测与 TTL 归档 -> Phase 3 删除旧实现并全量验收`。
- requirement_seeds：
  - `REQ-WF-001`：冻结直接删除口径并统一到 v3。
  - `REQ-WF-002`：统一入口支持 `--mode` 且保持与旧链路等价输出。
  - `REQ-WF-003`：4 个 L1 旧脚本 wrapper 化且参数兼容。
  - `REQ-WF-004`：命令/技能/文档引用迁移到统一入口。
  - `REQ-WF-005`：新增调用观测并支持 legacy 调用阻断判定。
  - `REQ-WF-006`：过程文件仅按生命周期 + TTL 归档，不触碰活跃任务与真理源。
- implementation_seeds：
  - `P0-FREEZE-COMMANDS`
    - blocked_by: `[]`
    - file_paths: `docs/内部参考/工程减法体检报告_2026-03-06.md`, `docs/内部参考/工程减法体检报告_2026-03-06_v3.md`, `docs/内部参考/工程减法治理看板模板_2026-03-06.md`
    - symbols: `NO_GO_SECTION`, `phase_plan_table`
    - change_type: `docs_update`
  - `P1-UNIFIED-ENTRY`
    - blocked_by: `["P0-FREEZE-COMMANDS"]`
    - file_paths: `scripts/check_workflow_contract.py`
    - symbols: `parse_args`, `run_mode`, `MODE_REGISTRY`, `main`
    - change_type: `add`
  - `P1-WRAPPER-L1`
    - blocked_by: `["P1-UNIFIED-ENTRY"]`
    - file_paths: `scripts/check_clarify_plan_alignment.py`, `scripts/check_plan_vk_coverage.py`, `scripts/check_gate_contract_consistency.py`, `scripts/check_integration_gate.py`
    - symbols: `main`
    - change_type: `refactor`
  - `P1-REFERENCE-MIGRATION`
    - blocked_by: `["P1-WRAPPER-L1"]`
    - file_paths: `.cursor/commands/*`, `.agents/skills/*`, `docs/开发文档/*`
    - symbols: `legacy_script_refs`
    - change_type: `refactor`
  - `P2-OBSERVABILITY`
    - blocked_by: `["P1-REFERENCE-MIGRATION"]`
    - file_paths: `scripts/check_workflow_contract.py`, `logs/workflow-gate-usage.jsonl`
    - symbols: `emit_usage_log`, `usage_record_schema_v1`
    - change_type: `add`
  - `P2-TTL-ARCHIVE`
    - blocked_by: `["P2-OBSERVABILITY"]`
    - file_paths: `scripts/*`, `docs/内部参考/任务拆解/*`
    - symbols: `ttl_archive_runner`
    - change_type: `refactor`
  - `P3-RETIRE-LEGACY`
    - blocked_by: `["P2-TTL-ARCHIVE"]`
    - file_paths: `scripts/*`, `.cursor/commands/*`, `.agents/skills/*`, `docs/*`
    - symbols: `legacy_l1_impl`
    - change_type: `delete_or_thin_wrapper`
- execution_chain_seed：
  - preferred_mode: `core`
  - task_key: `PP-20260306-workflow-gate-retirement`
  - card_seed:
    - `P0-FREEZE-COMMANDS`
    - `P1-UNIFIED-ENTRY`
    - `P1-WRAPPER-L1`
    - `P1-REFERENCE-MIGRATION`
    - `P2-OBSERVABILITY`
    - `P2-TTL-ARCHIVE`
    - `P3-RETIRE-LEGACY`
  - execution_contract_hint:
    - delivery_mode: `staged`
    - execution_unit: `per_task`
    - commit_policy: `per_pr`
    - stop_boundary: `per_task`

## 5. 决策权衡（仅放弃原因）
- 放弃路径：
  - 直接删除 4 个 L1 脚本。
  - 不加观测直接进入删除阶段。
  - 全量 `find -delete` 清理过程文件。
- 放弃原因：
  - 会切断命令/技能/文档依赖链，造成架构级故障。
  - 无观测无法证明调用链已清零，删除动作不可审计。
  - 无生命周期边界的清理会破坏可追溯性与运行态真理源。

## 6. risk_rollback_contract
- `RISK-001`：wrapper 参数兼容不完整导致旧命令失败。
  - 回退锚点：`WORKFLOW_GATE_UNIFIED_ENABLED=true`，回退时置 `false`。
  - 回退动作：旧脚本恢复直连原实现。
- `RISK-002`：引用迁移遗漏导致隐式旧入口仍被调用。
  - 回退锚点：`WORKFLOW_GATE_DEPRECATION_ENFORCED=true`，回退时置 `false`。
  - 回退动作：保留 wrapper 并回滚引用迁移，补齐清单后二次迁移。
- `RISK-003`：TTL 误删活跃证据或账本文件。
  - 回退锚点：`WORKFLOW_ARTIFACT_TTL_CLEANUP_ENABLED=true`，回退时置 `false`。
  - 回退动作：立即停用 TTL 清理并从归档恢复，改为白名单 + 时间窗裁剪。

## 7. 设计冻结回执（机读）
```yaml
design_freeze_summary:
  design_actionable: true
  missing_blocks: []
  risk_level: medium
  risk_counterexamples_count: 3
  handoff_contract_ready: true
  product_contract_ready: true
  implementation_seed_count: 7
  semantic_frozen: true
  contract_source_decided: true
  handoff_seed_alignment_ok: true
  parallel_dependency_ready: true
  replay_canonical_field_set: true
  blocking_issues: []
```

## 8. 承接契约（机读）
```yaml
clarify_handoff_contract:
  version: v2
  topic: "workflow-gate-retirement"
  design_source: "docs/plans/2026-03-06-workflow-gate-retirement-design.md"
  handoff_ready: true
  required:
    product_contract_summary:
      target_users:
        - "workflow维护者"
        - "门禁维护者"
        - "文档治理与CI维护者"
      core_scenarios:
        - "旧命令不中断"
        - "统一入口可替代旧链路"
        - "退役可观测可回退"
      business_goal_metrics:
        - "迁移期间命令中断=0"
        - "删除前无 legacy 调用阻断"
        - "主入口收敛到1个"
      non_goals:
        - "不改L0硬门禁"
        - "不改业务逻辑"
      acceptance_gates:
        - "P0冻结完成"
        - "P1统一入口+wrapper+引用迁移完成"
        - "P2观测与TTL达标"
        - "P3删除与全量验收通过"
    requirement_seeds:
      - requirement_id: "REQ-WF-001"
        summary: "冻结直接删除口径并统一到v3"
      - requirement_id: "REQ-WF-002"
        summary: "统一入口支持--mode并保持等价输出"
      - requirement_id: "REQ-WF-003"
        summary: "4个L1旧脚本wrapper化且参数兼容"
      - requirement_id: "REQ-WF-004"
        summary: "命令/技能/文档引用迁移到统一入口"
      - requirement_id: "REQ-WF-005"
        summary: "新增调用观测并支持 legacy 调用阻断判定"
      - requirement_id: "REQ-WF-006"
        summary: "过程文件仅按生命周期+TTL归档"
    implementation_seeds:
      - task_id: "P0-FREEZE-COMMANDS"
      - task_id: "P1-UNIFIED-ENTRY"
      - task_id: "P1-WRAPPER-L1"
      - task_id: "P1-REFERENCE-MIGRATION"
      - task_id: "P2-OBSERVABILITY"
      - task_id: "P2-TTL-ARCHIVE"
      - task_id: "P3-RETIRE-LEGACY"
    execution_chain_seed:
      preferred_mode: "core"
      task_key: "PP-20260306-workflow-gate-retirement"
      card_seed:
        - "P0-FREEZE-COMMANDS"
        - "P1-UNIFIED-ENTRY"
        - "P1-WRAPPER-L1"
        - "P1-REFERENCE-MIGRATION"
        - "P2-OBSERVABILITY"
        - "P2-TTL-ARCHIVE"
        - "P3-RETIRE-LEGACY"
      execution_contract_hint:
        delivery_mode: "staged"
        execution_unit: "per_task"
        commit_policy: "per_pr"
        stop_boundary: "per_task"
    alignment_contract:
      strict_match: true
      requirement_seed_ids:
        - "REQ-WF-001"
        - "REQ-WF-002"
        - "REQ-WF-003"
        - "REQ-WF-004"
        - "REQ-WF-005"
        - "REQ-WF-006"
      implementation_task_ids:
        - "P0-FREEZE-COMMANDS"
        - "P1-UNIFIED-ENTRY"
        - "P1-WRAPPER-L1"
        - "P1-REFERENCE-MIGRATION"
        - "P2-OBSERVABILITY"
        - "P2-TTL-ARCHIVE"
        - "P3-RETIRE-LEGACY"
      card_seed_ids:
        - "P0-FREEZE-COMMANDS"
        - "P1-UNIFIED-ENTRY"
        - "P1-WRAPPER-L1"
        - "P1-REFERENCE-MIGRATION"
        - "P2-OBSERVABILITY"
        - "P2-TTL-ARCHIVE"
        - "P3-RETIRE-LEGACY"
  extended:
    observability_hints:
      - "统一写入 logs/workflow-gate-usage.jsonl"
      - "结果canonical字段固定为 payload"
      - "历史字段按读旧写新兼容"
    risk_counterexample_map:
      - "旧命令参数边界值导致wrapper与旧实现不一致"
      - "文档/技能引用漏迁移导致仍命中旧入口"
      - "TTL误删活跃任务过程文件"
    assumptions:
      - "本轮按 core 串行推进"
      - "删除动作仅在验收矩阵通过后执行"
```

## 9. 一致性自检（机读）
```yaml
clarify_consistency_check:
  clarify_phase: approval
  current_round: 1
  question_mode: package
  open_questions_count: 0
  product_contract_ready: true
  semantic_frozen: true
  contract_source_decided: true
  handoff_seed_alignment_ok: true
  parallel_dependency_ready: true
  replay_canonical_field_set: true
  fail_fast_codes: []
```

## 10. 审批记录
- design_approved: true
- approved_at: 2026-03-06 20:36
- approved_round: round-1
- approval_evidence: 用户明确回复“确认”
- approval_mode: approved
- go_no_go: GO
- blocking_issues: []
