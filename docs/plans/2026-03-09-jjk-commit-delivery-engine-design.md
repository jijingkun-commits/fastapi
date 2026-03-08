# `jjk-commit` Git Delivery Engine 收敛设计

> 设计日期：2026-03-09
> 主题：把 `jjk-commit` 从“交付门禁 + 半套 merge 口径”收敛为“交付编排层”，并将 `rebase / merge / conflict / continue / abort / status` 统一下沉到共享 Git Delivery Engine

---

## 1. 执行结论

- 采用 **“`jjk-commit` 负责交付门禁，Git Delivery Engine 负责真实 Git 生命周期”** 的收敛方案。
- `jjk-commit` 不再单独定义 `--ff-only` 等 merge 细节；命令层只保留输入前置、验证证据、提交摘要、交付摘要与错误码翻译。
- `wt-flow.sh merge` 不再继续内嵌自己的 `rebase/merge` 主流程，而是复用同一个共享 engine；`wt-flow` 只负责 card/worktree 语义与 merge 后状态回写。
- 冲突恢复协议统一为 `--status / --continue / --abort`，不再让执行者在聊天上下文里凭记忆手拼 Git 命令。
- `master` checkout 改为 engine 内部准备逻辑，而不是 `jjk-commit` 的脆弱外部前置条件。

## 2. 背景与问题

- 当前 `jjk-commit` 文案明确写的是“默认 `--ff-only`，若无法快进则明确提示并改走人工冲突处理”，它更像一个保守的交付门禁，而不是完整的合并器。
- 但仓库内真实执行 merge 生命周期的 `scripts/coder4/wt-flow.sh` 仍沿用旧语义：当基线分支前进时会先 `rebase`，`rebase` 冲突会自动 `abort`，随后再执行 `merge --no-ff`，merge 冲突也会自动 `abort`。这套语义与目标中的 `continue/abort/status` 恢复协议并不一致。
- 这意味着当前仓库实际上存在两套 merge 语义：
  1. 命令层口径：`ff-only` + 不行就人工；
  2. 脚本层口径：`rebase + no-ff merge + abort`。
- 项目仍处于未上线阶段，按 Layer1 与 `core.mdc`，应优先消除结构性分裂，而不是继续给 `jjk-commit` 补提示词或加额外 fallback。

## 3. 四段式架构结论

### 3.1 模块边界

- `jjk-commit` 的职责边界是：**交付编排层**。
- 共享 Git Delivery Engine 的职责边界是：**Git 生命周期执行层**。
- `wt-flow.sh` 的职责边界是：**worktree/card 运行态编排层**。
- 文档、skill 镜像、工作流手册只负责解释入口与边界，不再定义另一套 merge 真相。

### 3.2 依赖方向

- 正确依赖方向应为：`jjk-commit -> Git Delivery Engine`。
- `wt-flow.sh merge -> Git Delivery Engine`。
- 文档与 skill 镜像依赖命令真理源，不能反向成为 merge 语义真理源。
- 禁止让 engine 反向依赖 review/test/verify 语义；这些属于交付编排层，不属于 Git 生命周期层。

### 3.3 状态归属

- Git 原生状态（`.git/rebase-*`、`.git/MERGE_HEAD` 等）是真正的“进行中”状态 owner。
- Engine 元数据只负责记录用户恢复所需上下文：`source_branch`、`base_branch`、`source_worktree`、`base_checkout`、`stage`、`commit_sha`、`verify_refs` 等。
- `task-runner-state.json`、`merge_results` 等 card 状态只归 `wt-flow` 持有；`jjk-commit` 不写业务状态。
- 禁止在文档、聊天话术、agent 临时变量中散落另一份“交付中状态”。

### 3.4 错误处理责任

- Engine 负责：探测 ahead/behind、准备基线 checkout、执行 `rebase/merge`、执行 `abort/continue`、输出结构化结果。
- `jjk-commit` 负责：输入门禁、验证证据门禁、提交摘要、结构化错误码、人类可读下一步建议。
- `wt-flow` 负责：在 engine 成功后回写 `done`、`merge_results`、可选 cleanup。
- 禁止再让编排层用临时 shell 命令兜底 Git 冲突。

