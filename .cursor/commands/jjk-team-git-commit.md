---
description: Team 封装命令：执行 /prompts:jjk-git-commit（自动同步源命令）
---
<!-- AUTO-GENERATED: jjk-team-bridge -->
<!-- source: jjk-git-commit.md -->
<!-- source_sha1: 84aa3e9ed8ec3b37d906da3ac5a1c7f371580cad -->

# Team 命令封装（`/jjk-team-git-commit`）

将 `/jjk-git-commit` 封装为 Team 入口，且始终以源命令文档为唯一真理源。

## 使用方式

在命令后可选补充：

1. `workers=<N>`（默认建议 5）
2. `role=<agent_type>`（默认建议 `git-master`）
3. `mode=ralph|team`（默认建议 `ralph`）
4. 任务正文（你希望 AI 完成什么）

示例：

```text
/jjk-team-git-commit workers=5 role=git-master mode=ralph
任务：<在这里写你的任务目标>
```

## 执行协议（强制）

1. 先读取源文件：`.cursor/commands/jjk-git-commit.md`，严格沿用其约束与产物要求。
2. 以 Team 方式组织执行，并显式执行：`/prompts:jjk-git-commit`。
3. 禁止把 `/jjk-git-commit` 当普通文本描述。
4. 每一步回传：`命令原文 + 产物绝对路径 + 校验结果(PASS/FAIL)`。

## 源命令元数据（自动同步）

| 字段 | 值 |
|---|---|
| source | `.cursor/commands/jjk-git-commit.md` |
| source_sha8 | `84aa3e9e` |
| actual_prompt | `/prompts:jjk-git-commit` |
| recommended_role | `git-master` |
| description | 📝 规范化 Git 提交：生成简洁、符合规范的 commit message |

## 同步机制

本文件由 `python3 scripts/sync_rules_to_cc.py --only commands` 自动生成。

当 `.cursor/commands/jjk-git-commit.md` 变更后，重新执行同步脚本即可自动刷新本文件，并同步到：

1. `.claude/commands/jjk-team-git-commit.md`（CC 端）
2. `~/.codex/prompts/jjk-team-git-commit.md`（Codex 端）
