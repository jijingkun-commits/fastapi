# agent-intent-anti-false-trigger 需求文档（v1）

## 1. 需求范围与目标

- 以 `router_result_v2.route_decisions[].data_intent` 作为 data 场景运行态唯一语义 contract。
- DataIntentContract 只允许挂到 `route_decisions[].data_intent`，不新增 `router_result_v3`。
- `clarify` 输出结构化 `clarify_contract`；`llm-shadow` 仅允许异步旁路。
- 指标真理源是 `t_metric_definition`；列/维度/数据类型真理源是 `t_meta_columns`。

## 2. requirements_contract

```yaml
requirements_contract:
  version: v1
  status: approved
  design_source: workdocs/归档/正文/设计/2026-03-09-agent-intent-anti-false-trigger-design.md
  design_approved: true
  clarify_handoff_source: workdocs/归档/正文/设计/2026-03-09-agent-intent-anti-false-trigger-design.md
  clarify_handoff_version: v2
  design_approval_evidence: approved_design_and_hydrated_tasks
  design_freeze_summary:
    design_actionable: true
    missing_blocks: []
    blocked_by: []
    risk_level: medium
    risk_counterexamples_count: 2
    product_contract_ready: true
```

## 3. traceability_matrix

```yaml
traceability_matrix:
  - task_id: T01
    task_summary: 建立 DataIntentContract 与 Router 单一契约源
    acceptance_cmd_ref: cmd: bash scripts/pytest_targeted.sh tests/unit/test_data_intent_router_contract.py -q
  - task_id: T02
    task_summary: Resolver/Guardrail 收口时间、维度、列语义与安全边界
    acceptance_cmd_ref: cmd: bash scripts/pytest_targeted.sh tests/unit/test_data_intent_resolver_guardrails.py -q
  - task_id: T03
    task_summary: workflow 去单关键词直触发与补充轮接线
    acceptance_cmd_ref: cmd: bash scripts/pytest_targeted.sh tests/unit/test_data_intent_router_negative_cases.py -q
  - task_id: T04
    task_summary: router_result_v2 内嵌 DataIntentContract 与 replay 收敛
    acceptance_cmd_ref: cmd: bash scripts/pytest_targeted.sh tests/unit/test_router_result_v2_replay.py -q
  - task_id: T05
    task_summary: 路由误触发/补充轮/影子对账回归矩阵
    acceptance_cmd_ref: cmd: bash scripts/pytest_targeted.sh tests/unit/test_data_intent_router_shadow_compare.py -q
  - task_id: T06
    task_summary: clarify_contract 与真理源回归
    acceptance_cmd_ref: cmd: bash scripts/pytest_targeted.sh tests/unit/test_data_intent_clarify_contract.py -q
  - task_id: T07
    task_summary: 文档同步与规划门禁收口
    acceptance_cmd_ref: cmd: PYTHON_BIN="$(bash scripts/repo_python.sh)" && "$PYTHON_BIN" scripts/docs_guard.py --strict
```
