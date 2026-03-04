---
description: 串行卡片执行入口（消费 /jjk-vkplan 产物）：主控调度 + 子代理逐卡执行 + done_gate 验证 + 会话隔离
---

> 参考规则: @dual-database

# CardRun 串行执行工作流 (Serial Card Runner)

`/jjk-cardrun` 是 `jjk-*` 体系里的串行执行入口，负责消费 `/jjk-vkplan` 产物（`vk_cards.json`、`parallel_plan.md`、`WS-*.md`），并按 `card_order` 单卡推进。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 会话隔离机制（v2.0 新增）

### 设计目标

支持多个 `jjk-cardrun` 实例并行执行，避免分支名和 worktree 路径冲突。

### 命名规则

#### 分支命名

- **有 task_key + 会话隔离**：`feature/<task_key>/<card_id>/<session_id>`
- **有 task_key（旧版兼容）**：`feature/<task_key>/<card_id>`
- **无 task_key（旧版兼容）**：`feature/<card_id>`

#### Worktree 路径

- **有 task_key + 会话隔离**：`.worktrees/<task_key>/<card_id>/<session_id>`
- **有 task_key（旧版兼容）**：`.worktrees/<task_key>/<card_id>`
- **无 task_key（旧版兼容）**：`.worktrees/<card_id>`

#### Session ID 格式

- 格式：`<timestamp>-<random_suffix>`
- 示例：`1709539200-a3f2`
- 生成方式：`date +%s` + 4 位随机十六进制

### 使用方式

#### 自动生成会话 ID（推荐）

```bash
/jjk-cardrun 2026-03-01_用户个性化永久记忆与管理能力 loop
```

每次执行自动生成新的 session_id，避免冲突。

#### 手动指定会话 ID（高级用法）

```bash
export WT_FLOW_SESSION_ID="1709539200-a3f2"
/jjk-cardrun 2026-03-01_用户个性化永久记忆与管理能力 loop
```

用于：
- 恢复中断的会话
- 多个 cardrun 实例协作（不同 session_id）
- 调试特定会话

#### 查看所有活跃会话

```bash
bash scripts/wt-flow.sh global-status
```

输出示例：

```
=== 全局 Worktree 状态 ===
TASK_KEY                                      CARD     STATUS          WORKTREE_PATH                                      BRANCH
--------------------------------------------- -------- --------------- -------------------------------------------------- ----------------------------------------
2026-03-01_用户个性化永久记忆与管理能力      C01      active          .worktrees/2026-03-01_.../C01/1709539200-a3f2     feature/2026-03-01_.../C01/1709539200-a3f2
2026-03-01_用户个性化永久记忆与管理能力      C02      active          .worktrees/2026-03-01_.../C02/1709539300-b4e3     feature/2026-03-01_.../C02/1709539300-b4e3
2026-02-28_另一个任务                         G01      active          .worktrees/2026-02-28_.../G01/1709539400-c5f4     feature/2026-02-28_.../G01/1709539400-c5f4
```

### 并行执行场景

#### 场景 1：同一 task 的不同卡片并行（支持）

```bash
# 终端 1
export WT_FLOW_SESSION_ID="session-1"
/jjk-cardrun 2026-03-01_用户个性化永久记忆与管理能力 once

# 终端 2
export WT_FLOW_SESSION_ID="session-2"
/jjk-cardrun 2026-03-01_用户个性化永久记忆与管理能力 once
```

**结果**：
- 分支名：`feature/2026-03-01_.../C01/session-1` 和 `feature/2026-03-01_.../C02/session-2`
- Worktree：`.worktrees/2026-03-01_.../C01/session-1` 和 `.worktrees/2026-03-01_.../C02/session-2`
- **不冲突**

#### 场景 2：不同 task 并行（支持）

```bash
# 终端 1
/jjk-cardrun 2026-03-01_用户个性化永久记忆与管理能力 loop

# 终端 2
/jjk-cardrun 2026-02-28_另一个任务 loop
```

**结果**：不同 task_key，天然隔离，不冲突。

#### 场景 3：同一卡片多实例（支持，但需手动指定 session_id）

