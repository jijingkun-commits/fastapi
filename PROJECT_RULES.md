# 项目代理工作指南

## 1. 全局原则（始终生效）

1. 中文主导：思考过程和输出永远使用中文
2. 审慎修改：修改前逐行审查源代码，不确定就问
3. 工程质量优先：优先结构清晰、命名一致、可读、可测试、可维护的方案
4. 复用优先：能用现有模块就不新建
5. 纯净注释：NEVER 在注释中使用 emoji，NEVER 添加"修复/优化"过程注释
6. 架构优先：无论是需求开发、缺陷修复还是性能调整，都先确认模块边界、状态契约与职责归属；跨层改动必须先梳理端到端数据流与状态生命周期，避免策略散落到多个节点造成隐性耦合
7. 拒绝补丁：禁止以临时条件分支、硬编码或重复逻辑掩盖问题；必须先定位根因，并在正确层级进行系统性修复，必要时先做适度重构以降低复杂度与后续维护成本
8. 文档同步：涉及架构/API/表结构/配置变更时，先更新文档再改代码
9. 智能体优先：本项目为智能体项目，涉及智能体流程（如 `app/ai/**`）的功能实现时，优先采用流程编排、策略配置、工具抽象与状态管理方案；禁止优先通过硬编码业务分支或固定决策路径实现功能
10. OpenClaw 对标优先：长期参考项目为 `/Users/jijingkun/bojxAI/bot/openclaw`，涉及智能体架构、流程编排、工具抽象、状态管理与关键实现方案时，优先对齐其设计理念与实现方式；若与本项目约束冲突，需先说明差异再给出落地方案

## 2. 技术栈

- 后端: FastAPI + LangGraph + SQLAlchemy 2.0
- 前端: Next.js 15 + React 19 + TypeScript
- AI: 涉及 LangChain/LangGraph 时用 `context7` MCP 查询最新 API

## 3. 银行业务场景要求

- 需求与测试文档必须结合银行业务场景（贷款、存款、分行、对公/零售）
- 需求文档需要体现业务口径与合规约束（权限、脱敏、敏感字段）
- 测试用例需覆盖至少一个银行场景与一个合规边界场景

### 示例

**需求示例**:
- 输入"查询上月对公存款余额"，系统生成带时间过滤的 SQL
- 输入"按分行统计贷款余额"，系统生成 GROUP BY 查询

**测试示例**:
- 场景：分行维度统计存款余额
- 边界：无权限访问客户明细时返回脱敏或拒绝

## 4. 双数据库架构

本项目使用两个独立的 PostgreSQL 数据库：

| 数据库 | 环境变量 | 用途 | 包含的表 |
|--------|---------|------|---------|
| `chat_db` | `DATABASE_URL` | 主应用库 | t_user, t_chat_message, t_todo, t_metric_definition, t_meta_tables 等 |
| `data_db` | `ANALYTICS_DATABASE_URL` | 分析/数仓库（只读） | fdmdata.f_mid_dep_tb, fdmdata.f_mid_index_result, sdmdata.* 等业务数据表 |

重要规则：
1. MCP postgres 工具默认连接 `chat_db`，查不到 `fdmdata.*` 或 `sdmdata.*` 的表
2. 查询分析库数据时，必须通过 Python 脚本连接 `ANALYTICS_DATABASE_URL`，不能用 MCP postgres 工具
3. 代码中 `analytics_engine`（见 `app/db/session.py`）连接的是 `data_db`
4. `vanna.run_sql()` 执行在 `data_db` 上

### 数据现状（2026-02-07）

- `data_db` 中 fdmdata/sdmdata schema 已有数据（日期 20250630）
- f_mid_index_result: 172,498 行（1277 个指标）
- f_mid_dep_tb: 3,969,646 行
- f_mid_loan_k_tb: 1,579,387 行

## 5. Python 代码风格（修改 `**/*.py` 时遵循）

