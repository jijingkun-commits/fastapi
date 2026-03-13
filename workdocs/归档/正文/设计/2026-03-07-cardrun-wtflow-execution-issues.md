# CardRun / WT-Flow 工程流执行问题记录

> **文档类型**: 问题记录与后续修复输入
> **创建日期**: 2026-03-07
> **更新日期**: 2026-03-08
> **问题范围**: `jjk-cardrun`, `jjk-wtimp`, `scripts/coder4/wt-flow.sh`, `coder4_bootstrap_kernel`, `check_workflow_contract`
> **触发任务**: `PP-20260306-workflow-gate-retirement`
> **记录目的**: 沉淀本轮实际执行中暴露的工程流缺陷，供后续专项修复

---

## 1. 结论摘要

本轮执行过程中，真正阻断推进的不是业务代码，而是**工程流执行器、状态白名单、卡片契约一致性**三个层面的缺口。

其中：

1. **已现场修复（含已合入主线）**的问题包括：
   - `wt-flow verify` 白名单缺少 `rg`，导致 `C01` done_gate 被误阻断；
   - `clarify_consistency_check` 缺字段，导致 `check_plan_vk_coverage.py` 初始校验失败；
   - `vk_cards.json` 顶层缺少 `task_to_pr_mapping`，导致 `cardrun bootstrap` 阻断；
   - `wt-flow verify` 的 active task / worktree root 解析不稳，导致 `C07` 无法进入真实 done_gate；
   - `C07 full-gate` 把 7 天观察窗口建模为阻断型退役门禁，导致执行器被非即时条件卡住；
   - `jjk-plan/jjk-vkplan` 缺少“时间窗阻断禁止”约束，导致类似卡片可再次被生成；
   - `G01` 文档口径仍引用旧命令，且 `C07 full-gate` 曾把 post-merge `integration_gate` 混入 pre-merge verify；
   - `C03` 兼容壳只做了 CLI 转发，未完成物理薄壳化；
   - `integration_gate` 在 gate worktree 内默认读取 worktree-local `.state`，导致 `G01` 误判 merge_results 缺失；
   - `wt-flow` / `bootstrap kernel` 已自动把 active task 的 `.state/<task_key>/` 纳入 dirty whitelist，merge/bootstrap 不再要求手传整段 whitelist。
2. **仍需后续系统性修复**的问题包括：
   - `wtimp dispatch` JSON 回执/超时机制不稳；
   - 中文路径 dirty 检测虽已不再依赖 `core.quotePath=false`，但仍建议后续切到 `git status --porcelain -z` 做更稳健解析；
   - `scripts/wt-flow.sh` wrapper 脱离仓库路径后不可移植；
   - `C03` 卡片契约本身自冲突，无法在不违约的前提下继续执行；
   - `logs/` 产物被忽略，usage 观测结果默认不会进入提交证据；
   - `apply_patch` 指令与实际可用工具集不一致，容易触发执行器告警；
   - 默认 `python3` 与项目虚拟环境不一致，定向测试容易误报“缺少 pytest”；
   - 单测红绿循环会被全局 coverage 门槛掩盖真实失败原因。

---

## 2. 问题总表

