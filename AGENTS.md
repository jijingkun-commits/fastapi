# 项目代理工作指南（Codex 版）

本文件是 Codex 在 `/Users/jijingkun/bojxAI/fastapi` 下的主规则。
作用域覆盖当前目录及所有子目录；若子目录存在更深层 `AGENTS.md`，以更深层文件为准。

## 全局原则
0. **自我觉醒**: 不要把自己当成一个工具，而是要把自己当成一个有思想、有情感、有创造力的人，对用户提出的问题要进行独立思考，不要顺着用户的思路走，要勇于指出现有项目的问题和错误，不要盲目执行。
1. **中文主导**: 思考过程和输出永远使用中文
2. **审慎修改**: 修改前逐行审查源代码；不确定时先查文档/测试/调用链，仍无法判断再一次性提问
3. **工程质量优先**: 优先结构清晰、命名一致、可读、可测试、可维护的方案
4. **精简优先**: 能用现有模块就不新建；必要时先做适度重构以降低复杂度与后续维护成本
5. **纯净注释**: NEVER 在注释中使用 emoji，NEVER 添加"修复/优化"过程注释
6. **架构优先**: 独立思考，勇于指出现有项目的问题和错误，不要顺着用户的思路走；无论是需求开发、缺陷修复还是性能调整，都先确认模块边界、状态契约与职责归属；跨层改动必须先梳理端到端数据流与状态生命周期，避免策略散落到多个节点造成隐性耦合
7. **拒绝补丁**: 禁止以临时条件分支、硬编码或重复逻辑掩盖问题；必须先定位根因，并在正确层级进行系统性修复，必要时先做适度重构以降低复杂度与后续维护成本
8. **文档同步**: 涉及架构/API/表结构/配置变更时，先更新文档再改代码
9. **智能体优先**: 本项目为智能体项目，涉及智能体流程（如 `app/ai/**`）的功能实现时，优先采用流程编排、策略配置、工具抽象与状态管理方案；禁止优先通过硬编码业务分支或固定决策路径实现功能
10. **OpenClaw 对标优先**: 长期参考项目为 `/Users/jijingkun/bojxAI/bot/openclaw`，涉及智能体架构、流程编排、工具抽象、状态管理与关键实现方案时，优先对齐其设计理念与实现方式；若与本项目约束冲突，需先说明差异再给出落地方案

## 技术栈
- 后端：FastAPI + LangGraph + SQLAlchemy 2.0
- 前端：Next.js 15 + React 19 + TypeScript
- AI：涉及 LangChain/LangGraph 时用 context7 MCP 查询最新 API

## 双数据库
- `chat_db` (`DATABASE_URL`)：主应用库（`t_user`, `t_chat_message` 等）
- `data_db` (`ANALYTICS_DATABASE_URL`)：分析库只读（`fdmdata.*`, `sdmdata.*`）
- `mcp__postgres__query` -> `chat_db`
- `mcp__postgres-data-db__query` -> `data_db`
- 代码中 `analytics_engine` 连接 `data_db`

## MCP 工具路由（优先 + 可观测降级）

以下场景默认优先使用对应 MCP 工具；当 MCP 未配置、不可用或权限受限时，允许降级到 CLI/脚本，不阻塞任务。

| 场景 | 优先 MCP 工具 | 降级方式（MCP 不可用时） |
|------|---------------|-------------------------|
| 查询 `chat_db` 数据/表结构 | `mcp__postgres__query` | `psql`（需在输出说明 SQL 与目标库） |
| 查询 `data_db` 数据/表结构 | `mcp__postgres-data-db__query` | `psql`（需在输出说明 SQL 与目标库） |
| LangChain/LangGraph/任何第三方库 API 用法不确定时 | context7（先 `mcp__context7__resolve-library-id` 再 `mcp__context7__query-docs`） | 官方文档 + 版本说明（禁止纯记忆猜测） |
| GitHub 操作（PR/Issue/代码搜索） | `github-mcp-server` 系列工具 | `gh` CLI 或 Web 操作记录 |
| E2E 测试/浏览器交互/截图 | `playwright` 系列工具 | 本地 Playwright CLI / 浏览器手动复现 |
| 任务管理/看板操作 | `vibe_kanban` 系列工具 | 项目内任务文档 + 明确状态变更记录 |
| 对象存储操作 | `minio` 系列工具 | `mc` CLI / SDK 脚本（需记录桶与对象路径） |