### 命名规范
- 文件名: `snake_case` (chat_service.py)
- 类名: `PascalCase` (ChatService)
- 变量/函数: `snake_case` (get_user_by_id)
- 常量: `UPPER_SNAKE_CASE` (MAX_RETRY_COUNT)

### 注释规范
- 所有注释使用中文
- 模块顶部必须有 docstring：`"""模块说明。"""`
- 禁止"修复/优化"过程注释，禁止 emoji

### 类型安全
- 完全使用 Type Hints
- ORM 使用 SQLAlchemy 2.0 `Mapped[...]` 语法

### 数据库规范
- 表名以 `t_` 开头
- 字段名 `snake_case`

### 代码位置
| 类型 | 目录 |
|-----|------|
| HTTP 接口 | `app/api/v1/endpoints/` |
| 业务逻辑 | `app/services/` |
| 数据库操作 | `app/repositories/` |
| AI 工具 | `app/ai/tools/` |
| 智能体 | `app/ai/agents/` |

## 6. TypeScript/React 代码风格（修改 `**/*.ts` / `**/*.tsx` 时遵循）

### 基本要求
- 严格使用 TypeScript，避免 `any`
- 注释使用中文
- 禁止 emoji 注释

### 代码位置
| 类型 | 目录 |
|-----|------|
| 组件 | `web/src/components/` |
| Hooks | `web/src/hooks/` |
| API | `web/src/lib/` |
| 类型 | `web/src/types/` |

## 7. LangGraph 开发规范（修改 `app/ai/**` 时遵循）

### 图架构（强约束）

所有 Workflow 必须遵循 Pre -> Core -> Post 三段式：

```
START -> Preprocess -> AgentCore -> Postprocess -> END
```

- Preprocess: 消息验证、上下文注入、安全护栏
- AgentCore: LLM 推理与工具调用
- Postprocess: 数据库持久化、资源清理（禁止跳过）

### 多智能体架构

- 禁止添加独立 `intent_classify` 节点
- 意图识别由 Supervisor 统一处理

### State 管理

```python
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: Optional[int]
    thread_id: Optional[str]
```

- 必须使用 `add_messages` reducer
- State 必须可序列化（否则 checkpointer 失败）

### 流式输出

- 使用 `astream_events(version="v2")`
- 输出转换为 `AgentEvent` 标准格式
- 禁止直接 yield 原始 chunk

### 消息持久化（强约束）

#### 保存时机与职责

| 场景 | 组件 | 保存内容 | 标记 |
|------|------|---------|------|
| interrupt 时 | `sse_stream` | Human + 中间 AI | `metadata.is_intermediate: true` |
| resume 完成 | `_postprocess` | 最终 AI 消息 | 无标记 |

#### 中间消息过滤

- `get_messages_by_thread(exclude_intermediate=True)` 默认过滤中间消息
- 中间消息通过 `metadata->>'is_intermediate' = 'true'` 标记
- 参考：LangGraph 官方 Agent Chat UI 的 `do-not-render-` 前缀机制

#### 禁止事项

- 禁止在 `sse_resume_stream` 中保存 AI 消息（会与 postprocess 重复）
- 禁止绕过 `_postprocess` 直接保存最终消息

### 禁止事项

- 禁止跳过 Pre/Post 节点
- 禁止使用 legacy AgentExecutor
- 禁止在 Node 中直接 print
- 禁止存储不可序列化对象
- 禁止在 Service 层直接保存 AI 消息（由 Postprocess 统一处理）

### 参考实现

- 单 Agent: `app/ai/workflow/chat_graph.py`
- 多 Agent: `app/ai/workflow/multi_agent_graph.py`

## 8. 多轮对话安全（修改 `app/ai/**` 时遵循）

### 禁止修改（高风险）

修改前必须询问用户确认：
- `app/ai/prompts/agent_prompts.py` - Agent Prompt
- `app/ai/state.py` - State 定义
- `*_graph.py` 中的 preprocess/postprocess 节点