```bash
# 终端 1
export WT_FLOW_SESSION_ID="session-1"
/jjk-cardrun 2026-03-01_用户个性化永久记忆与管理能力 once

# 终端 2（同一张卡片）
export WT_FLOW_SESSION_ID="session-2"
/jjk-cardrun 2026-03-01_用户个性化永久记忆与管理能力 once
```

**结果**：
- 如果两个实例选中同一张卡片（如 C01），会创建两个独立的 worktree
- 分支名：`feature/.../C01/session-1` 和 `feature/.../C01/session-2`
- **不冲突**

### 状态文件隔离

每个会话使用独立的状态文件：

- **有 session_id**：`.omc/state/<task_key>/sessions/<session_id>/wt-flow-state.json`
- **无 session_id（旧版）**：`.omc/state/<task_key>/wt-flow-state.json`

### 兼容性

- **向后兼容**：未设置 `WT_FLOW_SESSION_ID` 时，行为与旧版一致
- **自动升级**：首次使用会话隔离后，后续操作自动识别会话 ID
- **混合模式**：新旧 worktree 可以共存，互不干扰

## 与 Superpowers / OMX 的分工（强制）

1. `/jjk-vkplan`：提供串行执行契约（`execution_mode/card_order/depends_on/task_to_pr_mapping`）。
2. `/jjk-vktodo`：仅负责 create-only 幂等建卡（MCP 优先 + fallback）。
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
5. `mode=once|loop` 时执行 dirty 策略校验：仅 `docs/`、`.cursor/commands/`、`.agents/skills/`、`.claude/commands/` 白名单前缀可放行，其他变更阻断并输出 `CARDRUN_WORKTREE_DIRTY`。

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

1. 执行 `git status --porcelain --untracked-files=no`。
2. 若存在非白名单 dirty，立即失败：`CARDRUN_WORKTREE_DIRTY`。
3. 通过 `WT_FLOW_DIRTY_WHITELIST=<prefix1>,<prefix2>` 可覆盖默认白名单前缀。
4. `mode=status` 允许在 dirty 工作区运行（只读，不分派子代理）。

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
   - 若已有进行中卡（`in_progress/in_review/verified`），优先续跑该卡；
   - 否则执行 `bash scripts/wt-flow.sh next` 激活下一张可执行卡。
3. 若 `wt-flow.sh next` 返回 `ALL_DONE`，输出 `CARDRUN_ALL_DONE` 并结束。

### 3) 主控调度子代理执行当前卡

1. 主控必须把当前卡对应 `WS-*.md` 全量上下文交给子代理。
2. 子代理执行入口固定：`/jjk-imp-ws @<ws_file>`。
3. 单卡拆分并行规则：
   - 仅当单卡规模过大（文件 `>=8` 或跨域 `>=2`）时，允许 `team` 在卡内并行；
   - 禁止跨卡并行，禁止同时激活两张卡。
4. 子代理失败时，立即回收并标记 `CARDRUN_SUBAGENT_FAILED`，不得跳卡。

### 4) done_gate + merge 串行收口（强制）

1. 执行：`bash scripts/wt-flow.sh verify <card_id>`。
2. `verify` 通过后，当前卡状态只能进入 `verified`，不得直接写 `done`。
3. `verify` 通过后必须执行：`bash scripts/wt-flow.sh merge`。
4. `merge` 成功后状态写回 `done`，并清理当前 worktree，才允许推进下一卡。
5. `merge` 失败时立即阻断，输出 `CARDRUN_MERGE_FAILED` 与冲突/失败证据。
6. `verify` 不通过时保持 `in_progress`，输出 `CARDRUN_DONE_GATE_FAILED` 与失败证据。
7. 可选执行同步校验（只读）：

```bash
python3 scripts/coder4_vk_sync.py --sync-all --strict --output -
```
8. `local_mode` 场景下，结果证据必须回显 `applied.vk_sync.attempted/disabled/reason`，避免“卡片不可见”误判。

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
6. 禁止在未完成 `merge` 时将实现卡标记为 `done`。

## 推荐链路

`/jjk-plan -> /jjk-vkplan -> /jjk-vktodo(create-only) -> /jjk-cardrun(loop)`

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
