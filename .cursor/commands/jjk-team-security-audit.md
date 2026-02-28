---
description: Team 封装命令：执行 /prompts:jjk-security-audit（自动同步源命令）
---
<!-- AUTO-GENERATED: jjk-team-bridge -->
<!-- source: jjk-security-audit.md -->
<!-- source_sha1: 0095ac2f502737e7c5b7fe1887f4530bce932b2d -->

# Team 命令封装（`/jjk-team-security-audit`）

将 `/jjk-security-audit` 封装为 Team 入口，且始终以源命令文档为唯一真理源。

## 使用方式

在命令后可选补充：

1. `workers=<N>`（默认建议 5）
2. `role=<agent_type>`（默认建议 `security-reviewer`）
3. `mode=ralph|team`（默认建议 `ralph`）
4. 任务正文（你希望 AI 完成什么）

示例：

```text
/jjk-team-security-audit workers=5 role=security-reviewer mode=ralph
任务：<在这里写你的任务目标>
```

## 执行协议（强制）

1. 先读取源文件：`.cursor/commands/jjk-security-audit.md`，严格沿用其约束与产物要求。
2. 以 Team 方式组织执行，并显式执行：`/prompts:jjk-security-audit`。
3. 禁止把 `/jjk-security-audit` 当普通文本描述。
4. 每一步回传：`命令原文 + 产物绝对路径 + 校验结果(PASS/FAIL)`。

## 源命令元数据（自动同步）

| 字段 | 值 |
|---|---|
| source | `.cursor/commands/jjk-security-audit.md` |
| source_sha8 | `0095ac2f` |
| actual_prompt | `/prompts:jjk-security-audit` |
| recommended_role | `security-reviewer` |
| description | 🔒 安全审计：检查依赖漏洞、代码安全、敏感信息泄露 |

## 同步机制

本文件由 `python3 scripts/sync_rules_to_cc.py --only commands` 自动生成。

当 `.cursor/commands/jjk-security-audit.md` 变更后，重新执行同步脚本即可自动刷新本文件，并同步到：

1. `.claude/commands/jjk-team-security-audit.md`（CC 端）
2. `~/.codex/prompts/jjk-team-security-audit.md`（Codex 端）