## 4. 方案对比

| 方案 | 做法 | 优点 | 缺点 | 结论 |
|---|---|---|---|---|
| A | 只修改 `jjk-commit` 文案，继续保留“不能快进就人工处理” | 改动小 | 根因不变，双真理源继续存在 | 不选 |
| B | `jjk-commit` 变薄，统一委托共享 Git Delivery Engine | 边界清晰、可恢复、可测试、可复用 | 需要一次结构收敛 | 采用 |
| C | 直接废弃 `jjk-commit`，全部改用 `wt-flow.sh` | 真理源唯一 | 把 card/worktree 内部语义暴露给通用交付，破坏边界 | 不选 |

## 5. 目标架构

```mermaid
flowchart TD
    A["`/jjk-commit` 命令契约"] --> B["交付编排层"]
    B --> C["Git Delivery Engine"]
    D["`wt-flow.sh merge`"] --> C
    C --> E["Git 原生状态\nrebase / merge / worktree"]
    C --> F["Engine 元数据\noperation context"]
    B --> G["验证证据摘要 / 错误码 / 用户提示"]
    D --> H["card 状态回写 / cleanup"]
```

## 6. 命令契约设计

### 6.1 `jjk-commit` 主入口

- 默认模式：提交当前分支的本次改动，并通过 engine 尝试把当前分支收口到 `master`。
- `--dry-run`：只做上下文、脏状态、验证证据、基线可达性检查，不执行 commit/merge。
- `--status`：输出当前 engine 是否存在进行中的 `rebase` 或 `merge` 恢复上下文。
- `--continue`：在用户手动解决冲突后，继续当前交付流程。
- `--abort`：中止当前交付流程，并清理 engine 元数据。

### 6.2 `jjk-commit` 持续保留的门禁

- 当前分支为空、处于 detached HEAD、当前就在 `master`：继续阻断。
- 缺少 commit message：继续阻断。
- 缺少验证证据：继续阻断。
- 当前 worktree 存在与本次交付无关的脏改动：继续阻断。
- 当前分支没有新提交：继续阻断。

### 6.3 `jjk-commit` 不再直接承担的职责

- 不再直接定义 `--ff-only / --no-ff / rebase` 的细节策略。
- 不再要求调用者预先手工准备 `master` worktree。
- 不再把冲突处理简化为“提示人工处理”后完全失联。

## 7. Git Delivery Engine 设计

### 7.1 建议落点

- 新增共享脚本：`scripts/coder4/git-delivery-engine.sh`
- 初期采用 Bash 实现，保持与现有 `wt-flow.sh` 一致的运行环境与 Git 工具链；后续若确实需要更复杂状态管理，再评估迁移 Python。

### 7.2 子命令

- `merge`：执行 `source_branch -> base_branch` 收口。
- `status`：输出当前进行中的恢复上下文。
- `continue`：继续 `rebase` 或 `merge`。
- `abort`：中止 `rebase` 或 `merge`。
- `prepare-base`：解析或创建 `master` checkout，供主入口和调试场景复用。

### 7.3 推荐策略

- 默认策略：`rebase base_branch` 后 `merge --no-ff source_branch`。
- 选择这个策略的原因：
  1. 先吸收主干最新基线，减少“老基线直接 merge”带来的冲突面；
  2. 保留明确的收口提交，符合本仓库“显式交付入口”的设计目标；
  3. 比单纯 `ff-only` 更稳，且比完全暴露底层 Git 细节更易被命令层封装。

## 8. 状态与恢复协议

### 8.1 Engine 元数据建议

建议写入 common git dir 下的独立目录，例如：

- `${COMMON_GIT_DIR}/codex/jjk-commit/<branch>.json`

建议字段：

```json
{
  "schema_version": "1.0.0",
  "tool": "jjk-commit",
  "source_branch": "codex/example",
  "base_branch": "master",
  "source_worktree": "/path/to/source",
  "base_checkout": "/path/to/master",
  "stage": "rebase_conflict",
  "strategy": "rebase-then-no-ff-merge",
  "verify_refs": ["review_report_xxx.md"],
  "commit_sha": "abc123",
  "started_at": "2026-03-09T00:00:00Z",
  "updated_at": "2026-03-09T00:05:00Z"
}
```

