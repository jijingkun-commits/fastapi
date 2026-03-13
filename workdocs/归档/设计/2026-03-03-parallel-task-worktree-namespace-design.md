# jjk 多任务并行开发（Worktree 命名空间 + 异步收口 + 状态一致性）设计说明

## 1. 需求澄清结论
- 目标: 在不破坏现有 `jjk-*` 串行卡片语义的前提下，实现“任务级并行 + 卡片级串行”，消除并行任务下的分支、worktree、状态与证据冲突，并保证用户回答主链路不被额外收口逻辑阻塞。
- 范围: `scripts/coder4/wt-flow.sh`、`scripts/coder4/coder4_bootstrap_kernel.py`、`scripts/coder4/coder4_vk_sync.py`、`scripts/coder4/check_integration_gate.py`、相关流程文档（`jjk-cardrun`/`jjk-vkplan`/`jjk-vktodo`）。
- 边界: 不改 Vibe Kanban API 契约，不改 `jjk-cardrun` 的 `execution_mode=serial` 单活卡语义，不在本轮引入“多卡并发执行”。
- 成功标准:
  - 不同 `task_key` 下同名卡（如 `C01`）可并行推进且互不覆盖。
  - `verify -> merge -> done` 闭环保持不变。
  - 任务切换后，状态与证据读取不再漂移（active 索引与状态文件一致）。
  - 用户侧首包与完成响应时延不因记忆 flush、状态同步、证据归档而上升（改为异步执行）。

## 2. 方案对比（2-3个）
| 方案 | 优点 | 缺点 | 成本 | 推荐度 |
|---|---|---|---|---|
| A. 仅流程规范（手动切 active，不改脚本） | 零代码改动，落地快 | 不能解决分支/worktree/状态文件碰撞，依赖人工纪律，易复发 | 低 | 低 |
| B. 仅改 `wt-flow.sh` 命名空间 | 解决分支/worktree/会话冲突，主流程改动集中 | 读侧脚本仍读全局 `docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>`，会出现“写隔离、读错位” | 中 | 中 |
| C. 全链路命名空间（`wt-flow` + 读侧统一路径） | 一次性闭环解决“写入隔离 + 读取一致 + 证据隔离”，与现有 `jjk-*` 契约兼容 | 改动面更大，需要补充迁移与回归测试 | 中高 | 高 |

## 3. 推荐方案与理由
- 推荐: 方案 C（全链路命名空间）。
- 理由:
  - 当前仓库已出现 active 索引与运行状态漂移，单改流程或单改 `wt-flow` 都不足以止损。
  - 冲突根因不是单点，而是“命名空间 + 读写路径 + 证据目录”三处不一致。
  - 方案 C 能保持 `jjk-cardrun` 现有闭环，同时把并行能力建立在可验证的状态契约上。

## 4. 设计概要
- 架构:
  - 核心模式保持为“任务级并行 + 卡片级串行”。
  - 统一资源命名为 task_key 作用域:
    - 分支: `feature/<task_key>/<card_id>`
    - worktree: `.worktrees/<task_key>/<card_id>`
    - 会话状态: `docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/wt-flow-state.json`
    - 卡片状态: `docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/task-runner-state.json`
    - 证据目录: `docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/task-runner-state.json::gate_results/merge_results/<card_id>/`
  - 无 `task_key` 的 legacy 任务保持旧路径（兼容模式），新任务默认走命名空间路径。
- 组件:
  - `scripts/coder4/wt-flow.sh`
    - `create/next/verify/merge/list/cleanup` 统一按 task_key 解析状态根目录。
    - 分支解析兼容两种格式: `feature/<card_id>` 与 `feature/<task_key>/<card_id>`。
    - `merge_result.json`、`gate_result.json` 改写至 task_key 作用域 `attempts` 目录。
  - `scripts/coder4/coder4_bootstrap_kernel.py`
    - 默认状态路径从固定 `docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/task-runner-state.json` 升级为“按 active_task 推导的 task_key 路径”。
  - `scripts/coder4/coder4_vk_sync.py`
    - 默认读取逻辑与 bootstrap 保持同源，避免读全局旧文件。
  - `scripts/coder4/check_integration_gate.py`
    - `state_file` 与 `attempts` 改为 task_key 作用域路径，保证校验读取同一任务证据。
  - `scripts/coder4/coder4_scope_guard.py`
    - `already_active` 判定补齐 `task_key` 维度，避免“目录相同但 task_key 漂移”误判。
- 数据流:
  - 推荐链路保持不变:
    - `/jjk-plan -> /jjk-vkplan -> /jjk-vktodo(create-only) -> /jjk-cardrun(loop)`
  - 关键变化:
    - `/jjk-cardrun` 触发 `wt-flow.sh` 时，状态读写与证据归档自动落入当前 active task_key 的作用域目录。
    - 切换任务仍通过 `set_active_task.py`，但切换后读取不再指向全局单例状态文件。
- 异常与测试考虑:
  - 风险防护:
    - 增加 active-task 与 task-runner-state 的一致性校验（`task_key/card_order` 必须匹配）。
    - 增加会话文件存在性校验，避免切到新任务后误 merge 旧任务会话。
  - 回归用例:
    - 同时准备任务 A/B（均含 `C01`），验证分支/worktree/state/gate_results/merge_results 全部隔离。
    - 在 A、B 间切换 active 多次，验证 `next/verify/merge/list` 始终命中当前任务状态。
    - 兼容测试: legacy `feature/C01` + `.worktrees/C01` 场景仍可正常收口。
  - 文档同步:
    - 同步更新 `.cursor/commands/jjk-cardrun.md`、`.cursor/commands/jjk-vkplan.md`、`docs/开发文档/流程与工具/开发工作流.md` 中旧路径示例。

## 5. 未决问题（如有）
- [ ] 是否在 `_active_task.json` 显式新增 `state_root` 字段，减少多脚本重复推导。
- [ ] 是否提供一次性迁移脚本，将 legacy `docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/task-runner-state.json` 迁移到 `docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/`。
- [ ] `.cursor/scripts/coder4/wt-flow.sh` 与 `scripts/coder4/wt-flow.sh` 的维护策略是否统一为单一真理源（避免双份漂移）。

## 6. 审批记录
- design_approved: true
- approved_at: 2026-03-03 19:00
- approved_round: 用户指令 `$jjk-plan`（v0.2）
