# Vibe Coding 开发技巧

> **核心理念**: 用自然语言描述意图，让 AI 理解并实现。通过 Skills 增强 AI 能力，通过 Rules 规范 AI 行为。

**本文定位**：完整手册，详解 Skills、Commands、Rules 的原理、用法和项目配置。如果只需快速查阅命令列表，请看 [AI 协作速查表](AI协作速查表.md)。

## 0. 命令权威源与统计口径（2026-03-06 校准）

为保持“全量百科”定位且避免命令口径漂移，本文固定采用以下规则：

1. 命令细节权威源：`.cursor/commands/*.md`（对应 `authority_rule.commands_detail`）。
   - 运行时镜像：`.claude/commands/*.md`（Claude Code）与 `~/.codex/prompts/*.md`（Codex）。
   - 触发方式：Claude Code / Cursor 用 `/jjk-xxx`；Codex 用 `/prompts:jjk-xxx`。
2. 本文职责：保留命令百科、场景建议与链路示例，不替代权威命令文档。
3. 统计口径：按 `.cursor/commands/*.md` 文件计数（不含 `.bak`），统计时间 `2026-03-06`，当前共 `17` 个命令文件。
4. 冲突裁决：若本文与 `AI协作速查表.md`、`VibeKanban多Worktree本机开发测试.md`、或其他消费文档冲突，一律以对应 `.cursor/commands/*.md` 为准。

## 1. Cursor Skills 使用指南

### 1.1 已安装的 Skills

本项目已安装以下 Skills（位于 `.cursor/skills/`）：

| Skill | 用途 | 使用场景 |
|-------|------|----------|
| `python-development` | Python 3.12+ 开发最佳实践 | FastAPI、异步编程、类型提示 |
| `javascript-typescript` | ES6+/TypeScript 开发 | Next.js、React 前端开发 |
| `frontend-design` | UI 组件和样式 | 界面设计、Tailwind CSS |
| `llm-application-dev` | LLM 应用开发 | RAG、Prompt Engineering |
| `database-design` | 数据库设计和优化 | SQLAlchemy、PostgreSQL |
| `webapp-testing` | Playwright 测试 | E2E 测试、自动化测试 |
| `code-review` | 代码审查 | PR Review、质量检查 |
| `code-refactoring` | 代码重构 | 优化代码结构 |
| `skill-creator` | 创建新 Skill | 扩展 AI 能力 |

### 1.2 如何使用 Skills

在 Cursor 中，Skills 会根据上下文自动激活。你也可以在对话中提及：

```text
"使用 python-development skill 帮我优化这段 FastAPI 代码"
```

### 1.3 AI Agent Skills CLI 详解

#### 什么是 AI Agent Skills CLI？

AI Agent Skills CLI 是一个类似 npm 的**包管理器**，专门用于管理 AI agent 的技能。它可以：
- 从中央仓库安装 skills 到本地项目
- 更新已安装的 skills
- 支持多种 AI agent（Cursor、Claude Code、Copilot 等）

#### 架构说明

```
┌─────────────────────────────────────────────────────────┐
│                    GitHub 仓库                          │
│  https://github.com/skillcreatorai/Ai-Agent-Skills     │
│                                                         │
│  skills/                                                │
│  ├── python-development/SKILL.md                       │
│  ├── frontend-design/SKILL.md                          │
│  ├── llm-application-dev/SKILL.md                      │
│  └── ... (50+ skills)                                  │
└─────────────────────────────────────────────────────────┘
                           │
                           │ npx ai-agent-skills install
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    你的项目                              │
│  .cursor/skills/     (安装到这里)                       │
│  ├── python-development/SKILL.md                       │
│  ├── javascript-typescript/SKILL.md                    │
│  └── ...                                                │
└─────────────────────────────────────────────────────────┘
```

#### 管理命令

