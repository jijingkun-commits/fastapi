---
description: 单指令澄清冻结入口：在 /jjk-clarify 内完成探索与设计冻结
---

# 任务澄清（Clarify Task）

`/jjk-clarify` 是 `jjk-*` 执行链的设计冻结入口，目标是把模糊想法变成“可直接进入 `/jjk-plan`”的基线。

## 与 `brainstorming` 的关系

1. `/jjk-clarify` 默认直接执行“设计冻结 + handoff”，不强制前置 `brainstorming`。
2. 若用户明确要求“先头脑风暴/多方案比较”，在 `/jjk-clarify` 内先执行探索轮再收敛，不强制切换命令。
3. 进入 `/jjk-clarify` 冻结态后，主文档永远只保留最终单方案。

---

## 执行契约

1. 设计未审批前，禁止进入任何下游命令。
2. 标准产物：`docs/plans/YYYY-MM-DD-<topic>-design.md`。
3. 每份 `design.md` 必须包含 `design_freeze_summary`、`clarify_handoff_contract`、`clarify_consistency_check` 三个 YAML 区块。
4. 仅当用户明确要求 `brainstorming` 且该能力不可用时，走 fallback 并在执行备注标记 `BRAINSTORM_UNAVAILABLE_FALLBACK`。
5. 使用联网搜索和github搜索工具，以及上下文理解能力，确保设计符合用户意图。
6. 修改本命令/模板/镜像后，必须执行 `python3 scripts/check_clarify_contract_consistency.py` 做一致性体检。

---

## 提问原则

1. **默认问题包提问**：边界清晰时，`question_mode=package`，单轮最多 5 个关键问题
2. **先锁定目标/边界，再锁定契约/实现落点**
3. **不做并列方案打分**
4. **遇到以下情况切换为单题追问（`question_mode=single`）**：
   - 用户回答模糊或存在矛盾
   - 涉及跨模块状态契约（需先确认边界再问细节）
   - 连续 2 轮问题包仍不清晰

---

## 澄清阶段状态机（强制）

1. `clarify_phase=explore`：仍存在未冻结信息，允许继续提问；`open_questions_count >= 1`。
2. `clarify_phase=freeze`：最终单方案与机读区块已成型，准备做门禁自检；`open_questions_count = 0`。
3. `clarify_phase=approval`：全部门禁通过，等待用户明确确认；`open_questions_count = 0`。
4. 每一轮都必须显式维护：`clarify_phase/current_round/question_mode/open_questions_count`。
5. `clarify_phase != approval` 或 `open_questions_count > 0` 时，禁止发起正式审批。

---

## 设计完成定义（DoD v3.2，极简）

审批前必须冻结以下 7 块（缺一不可）：

1. `scope_contract`：目标 + 范围 + 边界 + 成功标准。
2. `product_contract`（PRD-Lite）：目标用户与核心场景 + 业务目标/KPI + 非目标 + 验收口径 + 发布约束。
3. `architecture_contract`：模块边界 + 端到端数据流 + 状态生命周期 + 异常语义。
4. `requirement_seeds`：字段级需求原子（至少 1 条）。
5. `implementation_seeds`：轻量版任务原子（`task_id + file_paths + symbols + change_type`，至少 1 条）。
6. `execution_chain_seed`：`preferred_mode + task_key + card_seed` 框架。
7. `risk_rollback_contract`：至少 2 条关键风险 + 回退锚点（开关默认 `true`，回退置 `false`）。

缺失任一块时：

1. 输出 `CLARIFY_DESIGN_NOT_ACTIONABLE`。
2. 继续澄清，不得审批。

---

## 工程流一致性附加门禁（v3.2，强制）

审批前除 DoD 外，必须额外通过以下 6 项一致性校验（任一失败即 `FAIL_FAST`）：

