# CardRun 分支感知基线设计

## 1. 需求澄清结论
- 目标：让 `/jjk-cardrun` 在非 `main/master` 分支上运行时，卡片 worktree 默认基于“当前 cardrun 所在分支”创建，并最终收口回该分支，而不是固定回 `master`。
- 范围：`scripts/coder4/wt-flow.sh`、相关测试、命令文档与开发工作流文档。
- 边界：不改变 `wtimp(cardrun_dispatch)` 的职责；不新增第二条 merge 主路径；不改业务模块。
- 成功标准：
  - `cardrun -> wt-flow next/create` 在 feature 分支上能继承父分支作为 `base_branch`；
  - `wtimp(cardrun_dispatch)` 仍只做“实现 + 提交 + 证据回传”；
  - `verify -> merge` 继续是唯一收口主路径；
  - 任务同一轮次内后续卡片继续沿用同一集成分支，不因 cwd 变化漂移。

## 2. 方案对比
| 方案 | 做法 | 优点 | 缺点 | 推荐度 |
|---|---|---|---|---|
| A. 继续固定 `master` | 不改现状 | 最省事 | 不能在 feature 分支上安全跑 `cardrun`；和用户预期冲突 | 低 |
| B. 仅按当前分支临时推断 | `create` 时默认取当前分支 | 改动小 | 续跑/恢复时若 cwd 变成别的分支，目标会漂 | 中 |
| C. 任务态保存集成分支 + 当前分支首轮推断 | 首轮从当前分支推断，随后写入 task state 并复用 | 简洁、稳定、职责清晰 | 需要补一点状态字段和测试 | 高 |

## 3. 推荐方案
- 采用方案 C。
- 理由：
  - 根因不在 `wtimp`，而在 `wt-flow create/next` 默认把 `base_branch` 写死成 `master`；
  - “集成到哪个分支”属于任务运行态，不该由 `wtimp` 或临时 cwd 猜测；
  - 首轮从当前分支推断、后续写入 task state，既保留“人话直觉”，又避免恢复执行时目标漂移。

## 4. 架构冻结
### 模块边界
- `cardrun`：编排、选卡、dispatch、verify/merge 主路径。
- `wt-flow`：创建卡片分支/worktree、记录 `base_branch`、执行 merge。
- `wtimp(cardrun_dispatch)`：只在已有 card worktree 中实现与提交，禁止二次 create/merge。
- `git-delivery-engine`：只做底层 `rebase + merge --no-ff`，不决定业务层目标分支。

### 依赖方向
- 固定为：`cardrun -> wt-flow -> git-delivery-engine`。
- `wtimp(cardrun_dispatch)` 依赖 `wt-flow` 已准备好的 worktree，不反向决定基线分支。

### 状态归属
- 新增任务级运行态字段：`task-runner-state.json.integration_branch`。
- 单卡会话继续保存 `active-session-*.json.base_branch`。
- 规则：
  1. 若任务态已有 `integration_branch`，后续卡片必须复用；
  2. 若任务态没有，则首轮从当前分支推断；
  3. 若当前分支是 `main/master` 或 card 会话分支，则回落到仓库主线分支。

### 错误处理责任
- `wt-flow create/next`：负责解析并持久化 `integration_branch`；若显式目标分支不存在则 fail-fast。
- `wt-flow merge`：只读取会话态中的 `base_branch` 合并，不再自行猜测。
- `wtimp(cardrun_dispatch)`：继续只负责禁止二次 create/merge 的契约与 JSON 回执。

## 5. 文档同步清单
### Must Update
- `.cursor/commands/jjk-cardrun.md`
- `.cursor/commands/jjk-wtimp.md`
- `docs/开发文档/工作流/开发工作流.md`
- `memory-bank.md`

### Should Review
- `docs/开发文档/工作流/VibeKanban多Worktree本机开发测试.md`

### Not In Scope
- API 文档
- 业务功能文档
- 数据库设计文档

## 6. 风险与回退
- 风险：旧任务 state 文件没有 `integration_branch`；通过“缺省推断 + 向后兼容”解决。
- 风险：用户在 `master` 上启动 `cardrun` 仍会继续收口到 `master`；这是保守默认，不是回归。
- 回退：删除 `integration_branch` 解析与写入逻辑，恢复 `cmd_create` 固定默认 `master`。
