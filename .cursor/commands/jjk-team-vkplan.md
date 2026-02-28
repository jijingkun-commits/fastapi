---
description: Team 封装命令：执行 /prompts:jjk-vkplan（自动同步源命令）
---
<!-- AUTO-GENERATED: jjk-team-bridge -->
<!-- source: jjk-vkplan.md -->
<!-- source_sha1: c113eeb360a7c2355a052f6e2dbdf0d022877a07 -->

# Team 命令封装（`/jjk-team-vkplan`）

将 `/jjk-vkplan` 封装为 Team 入口，且始终以源命令文档为唯一真理源。

## 使用方式

在命令后可选补充：

1. `workers=<N>`（默认建议 5）
2. `role=<agent_type>`（默认建议 `planner`）
3. `mode=ralph|team`（默认建议 `ralph`）
4. 任务正文（你希望 AI 完成什么）

示例：

```text
/jjk-team-vkplan workers=5 role=planner mode=ralph
任务：<在这里写你的任务目标>
```

## 执行协议（强制）

1. 先读取源文件：`.cursor/commands/jjk-vkplan.md`，严格沿用其约束与产物要求。
2. 以 Team 方式组织执行，并显式执行：`/prompts:jjk-vkplan`。
3. 禁止把 `/jjk-vkplan` 当普通文本描述。
4. 每一步回传：`命令原文 + 产物绝对路径 + 校验结果(PASS/FAIL)`。

## 源命令元数据（自动同步）

| 字段 | 值 |
|---|---|
| source | `.cursor/commands/jjk-vkplan.md` |
| source_sha8 | `c113eeb3` |
| actual_prompt | `/prompts:jjk-vkplan` |
| recommended_role | `planner` |
| description | 并行拆解入口（消费 /jjk-plan 产物）：生成 WS 拆解与 vk_cards 执行契约 |

## 同步机制

本文件由 `python3 scripts/sync_rules_to_cc.py --only commands` 自动生成。

当 `.cursor/commands/jjk-vkplan.md` 变更后，重新执行同步脚本即可自动刷新本文件，并同步到：

1. `.claude/commands/jjk-team-vkplan.md`（CC 端）
2. `~/.codex/prompts/jjk-team-vkplan.md`（Codex 端）
