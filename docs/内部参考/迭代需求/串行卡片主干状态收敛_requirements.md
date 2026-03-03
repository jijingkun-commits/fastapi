# 需求基线（串行卡片主干状态收敛）

## 1. 背景与问题陈述

当前 `jjk-*` 串行链路在执行层存在“流程串行”与“主干串行”语义不一致：

1. `jjk-cardrun` 可在 `verify` 通过后将卡片标记为 `done`，但并不强制“提交并合入 `master`”。
2. 任务后置依赖依据的是卡片状态而非主干集成状态，导致“门禁通过但主干不可见”的错觉。
3. `jjk-vktodo` 同时承担建卡、状态推进、作用域绑定等职责，边界过宽，增加链路理解与维护成本。

本需求目标是把串行执行收敛为“前置任务先进入主干，后置任务才可开始”的主干状态串行。

## 2. 目标与非目标

### 2.1 目标
1. 将串行任务完成定义收敛为：`verify_passed && merged_to_master`。
2. 保证后置卡片只能在前置卡片合入 `master` 后启动。
3. 将 `jjk-vktodo` 收敛为 create-only（仅建卡，幂等落卡）。
4. 明确双层门禁：流程门禁（G01）与集成门禁（IG01）。
5. 增强执行证据可追溯性（子代理、提交、合并、门禁证据）。

### 2.2 非目标
1. 不重构整套 `jjk-*` 命令体系。
2. 不修改业务功能实现（如 memory admin 功能本身）。
3. 不强制引入 GitHub PR 流程作为本地串行必经路径（保留可选）。

## 3. 用户故事

1. 作为串行执行者，我希望每张卡完成后自动提交并合入主干，再开始下一张卡，确保依赖稳定。
2. 作为任务管理者，我希望 `done` 状态代表“主干可见完成”，而不是“仅工作树局部通过”。
3. 作为排障人员，我希望能从 ledger 直接追溯每张卡的子代理执行、提交 SHA 与合并结果。

## 4. 功能需求（FR）

### FR-01 主干状态串行
1. 实现卡必须按顺序执行：`select -> implement -> verify -> commit -> merge -> cleanup -> next`。
2. 任一实现卡若 `merge` 失败，链路必须阻断，禁止继续激活后续卡。

### FR-02 完成态语义收敛
1. `done` 仅在合并成功后写入状态。
2. `verify` 通过后仅进入中间态（如 `verified` / `ready_to_merge`），不得直接 `done`。

### FR-03 命令职责边界
1. `jjk-vkplan` 负责契约生成与静态校验。
2. `jjk-vktodo` 仅负责 create-only 建卡。
3. `jjk-cardrun` 负责执行态推进、门禁验证与主干合并闭环。

### FR-04 双层门禁
1. G01（流程门禁）用于验证 scope 与各实现卡 gate_result。
2. IG01（集成门禁）用于验证实现卡已合并主干且主干回归通过。

### FR-05 可观测与追溯
1. 每卡必须沉淀子代理执行证据（`subagent_id`、`ws_file`、结果）。
2. 每卡必须沉淀集成证据（`commit_sha`、`merge_sha`、`merged_at`）。

## 5. 非功能需求（NFR）

1. 一致性：命令文档、执行脚本、状态账本对“完成态/脏仓策略”口径一致。
2. 可维护性：职责清晰，避免 `vktodo`、`cardrun` 交叉管理状态。
3. 可回滚性：每张卡提供明确回滚点，失败可在当前卡止损。
4. 可审计性：状态变更和门禁结果均可追溯到可执行证据。

## 6. 验收标准

### 6.1 Happy Path
1. 执行 `cardrun loop` 时，C02 不会在 C01 合并前启动。
2. 每张实现卡完成后可看到 `commit_sha` 与 `merge_sha`，并写入 `done`。
3. 全链路完成后 IG01 通过，`master` 可见变更。

### 6.2 异常/边界
1. `verify` 通过但 `merge` 失败时，状态停留在 `merge_blocked`（或等价阻断态），不推进后续卡。
2. 主仓 dirty 且不在白名单时，`cardrun` fail-fast 并给出一致错误码。

### 6.3 可观测
1. ledger 中每张卡都有子代理执行证据与合并证据。
2. G01 与 IG01 的证据文件可独立核查，不互相替代。

## 7. 测试用例矩阵（预留）

| TC 编号 | 场景 | 预期 |
|---|---|---|
| SERIAL-MASTER-TC-001 | C01 完成后自动提交并合并 | C01 状态由 `verified` 转 `done`，含 commit/merge 证据 |
| SERIAL-MASTER-TC-002 | C01 merge 失败 | `cardrun` 阻断且不创建 C02 worktree |
| SERIAL-MASTER-TC-003 | `vktodo move` 调用 | 返回 `VKTODO_ACTION_NOT_ALLOWED` |
| SERIAL-MASTER-TC-004 | G01 通过但 IG01 未通过 | 总体状态不应为最终完成 |
| SERIAL-MASTER-TC-005 | dirty 白名单与非白名单 | 白名单通过、非白名单阻断且口径一致 |

## 8. 约束与依赖

1. 依赖 `wt-flow.sh` 状态机支持 `verified -> done(merged)`。
2. 依赖 `coder4_bootstrap_kernel.py` 输出扩展执行证据字段。
3. 依赖 `vkplan` 模板明确 `merge_required` 与 `gate_contract` 双层语义。
