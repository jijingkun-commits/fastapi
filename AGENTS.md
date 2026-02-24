# 项目代理工作指南（Codex / Cursor 补充）

共有规则见 `PROJECT_RULES.md`（本文件仅包含 Cursor / Codex 特有的补充内容）。

## 1) 规则来源与适用范围

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

## 2) /命令 兼容（Cursor Commands -> Codex）

当用户输入 `/xxx` 或明确提到同名工作流时：

1. 若存在 `.cursor/commands/xxx.md`，先读取该文件；
2. 按该文件步骤执行（分析/改码/验证/文档）；
3. 若命令与当前任务冲突，以用户当前明确要求为准。

常用映射示例：

- `/jjk-plan` -> `.cursor/commands/jjk-plan.md`
- `/jjk-imp` -> `.cursor/commands/jjk-imp.md`
- `/jjk-debug` -> `.cursor/commands/jjk-debug.md`
- `/jjk-review` -> `.cursor/commands/jjk-review.md`
- `/jjk-test` -> `.cursor/commands/jjk-test.md`
- `/jjk-doc-check` -> `.cursor/commands/jjk-doc-check.md`

## 3) 技能目录

若用户要求使用本地技能，优先从以下目录读取 `SKILL.md`：
- `.cursor/skills/`
- `.agent/skills/skills/`

仅加载与当前任务直接相关的技能文件，避免全量读取。