### 核心原则

1. 只处理最新请求: AI 只回答最后一条 HumanMessage
2. 历史作为上下文: 不重复处理已回答的问题
3. Prompt 必须包含: "多轮对话处理规则"章节

### LangGraph 行为（禁止修改）

```python
# add_messages 自动追加消息到历史
messages: Annotated[Sequence[BaseMessage], add_messages]
```

### 常见问题

| 症状 | 原因 | 检查 |
|-----|------|-----|
| 重复回答第一轮问题 | Prompt 缺少多轮规则 | SUPERVISOR_PROMPT |
| 历史过长超时 | Context Pruning 被修改 | trim_messages 调用 |
| Checkpointer 异常 | State 存储不可序列化对象 | State 定义 |

## 9. 文档同步规则

### 文档结构统一原则

> 核心理念: 需求、设计、测试文档按功能模块对应，形成可追溯的文档矩阵。
> 2026-02-02 更新: 产品文档与需求文档已合并，统一放在 `产品文档/` 目录。

#### 功能模块对应关系

| 功能模块 | 需求文档 | 设计文档 | 测试文档 |
|---------|---------|---------|---------|
| 聊天系统 | 聊天系统需求.md | 后端架构.md | 聊天系统测试案例.md |
| 多智能体 | 系统需求.md §6 | AI模块设计.md | 测试用例库 §2 |
| 待办助手 | 待办助手需求.md | 待办Agent设计.md | 待办助手测试案例.md |
| 问数助手 | 问数助手需求.md | 问数引擎设计.md | 问数引擎测试案例.md |
| 管理后台 | 管理后台需求.md | 后端架构.md | 管理后台测试案例.md |
| 用户管理 | 用户管理需求.md | 后端架构.md | 用户管理测试案例.md |

#### 目录结构规范

```
docs/
├── 产品文档/                # 需求与产品说明（单一真理来源）
│   ├── 系统需求.md          # 全局功能列表 + 产品概述
│   ├── 待办助手需求.md
│   ├── 聊天系统需求.md
│   ├── 问数助手需求.md
│   ├── 管理后台需求.md
│   ├── 用户管理需求.md
│   └── 模型路由需求.md
├── 开发文档/
│   ├── 架构设计/            # 设计文档
│   └── 测试管理/
│       ├── 测试用例库.md    # 按功能模块组织的用例
│       ├── 测试指南与环境配置.md
│       ├── {模块}测试案例.md # 详细用例
│       └── 测试报告/        # 报告类归档
└── 内部参考/
    └── 迭代需求/            # 当前冲刺需求（Delta）
```

#### 命名规范

- 统一使用中文命名
- 测试案例: `{模块名}测试案例.md`
- 测试报告: `{模块名}测试报告.md` 或 `{模块名}测试报告_YYYYMMDD_{主题}.md` 或 `{模块名}测试报告_YYYY-MM-DD_{主题}.md`
- 禁止新增旧命名：`测试报告_{场景}_{日期}.md` 或仅日期无主题后缀

### 何时更新文档

涉及以下任务时，先更新文档，再修改代码：
- 架构变更
- 新增功能/模块
- API 接口变更
- 数据库表结构变更
- 新增或调整特殊处理（兜底逻辑、兼容补丁、临时绕过、历史债务）

### 设计文档映射

| 代码变更 | 更新文档 |
|---------|---------|
| `app/ai/workflow/` | `docs/开发文档/架构设计/AI模块设计.md` |
| `app/ai/tools/` | `docs/开发文档/架构设计/AI模块设计.md` |
| `app/ai/semantic/` | `docs/开发文档/架构设计/问数引擎设计.md` |
| `app/api/` | `docs/API文档/接口文档.md` |
| `app/models/` | `docs/开发文档/架构设计/数据库设计.md` |
| `web/src/components/` | `docs/开发文档/架构设计/前端架构.md` |
| 环境变量 | `docs/开发文档/快速入门/配置说明.md` + `.env.example` |
| 特殊处理（兜底逻辑/兼容补丁/临时绕过） | `docs/开发文档/架构设计/防屎山记录手册.md` |

