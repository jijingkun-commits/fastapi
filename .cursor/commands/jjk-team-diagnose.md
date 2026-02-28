---
description: Team 封装命令：执行 /prompts:jjk-diagnose（自动同步源命令）
---
<!-- AUTO-GENERATED: jjk-team-bridge -->
<!-- source: jjk-diagnose.md -->
<!-- source_sha1: 416232562f512a6f44f54efd918ff2a25d47d1bf -->

# Team 命令封装（`/jjk-team-diagnose`）

将 `/jjk-diagnose` 封装为 Team 入口，且始终以源命令文档为唯一真理源。

## 使用方式

在命令后可选补充：

1. `workers=<N>`（默认建议 5）
2. `role=<agent_type>`（默认建议 `debugger`）
3. `mode=ralph|team`（默认建议 `ralph`）
4. 任务正文（你希望 AI 完成什么）

示例：

```text
/jjk-team-diagnose workers=5 role=debugger mode=ralph
任务：<在这里写你的任务目标>
```

## 执行协议（强制）

1. 先读取源文件：`.cursor/commands/jjk-diagnose.md`，严格沿用其约束与产物要求。
2. 以 Team 方式组织执行，并显式执行：`/prompts:jjk-diagnose`。
3. 禁止把 `/jjk-diagnose` 当普通文本描述。
4. 每一步回传：`命令原文 + 产物绝对路径 + 校验结果(PASS/FAIL)`。

## 源命令元数据（自动同步）

| 字段 | 值 |
|---|---|
| source | `.cursor/commands/jjk-diagnose.md` |
| source_sha8 | `41623256` |
| actual_prompt | `/prompts:jjk-diagnose` |
| recommended_role | `debugger` |
| description | 问题诊断：仅分析定位问题并产出修复计划（/jjk-pc 的规范别名） |

## 同步机制

本文件由 `python3 scripts/sync_rules_to_cc.py --only commands` 自动生成。

当 `.cursor/commands/jjk-diagnose.md` 变更后，重新执行同步脚本即可自动刷新本文件，并同步到：

1. `.claude/commands/jjk-team-diagnose.md`（CC 端）
2. `~/.codex/prompts/jjk-team-diagnose.md`（Codex 端）
