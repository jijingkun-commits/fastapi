### 1) 测试摘要
- task_id: `na`
- pr_id: `na`
- feature_scope: `P1-01,P1-02,P1-03,P1-04,P2-01`
- execution_mode: `single`
- python_interpreter: `/Users/jijingkun/bojxAI/fastapi/venv/bin/python`
- summary: `PASS`
- markers: `none`

### 2) Risk Model
| risk_id | risk_area | trigger_change | expected_failure | priority | covered_by |
|---|---|---|---|---|---|
| `R-01` | `state` | `todo.query` observation gate 收紧后补动作推断 | 合法的“结合外部结果回复”场景被误杀，`pending_handoff.frame` 缺失 | `P0` | `TC-01,TC-02` |
| `R-02` | `boundary` | goal resolver 原子化与 handoff 规范化 | 多意图 goal 被错误合并，或路由边界回退到 bucket 级猜测 | `P0` | `TC-03,TC-04` |
| `R-03` | `partial_failure` | coverage / deliverable 收口重构 | goal 未完成却被误判为 `success`，最终答复错误宣称“已全部覆盖” | `P0` | `TC-03` |
| `R-04` | `external_dependency` | Tavily / direct lookup 结果进入 multi-intent 汇总 | 外部噪声污染 todo/data handoff 或知识库/天气相互吞没 | `P1` | `TC-01,TC-03` |
| `R-05` | `api` | SSE goal status / final answer 协议收口 | API 事件序列缺字段、错顺序，导致前端链路与单元测试口径不一致 | `P1` | `TC-04` |

### 3) 测试矩阵
| case_id | level | command_or_case | covers_risk | failure_mode | result | evidence |
|---|---|---|---|---|---|---|
| `TC-01` | `unit` | `bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py -k 'direct_lookup_plus_single_handoff' -q` | `R-01,R-04` | `boundary` | `PASS` | 单点失败用例转绿；`tool_observations` 恢复进入 `pending_handoff.frame` |
| `TC-02` | `unit` | `bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py -q` | `R-01` | `happy_path` | `PASS` | `streaming_helpers` 整文件通过，说明修复未破坏同模块其余路径 |
| `TC-03` | `unit+integration` | `python -m pytest -q app/tests/test_handoff_detection.py tests/unit/test_multi_intent_queue_flow.py tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_todo_handoff_observation.py tests/unit/test_router_ignores_intent_plan_runtime.py tests/unit/test_multi_intent_coverage_reconcile.py tests/unit/test_delivery_contract_validators.py tests/unit/test_intent_layer_boundary.py tests/unit/test_intent_plan_model_primary.py tests/unit/test_chat_service_done_payload.py tests/unit/test_multi_agent_skill_workflow.py tests/unit/test_data_graph_pending_handoff_state.py tests/unit/test_data_graph_clarify_guard.py` | `R-01,R-02,R-03,R-04` | `happy_path,partial_failure,boundary` | `PASS` | `170 passed`，coverage `40.30%` |
| `TC-04` | `api+integration` | `python -m pytest -q app/tests/test_handoff_detection.py tests/unit/test_multi_intent_queue_flow.py tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_todo_handoff_observation.py tests/unit/test_router_ignores_intent_plan_runtime.py tests/unit/test_multi_intent_coverage_reconcile.py tests/unit/test_delivery_contract_validators.py tests/unit/test_intent_layer_boundary.py tests/unit/test_intent_plan_model_primary.py tests/unit/test_chat_service_done_payload.py tests/unit/test_multi_agent_skill_workflow.py tests/unit/test_data_graph_pending_handoff_state.py tests/unit/test_data_graph_clarify_guard.py tests/api/test_chat_sse_intent_goal_status.py tests/integration/test_intent_shadow_metrics.py` | `R-01,R-02,R-03,R-04,R-05` | `happy_path,boundary,partial_failure` | `PASS` | `178 passed`，coverage `40.76%` |

### 4) Test Quality Review
- risk_model_complete: `yes`
- failure_modes_covered: `充分`
- assertion_quality: `高`，说明：`本轮断言覆盖 goal 归属、handoff frame、tool_observations、deliverable/coverage 与 SSE goal status，不是只看 200 或 not None`
- coupling_risk: `中`，说明：`部分单测仍直接断言编排层内部字段（如 pending_handoff.frame），对实现细节有一定耦合，但这些字段正是本次 contract 的核心`
- low_value_tests:
  - `none`
- score_summary:
  - 风险覆盖: `2`
  - 失败模式覆盖: `2`
  - 断言质量: `2`
  - 脆弱性: `1`
  - 可维护性: `2`
- quality_decision: `PASS`

### 5) 缺陷与分类
- new_issues:
  - `none`
- historical_issues:
  - `单独执行 tests/api/test_chat_sse_intent_goal_status.py + tests/integration/test_intent_shadow_metrics.py 时，测试本身通过，但因选择范围过窄触发 coverage 阈值失败（29.86%）；并入完整相关矩阵后恢复为 PASS，不属于功能缺陷`

### 6) Gate 与回填
- gate_backfill_run: `na`
- gate_backfill_result: `na`
- doc_sync_check: `PASS`

### 7) 资产沉淀
- report_path: `docs/开发文档/测试管理/测试报告/多意图编排测试报告_2026-03-12_todo_observation_gate回归.md`
- cases_updated: `no`
- trace_lib_updated: `no`
- summary_index_updated: `no`

### 8) 下一步
1. 进入 `/jjk-verify` 前，还缺本主题既有 `uat_cases` 证据；若要做正式验收，需要先确认是否存在对应 UAT 真理源。
2. 若只看本轮代码与相关验证，技术上已可进入 `commit/PR` 收口。