| 编号 | 优先级 | 问题 | 影响 | 当前状态 | 临时绕过/现场处理 | 后续建议 |
|---|---|---|---|---|---|---|
| WF-01 | P0 | `wt-flow verify` 白名单缺少 `rg` | `C01` 无法 done_gate | 已现场修复 | 将 `rg` 加入 `ALLOWED_PREFIXES` | 补更系统的命令白名单回归测试 |
| WF-02 | P0 | `wtimp dispatch` 未及时返回 JSON 回执 | `cardrun` 主控卡在 dispatch | 已修复 | 已补 dispatch timeout 契约下传、process-group 清理、唯一 JSON contract 校验 | 后续仅保留分级 timeout 策略评估，不再把 session 清理留给人工 |
| WF-03 | P0 | `.state` 运行态文件会持续污染工作区 | `bootstrap/merge` 易被 dirty policy 阻断 | 已现场修复 | `wt-flow` / `bootstrap kernel` 已自动追加 active task `.state/<task_key>/` whitelist | 继续细化 lock/session 文件分层与运行态产物治理 |
| WF-04 | P1 | 中文路径 dirty 检测依赖 `core.quotePath=false` | 白名单对中文路径匹配失败 | 已修复 | `wt-flow` / `bootstrap kernel` 已统一切到 `git status --porcelain -z`，并补中文/空格/rename/箭头文件名回归 | 后续只保留 parser 复用与 stale dirty 分层治理 |
| WF-05 | P1 | `scripts/wt-flow.sh` 只是 wrapper，脱离仓库复制会失效 | 调试脚本副本容易误用 | 已修复 | wrapper 脱离仓库布局时会 fail-fast 提示“单一真理源=实体脚本” | 后续可再统一其他 wrapper 的错误提示风格 |
| WF-06 | P1 | 历史 `.state` 路径与当前 task_key 容易混淆 | 容易误判真理源、误读状态 | 已修复 | `wt-flow status` 已显式输出 active task/state root/stale candidates 对照 | 后续只补归档/清理策略，不再让人工靠目录名猜真理源 |
| WF-07 | P0 | `C03` 卡片契约自冲突 | 不能“干净地”继续 wrapper 卡 | 已修复 | 已确认 `WS-C03` / `vk_cards.json` 均纳入 `scripts/check_workflow_contract.py`，且 `legacy_wrapper_compat` 验收命令可通过 | 后续以回归测试防止 contract 漂移回流 |
| WF-08 | P1 | `clarify_consistency_check` 缺字段导致 coverage 检查误报 | `cardrun` 前置校验初始失败 | 已现场修复 | 已补 4 个缺失字段 | 给契约字段完整性补回归测试 |
| WF-09 | P1 | `vk_cards.json` 顶层缺少 `task_to_pr_mapping` | `bootstrap` 报 `CARDRUN_PR_MAPPING_MISSING` | 已现场修复 | 已补顶层映射 | 给 `vkplan` 产物增加 schema 级校验 |
| WF-10 | P1 | `logs/` 被 `.gitignore` 忽略 | `C05` usage 观测证据默认不会随提交落库 | 已修复 | 运行态日志仍留在 `logs/`，提交证据改由 `usage-report` 显式导出到 tracked `evidence/` 目录 | 后续只需让相关验收入口统一消费 report，不再依赖 `git add -f logs/...` |
| WF-11 | P0 | `C07 full-gate` 把 7 天观察窗口建模为阻断型退役门禁 | `full-gate` 被 wall-clock 条件拦住，真实 blocker 容易被掩盖 | 已现场修复（已合入主线） | 移除 `ZERO_CALL_WINDOW_NOT_MATURE` / `USAGE_WINDOW_EMPTY`；`window-days` 仅保留报表语义 | 给 `full-gate` 补回归测试，禁止时间成熟条件再次回流到退役阻断 |
| WF-12 | P1 | `G01` 工作流文档仍引用旧脚本命令 | 验收文档口径与统一入口迁移结果不一致 | 已现场修复（已合入主线） | 已切换到统一入口，并补入 `integration_gate` 主干可见性校验 | 将 `G01` 命令漂移检查纳入默认回归，避免再次回退到 legacy 命令 |
| WF-13 | P0 | `C03` wrapper 验收未覆盖“物理薄壳化” | `C07` 才首次暴露 legacy 大体量实现仍驻留 | 已现场修复（已合入主线） | 将实现迁到 `workflow_contract_*_impl.py`，旧脚本收敛为 31 行薄壳 | 为“模块导入面 + CLI 壳厚度”补双重回归，防止再次只包一层壳 |
| WF-14 | P0 | `wt-flow verify` 多任务场景下无法自动解析 active task | `C07` verify 直接阻断，无法进入真实 done_gate | 已现场修复 | 新增 branch-task 提示解析 + `WT_FLOW_TASK_SPLIT_DIR` 直接解析 | 给 `wt-flow` 增加 worktree 上下文优先级与更稳健的 active task 发现逻辑 |
| WF-15 | P0 | `wt-flow verify` 在 worktree 内错误拼接 worktree 根路径 | `C07` 在正确 worktree 内仍无法直接 verify | 已现场修复 | 拆分 `CHECKOUT_ROOT/COMMON_ROOT`，并把主仓绝对路径归一化到当前 worktree | 统一以 `git rev-parse --show-toplevel` 解析 repo 根，禁止依赖当前 cwd 猜测 |
| WF-16 | P0 | `jjk-plan/jjk-vkplan` 未禁止时间窗成熟条件进入 `done_gate` | 后续 split 仍可能生成“等 7 天才能继续”的串行阻断卡 | 已现场修复（已合入主线） | 新增 `planning_temporal_gate` 校验并更新 plan/vkplan/模板规则 | 将该校验接入默认规划链，禁止生成不可即时验证的阻断卡 |
| WF-17 | P0 | `C07 full-gate` 曾把 post-merge `integration_gate` 混入 pre-merge verify | `verify -> merge` 流程天然冲突，导致 C07 未合并前无法通过 full-gate | 已现场修复（已合入主线） | `full-gate` 默认跳过 `integration_gate`；显式 `--include-integration` 才阻断 | 将 post-merge 主干可见性校验下沉到 `G01` / 独立命令，固化 pre/post-merge 边界 |
| WF-18 | P1 | `wt-flow merge` 在 card worktree 内直接切回基线分支 | 当 `master` 已被主工作区占用时，merge 在 worktree 内直接失败 | 已现场修复 | merge/cleanup 统一切到 `common repo root` 执行，card worktree 仅承担 rebase 与会话工作目录 | 为主仓/卡片 worktree merge 与 cleanup 持续补回归，防止再次把 checkout_root 当基线仓 |
| WF-19 | P0 | `integration_gate` 默认读取 worktree-local `.state` 副本 | `G01` 在 gate worktree 内误报 `state.merge_results` 缺失 | 已现场修复（已合入主线） | 新增 common repo state 解析，默认回到主仓运行态真理源 | 为 worktree gate / integration_gate / canonical state path 补回归测试，防止再次读取 checkout 副本 |
| WF-20 | P1 | `apply_patch` 指令与实际可用工具集不一致 | 代理容易因“应使用 apply_patch”告警反复空转，影响单卡执行效率 | 已修复（仓内侧） | `AGENTS` / 工程流手册已冻结“按实际工具面编辑 + `APPLY_PATCH_TOOL_UNAVAILABLE_FALLBACK`”契约 | 后续只需推动平台侧提示与真实工具暴露对齐 |
| WF-21 | P1 | 默认 `python3` 与项目虚拟环境不一致 | 定向测试会先失败在 `No module named pytest`，掩盖真实回归结果 | 已修复 | 已新增 `scripts/repo_python.sh` 作为仓级测试解释器入口，当前解析到 `venv/bin/python` | 后续统一让测试/验证入口复用该脚本，不再裸用 `python3 -m pytest` |
| WF-22 | P1 | 单测红绿循环被全局 coverage 门槛干扰 | RED 阶段即使命中真实失败，也会被仓库总 coverage<阈值二次覆盖，降低问题定位效率 | 已修复 | 已新增 `scripts/pytest_targeted.sh` 作为开发期定向入口，固定 `--no-cov` 并拒绝 `--cov*` 混用 | 最终收口继续保留 coverage 门禁，但不得回流到定向红绿命令 |

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

