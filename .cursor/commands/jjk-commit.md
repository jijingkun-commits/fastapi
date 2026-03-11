---
description: Git 交付编排入口：提交当前分支并通过 shared delivery engine 收口到 master（含上下文/证据/干净度门禁）
---

# 提交并收口到 master (Commit & Delivery)

`/jjk-commit` 是 `jjk-*` 体系里的本地 Git 交付编排入口，负责把“当前 worktree 上的已验证改动”提交为原子 commit，并委托 shared delivery engine 把当前分支安全收口到仓库主干 `master`。

> **中文主导**：无论是思考过程还是最终输出，**永远使用中文**。

## 输入前置（强制）

至少提供以下信息中的最小组合：

1. 目标分支默认是当前分支（禁止当前就在 `master`）；
2. 基线分支固定为本仓库 `master`；
3. 提交说明（commit message）或可生成 commit message 的变更摘要；
4. 任一验证证据：`acceptance_cmds`、`verify_report`、`review_report`、最近执行命令结果；
5. 可选模式：`--dry-run`、`--status`、`--continue`、`--abort`。

硬约束：

1. 当前分支为空、处于 detached HEAD、或当前就在 `master`，`FAIL_FAST` 输出 `COMMIT_BRANCH_INVALID`。
2. 默认提交模式下缺少提交说明，`FAIL_FAST` 输出 `COMMIT_MESSAGE_MISSING`。
3. 默认提交模式下缺少可追溯验证证据，`FAIL_FAST` 输出 `COMMIT_VERIFY_MISSING`。
4. 工作区存在与本次交付无关的脏改动，`FAIL_FAST` 输出 `COMMIT_WORKTREE_DIRTY`。
5. 调用 `--continue` / `--abort` 时不存在进行中的 delivery 上下文，`FAIL_FAST` 输出 `DELIVERY_NOT_IN_PROGRESS`。
6. shared delivery engine 无法准备 `master` checkout 或无法解析基线上下文，`FAIL_FAST` 输出 `DELIVERY_BASE_UNAVAILABLE`。

## 执行模式（强制）

### 默认模式

- 先做上下文与门禁校验；
- 若当前改动尚未提交，则创建原子 commit；
- 然后调用 shared delivery engine 执行 `merge`；
- engine 统一负责：准备 `master` checkout、处理 `rebase / merge / abort`、输出结构化结果；
- `jjk-commit` 只负责回显人类可读交付摘要。

### 恢复模式

1. `--status`：查看当前 delivery 是否处于 `rebase_conflict`、`merge_conflict` 或 idle；
2. `--continue`：在用户手动解决冲突后，继续当前 delivery；
3. `--abort`：中止当前 delivery，并清理 engine 元数据；
4. `--dry-run`：仅校验上下文、证据、脏状态和基线可达性，不创建 commit、不执行 merge。

## 执行流程（强制顺序）

### 0) 先探索上下文（强制）

补充执行约束：执行命令时统一遵循 `.cursor/rules/core.mdc` 的“命令执行拆分”规则：单步单目标、失败只重跑当前步、长任务只轮询不重启、输出截断时优先拆短当前步。

至少检查：

1. `pwd`、`git branch --show-current`、`git worktree list`；
2. 当前分支是否为非 `master` 的 feature/codex/vk 分支；
3. 当前 worktree 路径、仓库根目录、HEAD SHA；
4. 最近验证证据是否能覆盖本次改动范围；
5. 当前是否已有进行中的 delivery 恢复上下文。

### 1) 提交前门禁

1. 汇总 `git status --short`，确认只包含本次变更；
2. 检查是否已有未提交文档/测试遗漏；
3. 若命中文档同步规则，必须先完成文档回填；
4. 若需要测试，先执行针对性验证，再进入提交；
5. 若是恢复模式，跳过“创建 commit”，直接进入 engine 恢复分支。

### 2) 生成并创建提交（默认模式）

1. 先给出提交摘要（按模块分组）；
2. 使用明确 commit message 创建原子提交；
3. 提交后回显 `commit_sha`、提交文件清单与摘要；
4. 禁止把无关改动打包进同一个提交。

### 3) 委托 shared delivery engine 收口到 `master`

1. 调用 engine `prepare-base` 解析或创建 `master` checkout；
2. 调用 engine `merge` 执行 `rebase -> merge --no-ff` 默认策略；
3. 若 `rebase` 或 `merge` 发生冲突，engine 负责保留进行中的 Git 状态与恢复上下文，不再自动 `abort`；
4. 若用户已手动解决冲突，则通过 `--continue` 继续，或通过 `--abort` 显式退出；
5. 合并成功后回显 `master` 新 HEAD、delivery 状态与冲突恢复信息（若有）。

### 4) 交付摘要

必须输出：

1. 当前分支名；
2. `commit_sha`（若本轮创建了新提交）；
3. `master` 收口后的 `HEAD`；
4. 验证证据摘要；
5. delivery 状态（`merged` / `rebase_conflict` / `merge_conflict` / `idle`）；
6. 是否建议继续执行 `/jjk-deleteworktree` 做生命周期清理。

## 输出模板（推荐）

至少包含以下标题：

1. `## 上下文校验`
2. `## 提交门禁`
3. `## Commit 结果`
4. `## Delivery 结果`
5. `## 恢复动作`
6. `## 后续动作`

## 禁止项（强制）

1. 禁止在 `master` 上直接开发后再用 `/jjk-commit` 伪装交付。
2. 禁止缺少验证证据就直接提交并收口。
3. 禁止默认使用 `--no-verify`、`--squash`、`--force` 等掩盖问题。
4. 禁止继续在命令层重复定义一套 `rebase/merge` 策略，绕过 shared delivery engine。
5. 禁止把删除 worktree / 删除分支职责混入本命令。

## 推荐链路

`/jjk-review -> /jjk-test -> /jjk-verify -> /jjk-commit -> /jjk-deleteworktree`

## 使用示例

```text
/jjk-commit
```

```text
/jjk-commit --dry-run
```

```text
/jjk-commit --status
```

```text
/jjk-commit --continue
```

```text
/jjk-commit --abort
```

```text
/jjk-commit @docs/内部参考/迭代需求/review_report_xxx.md
```

---
*使用 `/jjk-commit` 触发。目标是“已验证改动的本地提交与主干收口”，不是“绕过验证的一键推平”，也不是“让命令层再维护一套独立 Git 策略”。*
