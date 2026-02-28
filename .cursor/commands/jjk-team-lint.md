---
description: Team 封装命令：执行 /prompts:jjk-lint（自动同步源命令）
---
<!-- AUTO-GENERATED: jjk-team-bridge -->
<!-- source: jjk-lint.md -->
<!-- source_sha1: 84c6f7a36a51350d25f82df73a8719940de31590 -->

# Team 命令封装（`/jjk-team-lint`）

将 `/jjk-lint` 封装为 Team 入口，且始终以源命令文档为唯一真理源。

## 使用方式

在命令后可选补充：

1. `workers=<N>`（默认建议 5）
2. `role=<agent_type>`（默认建议 `planner`）
3. `mode=ralph|team`（默认建议 `ralph`）
4. 任务正文（你希望 AI 完成什么）

示例：

```text
/jjk-team-lint workers=5 role=planner mode=ralph
任务：<在这里写你的任务目标>
```

## 执行协议（强制）

1. 先读取源文件：`.cursor/commands/jjk-lint.md`，严格沿用其约束与产物要求。
2. 以 Team 方式组织执行，并显式执行：`/prompts:jjk-lint`。
3. 禁止把 `/jjk-lint` 当普通文本描述。
4. 每一步回传：`命令原文 + 产物绝对路径 + 校验结果(PASS/FAIL)`。

## 源命令元数据（自动同步）

| 字段 | 值 |
|---|---|
| source | `.cursor/commands/jjk-lint.md` |
| source_sha8 | `84c6f7a3` |
| actual_prompt | `/prompts:jjk-lint` |
| recommended_role | `planner` |
| description | 代码规范检查与自动修复 |

## 同步机制

本文件由 `python3 scripts/sync_rules_to_cc.py --only commands` 自动生成。

当 `.cursor/commands/jjk-lint.md` 变更后，重新执行同步脚本即可自动刷新本文件，并同步到：

1. `.claude/commands/jjk-team-lint.md`（CC 端）
2. `~/.codex/prompts/jjk-team-lint.md`（Codex 端）
