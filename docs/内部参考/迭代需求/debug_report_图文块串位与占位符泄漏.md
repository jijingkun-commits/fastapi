# 图文块串位与占位符泄漏调试报告

## 1. 问题现象与影响范围

- 现象 1：连续两轮知识库问答时，后一轮 `kb_images` 到达后会影响前一轮消息，出现“图片串到上面一轮”的现象。
- 现象 2：刷新历史消息后，第二轮知识库图片可能消失，只剩 `[IMG-N]` 占位符。
- 现象 3：只要有一个占位符未解析，整段文本都会退回纯 Markdown，导致已知图片也不显示。
- 影响范围：`app/repositories/chat_repo.py`、`app/core/message_display_blocks.py`、`web/src/hooks/useSSEStream.ts`、`web/src/components/chat/messages/ai.tsx`、`web/src/lib/message-display-blocks.ts`。

## 2. 根因证据链

### 根因 A：前端把 `kb_images` 当线程级全局状态使用

- 证据：`web/src/components/chat/messages/ai.tsx` 原先直接读取 `thread.kbImages` 参与占位符编译。
- 证据：`web/src/hooks/useSSEStream.ts` 的 `onKbImages` 只更新 `threadRuntime.kbImages`，没有把当前轮映射写回到当前 AI 消息。
- 结果：如果两轮都出现 `[IMG-0]`，第二轮映射会覆盖第一轮消息的渲染结果，造成跨轮串图。

### 根因 B：落库阶段只从 ToolMessage 正文提取 `KB_IMAGES`

- 证据：`app/repositories/chat_repo.py` 原先只扫描 ToolMessage 中的 `<!--KB_IMAGES:{...}-->` 注释。
- 证据：新增回归 `test_save_conversation_from_messages_should_use_ai_kb_images_when_tool_marker_missing` 在修复前失败，表现为 `content_type == "markdown"`。
- 结果：一旦 ToolMessage 标记缺失或未被保存链拿到，历史消息无法恢复图片，只能保留占位符。

### 根因 C：占位符编译采用“全有或全无”回退

- 证据：`app/core/message_display_blocks.py` 与 `web/src/lib/message-display-blocks.ts` 原先只要发现任意一个 placeholder 缺图，就整段退回纯 Markdown。
- 证据：新增回归 `test_compile_message_display_blocks_should_replace_known_placeholder_without_dropping_unknown_one` 在修复前失败。
- 结果：即使已知图片可解析，也会和未知占位符一起退回文本，形成“图片没了，占位符还在”的体验。

### 被排除假设

- 假设：历史接口把 `multimodal` 块数组打平导致丢图。
  - 结论：排除。`tests/api/test_chat_api.py` 通过，且 `app/api/v1/endpoints/chat_api.py` 会保留 `multimodal` 数组。
- 假设：Next/Playwright 环境导致图片不显示。
  - 结论：排除。修复后两条 Playwright 用例均通过，说明不是浏览器层问题。

## 3. 修复内容

### 3.1 后端

- `app/core/message_display_blocks.py`
  - 将占位符编译改为“逐个替换、逐个降级”，不再因单个缺图而整段回退。

- `app/repositories/chat_repo.py`
  - 新增 `kb_images` 规范化与收敛逻辑。
  - 落库时优先把当前轮 AI `additional_kwargs.kb_images` 合并进最终 `extra_data`。
  - ToolMessage 中提取到的 `KB_IMAGES` 仅作为兼容兜底来源。

### 3.2 前端

- `web/src/hooks/useSSEStream.ts`
  - 在流式 `onKbImages` / 恢复流 `onKbImages` 时，把映射写回当前 AI 消息的 `additional_kwargs.kb_images`。

- `web/src/components/chat/messages/ai.tsx`
  - 渲染时优先使用“消息自己的 `kb_images`”，只有缺失时才回退到线程级缓存。

- `web/src/lib/message-display-blocks.ts`
  - 与后端保持同一编译语义：已知占位符正常替换，未知占位符原位保留。

## 4. 验证命令与结果

### 4.1 失败证据（修复前）

- `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh tests/unit/test_message_display_blocks.py tests/unit/test_chat_repo_serialization.py -q`
  - 结果：2 个失败
  - 失败点：
    - `test_compile_message_display_blocks_should_replace_known_placeholder_without_dropping_unknown_one`
    - `test_save_conversation_from_messages_should_use_ai_kb_images_when_tool_marker_missing`

- `PLAYWRIGHT_BASE_URL=http://127.0.0.1:3102 E2E_API_BASE=http://127.0.0.1:8199 PLAYWRIGHT_FRONTEND_PORT=3102 TEST_BACKEND_PORT=8199 PLAYWRIGHT_REUSE_EXISTING_SERVER=false ./node_modules/.bin/playwright test e2e/chat-ordered-content-blocks.spec.cjs --project=chromium --grep "TC-CHAT-BLOCK-02"`
  - 结果：失败
  - 失败点：历史 markdown 占位符仍直接显示 `[IMG-0]`

### 4.2 通过证据（修复后）

- `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh tests/unit/test_message_display_blocks.py tests/unit/test_chat_repo_serialization.py -q`
  - 结果：`14 passed`

- `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh tests/api/test_chat_api.py -q`
  - 结果：`25 passed`

- `cd web && ./node_modules/.bin/tsc --noEmit`
  - 结果：通过

- `cd web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3103 E2E_API_BASE=http://127.0.0.1:8199 PLAYWRIGHT_FRONTEND_PORT=3103 TEST_BACKEND_PORT=8199 PLAYWRIGHT_REUSE_EXISTING_SERVER=false ./node_modules/.bin/playwright test e2e/chat-ordered-content-blocks.spec.cjs --project=chromium`
  - 结果：`2 passed (17.2s)`

- `cd web && ./node_modules/.bin/next lint`
  - 结果：通过，但仓内仍有既有 warning（未在本次修复范围内）

## 5. 风险、回滚点与后续建议

### 风险

- 当前仍保留线程级 `kbImages` 作为流式兼容缓存；虽然渲染优先级已下放到消息级，但该线程级状态尚未完全退役。
- 若未来 SSE done payload 直接提供 canonical `display_blocks`，可进一步删除前端兼容编译路径。

### 回滚点

- 若需快速回退，可撤销以下文件本次变更：
  - `app/core/message_display_blocks.py`
  - `app/repositories/chat_repo.py`
  - `web/src/components/chat/messages/ai.tsx`
  - `web/src/hooks/useSSEStream.ts`
  - `web/src/lib/message-display-blocks.ts`
  - 对应测试文件

### 后续建议

- Phase 2：让 SSE 直接下发 canonical `display_blocks`，前端移除 placeholder 编译兼容层。
- 为“同一轮多次知识库检索、占位符重复编号”的流式场景再补一条 E2E，继续压实跨轮/跨工具隔离。