```bash
# 浏览所有可用 skills（交互式 TUI）
npx ai-agent-skills browse

# 列出已安装的 skills
npx ai-agent-skills list --installed --agent cursor

# 安装新 skill
npx ai-agent-skills install <skill-name> --agent cursor

# 从 GitHub 仓库安装
npx ai-agent-skills install github-username/repo-name --agent cursor

# 更新所有 skills
npx ai-agent-skills update --all

# 搜索特定 skill
npx ai-agent-skills search <keyword>

# 查看 skill 详情
npx ai-agent-skills info <skill-name>
```

#### Skills 资源

| 资源 | 地址 | 说明 |
|------|------|------|
| **主仓库** | https://github.com/skillcreatorai/Ai-Agent-Skills | 50+ Skills 集合 |
| **市场** | https://www.agentskills.in/marketplace | 可视化浏览和安装 |
| **官方示例** | https://github.com/anthropics/skills | Anthropic 官方 Skills |

---

## 2. Vibe Coding 工作流

### 2.1 核心流程

```
想法 → /jjk-clarify（设计冻结 + PRD-Lite） → /jjk-plan → requirements.md + implementation_plan.md
     → /jjk-imp（或 /jjk-vkplan -> /jjk-cardrun） → /jjk-verify → 验收
                                                （或 /jjk-review → /jjk-test → 验收）
```

`/jjk-clarify` 支持在同一命令内完成探索与冻结（不强制前置 `brainstorming`）。

| 阶段 | 命令 | 产出 | 说明 |
|------|------|------|------|
| **澄清冻结** | `/jjk-clarify` | `design.md` + `design_freeze_summary` + `clarify_handoff_contract` | 开发前冻结边界/语义/回退口径 |
| **规划** | `/jjk-plan` | `requirements.md` + `implementation_plan.md` | 形成 WHAT + HOW，可直接承接实现 |
| **实现** | `/jjk-imp` | 代码 + 文档 | AI 实现功能 |
| **一站式验证** | `/jjk-verify` | 验证报告 | 审查 + 测试 + 交互式 UAT |
| **测试** | `/jjk-test` | 测试报告 | 验证功能 |
| **调试** | `/jjk-debug` | 修复方案 | 排查问题 |
| **审查** | `/jjk-review` | 审查意见 | 代码质量检查 |
| **并行拆解** | `/jjk-vkplan` + `/jjk-cardrun` | `parallel_plan` + 卡片执行证据 | 多任务并行与串行收口 |

### 2.1.1 Clarify v3.2 必过门禁（工程模式）

开发前必须满足：

1. `product_contract`（PRD-Lite）完整：`target_users/core_scenarios/business_goals/non_goals/acceptance_gates`。
2. `design_freeze_summary.product_contract_ready=true`。
3. `clarify_consistency_check.clarify_phase=approval` 且 `open_questions_count=0`。
4. 条件采纳（`design_approved=false`）不得进入 `/jjk-plan`。
5. 修改 `jjk-clarify` 命令/模板后执行：`python3 scripts/check_clarify_contract_consistency.py`。
6. 建议执行：`python3 scripts/check_clarify_plan_alignment.py --requirements-path ... --implementation-path ...` 做桥接校验。

### 2.2 上下文引用策略

通过 `@` 符号引用上下文，让 AI 更精准理解任务：

```
# 开发新功能
@requirements.md @app/services/chat_service.py
"根据需求实现聊天消息保存功能"

# 修复 Bug
@错误日志 @相关代码文件
"帮我分析这个 NoneType 错误"

# 参考架构
@docs/开发文档/架构设计/后端架构.md
"在现有架构基础上添加缓存层"
```

---

## 3. 项目特定技巧

### 3.1 后端开发 (FastAPI + LangGraph)

```python
# 使用 Repository 模式
# @app/repositories/chat_repo.py 是参考模板

# 使用 Service 层处理业务逻辑
# @app/services/chat_service.py 是参考模板

# LangGraph 相关开发
# 使用 context7 MCP 查询最新 API
```

**常用 Prompt**:
- "帮我创建一个新的 API 端点，参考 @app/api/v1/endpoints/chat_api.py 的模式"
- "使用 llm-application-dev skill 帮我设计 RAG 流程"
- "参考 @.cursor/rules/langgraph.mdc 规范实现 Agent 节点"

