# AI / Skill / DB Runtime 工程流验证门禁收紧设计

## 1. scope_contract
- 目标:
  - 先只收紧 `AI / skill / DB runtime` 相关改动的测试与验收口径，避免“离线专项通过，但真实 DB/运行态未覆盖”继续被误判为可放行。
  - 把“这次必须测什么”从执行者临场判断，收敛为 `jjk-plan` 产出的显式 `required_gates` 契约。
  - 把 `jjk-test` 与 `jjk-verify` 的职责固定为“执行与裁决”，不再允许对高风险改动自行放宽 DB/运行态验证要求。
- 范围:
  - 工程流命令与模板：`.cursor/commands/jjk-plan.md`、`.cursor/commands/jjk-test.md`、`.cursor/commands/jjk-verify.md`
  - 项目覆盖模板：`docs/内部参考/迭代需求/_templates/jjk_plan_templates.md`、`docs/内部参考/迭代需求/_templates/jjk_test_templates.md`、`docs/内部参考/迭代需求/_templates/jjk_verify_templates.md`
  - 项目工作流与测试文档：`docs/开发文档/工作流/开发工作流.md`、`docs/开发文档/测试管理/测试用例库.md`
  - 首批强制命中范围：`app/ai/workflow/**`、`app/services/skill_service.py`、`app/models/**` 中 skill / config / truth source 相关文件、迁移与初始化脚本。
- 边界:
  - 本轮不把全项目所有改动统一升级为强制联机验证，只先约束 `AI / skill / DB runtime` 高风险改动。
  - 本轮不重构现有测试脚本目录结构，只增加工程流对 Gate 的声明、执行与判定约束。
  - 本轮不要求每次改动都跑全量 E2E；浏览器链路仅在命中前端路径或用户明确要求时提升到 `L4`。
- 成功标准:
  - `jjk-plan` 产物中存在唯一可机读的 `required_gates`，且 `jjk-test` / `jjk-verify` 只消费该字段，不再靠自由文本推断。
  - 对 `AI / skill / DB runtime` 改动，缺少真实 DB 证据时不得给出 `PASS`，直接 `FAIL`。
  - `L3` 运行态最小验证固定为：健康检查 + 真实消息 + DB/日志断言。
  - 测试报告与验收报告都能明确区分 `Required / Executed / Result / Evidence / Blocker`。

## 2. product_contract

### 2.1 target_users
- 使用 `jjk-plan / jjk-test / jjk-verify` 的开发者。
- 负责 AI / skill / 数据链路交付的实现者与验收者。
- 在未上线阶段为设计合理性兜底的项目 owner。

### 2.2 core_scenarios
- 场景 A：修改 `skill runtime / progressive catalog / truth source` 后，工程流必须强制要求真实 DB 与运行态 smoke，而不是只跑离线专项。
- 场景 B：修改 `AI workflow / DB-backed routing / preprocess` 后，`jjk-verify` 必须能从证据矩阵直接判定“缺 DB 证据 -> FAIL”。
- 场景 C：历史 `review_report / test_report` 仍可能是自由文本，但新的工程流必须有唯一机读字段支撑后续执行。

### 2.3 business_goals
- KPI-1：`AI / skill / DB runtime` 改动的“缺 DB 证据却被放行”为 `0`。
- KPI-2：命中高风险范围的改动，`required_gates` 产出覆盖率达到 `100%`。
- KPI-3：`jjk-verify` 对高风险改动的误判 `PASS` 数量为 `0`。

### 2.4 non_goals
- 不在本轮解决 CI 基础设施、外部依赖服务稳定性、Playwright 全量提速。
- 不在本轮统一所有低风险改动的测试策略。
- 不在本轮重写仓库已有测试案例内容，只调整工程流如何消费这些测试资产。

