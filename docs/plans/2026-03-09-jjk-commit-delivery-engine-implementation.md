# JJK Commit Git Delivery Engine Implementation Plan

> **For Claude/Codex:** 优先按“文档先行 -> 测试先行 -> 结构收敛 -> 命令接线 -> 最终验证”的顺序执行。

**Goal:** 把 `jjk-commit` 收敛为交付编排层，新增共享 `Git Delivery Engine` 统一承担 `rebase / merge / conflict / continue / abort / status`，并让 `wt-flow.sh merge` 复用同一套 Git 生命周期实现。

**Architecture:** 以 `.cursor/commands/jjk-commit.md` 作为命令真理源，`scripts/coder4/git-delivery-engine.sh` 作为 Git 生命周期真理源，`scripts/coder4/wt-flow.sh` 只负责 card/worktree 运行态编排与 merge 后状态回写。

**Tech Stack:** Markdown、Bash、Git worktree、现有 `wt-flow` 测试基座、`scripts/repo_python.sh`、`scripts/pytest_targeted.sh`。

---

### Task 1: 固化设计与实施文档

**Files:**
- Create: `docs/plans/2026-03-09-jjk-commit-delivery-engine-design.md`
- Create: `docs/plans/2026-03-09-jjk-commit-delivery-engine-implementation.md`

**Step 1: 写入设计冻结结论**

把已获批准的方案 B 固化为 design 文档，明确四段式架构结论、共享 engine 边界、恢复协议与测试矩阵。

**Step 2: 写入实施计划**

把后续改动拆成文档同步、测试补齐、engine 提取、命令接线、最终验证五个阶段，避免边做边漂移。

**Step 3: 自检文档命名**

确认 design / implementation 文件名、日期与主题一致，便于后续检索与记忆同步。

### Task 2: 先更新命令与工作流文档

**Files:**
- Modify: `.cursor/commands/jjk-commit.md`
- Modify: `.agents/skills/jjk-commit/SKILL.md`
- Modify: `docs/开发文档/工作流/开发工作流.md`
- Modify: `docs/开发文档/工作流/指令用法_实现方式_工程流全景手册.md`
- Modify: `docs/开发文档/技巧与速查/AI协作速查表.md`
- Modify: `docs/开发文档/技巧与速查/vibe-coding开发技巧.md`
- Modify: `memory-bank.md`

**Step 1: 收敛命令契约**

把 `jjk-commit` 文案从“默认 `--ff-only`，不行就人工处理”改为“委托 engine 执行交付收口”，补入 `--status / --continue / --abort / --dry-run`。

**Step 2: 统一工作流口径**

在工作流手册和速查文档中明确：`jjk-commit` 是交付编排层，Git 生命周期真理源是共享 engine，而不是聊天口述或 `wt-flow` 内嵌实现。

**Step 3: 记录长期决策**

在 `memory-bank.md` 追加“Git 交付收口分层为命令编排层 + 共享 delivery engine”的长期决策。

### Task 3: 先写失败测试，再提取共享 engine

**Files:**
- Create: `tests/unit/test_git_delivery_engine.py`
- Modify: `tests/unit/test_coder4_wt_flow_verified_state.py`
- Create: `scripts/coder4/git-delivery-engine.sh`

**Step 1: 为 engine 设计最小测试夹具**

复用当前 `wt-flow` 测试中已有的临时 git repo / worktree 夹具，避免重新造轮子。

**Step 2: 写 happy path 测试**

覆盖“源分支有新提交、基线未前进、merge 成功”的最小主路径。

**Step 3: 写基线前进测试**

覆盖“基线前进、engine 自动 rebase 后 merge 成功”的路径。

**Step 4: 写冲突恢复测试**

覆盖 `rebase` 冲突、`merge` 冲突、`status`、`continue`、`abort` 的结构化输出与行为；冲突时必须保留进行中的 Git 状态，不能先自动 `abort`。

**Step 5: 提取 engine 最小骨架**

实现 `prepare-base / merge / status / continue / abort` 五个子命令，先只服务 `jjk-commit` 与 `wt-flow`，不要扩张为通用 Git 平台。