### 3.2 前端开发 (Next.js + React)

```typescript
// 组件开发参考 @web/src/components/
// Hook 开发参考 @web/src/hooks/
// API 调用参考 @web/src/lib/backend.ts
```

**常用 Prompt**:
- "使用 frontend-design skill 帮我设计一个聊天界面组件"
- "参考 @web/src/hooks/useSSEStream.ts 实现流式响应"
- "用 Tailwind CSS 美化这个表单"

### 3.3 数据库操作

```python
# 模型定义参考 @app/models/
# 使用 SQLAlchemy 2.0 async 模式
# 参考 @docs/开发文档/架构设计/数据库设计.md
```

**常用 Prompt**:
- "使用 database-design skill 帮我设计这个表结构"
- "帮我写一个复杂查询，需要 JOIN 三个表"
- "这个 SQL 需要添加索引吗？"

---

## 4. Skills 高级用法

### 4.1 组合使用多个 Skills

```
# 全栈功能开发
"使用 python-development 和 javascript-typescript skills，
帮我实现一个完整的用户认证功能，包括后端 API 和前端组件"

# LLM + 测试
"使用 llm-application-dev 实现 RAG 查询功能，
然后用 webapp-testing skill 生成测试用例"
```

### 4.2 创建项目专属 Skill

使用 `skill-creator` skill 创建自定义技能：

```bash
# 在 .cursor/skills/ 下创建新目录
mkdir -p .cursor/skills/my-custom-skill

# 创建 SKILL.md
```

SKILL.md 模板：

```markdown
---
name: my-custom-skill
description: 项目专属技能描述
---

# 技能名称

## 使用场景
描述何时使用此技能

## 指导原则
1. 规则一
2. 规则二

## 代码模板
\`\`\`python
# 示例代码
\`\`\`
```

### 4.3 Skills vs Rules 的区别

| 特性 | Skills | Rules |
|------|--------|-------|
| **位置** | `.cursor/skills/` | `.cursor/rules/` |
| **格式** | `SKILL.md` | `*.mdc` |
| **激活方式** | 按需加载、手动调用 | 始终激活、自动应用 |
| **用途** | 领域专家知识、操作指南 | 代码规范、项目约定 |
| **示例** | Python 开发最佳实践 | 变量命名规范 |

---

## 5. 常见问题排查

### 5.1 Skill 不生效

```bash
# 检查 skill 是否正确安装
ls -la .cursor/skills/

# 重新安装
npx ai-agent-skills install <skill-name> --agent cursor
```

### 5.2 更新 Skills 到最新版本

```bash
# 更新单个 skill
npx ai-agent-skills update <skill-name>

# 更新所有 skills
npx ai-agent-skills update --all
```

### 5.3 从 GitHub 安装自定义 Skill

```bash
# 从 GitHub 仓库安装
npx ai-agent-skills install github-username/repo-name --agent cursor

# 从特定路径安装
npx ai-agent-skills install github-username/repo-name/skills/my-skill --agent cursor
```

---

## 6. 推荐资源

### 6.1 Skills 资源库

- **AI Agent Skills**: https://github.com/skillcreatorai/Ai-Agent-Skills
- **Skill 市场**: https://www.agentskills.in/marketplace
- **Awesome Cursorrules**: https://github.com/PatrickJS/awesome-cursorrules

### 6.2 本项目规则文件

| 规则 | 路径 | 说明 |
|------|------|------|
| 核心规则 | `.cursor/rules/core.mdc` | 基本原则和技术栈 |
| Python 风格 | `.cursor/rules/python_style.mdc` | Python 代码规范 |
| TypeScript 风格 | `.cursor/rules/typescript_style.mdc` | TS 代码规范 |
| LangGraph | `.cursor/rules/langgraph.mdc` | Agent 开发规范 |
| 对话安全 | `.cursor/rules/conversation_safety.mdc` | 会话处理规范 |
| 文档同步 | `.cursor/rules/doc_sync.mdc` | 代码文档同步规则 |

