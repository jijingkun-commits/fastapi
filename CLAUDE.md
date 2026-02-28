# 项目代理工作指南

## 全局原则
1. 中文主导：思考过程和输出永远使用中文
2. 审慎修改：修改前逐行审查源代码，不确定就问
3. 工程质量优先：结构清晰、命名一致、可读、可测试、可维护
4. 复用优先：能用现有模块就不新建
5. 纯净注释：禁止 emoji，禁止"修复/优化"过程注释
6. 架构优先：先确认模块边界、状态契约与职责归属
7. 拒绝补丁：禁止临时条件分支、硬编码掩盖问题
8. 文档同步：涉及架构/API/表结构/配置/规则/使用技巧/命令（workflow)变更时，先更新文档再改代码
9. 智能体优先：涉及 app/ai/** 时优先采用流程编排、策略配置、工具抽象，禁止硬编码业务分支
10. OpenClaw 对标：参考 /Users/jijingkun/bojxAI/bot/openclaw 的架构设计，冲突时先说明差异

## 技术栈
- 后端: FastAPI + LangGraph + SQLAlchemy 2.0
- 前端: Next.js 15 + React 19 + TypeScript
- AI: 涉及 LangChain/LangGraph 时用 context7 MCP 查询最新 API

## 双数据库
- chat_db (DATABASE_URL): 主应用库（t_user, t_chat_message 等）
- data_db (ANALYTICS_DATABASE_URL): 分析库只读（fdmdata.*, sdmdata.*）
- mcp__postgres__query → chat_db; mcp__postgres-data-db__query → data_db
- 代码中 analytics_engine 连接 data_db

## MCP 工具路由（强制）

以下场景必须优先使用对应 MCP 工具，禁止用 Bash/内置工具替代：

| 场景 | 必须使用的 MCP 工具 | 禁止替代方式 |
|------|-------------------|-------------|
| 查询 chat_db 数据/表结构 | `mcp__postgres__query` | 禁止用 psql 命令行 |
| 查询 data_db 数据/表结构 | `mcp__postgres-data-db__query` | 禁止用 psql 命令行 |
| LangChain/LangGraph/任何第三方库 API 用法不确定时 | `context7`（先 resolve-library-id 再 query-docs） | 禁止凭记忆猜测 API |
| GitHub 操作（PR/Issue/代码搜索） | `github-mcp-server` 系列工具 | 禁止用 gh CLI |
| E2E 测试/浏览器交互/截图 | `playwright` 系列工具 | 禁止手写 playwright 脚本再执行 |
| 任务管理/看板操作 | `vibe_kanban` 系列工具 | 禁止手动操作 |
| 对象存储操作 | `minio` 系列工具 | 禁止用 mc CLI |

### 触发规则
1. 涉及数据库查询时，先判断目标库（chat_db vs data_db），然后直接调用对应 MCP，不要先用 Bash 尝试
2. 涉及第三方库 API 且不是 100% 确定用法时，必须先用 context7 查文档，再写代码
3. 涉及 GitHub 操作时，优先用 github-mcp-server，而非 gh CLI
4. 需要浏览器测试时，直接用 playwright MCP，不要生成脚本文件再执行

## 端口
- 前端: 3000 | 后端: 8000

## 执行上下文校验
修改代码/运行测试前必须校验 pwd/git branch/git worktree，不一致时立即停止。

## 详细规则
领域规则（代码风格、LangGraph、文档同步等）见 .claude/rules/ 目录。

## 规则与脚本速查
- 改规则/命令 → CC 侧 PostToolUse hook 自动同步（也可手动 `python3 scripts/sync_rules_to_cc.py`）
- 加工作流脚本 → 放 `.cursor/scripts/` + 在 `scripts/` 补 symlink
- 加项目脚本 → 直接放 `scripts/` 或子目录
- 建立新约定/流程 → 必须同步写入操作手册（本文件或对应 docs）

## 规则维护
- 规则唯一源：.cursor/rules/*.mdc
- 命令唯一源：.cursor/commands/*.md
- 同步到 CC：`python3 scripts/sync_rules_to_cc.py`（rules 去 frontmatter 生成 .claude/rules/*.md，commands 直接复制到 .claude/commands/*.md）
- 自动同步：CC 侧 PostToolUse hook 在编辑 .cursor/rules/*.mdc 或 .cursor/commands/*.md 时自动触发 sync
- 新增规则：在 .cursor/rules/ 创建 .mdc 文件，编辑保存后自动同步
- 新增命令：在 .cursor/commands/ 创建 .md 文件，编辑保存后自动同步

## 脚本目录
- 个人工作流脚本实体在 `.cursor/scripts/`，`scripts/` 下为 symlink
- 项目脚本直接放 `scripts/` 及其子目录（db/、data/）
- 新增个人工作流脚本：文件放 `.cursor/scripts/`，然后 `ln -s ../.cursor/scripts/xxx scripts/xxx` 建 symlink
- 新增项目脚本：直接放 `scripts/` 或对应子目录，无需额外操作
