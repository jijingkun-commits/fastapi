# 调试报告：todo.query observation gate 误杀合法组合查询

## 1. 问题现象与影响范围

- 现象：复合请求“查待办并看天气”进入 `multi_intent_mode` 后，Supervisor 已产出 `tavily_search` 结果和 `todo_expert` handoff，但 `pending_handoff.frame` 缺失，导致合法 observation 没有传给 todo 子任务。
- 影响：`tests/unit/test_multi_agent_streaming_helpers.py::test_dispatch_values_mode_chunk_marks_multi_intent_for_direct_lookup_plus_single_handoff` 失败；用户会看到“待办查询”和“天气结果”脱节，无法实现“结合天气结果回复用户”。
- 影响范围：`app/ai/intent/goal_resolver.py` 的 todo observation 判定，以及依赖该判定的 `app/ai/workflow/multi_agent_graph.py::_augment_todo_handoff_with_observations`。

## 2. 根因证据链

- 根因：`should_attach_todo_observations()` 只信任显式 `frame.todo_action`；当 handoff 只有 `task_description="查询待办并结合天气结果回复用户"`、但没有 `frame.todo_action` 时，会把动作判成空字符串，直接返回 `False`。
- 证据：
  - 失败测试显示 `pending_handoff["frame"]` 缺失，最终报 `KeyError: 'frame'`。
  - 同一逻辑对简单 `task_description="查询待办"` 的 case 是对的，因为这类 query 不该被天气 observation 污染。
- 排除假设：不是 `tavily_search` 提取失败，也不是 handoff 路由错发；失败 case 里 `target_agent="todo_expert"` 与 `multi_intent_mode=True` 都已成立。

## 3. 修复内容

- 文件：`app/ai/intent/goal_resolver.py`
- 符号：`should_attach_todo_observations()`
- 变更：
  - 当 `todo_action` 为空时，先按 `has_todo_target -> update` 兜底。
  - 若 `task_description` 或 `user_text` 明显是待办域请求，再条件式推断 `query/create`。
  - 真正放行 observation 的门仍保持不变：`todo.query` 必须同时满足“有外部上下文 + 有 combine hint”。
- 结果：简单查询待办继续不带 observation；只有“查询待办并结合天气结果回复用户”这类明确组合场景才附带结构化 `tool_observations`。

## 4. 验证命令与结果

- 解释器解析：
  - `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/repo_python.sh`
  - 结果：`/Users/jijingkun/bojxAI/fastapi/venv/bin/python`
- 最小复现回归：
  - `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py -k 'direct_lookup_plus_single_handoff' -q`
  - 结果：`1 passed`
- 扩大到 streaming helper 文件：
  - `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py -q`
  - 结果：整文件通过
- 6 文件大回归：
  - `/Users/jijingkun/bojxAI/fastapi/venv/bin/python -m pytest -q tests/unit/test_multi_intent_queue_flow.py app/tests/test_handoff_detection.py tests/unit/test_intent_plan_model_primary.py tests/unit/test_chat_service_done_payload.py tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_multi_agent_skill_workflow.py`
  - 结果：`124 passed`，总 coverage `38.36%`
- 额外门禁：
  - `git diff --check`：通过
  - `python3 scripts/ci/check_lean_budget.py --diff-range HEAD --strict`：`未命中 Lean Guard 热点目录，跳过检查`

## 5. 风险、回滚点与后续建议

- 风险：
  - 当前动作推断仍是轻量规则，未来若 handoff 描述进一步收缩，可能需要把 todo action 显式编译进 handoff contract，而不是继续依赖文本推断。
- 回滚点：
  - 回滚文件：`app/ai/intent/goal_resolver.py`
  - 回滚后，最小复现测试会重新失败，能直接暴露问题。
- 后续建议：
  - 下一轮若继续收敛多意图 handoff，建议把 `todo.query` 的 `frame.todo_action` 也纳入 canonical handoff contract，减少后续文本推断分支。
