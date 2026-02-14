# Vibe Coding 开发技巧

> **核心理念**: 用自然语言描述意图，让 AI 理解并实现。通过 Skills 增强 AI 能力，通过 Rules 规范 AI 行为。

**本文定位**：完整手册，详解 Skills、Commands、Rules 的原理、用法和项目配置。如果只需快速查阅命令列表，请看 [AI 协作速查表](AI协作速查表.md)。

## 0. 命令权威源与统计口径（2026-02-14 校准）

为保持“全量百科”定位且避免命令口径漂移，本文固定采用以下规则：

1. 命令细节权威源：`.cursor/commands/*.md`（对应 `authority_rule.commands_detail`）。
2. 本文职责：保留命令百科、场景建议与链路示例，不替代权威命令文档。
3. 统计口径：按 `.cursor/commands/` 目录文件计数，统计时间 `2026-02-14`，当前共 `26` 个命令文件。
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
想法 → /plan → requirements.md → /imp → 代码 → /test → 验收
```

| 阶段 | 命令 | 产出 | 说明 |
|------|------|------|------|
| **规划** | `/plan` | `requirements.md` | 明确需求和设计 |
| **实现** | `/imp` | 代码 + 文档 | AI 实现功能 |
| **测试** | `/test` | 测试报告 | 验证功能 |
| **调试** | `/debug` | 修复方案 | 排查问题 |
| **审查** | `/review` | 审查意见 | 代码质量检查 |
| **全流程** | `/feature` | 完整功能 | Plan + Imp + Test |

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
├─ 需求不明确，想先澄清
│   └─ /clarify （轻量问答，不产出文档）
│
├─ 需要正式的需求文档
│   └─ /plan （产出 requirements.md）
│
├─ 已有明确计划，只需编码
│   └─ /imp
│
├─ 完整的新功能开发
│   └─ /feature （= plan + imp + review）
│
├─ 代码写完了，需要审查
│   └─ /review （含快速自测）
│
├─ 需要完整的测试流程
│   └─ /test （用例生成、E2E、报告）
│
└─ 遇到 Bug 需要排查
    └─ /debug （重现、定位、修复、预防）
```

### 7.2 核心开发流程

| 命令 | 说明 | 产出物 |
|------|------|--------|
| `/clarify` | 快速澄清 - 通过问答确认理解，不产出文档 | 无 |
| `/plan` | 正式规划 - 产出需求文档和技术方案 | `requirements.md` |
| `/imp` | 代码实现 - 根据计划编写代码，同步文档 | 代码 + 文档 |
| `/review` | 代码审查 - 功能验证 + 质量检查 + 安全审计 + 快速自测 | 审查意见 |
| `/test` | 完整测试 - 用例生成、三重验证、报告产出 | `test_report.md` |
| `/debug` | 问题排查 - 重现、定位、修复、预防 | 修复 + 测试用例 |
| `/feature` | 全流程 - 一站式从需求到交付 (= plan + imp + review) | 全部 |

### 7.3 Git 工作流

标准化的 Git 操作流程，确保提交信息规范、PR 描述完整。

| 命令 | 说明 | 使用示例 |
|------|------|----------|
| `/git-commit` | 规范化提交 - 自动分析变更并生成符合规范的提交信息 | `/git-commit` |
| `/create-pr` | 创建 PR - 生成完整的 PR 描述，包含变更摘要和测试计划 | `/create-pr` |

### 7.4 代码质量

提升代码质量的工具集，包括规范检查、重构、优化和安全审计。

| 命令 | 说明 | 使用示例 |
|------|------|----------|
| `/lint` | 代码规范检查 - 运行 ruff/eslint 并自动修复问题 | `/lint @app/services/` |
| `/refactor` | 代码重构 - 在保持功能不变的前提下改善代码结构 | `/refactor @app/services/chat_service.py` |
| `/deslop` | 清理 AI 冗余代码 - 移除不必要的复杂性和过度工程 | `/deslop` |
| `/optimize` | 性能优化 - 分析瓶颈并提供优化方案 | `/optimize 这个查询很慢` |
| `/error-handling` | 添加错误处理 - 为代码添加健壮的异常处理和验证 | `/error-handling @app/api/` |
| `/security-audit` | 安全审计 - 检查注入漏洞、认证问题、数据泄露风险 | `/security-audit` |

### 7.5 数据库

数据库相关的操作命令，确保迁移安全可回滚。

| 命令 | 说明 | 使用示例 |
|------|------|----------|
| `/migration` | 数据库迁移 - 创建带回滚脚本的迁移文件，自动更新文档 | `/migration 添加 user_profile 表` |

### 7.6 文档与可视化

自动生成文档和架构图，保持文档与代码同步。

| 命令 | 说明 | 使用示例 |
|------|------|----------|
| `/diagrams` | 生成 Mermaid 图 - 支持流程图、时序图、类图、ER 图等 | `/diagrams 画一下聊天系统时序图` |
| `/api-docs` | 生成 API 文档 - 根据代码自动生成接口文档 | `/api-docs @app/api/v1/endpoints/` |
| `/doc-check` | 文档同步检查 - 检测代码变更是否有对应文档更新 | `/doc-check`（建议在 git commit 前执行） |