### 2.5 acceptance_gates
- `AG-01`：`jjk-plan` 为命中高风险范围的改动生成 `validation_contract.required_gates`。
- `AG-02`：`jjk-test` 按 `required_gates` 输出 Gate 结果矩阵；缺失强制 Gate 时 `FAIL_FAST`。
- `AG-03`：`jjk-verify` 按 `required_gates` 对照测试证据；缺 DB 证据直接 `FAIL`。
- `AG-04`：`L3` 的最小口径固定为“健康检查 + 真实消息 + DB/日志断言”，不可再降级为纯日志或纯 UI 响应。
- `AG-05`：文档与模板同步更新，确保新口径能稳定产出到后续任务。

### 2.6 release_constraints
- 项目未上线阶段，优先级固定为“严格阻断漏测”高于“开发速度”。
- 若执行环境不满足 `L2/L3`，应阻断交付，而不是将缺口伪装为 `WARN` 或 `SKIP`。

## 3. architecture_contract

### 3.1 模块边界
- **Plan Contract Source**
  - `jjk-plan` 是“该测什么”的唯一契约源。
  - 它必须把风险分级与 `required_gates` 写进可机读产物，供后续命令消费。
- **Review Risk Annotator**
  - `jjk-review` 只负责识别风险边界与阻断项，不再定义最终 Gate 集。
  - 它可补充 `gate_hints`，但不能覆盖 `required_gates`。
- **Test Executor**
  - `jjk-test` 只负责执行 `required_gates` 对应命令、沉淀证据、填报 Gate 矩阵。
  - 它不得因为环境不全而静默缩减高风险 Gate。
- **Verify Arbiter**
  - `jjk-verify` 只负责“应有证据 vs 实际证据”的最终裁决。
  - 对强制 Gate 缺失、强制 Gate 失败、阻断项未关闭，必须直接 `FAIL`。
- **Evidence Artifacts**
  - `implementation_plan` 保存 `required_gates`。
  - `test_report` 保存 `gate_results`。
  - `verify_report` 保存 `evidence_ledger` 与最终结论。

### 3.2 依赖方向
1. `jjk-plan -> implementation_plan.validation_contract.required_gates`
2. `jjk-review -> review_report.risk_boundary / blocker_summary`
3. `jjk-test -> test_report.gate_results`
4. `jjk-verify -> consume(plan + review + test) -> PASS|WARN|FAIL`

冻结规则：
- `jjk-test` / `jjk-verify` 禁止跳过 `jjk-plan` 的 `required_gates` 自行推断。
- `jjk-review` 的风险评语不能替代 `required_gates`。
- `jjk-verify` 的最终判定必须建立在 `required_gates` 完整对账之上。

### 3.3 状态归属
- `validation_contract.required_gates`：唯一归属 `implementation_plan`。
- `gate_results[*]`：唯一归属 `test_report`。
- `evidence_ledger[*]` 与 `verify_conclusion`：唯一归属 `verify_report`。
- 自由文本中的“已测 / 已验证 / 应该没问题”不具备机器判定资格。

### 3.4 端到端数据流
1. `jjk-plan` 根据改动范围与风险分类产出 `validation_contract.required_gates`。
2. `jjk-review` 标注高风险边界与 blocker，供 `jjk-test` / `jjk-verify` 参考。
3. `jjk-test` 读取 `required_gates`，执行 `L0/L1/L2/L3/L4` 中被要求的 Gate。
4. `jjk-test` 输出 `gate_results`，每条结果至少包含：`gate_id / required / executed / result / evidence / blocker_code`。
5. `jjk-verify` 读取 `required_gates + gate_results + review_report`。
6. `jjk-verify` 输出 `evidence_ledger` 与最终结论：
   - 任一强制 Gate 缺失 -> `FAIL`
   - 任一强制 Gate 失败 -> `FAIL`
   - blocker 未关闭 -> `FAIL`
   - 核心链路全部通过且证据完整 -> `PASS`

### 3.5 Gate 分层语义（首批只对高风险改动强制）