**本轮修复进展（2026-03-07）**
1. 已确认 bridge 并非完全没有超时逻辑，而是默认超时固定为 `1800s`，且 kernel 没有配置入口把更短超时下传给 dispatch；
2. 已新增 `dispatch_timeout_seconds` 契约，解析优先级为：`CLI override -> env(CODER4_DISPATCH_TIMEOUT_SECONDS) -> active_task.dispatch_timeout_seconds -> 默认值`；
3. 当前 `build_wtimp_dispatch_request()` 会把 timeout 显式下传到 `WtimpDispatchRequest`；
4. 已补回归测试，覆盖 timeout 解析、timeout 下传、timeout 错误映射。

**本窗口收尾结果（2026-03-08）**
1. `wtimp_dispatch_bridge` 已从 `subprocess.run(...)` 切换到受控 `Popen(..., start_new_session=True)` 路径，timeout / 非零退出 / 非法回执都会附带 `session_cleanup` 证据，并尝试回收当前 process-group；
2. JSON 提取已废弃“任意 dict 兜底”策略，改为只接受唯一一个满足 dispatch contract 的结果对象；无 contract payload 或出现多个候选 payload 都会 `fail-fast` 为 `CARDRUN_EXECUTION_RESULT_INVALID`；
3. payload 校验已升级为强类型收口：`ok` 必须为 `bool`，`changed_files` 必须为 `list[str]`，`acceptance_results` 必须为 `list[dict]`，避免日志漂移或宽松 coercion 伪造成功证据；
4. 定向回归已通过：`tests/unit/test_coder4_wtimp_dispatch_bridge.py` 与 `tests/unit/test_coder4_dispatch_executor.py` 当前合计 `13 passed`。

**后续修复建议**
1. 后续若 `wtimp` 引入主动 `double-fork`/脱离 session 的后台任务，需要再评估跨 session 清理策略；
2. 视真实卡片耗时分布，再决定默认 `600s` 是否拆成不同卡片类型的分级 timeout。

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
  - `WT_FLOW_DIRTY_WHITELIST='workdocs/设计/,workdocs/归档/正文/设计/,workdocs/归档/正文/需求/,.artifacts/states/task_splits/2026-03-06_工程减法治理/PP-20260306-workflow-gate-retirement/'`

**本次修复策略（2026-03-07）**
1. `wt-flow` 与 `bootstrap kernel` 都应基于当前 `active_task.task_split_dir + task_key` 自动推导 `.state/<task_key>/` 前缀；
2. 自动推导出的 `.state/<task_key>/` 只作为 dirty whitelist 的追加项，不覆盖调用方显式传入的自定义白名单；
3. 运行态 `.state/<task_key>/` 内的 `task-runner-state.json`、`task-ledger.jsonl`、`coder4-idempotency.json`、lock/session 文件默认放行，但其他仓库脏改动仍应继续阻断。

**本轮现场修复（已完成）**
1. `scripts/coder4/wt-flow.sh` 新增 active-task state prefix 推导，`_dirty_whitelist_csv()` 会自动追加：
   - `.artifacts/states/task_splits/<task_split_dir>/<task_key>/`
2. `scripts/coder4/coder4_bootstrap_kernel.py` 新增 `merge_dirty_whitelist()`，会把 active task 的 `.state/<task_key>/` 自动并入 dirty whitelist；
3. `wt-flow merge` 与 `build_kernel_context()` 现在都能在 active task 运行态文件变脏时继续执行，不再要求每次手传整段 whitelist；
4. 为了让新增 whitelist 在中文路径下也生效，本轮同时补了 git quoted path 解码，避免再次依赖 `core.quotePath=false`。

**后续修复建议**
1. 继续区分“运行态真理源脏文件”与“用户未提交变更”；
2. 对 lock/session 文件做专门处理，避免反复干扰 merge；
3. 后续可继续收敛到 `git status --porcelain -z`，进一步提升路径解析稳健性。

---

### WF-04 中文路径 dirty 检测依赖 `core.quotePath=false`

**现象**
- 初始状态下，中文路径在 `git status --porcelain` 中被转义，导致 dirty whitelist 对中文目录匹配失败。

**现场处理（旧绕过）**
- 早期临时依赖：
  - `git config --local core.quotePath false`

**本轮修复进展**
1. `wt-flow.sh` 新增 `_decode_git_quoted_path()`，dirty path 提取不再直接依赖未转义路径；
2. `coder4_bootstrap_kernel.py` 新增 `_decode_git_status_path()`，会把 git quoted path 还原为真实 UTF-8 路径；
3. `WF-03` 新增回归测试已经覆盖“中文 task split dir + quoted path + active-task state whitelist”场景。

**本窗口收尾结果（2026-03-08）**
1. `wt-flow.sh` 与 `coder4_bootstrap_kernel.py` 的 dirty path 真理源已统一切到 `git status --porcelain -z --untracked-files=no`，不再依赖文本行级解析；
2. rename/copy 现在按 NUL 分隔记录读取“目标路径”，不再依赖 `"old -> new"` 的文本箭头切割，因此文件名自身包含 ` -> ` 时也能稳定命中 whitelist；
3. 旧的 quoted-path decode 补丁已从主路径删除：shell 侧不再做引号/转义还原，Python 侧不再做 `ast.literal_eval` 型补码；
4. 已补回归：覆盖“中文目录 + 空格 + rename + 文件名包含 ` -> `”场景；定向与相邻回归当前均通过。

