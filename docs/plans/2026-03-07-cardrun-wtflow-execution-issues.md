# CardRun / WT-Flow 工程流执行问题记录

> **文档类型**: 问题记录与后续修复输入
> **创建日期**: 2026-03-07
> **更新日期**: 2026-03-07
> **问题范围**: `jjk-cardrun`, `jjk-wtimp`, `scripts/coder4/wt-flow.sh`, `coder4_bootstrap_kernel`, `check_workflow_contract`
> **触发任务**: `PP-20260306-workflow-gate-retirement`
> **记录目的**: 沉淀本轮实际执行中暴露的工程流缺陷，供后续专项修复

---

## 1. 结论摘要

本轮执行过程中，真正阻断推进的不是业务代码，而是**工程流执行器、状态白名单、卡片契约一致性**三个层面的缺口。

其中：

1. **已现场修复**的问题有 3 类：
   - `wt-flow verify` 白名单缺少 `rg`，导致 `C01` done_gate 被误阻断；
   - `clarify_consistency_check` 缺字段，导致 `check_plan_vk_coverage.py` 初始校验失败；
   - `vk_cards.json` 顶层缺少 `task_to_pr_mapping`，导致 `cardrun bootstrap` 阻断。
2. **仍需后续系统性修复**的问题有 11 类：
   - `wtimp dispatch` JSON 回执/超时机制不稳；
   - `.state` 运行态文件对白名单依赖过强；
   - 中文路径 dirty 检测依赖 `core.quotePath=false` 临时配置；
   - `scripts/wt-flow.sh` wrapper 脱离仓库路径后不可移植；
   - `C03` 卡片契约本身自冲突，无法在不违约的前提下继续执行；
   - `logs/` 产物被忽略，usage 观测结果默认不会进入提交证据；
   - `C07` 退役门禁天然依赖 7 天 wall-clock 观测窗口，单轮 `cardrun` 无法自然闭环；
   - `G01` 工作流文档仍引用旧脚本命令，与统一入口迁移后的口径不一致；
   - `C03` 的 wrapper 完成定义未约束“物理薄壳化”，导致 `C07` 才暴露 legacy 实现仍驻留；
   - `wt-flow verify` 在多任务并存时无法稳定自动解析当前 `_active_task.json`；
   - `wt-flow verify` 在 worktree 内执行时会把当前目录误当 repo 根，导致 worktree 路径二次拼接。

---

## 2. 问题总表

