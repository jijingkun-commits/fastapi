# Chat Tool Call Card Compact Tuning Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让聊天里的工具调用卡片更紧凑，收窄横向宽度和纵向留白，同时保持现有主题、交互和可读性不变。

**Architecture:** 组件结构与本地展开状态保持不变，只在 `chat-tool-call-*` 单一样式入口内收紧宽度与 spacing token，避免再次引入局部样式分叉。

**Tech Stack:** Next.js 15、React 19、TypeScript、Tailwind CSS v4、Framer Motion

---

### Task 1: 固化本轮紧凑化设计

**Files:**
- Create: `docs/plans/2026-03-12-chat-tool-call-card-compact-tuning-design.md`
- Create: `docs/plans/2026-03-12-chat-tool-call-card-compact-tuning.md`

**Step 1: 写入微调目标与边界**

- 明确这轮只处理工具调用卡片宽度/间距，不改结构、不改交互、不引入新视觉 owner。

**Step 2: 写入架构门禁与瘦身合同**

- 记录模块边界、依赖方向、状态归属、错误处理责任；
- 冻结 `obsolete_paths / retained_paths / single_entry_owner`。

### Task 2: 收紧工具调用卡片的 spacing token

**Files:**
- Modify: `web/src/app/globals.css`

**Step 1: 收紧头部最小宽度**

- 将 `chat-tool-call-toggle` 的 `min-width` 从 `320px` 收到 `280px`，让短工具名不再被无谓撑宽。

**Step 2: 收紧头部与展开体内边距**

- 将 `chat-tool-call-toggle` 与 `chat-tool-call-body` 的 `padding` 从 `10px 14px` 收到 `8px 12px`。

**Step 3: 收紧键值条目间距**

- 将 `chat-tool-call-kv` 的 `gap` 从 `10px` 收到 `8px`，维持小卡片的紧凑节奏。

### Task 3: 做最小验证

**Files:**
- Modify: `web/src/app/globals.css`

**Step 1: 运行前端 lint**

- Run: `cd web && pnpm run lint`
- Expected: PASS

**Step 2: 检查 diff 格式**

- Run: `git diff --check`
- Expected: no output

**Step 3: 提交策略**

- 当前会话按仓内与系统约束不自动提交；如用户需要，再走提交流程。
