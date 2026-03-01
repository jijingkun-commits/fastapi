---
name: jjk-git-commit
description: "Use when you need `jjk-git-commit` in this repository. Source intent: 提交入口（消费 manifest/review）：生成可追溯 commit 并执行原子提交，支持大范围自动 Team"
---
<!-- AUTO-GENERATED: jjk-skill-mirror -->
<!-- source: .cursor/commands/jjk-git-commit.md -->

# Git 提交流程 (Git Commit Workflow)

`$jjk-git-commit` 是 `jjk-*` 体系里的提交入口，负责把已落地改动整理成可追溯、可复盘的 commit 资产。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 与 Superpowers / OMX 的分工（强制）

1. `git-master`：提供提交拆分、历史整洁与提交语义策略。
2. `verification-before-completion`：提供“先证据后宣称完成”的提交前门禁。
3. `$jjk-review`：提供阻断项状态（若有未闭环阻断项，不得提交）。
4. `team`（OMX）：大范围提交拆分并行分析与统一汇总。
5. `$jjk-git-commit`：负责输入追溯校验、提交分组、消息生成、执行与结果回填。

约束：

1. 禁止在 `$jjk-git-commit` 复制上游 skill 正文；仅保留调用契约与本地增强。
2. 禁止把 `$jjk-team-git-commit` 作为主入口，统一由 `$jjk-git-commit` 按规模自动升级 Team。
3. 禁止“无范围约束 git add -A 一把梭”；必须先锁定提交边界。

## 跨 IDE 调用方式

1. Cursor / Claude Code：`$jjk-git-commit`
2. Codex：`$jjk-git-commit`

> 说明：Codex 推荐显式调用 `$jjk-git-commit`。

## 模板来源优先级（跨项目，强制）

`$jjk-git-commit` 的模板按以下优先级读取：

1. 全局共享模板（默认主模板）：
   `/Users/jijingkun/.codex/engineering/templates/jjk_git_commit_templates.md`
2. 项目覆盖模板（仅放差异，不放全量复制）：
   `docs/内部参考/迭代需求/_templates/jjk_git_commit_templates.md`

若全局模板缺失，输出标记 `GLOBAL_TEMPLATE_MISSING` 并提示先初始化共享模板目录。
`GLOBAL_TEMPLATE_MISSING` 属于全局预检失败标记，可与命令级 `FAIL_FAST` 标记并存。

## 何时使用

| 场景 | 推荐命令 |
|---|---|
| 已完成实现并需要规范 commit | `$jjk-git-commit` ✅ |
| 仍在开发中，仅临时保存草稿 | `$jjk-imp`（继续实现，不建议提交） |
| 需要结构化审查结论 | `$jjk-review` |
| 需要最终验收结论 | `$jjk-verify` |

---

## 输入前置（强制）

至少提供以下输入之一：

1. `pr_ready_manifest` / `pr_ready_manifest_ws`；
2. `review_report_<topic>.md` + 本轮待提交文件；
3. 可追溯 `task_id`（`pr_id` 可选）的 `implementation_plan` + `git diff --cached`。

硬约束：

1. 若无已暂存变更（`git diff --cached` 为空），`FAIL_FAST` 输出 `GIT_COMMIT_NOTHING_STAGED`。
2. 若无法解析 `task_id`（`pr_id` 可选），`FAIL_FAST` 输出 `GIT_COMMIT_TRACE_MISSING`。
3. 若暂存文件超出输入范围（manifest/review 约束），`FAIL_FAST` 输出 `GIT_COMMIT_SCOPE_MISMATCH`。
4. 若存在未关闭阻断项（如 `P0/P1`），`FAIL_FAST` 输出 `GIT_COMMIT_BLOCKER_UNRESOLVED`。
5. 若提交前缺少最小验证证据（命令结果/测试摘要），`FAIL_FAST` 输出 `GIT_COMMIT_EVIDENCE_MISSING`。

## 执行流程（强制顺序）

### 0) 先探索上下文（强制）

至少检查：

1. 当前暂存文件与目标任务映射（`task_id -> files`）。
2. 最近审查/验证结论，确认不存在未关闭阻断项。
3. 本轮提交是否需要拆分为多个原子 commit。

### 0.5) 大范围提交自动启用 Team（强制判定）

触发条件（满足任一即可）：

1. 暂存文件 `>= 20`；
2. 拆分提交候选 `>= 3`；
3. 同时覆盖后端+前端+数据库/配置三类以上边界；
4. 需要并行梳理多个 `task_id` 的提交说明。

执行策略：

1. **有 Team 能力时**：并行整理提交分组与 message 草案，Leader 汇总最终提交序列。
2. **无 Team 能力时**：降级单代理执行，并输出 `TEAM_UNAVAILABLE_FALLBACK`。

### 1) 提交范围锁定

1. 以 `task_id` 为主键锁定文件范围，`pr_id` 仅作为补充追溯字段。
2. 对混杂暂存区执行分组，确保“一个 commit 一个明确意图”。
3. 无法归属的文件不得提交，需回退到实现阶段补齐追溯信息。

### 2) 生成 commit message（强制规范）

标题格式：

`<type>(<scope>): <summary>`

规则：

1. 标题长度建议 `<= 72` 字符；
2. 使用祈使句，首字母小写，结尾不加句号；
3. body 需包含最小追溯信息：`task_id`、`pr_id(可选)`、`关键验证命令`、`风险点`；
4. 如存在 issue key，可在首行前缀补充，但不得替代 `task_id`。

### 3) 提交前门禁

1. 复核 `acceptance_cmds` 或等价最小验证证据。
2. 复核 `git diff --cached --name-only` 与计划范围一致。
3. 门禁失败不得提交，并返回对应 `FAIL_FAST` 标记。

### 4) 执行提交与校验

1. 执行 `git commit`（必要时按分组多次执行）。
2. 校验提交结果：`commit sha`、文件清单、message 合规。
3. 提交失败时 `FAIL_FAST` 输出 `GIT_COMMIT_EXEC_FAILED`。

### 5) 产物回填与交接

必须输出：

1. `task_id -> commit sha` 映射（`pr_id` 可选补充）；
2. 每个 commit 的文件清单与验证证据引用；
3. 下一步建议命令（`$jjk-review`、`$jjk-verify`、`$jjk-create-pr`）。

---

## 输出模板（推荐）

见全局模板：`/Users/jijingkun/.codex/engineering/templates/jjk_git_commit_templates.md`（`输出模板` 段）。
若本项目有覆盖规则，再查：`docs/内部参考/迭代需求/_templates/jjk_git_commit_templates.md`。

## 禁止项（强制）

1. 禁止无追溯字段直接提交。
2. 禁止把多个无关任务硬塞进一个 commit。
3. 禁止在阻断项未关闭时提交“可发布”变更。
4. 禁止只给 message 不执行提交校验。

## 推荐链路

`$jjk-imp -> $jjk-git-commit -> $jjk-review -> $jjk-verify`

## 使用示例

```text
$jjk-git-commit
```

```text
$jjk-git-commit @docs/内部参考/迭代需求/review_report_<topic>.md
```

---
*使用 `$jjk-git-commit` 触发。目标是“可追溯原子提交”，不是机械生成一句 message。*