---

## 7. Commands 详解

### 7.0 什么是 Commands？

Commands 是 Cursor 的**可复用工作流**功能，通过 `/` 前缀在聊天中触发。

#### 存储位置

| 类型 | 位置 | 说明 |
|------|------|------|
| **项目级** | `.cursor/commands/` | 随项目版本控制 |
| **全局** | `~/.cursor/commands/` | 个人所有项目可用 |
| **团队级** | Cursor Dashboard | Team/Enterprise 计划 |

#### 命令格式

每个命令是一个 `.md` 文件，包含 YAML 头部和 Markdown 内容：

```markdown
---
description: 命令的简短描述
---

# 命令标题

## 步骤
1. 步骤一
2. 步骤二

## 检查清单
- [ ] 检查项
```

#### Commands 资源

| 资源 | 地址 | 说明 |
|------|------|------|
| **官方文档** | https://cursor.com/docs/context/commands | Cursor Commands 官方文档 |
| **命令集合** | https://github.com/hamzafer/cursor-commands | 527+ stars，30+ 命令 |
| **规则集合** | https://github.com/PatrickJS/awesome-cursorrules | 37k+ stars |

---

### 7.1 命令选择指南

> **不知道用哪个命令？看这里！**

```
你的场景是什么？
│
├─ 需求还模糊，也直接进入澄清
│   └─ /jjk-clarify （命令内先探索再冻结；历史 /ask 会重定向到这里）
│
├─ 需要冻结边界与验收口径
│   └─ /jjk-clarify
│
├─ 需要正式规划文档
│   └─ /jjk-plan （core/parallel）
│
├─ 已有计划，执行单任务实现
│   └─ /jjk-imp
│
├─ 需要隔离环境执行实现
│   └─ /jjk-wtimp
│
├─ 需要并行拆解与收口
│   └─ /jjk-vkplan -> /jjk-vktodo create -> /jjk-cardrun loop
│
├─ 单个工作包（WS）实现
│   └─ /jjk-imp-ws
│
├─ 代码写完了，需要验收
│   └─ /jjk-verify （或 /jjk-review -> /jjk-test）
│
└─ 遇到 Bug 需要排查
    └─ /jjk-debug （结构治理用 /jjk-refactor）
```

### 7.2 核心开发流程

| 命令 | 说明 | 产出物 |
|------|------|--------|
| `/ask` | 兼容入口（已降级），触发后立即并入 `/jjk-clarify` | 无独立权威产物 |
| `/jjk-clarify` | 设计冻结入口（默认收敛），沉淀 `design_freeze_summary + clarify_handoff_contract` | `design.md` |
| `/jjk-plan` | 正式规划入口（`core/parallel`），产出需求与实现方案 | `requirements.md` + `implementation_plan.md` |
| `/jjk-imp` | 标准实现入口，按计划改码并同步必要文档 | 代码 + 文档 |
| `/jjk-wtimp` | worktree 隔离实现入口，适合中大改动 | 隔离实现证据 + 合并结果 |
| `/jjk-vkplan` | 并行拆解入口，生成可执行卡片契约 | `parallel_plan.md` + `vk_cards.json` |
| `/jjk-vktodo` | create-only 幂等建卡，不负责状态推进 | VK 卡片 |
| `/jjk-cardrun` | 串行卡片执行与收口（`verify -> merge -> done`） | 卡片执行轨迹 + merge 证据 |
| `/jjk-imp-ws` | 单个 WS 白名单实现并回填自检卡 | WS 实现证据 |
| `/jjk-review` | 代码审查与风险分级 | 审查报告 |
| `/jjk-test` | 测试执行与报告沉淀 | 测试报告 |
| `/jjk-verify` | 一站式验收（审查 + 测试 + UAT） | 验收结论 |
| `/jjk-debug` | 系统化问题排查与最小修复 | 修复说明 + 验证证据 |
| `/jjk-refactor` | 行为等价重构与结构治理 | 重构结果 + 验证证据 |
| `/jjk-create-pr` | PR 交付入口（消费 `pr_ready_manifest`） | PR 链接 + 交付摘要 |

