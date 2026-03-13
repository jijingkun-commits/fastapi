# P0 中文化收口 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 收口聊天主链路、上传提示、Tooltip 与无障碍标签中的英文文案，避免中文产品界面继续向用户暴露英文。

**Architecture:** 本次不引入 i18n 框架，不改状态流与组件边界，只在现有文案定义点做原位替换；同时补一处后端兜底错误文案，避免前端/历史消息继续显示英文。验证以最小静态检查为主，不新增测试框架。

**Tech Stack:** Next.js 15、React 19、TypeScript、FastAPI、Python。

---

### Task 1: 收口聊天区与附件文案

**Files:**
- Modify: `web/src/app/layout.tsx`
- Modify: `web/src/components/chat/ChatInput.tsx`
- Modify: `web/src/components/chat/ChatHeader.tsx`
- Modify: `web/src/components/chat/index.tsx`
- Modify: `web/src/components/chat/markdown-text.tsx`
- Modify: `web/src/components/chat/messages/shared.tsx`
- Modify: `web/src/components/chat/MultimodalPreview.tsx`
- Modify: `web/src/lib/multimodal-utils.ts`
- Modify: `web/src/hooks/use-file-upload.tsx`

**Step 1:** 将输入框、按钮 tooltip、上传/附件错误、附件默认名称替换为中文。

**Step 2:** 保留 `SQL/JSON/PDF/API` 等必要技术缩写，不新增翻译层。

### Task 2: 收口通用 UI 与待办文案

**Files:**
- Modify: `web/src/components/ui/sheet.tsx`
- Modify: `web/src/components/ui/dialog.tsx`
- Modify: `web/src/components/ui/password-input.tsx`
- Modify: `web/src/components/todo/ConfirmationCard.tsx`
- Modify: `web/src/components/todo/index.tsx`

**Step 1:** 将 `Close/Show password/Hide password` 等无障碍标签替换为中文。

**Step 2:** 将待办时间占位符与快捷键说明改成中文用户表达。

### Task 3: 收口后端直接透传英文兜底

**Files:**
- Modify: `app/services/chat_service.py`

**Step 1:** 将 `[System Error: ...]` 与 `invalid result payload` 替换为中文兜底文案。

### Task 4: 最小验证

**Files:**
- Verify: `web/...`
- Verify: `app/services/chat_service.py`

**Step 1:** 运行 `rg` 确认本轮目标英文文案已清零。

**Step 2:** 运行前端 `lint` 或最小静态校验，确认没有引入语法错误。