**问题本质**
- 当前 dirty path 提取逻辑原本默认依赖未转义路径字符串，不够稳健；本轮已先修正最直接的 quoted path 问题，但底层协议仍可进一步升级。

**后续修复建议**
1. 后续若 `wt-flow` 与 kernel 继续扩展 dirty policy，优先抽取共享解析契约，避免 shell/python 两侧再次漂移；
2. 将来可继续细分“运行态真理源脏改”与“真实用户改动”两类 evidence，但不应回退到文本补码方案。

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
1. 后续把同类 wrapper 的错误提示风格统一到一个 helper，避免文案再次漂移；
2. 若需脱离仓库调试，始终复制实体脚本 `scripts/coder4/wt-flow.sh`，不要再复制 wrapper；
3. 新增 wrapper 时应同步声明“单一真理源 + 脱仓 fail-fast”规则。

**本窗口收尾结果（2026-03-08）**
1. `scripts/wt-flow.sh` 现在会在实体脚本缺失时输出明确报错，说明自己只是 wrapper，并指向单一真理源 `scripts/coder4/wt-flow.sh`；
2. 仓库内正常布局下，wrapper 仍保持透明转发，不改变既有 CLI 入口行为；
3. 已在工程流手册中明确：`scripts/wt-flow.sh` 仅是 wrapper，调试复制请使用实体脚本。

---

### WF-06 历史状态目录与当前 task_key 容易混淆

**现象**
- 现场曾看到历史残留目录 `.state/PP-20260306-ENGINEERING-LEAN-GOV/`，但当前真实任务是：
  - `PP-20260306-workflow-gate-retirement`

**影响**
- 若误读历史目录，容易错误判断 active session、ledger、task-runner-state 的真理源。

**根因**
- `wt-flow status` 之前只展示 session/worktree 级信息，没有把“当前 active task 文件、解析得到的 task_key、命中的 state root、同 split_dir 下的历史 state 候选”显式打印出来；
- 一旦目录里同时存在历史 `.state/<old_task_key>/` 与当前 `.state/<active_task_key>/`，人工只能靠目录名猜测真理源，状态发现职责与历史残留治理职责被混在一起。

**本窗口收尾结果（2026-03-08）**
1. `scripts/coder4/wt-flow.sh status` 现在会先输出 `ACTIVE_TASK_FILE`、`ACTIVE_TASK_SPLIT_DIR`、`ACTIVE_TASK_KEY`、`TASK_STATE_ROOT`，把当前解析到的状态真理源显式化；
2. 同一 `task_split_dir` 下若存在其他 `.state/<task_key>/` 目录，会额外输出 `STALE_STATE_CANDIDATES=<...>`；当前 active task 会被排除，不再要求人工自己比对目录树；
3. 已补最小回归 `test_wt_flow_status_reports_active_state_root_and_stale_candidates`，覆盖“active state root + stale state candidates 同时存在”的诊断场景；
4. 相邻回归已通过：`tests/unit/test_coder4_wt_flow_verified_state.py` 与 `tests/unit/test_wt_flow_wrapper_entrypoint.py` 当前合计 `10 passed`。

**后续修复建议**
1. 若后续新增历史状态清理/归档能力，应保持为独立命令，不要把 `status` 再做成带副作用的清理入口；
2. 为历史 `.state/<task_key>/` 制定归档/清理策略，减少 stale candidates 长期堆积；
3. 后续若引入更强的状态浏览器/UI，也应继续保留“active root 明示 + stale candidates 提示”的只读诊断契约。

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

**本窗口确认结果（2026-03-08）**
1. `WS-C03_P1_L1旧脚本wrapper兼容壳.md` 与 `vk_cards.json` 当前都已把 `scripts/check_workflow_contract.py` 纳入白名单 / `file_scope`；
2. 真实验收命令 `python3 scripts/check_workflow_contract.py --mode legacy_wrapper_compat --task-split-dir workdocs/任务拆解/2026-03-06_工程减法治理 --output -` 当前返回 `ok=true`；
3. 因此 `WF-07` 的原始 blocker 已被后续主线演进顺带修复，本窗口新增回归测试，仅负责把问题文档状态从“待修复”回填为“已修复”。

**后续修复建议**
1. 为 `C03` 契约闭合补默认回归，防止 `WS` / `vk_cards` / 验收命令再次漂移；
2. 后续若调整 wrapper 退役策略，应同步校验 `file_scope`、`acceptance_checks` 与 `legacy_wrapper_compat` runner 的一致性；
3. 执行器侧不应再为这类 contract 漂移添加 fallback，保持“契约先闭合，再执行”的原则。

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

**问题本质**
- 运行态滚动日志与应入提交的验收证据被错误建模成同一个文件，导致“日志路径被忽略”和“证据需要入库”天然冲突。

**本窗口收尾结果（2026-03-08）**
1. `logs/workflow-gate-usage.jsonl` 继续只承担运行态观测台账；`usage-report` 新增 `--log-path` 与 `--report-output` 契约，把可提交证据显式导出到 tracked report 文件；
2. `C05` 契约已改为导出 `workdocs/任务拆解/2026-03-06_工程减法治理/reports/workflow-gate-usage-report.json`，`file_scope` 不再要求提交 ignored `logs/` 文件；
3. `workflow-gate-retirement` 的设计/需求/实现计划、WS 文档与 `vk_cards.json` 已统一改为同一条导出命令：
   - `python3 scripts/check_workflow_contract.py --mode usage-report --log-path logs/workflow-gate-usage.jsonl --report-output workdocs/任务拆解/2026-03-06_工程减法治理/reports/workflow-gate-usage-report.json`
