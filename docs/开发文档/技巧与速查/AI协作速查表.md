# 🤖 AI 协作速查表 (AI Collaboration Cheatsheet)

> **一句话原则**: 用 Slash Command (/) 触发流程，用 Artifact (@) 注入上下文。

## 1. 核心工作流 (Core Workflows)

| 阶段 | 你的动作 (Slash Command) | AI 的产出 (Artifact) | 你的下一步 |
|---|---|---|---|
| **想点子** | `/vibe-coding` | (无，纯对话) | 明确意图，准备规划 |
| **做规划** | `/plan` | `docs/需求文档/requirements.md` | **@引用此文件** 进行开发 |
| **写代码** | (直接对话) + `@requirements.md` | 代码变更 + 文档更新 | 审查代码 (Review) |
| **测功能** | `/test` | `docs/测试报告/` | 验收通过 (Green) |
| **修 Bug** | `/vibe-coding` (Review 阶段) | (无) | 针对性修改 |

---

## 2. 如何 "引用文档" (@Context)

不要把所有文档都扔给 AI。根据当前任务，只 `@` 最相关的那个：

### 场景 A：我要开发新功能
- 🟢 **必须引用**: `@requirements.md` (需求契约)
- ⚪ **可选引用**: `@相关代码文件`, `@数据库设计.md`

### 场景 B：我要修复 Bug
- 🟢 **必须引用**: `@报错日志` (或截图), `@疑似出问题的代码`
- ⚪ **可选引用**: `@requirements.md` (确认是否符合预期)

### 场景 C：我要写新的 API
- 🟢 **必须引用**: `@api-doc/SKILL.md` (格式规范), `@requirements.md`
- ⚪ **可选引用**: `@后端架构.md`

### 场景 D：使用 AI 技能 (Superpowers)
- 💡 **头脑风暴**: `@brainstorming` (我有想法但没细节)
- 🐛 **Python 调试**: `@python-debug` (代码报错求救)
- ⚛️ **前端开发**: `@react-best-practices` + `@tailwind-patterns`
- 🔒 **安全检查**: `@security-checklist`
- 🧪 **编写测试**: `@testing-patterns`

> 💡 **Tip**: 这里的 `api-doc/SKILL.md` 指的是物理文件路径。而在 Antigravity IDE 中，你可以直接尝试用自然语言（如 "Use python-expert to debug..."）或尝试 `@skills/python-expert` (取决于 IDE 版本支持)。

---

## 3. 常见误区 (Anti-Patterns)

- ❌ **误区 1**: "我只要 @文档编写规范.md，AI 就能写出好代码。"
    - **真相**: 规范只告诉 AI "格式" (Format)，不告诉 AI "内容" (Content)。你需要 `@requirements.md` 告诉它**做什么**。
- ❌ **误区 2**: "开发完了再补文档。"
    - **真相**: 遵循 Vibe Coding，**先**生成 `requirements.md`，**再**写代码。文档是 AI 的"导航图"。
- ❌ **误区 3**: "AI 写的代码不用看。"
    - **真相**: 你是 Tech Lead。AI 是实习生。**必须 Review**。

---

## 4. 常用指令速查

### 4.1 核心指令
- `/feature`: **全流程开发**。一键搞定 Plan + Imp + Review + Test。
    - *适用场景*: 任务较简单，或不希望手动分步执行时。
- `/plan` + `/imp` + `/review`: **分步开发模式**。
    - *适用场景*: 任务复杂，或者希望在每个阶段人工介入（例如：想在 Review 阶段切换模型以节省成本）。
- `/debug`: **标准排查流**。重现 -> 定位 -> 修复。

### 4.2 细分指令 (微操)
- `/plan`: 仅做规划 (生成 requirements.md)。
- `/implement` (或 `/imp`): 仅做实现 (代码 + 文档同步)。
- `/test`: 仅跑测试 (生成报告)。

> **💡 区别**: `/feature` = `/plan` + `/implement` + `/test`。
> 想省心用 `/feature`，想微操用细分指令。

### 4.3 其他
- `/run-dev`: 启动开发服务器
- `/langchain-agent-protection`: 查看 Agent 开发规范