1. **产品契约完整性门禁（PRD-Lite）**
   - `product_contract` 必须具备：`target_users/core_scenarios/business_goals(non-empty KPI)/non_goals/acceptance_gates`。
   - 禁止“待确认/后续补充/TBD”占位进入审批态。
   - 失败输出：`CLARIFY_PRODUCT_CONTRACT_INCOMPLETE`。
2. **语义唯一化门禁**
   - 关键异常语义必须“单策略冻结”（例如缺失关键字段时由后端归一为 `error` 或前端统一 fallback，只能二选一）。
   - 禁止在最终方案中保留“`A 或 B`”未决语义。
   - 失败输出：`CLARIFY_SEMANTIC_NOT_FROZEN`。
3. **契约源唯一化门禁**
   - “单一契约源”必须明确唯一机制（如代码生成 *或* 镜像同步，必须单选并冻结）。
   - 禁止“并存可选”描述进入 handoff。
   - 失败输出：`CLARIFY_CONTRACT_SOURCE_UNDECIDED`。
4. **handoff 种子对齐门禁**
   - `clarify_handoff_contract.required.requirement_seeds` 必须完整覆盖主文档 `requirement_seeds`。
   - `clarify_handoff_contract.required.implementation_seeds` 必须完整覆盖主文档 `implementation_seeds`。
   - `execution_chain_seed.card_seed` 必须与 implementation task_id 集一致（可排序不同，不可缺失/新增）。
   - 失败输出：`CLARIFY_HANDOFF_CONTRACT_INCOMPLETE`。
5. **并行依赖门禁**
   - 当 `preferred_mode=parallel` 且 `card_seed>=2` 时，`implementation_seeds` 必须显式给出依赖关系（`blocked_by` 或等价字段）。
   - 必须可恢复出拓扑顺序，不允许“无依赖并行”直接落地。
   - 失败输出：`CLARIFY_EXECUTION_DEPENDENCY_MISSING`。
6. **回放归一门禁**
   - 必须指定结构化结果在消息体的 canonical 字段（如 `additional_kwargs`）。
   - 若存在历史字段并存，必须给出“读旧写新”迁移语义。
   - 失败输出：`CLARIFY_REPLAY_CANONICAL_UNSET`。

---

## 设计冻结回执（唯一门禁）

审批前必须输出：

```yaml
design_freeze_summary:
  design_actionable: true|false
  missing_blocks: []
  risk_level: low|medium|high
  risk_counterexamples_count: 2
  handoff_contract_ready: true|false
  product_contract_ready: true|false
  implementation_seed_count: <int>
  semantic_frozen: true|false
  contract_source_decided: true|false
  handoff_seed_alignment_ok: true|false
  parallel_dependency_ready: true|false
  replay_canonical_field_set: true|false
  blocking_issues: []
```

门禁规则：

1. `design_actionable=false` 或 `missing_blocks` 非空：禁止审批。
2. `handoff_contract_ready=false`：禁止审批。
3. `product_contract_ready=false`：禁止审批。
4. `implementation_seed_count=0`：禁止审批。
5. `risk_counterexamples_count<2`：禁止审批。
6. `semantic_frozen=false`：禁止审批。
7. `contract_source_decided=false`：禁止审批。
8. `handoff_seed_alignment_ok=false`：禁止审批。
9. `parallel_dependency_ready=false`（仅 parallel 模式要求）：禁止审批。
10. `replay_canonical_field_set=false`：禁止审批。
11. `blocking_issues` 非空：禁止审批。

---

## 设计审批（v3 自然版）

进入 `clarify_phase=approval` 后必须主动发起确认：

> 以上设计已完全冻结。  
> 请回复：**确认 / 需要修改XX点 / 否**  
> （回复“确认”或“是”且门禁全部通过即视为审批通过，可进入 `/jjk-plan`；否则记录条件采纳并继续澄清）

审批规则：