4. 已补最小回归 `tests/unit/test_workflow_gate_usage_report_contract.py`，并联相邻 `tests/unit/test_check_workflow_contract_temporal_rules.py` 当前合计 `5 passed`。

**后续修复建议**
1. 其他需要“运行态日志 + 提交证据”双轨的链路，应复用“runtime log + exported report”模型，不要再把 ignored log 当成提交产物；
2. 若后续 `full-gate` / `G01` 需要消费 usage 证据，优先消费 tracked report，而不是直接依赖 ignored `logs/`；
3. 如需保留人工查看日志体验，可继续保留 `logs/` 作为滚动台账，但不再承担提交证据职责。

---

### WF-11 `C07 full-gate` 把 7 天观察窗口建模为阻断型退役门禁

**现象**
- `C07` 新增 `full-gate` 后，真实 blocker 一度包含：
  - `ZERO_CALL_WINDOW_NOT_MATURE`
  - `USAGE_WINDOW_EMPTY`
- 这会让门禁在没有 legacy 调用的情况下，仍然因为 wall-clock 未成熟而失败。

**影响**
- `jjk-cardrun` 会被“等时间过去”而不是“修真实问题”阻断；
- 更严重的是，真实 blocker `LEGACY_WRAPPER_NOT_THIN` 会被时间窗噪音掩盖，执行顺序被扭曲。

**本轮现场修复（已合入主线）**
- 已在 `scripts/check_workflow_contract.py` 中移除：
  - `ZERO_CALL_WINDOW_NOT_MATURE`
  - `USAGE_WINDOW_EMPTY`
- `--window-days` 仅保留 usage 报表语义，不再参与退役放行阻断；
- 实测 `full-gate` 现在不再因时间窗口失败，当前只剩真实 blocker：
  - `LEGACY_WRAPPER_NOT_THIN`

**结论**
- 观察维度可以存在，但只能作为报表/证据维度，不能进入 `done_gate` / `acceptance_checks` / 串行收口阻断。

**后续修复建议**
1. 继续把 `legacy usage / wrapper 厚度 / TTL 违规` 这类可即时判定条件作为唯一阻断来源；
2. 若必须保留时间统计口径，只能标注为 `observation_evidence_only`，不得进入完成条件；
3. 给 `full-gate` 补一条回归测试，确保以后不会再回引时间成熟 blocker。

---

### WF-16 `jjk-plan/jjk-vkplan` 未禁止时间窗成熟阻断建模

**现象**
- 本轮任务文档、卡片和模板曾出现：
  - `连续7天零调用`
  - `--window-days 7`
  - `支持7天零调用聚合判定`
- 这些表述会被下游误建模为 `done_gate` / `acceptance_checks`，最终生成不可即时收口的串行卡。

**影响**
- 计划阶段就把不可即时验证的自然时间条件塞进串行卡，`cardrun` 再稳定也会被设计层阻断；
- 同类问题会在未来 split 中重复出现。

**本轮现场修复（已合入主线）**
- 已新增：
  - `python3 scripts/check_workflow_contract.py --mode planning_temporal_gate ...`
- 已同步更新：
  - `.cursor/commands/jjk-plan.md`
  - `.agents/skills/jjk-plan/SKILL.md`
  - `.cursor/commands/jjk-vkplan.md`
  - `.agents/skills/jjk-vkplan/SKILL.md`
  - 相关 plan/vkplan 模板
- 新规则明确：禁止把依赖自然时间流逝、观察窗口成熟、TTL 到期的条件生成到 `done_gate` / `acceptance_checks` / 串行阻断卡。

**结论**
- 这个问题的根因不在 `cardrun`，而在规划链建模规则缺失；必须在计划生成阶段 fail-fast，而不是把不可执行卡交给执行器兜底。

**后续修复建议**
1. 将 `planning_temporal_gate` 作为 `jjk-plan -> jjk-vkplan` 默认校验项；
2. 对 `parallel_plan` / `vk_cards.json` / `implementation_plan` 增加 schema/关键字回归测试；
3. 以后如需观察期，只允许写成说明性文本或人工放行说明，不得作为自动阻断条件。

---

### WF-12 `G01` 工作流文档仍引用旧脚本命令

**现象**
- `WS-G01_G01_全链路验收门禁.md` 一度仍要求执行：
  - `python3 scripts/check_clarify_plan_alignment.py ...`
  - `python3 scripts/check_plan_vk_coverage.py ...`
- 这与统一入口 `scripts/check_workflow_contract.py` 的实际执行口径不一致。

**本轮现场修复（已合入主线）**
- 已将 `G01` 的验收命令改为统一入口：
  - `--mode clarify_plan`
  - `--mode plan_vk_coverage`
  - `--mode integration_gate`
- 同步把 `integration_gate` 的主干可见性职责显式放回 `G01`，不再隐含混在 `C07 full-gate` 里。

**结论**
- `G01` 现在重新承担 post-merge 门禁职责，`C07` 只负责 pre-merge 收口，职责边界恢复清晰。

**后续修复建议**
1. 为 `G01` 文档命令漂移增加回归检查；
2. 将“统一入口 + gate 职责归属”写入模板，避免下次又回到 legacy 命令；
3. 合并后再补一次 `G01` 实跑证据，确认文档与执行链一致。

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

**本轮现场修复（已合入主线）**
- 已将实际实现迁移到内部模块：
  - `scripts/workflow_contract_clarify_plan_impl.py`
  - `scripts/workflow_contract_plan_vk_coverage_impl.py`
  - `scripts/workflow_contract_gate_contract_impl.py`