### 7.7 并行与看板协作

用于多 AI / 多 worktree 并行开发，核心链路为 `/plan -> /vkplan -> /vktodo（或 /vkkb） -> /imp-ws`。

| 命令 | 说明 | 使用示例 |
|------|------|----------|
| `/vkplan` | 并行拆解入口 - 在 `/plan` 后生成 `parallel_plan.md`、`workstreams/WS-*.md`、`vk_cards.json` | `/vkplan` |
| `/vksync` | 基线同步检查 - 校验 `WS-00` 是否已进入各并行 worktree 基线 | `/vksync 2026-02-14_文档治理执行 check` |
| `/vk` | 看板导出 - 审阅 `card_export` 组装结果（默认 `strict`） | `/vk 2026-02-14_文档治理执行` |
| `/vktodo` | 批量建卡/推进 - 默认执行基线硬拦截并支持本地后端兜底 | `/vktodo 2026-02-14_文档治理执行 move Doing` |
| `/vkkb` | 看板一体命令 - 自动补导出并调用 `/vktodo` 落卡 | `/vkkb 2026-02-14_文档治理执行` |
| `/imp-ws` | 子任务实现 - 按单个 `WS-*.md` 白名单执行并回填自检卡 | `/imp-ws @workstreams/WS-02_命令权威源与百科校准.md` |

### 7.8 问题诊断（只分析不改码）

| 命令 | 说明 | 使用示例 |
|------|------|----------|
| `/pc` | 问题诊断 - 只做根因分析并产出 `fix_plan.md`，不改代码（命令文档内示例触发词为 `/diagnose`） | `/pc 生产环境出现 500 错误` |

---

## 8. 快捷命令总览

```bash
# === Skills 管理 ===
npx ai-agent-skills browse          # 交互式浏览
npx ai-agent-skills list            # 列出所有
npx ai-agent-skills install <name>  # 安装
npx ai-agent-skills update --all    # 更新全部

# === Commands（在聊天中输入）===

# 核心开发流程 - 覆盖完整开发周期
/clarify       # 通过问答澄清需求，避免返工
/plan          # 生成 requirements.md 和技术方案
/imp           # 根据计划编写代码，自动同步文档
/test          # 全链路测试：环境准备、用例生成、执行验证
/debug         # 重现、定位、修复、记录的标准排查流程
/review        # 检查代码质量、文档同步、规范遵循
/feature       # 一站式完成从需求到交付的全流程
/pc            # 仅诊断并输出 fix_plan（命令文档示例触发词 /diagnose）

# 并行与看板 - 多 worktree 协作
/vkplan        # 在 /plan 后执行并行拆解并产出 vk_cards.json
/vkkb          # 一条命令完成导出 + 落卡（可选继续 move）
/vktodo        # 批量建卡/推进，默认执行基线硬拦截
/vksync        # 手动执行 G0 基线同步检查（check/apply）
/vk            # 导出看板 payload（strict/auto）
/imp-ws        # 按单个 WS 白名单执行实现与回填

# Git 工作流 - 标准化的版本控制操作
/git-commit    # 自动分析变更并生成规范提交信息
/create-pr     # 生成完整 PR 描述，含变更摘要和测试计划

# 代码质量 - 提升代码健壮性
/lint          # 运行 ruff/eslint 并自动修复问题
/refactor      # 在保持功能不变的前提下改善代码结构
/deslop        # 移除 AI 生成的不必要复杂性
/optimize      # 分析性能瓶颈并提供优化方案
/error-handling # 添加健壮的异常处理和输入验证
/security-audit # 检查注入漏洞、认证问题、数据泄露

# 数据库 - 安全的数据库操作
/migration     # 创建带回滚脚本的迁移文件

# 文档与可视化 - 保持文档同步
/diagrams      # 生成 Mermaid 图（流程图、时序图、ER 图等）
/api-docs      # 根据代码自动生成接口文档
/doc-check     # 检查代码变更是否有对应文档更新

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

### 9.2 Commands（26 个）

```
.cursor/commands/
├── api-docs.md        # 生成 API 文档
├── clarify.md         # 快速澄清需求
├── create-pr.md       # 创建 PR
├── debug.md           # 调试问题
├── deslop.md          # 清理 AI 冗余代码
├── diagrams.md        # 生成 Mermaid 图表
├── doc-check.md       # 文档同步检查
├── error-handling.md  # 添加错误处理
├── feature.md         # 全流程开发
├── git-commit.md      # 规范化提交
├── imp-ws.md          # 子任务实现（WS）
├── imp.md             # 实现代码
├── lint.md            # 代码规范检查
├── migration.md       # 数据库迁移
├── optimize.md        # 性能优化
├── pc.md              # 问题诊断（命令文档示例触发词 /diagnose）
├── plan.md            # 需求规划
├── refactor.md        # 代码重构
├── review.md          # 代码审查
├── security-audit.md  # 安全审计
├── test.md            # 运行测试
├── vk.md              # 看板导出
├── vkkb.md            # 看板一体落地
├── vkplan.md          # 并行拆解
├── vksync.md          # 基线同步检查
└── vktodo.md          # 批量建卡/推进
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
