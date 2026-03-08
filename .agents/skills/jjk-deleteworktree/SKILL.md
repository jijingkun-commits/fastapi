---
name: jjk-deleteworktree
description: "Use when you need `jjk-deleteworktree` in this repository. Source intent: 生命周期清理入口：删除当前分支及其 worktree（含合并状态与上下文门禁）"
---
<!-- AUTO-GENERATED: jjk-skill-mirror -->
<!-- source: .cursor/commands/jjk-deleteworktree.md -->

# 删除当前分支与 worktree (Delete Worktree)

`$jjk-deleteworktree` 是 `jjk-*` 体系里的 Git 生命周期清理入口，负责在当前 worktree 任务已完成后，安全删除“当前分支 + 当前 worktree”。

> **中文主导**：无论是思考过程还是最终输出，**永远使用中文**。

## 输入前置（强制）

至少提供以下信息中的最小组合：

1. 当前 worktree 路径；
2. 当前分支名；
3. 已完成交付的证据（至少其一）：`$jjk-commit` 结果、merge 结果、verify 结论、用户显式允许删除。

硬约束：

1. 当前路径若是主仓库根工作区或 `master` worktree，`FAIL_FAST` 输出 `DELETE_WORKTREE_PRIMARY_FORBIDDEN`。
2. 当前分支为空、detached HEAD、或仍被其他 worktree 占用，`FAIL_FAST` 输出 `DELETE_WORKTREE_BRANCH_INVALID`。
3. 当前分支尚未并入 `master`，`FAIL_FAST` 输出 `DELETE_WORKTREE_NOT_MERGED`。
4. 当前 worktree 有未提交改动，`FAIL_FAST` 输出 `DELETE_WORKTREE_DIRTY`。
5. 缺少删除授权或交付证据，`FAIL_FAST` 输出 `DELETE_WORKTREE_EVIDENCE_MISSING`。

## 执行流程（强制顺序）

### 0) 先探索上下文（强制）

至少检查：

1. `pwd`、`git branch --show-current`、`git worktree list`；
2. 当前 worktree 是否为可删除的附加 worktree；
3. 当前分支是否已合并到 `master`；
4. 是否还有其他 worktree 持有同一分支。

### 1) 删除前门禁

1. 校验当前 worktree 干净度；
2. 校验 `master` 中已包含当前分支 HEAD；
3. 若只满足“已提交未合并”，阻断并提示先执行 `$jjk-commit`；
4. 若用户要求强删，必须明确指出风险与回退困难，不默认执行。

### 2) 删除当前 worktree

1. 从非当前 worktree 位置执行删除（避免在被删除目录内自删）；
2. 删除当前附加 worktree；
3. 回显被删除路径与结果。

### 3) 删除当前分支

1. 在确认分支已合并后，删除本地分支；
2. 回显删除结果；
3. 若删除失败，保留 worktree 删除结果并明确剩余风险。

### 4) 清理摘要

必须输出：

1. 删除的 worktree 路径；
2. 删除的分支名；
3. 合并校验依据；
4. 残余风险（如分支删除失败、其他 worktree 占用等）。

## 输出模板（推荐）

至少包含以下标题：

1. `## 上下文校验`
2. `## 删除门禁`
3. `## Worktree 删除结果`
4. `## Branch 删除结果`
5. `## 残余风险`

## 禁止项（强制）

1. 禁止删除主仓库根工作区或 `master` worktree。
2. 禁止在未合并到 `master` 前删除当前分支。
3. 禁止把“强制删除”作为默认路径。
4. 禁止在当前目录内直接执行自删而不先切出到安全目录。
5. 禁止顺手删除其他无关 worktree 或分支。

## 推荐链路

`$jjk-commit -> $jjk-deleteworktree`

## 使用示例

```text
$jjk-deleteworktree
```

```text
$jjk-deleteworktree @docs/内部参考/迭代需求/review_report_xxx.md
```

---
*使用 `$jjk-deleteworktree` 触发。目标是“完成交付后的生命周期清理”，不是“图省事的强删命令包装器”。*
