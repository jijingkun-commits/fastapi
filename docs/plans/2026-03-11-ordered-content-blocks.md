# Ordered Content Blocks Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 AI 回复统一收口为有序内容块，让知识库图片、工具生成图片和结构化结果按自然顺序贴靠到对应文本附近。

**Architecture:** 后端新增 canonical `message display blocks` 编译器，把最终文本、`kb_images`、`result_events` 编译为 `content(blocks[])` 并落库；前端优先渲染 blocks，旧消息通过兼容编译回放。Phase 1 先解决最终展示与历史回放，Phase 2 再补 SSE block snapshot，彻底删除临时兼容路径。

**Tech Stack:** FastAPI、SQLAlchemy、LangGraph、Next.js、TypeScript、Playwright、pytest、现有聊天消息/API 契约。

---

### Task 1: 定义 canonical block compiler

**Files:**
- Create: `app/core/message_display_blocks.py`
- Modify: `app/core/message_content.py`
- Test: `tests/unit/test_message_display_blocks.py`

**Step 1: Write the failing test**
- 新增用例：`final_text` 中的 `[IMG-0]` 应被编译成位于对应文本片段之间的 `image(source=knowledge)` block。
- 新增用例：`result_events` 中的 `sql_result`、`todo_list`、`image` 必须按 `sequence_number` 保序编译。
- 新增用例：未知 `data_type` 必须输出 `fallback_result` block，而不是 silently drop。
- 新增用例：未命中的 `[IMG-N]` 保留为可读文本，不抛异常。

**Step 2: Run test to verify it fails**
- Run: `bash scripts/pytest_targeted.sh tests/unit/test_message_display_blocks.py -q`
- Expected: FAIL，当前还没有 `message_display_blocks.py` 或编译函数。

**Step 3: Write minimal implementation**
- 在 `app/core/message_display_blocks.py` 中实现：
  - `compile_message_display_blocks(final_text, kb_images, result_events)`
  - `merge_adjacent_markdown_blocks(blocks)`
  - `dedupe_image_blocks(blocks)`
- 复用 `app/core/message_content.py` 的“提取可读内容”思路，不再新增第三套文本解析 helper。

**Step 4: Run test to verify it passes**
- Run: `bash scripts/pytest_targeted.sh tests/unit/test_message_display_blocks.py -q`
- Expected: PASS

### Task 2: 持久化 canonical blocks，删除旧补丁逻辑

**Files:**
- Modify: `app/repositories/chat_repo.py`
- Modify: `app/api/v1/endpoints/chat_api.py`
- Test: `tests/unit/test_chat_repo_message_blocks.py`
- Modify: `tests/api/test_chat_api.py`

**Step 1: Write the failing test**
- 新增仓储用例：当 AI 最终消息包含 `[IMG-N]` 或 `result_events` 时，`save_conversation_from_messages()` 应保存 `content_type="multimodal"` 和 `content=blocks[]`。
- 新增仓储用例：图表图片已由 `result(image)` 表达时，不得再把图片 Markdown 追加到消息末尾。
- 新增 API 用例：历史消息如果 `content_type="multimodal"`，`/api/v1/chat/threads/{thread_id}/messages` 应返回 block 数组，而不是被打平成纯文本。

**Step 2: Run test to verify it fails**
- Run: `bash scripts/pytest_targeted.sh tests/unit/test_chat_repo_message_blocks.py tests/api/test_chat_api.py -q`
- Expected: FAIL，当前仓储仍在做占位符转 Markdown 与末尾补图。

**Step 3: Write minimal implementation**
- `chat_repo.save_conversation_from_messages()`：
  - 删除保存前 `[IMG-N] -> Markdown image` 的改写；
  - 删除“未引用图表自动补到末尾”；
  - 调用 block compiler，优先存 `content_type="multimodal"`。
- `chat_api`：
  - 对 `multimodal` 内容保留 JSON block 数组；
  - 旧字符串消息继续兼容回放。

**Step 4: Run test to verify it passes**
- Run: `bash scripts/pytest_targeted.sh tests/unit/test_chat_repo_message_blocks.py tests/api/test_chat_api.py -q`
- Expected: PASS

### Task 3: 前端消息标准化优先 blocks

**Files:**
- Modify: `web/src/types/message.ts`
- Modify: `web/src/lib/backend.ts`
- Modify: `web/src/lib/message-normalizer.ts`

**Step 1: Add failing type/normalization assertions**
- 在现有消息标准化相关测试位置新增断言；若暂无现成前端单测入口，则先在文档中记录“不新增新框架”，后续由 Playwright 覆盖最终行为。
- 补一个后端返回样例：`content_type="multimodal"` + `content=[...]`。

**Step 2: Write minimal implementation**
- 扩展 `ContentBlock` 类型，纳入 `sql_result`、`todo_list`、`fallback_result`。
- `message-normalizer` 优先保留 block 数组；仅在旧消息场景下再走兼容打平。
- `backend.ts` 的历史消息类型定义同步更新，避免 block 被当作 `string` 丢失。