### Task 4: 让 `wt-flow.sh` 改为委托 engine

**Files:**
- Modify: `scripts/coder4/wt-flow.sh`
- Verify only: `scripts/wt-flow.sh`

**Step 1: 抽离 merge 主流程**

把 `wt-flow.sh` 中 ahead/behind 判定、rebase、merge、abort 逻辑迁移到 engine。

**Step 2: 保留 card 语义**

`wt-flow.sh` 只保留 verified 门禁、session/card 校验、merge 成功后的 `done` / `merge_results` 回写与 cleanup。

**Step 3: 确保 wrapper 不变**

`scripts/wt-flow.sh` 仍只做 wrapper，不引入第二套逻辑。

### Task 5: 让 `jjk-commit` 真正接入 engine

**Files:**
- Modify: `.cursor/commands/jjk-commit.md`
- Modify: `.agents/skills/jjk-commit/SKILL.md`
- Create or Modify: `scripts/coder4/jjk-commit.sh`（若仓内已有等效入口则复用，否则新增最薄入口）

**Step 1: 保留交付门禁**

继续校验当前分支、commit message、验证证据、源 worktree 干净度与是否存在无关脏改动。

**Step 2: 接入 engine merge 主路径**

默认路径改为：必要时创建 commit -> 调用 engine `merge` -> 输出结构化交付摘要。

**Step 3: 接入恢复子命令**

让 `--status / --continue / --abort` 直连 engine，而不是在命令层重复实现。

### Task 6: 同步错误码与用户输出

**Files:**
- Modify: `.cursor/commands/jjk-commit.md`
- Modify: `scripts/coder4/git-delivery-engine.sh`
- Modify: 相关文档中的失败码说明（若已有集中说明则原位更新）

**Step 1: 对齐错误码**

统一 `COMMIT_*` 与 `DELIVERY_*` 失败码，避免一个场景两个名字。

**Step 2: 对齐人类输出**

确保用户看到的是“发生了什么、现在在哪个 worktree、下一步执行什么”，而不是底层 Git 噪音。

### Task 7: 做定向验证与最终静态校验

**Files:**
- Verify only: `tests/unit/test_git_delivery_engine.py`
- Verify only: `tests/unit/test_coder4_wt_flow_verified_state.py`
- Verify only: `.cursor/commands/jjk-commit.md`
- Verify only: `docs/开发文档/工作流/开发工作流.md`

**Step 1: 解析测试解释器**

先运行：`bash scripts/repo_python.sh`，记录本次命中的解释器路径。

**Step 2: 定向回归**

运行：`bash scripts/pytest_targeted.sh tests/unit/test_git_delivery_engine.py tests/unit/test_coder4_wt_flow_verified_state.py`

**Step 3: 最小静态检查**

运行：`git diff --check`

**Step 4: 需要时再做更宽验证**

若定向回归命中共享逻辑的范围较大，再补相关 unit tests；不要一上来跑全量 pytest。

### Task 8: 收口交付说明

**Files:**
- Update summary only: 最终交付说明

**Step 1: 提供瘦身证据**

说明 `wt-flow.sh` 减少了哪些 merge 逻辑、哪些职责迁移到 engine、哪些重复口径被删除。

**Step 2: 提供验证证据**

回显解释器路径、定向测试命令、通过结果、若未做运行态校验则说明原因与残余风险。

**Step 3: 提供后续动作**

建议是否继续补 `jjk-deleteworktree` 与共享 engine 的配套收敛，避免下一轮再次分叉。

---

## 实施守则

- 先改文档，再改代码；命令契约先于脚本实现冻结。
- 命中 `scripts/**/*.sh` 的热点目录时，严格遵守 shrink-only：通过提取共享 engine 来减少 `wt-flow.sh` 的体积，而不是继续往里塞 helper。
- 禁止新增兼容壳掩盖双真理源问题；如果旧路径需要兼容，必须明确写出退役策略与失效条件。
- 冲突恢复协议必须可测试，不接受“文案提示用户自己处理”作为完成标准。
