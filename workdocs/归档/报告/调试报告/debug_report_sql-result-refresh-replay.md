# debug_report_sql-result-refresh-replay

## 1. 问题现象与影响范围
- 现象：同一轮复合问答中，实时流能展示 `sql_result` 图表/表格；刷新页面后图表消失。
- 影响范围：多意图/最终汇总场景下，数据查询结果仅存在于实时 SSE 事件，不稳定落库到最终 AI 消息。
- 用户影响：刷新、重新进入线程、历史回放时看不到图表/表格，只能看到最终摘要文本。

## 2. 根因证据链
- 现象证据：用户反馈“刷新后数据查询图表没有了”，并确认数据库里对应表格/图表数据确实不在。
- 代码证据 1：`app/ai/workflow/multi_agent_graph.py` 的 `final_composer` 最终只生成带 `skill_runtime` 的最后一条 AI 消息，不携带本轮已有的 `sql_result` 结构化结果。
- 代码证据 2：`app/repositories/chat_repo.py` 的 `save_conversation_from_messages()` 只保存“最后一条 AI 消息”的 `additional_kwargs`。
- 结果：当 `sql_result` 出现在较早的 AI 消息、最终总结消息不带结构化结果时，落库 `extra_data` 不含 `data_type/data/result_events`，刷新回放必然丢失。
- 已排除假设：前端刷新渲染器本身缺陷。前端已支持从 `additional_kwargs.result_events/result_event/data_type+data` 回放；真正缺的是后端持久化真值。

## 3. 修复内容
- 修复文件：`app/repositories/chat_repo.py`
- 修复策略：在持久化边界归并“当前轮所有 AI 消息中的结构化结果”，统一收敛到最终落库 AI 消息的 `additional_kwargs.result_events`。
- 关键变更：
  - 新增 result_event 去重键生成逻辑；
  - 新增“当前轮 AI 消息结构化结果归并”逻辑；
  - `save_conversation_from_messages()` 落库前不再只拿最后一条 AI 的裸 `additional_kwargs`，而是保存归并后的 canonical 结果。
- 变更原则：只修状态归属与持久化真值，不改前端 renderer，不新增兼容层。

## 4. 验证命令与结果
- RED：
  - `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh tests/unit/test_chat_repo_serialization.py -q`
  - 结果：新增回归测试失败，报错 `KeyError: 'data_type'`，证明最终落库 `extra_data` 缺少 `sql_result`。
- GREEN：
  - `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh tests/unit/test_chat_repo_serialization.py -q`
  - 结果：`5 passed`
- 受影响回归：
  - `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh tests/unit/test_chat_repo_serialization.py tests/unit/test_multi_intent_coverage_reconcile.py -q`
  - 结果：`10 passed`

## 5. 风险、回滚点与后续建议
- 风险：若未来同一轮出现多个无 `sequence_number` 且无 `envelope.id` 的结构化结果，当前去重会回退到 payload 级 identity；虽可工作，但建议后续统一保证 `envelope.id`。
- 回滚点：回退 `app/repositories/chat_repo.py` 中“turn result_events 归并”逻辑。
- 后续建议：
  - 建议在 `final_composer` 输出的最终 AI 消息中也显式携带 canonical `result_events`，让运行态与持久化态完全一致；
  - 后续可补一条 API/线程历史加载测试，直接覆盖“刷新页面后 sql_result 图表仍存在”的端到端回放场景。

## 6. 执行备注
- `TEAM_UNAVAILABLE_FALLBACK`：本次按单代理完成。
- `APPLY_PATCH_TOOL_UNAVAILABLE_FALLBACK`：编辑通过直接写回完成。
