---
description: Team 封装命令：执行 /prompts:jjk-debug（自动同步源命令）
---
<!-- AUTO-GENERATED: jjk-team-bridge -->
<!-- source: jjk-debug.md -->
<!-- source_sha1: e5278c4d7dd83ca642d207041963211c46d7c3f9 -->

# Team 命令封装（`/jjk-team-debug`）

将 `/jjk-debug` 封装为 Team 入口，且始终以源命令文档为唯一真理源。

## 使用方式

在命令后可选补充：

1. `workers=<N>`（默认建议 5）
2. `role=<agent_type>`（默认建议 `debugger`）
3. `mode=ralph|team`（默认建议 `ralph`）
4. 任务正文（你希望 AI 完成什么）

示例：

```text
/jjk-team-debug workers=5 role=debugger mode=ralph
任务：<在这里写你的任务目标>
```

## 执行协议（强制）

1. 先读取源文件：`.cursor/commands/jjk-debug.md`，严格沿用其约束与产物要求。
2. 以 Team 方式组织执行，并显式执行：`/prompts:jjk-debug`。
3. 禁止把 `/jjk-debug` 当普通文本描述。
4. 每一步回传：`命令原文 + 产物绝对路径 + 校验结果(PASS/FAIL)`。

## 源命令元数据（自动同步）

| 字段 | 值 |
|---|---|
| source | `.cursor/commands/jjk-debug.md` |
| source_sha8 | `e5278c4d` |
| actual_prompt | `/prompts:jjk-debug` |
| recommended_role | `debugger` |
| description | 问题排查：重现 -> 定位 -> 修复 -> 验证 -> 预防 |

## 同步机制

本文件由 `python3 scripts/sync_rules_to_cc.py --only commands` 自动生成。

当 `.cursor/commands/jjk-debug.md` 变更后，重新执行同步脚本即可自动刷新本文件，并同步到：

1. `.claude/commands/jjk-team-debug.md`（CC 端）
2. `~/.codex/prompts/jjk-team-debug.md`（Codex 端）
