---
description: 串行卡片执行入口（消费 /jjk-vkplan 产物）：主控调度 + 子代理逐卡执行 + done_gate 验证
---

> 参考规则: @dual-database

# CardRun 串行执行工作流 (Serial Card Runner)

`/jjk-cardrun` 是 `jjk-*` 体系里的串行执行入口，负责消费 `/jjk-vkplan` 产物（`vk_cards.json`、`parallel_plan.md`、`WS-*.md`），并按 `card_order` 单卡推进。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 与 Superpowers / OMX 的分工（强制）

1. `/jjk-vkplan`：提供串行执行契约（`execution_mode/card_order/depends_on/task_to_pr_mapping`）。
2. `/jjk-vktodo`：负责看板建卡与状态推进（MCP 优先 + fallback）。
3. `/jjk-imp-ws`：负责单卡对应 WS 的代码实现与证据回填。
4. `subagent-driven-development`：负责“主控调度 + 子代理执行 + 评审回环”方法。
5. `team`（OMX）：仅在“单卡内部过大”时并行拆分，禁止多卡并行抢占。
6. `/jjk-cardrun`：负责单活卡门禁、调度顺序、scope_guard 校验与状态闭环。

约束：

1. 禁止在 `/jjk-cardrun` 重写 `/jjk-vkplan` 契约语义；只允许消费。
2. 禁止并发执行多个实现卡；必须保持 `execution_mode=serial` 的单活卡语义。
3. 禁止手工改写 `_active_task.json` 与 `task-runner-state.json`。
4. 每轮分派前必须执行 `scope_guard`；未通过立即阻断。

## 跨 IDE 调用方式

1. Cursor / Claude Code：`/jjk-cardrun`
2. Codex：`/prompts:jjk-cardrun`

> 说明：Codex 的自定义命令入口是 `/prompts:<name>`，不是 `/<name>`。

## 何时使用

| 场景 | 推荐命令 |
|---|---|
| 已完成 `/jjk-vkplan`，希望按卡片串行推进实现 | `/jjk-cardrun` ✅ |
| 只想建卡/推进看板，不执行实现 | `/jjk-vktodo` |
| 只执行单个 WS，不做卡片调度 | `/jjk-imp-ws` |

---

## 输入前置（强制）

必须可解析以下输入（显式参数优先，其次 `_active_task.json` 自动推断）：

1. `task_split_dir`
2. `project_id`
3. 执行模式（默认 `once`，可选 `status|once|loop`）
4. 可选 `max_cards`（默认 `1`，用于 `loop`）

必备文件：

1. `docs/内部参考/任务拆解/<task_split_dir>/vk_cards.json`
2. `docs/内部参考/任务拆解/<task_split_dir>/parallel_plan.md`
3. `docs/内部参考/任务拆解/<task_split_dir>/workstreams/WS-*.md`
4. `docs/内部参考/任务拆解/_active_task.json`

硬约束：

1. `vk_cards.json.execution_mode` 必须为 `serial`，否则 `FAIL_FAST` 输出 `CARDRUN_NOT_SERIAL`。
2. `card_order` 不能为空，否则 `FAIL_FAST` 输出 `CARDRUN_CARD_ORDER_EMPTY`。
3. `task_to_pr_mapping` 必须完整，否则 `FAIL_FAST` 输出 `CARDRUN_PR_MAPPING_MISSING`。
4. `card_id -> WS -> pr_id` 必须唯一可解析，否则 `FAIL_FAST` 输出 `CARDRUN_CARD_MAPPING_BROKEN`。
5. `mode=once|loop` 时主工作区必须干净（`git status --porcelain` 为空）；否则 `FAIL_FAST` 输出 `CARDRUN_WORKTREE_DIRTY`。

## 执行流程（强制顺序）

### 0) 执行上下文校验（必做）

每轮必须先执行并记录：

```bash
pwd
git branch --show-current
git worktree list
```

不一致时立即失败：`CARDRUN_CONTEXT_INVALID`。

### 0.2) 工作区洁净校验（mode=once|loop 必做）

1. 执行 `git status --porcelain`。
2. 若输出非空，立即失败：`CARDRUN_WORKTREE_DIRTY`。
3. `mode=status` 允许在 dirty 工作区运行（只读，不分派子代理）。

说明：