### 需求文档映射

| 功能逻辑变更 | 更新文档 |
|-------------|---------|
| 待办助手相关 | `docs/产品文档/待办助手需求.md` |
| 聊天系统相关 | `docs/产品文档/聊天系统需求.md` |
| 管理后台相关 | `docs/产品文档/管理后台需求.md` |
| 问数助手相关 | `docs/产品文档/问数助手需求.md` |
| 用户管理相关 | `docs/产品文档/用户管理需求.md` |

### 测试文档映射

| 测试行为变更 | 更新文档 |
|-------------|---------|
| 待办助手测试 | `docs/开发文档/测试管理/待办助手测试案例.md` |
| 聊天系统测试 | `docs/开发文档/测试管理/聊天系统测试案例.md` |
| 管理后台测试 | `docs/开发文档/测试管理/管理后台测试案例.md` |
| 问数引擎测试 | `docs/开发文档/测试管理/问数引擎测试案例.md` |
| 用户管理测试 | `docs/开发文档/测试管理/用户管理测试案例.md` |
| 追溯矩阵 | `docs/开发文档/测试管理/测试用例库.md` |

### 特殊处理记录映射（防屎山）

| 变更类型 | 同步要求 |
|---------|---------|
| 新增特殊处理 | 新增 SP 编号，并补全"问题描述/涉及文件/风险/优化方向" |
| 调整已有特殊处理 | 更新对应 SP 条目的"最后更新"、状态与涉及文件 |
| 删除特殊处理 | 标记 SP 条目为"已修复"或"已废弃"，保留历史记录 |

### 测试脚本双向同步规则

> 核心原则: 测试案例文档 <-> E2E 脚本必须双向追溯。

| 变更类型 | 同步要求 |
|---------|---------|
| 新增测试脚本 | 在对应测试案例.md 第 0 节"自动化覆盖"列添加映射 |
| 新增测试用例 | 脚本开头添加 `@test-case` 和 `@see` 注释 |
| 删除/重命名脚本 | 同步更新测试案例文档中的映射表 |
| 修改用例覆盖范围 | 同时更新脚本注释和文档映射表 |

脚本模板规范（每个新测试脚本必须包含）:

```javascript
/**
 * [功能描述]
 *
 * @test-case TC-XXX-01 [用例名称]
 * @test-case TC-XXX-02 [用例名称]
 * @see docs/开发文档/测试管理/[模块]测试案例.md
 */
```

脚本与文档位置对应:

| 脚本目录 | 文档位置 |
|---------|---------|
| `web/e2e/todo*.spec.cjs` | `待办助手测试案例.md` |
| `web/e2e/chat*.spec.cjs` | `聊天系统测试案例.md` |
| `web/e2e/data*.spec.cjs` | `问数引擎测试案例.md` |
| `web/e2e/features/*.feature.cjs` | 对应模块测试案例.md |

### 跳过条件

- 用户说"直接改代码"
- 纯格式化/重构（不改功能）
- 简单 Bug 修复（不涉及设计）

### 执行流程

```
分析需求 -> 识别文档 -> 更新文档 -> 确认 -> 编写代码
```

## 10. 执行上下文校验

当任务涉及修改代码/运行测试/构建/数据迁移时，必须先校验：
- `pwd` / `git rev-parse --show-toplevel` / `git branch --show-current` / `git worktree list`
- 若任务已给定目标分支或 worktree，必须与校验结果一致；不一致时立即停止
- 若任务未给定目标分支或 worktree，先回传校验结果，再继续后续执行
- 命令优先使用显式路径（如 `pnpm -C web ...`）

纯问答、方案讨论、文档阅读类任务可跳过

## 11. 端口

- 前端 (Next.js): `3000`
- 后端 (FastAPI): `8000`