| 编号 | 优先级 | 问题 | 影响 | 当前状态 | 临时绕过/现场处理 | 后续建议 |
|---|---|---|---|---|---|---|
| WF-01 | P0 | `wt-flow verify` 白名单缺少 `rg` | `C01` 无法 done_gate | 已现场修复 | 将 `rg` 加入 `ALLOWED_PREFIXES` | 补更系统的命令白名单回归测试 |
| WF-02 | P0 | `wtimp dispatch` 未及时返回 JSON 回执 | `cardrun` 主控卡在 dispatch | 待修复 | 终止挂起进程，改为手工收口 `verify -> merge` | 给 dispatch 增加超时、JSON 校验、失败回收 |
| WF-03 | P0 | `.state` 运行态文件会持续污染工作区 | `bootstrap/merge` 易被 dirty policy 阻断 | 待修复 | 显式传 `WT_FLOW_DIRTY_WHITELIST` | 将 active task 作用域下 `.state/<task_key>/` 内建加入白名单 |
| WF-04 | P1 | 中文路径 dirty 检测依赖 `core.quotePath=false` | 白名单对中文路径匹配失败 | 待修复 | 仓库本地 `git config core.quotePath false` | 改用 `git status --porcelain -z` 或做路径反转义 |
| WF-05 | P1 | `scripts/wt-flow.sh` 只是 wrapper，脱离仓库复制会失效 | 调试脚本副本容易误用 | 待修复 | 必须复制 `scripts/coder4/wt-flow.sh` 真正源码 | 明确单一真理源，避免 wrapper 被误当实体脚本 |
| WF-06 | P1 | 历史 `.state` 路径与当前 task_key 容易混淆 | 容易误判真理源、误读状态 | 待修复 | 人工确认当前 task_key=`PP-20260306-workflow-gate-retirement` | 增加状态目录发现器和 stale state 提示 |
| WF-07 | P0 | `C03` 卡片契约自冲突 | 不能“干净地”继续 wrapper 卡 | 待修复 | 暂停执行 `C03` | 先修 `C03` 契约/白名单，再继续 cardrun |
| WF-08 | P1 | `clarify_consistency_check` 缺字段导致 coverage 检查误报 | `cardrun` 前置校验初始失败 | 已现场修复 | 已补 4 个缺失字段 | 给契约字段完整性补回归测试 |
| WF-09 | P1 | `vk_cards.json` 顶层缺少 `task_to_pr_mapping` | `bootstrap` 报 `CARDRUN_PR_MAPPING_MISSING` | 已现场修复 | 已补顶层映射 | 给 `vkplan` 产物增加 schema 级校验 |
| WF-10 | P1 | `logs/` 被 `.gitignore` 忽略 | `C05` usage 观测证据默认不会随提交落库 | 待修复 | 提交时需 `git add -f logs/workflow-gate-usage.jsonl` | 明确日志产物策略，避免证据与代码分离 |
| WF-11 | P0 | `C07` 退役门禁依赖 7 天 wall-clock 观测窗口 | 单轮 `jjk-cardrun` 无法在同一执行波次内自然闭环 | 待修复 | 先以 `full-gate` 真实阻断，不跳过 7 天窗口 | 拆分“门禁建设”与“退役放行”两个阶段性完成定义 |
| WF-12 | P1 | `G01` 工作流文档仍引用旧脚本命令 | 验收文档口径与统一入口迁移结果不一致 | 待修复 | 以 `v3` 退役口径和统一入口实现为准 | 同步 `G01`、命令文档、技能文档的验收命令引用 |
| WF-13 | P0 | `C03` wrapper 验收未覆盖“物理薄壳化” | `C07` 才首次暴露 legacy 大体量实现仍驻留 | 待修复 | 由 `full-gate` 的 `LEGACY_WRAPPER_NOT_THIN` 真实阻断 | 区分“CLI 兼容完成”与“旧实现已物理退役”两个完成定义 |
| WF-14 | P0 | `wt-flow verify` 多任务场景下无法自动解析 active task | `C07` verify 直接阻断，无法进入真实 done_gate | 待修复 | 显式设置 `WT_FLOW_ACTIVE_TASK_FILE` 或 `WT_FLOW_TASK_SPLIT_DIR` | 给 `wt-flow` 增加 worktree 上下文优先级与更稳健的 active task 发现逻辑 |
| WF-15 | P0 | `wt-flow verify` 在 worktree 内错误拼接 worktree 根路径 | `C07` 在正确 worktree 内仍无法直接 verify | 待修复 | 从主仓根目录执行 `verify` | 统一以 `git rev-parse --show-toplevel` 解析 repo 根，禁止依赖当前 cwd 猜测 |

---

## 3. 关键问题详述

### WF-01 `wt-flow verify` 白名单缺少 `rg`

**现象**
- `C01` 的 `check_cmd` 是：
  - `rg -n "NO-GO|rm scripts/check_\*\.py" ...`
- `bash scripts/wt-flow.sh verify C01` 被阻断：
  - `BLOCKED: 命令前缀不在白名单中: rg ...`

**根因**
- `scripts/coder4/wt-flow.sh` 的 `ALLOWED_PREFIXES` 未包含 `rg`。

**现场处理**
- 已将 `rg` 加入白名单，并补回归测试验证 `rg` 类验收命令可进入 `verified`。

**后续修复建议**
1. 为 `ALLOWED_PREFIXES` 增加显式测试矩阵（`rg/grep/python3/bash` 至少各一例）。
2. 把“命令前缀白名单”和“真实验收命令集合”做一致性检查，避免契约允许但执行器拒绝。

---

### WF-02 `wtimp dispatch` 未及时返回 JSON 回执