1. 仅当 `clarify_consistency_check.clarify_phase=approval` 且 `open_questions_count=0` 时，才可发起正式审批。
2. 仅当所有门禁通过且用户回复肯定语义（如“确认”“是”“OK”“走这个”）时，审批通过（`design_approved=true`）。
3. 若用户肯定但仍存在阻断项，记录“条件采纳”并保持 `design_approved=false`，输出 `CONDITIONAL_APPROVAL_BLOCKED`，不得进入下游。
4. 非肯定语义或存在修改点时，继续澄清，不进入下游。
5. 审批动作后，自动在 `design.md` 追加审批记录：`design_approved/approved_at/approved_round/approval_evidence`；若为条件采纳，建议补充 `approval_mode=conditional` 与 `go_no_go=NO_GO`。

---

## clarify_handoff_contract（v2，推荐结构）

保持 v2 结构（`required + extended`），并继续兼容 v1 顶层字段。

```yaml
clarify_handoff_contract:
  version: v2
  topic: "<topic>"
  design_source: docs/plans/YYYY-MM-DD-<topic>-design.md
  handoff_ready: true
  required:
    product_contract_summary:
      target_users: []
      core_scenarios: []
      business_goal_metrics: []
      non_goals: []
      acceptance_gates: []
    requirement_seeds: [...]
    implementation_seeds: [...]
    execution_chain_seed:
      preferred_mode: core|parallel
      task_key: PP-YYYYMMDD-topic
      card_seed: []
      execution_contract_hint:
        delivery_mode: one_shot|staged
        execution_unit: all_tasks|per_pr|per_task
        commit_policy: single_commit|per_pr
        stop_boundary: none|per_pr|per_task
    alignment_contract:
      strict_match: true
      requirement_seed_ids: []
      implementation_task_ids: []
      card_seed_ids: []
  extended:
    observability_hints: []
    risk_counterexample_map: []
    assumptions: []
```

---

## clarify_consistency_check（v3，强制）

每份 `design.md` 必须包含以下机读区块，用于记录澄清阶段状态与审批前最后自检：

```yaml
clarify_consistency_check:
  clarify_phase: explore|freeze|approval
  current_round: <int>
  question_mode: package|single
  open_questions_count: <int>
  product_contract_ready: true|false
  semantic_frozen: true|false
  contract_source_decided: true|false
  handoff_seed_alignment_ok: true|false
  parallel_dependency_ready: true|false
  replay_canonical_field_set: true|false
  fail_fast_codes: []
```

门禁规则：

1. `clarify_phase=approval` 且 `open_questions_count=0` 后，才可发起正式审批。
2. `current_round<1`：输出 `CLARIFY_ROUND_INVALID`。
3. `question_mode` 仅允许 `package|single`。
4. `fail_fast_codes` 非空时，禁止审批。

---

## Team 策略

默认单代理。满足 `>=2` 条时建议升级：

1. `module_count >= 3`
2. `boundary_count >= 2`
3. `uncertainty_count >= 2`
4. `estimated_file_count >= 12`

无 Team 能力时降级单代理，并标记 `TEAM_UNAVAILABLE_FALLBACK`。

---

## 执行备注

若发生能力降级或模板异常，回复末尾追加：

```yaml
execution_notes:
  fallback:
    brainstorming: false
    team: false
  template:
    missing: false
    source: "docs/内部参考/迭代需求/_templates/jjk_clarify_templates.md"
  question_mode: "package|single"
  degrade_reason: ""
  alternative_tool: ""
  verification: ""
```

---

## 禁止项

1. 禁止未审批直接跳实现。
2. 禁止在主文档输出 A/B/C 对比。
3. 禁止把“brainstorming 与 clarify 冲突”作为固定话术输出（仅在用户明确要求排查冲突时说明）。
4. 禁止在未被用户要求时默认建议切换到其他探索命令。

---

*使用 `/jjk-clarify` 触发。目标是最小必要流程 + 最大执行确定性。*
