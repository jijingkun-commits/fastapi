# 工作包说明

> WS 编号: WS-C05
> 名称: P5 稳态增强与插件后置接线
> 类型: parallel
> 对应 feature_id: P5-01

## 0. 关联与来源

- 对应 task_key: PP-20260221-OPENCLAW-REBUILD-BASELINE
- 对应 card_id: C05
- 来源主计划: `docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md`
- 来源并行计划: `workdocs/任务拆解/2026-02-21_openclaw迁移重建基线/parallel_plan.md`

## 1. 目标

- 本包目标: P5 稳态增强与插件后置接线 的可执行落地。
- 完成定义（DoD）:
  - 恢复任务、观测阈值、降级策略验收通过
  - 多用户并发流式场景下恢复与降级互不干扰
  - 插件后置接线不阻塞主链

### 1.1 功能机制

  - 恢复/隔离/观测增强与异常降级
  - 插件能力后置接线，不阻塞主链
  - fallback、队列与子任务稳定化

### 1.2 代码锚点

  - app/ai/workflow/multi_agent_graph.py::_build_supervisor_fallback_handoff
  - app/ai/workflow/multi_agent_graph.py::_execute_streaming_wrapper
  - app/ai/state.py::MultiAgentState
  - app/services/chat_service.py::sse_stream

- 本卡新增实体目标（C05 实现阶段创建）:
  - app/ai/workflow/multi_agent_graph.py（fallback_router）
  - app/ai/state.py（runtime_recovery_state）
  - app/services/chat_service.py（degrade_on_plugin_failure）

- 来源证据:
  - docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md#4.10

## 2. 文件边界

### 可修改（白名单）
  - app/ai/workflow/multi_agent_graph.py
  - app/ai/state.py
  - app/services/chat_service.py
  - tests/unit/test_multi_agent_streaming_helpers.py

### 禁止修改（黑名单）
- 其他 card_id 对应白名单外文件

## 3. 串行门禁

- 前置卡: C02, C04
- 解锁条件: 前置卡 `done_gate` 全部通过
- 本 WS 不得推进条件: 前置卡存在 `TODO/IN_PROGRESS/BLOCKED`

## 4. 测试与验收

- 验收命令:
  - PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py -k fallback

## 5. 风险与回滚

- 回滚锚点:
  - ENABLE_RUNTIME_RECOVERY
  - ENABLE_PLUGIN_REGISTRY

## 6. card_export

```yaml
card_export:
  id: WS-C05
  card_id: C05
  feature_ids: [P5-01]
  card_key: PP-20260221-OPENCLAW-REBUILD-BASELINE::WS-C05
  title: P5 稳态增强与插件后置接线
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  hard_depends_on: [C02, C04]
  depends_on: [C02, C04]
  file_whitelist:
  - app/ai/workflow/multi_agent_graph.py
  - app/ai/state.py
  - app/services/chat_service.py
  - tests/unit/test_multi_agent_streaming_helpers.py
  mechanism_summary:
  - 恢复/隔离/观测增强与异常降级
  - 插件能力后置接线，不阻塞主链
  - fallback、队列与子任务稳定化
  code_anchor_refs:
  - app/ai/workflow/multi_agent_graph.py::_build_supervisor_fallback_handoff
  - app/ai/workflow/multi_agent_graph.py::_execute_streaming_wrapper
  - app/ai/state.py::MultiAgentState
  - app/services/chat_service.py::sse_stream
  acceptance_checks:
  - PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py -k fallback
  rollback_anchors:
  - ENABLE_RUNTIME_RECOVERY
  - ENABLE_PLUGIN_REGISTRY
  evidence_entry: docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md#4.10
  done_gate:
  - 恢复任务、观测阈值、降级策略验收通过
  - 多用户并发流式场景下恢复与降级互不干扰
  - 插件后置接线不阻塞主链
```