| Gate | 语义 | 最小证据 |
|---|---|---|
| `L0` | 环境与前置门禁 | DB 连通、端口、健康检查、配置可用 |
| `L1` | 单测 / 契约 / Mock | 邻近单测、契约测试、静态守护 |
| `L2` | DB 集成 / 持久化 / truth source | 迁移存在性、真实表/列、真实写读或查询断言 |
| `L3` | 运行态 smoke | 健康检查 + 真实消息 + DB/日志断言 |
| `L4` | 浏览器 / UAT | E2E、关键路径回包、页面或交互断言 |

### 3.6 风险分级（本轮冻结）

| 风险级别 | 触发条件 | 强制 Gate | 缺证据策略 |
|---|---|---|---|
| `R1` | 纯局部逻辑、无真实状态变更 | `L1` | `WARN` |
| `R2` | 普通 API / 服务改动，涉及持久化但不触碰 truth source 主链 | `L0 + L1 + L2` | `WARN/FAIL` 依 blocker 而定 |
| `R3` | `AI / skill / DB runtime / migration / truth source / preprocess` | `L0 + L1 + L2 + L3` | **直接 `FAIL`** |
| `R4` | `R3` 且涉及前端关键路径或用户要求联机确认 | `L0 + L1 + L2 + L3 + L4` | **直接 `FAIL`** |

冻结口径：本次只要求 `AI / skill / DB runtime` 改动至少命中 `R3`。

### 3.7 异常语义（单策略冻结）
- `required_gates_missing`
  - 触发：`jjk-plan` 未产出 `required_gates`。
  - 处理：`jjk-test` / `jjk-verify` 直接 `FAIL_FAST`，不再用自由文本推断补救。
- `db_evidence_missing`
  - 触发：命中 `R3/R4`，但 `L2` 或 `L3` 缺失 DB 证据。
  - 处理：`jjk-verify` 直接 `FAIL`。
- `runtime_smoke_missing`
  - 触发：命中 `R3/R4`，但未完成健康检查 + 真实消息 + DB/日志断言。
  - 处理：`jjk-test` 标记 Gate 缺失，`jjk-verify` 直接 `FAIL`。
- `environment_not_ready`
  - 触发：本地或 worktree 环境不满足运行态验证前置。
  - 处理：阻断本轮交付；允许进入修环境或补证据，不允许假装通过。

### 3.8 契约源唯一化与迁移语义
- 唯一契约源字段：`implementation_plan.validation_contract.required_gates`
- 唯一测试结果字段：`test_report.gate_results`
- 唯一验收账本字段：`verify_report.evidence_ledger`

迁移语义：
- 新生成产物一律“写新字段”。
- 遇到历史 `review_report` / `test_report` 仅含自由文本时，`jjk-test` / `jjk-verify` 可读取旧文本做诊断说明，但**不得**将其视为可执行 Gate 契约。
- 历史缺少 `required_gates` 的计划产物必须先重跑 `jjk-plan`，然后才能进入正式测试/验收。

### 3.9 回放归一字段
- `implementation_plan.validation_contract.required_gates` 是“本次应该做哪些 Gate”的 canonical 字段。
- 历史 `risk_boundary`、`test_scope`、自由文本矩阵只作辅助展示，不再承担执行语义。
- `test_report.gate_results` 是“本次实际做了什么”的 canonical 字段。
- `verify_report.evidence_ledger` 是“本次为什么能/不能放行”的 canonical 字段。