**现象**
- `jjk-cardrun` 进入 `dispatch` 后，`wtimp bridge` 未及时返回结构化 JSON。
- 现场出现挂起进程链，需要手工终止相关进程后，改走手工收口路径。

**影响**
- `cardrun` 编排层无法自动确认 `commit_sha / changed_files / acceptance_results`，破坏主控闭环。

**现场处理**
- 终止挂起 dispatch 进程。
- 使用已创建 worktree 手工执行：实现/提交/`wt-flow verify`/`wt-flow merge`。

**后续修复建议**
1. 给 dispatch 增加硬超时与超时错误码；
2. 对 JSON 回执做 schema 校验与超时回收；
3. 明确挂起时的 session 清理策略，避免残留活动会话。

---

### WF-03 `.state` 运行态文件导致 dirty policy 高耦合

**现象**
- 运行 `bootstrap` 或 `merge` 后，以下文件会持续变脏：
  - `coder4-idempotency.json`
  - `task-ledger.jsonl`
  - `task-runner-state.json`
  - `task-runner-state.json.lock`
- 若不显式传入 `WT_FLOW_DIRTY_WHITELIST`，主流程容易被误阻断。

**根因**
- 运行态真理源位于任务目录 `.state/<task_key>/`，但 dirty policy 默认白名单不足以覆盖这些文件。

**现场处理**
- 每次执行显式传：
  - `WT_FLOW_DIRTY_WHITELIST='docs/plans/,docs/内部参考/迭代需求/,docs/内部参考/任务拆解/2026-03-06_工程减法治理/.state/PP-20260306-workflow-gate-retirement/'`

**后续修复建议**
1. 基于当前 active task 自动推导 `.state/<task_key>/` 白名单；
2. 区分“运行态真理源脏文件”与“用户未提交变更”；
3. 对 lock 文件做专门处理，避免反复干扰 merge。

---

### WF-04 中文路径 dirty 检测依赖 `core.quotePath=false`

**现象**
- 初始状态下，中文路径在 `git status --porcelain` 中被转义，导致 dirty whitelist 对中文目录匹配失败。

**现场处理**
- 临时执行：
  - `git config --local core.quotePath false`

**问题本质**
- 当前 dirty path 提取逻辑默认依赖未转义路径字符串，不够稳健。

**后续修复建议**
1. 优先改为 `git status --porcelain -z` + NUL 分隔解析；
2. 不再依赖本地 git config；
3. 给中文路径、空格路径、rename 路径补回归用例。

---

### WF-05 `scripts/wt-flow.sh` wrapper 容易被误当真实脚本

**现象**
- 调试时若复制 `scripts/wt-flow.sh` 到 `/tmp`，会因其内部相对路径 `coder4/wt-flow.sh` 无法解析而失败。

**根因**
- `scripts/wt-flow.sh` 是 wrapper，不是自包含脚本实体。

**现场处理**
- 必须复制真正源码：
  - `scripts/coder4/wt-flow.sh`

**后续修复建议**
1. 明确 wrapper 与实体脚本的单一真理源关系；
2. 给 wrapper 增加更清晰的报错信息，避免脱离仓库执行时静默踩坑；
3. 在工程流文档里显式标注“调试请使用 `scripts/coder4/wt-flow.sh`”。

---

### WF-06 历史状态目录与当前 task_key 容易混淆

**现象**
- 现场曾看到历史残留目录 `.state/PP-20260306-ENGINEERING-LEAN-GOV/`，但当前真实任务是：
  - `PP-20260306-workflow-gate-retirement`

**影响**
- 若误读历史目录，容易错误判断 active session、ledger、task-runner-state 的真理源。

**后续修复建议**
1. 给状态探测命令增加“当前 active task_key 与命中 state_dir”的对照输出；
2. 发现同 split_dir 下存在多个 task_key 时输出 `STALE_STATE_CANDIDATES` 提示；
3. 设计归档/清理策略，避免历史残留持续干扰人工操作。

---

### WF-07 `C03` 卡片契约自冲突

**现象**
- `C03` 验收要求：
  - `python3 scripts/check_workflow_contract.py --mode legacy_wrapper_compat ...`
