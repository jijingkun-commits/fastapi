---
name: jjk-commit
description: "Use when you need `jjk-commit` in this repository. Source intent: Git 交付入口：提交当前分支并合并到 master（含上下文/证据/干净度门禁）"
---
<!-- AUTO-GENERATED: jjk-skill-mirror -->
<!-- source: .cursor/commands/jjk-commit.md -->

# 提交并合并到 master (Commit & Merge)

`$jjk-commit` 是 `jjk-*` 体系里的本地 Git 交付入口，负责把“当前 worktree 上的已验证改动”安全提交，并合并回仓库主工作区的 `master`。

> **中文主导**：无论是思考过程还是最终输出，**永远使用中文**。

## 输入前置（强制）

至少提供以下信息中的最小组合：

1. 目标分支默认是当前分支（禁止当前就在 `master`）；
2. 合并目标固定为本仓库 `master`；
3. 提交说明（commit message）或可生成 commit message 的变更摘要；
4. 任一验证证据：`acceptance_cmds`、`verify_report`、`review_report`、最近执行命令结果。

硬约束：

1. 当前分支为空、处于 detached HEAD、或当前就在 `master`，`FAIL_FAST` 输出 `COMMIT_BRANCH_INVALID`。
2. 缺少提交说明，`FAIL_FAST` 输出 `COMMIT_MESSAGE_MISSING`。
3. 缺少可追溯验证证据，`FAIL_FAST` 输出 `COMMIT_VERIFY_MISSING`。
4. 工作区存在与本次交付无关的脏改动，`FAIL_FAST` 输出 `COMMIT_WORKTREE_DIRTY`。
5. 仓库不存在主工作区 `master`，`FAIL_FAST` 输出 `COMMIT_MASTER_WORKTREE_MISSING`。
6. 当前分支已被其他 worktree 占用且无法安全收口时，`FAIL_FAST` 输出 `COMMIT_BRANCH_IN_USE`。

## 执行流程（强制顺序）

### 0) 先探索上下文（强制）

至少检查：

1. `pwd`、`git branch --show-current`、`git worktree list`；
2. 当前分支是否为非 `master` 的 feature/codex/vk 分支；
3. `master` 对应 worktree 路径、当前 worktree 路径、HEAD SHA；
4. 最近验证证据是否能覆盖本次改动范围。

### 1) 提交前门禁

1. 汇总 `git status --short`，确认只包含本次变更；
2. 检查是否已有未提交文档/测试遗漏；
3. 若命中文档同步规则，必须先完成文档回填；
4. 若需要测试，先执行针对性验证，再进入提交。

### 2) 生成并创建提交

1. 先给出提交摘要（按模块分组）；
2. 使用明确 commit message 创建原子提交；
3. 提交后回显 `commit_sha`、提交文件清单与摘要；
4. 禁止把无关改动打包进同一个提交。

### 3) 合并到主工作区 `master`

1. 在 `git worktree list` 中定位 `master` 对应 worktree；
2. 在 `master` worktree 内检查干净度与基线状态；
3. 将当前分支合并进 `master`（默认 `--ff-only`，若无法快进则明确提示并改走人工冲突处理）；
4. 合并成功后回显 `master` 新 HEAD 与 merge 结果。

### 4) 交付摘要

必须输出：

1. 当前分支名；
2. 提交 `commit_sha`；
3. `master` 合并后 `HEAD`；
4. 验证证据摘要；
5. 是否建议继续执行 `$jjk-deleteworktree` 做生命周期清理。

## 输出模板（推荐）

至少包含以下标题：

1. `## 上下文校验`
2. `## 提交门禁`
3. `## Commit 结果`
4. `## Merge 结果`
5. `## 后续动作`

## 禁止项（强制）

1. 禁止在 `master` 上直接开发后再用 `$jjk-commit` 伪装交付。
2. 禁止缺少验证证据就直接提交并合并。
3. 禁止默认使用 `--no-verify`、`--squash`、`--force` 等掩盖问题。
4. 禁止在 `master` worktree 脏状态下强行合并。
5. 禁止把删除 worktree / 删除分支职责混入本命令。

## 推荐链路

`$jjk-review -> $jjk-test -> $jjk-verify -> $jjk-commit -> $jjk-deleteworktree`

## 使用示例

```text
$jjk-commit
```

```text
$jjk-commit @docs/内部参考/迭代需求/review_report_xxx.md
```

---
*使用 `$jjk-commit` 触发。目标是“已验证改动的本地提交与主干合并收口”，不是“绕过验证的一键推平”。*