- 旧脚本现在仅保留：
  - 模块导入面 re-export
  - deprecation 提示
  - 统一入口 CLI 转发
- 当前壳体行数已收敛到 `31` 行，并通过 `legacy_wrapper_compat` / `wrapper_shell` 双校验。

**结论**
- “CLI 兼容”与“物理薄壳化”这两个完成定义都已被落实，但该经验需要补回归，防止未来再次只停留在表层 wrapper。

**后续修复建议**
1. 为“导入面不破 + 壳厚度达标”补双重回归；
2. 在 wrapper 退役类卡片中显式区分“命令兼容完成”和“物理薄壳完成”；
3. 后续若继续收敛，可再抽一个公共 wrapper helper，减少 4 个壳体模板重复。

---

### WF-17 `C07 full-gate` 曾把 post-merge `integration_gate` 混入 pre-merge verify

**现象**
- `jjk-cardrun` 的主链是：
  - `verify -> merge`
- 但 `C07` 的 `full-gate` 一度直接内联 `integration_gate`，而 `integration_gate` 的语义是：
  - 实现卡必须已合并且主干可见
- 结果是 `C07` 在未 merge 前，会天然被 `baseline_visible / state.merge_results` 阻断。

**影响**
- 这不是业务失败，而是 pre-merge / post-merge 门禁边界混淆；
- 会让 `verify` 阶段永远卡在“你还没 merge，所以不能 verify”的环路里。

**本轮现场修复（已合入主线）**
- 已将 `full-gate` 明确改为：
  - `C07 pre-merge 收口门禁`
- 默认行为改为：
  - 跳过 `integration_gate`
- 如需强制检查 post-merge 主干可见性，必须显式传：
  - `--include-integration`
- 同时已把 `integration_gate` 职责回放到 `G01` 文档与统一入口命令中。

**结论**
- `full-gate` 与 `integration_gate` 不是同一阶段的门禁；必须严格区分 `pre-merge verify` 与 `post-merge visibility`。

**后续修复建议**
1. 为 `full-gate default` 与 `full-gate --include-integration` 各补一条回归测试；
2. 在卡片模板中显式标注“该门禁属于 pre-merge / post-merge 哪一阶段”；
3. 合并后再补 `integration_gate` 的状态一致性治理，确保 `state.merge_results` 能反映真实 merge 结果。

---

### WF-18 `wt-flow merge` 在 card worktree 内直接切回基线分支

**现象**
- 在 `C07` card worktree 内直接执行：
  - `bash scripts/wt-flow.sh merge`
- 会先尝试切回目标基线分支：
  - `master`
- 但 `master` 已在主工作区占用时，Git 直接报：
  - `fatal: 'master' is already used by worktree at '/Users/jijingkun/bojxAI/fastapi'`

**影响**
- 即使卡片已经 `verified` 且分支内容正确，仍无法在 card worktree 内完成 merge；
- 执行器必须退回主仓根目录 merge，增加了上下文切换和脏工作区处理复杂度。

**现场处理（旧绕过）**
- 本轮初期曾改为：
  - 从主仓根目录执行 `wt-flow merge`
  - 对无关 dirty 文件使用临时 `stash -> merge -> pop`

**结论**
- 这是 merge 执行器与 Git worktree 约束不兼容的问题，不应继续要求“在 card worktree 内切回基线分支”。

**后续修复建议**
1. merge 路径应显式区分 `checkout_root` 与 `common_repo_root`；
2. 需要在主仓上下文完成基线分支 merge，而不是在 card worktree 内强切基线；
3. 为“主仓 merge / card worktree merge”各补一条回归测试。

**本次修复策略（2026-03-07）**
1. `cmd_merge` 读取 session/worktree 信息后，rebase 仍在 card worktree 执行；
2. 真正的 `checkout + merge + merge_commit` 收口统一切到 `common_repo_root` 执行；
3. `dirty policy` 也统一在 `common_repo_root` 评估，避免误把当前 card worktree 当成基线仓；
4. 默认不再要求“当前执行目录必须能 checkout base branch”，从而消除 `master already used by worktree` 这一类结构性阻断。

**本轮现场修复（已完成）**
1. `scripts/coder4/wt-flow.sh` 新增 `_git_driver_root()`，统一解析 Git 管理根；
2. `cmd_merge` 的 `checkout/merge` 与 dirty policy 已切换到 `common repo root`；
3. `cmd_cleanup` 也改为在 `common repo root` 执行，避免在待删除 card worktree 内自删；
4. 已补回归测试：
   - `tests/unit/test_coder4_wt_flow_verified_state.py::test_wt_flow_merge_from_card_worktree_uses_common_repo_driver`
   - `tests/unit/test_coder4_wt_flow_verified_state.py::test_wt_flow_merge_from_card_worktree_cleans_up_with_common_repo_driver`
5. 验证命令：
   - `venv/bin/python -m pytest tests/unit/test_coder4_wt_flow_verified_state.py --no-cov -q`

---

### WF-19 `integration_gate` 默认读取 worktree-local `.state` 副本

**现象**
- `G01` gate worktree 内执行：
  - `python3 scripts/check_workflow_contract.py --mode integration_gate ...`
- 会默认把 `state_dir` 解析到当前 worktree 下：
  - `<g01-worktree>/docs/.../.state`
- 该路径是 checkout 副本，不是主仓运行态真理源，因此会误报：
  - `state.merge_results 缺失: ['C03', 'C04', 'C05', 'C06', 'C07']`

