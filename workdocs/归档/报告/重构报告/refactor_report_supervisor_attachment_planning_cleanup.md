# refactor_report_supervisor_attachment_planning_cleanup

## 1. 输入映射
- task_id/card_id/pr_id: none
- worktree: `/Users/jijingkun/.codex/worktrees/011a/fastapi`
- branch: `codex/subagent1`
- topic: `supervisor attachment planning cleanup`

## 2. 重构切片与改动清单
- 抽离附件 planning 纯函数到 `app/ai/workflow/attachment_planning.py`
- `app/services/chat_service.py` 删除一次性包装 helper，直接产出结构化附件合同
- `app/ai/workflow/multi_agent_graph.py` 删除 `_build_attachment_planning_payload`，在 preprocess 内直接消费纯合同函数
- `tests/unit/test_multi_agent_streaming_helpers.py` 改为直接验证 `build_attachment_planning_contract`
- 删除死代码：`app/ai/tools/ragflow_tool.py`、`app/ai/workflow/data_graph.py`、`app/ai/workflow/todo_graph.py` 中各 1 个未使用函数
- `app/ai/protocol.py` 收口重复归一化 helper，统一 snapshot / expert_input / research payload 构造
- `app/ai/tools/chatTools.py` 收口 web_research task_id、执行上下文与错误截断逻辑，减少工具层重复壳
- `app/ai/workflow/todo_intent_helpers.py` 删除无用 import，复用 todo handoff message 投影逻辑，压缩 task_desc 字段提取重复
- `app/ai/workflow/multi_agent_graph.py` 删除死 helper，收口 dispatch queue 的 query fallback 逻辑，减少 router / handoff 可见性判断中的重复分支
- `app/ai/workflow/multi_agent_graph.py` 删除热点文件中重复的架构说明/步骤性注释/调试噪音，代码内只保留必要语义，真理源回收到 `docs/`
- `app/ai/state.py` / `app/ai/protocol.py` 删除重复说明性 docstring 与步骤性注释，保留 contract 本身，不改状态/协议语义

## 3. 行为等价验证证据
- `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/repo_python.sh`
- `py_compile` 通过：`app/services/chat_service.py`、`app/ai/workflow/multi_agent_graph.py`、`app/ai/workflow/attachment_planning.py`、`app/ai/tools/ragflow_tool.py`、`app/ai/workflow/data_graph.py`、`app/ai/workflow/todo_graph.py`、`tests/unit/test_multi_agent_streaming_helpers.py`
- `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_todo_handoff_observation.py tests/unit/test_data_graph_pending_handoff_state.py tests/unit/test_ragflow_tool.py tests/unit/test_research_dispatch_contract.py -q`
- `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_chat_tools_streaming_payload.py tests/unit/test_research_dispatch_contract.py tests/unit/test_todo_handoff_observation.py tests/unit/test_todo_nodes.py app/tests/test_concurrency_tools.py -q`
- 回归结果：通过

## 4. 待处理项与风险
- 总体代码仍较 `master` 净增长，主要来自新状态合同、协议载荷与测试补位，不是这两轮深清新增的包装层
- 继续瘦身后，整体净增从 `1283` 继续降到 `1056`；单看代码净增已从 `648` 继续降到 `415`
- `scripts/ci/check_lean_budget.py --strict` 对当前 unstaged 变更未命中热点，需要以最终提交形态再做一次门禁验证

## 5. 下一步命令建议
- `$jjk-review`
- `$jjk-verify`
