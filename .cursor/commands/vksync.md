---
description: VK 基线同步：在 /vktodo 前校验并同步 G0（WS-00）到多 worktree
---

# VK 基线同步工作流 (VK Sync Workflow)

用于在多 worktree 场景下，确保 `WS-00_G0_协议冻结` 已进入基线并同步到各并行 worktree，再执行 `/vktodo` 落卡。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 何时使用

| 场景 | 推荐命令 |
|------|----------|
| 准备执行 `/vktodo`，且存在多个 worktree | `/vksync` ✅ |
| 单 worktree 本地演练 | 可跳过 |

---

## 输入约定

`/vksync <task_split_dir_or_path> [mode]`

- `mode=check`：仅校验，不改动分支（默认）
- `mode=apply`：对未同步 worktree 自动执行 rebase（失败即停止）

---

## 执行步骤

### Step 1: 校验 G0 产物完整性

校验以下文件存在且可解析：

1. `parallel_plan.md`（包含 `## 0. G0 协议冻结`）
2. `workstreams/WS-00_G0_协议冻结.md`
3. `contracts/sse_events_v1.json`

若缺失任一文件，直接失败并提示回到 `/vkplan` 重产。

### Step 2: 解析基线提交

1. 优先从 `parallel_plan.md` 读取本轮冻结记录的 `g0_baseline_commit`（若已记录）。
2. 若未记录，再回退到基线分支 HEAD（优先 `main`，其次 `master`）。
3. 最终得到 `g0_baseline_commit` 后再进入 worktree 对齐校验。

### Step 3: 校验 worktree 同步状态

1. 列出所有 worktree。
2. 对每个待并行 worktree 执行：
   - `git -C <wt> merge-base --is-ancestor <g0_baseline_commit> HEAD`
3. 输出 READY / NOT_READY 清单。

### Step 4: 处理未同步 worktree

- `mode=check`：发现 `NOT_READY` 直接失败，提示先同步。
- `mode=apply`：对 `NOT_READY` 执行 rebase；若冲突，停止并输出冲突 worktree。

### Step 5: 通过判定

1. 若全部 worktree 为 READY，方可进入 `/vktodo`。
2. 若存在 `NOT_READY`，默认阻断 `/vktodo`。
3. 仅当调用方显式声明 `allow_not_ready=true` 时，允许带风险继续，并必须记录风险确认。

---

## 推荐链路

`/plan -> /vkplan -> /vksync -> /vktodo（或 /vkkb） -> /imp-ws`

---

## 使用示例

```text
/vksync 2026-02-12_skill检索对齐_cursor_mvp
```

```text
/vksync 2026-02-12_skill检索对齐_cursor_mvp apply
```

---
*使用 `/vksync` 触发。用于多 worktree 并行前的 G0 基线生效校验。*