**Step 3: Verify locally via static checks**
- Run: `cd web && pnpm lint`
- Expected: PASS

### Task 4: AssistantMessage 切到单入口块渲染

**Files:**
- Create: `web/src/components/chat/messages/assistant-content-blocks.tsx`
- Modify: `web/src/components/chat/messages/ai.tsx`
- Modify: `web/src/components/chat/utils.ts`

**Step 1: Write the failing UI regression**
- 新增 Playwright 用例：
  - AI 回复同时包含文本、知识库图片、图表图片时，图片必须出现在对应段落附近；
  - 不允许所有图片统一堆在消息底部。
- 推荐新建：`web/e2e/chat-ordered-content-blocks.spec.cjs`

**Step 2: Run test to verify it fails**
- Run: `cd web && pnpm exec playwright test e2e/chat-ordered-content-blocks.spec.cjs --project=chromium`
- Expected: FAIL，当前仍是“正文 + 底部结果卡片”布局。

**Step 3: Write minimal implementation**
- 新增 `assistant-content-blocks.tsx`：
  - `markdown` -> `MarkdownText`
  - `image` -> 复用现有图片渲染/lightbox 交互
  - `sql_result` -> 复用 `SqlResultChart` + `SqlResultTable`
  - `todo_list` -> 复用 `TodoListCard`
  - `fallback_result` -> 复用现有 fallback 卡片样式
- `ai.tsx`：
  - blocks 存在时只走单入口块渲染；
  - 工具调用展示和命令栏保持原样；
  - 旧 `replaceImagePlaceholders()` 路径只保留给兼容旧消息，待 Phase 2 删除。

**Step 4: Run test to verify it passes**
- Run: `cd web && pnpm exec playwright test e2e/chat-ordered-content-blocks.spec.cjs --project=chromium`
- Expected: PASS

### Task 5: 流式兼容收口到 Phase 1 可用状态

**Files:**
- Modify: `web/src/hooks/useSSEStream.ts`
- Modify: `web/src/providers/StreamContext.tsx`
- Modify: `web/src/components/chat/messages/ai.tsx`

**Step 1: Write the failing regression**
- 扩展上一个 Playwright 用例：同一轮消息在“生成完成但未刷新页面”时，也要看到正确图文顺序。

**Step 2: Write minimal implementation**
- 在 Phase 1 里，允许前端对 in-flight message 做一次**临时兼容编译**：
  - 输入仍是 `final_answer + kb_images + result_events`
  - 输出只服务当前消息视图，不作为长期 owner 持久化
- 兼容编译必须复用与后端 compiler 同一份 block 规则文档，不能额外加关键词猜测。
- 在代码中明确标记：该路径仅服务 Phase 1，Phase 2 增加 SSE `display_blocks` 后删除。

**Step 3: Verify behavior**
- Run: `cd web && pnpm exec playwright test e2e/chat-ordered-content-blocks.spec.cjs --project=chromium`
- Expected: PASS，当前页不刷新也能看到图文贴靠。

### Task 6: 文档同步与长期决策记录

**Files:**
- Modify: `docs/开发文档/架构设计/AI模块设计.md`
- Modify: `docs/API文档/接口文档.md`
- Modify: `memory-bank.md`

**Step 1: Update docs first**
- 在架构设计文档中明确：AI assistant message 的最终展示协议是 ordered content blocks。
- 在 API 文档中说明：历史消息 `content_type=multimodal` 时，`content` 返回 block 数组。
- 在 `memory-bank.md` 中记录“知识库占位符降级为中间语法，最终展示收敛到 ordered content blocks”的长期决策。

**Step 2: Run focused verification**
- Run: `bash scripts/pytest_targeted.sh tests/unit/test_message_display_blocks.py tests/unit/test_chat_repo_message_blocks.py tests/api/test_chat_api.py -q`
- Expected: PASS
- Run: `cd web && pnpm exec playwright test e2e/chat-ordered-content-blocks.spec.cjs --project=chromium`
- Expected: PASS

### Task 7: Phase 2 预留（可单独卡片推进）

**Files:**
- Modify: `app/services/chat_service.py`
- Modify: `web/src/hooks/useSSEStream.ts`
- Modify: `web/src/types/message.ts`

**Step 1: Add protocol design test / fixture**
- 为 SSE `display_blocks` 快照事件补协议 fixture，约束其 payload 结构。

**Step 2: Implement snapshot event**
- 后端在 `final_answer` / `result` 收敛后发 `display_blocks`；
- 前端直接消费 canonical blocks snapshot。

**Step 3: Delete temporary compatibility path**
- 删除 `ai.tsx` / `useSSEStream.ts` 中的 Phase 1 临时兼容编译逻辑。

**Step 4: Verify**
- Run: `cd web && pnpm exec playwright test e2e/chat-ordered-content-blocks.spec.cjs --project=chromium`
- Expected: PASS，且无需刷新/兼容编译。