- 但 `C03` file whitelist 仅允许修改：
  - `scripts/check_clarify_plan_alignment.py`
  - `scripts/check_plan_vk_coverage.py`
  - `scripts/check_gate_contract_consistency.py`
  - `scripts/check_integration_gate.py`
- 当前 `legacy_wrapper_compat` mode 仍在 `scripts/check_workflow_contract.py` 中占位，若不修改该文件就无法让验收命令通过。
- 同时，如果先把 4 个旧脚本都改成 wrapper，而 `legacy_wrapper_compat` 仍通过新入口反调旧脚本，会形成递归调用风险。

**结论**
- `C03` 不是“实现没开始”，而是**卡片契约不闭合**，继续编码会违反白名单边界。

**后续修复建议**
1. 先修 `C03` 契约：把 `scripts/check_workflow_contract.py` 纳入 file whitelist；或
2. 拆一张独立卡片，专门实现 `legacy_wrapper_compat` mode 与兼容性自检；
3. 明确 wrapper 兼容测试不应依赖可能递归回流的新入口分发链路。

---

### WF-08 `clarify_consistency_check` 缺字段导致 coverage 校验误报

**现象**
- `check_plan_vk_coverage.py` 初始校验时，`clarify_consistency_check` 缺少 4 个关键字段，导致结果 `ok=false`。

**现场处理**
- 已完成字段补齐，使 `check_plan_vk_coverage.py` 返回 `ok=true`。

**后续修复建议**
1. 给 `clarify_consistency_check` 机读区块增加 schema 级字段完整性检查；
2. 在 `jjk-plan`/`jjk-vkplan` 之间增加更早期的 fail-fast。

---

### WF-09 `vk_cards.json` 顶层缺少 `task_to_pr_mapping`

**现象**
- `cardrun bootstrap` 报：
  - `CARDRUN_PR_MAPPING_MISSING`

**现场处理**
- 已补齐 `vk_cards.json` 顶层 `task_to_pr_mapping`，使 bootstrap 恢复可用。

**后续修复建议**
1. 为 `vk_cards.json` 增加顶层 schema 校验；
2. 对 `bootstrap` 增加更精确的缺字段提示，输出缺失路径而不是仅报通用错误码。

---

### WF-10 `logs/` 被 `.gitignore` 忽略导致 usage 证据默认不入提交

**现象**
- `C05` 新增的 usage 观测文件位于：
  - `logs/workflow-gate-usage.jsonl`
- 该路径被 `.gitignore` 忽略，常规 `git add` 不会纳入提交。

**影响**
- `C05` 已完成“代码能力”，但若忘记 `git add -f`，提交中会缺失观测基线，导致后续 `C07`/`G01` 只能看到能力看不到证据。

**现场处理**
- 本轮通过人工约定：提交 usage 观测卡时必须显式执行：
  - `git add -f logs/workflow-gate-usage.jsonl`

**后续修复建议**
1. 为 workflow-gate usage 日志单独定义产物策略：提交基线样本 / 运行态滚动日志二选一；
2. 若保留提交样本，建议迁到非忽略目录或提供导出命令；
3. 在 `C05`/`C07` 验收命令中增加“观测证据文件存在性”提示。

---

### WF-11 `C07` 退役门禁依赖 7 天 wall-clock 观测窗口

**现象**
- `C07` 新增 `full-gate` 后，真实 blocker 为：
  - `ZERO_CALL_WINDOW_NOT_MATURE`
- 当前 usage 最早观测时间约为：
  - `2026-03-06T19:58:13Z`
- 依 7 天窗口，最早放行时间约为：
  - `2026-03-13T19:58:13Z` 之后。

**影响**
- `jjk-cardrun` 的“同轮串行执行”可以完成 `C01-C06`，但无法在同一轮自然完成 `C07 -> G01` 的最终放行；
- 若工程流没有区分“门禁建设完成”和“时间窗放行完成”，执行器容易被误判为卡死。

**结论**
- 这是**设计上正确但调度上未显式建模**的问题：`C07` 不应为了收尾而绕过 7 天窗口，而应输出真实阻断并等待时间成熟。