## 4. requirement_seeds
```yaml
requirement_seeds:
  - design_item: D-01
    fr_id: FR-PLAN-REQUIRED-GATES-SINGLE-SOURCE
    trigger: jjk-plan 生成 implementation_plan
    input_contract:
      required_fields: [task_id, feature_id, risk_boundary]
      optional_fields: [changed_paths, user_acceptance_focus]
      defaults:
        user_acceptance_focus: []
    output_contract:
      required_fields: [validation_contract.required_gates, validation_contract.risk_level]
      optional_fields: [validation_contract.gate_reasoning]
    failure_semantics: 缺少 required_gates 时下游禁止执行正式测试与验收
    observability_fields: [task_id, feature_id, risk_level, required_gate_ids]
    rollback_anchor: ENABLE_REQUIRED_GATES_ENFORCED=false
    acceptance_cmd_ref: rg -n "required_gates|validation_contract" .cursor/commands/jjk-plan.md docs/内部参考/迭代需求/_templates/jjk_plan_templates.md

  - design_item: D-02
    fr_id: FR-TEST-GATE-MATRIX-STRICT
    trigger: jjk-test 消费 implementation_plan
    input_contract:
      required_fields: [validation_contract.required_gates]
      optional_fields: [review_report.risk_boundary, review_report.blocker_summary]
      defaults: {}
    output_contract:
      required_fields: [test_report.gate_results]
      optional_fields: [test_report.blocker_summary, test_report.degrade_records]
    failure_semantics: 命中 R3/R4 时，任一强制 Gate 未执行或无证据均标记失败，不得静默降级
    observability_fields: [gate_id, required, executed, result, blocker_code]
    rollback_anchor: ENABLE_TEST_GATE_MATRIX_STRICT=false
    acceptance_cmd_ref: rg -n "gate_results|Required|Executed|Result|Evidence|Blocker" .cursor/commands/jjk-test.md docs/内部参考/迭代需求/_templates/jjk_test_templates.md

  - design_item: D-03
    fr_id: FR-VERIFY-DB-EVIDENCE-FAIL-CLOSED
    trigger: jjk-verify 消费 review_report + test_report + implementation_plan
    input_contract:
      required_fields: [validation_contract.required_gates, test_report.gate_results]
      optional_fields: [review_report.blocker_summary]
      defaults: {}
    output_contract:
      required_fields: [verify_report.evidence_ledger, verify_report.conclusion]
      optional_fields: [verify_report.next_actions]
    failure_semantics: R3/R4 缺 DB 证据或缺 L3 运行态证据时直接 FAIL
    observability_fields: [missing_gate_ids, missing_db_evidence, missing_runtime_smoke, conclusion]
    rollback_anchor: ENABLE_DB_EVIDENCE_FAIL_CLOSED=false
    acceptance_cmd_ref: rg -n "evidence_ledger|db_evidence_missing|runtime_smoke_missing|FAIL" .cursor/commands/jjk-verify.md docs/内部参考/迭代需求/_templates/jjk_verify_templates.md

  - design_item: D-04
    fr_id: FR-RUNTIME-SMOKE-MINIMAL-TRIPLE-CHECK
    trigger: 命中 AI / skill / DB runtime 高风险改动
    input_contract:
      required_fields: [VK_BACKEND_BASE_URL, real_message_input]
      optional_fields: [VK_FRONTEND_BASE_URL, expected_db_side_effect]
      defaults: {}
    output_contract:
      required_fields: [health_check_passed, runtime_message_passed, db_or_log_assert_passed]
      optional_fields: [actual_url, log_excerpt, db_assert_query]
    failure_semantics: 三项任一缺失或失败均记为 L3 FAIL，不得以 UI 有响应替代通过
    observability_fields: [backend_url, frontend_url, thread_id, db_assert_query, log_signal]
    rollback_anchor: ENABLE_RUNTIME_SMOKE_REQUIRED_FOR_AI_DB=false
    acceptance_cmd_ref: rg -n "L3|真实消息|DB/日志断言|health" .cursor/commands/jjk-test.md .cursor/commands/jjk-verify.md docs/开发文档/测试管理/测试用例库.md
```

