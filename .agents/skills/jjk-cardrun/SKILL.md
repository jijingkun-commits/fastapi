---
name: jjk-cardrun
description: "Use when you need `jjk-cardrun` in this repository. Source intent: 串行卡片执行入口：消费 /jjk-vkplan 产物并按 card_order 单卡推进"
---
<!-- AUTO-GENERATED: jjk-skill-mirror -->
<!-- source: .cursor/commands/jjk-cardrun.md -->

> 参考规则: @dual-database

# CardRun 串行执行工作流（Serial Card Runner）

`$jjk-cardrun` 负责主控调度与单卡串行推进，默认链路：

`$jjk-plan -> $jjk-vkplan -> $jjk-cardrun(loop) -> $jjk-wtimp(executor_mode=cardrun_dispatch)`

> **中文主导**：思考与输出统一中文。

---

## 输入前置（强制）

显式参数优先，其次从活跃任务索引推断：

1. `task_split_dir`
2. `project_id`
3. `mode=status|once|loop`（默认 `once`）
4. `max_cards`（仅 loop；默认 `1`）

必备文件：

1. `docs/内部参考/任务拆解/<task_split_dir>/vk_cards.json`
2. `docs/内部参考/任务拆解/<task_split_dir>/parallel_plan.md`（可选；自动生成总览，仅供人工阅读）
3. `docs/内部参考/任务拆解/<task_split_dir>/workstreams/WS-*.md`
4. `docs/内部参考/任务拆解/<task_split_dir>/_active_task.json`
5. `docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/task-runner-state.json`（首次执行可由调度器自动创建；可持久化 `integration_branch`）

硬约束：

1. `vk_cards.json.execution_mode` 必须是 `serial`，否则 `CARDRUN_NOT_SERIAL`
2. `card_order` 不可空，否则 `CARDRUN_CARD_ORDER_EMPTY`
3. `task_to_pr_mapping` 必须完整，否则 `CARDRUN_PR_MAPPING_MISSING`
4. `card_id -> WS -> pr_id` 必须唯一可解析，否则 `CARDRUN_CARD_MAPPING_BROKEN`
5. 运行态根目录必须位于 `<task_split_dir>/.state`，否则 `CARDRUN_STATE_DIR_INVALID`
6. 卡片必须声明 `risk_tags/mandatory_evidence`，缺失即 `CARDRUN_EVIDENCE_CONTRACT_MISSING`
7. DB 风险卡片必须可解析到 DB 类 `mandatory_evidence`，否则阻断派发

---

## 会话隔离（最小规则）

1. 分支命名：`feature/<task_key>/<card_id>/<session_id>`
2. worktree 路径：`.worktrees/<task_key>/<card_id>/<session_id>`
3. `session_id` 默认自动生成；可通过 `WT_FLOW_SESSION_ID` 手动指定（恢复/调试场景）

---

## 执行流程（强制顺序）

### 0) 上下文与洁净校验（必做）

每轮先执行并记录：

```bash
pwd
git branch --show-current
git worktree list
git status --porcelain --untracked-files=no
```

规则：

1. 上下文异常：`CARDRUN_CONTEXT_INVALID`
2. `mode=once|loop` 存在非白名单 dirty：`CARDRUN_WORKTREE_DIRTY`
3. `mode=status` 允许脏工作区（只读，不分派）

### 1) 轻量校验（mode=once|loop 推荐）

```bash
python3 scripts/check_workflow_contract.py --mode plan_vk_coverage --task-split-dir <task_split_dir> --output -
```

硬约束：

1. 校验结果 `ok=false` 时必须 `FAIL_FAST` 输出 `CARDRUN_CONTRACT_INVALID`；
2. 出现 `missing_task_ids/missing_task_id_fields/empty_task_ids` 任一非空时必须阻断；
3. 命中 `CLARIFY_PLAN_ALIGNMENT_FAILED` 时必须阻断，禁止进入 `next/dispatch/verify/merge`。

### 2) 选卡与激活（单活卡）

1. `status`：只展示队列，不执行实现。
2. `once|loop`：
   - 优先续跑已有 `in_progress/in_review/verified` 卡；
   - 否则执行 `bash scripts/wt-flow.sh next` 激活下一张可执行卡。
   - `next/create` 必须先解析并固定本任务的 `integration_branch`：优先复用 `task-runner-state.json.integration_branch`，否则继承当前非 `main/master` 父分支；若仍无法解析，再回落到仓库主线分支。
