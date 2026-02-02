# AI 技能库

> 系统集成的 AI 技能包清单与追踪。
> **更新日期**: 2026-01-27
> **当前总数**: 24 个

---

## 1. 核心精选 (Core)

这些技能是根据项目技术栈 (FastAPI, React, LangGraph) 特别挑选的架构级知识。

| Skill ID | 类别 | 说明 |
|---|---|---|
| `api-patterns` | Backend | API 设计决策树 |
| `python-patterns` | Backend | Python 最佳实践与设计模式 |
| `database-design` | Backend | 数据库模型设计原则 |
| `react-best-practices` | Frontend | React 性能优化指南 |
| `ui-ux-pro-max` | Frontend | 高级 UI/UX 交互模式 |
| `frontend-dev-guidelines` | Frontend | 前端工程化规范 |
| `langgraph` | Agent | LangGraph 状态机与多智能体模式 |
| `ai-agents-architect` | Agent | 智能体架构设计方法论 |
| `testing-patterns` | Quality | 测试策略与模式 |
| `clean-code` | Quality | 代码整洁之道 |
| `software-architecture` | Architecture | 软件架构通用原则 |
| `tailwind-patterns` | Frontend | Tailwind CSS 使用规范 |

---

## 2. 基础工具 (Basic)

| Skill ID | 说明 | 来源 |
|---|---|---|
| `meeting-minutes` | 会议纪要整理专家 | awesome-cursorrules |
| `code-review` | 代码审查助手 | awesome-cursorrules |
| `translator` | 中英互译专家 | 自定义 |
| `sql-expert` | SQL 编写专家 | awesome-cursorrules |
| `python-debug` | Python 调试助手 | awesome-cursorrules |
| `regex-wizard` | 正则表达式生成器 | awesome-cursorrules |
| `data-insight` | 数据洞察分析 | 自定义 |
| `email-pro` | 商务邮件助手 | 自定义 |
| `copywriter` | 文案润色专家 | 自定义 |
| `git-commit` | Git Commit Msg 生成 | awesome-cursorrules |
| `api-doc` | API 文档生成 | 自定义 |

---

## 3. 开发技能

| 技能 ID | 说明 | 来源目录 |
|---|---|---|
| `fastapi-expert` | FastAPI 最佳实践 | `python-fastapi-best-practices` |
| `nextjs-expert` | Next.js App Router 栈 | `nextjs-app-router` |
| `python-expert` | Python 通用开发规范 | `python-best-practices` |
| `git-expert` | Git 提交消息规范 | `git-conventional-commit-messages` |
| `technical-writer` | 技术文档写作 | `kubernetes-mkdocs-documentation` |

---

## 4. 使用方式

Agent 会根据用户 Query 的语义相似度自动挂载相关技能。

**示例**:
- 用户问: *"帮我设计一个高并发的用户积分表"*
- 触发: 自动检索到 `database-design` 和 `sql-expert`
- 效果: Agent 在回答时会参考 "3NF 范式" 和 "索引优化" 等专业知识

---

## 5. 同步机制

1. **文件即真理**: 所有技能源文件位于 `app/ai/skills/<skill-id>/SKILL.md`
2. **自动同步**: 应用启动时 (`app/main.py:lifespan`) 自动扫描目录，同步到 `t_agent_skills` 表
3. **手动维护**: 更新技能请直接修改 `SKILL.md` 文件，然后重启应用

---

## 6. 维护日志

- **2026-01-27**: 初始化引入核心开发包及办公三件套
