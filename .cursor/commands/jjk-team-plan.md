---
description: Team 封装命令：执行 /prompts:jjk-plan（自动同步源命令）
---
<!-- AUTO-GENERATED: jjk-team-bridge -->
<!-- source: jjk-plan.md -->
<!-- source_sha1: 44ab29c72ffa373845fdabf8d8f9383cbff8096e -->

# Team 命令封装（`/jjk-team-plan`）

将 `/jjk-plan` 封装为 Team 入口，且始终以源命令文档为唯一真理源。

## 使用方式

在命令后可选补充：

1. `workers=<N>`（默认建议 5）
2. `role=<agent_type>`（默认建议 `planner`）
3. `mode=ralph|team`（默认建议 `ralph`）
4. 任务正文（你希望 AI 完成什么）

示例：

```text
/jjk-team-plan workers=5 role=planner mode=ralph
任务：<在这里写你的任务目标>
```

## 执行协议（强制）

1. 先读取源文件：`.cursor/commands/jjk-plan.md`，严格沿用其约束与产物要求。
2. 以 Team 方式组织执行，并显式执行：`/prompts:jjk-plan`。
3. 禁止把 `/jjk-plan` 当普通文本描述。
4. 每一步回传：`命令原文 + 产物绝对路径 + 校验结果(PASS/FAIL)`。

## 源命令元数据（自动同步）

| 字段 | 值 |
|---|---|
| source | `.cursor/commands/jjk-plan.md` |
| source_sha8 | `44ab29c7` |
| actual_prompt | `/prompts:jjk-plan` |
| recommended_role | `planner` |
| description | 正式规划：默认产出专题前缀需求与技术方案，可选生成并行 card_seed |

## 同步机制

本文件由 `python3 scripts/sync_rules_to_cc.py --only commands` 自动生成。

当 `.cursor/commands/jjk-plan.md` 变更后，重新执行同步脚本即可自动刷新本文件，并同步到：

1. `.claude/commands/jjk-team-plan.md`（CC 端）
2. `~/.codex/prompts/jjk-team-plan.md`（Codex 端）