### 8.2 恢复语义

| 场景 | `--status` | `--continue` | `--abort` |
|---|---|---|---|
| `rebase` 冲突 | 显示 source worktree、冲突阶段、下一步 | 在 source worktree 执行 `git rebase --continue`，成功后自动继续 merge | 执行 `git rebase --abort`，清理元数据 |
| `merge` 冲突 | 显示 base checkout、冲突阶段、下一步 | 在 base checkout 执行 `git merge --continue` | 执行 `git merge --abort`，清理元数据 |
| 无进行中操作 | 输出 idle | fail-fast | fail-fast |

## 9. 关键错误码建议

| 错误码 | 含义 | 责任层 |
|---|---|---|
| `COMMIT_BRANCH_INVALID` | 当前分支非法或位于 `master` | `jjk-commit` |
| `COMMIT_MESSAGE_MISSING` | 缺少 commit message | `jjk-commit` |
| `COMMIT_VERIFY_MISSING` | 缺少验证证据 | `jjk-commit` |
| `COMMIT_WORKTREE_DIRTY` | 源 worktree 存在无关脏改动 | `jjk-commit` |
| `DELIVERY_BASE_UNAVAILABLE` | engine 无法准备 `master` checkout | engine |
| `DELIVERY_REBASE_CONFLICT` | `rebase` 冲突，Git 状态保持进行中，等待用户 `--continue` 或 `--abort` | engine |
| `DELIVERY_MERGE_CONFLICT` | `merge` 冲突，Git 状态保持进行中，等待用户 `--continue` 或 `--abort` | engine |
| `DELIVERY_NOT_IN_PROGRESS` | 调用了 `--continue/--abort` 但无进行中操作 | engine |

## 10. 文档同步范围

本轮实现至少同步：

1. `.cursor/commands/jjk-commit.md`
2. `.agents/skills/jjk-commit/SKILL.md`
3. `scripts/coder4/wt-flow.sh`
4. `docs/开发文档/工作流/开发工作流.md`
5. `docs/开发文档/工作流/指令用法_实现方式_工程流全景手册.md`
6. `docs/开发文档/技巧与速查/AI协作速查表.md`
7. `docs/开发文档/技巧与速查/vibe-coding开发技巧.md`
8. `memory-bank.md`

## 11. 测试设计

### 11.1 最小新增测试矩阵

- `jjk-commit` happy path：提交后自动合并成功。
- 基线前进但无冲突：自动 `rebase` 后合并成功。
- `rebase` 冲突：保留进行中的 rebase 状态，`status` 可见，`continue/abort` 行为正确。
- `merge` 冲突：保留进行中的 merge 状态，`status` 可见，`continue/abort` 行为正确。
- 无 `master` checkout：engine 自动准备基线 checkout。
- 无新提交 / 在 `master` 上执行 / 缺少验证证据：继续 fail-fast。

### 11.2 测试落点建议

- 继续复用：`tests/unit/test_coder4_wt_flow_verified_state.py`
- 新增：`tests/unit/test_git_delivery_engine.py`
- 如有必要，再新增：`tests/unit/test_jjk_commit_contract.py`

## 12. 风险与控制

| 风险 | 表现 | 控制手段 |
|---|---|---|
| 继续把逻辑堆进 `wt-flow.sh` | 热点脚本继续膨胀 | 把 merge 主流程外提到新 engine，`wt-flow` 只保留 card 语义 |
| 命令层和脚本层再次漂移 | 文档、命令、脚本口径再次分裂 | 以 engine 为 Git 生命周期真理源，命令层只描述契约 |
| 恢复协议失真 | `status/continue/abort` 与 Git 真实状态不一致 | Git 原生状态为准，engine 元数据只做辅助上下文 |
| 过度设计 | 一次性引入过重平台 | 第一阶段仅收敛 `merge/status/continue/abort/prepare-base` |

## 13. 设计冻结回执

- `design_approved=true`
- `approved_at=2026-03-09`
- `approved_round=1`
- `approval_evidence=用户在当前会话中确认采用“方案 B”，并回复“好的”允许继续落地为实施计划`