### 7.3 Git 工作流

聚焦“实现完成后的交付收口”：

| 命令 | 说明 | 使用示例 |
|------|------|----------|
| `/jjk-create-pr` | 创建/更新 PR，校验任务映射与验收证据 | `/jjk-create-pr` |

### 7.4 代码质量

优先采用“审查 + 测试 + 验收 + 根因修复”的闭环。

| 命令 | 说明 | 使用示例 |
|------|------|----------|
| `/jjk-review` | 结构化代码审查，定位高风险点 | `/jjk-review` |
| `/jjk-test` | 执行测试矩阵并输出测试报告 | `/jjk-test` |
| `/jjk-verify` | 审查 + 测试 + UAT 一体化验收 | `/jjk-verify` |
| `/jjk-debug` | 出现缺陷时做根因定位与最小修复 | `/jjk-debug` |
| `/jjk-refactor` | 行为等价重构，降低复杂度与重复 | `/jjk-refactor @app/services/chat_service.py` |

### 7.5 数据库

数据库改动统一走标准研发链路（`/jjk-plan -> /jjk-imp -> /jjk-test -> /jjk-verify`），不再维护独立数据库迁移命令入口。

### 7.6 文档同步

文档同步已并入标准研发链路，不再维护独立文档命令。

| 入口/命令 | 说明 | 使用示例 |
|------|------|----------|
| `/jjk-imp` | 实现阶段同步必要文档变更 | `/jjk-imp` |
| `/jjk-review` | 审查阶段检查文档-代码一致性 | `/jjk-review` |
| `/jjk-verify` | 验收阶段做最终文档收口确认 | `/jjk-verify` |
| `python3 scripts/check_clarify_plan_alignment.py ...` | Clarify/Plan 契约一致性校验 | `python3 scripts/check_clarify_plan_alignment.py --requirements-path ... --implementation-path ...` |

### 7.7 并行与看板协作

用于多 AI / 多 worktree 协作，核心链路为 `/jjk-plan -> /jjk-vkplan -> /jjk-vktodo(create-only) -> /jjk-cardrun(loop)`。

| 命令 | 说明 | 使用示例 |
|------|------|----------|
| `/jjk-vkplan` | 并行拆解入口 - 在 `/jjk-plan` 后生成 `parallel_plan.md`、`workstreams/WS-*.md`、`vk_cards.json` | `/jjk-vkplan` |
| `/jjk-vktodo` | create-only 幂等建卡 - 消费 `vk_cards.json` 落卡，不负责状态推进 | `/jjk-vktodo 2026-02-14_文档治理执行 create` |
| `/jjk-cardrun` | 串行执行调度 - 消费 `vk_cards.json` 按 `card_order` 单活卡推进并执行 `verify -> merge -> done` | `/jjk-cardrun 2026-03-01_用户个性化永久记忆与管理能力 loop` |
| `/jjk-imp-ws` | 子任务实现 - 按单个 `WS-*.md` 白名单执行并回填自检卡 | `/jjk-imp-ws @workstreams/WS-02_命令权威源与百科校准.md` |
| `python3 scripts/check_gate_contract_consistency.py --task-split-dir ...` | G01 契约一致性校验 | `python3 scripts/check_gate_contract_consistency.py --task-split-dir <任务拆解目录>` |
| `python3 scripts/coder4/check_integration_gate.py --task-split-dir ... --baseline master` | IG01 集成门禁校验 | `python3 scripts/coder4/check_integration_gate.py --task-split-dir <任务拆解目录> --baseline master` |

### 7.8 通用命令补充（非 JJK 主链）

| 命令 | 说明 | 使用示例 |
|------|------|----------|
| `/plan` | 通用实施规划，输出 `docs/plans/...` 计划文档 | `/plan` |
| `/do` | 按已有计划执行实现、测试与审查 | `/do` |

---

## 8. 快捷命令总览