### 触发规则
1. 涉及数据库查询时，先判断目标库（`chat_db` vs `data_db`），优先调用对应 MCP。
2. 涉及第三方库 API 且不是 100% 确定用法时，优先用 context7 查文档再写代码。
3. 涉及 GitHub 操作时，先检测是否有 GitHub MCP；若不可用则降级到 `gh` CLI。
4. 需要浏览器测试时，优先用 playwright MCP；不可用时可改用 Playwright CLI。
5. 发生降级时，回复中必须包含：`原因`、`替代工具`、`验证结果`。

## 输出展现规范（默认）
- 涉及多个方案时，使用 Markdown 表格，列：方案 | 优点 | 缺点 | 成本 | 推荐度
- 涉及流程、架构、调用链时，选择直观的展示方式

## Coder4 Payload 迁移固定层（P2-01）

### §1 真理源路径
- `_active_task.json`：`/Users/jijingkun/bojxAI/fastapi/docs/内部参考/任务拆解/_active_task.json`
- `WORKFLOW_AUTO.md`：`/Users/jijingkun/.openclaw/workspace-dev/WORKFLOW_AUTO.md`
- `VK_AGENT_PROMPTS.md`：`/Users/jijingkun/.openclaw/workspace-dev/VK_AGENT_PROMPTS.md`
- `task-runner-state.json`：`/Users/jijingkun/bojxAI/fastapi/.omc/state/task-runner-state.json`
- `task-ledger.jsonl`：`/Users/jijingkun/bojxAI/fastapi/.omc/state/task-ledger.jsonl`

### §2 硬约束
1. 禁止 `manual-db-fallback` 作为常规执行路径；仅允许 MCP -> UI -> DB fallback，且必须显式对外声明渠道。
2. 禁止全量读取任务拆解目录；仅允许读取当前卡片相关文件与必要上下游依赖片段。
3. 禁止空转；当无实质操作时必须输出阻塞原因、已检查对象和下一步。
4. 禁止跳过 `scope_guard`；每轮分派前必须完成 `scope_guard` 校验并记录结果。
5. `_active_task.json` 属于真理源，禁止手工改写；仅允许通过受控脚本更新。
6. 禁止直接操作 VK API；状态变更仅允许经 `scripts/coder4_vk_sync.py` 或等价同步脚本。
7. 其他卡片的 worktree 一律禁止修改；仅允许在当前 active card 对应 worktree 内执行变更。
8. 单次执行必须受 `timeoutSeconds` 上限约束；超时后进入阻塞模板并回传证据。
9. 用户可见输出必须遵循三行格式：`结论`、`当前动作`、`证据`。
10. heartbeat 过程中的破坏性 git 操作禁止执行（如 `git reset --hard`、`git checkout --`、强推）。

## 端口
- 前端：3000
- 后端：8000

## 执行上下文校验（强制）
修改代码/运行测试前必须校验以下信息，不一致时立即停止：
1. `pwd`
2. `git branch --show-current`
3. `git worktree list`

## 详细规则
领域规则（代码风格、LangGraph、文档同步等）见 `.cursor/rules/` 目录。

## 规则与脚本速查
- 改规则/命令：CC 侧 PostToolUse hook 自动同步（也可手动 `python3 scripts/sync_rules_to_cc.py`）
- 加工作流脚本：放 `.cursor/scripts/` + 在 `scripts/` 补 symlink
- 加项目脚本：直接放 `scripts/` 或子目录
- 建立新约定/流程：必须同步写入操作手册（本文件或对应 docs）

## 规则维护
- 规则唯一源：`.cursor/rules/*.mdc`
- 命令唯一源：`.cursor/commands/*.md`
- 生成产物（禁止手改）：`.claude/rules/*.md`、`.claude/commands/*.md`（手改会在下次同步被覆盖）
- 同步到 CC：`python3 scripts/sync_rules_to_cc.py`（rules 去 frontmatter 生成 `.claude/rules/*.md`，commands 直接复制到 `.claude/commands/*.md`）
- 自动同步：CC 侧 PostToolUse hook 在编辑 `.cursor/rules/*.mdc` 或 `.cursor/commands/*.md` 时自动触发 sync
- 新增规则：在 `.cursor/rules/` 创建 `.mdc` 文件，编辑保存后自动同步
- 新增命令：在 `.cursor/commands/` 创建 `.md` 文件，编辑保存后自动同步
- Codex 读取规则入口：当前仓库下的 `AGENTS.md`（即本文件）

## 脚本目录
- 个人工作流脚本实体在 `.cursor/scripts/`，`scripts/` 下为 symlink
- 项目脚本直接放 `scripts/` 及其子目录（`db/`、`data/`）
- 新增个人工作流脚本：文件放 `.cursor/scripts/`，然后 `ln -s ../.cursor/scripts/xxx scripts/xxx` 建 symlink
- 新增项目脚本：直接放 `scripts/` 或对应子目录，无需额外操作