## 5. implementation_seeds
```yaml
implementation_seeds:
  - task_id: T-01
    feature_id: P1-required-gates-contract
    file_paths:
      - .cursor/commands/jjk-plan.md
      - docs/内部参考/迭代需求/_templates/jjk_plan_templates.md
    symbols:
      - validation_contract.required_gates
      - validation_contract.risk_level
      - gate_reasoning
    change_type: modify

  - task_id: T-02
    feature_id: P1-test-gate-matrix
    file_paths:
      - .cursor/commands/jjk-test.md
      - docs/内部参考/迭代需求/_templates/jjk_test_templates.md
    symbols:
      - test_report.gate_results
      - required_vs_executed_matrix
      - L3_runtime_smoke_contract
    change_type: modify

  - task_id: T-03
    feature_id: P1-verify-fail-closed
    file_paths:
      - .cursor/commands/jjk-verify.md
      - docs/内部参考/迭代需求/_templates/jjk_verify_templates.md
    symbols:
      - verify_report.evidence_ledger
      - db_evidence_missing
      - runtime_smoke_missing
    change_type: modify

  - task_id: T-04
    feature_id: P1-doc-sync
    file_paths:
      - docs/开发文档/工作流/开发工作流.md
      - docs/开发文档/测试管理/测试用例库.md
    symbols:
      - required_gates_policy
      - risk_level_R3_R4
      - L0_to_L4_gate_matrix
    change_type: modify

  - task_id: T-05
    feature_id: P1-strict-guard-tests
    file_paths:
      - docs/内部参考/迭代需求/_templates/jjk_plan_templates.md
      - docs/内部参考/迭代需求/_templates/jjk_test_templates.md
      - docs/内部参考/迭代需求/_templates/jjk_verify_templates.md
    symbols:
      - required_gates_examples
      - gate_results_examples
      - evidence_ledger_examples
    change_type: modify
```

## 6. execution_chain_seed
```yaml
execution_chain_seed:
  preferred_mode: core
  task_key: PP-20260308-ai-skill-db-runtime-validation-gates
  card_seed:
    - T-01
    - T-02
    - T-03
    - T-04
    - T-05
  execution_contract_hint:
    delivery_mode: staged
    execution_unit: all_tasks
    commit_policy: single_commit
    stop_boundary: none
```

## 7. risk_rollback_contract
- 风险 R-01：历史计划产物不含 `required_gates`，导致工程流升级后大面积阻断。
  - 取舍：接受短期阻断，强制重跑 `jjk-plan`，避免继续让旧自由文本充当机器契约。
  - 回退锚点：`ENABLE_REQUIRED_GATES_ENFORCED=true`，紧急回退置 `false`。
- 风险 R-02：本地环境不稳导致高风险改动频繁卡在 `L3`，开发者短期体感变慢。
  - 取舍：未上线阶段优先严格阻断漏测，而不是保持表面流畅。
  - 回退锚点：`ENABLE_RUNTIME_SMOKE_REQUIRED_FOR_AI_DB=true`，紧急回退置 `false`。
- 风险 R-03：`jjk-verify` 从“证据不足给 WARN”切到“缺 DB 证据直接 FAIL”后，历史习惯与新口径冲突。
  - 取舍：固定 fail-closed 语义，减少误放行。
  - 回退锚点：`ENABLE_DB_EVIDENCE_FAIL_CLOSED=true`，紧急回退置 `false`。

## 8. 最终冻结结论
- 单方案冻结：`jjk-plan` 产出 `required_gates`，`jjk-test` 执行 Gate，`jjk-verify` 对账裁决。
- 单语义冻结：命中 `AI / skill / DB runtime` 的 `R3/R4` 改动，缺 DB 证据直接 `FAIL`。
- 单最小口径冻结：`L3 = 健康检查 + 真实消息 + DB/日志断言`。
- 单优先级冻结：项目未上线，严格阻断漏测高于开发速度。

## 9. 设计冻结回执（机读）
```yaml
design_freeze_summary:
  design_actionable: true
  missing_blocks: []
  risk_level: high
  risk_counterexamples_count: 3
  handoff_contract_ready: true
  product_contract_ready: true
  implementation_seed_count: 5
  semantic_frozen: true
  contract_source_decided: true
  handoff_seed_alignment_ok: true
  parallel_dependency_ready: true
  replay_canonical_field_set: true
  blocking_issues: []
```