```bash
# === Skills 管理 ===
npx ai-agent-skills browse          # 交互式浏览
npx ai-agent-skills list            # 列出所有
npx ai-agent-skills install <name>  # 安装
npx ai-agent-skills update --all    # 更新全部

# === Commands（在聊天中输入）===

# 发散与冻结
/ask               # 兼容别名（已降级），会立即转入 /jjk-clarify
/jjk-clarify       # 设计冻结 + handoff 契约（含 PRD-Lite）
/jjk-plan          # 生成 requirements + implementation_plan（core/parallel）

# 并行与看板 - 多 worktree 协作
/jjk-vkplan        # 在 /jjk-plan 后执行并行拆解并产出 vk_cards.json
/jjk-vktodo        # create-only 落卡（不做 move/review/done）
/jjk-cardrun       # 按 card_order 串行推进，并执行 verify->merge->done 收口
/jjk-imp-ws        # 按单个 WS 白名单执行实现与回填

# 单任务实现与隔离实现
/jjk-imp           # 标准实现入口（不隔离）
/jjk-wtimp         # worktree 隔离实现（适合中大改动）

# 审查、测试、验收与治理
/jjk-review        # 代码审查与风险分级
/jjk-test          # 执行测试矩阵并产出报告
/jjk-verify        # 一站式验收（审查 + 测试 + UAT）
/jjk-debug         # 问题重现、定位、修复与预防
/jjk-refactor      # 行为等价重构与结构治理

# 交付与通用补充
/jjk-create-pr     # 创建/更新 PR，校验交付证据
/plan              # 通用规划命令（非 JJK 主链）
/do                # 通用执行命令（非 JJK 主链）

# === 上下文引用 ===
@文件路径                            # 引用文件
@目录路径/                           # 引用目录
@skill-name                         # 引用技能
```

---

## 9. 本项目配置一览

### 9.1 Skills（9 个）

```
.cursor/skills/
├── code-refactoring/      # 代码重构技术
├── code-review/           # 自动化 PR 审查
├── database-design/       # 数据库设计优化
├── frontend-design/       # UI 组件和样式
├── javascript-typescript/ # JS/TS 开发
├── llm-application-dev/   # LLM 应用开发
├── python-development/    # Python 最佳实践
├── skill-creator/         # 创建新 Skill
└── webapp-testing/        # Playwright 测试
```

### 9.2 Commands（17 个）

```
.cursor/commands/
├── ask.md                 # 兼容入口（已降级，立即并入 jjk-clarify）
├── do.md                  # 通用执行实施
├── jjk-cardrun.md         # 串行卡片执行调度
├── jjk-clarify.md         # 设计冻结 + handoff 契约
├── jjk-create-pr.md       # PR 交付入口
├── jjk-debug.md           # 调试问题
├── jjk-imp-ws.md          # 子任务实现（WS）
├── jjk-imp.md             # 实现代码
├── jjk-plan.md            # 正式规划入口（core/parallel）
├── jjk-refactor.md        # 代码重构
├── jjk-review.md          # 代码审查
├── jjk-test.md            # 运行测试
├── jjk-verify.md          # 一站式验证（审查 + 测试 + UAT）
├── jjk-vkplan.md          # 并行拆解
├── jjk-vktodo.md          # create-only 幂等建卡
├── jjk-wtimp.md           # Worktree 隔离编码
└── plan.md                # 通用实施规划
```

### 9.3 Rules（8 个）

```
.cursor/rules/
├── banking-context.mdc     # 银行业务上下文约束
├── conversation_safety.mdc # 会话处理规范
├── core.mdc                # 核心原则和技术栈
├── doc_sync.mdc            # 代码文档同步规则
├── dual-database.mdc       # 双数据库边界约束
├── langgraph.mdc           # Agent 开发规范
├── python_style.mdc        # Python 代码规范
└── typescript_style.mdc    # TypeScript 代码规范
```

---

> **提示**: 善用 Skills + Rules + Commands + Context，让 AI 成为你的超级编程搭档！
