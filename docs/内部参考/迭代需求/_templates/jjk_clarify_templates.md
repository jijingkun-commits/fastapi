# `/jjk-clarify` 项目主模板（v3）

## 1) 默认提问模板（一问一答）

```markdown
## 当前澄清问题（单题）

请仅回答下面 1 个关键问题：

<问题正文>

回答后我将继续下一题，直到冻结 `design_freeze_summary` 与 `clarify_handoff_contract`。
```

## 2) 提速模板（仅用户显式要求时启用）

```markdown
## 本轮澄清主题：<主题名>

A. 目标优先级（单选）
1) 先可用 2) 先稳定 3) 先性能

B. 范围边界（多选）
1) 仅后端 2) 前后端都改 3) 含工作流/编排

C. 交付约束（单选）
1) 本周交付 2) 可分阶段 3) 本轮只冻结设计

D. 关键证据（自由文本，必填）
- 现状证据:
- 失败样例（至少 1 条）:
- 不可做项/依赖约束:

E. 轻量实现落点（自由文本，必填）
- task_id（至少 1 条）:
- file_paths:
- symbols:
- change_type:

请回复 `A?/B?/C?`，并补充 `D/E`。
```

## 3) design 文档结构模板

> 主文档只保留最终方案，禁止 A/B/C 对比。

```markdown
# <topic> 设计说明

## 1. scope_contract
- 目标:
- 范围:
- 边界:
- 成功标准:

## 2. product_contract（PRD-Lite）
- target_users:
- core_scenarios:
- business_goals（含可量化 KPI）:
- non_goals:
- acceptance_gates:
- release_constraints:

## 3. architecture_contract
- 模块边界与职责:
- 端到端数据流:
- 状态生命周期:
- 异常语义与降级策略:

## 4. 最终方案
- 方案描述:
- 关键决策:

## 5. 决策权衡（仅放弃原因）
- 放弃路径:
- 放弃原因:

## 6. risk_rollback_contract
- 关键风险（>=2）:
- 回退锚点（默认开关 true，回退 false）:
```

## 4) 设计冻结回执（机读）模板

````markdown
## 7. 设计冻结回执（机读）
```yaml
design_freeze_summary:
  design_actionable: true
  missing_blocks: []
  risk_level: low
  risk_counterexamples_count: 2
  handoff_contract_ready: true
  product_contract_ready: true
  implementation_seed_count: 1
  semantic_frozen: true
  contract_source_decided: true
  handoff_seed_alignment_ok: true
  parallel_dependency_ready: true
  replay_canonical_field_set: true
  blocking_issues: []
```
````

## 5) 承接契约（机读）模板（v2 推荐）

````markdown
## 8. 承接契约（机读）
```yaml
clarify_handoff_contract:
  version: v2
  topic: "<topic>"
  design_source: docs/plans/YYYY-MM-DD-<topic>-design.md
  handoff_ready: true
  required:
    product_contract_summary:
      target_users: [运营管理员]
      core_scenarios: [在会话中稳定查看结构化结果]
      business_goal_metrics: [结构化结果可见率>=99%]
      non_goals: [本轮不重构多智能体路由策略]
      acceptance_gates: [未知 data_type 必须可见 fallback]
    requirement_seeds:
      - design_item: D-01
        fr_id: FR-01
        trigger: 用户输入澄清请求
        input_contract:
          required_fields: [user_id, message]
          optional_fields: [session_id]
          defaults:
            session_id: ""
        output_contract:
          required_fields: [intent, confidence]
        failure_semantics: 无法解析时返回可重试提示
        observability_fields: [trace_id, intent, confidence]
        rollback_anchor: ENABLE_XXX=false
        acceptance_cmd_ref: venv/bin/python -m pytest tests/unit/test_xxx.py -q
    implementation_seeds:
      - task_id: T-01
        feature_id: P1-01
        blocked_by: []
        file_paths:
          - app/ai/workflow/multi_agent_graph.py
        symbols:
          - build_intent_plan
        change_type: modify
    execution_chain_seed:
      preferred_mode: core
      task_key: PP-YYYYMMDD-topic
      card_seed: []
      execution_contract_hint:
        delivery_mode: one_shot
        execution_unit: all_tasks
        commit_policy: single_commit
        stop_boundary: none
    alignment_contract:
      strict_match: true
      requirement_seed_ids: [D-01]
      implementation_task_ids: [T-01]
      card_seed_ids: [T-01]
  extended:
    observability_hints:
      - trace_id 贯穿全链路
    risk_counterexample_map:
      - risk_id: R-01
        counterexample: 缺少 session_id 时上下文丢失
        verify_cmd: venv/bin/python -m pytest tests/unit/test_xxx.py -q
    assumptions:
      - 暂不改动前端路由契约
```
````

## 6) 承接契约（v1 兼容）

```yaml
clarify_handoff_contract:
  version: v1
  requirement_seeds: [...]
  implementation_seeds: [...]
  execution_chain_seed: {...}
```

## 7) 自然审批提示模板

```markdown
以上设计已完全冻结。  
请回复：**确认 / 需要修改XX点 / 否**  
（回复“确认”或“是”且门禁全部通过即视为审批通过，可进入 /jjk-plan；否则记录条件采纳并继续澄清）
```

## 8) 审批记录模板

```markdown
## 8. 审批记录
- design_approved: true|false
- approved_at: <YYYY-MM-DD HH:mm>
- approved_round: <round-or-version>
- approval_evidence: <用户明确确认原话>
- approval_mode: approved|conditional|rejected
- go_no_go: GO|NO_GO
- blocking_issues: []
```

## 9) 一致性自检模板（建议强制）

````markdown
## 9. 一致性自检（机读）
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
````
