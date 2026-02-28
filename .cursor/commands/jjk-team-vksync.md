---
description: Team 封装命令：执行 /prompts:jjk-vksync（自动同步源命令）
---
<!-- AUTO-GENERATED: jjk-team-bridge -->
<!-- source: jjk-vksync.md -->
<!-- source_sha1: f2224afa27bf9d8b0c7f84675e959ab11144b802 -->

# Team 命令封装（`/jjk-team-vksync`）

将 `/jjk-vksync` 封装为 Team 入口，且始终以源命令文档为唯一真理源。

## 使用方式

在命令后可选补充：

1. `workers=<N>`（默认建议 5）
2. `role=<agent_type>`（默认建议 `planner`）
3. `mode=ralph|team`（默认建议 `ralph`）
4. 任务正文（你希望 AI 完成什么）

示例：

```text
/jjk-team-vksync workers=5 role=planner mode=ralph
任务：<在这里写你的任务目标>
```

## 执行协议（强制）

1. 先读取源文件：`.cursor/commands/jjk-vksync.md`，严格沿用其约束与产物要求。
2. 以 Team 方式组织执行，并显式执行：`/prompts:jjk-vksync`。
3. 禁止把 `/jjk-vksync` 当普通文本描述。
4. 每一步回传：`命令原文 + 产物绝对路径 + 校验结果(PASS/FAIL)`。

## 源命令元数据（自动同步）

| 字段 | 值 |
|---|---|
| source | `.cursor/commands/jjk-vksync.md` |
| source_sha8 | `f2224afa` |
| actual_prompt | `/prompts:jjk-vksync` |
| recommended_role | `planner` |
| description | VK 基线闸门入口（消费 /jjk-vkplan 产物）：多 worktree READY 校验与可控同步（check/apply） |

## 同步机制

本文件由 `python3 scripts/sync_rules_to_cc.py --only commands` 自动生成。

当 `.cursor/commands/jjk-vksync.md` 变更后，重新执行同步脚本即可自动刷新本文件，并同步到：

1. `.claude/commands/jjk-team-vksync.md`（CC 端）
2. `~/.codex/prompts/jjk-team-vksync.md`（Codex 端）
