# Chat Shell Style Unification Refactor Report

## 输入映射

- task_id/card_id/pr_id: none
- worktree: `/Users/jijingkun/.codex/worktrees/8673/fastapi`
- branch: `codex/ui1`

## 重构切片

- `web/src/components/chat/index.tsx`：页面壳层、滚动区、footer、`runtime-status` 接到 `chat-*` 主题 class
- `web/src/components/chat/ChatInput.tsx`：待办提示、输入框、工具栏、发送按钮、底部说明收口到 `chat-compose-*` / `chat-todo-*` / `chat-contrast-button`
- `web/src/components/chat/messages/{human,ai,shared}.tsx`：消息气泡、消息工具条、分支切换按钮统一消费 `chat-human-bubble` / `chat-message-*` / `chat-branch-switcher`
- `web/src/app/globals.css`：删除无消费者的 `chat-empty-card`、`chat-panel-surface`，新增 `chat-runtime-status`

## 瘦身合同执行结果

- obsolete_paths：旧 footer/status inline shell、旧输入框 inline shell、旧消息气泡/工具条 inline shell、无消费者聊天 class，均已删除
- retained_paths：`data-testid="chat-input"`、`data-testid="chat-input-container"`、`data-testid="runtime-status"`，唯一理由是 E2E 契约依赖
- single_entry_owner：聊天壳层视觉唯一入口为 `web/src/app/globals.css` 中被组件实际消费的 `chat-*` 主题 class

## 验证证据

- `git diff --check`：通过
- `python3 scripts/ci/check_lean_budget.py --diff-range HEAD --strict`：通过（未命中热点目录）
- `chat-*` 定义/使用对账：通过，当前无聊天壳层死 class
- `cd web && pnpm run lint`：通过，0 warning / 0 error

## 风险与后续

- 已补装 `web` 依赖，并将 lint 入口收敛为官方推荐的 `eslint .` + `@next/eslint-plugin-next`；当前 `pnpm run lint` 已清零 warning。
- 若后续要基于 `phase` 做更细粒度动效，需要单独立卡，不在本次收口范围
