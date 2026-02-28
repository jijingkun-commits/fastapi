# WS-C07 C07 P2 json_object与text_parse降级链路

> WS 编号: WS-C07  
> 对应卡片: `C07`  
> 类型: `parallel`  
> 对应 feature_id: `P2-03, P2-04`

## 0. 关联与来源

- 对应 `task_key`: `PP-20260228-INTENT-DECOMPOSITION-DB`
- 来源主计划: `docs/内部参考/迭代需求/意图目标分解治理_implementation_plan.md`
- 来源并行计划: `docs/内部参考/任务拆解/2026-02-28_意图目标分解治理/parallel_plan.md`

## 1. 目标

- 本包目标:
- tool_call 不可用或失败时自动进入 json_object 路径
- json_object 失败继续进入 text_parse + schema 校验
- 分级降级链路保持主对话不中断
- 完成定义（DoD）:
- json_object fallback pass
- text_parse fallback pass

### 1.1 功能机制（必填）

- 触发条件: 前置依赖 `C06` 已完成并满足 done gate
- 输入: `intent_plan`、`planning_contract`、上游运行证据
- 输出: 对应卡片 DoD 证据、可回滚锚点、门禁结论
- 状态流转（含异常分支）: `Backlog -> Doing -> Review -> Gate -> Done`；失败时写入 `blocked` 并触发回滚锚点
- 与上/下游 WS 的契约关系: 上游满足 `depends_on` 才解锁；下游只消费本包 evidence

### 1.2 代码锚点与样例（必填）

- 代码锚点（函数/类级）:
- `app/ai/workflow/multi_agent_graph.py::_infer_model_intent_plan_via_json_object`
- `app/ai/workflow/multi_agent_graph.py::_infer_model_intent_plan_via_text_parse`
- `app/ai/workflow/multi_agent_graph.py::_IntentPlanModel`
- 最小样例（可伪代码）:

```python
if dependencies_ready and checks_passed:
    promote_card("Done")
else:
    emit_blocked_reason()
```

- 来源证据（output/专题文档）:
  - `docs/内部参考/迭代需求/意图目标分解治理_implementation_plan.md`

## 2. 文件边界

### 可修改（白名单）
- `app/ai/workflow/multi_agent_graph.py`
- `tests/unit/test_planner_json_object_fallback.py`
- `tests/unit/test_planner_text_parse_fallback.py`

### 禁止修改（黑名单）
- `docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md`

## 3. 状态与契约

- 可写字段: `card.status`、`evidence_entry`、`gate_result`
- 只读字段: `card_id`、`feature_ids`、`depends_on`
- 外部契约: `planning_contract` 与 `vk_cards.json` 保持一致

## 4. 实施步骤

1. 读取本卡前置依赖与 done gate。
2. 执行 `acceptance_checks` 并记录结果。
3. 回填 `evidence_entry` 与回滚锚点验证。

### 4.1 串行门禁（serial 模式必填）

- 前置卡: `C06`
- 解锁条件: `depends_on` 对应卡片全部通过
- 本 WS 不得推进条件: 任一 `acceptance_checks` 失败

## 5. 测试与验收

- 最小测试集:
- `cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest -q tests/unit/test_planner_json_object_fallback.py`
- `cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest -q tests/unit/test_planner_text_parse_fallback.py`
- 验收标准:
- json_object fallback pass
- text_parse fallback pass

### 5.0 验收门禁映射（必填）

- 对应 implementation plan `done_gate`: `json_object fallback pass; text_parse fallback pass`
- 本 WS 负责的门禁子项: `C07:P2-03, P2-04`
- 证据回填位置（文档节）: `docs/内部参考/迭代需求/意图目标分解治理_implementation_plan.md#12.4`

## 6. 风险与回滚

- 主要风险: 依赖卡未完成导致串行断链，或门禁证据不一致。
- 回滚点:
- `PLANNER_DISABLE_JSON_OBJECT=true`
- `PLANNER_DISABLE_TEXT_PARSE=true`
- 回滚开关/策略: 按 `rollback_anchors` 单卡回退，不跨卡混退。

## 7. 协作者自检卡（提交必填）

- 实际修改文件列表: 见 file whitelist
- 是否修改了白名单外文件（是/否）: 否
- 测试命令与结果: 见 acceptance_checks
- 已知风险点: 依赖链顺序错配
- 回滚建议: 先回滚本卡，再评估上游卡
- 证据绑定检查（target_task_id == evidence_task_id）: 必填

## 8. card_export（机读，必填）

```yaml
card_export:
  id: WS-C07
  feature_id: P2-03,P2-04
  card_key: PP-20260228-INTENT-DECOMPOSITION-DB::WS-C07
  title: C07 P2 json_object与text_parse降级链路
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  lane: lane-backend-compat
  hard_depends_on: ["C06"]
  soft_depends_on: []
  depends_on: ["C06"]
  file_whitelist: ["app/ai/workflow/multi_agent_graph.py", "tests/unit/test_planner_json_object_fallback.py", "tests/unit/test_planner_text_parse_fallback.py"]
  readonly_scope: []
  owner_fields: []
  mechanism_summary: ["tool_call 不可用或失败时自动进入 json_object 路径", "json_object 失败继续进入 text_parse + schema 校验", "分级降级链路保持主对话不中断"]
  code_anchor_refs: ["app/ai/workflow/multi_agent_graph.py::_infer_model_intent_plan_via_json_object", "app/ai/workflow/multi_agent_graph.py::_infer_model_intent_plan_via_text_parse", "app/ai/workflow/multi_agent_graph.py::_IntentPlanModel"]
  example_refs: ["docs/内部参考/迭代需求/意图目标分解治理_implementation_plan.md#12.1", "docs/内部参考/迭代需求/意图目标分解治理_implementation_plan.md#12.2"]
  acceptance_checks: ["cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest -q tests/unit/test_planner_json_object_fallback.py", "cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest -q tests/unit/test_planner_text_parse_fallback.py"]
  rollback_anchors: ["PLANNER_DISABLE_JSON_OBJECT=true", "PLANNER_DISABLE_TEXT_PARSE=true"]
  evidence_entry: docs/内部参考/迭代需求/意图目标分解治理_implementation_plan.md#12.4
  check_cmd: ["cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest -q tests/unit/test_planner_json_object_fallback.py", "cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest -q tests/unit/test_planner_text_parse_fallback.py"]
  handoff_artifacts:
    - docs/内部参考/任务拆解/2026-02-28_意图目标分解治理/contracts/sse_events_v1.json
  done_gate: ["json_object fallback pass", "text_parse fallback pass"]
```
