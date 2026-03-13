# Chat Typography CJK Refresh Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将聊天前端从默认后台/默认聊天排版升级为统一的 CJK WebFont + 中文阅读型 typography 体系。

**Architecture:** 在根布局收口字体入口，在全局样式收口排版 token，在 Markdown 样式层收口正文阅读规则，并把消息流宽度与正文阅读宽度拆分，避免图表/SQL/工具结果被错误缩窄。

**Tech Stack:** Next.js 15、React 19、TypeScript、Tailwind CSS v4、`next/font/google`

---

## 最终方案

> 本轮补充：统一以后台管理的克制产品风格为基准，聊天区跟随同一标题层级、侧边栏文字对比与辅助文案色阶。


### 模块边界
- 根布局只负责注入 CJK 主字体变量，不在组件层重复声明 `font-family`。
- `globals.css` 负责全局 typography token、基础排版与聊天流宽度 token，并提供“会话型文本元素”共用的内容列宽 token。
- `markdown-styles.css` 负责聊天正文阅读样式，不承载图表/SQL/工具卡片布局职责，但必须消费共享内容列宽 token 以与会话列对齐。
- 代码、ID、SQL 等保留 `font-mono` 语义，不随主字体切换。

### 依赖方向
- `layout.tsx` 注入 `Noto Sans SC` 变量。
- `globals.css` 消费字体变量并定义全局字号、行高、宽度 token。
- `ChatInput.tsx`、`human.tsx` 与 `ai.tsx` 中的会话型文本元素共同消费同一内容列宽 token，避免输入框、用户气泡、状态行各自写死。
- `markdown-text.tsx` 暴露可选 `className` 入口。
- `ai.tsx` 让 AI 正文、操作栏、流式状态与加载占位共享同一内容列宽；图表、SQL、工具结果继续保持原有宽布局。

### 状态归属
- 字体与 typography 都是设计系统静态配置，不引入组件状态或运行时切换逻辑。

### 错误处理责任
- 由根布局提供统一 fallback 字体链；组件层不新增字体兼容分支。

## 关键验收口径
- 全站默认文本切换到 CJK 主字体体系，中文观感统一。
- AI Markdown 长文具备更清晰的标题、段落、列表、引用层次。
- 消息流宽度放宽，但 AI 正文、操作栏、用户气泡、状态行与底部输入框共享同一内容列宽，并保持居中对齐。
- SQL 表格、图表、工具结果卡片不被错误缩窄。
- `pnpm lint` 与 `pnpm build` 通过。
