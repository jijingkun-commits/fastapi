---
description: Team 封装命令：执行 /prompts:jjk-create-pr（自动同步源命令）
---
<!-- AUTO-GENERATED: jjk-team-bridge -->
<!-- source: jjk-create-pr.md -->
<!-- source_sha1: fb1d1042884fc4dda995d186202ffa621465a95a -->

# Team 命令封装（`/jjk-team-create-pr`）

将 `/jjk-create-pr` 封装为 Team 入口，且始终以源命令文档为唯一真理源。

## 使用方式

在命令后可选补充：

1. `workers=<N>`（默认建议 5）
2. `role=<agent_type>`（默认建议 `git-master`）
3. `mode=ralph|team`（默认建议 `ralph`）
4. 任务正文（你希望 AI 完成什么）

示例：

```text
/jjk-team-create-pr workers=5 role=git-master mode=ralph
任务：<在这里写你的任务目标>
```

## 执行协议（强制）

1. 先读取源文件：`.cursor/commands/jjk-create-pr.md`，严格沿用其约束与产物要求。
2. 以 Team 方式组织执行，并显式执行：`/prompts:jjk-create-pr`。
3. 禁止把 `/jjk-create-pr` 当普通文本描述。
4. 每一步回传：`命令原文 + 产物绝对路径 + 校验结果(PASS/FAIL)`。

## 源命令元数据（自动同步）

| 字段 | 值 |
|---|---|
| source | `.cursor/commands/jjk-create-pr.md` |
| source_sha8 | `fb1d1042` |
| actual_prompt | `/prompts:jjk-create-pr` |
| recommended_role | `git-master` |
| description | PR 交付入口（消费 pr_ready_manifest）：校验任务映射与验收证据后创建/更新 Pull Request |

## 同步机制

本文件由 `python3 scripts/sync_rules_to_cc.py --only commands` 自动生成。

当 `.cursor/commands/jjk-create-pr.md` 变更后，重新执行同步脚本即可自动刷新本文件，并同步到：

1. `.claude/commands/jjk-team-create-pr.md`（CC 端）
2. `~/.codex/prompts/jjk-team-create-pr.md`（Codex 端）
