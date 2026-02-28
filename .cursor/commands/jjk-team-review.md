---
description: Team 封装命令：执行 /prompts:jjk-review（自动同步源命令）
---
<!-- AUTO-GENERATED: jjk-team-bridge -->
<!-- source: jjk-review.md -->
<!-- source_sha1: 85a5f2834c670c8b95d77b69e5ab331478648e9e -->

# Team 命令封装（`/jjk-team-review`）

将 `/jjk-review` 封装为 Team 入口，且始终以源命令文档为唯一真理源。

## 使用方式

在命令后可选补充：

1. `workers=<N>`（默认建议 5）
2. `role=<agent_type>`（默认建议 `code-reviewer`）
3. `mode=ralph|team`（默认建议 `ralph`）
4. 任务正文（你希望 AI 完成什么）

示例：

```text
/jjk-team-review workers=5 role=code-reviewer mode=ralph
任务：<在这里写你的任务目标>
```

## 执行协议（强制）

1. 先读取源文件：`.cursor/commands/jjk-review.md`，严格沿用其约束与产物要求。
2. 以 Team 方式组织执行，并显式执行：`/prompts:jjk-review`。
3. 禁止把 `/jjk-review` 当普通文本描述。
4. 每一步回传：`命令原文 + 产物绝对路径 + 校验结果(PASS/FAIL)`。

## 源命令元数据（自动同步）

| 字段 | 值 |
|---|---|
| source | `.cursor/commands/jjk-review.md` |
| source_sha8 | `85a5f283` |
| actual_prompt | `/prompts:jjk-review` |
| recommended_role | `code-reviewer` |
| description | 代码审查：功能验证 + 质量检查 + 安全审计 + 快速自测 |

## 同步机制

本文件由 `python3 scripts/sync_rules_to_cc.py --only commands` 自动生成。

当 `.cursor/commands/jjk-review.md` 变更后，重新执行同步脚本即可自动刷新本文件，并同步到：

1. `.claude/commands/jjk-team-review.md`（CC 端）
2. `~/.codex/prompts/jjk-team-review.md`（Codex 端）