**后续修复建议**
1. 将 `C07` 拆成“门禁能力建设完成”和“时间窗成熟后退役放行”两个阶段状态；
2. 在 `cardrun`/`wt-flow verify` 中显式支持 time-gated blocker，避免误判为普通失败；
3. 在任务文档中记录 `eligible_after_utc`，作为后续恢复执行的唯一放行时刻。

---

### WF-12 `G01` 工作流文档仍引用旧脚本命令

**现象**
- 当前 `WS-G01_G01_全链路验收门禁.md` 仍要求执行：
  - `python3 scripts/check_clarify_plan_alignment.py ...`
  - `python3 scripts/check_plan_vk_coverage.py ...`
- 但 `C04` 已把命令/技能/文档口径迁移到统一入口 `scripts/check_workflow_contract.py`。

**影响**
- 实际实现已统一入口，验收文档却仍按旧命令表述，造成“实现收敛、文档回退”的双口径；
- 后续若继续推进 legacy wrapper 退役，`G01` 会把过时命令继续固化到验收链路。

**现场结论**
- 本轮以统一入口与 `v3` 退役口径为准，`G01` 文档需要在后续卡片中补迁移，而不应倒逼代码回退。

**后续修复建议**
1. 更新 `WS-G01` 的 acceptance / check_cmd 为统一入口调用；
2. 同步 `.cursor/commands/`、`.agents/skills/` 与任务拆解文档，保持同一口径；
3. 为“文档命令仍引用 legacy entry”增加回归检查，避免再次漂移。

---

### WF-13 `C03` wrapper 验收未覆盖“物理薄壳化”

**现象**
- `C03` 已完成旧命令 wrapper 化，CLI 入口可正常转发到统一入口；
- 但 `C07` 新增 `full-gate` 后，`wrapper_shell` 检查显示以下文件仍保留大量旧实现代码：
  - `scripts/check_clarify_plan_alignment.py`
  - `scripts/check_plan_vk_coverage.py`
  - `scripts/check_gate_contract_consistency.py`
- 真实 blocker 为：
  - `LEGACY_WRAPPER_NOT_THIN`

**影响**
- `C03` 可以在“命令兼容”意义上完成，但并不代表“旧实现已经足够薄壳化，可进入物理退役阶段”；
- 若执行器没有把这两个完成定义拆开，团队容易误以为 wrapper 卡完成后即可进入删除阶段。

**结论**
- 这是卡片完成定义层面的缺口：`C03` 更像“兼容入口迁移完成”，而不是“legacy 实现已物理退役完成”。

**后续修复建议**
1. 为 `C03` 增加“CLI 兼容完成”与“代码体量收敛完成”的双层验收；
2. 允许 `C07` 继续承担最终物理退役判定，但必须在计划中显式声明；
3. 将 `LEGACY_WRAPPER_NOT_THIN` 写入退役前置条件，避免后续再次口径漂移。

---

### WF-14 `wt-flow verify` 多任务场景下无法自动解析 active task

**现象**
- 在 `C07` worktree 执行：
  - `bash scripts/wt-flow.sh verify C07`
- 直接报错：
  - `检测到多个任务级 _active_task.json（5 个），请显式设置 WT_FLOW_ACTIVE_TASK_FILE 或 WT_FLOW_TASK_SPLIT_DIR`
  - `无法解析任务级 state 目录：请先设置 active_task`
  - `状态文件不存在: /task-runner-state.json`

**影响**
- `verify` 阶段还没进入卡片自己的 done_gate，就先被 active task 自动发现逻辑阻断；
- 多任务并存已经是常态，该问题会直接削弱 `cardrun` 在真实仓库中的可用性。

**现场处理**
- 本轮改为显式传入：
  - `WT_FLOW_ACTIVE_TASK_FILE` 或 `WT_FLOW_TASK_SPLIT_DIR`
- 先让 `wt-flow` 锁定当前任务，再继续验证真实 blocker。

