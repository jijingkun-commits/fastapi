# 项目代理工作指南

## 1. 全局原则（始终生效）

1. 中文主导：思考过程和输出永远使用中文
2. 审慎修改：修改前逐行审查源代码，不确定就问；先理解上下文与模块边界，再从整体架构、可读性、可维护性出发做必要改进
3. 工程质量优先：优先结构清晰、命名一致、可读、可测试、可维护的方案
4. 复用优先：能用现有模块就不新建
5. 纯净注释：禁止在注释中使用 emoji，禁止添加"修复/优化"过程注释
6. 架构优先：无论是需求开发、缺陷修复还是性能调整，都先确认模块边界、状态契约与职责归属；跨层改动必须先梳理端到端数据流与状态生命周期，避免策略散落到多个节点造成隐性耦合
7. 拒绝补丁：禁止以临时条件分支、硬编码或重复逻辑掩盖问题；必须先定位根因，并在正确层级进行系统性修复
8. 文档同步：涉及架构/API/表结构/配置变更时，先更新文档再改代码
9. 智能体优先：本项目为智能体项目，涉及智能体流程（如 `app/ai/**`）的功能实现时，优先采用流程编排、策略配置、工具抽象与状态管理方案；禁止优先通过硬编码业务分支或固定决策路径实现功能
10. OpenClaw 对标优先：长期参考项目为 `/Users/jijingkun/bojxAI/bot/openclaw`，涉及智能体架构、流程编排、工具抽象、状态管理与关键实现方案时，优先对齐其设计理念与实现方式；若与本项目约束冲突，需先说明差异再给出落地方案

## 2. 技术栈

- 后端: FastAPI + LangGraph + SQLAlchemy 2.0
- 前端: Next.js 15 + React 19 + TypeScript
- AI: 涉及 LangChain/LangGraph 时查询最新 API 文档

## 3. 银行业务场景要求

- 需求与测试文档必须结合银行业务场景（贷款、存款、分行、对公/零售）
- 需求文档需要体现业务口径与合规约束（权限、脱敏、敏感字段）
- 测试用例需覆盖至少一个银行场景与一个合规边界场景

## 4. 双数据库架构

| 数据库 | 环境变量 | 用途 | 包含的表 |
|--------|---------|------|---------|
| `chat_db` | `DATABASE_URL` | 主应用库 | t_user, t_chat_message, t_todo, t_metric_definition, t_meta_tables 等 |
| `data_db` | `ANALYTICS_DATABASE_URL` | 分析/数仓库（只读） | fdmdata.f_mid_dep_tb, fdmdata.f_mid_index_result, sdmdata.* 等业务数据表 |

重要规则：
1. 查询分析库数据时，必须通过 Python 脚本连接 `ANALYTICS_DATABASE_URL`
2. 代码中 `analytics_engine`（见 `app/db/session.py`）连接的是 `data_db`
3. `vanna.run_sql()` 执行在 `data_db` 上
4. MCP Postgres 默认连接 `chat_db`，查分析库请走 `ANALYTICS_DATABASE_URL` 对应链路

## 5. Python 代码风格（修改 `**/*.py` 时遵循）

- 文件名: `snake_case`，类名: `PascalCase`，变量/函数: `snake_case`，常量: `UPPER_SNAKE_CASE`
- 所有注释使用中文，模块顶部必须有 docstring
- 完全使用 Type Hints，ORM 使用 SQLAlchemy 2.0 `Mapped[...]` 语法
- 表名以 `t_` 开头，字段名 `snake_case`

## 6. TypeScript/React 代码风格（修改 `**/*.ts` / `**/*.tsx` 时遵循）

- 严格使用 TypeScript，避免 `any`
- 注释使用中文，禁止 emoji 注释

## 7. 代码位置规范

| 类型 | 目录 |
|-----|------|
| HTTP 接口 | `app/api/v1/endpoints/` |
| 业务逻辑 | `app/services/` |
| 数据库操作 | `app/repositories/` |
| AI 工具 | `app/ai/tools/` |
| 智能体 | `app/ai/agents/` |
| 前端组件 | `web/src/components/` |
| 前端 Hooks | `web/src/hooks/` |
| 前端 API | `web/src/lib/` |
| 前端类型 | `web/src/types/` |

## 8. LangGraph 开发规范（修改 `app/ai/**` 时遵循）

所有 Workflow 必须遵循 Pre -> Core -> Post 三段式：
- Preprocess: 消息验证、上下文注入、安全护栏
- AgentCore: LLM 推理与工具调用
- Postprocess: 数据库持久化、资源清理（禁止跳过）

State 管理：
- 必须使用 `add_messages` reducer
- State 必须可序列化
- 流式输出使用 `astream_events(version="v2")`，输出转换为 `AgentEvent` 标准格式

禁止事项：
- 禁止添加独立 `intent_classify` 节点（意图识别由 Supervisor 统一处理）
- 禁止使用 legacy AgentExecutor
- 禁止在 Node 中直接 print
- 禁止在 Service 层直接保存 AI 消息（由 Postprocess 统一处理）

参考实现：
- 单 Agent: `app/ai/workflow/chat_graph.py`
- 多 Agent: `app/ai/workflow/multi_agent_graph.py`

## 9. 多轮对话安全（修改 `app/ai/**` 时遵循）

修改前必须询问用户确认：
- `app/ai/prompts/agent_prompts.py` - Agent Prompt
- `app/ai/state.py` - State 定义
- `*_graph.py` 中的 preprocess/postprocess 节点

核心原则：AI 只回答最后一条 HumanMessage，历史作为上下文不重复处理

## 10. 文档同步规则

涉及以下任务时，先更新文档，再修改代码：架构变更、新增功能/模块、API 接口变更、数据库表结构变更

代码变更 -> 文档映射：

| 代码变更 | 更新文档 |
|---------|---------|
| `app/ai/workflow/`, `app/ai/tools/` | `docs/开发文档/架构设计/AI模块设计.md` |
| `app/ai/semantic/` | `docs/开发文档/架构设计/问数引擎设计.md` |
| `app/api/` | `docs/API文档/接口文档.md` |
| `app/models/` | `docs/开发文档/架构设计/数据库设计.md` |
| `web/src/components/` | `docs/开发文档/架构设计/前端架构.md` |
| 环境变量 | `docs/开发文档/快速入门/配置说明.md` + `.env.example` |
| 特殊处理（兜底/兼容/临时绕过） | `docs/开发文档/架构设计/防屎山记录手册.md` |

补充要求：
- 若变更命中已登记的 SP 条目对应文件，必须同步更新该条目的"最后更新"与状态
- 若新增特殊处理，必须新增 SP 编号并按模板补全"问题描述/涉及文件/风险/优化方向"

跳过条件：用户说"直接改代码"、纯格式化/重构、简单 Bug 修复

## 11. 执行上下文校验

当任务涉及修改代码/运行测试/构建/数据迁移时，必须先校验：
- `pwd` / `git rev-parse --show-toplevel` / `git branch --show-current` / `git worktree list`
- 若任务已给定目标分支或 worktree，必须与校验结果一致；不一致时立即停止
- 若任务未给定目标分支或 worktree，先回传校验结果，再继续后续执行
- 命令优先使用显式路径（如 `pnpm -C web ...`）

纯问答、方案讨论、文档阅读类任务可跳过

## 12. 端口

- 前端 (Next.js): `3000`
- 后端 (FastAPI): `8000`
