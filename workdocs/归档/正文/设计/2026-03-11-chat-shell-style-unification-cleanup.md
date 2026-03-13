# Chat Shell Style Unification Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 收口聊天页壳层样式 owner，删除旧 inline 壳层路径，确保技能加载状态条、输入区、消息工具条都只走同一套 `chat-*` 主题 class。

**Architecture:** `Thread` 负责页面壳层与状态条接线，`ChatInput` 负责输入区皮肤接线，`shared/human/ai` 负责消息级视觉；样式唯一 owner 为 `web/src/app/globals.css` 中被实际消费的 `chat-*` class，不保留无消费者死定义。

**Tech Stack:** Next.js 15、React 19、Tailwind CSS 4、Radix UI。

---

### Task 1: 冻结聊天壳层单入口
- 修改 `web/src/components/chat/index.tsx`
- 修改 `web/src/app/globals.css`
- 修改 `docs/开发文档/架构设计/前端架构.md`

### Task 2: 收口输入区与消息级样式
- 修改 `web/src/components/chat/ChatInput.tsx`
- 修改 `web/src/components/chat/messages/human.tsx`
- 修改 `web/src/components/chat/messages/ai.tsx`
- 修改 `web/src/components/chat/messages/shared.tsx`
- 修改 `docs/开发文档/架构设计/前端UI设计方案.md`

### Task 3: 做最小验证并产出重构报告
- 新建 `workdocs/归档/报告/重构报告/refactor_report_chat-shell-style-unification.md`
- 修改 `memory-bank.md`