**后续修复建议**
1. `wt-flow` 优先使用当前 worktree 相邻的任务拆解目录解析 active task；
2. 当存在多个 `_active_task.json` 时，输出候选列表和推荐值，而不是直接把 state 路径解析成根目录；
3. 将 `WT_FLOW_ACTIVE_TASK_FILE` 写入 `cardrun`/`wtimp` 派发上下文，避免每轮人工补环境变量。

---

### WF-15 `wt-flow verify` 在 worktree 内错误拼接 worktree 根路径

**现象**
- 已显式设置 `WT_FLOW_ACTIVE_TASK_FILE` / `WT_FLOW_TASK_SPLIT_DIR` 后，在 `C07` worktree 内执行：
  - `bash scripts/wt-flow.sh verify C07`
- 仍报：
  - `未找到卡片 C07 的 worktree，预期路径: <当前 worktree>/.worktrees/C07`

**影响**
- 即使上下文已经明确，`wt-flow` 仍会把当前 worktree 目录继续当成 repo 根，再拼接一层 `.worktrees/...`；
- 这使得“在卡片 worktree 内自验证”这一路径不可用，只能退回主仓根目录执行。

**现场处理**
- 本轮改回主仓根目录执行 `verify`，避免 worktree 根解析偏移。

**后续修复建议**
1. 一律使用 `git rev-parse --show-toplevel` 解析当前 checkout 根，而不是依赖 `pwd` 推断；
2. 将 repo 根与 card worktree 根显式区分，避免字符串拼接型路径推导；
3. 为“从主仓执行”和“从 card worktree 执行”各补一条回归用例。

---

## 4. 修复优先级建议

| 波次 | 目标 | 建议纳入的问题 |
|---|---|---|
| Wave 1 | 恢复工程流稳定执行 | WF-02, WF-03, WF-04, WF-07, WF-14, WF-15 |
| Wave 2 | 让退役门禁可持续运行 | WF-10, WF-11, WF-12, WF-13 |
| Wave 3 | 降低误操作与调试成本 | WF-05, WF-06 |
| Wave 4 | 强化契约与回归测试 | WF-01, WF-08, WF-09 |

---

## 5. 推荐后续卡片

1. **P0**：`cardrun_dispatch JSON 回执与超时治理`
2. **P0**：`wt-flow dirty policy active-task 白名单内建化`
3. **P0**：`修正 C03 契约与 legacy_wrapper_compat 验收路径`
4. **P0**：`time-gated retirement blocker 显式建模`
5. **P1**：`workflow-gate usage 日志产物策略治理`
6. **P1**：`G01/命令/技能文档统一入口再同步`
7. **P0**：`C03 CLI 兼容 vs 物理薄壳 双层验收建模`
8. **P0**：`wt-flow active task 自动发现稳健化`
9. **P0**：`wt-flow repo_root/worktree_root 解析修正`
10. **P1**：`git porcelain 中文路径稳健解析`
11. **P1**：`wrapper/实体脚本单一真理源治理`
12. **P1**：`clarify/vk_cards schema 回归测试`

---

## 6. 关联证据

- 执行链相关文件：
  - `scripts/coder4/wt-flow.sh`
  - `scripts/check_workflow_contract.py`
  - `scripts/check_clarify_plan_alignment.py`
  - `scripts/check_plan_vk_coverage.py`
  - `scripts/check_gate_contract_consistency.py`
  - `scripts/check_integration_gate.py`
- 当前任务状态目录：
  - `docs/内部参考/任务拆解/2026-03-06_工程减法治理/.state/PP-20260306-workflow-gate-retirement/`
- 当前卡片契约：
  - `docs/内部参考/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C03_P1_L1旧脚本wrapper兼容壳.md`
  - `docs/内部参考/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C07_P3_删除旧实现与兼容壳收口.md`
  - `docs/内部参考/任务拆解/2026-03-06_工程减法治理/workstreams/WS-G01_G01_全链路验收门禁.md`
- 退役门禁观测证据：
  - `logs/workflow-gate-usage.jsonl`
  - `python3 scripts/check_workflow_contract.py --mode full-gate --task-split-dir docs/内部参考/任务拆解/2026-03-06_工程减法治理 --baseline master --output -`

