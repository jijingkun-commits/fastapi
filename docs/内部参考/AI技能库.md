# AI 技能库

> 系统集成的 AI 技能包清单与追踪。
> **更新日期**: 2026-03-08
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

1. **数据库即唯一真理源**: 技能定义、版本、catalog metadata、向量与可见性统一维护在 `t_agent_skill_definitions` / `t_agent_skill_versions` / `t_user_skill_bindings`
2. **运行时只读 versioned 模型**: 聊天运行态 catalog、正文加载、管理面列表与详情统一读取 definition/version/binding 聚合视图
3. **`t_agent_skills` 不再参与正式主路径**: 该表仅保留历史兼容/调试遗留，不得作为导入、runtime、admin 的真理源
4. **本地 `SKILL.md` / 导入脚本已退役**: 禁止再通过 `app/ai/skills`、`scripts/data/import_skills.py` 或重启扫描回写数据库

## 6. Progressive Loader 运行时口径

- 首轮预装：`preprocess` 按当前用户可见范围构建 `skill_catalog_manifest / skill_catalog_context`
- 会话累积：模型通过 `load_skills` 显式加载正文，状态统一沉淀到 `loaded_skill_registry / loaded_skill_context`
- 回放 canonical：最终 AIMessage 统一写 `additional_kwargs.skill_runtime`，字段至少包含 `runtime_mode / catalog_version / visible_skill_count / loaded_skills / replay_source`
- 元数据字段：`catalog_path / catalog_order` 属于 definition 层；`catalog_description / when_to_use` 属于 version 层

---

## 7. 维护日志

- **2026-01-27**: 初始化引入核心开发包及办公三件套