3. 若返回 `ALL_DONE`：输出 `CARDRUN_ALL_DONE` 并结束。

### 3) 主控调度子代理

1. 必须把当前卡对应 `WS-*.md` 全量上下文交给子代理。
2. 子代理入口固定：`$jjk-wtimp @<ws_file>`（`executor_mode=cardrun_dispatch`），并由 cardrun 在 `dispatch` 阶段真实调用。
3. `wtimp` 必须以结构化 JSON 回执 `executor/subagent_id/ws_file/commit_sha/merge_sha/acceptance_results/evidence_satisfied`，禁止只靠人工口头回填。
4. 仅允许“卡内并行”，禁止“跨卡并行”。
5. 子代理失败立即阻断：`CARDRUN_SUBAGENT_FAILED`。
6. 子代理回执必须包含当前卡片对应的 `commit_sha` 证据；缺失时阻断：`CARDRUN_NO_COMMIT_EVIDENCE`。
7. 子代理回执中 `acceptance_results` 必须可追溯到命令级结果对象（至少 `kind/cmd/exit_code/summary`）。
8. 若 `evidence_satisfied=false` 或 DB/scripted_flow 必需证据缺口存在，直接阻断：`CARDRUN_DB_EVIDENCE_UNSATISFIED` / `CARDRUN_SCRIPTED_FLOW_MISSING`。

### 4) done_gate + merge 收口（强制）

```bash
bash scripts/wt-flow.sh verify <card_id>
bash scripts/wt-flow.sh merge
```

规则：

1. `verify` 通过后先到 `verified`，不得直接 `done`。
1.1 `verify` 必须消费最近一次 dispatch 的 `acceptance_results/evidence_satisfied`，禁止只看 `commit_sha`。
2. 只有 `merge` 成功后才写 `done` 并推进下一卡。
3. `verify` 失败：`CARDRUN_DONE_GATE_FAILED`
4. `merge` 失败：`CARDRUN_MERGE_FAILED`
5. `merge` 前必须满足“会话分支卡片 == 当前激活卡片”且状态为 `verified`；不满足即阻断（防止误合并到错误卡片）。
6. `merge` 时若目标分支相对基线 `ahead=0`，必须阻断：`MERGE_NO_COMMITS`（禁止“无提交也标记完成”）。
7. 门禁/编排类卡片若无文件改动，允许空提交进入 `merge`，但必须有 `commit_sha` 与原因证据。
8. `cardrun` 是唯一 merge 主路径；`wtimp` 在 `executor_mode=cardrun_dispatch` 下不得重复执行 merge。
9. `merge` 目标分支以当前 card session 的 `base_branch` 为准；该值只能由 `wt-flow next/create` 决定并持久化，禁止在 `wtimp` 内重算。
10. DB 风险卡片在 `evidence_satisfied=true` 前禁止进入 merge。

### 5) 循环推进（仅 loop）

1. 默认 `max_cards=1`，防止单次失控。
2. 显式 `max_cards=N` 时最多推进 `N` 张。
3. 任一轮失败立刻停止，不允许跳卡继续。

---


## 失败码补充（DB 证据门禁）

1. `CARDRUN_EVIDENCE_CONTRACT_MISSING`
2. `CARDRUN_DB_EVIDENCE_UNSATISFIED`
3. `CARDRUN_SCRIPTED_FLOW_MISSING`

## 输出模板（强制）

每轮对用户输出三行：

1. `结论: <PASS|BLOCKED|FAIL> + 任务态`
2. `当前动作: <当前卡/下一步动作>`
3. `证据: <命令结果 + 产物路径 + 失败原因或空>`

---

## 禁止项（强制）

1. 禁止直接调用 VK API 改状态（仅允许 `jjk-vktodo` 或 `coder4_vk_sync.py` 路径）。
2. 禁止跳过 `verify -> merge` 主干收口。
3. 禁止手工编辑 `_active_task.json`、`task-runner-state.json`、`task-ledger.jsonl`。
4. 禁止跨 worktree 修改“非当前卡片”文件。
5. 禁止在未 `merge` 成功前把卡标记为 `done`。

---

*使用 `$jjk-cardrun` 触发。目标是“单卡串行推进 + done_gate 证据闭环”。*