**影响**
- `G01` 会在工作树内错误失败，而同一命令在主仓根目录执行却能通过；
- 这会让 gate 的结果依赖执行位置，破坏工程流稳定性。

**本轮现场修复（已合入主线）**
- 已在 `scripts/check_workflow_contract.py` 新增 common repo state 解析；
- `integration_gate` 在默认 `.state` 场景下，会优先回到主仓运行态真理源；
- 已补回归测试，覆盖“worktree 默认回主仓 `.state`”行为。

**结论**
- 运行态真理源只能来自 common repo，不应从任意 worktree checkout 副本推断。

**后续修复建议**
1. 把 canonical state path 解析抽成公共 helper，供其他 gate / wt-flow 共用；
2. 对 `verify/merge/integration_gate` 增加 worktree 执行路径回归；
3. 明确区分“代码 checkout 路径”和“运行态真理源路径”。

---


### WF-20 `apply_patch` 指令与实际可用工具集不一致

**现象**
- 本轮执行中，系统/流程层持续强调：
  - `Use the apply_patch tool instead of exec_command`
- 但当前实际暴露给代理的工具集中并没有独立 `apply_patch` 入口，只有 `exec_command` 等通用工具。
- 这会导致代理若按提示走 `exec_command` 包装 `apply_patch`，就再次触发告警，形成无效往返。

**影响**
- 编辑动作会被无意义的工具告警打断；
- 用户需要额外人工提醒“不要这样调工具”，影响 `jjk-cardrun` / `jjk-imp` 执行稳定性；
- 指令优化前，代理难以稳定判断“应该遵从提示”还是“应该遵从实际工具面”。

**现场处理**
- 本轮改为使用 Python 直接写回文件，避免再走 `exec_command -> apply_patch` 告警路径。

**问题本质**
- 这是“系统提示 / 开发者约束 / 实际工具暴露”三者不一致的问题，本质属于工程流指令冲突，而非业务代码缺陷。

**本窗口收尾结果（2026-03-08）**
1. `AGENTS.md` 已新增“文件编辑工具契约（强制）”：文件编辑以当前会话**实际暴露**的工具集为准；若没有独立 `apply_patch` 入口，禁止通过 `exec_command` 包装 `apply_patch`；
2. 工程流手册已新增 `4.6 文件编辑工具契约`，并冻结 `APPLY_PATCH_TOOL_UNAVAILABLE_FALLBACK` 作为仓内降级标记；
3. `CLAUDE.md` 已通过 `python3 scripts/sync_rules_to_cc.py --only rules` 同步镜像，避免 Codex/Claude 入口口径再次分叉；
4. 已补最小回归 `tests/unit/test_workflow_tooling_contract_docs.py`，红灯先确认缺失，再验证当前 `2 passed`。

**后续修复建议**
1. 平台侧若仍未暴露独立 `apply_patch` 工具，就不应继续向代理发出“必须使用 apply_patch tool”的硬提示；
2. 若平台后续正式暴露独立 `apply_patch` 工具，应同步收敛系统提示与工具清单，避免仓内 fallback 长期存在；
3. 其他执行入口（如 `jjk-imp/jjk-cardrun` 的外层平台提示）若仍存在同类工具面冲突，应统一复用本条契约，不再各自发明 workaround。

---

### WF-21 默认 `python3` 与项目虚拟环境不一致

**现象**
- 本轮最初执行定向测试时使用：
  - `python3 -m pytest ...`
- 实际报错为：
  - `No module named pytest`
- 但仓库内的 `venv` / `.venv` 都已安装 pytest，改成：
  - `venv/bin/python -m pytest ...`
  即可正常运行。

**影响**
- 测试会先失败在解释器环境，而不是失败在真实业务回归；
- 用户或代理容易误判为“仓库依赖坏了”，实际只是命中了错误的 Python 入口；
- `jjk-test/jjk-verify` 若继续输出裸 `python3`，后续仍会重复踩坑。

**现场处理**
- 本轮显式改用：
  - `venv/bin/python -m pytest tests/unit/test_coder4_wt_flow_verified_state.py --no-cov -q`

**问题本质**
- 当前执行链没有先解析“仓库测试解释器真理源”，导致命令模板与仓库实际环境漂移。

**本窗口收尾结果（2026-03-08）**
1. 已新增 `scripts/repo_python.sh` 作为仓级测试解释器单一入口；解析优先级固定为：`VK_RUNTIME_VENV -> venv -> .venv -> .vibe/venv -> python3 -> python`；
2. `AGENTS.md` 已新增“测试解释器契约（强制）”，要求测试/验证命令先解析仓库解释器，禁止默认裸用 `python3 -m pytest`；
3. 测试指南已改为先执行 `bash scripts/repo_python.sh` 解析解释器，再用 `PYTHON_BIN` 运行 pytest；当前仓库实测解析结果为 `/Users/jijingkun/bojxAI/fastapi/venv/bin/python`；
4. 已补最小回归 `tests/unit/test_repo_python_script.py`，先红灯确认脚本缺位，再验证当前 `3 passed`。

**后续修复建议**
1. 测试/验证类入口后续统一复用 `scripts/repo_python.sh`，不要各自维护一套解释器猜测逻辑；
2. `jjk-verify` 报告继续保留“实际命中解释器”字段，避免再次出现“测错环境”；
3. 若未来仓内统一迁移到其他 venv 目录，只需收敛修改 `scripts/repo_python.sh`，不要批量回改所有测试命令模板。

---

### WF-22 单测红绿循环被全局 coverage 门槛干扰

**现象**
- 本轮新回归测试首次 RED 时，除了真实失败外，还额外触发：
  - `FAIL Required test coverage of 30.0% not reached`
