# 工作包说明

> WS 编号: WS-C01
> 名称: P1 运行时可取消控制
> 类型: parallel
> 对应 feature_id: P1-01, P1-02, P1-03, P1-04, P1-05

## 0. 关联与来源

- 对应 task_key: PP-20260221-OPENCLAW-REBUILD-BASELINE
- 对应 card_id: C01
- 来源主计划: `docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md`
- 来源并行计划: `workdocs/任务拆解/2026-02-21_openclaw迁移重建基线/parallel_plan.md`

## 1. 目标

- 本包目标: P1 运行时可取消控制 的可执行落地。
- 完成定义（DoD）:
  - P1-01~P1-05 验收命令全部通过
  - cancel_after_token_count=0
  - 多用户并发取消隔离回归通过（A 用户取消不影响 B 用户）
  - `done/stopped/interrupt` 终态互斥与顺序语义回归通过
  - ENABLE_RUN_CONTROL 与 ENABLE_SSE_STOPPED_EVENT 回滚验证通过

### 1.1 功能机制

  - run 状态模型、取消控制面与 run_id 全链路接线
  - 取消后阻断 token 回灌并 drain 队列
  - 统一 cancel API 并新增 SSE stopped 兼容事件
  - 补齐 active_run 恢复与 orphan 清理

### 1.2 代码锚点

  - app/services/chat_service.py::stream
  - app/services/chat_service.py::sse_stream
  - app/services/chat_service.py::sse_resume_stream
  - app/api/v1/endpoints/chat_api.py::chat_stream
  - app/api/v1/endpoints/chat_api.py::resume_stream
  - app/ai/workflow/multi_agent_graph.py::_execute_streaming_wrapper
  - app/ai/events.py::EventType
  - app/schemas/chat.py::ChatRequest

- 本卡新增实体目标（C01 实现阶段创建）:
  - app/models/chat_run.py（ChatRun）
  - app/services/run_control_service.py（RunControlService）
  - app/api/v1/endpoints/chat_api.py（cancel_run）
  - app/ai/events.py（stopped_event）
  - app/schemas/chat.py（run_id）

- 来源证据:
  - docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md#4.2

## 2. 文件边界

### 可修改（白名单）
  - app/models/chat_run.py
  - app/services/run_control_service.py
  - app/services/chat_service.py
  - app/api/v1/endpoints/chat_api.py
  - app/ai/workflow/multi_agent_graph.py
  - app/ai/events.py
  - app/schemas/chat.py
  - tests/api/test_chat_api.py
  - tests/unit/test_run_control_service.py
  - tests/unit/test_chat_service_cancel_stream.py
  - tests/unit/test_chat_service_resume_after_cancel.py

### 禁止修改（黑名单）
- 其他 card_id 对应白名单外文件

## 3. 串行门禁

- 前置卡: 无
- 解锁条件: 前置卡 `done_gate` 全部通过
- 本 WS 不得推进条件: 前置卡存在 `TODO/IN_PROGRESS/BLOCKED`

## 4. 测试与验收

- 先决要求:
  - 若测试文件不存在，先补测试骨架并提交红灯用例，再进入功能实现
- 验收命令:
  - PYTHONPATH=. pytest tests/unit/test_run_control_service.py
  - PYTHONPATH=. pytest tests/unit/test_chat_service_cancel_stream.py
  - PYTHONPATH=. pytest tests/unit/test_chat_service_resume_after_cancel.py
  - PYTHONPATH=. pytest tests/api/test_chat_api.py -k cancel

## 5. 风险与回滚

- 回滚锚点:
  - ENABLE_RUN_CONTROL
  - ENABLE_SSE_STOPPED_EVENT

## 6. card_export

```yaml
card_export:
  id: WS-C01
  card_id: C01
  feature_ids: [P1-01, P1-02, P1-03, P1-04, P1-05]
  card_key: PP-20260221-OPENCLAW-REBUILD-BASELINE::WS-C01
  title: P1 运行时可取消控制
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  hard_depends_on: []
  depends_on: []
  file_whitelist:
  - app/models/chat_run.py
  - app/services/run_control_service.py
  - app/services/chat_service.py
  - app/api/v1/endpoints/chat_api.py
  - app/ai/workflow/multi_agent_graph.py
  - app/ai/events.py
  - app/schemas/chat.py
  - tests/api/test_chat_api.py
  - tests/unit/test_run_control_service.py
  - tests/unit/test_chat_service_cancel_stream.py
  - tests/unit/test_chat_service_resume_after_cancel.py
  mechanism_summary:
  - run 状态模型、取消控制面与 run_id 全链路接线
  - 取消后阻断 token 回灌并 drain 队列
  - 统一 cancel API 并新增 SSE stopped 兼容事件
  - 补齐 active_run 恢复与 orphan 清理
  code_anchor_refs:
  - app/services/chat_service.py::stream
  - app/services/chat_service.py::sse_stream
  - app/services/chat_service.py::sse_resume_stream
  - app/api/v1/endpoints/chat_api.py::chat_stream
  - app/api/v1/endpoints/chat_api.py::resume_stream
  - app/ai/workflow/multi_agent_graph.py::_execute_streaming_wrapper
  - app/ai/events.py::EventType
  - app/schemas/chat.py::ChatRequest
  acceptance_checks:
  - PYTHONPATH=. pytest tests/unit/test_run_control_service.py
  - PYTHONPATH=. pytest tests/unit/test_chat_service_cancel_stream.py
  - PYTHONPATH=. pytest tests/unit/test_chat_service_resume_after_cancel.py
  - PYTHONPATH=. pytest tests/api/test_chat_api.py -k cancel
  rollback_anchors:
  - ENABLE_RUN_CONTROL
  - ENABLE_SSE_STOPPED_EVENT
  evidence_entry: docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md#4.2
  done_gate:
  - P1-01~P1-05 验收命令全部通过
  - cancel_after_token_count=0
  - 多用户并发取消隔离回归通过
  - done/stopped/interrupt 终态互斥与顺序语义回归通过
  - ENABLE_RUN_CONTROL 与 ENABLE_SSE_STOPPED_EVENT 回滚验证通过
```
