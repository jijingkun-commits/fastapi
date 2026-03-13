# WS-C02 C02 P1 fallback触发网关与规则兜底收敛

> WS 编号: WS-C02  
> 对应卡片: `C02`  
> 类型: `parallel`  
> 对应 feature_id: `P1-03`

## 0. 关联与来源

- 对应 `task_key`: `PP-20260228-INTENT-DECOMPOSITION-DB`
- 来源主计划: `workdocs/归档/实施计划/意图目标分解治理_implementation_plan.md`
- 来源并行计划: `workdocs/任务拆解/2026-02-28_意图目标分解治理/parallel_plan.md`

## 1. 目标

- 本包目标:
- 规则兜底仅在模型失败、超时、输出非法时触发
- fallback_meta 必须写入可观测原因并绑定规则触发信息
- 禁止关键词路径漂移为主路径
- 完成定义（DoD）:
- fallback gate enabled and explainable

### 1.1 功能机制（必填）

- 触发条件: 前置依赖 `C01` 已完成并满足 done gate
- 输入: `intent_plan`、`planning_contract`、上游运行证据
- 输出: 对应卡片 DoD 证据、可回滚锚点、门禁结论
- 状态流转（含异常分支）: `Backlog -> Doing -> Review -> Gate -> Done`；失败时写入 `blocked` 并触发回滚锚点
- 与上/下游 WS 的契约关系: 上游满足 `depends_on` 才解锁；下游只消费本包 evidence

### 1.2 代码锚点与样例（必填）

- 代码锚点（函数/类级）:
- `app/ai/workflow/multi_agent_graph.py::_build_planner_intent_plan`
- `app/ai/workflow/multi_agent_graph.py::_infer_initial_intent_plan`
- 最小样例（可伪代码）:

```python
if dependencies_ready and checks_passed:
    promote_card("Done")
else:
    emit_blocked_reason()
```

- 来源证据（output/专题文档）:
  - `workdocs/归档/实施计划/意图目标分解治理_implementation_plan.md`

## 2. 文件边界

### 可修改（白名单）
- `app/ai/workflow/multi_agent_graph.py`
- `tests/unit/test_intent_fallback_gate.py`

### 禁止修改（黑名单）
- `workdocs/归档/实施计划/openclaw迁移重建基线_implementation_plan.md`

## 3. 状态与契约

- 可写字段: `card.status`、`evidence_entry`、`gate_result`
- 只读字段: `card_id`、`feature_ids`、`depends_on`
- 外部契约: `planning_contract` 与 `vk_cards.json` 保持一致

## 4. 实施步骤

1. 读取本卡前置依赖与 done gate。
2. 执行 `acceptance_checks` 并记录结果。
3. 回填 `evidence_entry` 与回滚锚点验证。

### 4.1 串行门禁（serial 模式必填）

- 前置卡: `C01`
- 解锁条件: `depends_on` 对应卡片全部通过
- 本 WS 不得推进条件: 任一 `acceptance_checks` 失败

## 5. 测试与验收

- 最小测试集:
- `cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest -q tests/unit/test_intent_fallback_gate.py`
- 验收标准:
- fallback gate enabled and explainable

### 5.0 验收门禁映射（必填）

- 对应 implementation plan `done_gate`: `fallback gate enabled and explainable`
- 本 WS 负责的门禁子项: `C02:P1-03`
- 证据回填位置（文档节）: `workdocs/归档/实施计划/意图目标分解治理_implementation_plan.md#11`

## 6. 风险与回滚

- 主要风险: 依赖卡未完成导致串行断链，或门禁证据不一致。
- 回滚点:
- `ENABLE_INTENT_FALLBACK_GATE=false`
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
  id: WS-C02
  feature_id: P1-03
  card_key: PP-20260228-INTENT-DECOMPOSITION-DB::WS-C02
  title: C02 P1 fallback触发网关与规则兜底收敛
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  lane: lane-backend-intent
  hard_depends_on: ["C01"]
  soft_depends_on: []
  depends_on: ["C01"]
  file_whitelist: ["app/ai/workflow/multi_agent_graph.py", "tests/unit/test_intent_fallback_gate.py"]
  readonly_scope: []
  owner_fields: []
  mechanism_summary: ["规则兜底仅在模型失败、超时、输出非法时触发", "fallback_meta 必须写入可观测原因并绑定规则触发信息", "禁止关键词路径漂移为主路径"]
  code_anchor_refs: ["app/ai/workflow/multi_agent_graph.py::_build_planner_intent_plan", "app/ai/workflow/multi_agent_graph.py::_infer_initial_intent_plan"]
  example_refs: ["workdocs/归档/实施计划/意图目标分解治理_implementation_plan.md#4.3"]
  acceptance_checks: ["cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest -q tests/unit/test_intent_fallback_gate.py"]
  rollback_anchors: ["ENABLE_INTENT_FALLBACK_GATE=false"]
  evidence_entry: workdocs/归档/实施计划/意图目标分解治理_implementation_plan.md#11
  check_cmd: ["cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest -q tests/unit/test_intent_fallback_gate.py"]
  handoff_artifacts:
    - workdocs/任务拆解/2026-02-28_意图目标分解治理/contracts/sse_events_v1.json
  done_gate: ["fallback gate enabled and explainable"]
```