## 10. clarify_handoff_contract（机读）
```yaml
clarify_handoff_contract:
  version: v2
  topic: "ai-skill-db-runtime-validation-gates"
  design_source: "docs/plans/2026-03-08-ai-skill-db-runtime-validation-gate-design.md"
  handoff_ready: true
  required:
    product_contract_summary:
      target_users:
        - 使用 jjk-plan / jjk-test / jjk-verify 的开发者
        - 负责 AI / skill / DB runtime 交付的实现者与验收者
      core_scenarios:
        - skill runtime / truth source 改动必须强制真实 DB 与运行态验证
        - verify 对缺 DB 证据的高风险改动直接 FAIL
        - 新工程流必须以 required_gates 作为唯一测试契约源
      business_goal_metrics:
        - "AI / skill / DB runtime 改动缺 DB 证据被放行 = 0"
        - "高风险改动 required_gates 覆盖率 = 100%"
        - "verify 对高风险改动误判 PASS = 0"
      non_goals:
        - 不在本轮统一所有低风险改动的测试策略
        - 不在本轮重构现有测试目录结构
      acceptance_gates:
        - AG-01: jjk-plan 生成 validation_contract.required_gates
        - AG-02: jjk-test 输出 gate_results 矩阵
        - AG-03: jjk-verify 缺 DB 证据直接 FAIL
        - AG-04: L3 固定为健康检查 + 真实消息 + DB/日志断言
        - AG-05: 工作流与测试文档同步更新
    requirement_seeds:
      - design_item: D-01
        fr_id: FR-PLAN-REQUIRED-GATES-SINGLE-SOURCE
      - design_item: D-02
        fr_id: FR-TEST-GATE-MATRIX-STRICT
      - design_item: D-03
        fr_id: FR-VERIFY-DB-EVIDENCE-FAIL-CLOSED
      - design_item: D-04
        fr_id: FR-RUNTIME-SMOKE-MINIMAL-TRIPLE-CHECK
    implementation_seeds:
      - task_id: T-01
        feature_id: P1-required-gates-contract
      - task_id: T-02
        feature_id: P1-test-gate-matrix
      - task_id: T-03
        feature_id: P1-verify-fail-closed
      - task_id: T-04
        feature_id: P1-doc-sync
      - task_id: T-05
        feature_id: P1-strict-guard-tests
    execution_chain_seed:
      preferred_mode: core
      task_key: PP-20260308-ai-skill-db-runtime-validation-gates
      card_seed:
        - T-01
        - T-02
        - T-03
        - T-04
        - T-05
      execution_contract_hint:
        delivery_mode: staged
        execution_unit: all_tasks
        commit_policy: single_commit
        stop_boundary: none
    alignment_contract:
      strict_match: true
      requirement_seed_ids:
        - D-01
        - D-02
        - D-03
        - D-04
      implementation_task_ids:
        - T-01
        - T-02
        - T-03
        - T-04
        - T-05
      card_seed_ids:
        - T-01
        - T-02
        - T-03
        - T-04
        - T-05
  extended:
    observability_hints:
      - gate_id
      - risk_level
      - missing_db_evidence
      - missing_runtime_smoke
    risk_counterexample_map:
      - risk_id: R-01
        counterexample: 历史 plan 无 required_gates 导致误进测试阶段
      - risk_id: R-02
        counterexample: UI 有响应但 DB 未补齐仍被误判通过
      - risk_id: R-03
        counterexample: 本地环境未拉起却以 WARN 冒充通过
    assumptions:
      - jjk-plan 可稳定生成 implementation_plan
      - 项目允许同步调整 commands 与项目模板
      - 高风险改动存在可执行的 L0/L2/L3 最小验证路径
```

## 11. clarify_consistency_check（机读）
```yaml
clarify_consistency_check:
  clarify_phase: approval
  current_round: 2
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