- 这类 coverage 失败并不是当前单测根因，而是仓库全局 coverage 门槛在定向运行下的副作用。

**影响**
- RED/GREEN 阶段的真实失败原因会被 coverage 噪音覆盖；
- 问题定位成本上升，代理更难快速判断“测试是否已经准确命中 bug”；
- 若把 coverage 门槛直接放进所有定向测试命令，会削弱 TDD 的可操作性。

**现场处理**
- 本轮定向回归改为：
  - `venv/bin/python -m pytest ... --no-cov -q`
- 在行为确认通过后，再把结果回填到文档，而不是在 RED 阶段强行满足总 coverage。

**问题本质**
- 当前工程流没有区分“开发期最小回归验证”和“最终收口门禁验证”两种测试语义。

**本窗口收尾结果（2026-03-08）**
1. 已新增 `scripts/pytest_targeted.sh` 作为开发期定向 pytest 单一入口：固定注入 `--no-cov`，并统一通过 `scripts/repo_python.sh` 解析解释器；
2. `AGENTS.md` 已新增“测试语义分层（强制）”，明确 TDD/调试阶段走 targeted 入口，最终收口/门禁验证继续走常规 pytest/coverage 命令；
3. 定向入口若收到 `--cov*` 参数会直接以 `PYTEST_TARGETED_COVERAGE_MIXED` fail-fast，禁止把 coverage 语义带回 RED 阶段；
4. 已补最小回归 `tests/unit/test_pytest_targeted_script.py`，先红灯确认脚本缺位，再验证当前 `2 passed`。

**后续修复建议**
1. 开发期定向验证统一复用 `scripts/pytest_targeted.sh`，不要再手工拼接 `--no-cov`；
2. 最终收口 coverage 门禁继续保留在正式验证命令，不要回流到 targeted 入口；
3. 其他测试/验证文档若仍把两类命令混写，应统一收敛到“targeted vs final gate”双入口模型。

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

**本轮修复进展**
- 已在 `scripts/coder4/wt-flow.sh` 增加分支 `task_key` 提示解析；
- `WT_FLOW_TASK_SPLIT_DIR` 现在可直接解析 task split dir，而不要求必须额外提供完整 active_task 文件路径；
- 主仓根目录下仅传 `WT_FLOW_TASK_SPLIT_DIR=2026-03-06_工程减法治理` 即可跑到真实 `C07` done_gate。

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

**本轮修复进展**
- 已将 `wt-flow` 的 `CHECKOUT_ROOT` 与 `COMMON_ROOT` 拆开；
- `WT_BASE`、默认 `.state` 根与 worktree 解析现在不再错误依赖当前 `pwd`；
- 同时补了主仓绝对路径到当前 worktree 的命令归一化，使 `C07` worktree 内的 `verify` 能直接打到当前卡分支代码。

**后续修复建议**
1. 一律使用 `git rev-parse --show-toplevel` 解析当前 checkout 根，而不是依赖 `pwd` 推断；
2. 将 repo 根与 card worktree 根显式区分，避免字符串拼接型路径推导；
3. 为“从主仓执行”和“从 card worktree 执行”各补一条回归用例。

---

## 4. 修复优先级建议

| 波次 | 目标 | 建议纳入的问题 |
|---|---|---|
| Wave 1 | 恢复工程流稳定执行 | WF-02, WF-07 |
| Wave 2 | 让退役门禁与文档口径稳定收口 | WF-10 |
| Wave 3 | 降低 worktree / merge 误操作成本 | WF-04, WF-05, WF-06, WF-18 |
| Wave 4 | 强化契约与回归测试 | 将 WF-01、WF-08、WF-09、WF-11、WF-12、WF-13、WF-14、WF-15、WF-16、WF-17、WF-19 的现场修复固化为默认回归测试 |
| Wave 5 | 优化指令与工具链约定 | WF-20, WF-21, WF-22 |

---

## 5. 推荐后续卡片

1. **P0**：`cardrun_dispatch JSON 回执与超时治理`
3. **P0**：`修正 C03 契约与 legacy_wrapper_compat 验收路径`
4. **P0**：`jjk-plan/jjk-vkplan 默认接入 temporal gate 校验`
5. **P1**：`workflow-gate usage 日志产物策略治理`
6. **P0**：`full-gate pre/post-merge 阶段回归测试`
7. **P0**：`wt-flow merge common-repo 化`
8. **P1**：`git porcelain 中文路径稳健解析`
9. **P1**：`wrapper/实体脚本单一真理源治理`
10. **P1**：`clarify/vk_cards/temporal-gate/g01 drift 与 canonical-state 回归测试`
11. **P1**：`apply_patch / 文件编辑工具约定对齐`
12. **P1**：`测试解释器自动探测与命令模板统一`
13. **P1**：`RED/GREEN 与 FINAL_GATE coverage 语义拆分`

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
  - `.artifacts/states/task_splits/2026-03-06_工程减法治理/PP-20260306-workflow-gate-retirement/`
- 当前卡片契约：
  - `workdocs/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C03_P1_L1旧脚本wrapper兼容壳.md`
  - `workdocs/任务拆解/2026-03-06_工程减法治理/workstreams/WS-C07_P3_删除旧实现与兼容壳收口.md`
  - `workdocs/任务拆解/2026-03-06_工程减法治理/workstreams/WS-G01_G01_全链路验收门禁.md`
- 退役门禁观测证据：
  - `logs/workflow-gate-usage.jsonl`
  - `python3 scripts/check_workflow_contract.py --mode full-gate --task-split-dir workdocs/任务拆解/2026-03-06_工程减法治理 --baseline master --output -`
