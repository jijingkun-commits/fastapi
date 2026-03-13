# CardRun 分支感知基线 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让 `cardrun` 在 feature 分支上运行时，卡片 worktree 默认继承该分支作为基线，并统一收口回该分支。

**Architecture:** 在 `wt-flow` 内新增“任务级 integration_branch 解析 + 复用”能力：首轮从当前分支推断，写入 `task-runner-state.json`，单卡会话继续保存 `base_branch`。`wtimp(cardrun_dispatch)` 不变，`merge` 主路径不变。

**Tech Stack:** Bash、Git worktree、jq、pytest、现有 `wt-flow` / `git-delivery-engine` / 工程流文档。

---

### Task 1: 先补失败测试

**Files:**
- Modify: `tests/unit/test_coder4_wt_flow_verified_state.py`

**Step 1: Write the failing test**
- 新增用例：`wt-flow next` 在父分支为 `feature/cardrun-parent` 时，应创建基于该分支的 card worktree，并把 `task-runner-state.json.integration_branch` 与 session `base_branch` 写成该分支。
- 新增用例：已有 `task-runner-state.json.integration_branch` 时，即使当前 cwd 在 `master`，下一张卡仍应复用该分支。

**Step 2: Run test to verify it fails**
- Run: `bash scripts/pytest_targeted.sh tests/unit/test_coder4_wt_flow_verified_state.py -q`
- Expected: 新增用例 FAIL，当前实现仍固定写 `master`。

### Task 2: 更新命令与工作流文档

**Files:**
- Modify: `.cursor/commands/jjk-cardrun.md`
- Modify: `.cursor/commands/jjk-wtimp.md`
- Modify: `docs/开发文档/流程与工具/开发工作流.md`
- Modify: `memory-bank.md`

**Step 1: Update docs first**
- 明确 `/jjk-cardrun` 在非主线分支上启动时，`wt-flow next/create` 会继承并固定任务级 `integration_branch`。
- 明确 `wtimp(cardrun_dispatch)` 继续禁止二次 create/merge。

### Task 3: 实现最小代码改动

**Files:**
- Modify: `scripts/coder4/wt-flow.sh`

**Step 1: Add branch resolution helpers**
- 新增主线分支判断、仓库默认主线探测、任务级 `integration_branch` 读取/写回辅助函数。

**Step 2: Update `cmd_create` / `cmd_next`**
- `cmd_create` 默认不再固定 `master`，而是走统一解析函数。
- `cmd_next` 在创建下一卡前解析并持久化 `integration_branch`，再传给 `cmd_create`。

**Step 3: Keep merge path stable**
- `cmd_merge` 继续读取 session `base_branch`，不新增第二套 merge 逻辑。

### Task 4: 验证与收口

**Files:**
- Modify: `tests/unit/test_coder4_wt_flow_verified_state.py`

**Step 1: Run targeted tests**
- Run: `bash scripts/pytest_targeted.sh tests/unit/test_coder4_wt_flow_verified_state.py -q`
- Expected: PASS

**Step 2: Optional adjacent regression**
- Run: `bash scripts/pytest_targeted.sh tests/unit/test_coder4_wt_flow_verified_state.py tests/unit/test_coder4_worktree_session_resolution.py -q`
- Expected: PASS
