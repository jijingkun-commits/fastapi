---
description: Team 封装命令：执行 /prompts:jjk-feature（自动同步源命令）
---
<!-- AUTO-GENERATED: jjk-team-bridge -->
<!-- source: jjk-feature.md -->
<!-- source_sha1: 8082dd3b3fd2a97f5c5926fee8b23d9410ee6cdd -->

# Team 命令封装（`/jjk-team-feature`）

将 `/jjk-feature` 封装为 Team 入口，且始终以源命令文档为唯一真理源。

## 使用方式

在命令后可选补充：

1. `workers=<N>`（默认建议 5）
2. `role=<agent_type>`（默认建议 `executor`）
3. `mode=ralph|team`（默认建议 `ralph`）
4. 任务正文（你希望 AI 完成什么）

示例：

```text
/jjk-team-feature workers=5 role=executor mode=ralph
任务：<在这里写你的任务目标>
```

## 执行协议（强制）

1. 先读取源文件：`.cursor/commands/jjk-feature.md`，严格沿用其约束与产物要求。
2. 以 Team 方式组织执行，并显式执行：`/prompts:jjk-feature`。
3. 禁止把 `/jjk-feature` 当普通文本描述。
4. 每一步回传：`命令原文 + 产物绝对路径 + 校验结果(PASS/FAIL)`。

## 源命令元数据（自动同步）

| 字段 | 值 |
|---|---|
| source | `.cursor/commands/jjk-feature.md` |
| source_sha8 | `8082dd3b` |
| actual_prompt | `/prompts:jjk-feature` |
| recommended_role | `executor` |
| description | 全流程开发入口（澄清->规划->实现->审查->验证）：单命令编排，禁止跳阶段 |

## 同步机制

本文件由 `python3 scripts/sync_rules_to_cc.py --only commands` 自动生成。

当 `.cursor/commands/jjk-feature.md` 变更后，重新执行同步脚本即可自动刷新本文件，并同步到：

1. `.claude/commands/jjk-team-feature.md`（CC 端）
2. `~/.codex/prompts/jjk-team-feature.md`（Codex 端）