1. `jjk-cardrun` 并不要求你手工先创建 worktree。
2. 进入 `once|loop` 时会通过 `bash scripts/wt-flow.sh next` 自动创建/切换卡片 worktree。
3. 阻断根因是“主工作区不干净”，不是“缺少手工 worktree”。

### 0.5) scope_guard 校验（每轮分派前必做）

```bash
python3 scripts/coder4_scope_guard.py \
  --repo-root /Users/jijingkun/bojxAI/fastapi \
  --active-task docs/内部参考/任务拆解/_active_task.json \
  --scope-request /Users/jijingkun/.openclaw/workspace-dev/state/coder4_scope_request.json
```

未通过时：`FAIL_FAST` 输出 `CARDRUN_SCOPE_GUARD_FAILED`。

### 1) 读取并校验串行契约

1. 读取 `vk_cards.json` 的 `task_key/card_order/cards/hard_depends_on`。
2. 读取 `parallel_plan.md` 与 `WS-*.md`，建立 `card_id -> ws_file` 映射。
3. 读取 `task-runner-state.json`：
   - 若不存在，运行 `coder4_bootstrap_kernel.py` 生成初始状态；
   - 已存在则只读加载，不允许手工修补。

### 2) 选卡与激活（单活卡）

1. `mode=status`：只输出当前卡队列，不触发实现。
2. `mode=once|loop`：
   - 若已有进行中卡（`in_progress/in_review`），优先续跑该卡；
   - 否则执行 `bash scripts/wt-flow.sh next` 激活下一张可执行卡。
3. 若 `wt-flow.sh next` 返回 `ALL_DONE`，输出 `CARDRUN_ALL_DONE` 并结束。

### 3) 主控调度子代理执行当前卡

1. 主控必须把当前卡对应 `WS-*.md` 全量上下文交给子代理。
2. 子代理执行入口固定：`/jjk-imp-ws @<ws_file>`。
3. 单卡拆分并行规则：
   - 仅当单卡规模过大（文件 `>=8` 或跨域 `>=2`）时，允许 `team` 在卡内并行；
   - 禁止跨卡并行，禁止同时激活两张卡。
4. 子代理失败时，立即回收并标记 `CARDRUN_SUBAGENT_FAILED`，不得跳卡。

### 4) done_gate 验证与状态收口

1. 执行：`bash scripts/wt-flow.sh verify <card_id>`。
2. 通过：状态写回 `done`，允许推进下一卡。
3. 不通过：保持 `in_progress`，输出 `CARDRUN_DONE_GATE_FAILED` 与失败证据。
4. 可选执行同步校验（只读）：

```bash
python3 scripts/coder4_vk_sync.py --sync-all --strict --output -
```

### 5) 循环推进策略（仅 mode=loop）

1. 默认 `max_cards=1`，避免单次执行失控。
2. 显式指定 `max_cards=N` 时，最多推进 `N` 张。
3. 任一轮失败立刻停止并回报阻塞点，不允许“跳过失败卡继续后续卡”。

---

## 输出模板（强制）

用户可见输出必须使用三行：

1. `结论: <PASS|BLOCKED|FAIL> + 任务态`
2. `当前动作: <当前卡/下一步动作>`
3. `证据: <命令结果 + 产物路径 + 失败原因或空>`

## 禁止项（强制）

1. 禁止直接调用 VK API 改状态；仅允许 `/jjk-vktodo` 或 `scripts/coder4_vk_sync.py` 路径。
2. 禁止跳过 `scope_guard` 直接分派子代理。
3. 禁止手工编辑 `_active_task.json`、`task-runner-state.json`、`task-ledger.jsonl`。
4. 禁止跨 worktree 修改“非当前卡片”文件。
5. 禁止在 heartbeat/调度周期执行破坏性 git 操作（`reset --hard`、`checkout --`、强推）。

## 推荐链路

`/jjk-plan -> /jjk-vkplan -> /jjk-vktodo -> /jjk-cardrun -> /jjk-create-pr`

## 使用示例

```text
/jjk-cardrun 2026-03-01_用户个性化永久记忆与管理能力
```

```text
/jjk-cardrun 2026-03-01_用户个性化永久记忆与管理能力 once
```

```text
/jjk-cardrun 2026-03-01_用户个性化永久记忆与管理能力 loop max_cards=2
```

```text
/jjk-cardrun 2026-03-01_用户个性化永久记忆与管理能力 status
```

---
*使用 `/jjk-cardrun` 触发。目标是“主控调度 + 子代理逐卡串行执行 + 证据闭环”。*
