# P1 后台术语中文化 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 收口管理后台中直接展示给用户的中英混搭术语，统一成中文表达，同时不破坏依赖英文枚举值的筛选/治理输入。

**Architecture:** 本次仅调整 `web/src/components/admin/**` 展示层文案与少量显示映射；对 `value="active"`、`value="archived"`、`doc_kind` 等真实契约保持不变，只替换可见标题、说明、徽标文本和占位提示。为减少重复，允许在前端增加极小型显示映射 helper。

**Tech Stack:** Next.js 15、React 19、TypeScript。

---

### Task 1: 收口 LLM/Skill/Metric/Access 标题术语
- 仅替换 `Base URL`、`API Key`、`Skill ID`、`指标 ID`、`query_template`、`sql_template`、`Schema 白名单` 等用户可见标题。
- 保留 `API/SQL/JSON/ETL/LLM` 等必要缩写。

### Task 2: 收口 Memory 后台原始字段显示
- 为 `status/doc_kind/chunk status` 增加中文显示映射。
- 对必须按英文代码输入的筛选框，仅把标签与说明翻成中文，示例值继续保留英文代码。

### Task 3: 最小静态验证
- 用精确 `rg` 检查本轮目标英文是否清零。
- 运行前端 `lint`，确认没有新增错误；若只有既有 warning，则记录为替代证据。
