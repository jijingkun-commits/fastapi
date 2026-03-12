# ChatService done 收口 human anchor 调试报告

## 1. 问题现象与影响范围
- 现象：聊天流在 graph 正常结束后进入 done 补发逻辑时，前端收到错误 `name 'current_human_message_id' is not defined`。
- 影响范围：`ChatService.stream` 的非 interrupt 收口路径，尤其是依赖 snapshot messages 做当前轮切片的 SSE done fallback。
- 用户可见结果：前端 toast 报错，当前轮最终文本无法稳定补发。

## 2. 根因证据链（含被排除假设）
- 证据 1：`app/services/chat_service.py` 在 done fallback 中调用 `_slice_current_turn_messages(messages, current_human_message_id)`，但函数体内已不存在该变量定义。
- 证据 2：本轮 human 锚点由 `human_message.id` 单点生成并在 done fallback 直接消费，说明 graph/supervisor 并未丢失状态，问题发生在 service 层本地变量断链。
- 证据 3：定向回归 `tests/unit/test_chat_service_human_attachment_persistence.py::test_stream_done_fallback_should_use_current_turn_human_anchor` 在修复前稳定失败，并直接捕获同名 `NameError`。
- 被排除假设：
  - supervisor 路由异常：排除。graph 已正常返回 snapshot。
  - agent 结果异常：排除。snapshot 中存在当前轮 AIMessage，错误发生在读取前的变量解析阶段。
  - DB message_id 异常：排除。失败先于 `_get_latest_ai_message_id` 生效。

## 3. 修复内容（文件/符号/变更摘要）
- 文件：`app/services/chat_service.py`
- 符号：`ChatService.stream`
- 变更：新增单一 owner `human_message.id` 作为唯一 owner，并统一投影/消费于：
  - done fallback 的 `_slice_current_turn_messages(...)`
- 结论：将“本轮 human 锚点”收口为 `human_message.id` 单一来源，去掉悬空变量名依赖与额外中间变量。

## 4. 验证命令与结果（含失败 -> 通过过程）
- 红灯：
  - 命令：`VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh tests/unit/test_chat_service_human_attachment_persistence.py`
  - 结果：1 failed / 1 passed
  - 失败点：`NameError: name 'current_human_message_id' is not defined`
- 绿灯：
  - 命令：`VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh tests/unit/test_chat_service_human_attachment_persistence.py tests/unit/test_chat_service_turn_slice.py`
  - 结果：5 passed

## 5. 风险、回滚点与后续建议
- 风险：本次只收口 `ChatService.stream` 内的 turn anchor，本轮之外的状态 contract 未改动。
- 回滚点：回滚 `app/services/chat_service.py` 中本轮 human 锚点收口相关改动即可恢复到修复前实现。
- 后续建议：若继续推进“单一真理源”治理，可把 turn-level 输入 contract 与 human anchor 的创建/投影放进同一 builder/入口，避免 service 层再次出现局部变量与 state 投影分叉。
