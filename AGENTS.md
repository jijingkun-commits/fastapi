# 项目代理工作指南（Codex / VSCode）

本文件用于让 Codex 在 VSCode 会话中直接继承项目规则、命令工作流与目录约定。

## 1) 全局原则（始终生效）

1. 中文主导：思考与输出默认使用中文。
2. 审慎演进：先理解上下文与模块边界，再从整体架构、可读性、可维护性出发做必要改进。
3. 复用优先：优先复用现有模块与已有实现。
4. 架构优先：无论需求、缺陷还是性能问题，先梳理模块边界、状态契约与端到端数据流。
5. 拒绝补丁：禁止以临时分支、硬编码或重复逻辑掩盖问题，必须基于根因在正确层级修复。
6. 注释约束：禁止 emoji 注释；禁止“修复/优化过程”式注释。
7. 文档同步：涉及架构/API/表结构/配置变更时，先更新文档再改代码。

## 2) 规则来源与适用范围

规则来源（兼容迁移）：

- `.cursor/rules/core.mdc`
- `.cursor/rules/banking-context.mdc`
- `.cursor/rules/doc_sync.mdc`
- `.cursor/rules/conversation_safety.mdc`
- `.cursor/rules/dual-database.mdc`
- `.cursor/rules/langgraph.mdc`
- `.cursor/rules/python_style.mdc`
- `.cursor/rules/typescript_style.mdc`

默认必遵循：`core`、`banking-context`、`doc_sync`。

按场景追加：

- 修改 `**/*.py`：应用 `python_style`。
- 修改 `**/*.ts` / `**/*.tsx`：应用 `typescript_style`。
- 涉及 `app/ai/**`：应用 `langgraph` 与 `conversation_safety`。
- 涉及数据库、问数、`data_db`：应用 `dual-database`。

## 3) `/命令` 兼容（Cursor Commands -> Codex）

当用户输入 `/xxx` 或明确提到同名工作流时：

1. 若存在 `.cursor/commands/xxx.md`，先读取该文件；
2. 按该文件步骤执行（分析/改码/验证/文档）；
3. 若命令与当前任务冲突，以用户当前明确要求为准。

常用映射示例：

- `/plan` -> `.cursor/commands/plan.md`
- `/imp` -> `.cursor/commands/imp.md`
- `/debug` -> `.cursor/commands/debug.md`
- `/review` -> `.cursor/commands/review.md`
- `/test` -> `.cursor/commands/test.md`
- `/doc-check` -> `.cursor/commands/doc-check.md`

## 4) 双数据库强约束

1. `DATABASE_URL` -> `chat_db`（主应用库）。
2. `ANALYTICS_DATABASE_URL` -> `data_db`（分析库，只读）。
3. MCP Postgres 默认连接 `chat_db`，查分析库请走 `ANALYTICS_DATABASE_URL` 对应链路。

## 5) 文档同步约定

涉及以下代码路径时，同步更新对应文档：

- `app/ai/workflow/`、`app/ai/tools/` -> `docs/开发文档/架构设计/AI模块设计.md`
- `app/ai/semantic/` -> `docs/开发文档/架构设计/问数引擎设计.md`
- `app/models/` -> `docs/开发文档/架构设计/数据库设计.md`
- `web/src/components/` -> `docs/开发文档/架构设计/前端架构.md`
- 环境变量变更 -> `docs/开发文档/快速入门/配置说明.md` 与 `.env.example`
- 涉及特殊处理（兜底逻辑、兼容补丁、临时绕过、历史债务）-> `docs/开发文档/架构设计/防屎山记录手册.md`

补充要求：

- 若变更命中已登记的 SP 条目对应文件，必须同步更新该条目的“最后更新”与状态。
- 若新增特殊处理，必须新增 SP 编号并按模板补全“问题描述/涉及文件/风险/优化方向”。

## 6) 技能目录（本项目）

若用户要求使用本地技能，优先从以下目录读取 `SKILL.md`：

- `.cursor/skills/`
- `.agent/skills/skills/`

执行规则：仅加载与当前任务直接相关的技能文件，避免全量读取。
