# Coder4自动执行总控手册

> 适用对象：需要让 `jjk_coder4_bot` 自动推进 VK 卡片的人  
> 更新日期：2026-02-24

## 1. 这份手册解决什么问题

本手册回答三个核心问题：

1. coder4 当前是如何自动工作的（不是抽象描述，而是落到文件、状态、门禁）。
2. 为什么它有时会 `RECONCILE_ONLY / NO_INCREMENT`，以及这些状态各自意味着什么。
3. 要让它稳定跑整夜，你的任务文档、看板、定时任务要满足哪些硬条件。

---

## 2. 架构总览（你当前环境）

### 2.1 运行入口

- 定时任务文件：`/Users/jijingkun/.openclaw-dev/cron/jobs.json`
- coder4 任务 ID：`3889e1fe-ff85-4e49-adad-4c99a542743e`
- 调度频率：`*/3 * * * *`（每 3 分钟）
- 投递通道：Telegram `6358651433`

### 2.2 真理源与执行链

coder4 每轮执行前会读取并校验以下链路（缺一会阻断）：

1. `docs/内部参考/任务拆解/_active_task.json`（当前任务作用域真理源）
2. `docs/内部参考/任务拆解/<task_split_dir>/vk_cards.json`
3. `docs/内部参考/任务拆解/<task_split_dir>/parallel_plan.md`
4. `docs/内部参考/任务拆解/<task_split_dir>/workstreams/WS-*.md`
5. `docs/内部参考/迭代需求/<topic>_implementation_plan.md`

---

## 3. `_active_task.json` 是什么

`_active_task.json` 是“当前自动任务指针”。  
它告诉 coder4：本轮到底该看哪个 project、哪个 task_key、执行哪条策略。

当前字段定义（最小必填）：

- `project_id`
- `task_split_dir`
- `task_key`
- `execution_mode`
- `single_active_card`
- `auto_done_policy`
- `preflight_required`

自动更新命令：

```bash
python3 scripts/set_active_task.py \
  --task-split-dir <YYYY-MM-DD_主题> \
  --project-id <VK_PROJECT_ID>
```

说明：

- 推荐通过脚本更新，不建议手改 JSON。
- 脚本会自动读取对应任务目录下的 `vk_cards.json`，同步 `task_key/execution_mode/preflight`。

---

## 4. 每轮执行时序（真实逻辑）

coder4 每一轮按固定顺序执行：

1. 读取 `_active_task.json`，若缺失或字段不全 -> `BLOCKED_DOC_CONTEXT`。
2. 读取 `vk_cards.json`，校验 `task_key` 一致性，失败 -> `BLOCKED_DOC_CONTEXT`。
3. 读取 project 看板任务并分组：
   - `scoped_tasks`：标题含 `[task_key]`，或 labels 含 `task_key`，或 ID 前缀匹配 `task_key::`
   - `unscoped_tasks`：其他卡片
4. 执行作用域门禁：
   - `unscoped` 有活动卡 -> `RECONCILE_ONLY(scope_conflict)`
   - `single_active_card=true` 且 scoped 活动卡 > 1 -> `RECONCILE_ONLY(multi_active_scoped)`
   - scoped 活动卡 = 0 且 todo > 0 -> `NO_INCREMENT(scope_no_active)`
   - scoped 活动卡 = 0 且 todo = 0 -> `ALL_DONE`
5. 若门禁通过，才允许派单；且每轮只派 1 个最小步骤。
6. 回读 main 会话最新有效回报，做证据绑定检查。
7. 写回状态文件与汇报。

---

## 5. 状态机与门禁规则

### 5.1 允许的自动迁移

- `todo -> inprogress`
- `inprogress -> inreview`
- `inreview -> done`（仅当 `auto_done_policy=hard_gate` 且全部门禁通过）

### 5.2 `inreview -> done` 的 hard gate

实现卡（implementation-card）必须同时满足：

1. 证据绑定通过（`target_task_id == evidence_task_id`）。
2. 验收命令通过（`acceptance_checks`）。
3. 若 `merge_required=true`，`merge_commit` 可 git 验证且已在主线。
4. 写入 `coder4_task_ledger.jsonl` 成功。
5. 完成通知发送成功（Telegram）。
6. 成功执行一次 compact，并记录 `done_cleanup_at`。

任一失败都保持在 `inreview`，并返回 `BLOCKED_EVIDENCE_GAP`。

---

## 6. 稳定性机制（防卡死、防重复、防漂移）

### 6.1 签名去重

- 签名：`task_id|status|turn_id|process_id`
- 15 分钟内重复签名禁止重复派单，避免刷同一步。

### 6.1.1 定时任务不重复触发（配置层）

1. 同一执行器只允许一个启用中的 cron 任务（固定 `job_id` 做 update，不新建平行 job）。
2. 启停统一走 cron `update enabled=true/false`，不要反复 `create`。
3. 若发现多个同类 job 同时启用，先禁用旧 job，再保留当前主 job。

### 6.2 无增量熔断

- `no_increment_fuse=8`
- 连续 8 轮无增量后，进入“仅巡检+告警”模式，不再盲目推进。

### 6.3 会话轮换兜底

- 每 20 轮或 2 小时触发一次 rotate（兜底，不是主路径）。
- 轮换后先 precheck，不直接改代码。

### 6.4 卡死恢复

仅在以下情况触发一次恢复：

- 输出只有 `model:xxx`
- 或 process `running` 且 `summary_len=0`

恢复动作：`stop -> follow-up continue`。  
若恢复后仍无增量，标记 `BLOCKED_STALL`。

---

## 7. 证据与记忆落盘

### 7.1 状态文件（短期运行态）

`/Users/jijingkun/.openclaw/workspace-dev/state/coder4_cron_state.json`

用于保存最近一轮的签名、轮次、熔断计数、轮换信息、清理时间等。

### 7.2 任务台账（长期证据）

`/Users/jijingkun/.openclaw/workspace-dev/state/coder4_task_ledger.jsonl`

每次成功 DONE 会写一条记录，至少包含：

- `task_id`
- `turn_id`
- `process_id`
- `status`
- `target_task_id`
- `evidence_task_id`
- `merge_commit`
- `check_results`
- `docs_guard_result`
- `timestamp`

约束：

1. evidence 四元组 `task_id/turn_id/process_id/status` 必须完整。
2. 证据绑定必须满足 `target_task_id == evidence_task_id`，否则视为 `BLOCKED_EVIDENCE_GAP`。

### 7.3 短上下文清理

每次 DONE 后只清“短上下文”（compact）。  
长期证据（ledger/state/docs）不会被清掉。

---

## 8. 你日常怎么用（最短路径）

### Step A：产出任务拆解

1. `/jjk-plan`（或 `/jjk-plan parallel`）
2. `/jjk-vkplan`

### Step B：落卡到 VK

使用 `/jjk-vktodo <task_split_dir>` 落卡，确保 C 卡进入目标 project。

### Step C：更新自动作用域

```bash
python3 scripts/set_active_task.py \
  --task-split-dir <YYYY-MM-DD_主题> \
  --project-id <VK_PROJECT_ID>
```

### Step D：确认看板满足串行执行

- scoped 卡存在
- `inprogress + inreview <= 1`
- C00 preflight 已满足

### Step E：开启 coder4 cron

在定时任务中启用 coder4 任务（ID `3889e1fe-ff85-4e49-adad-4c99a542743e`）。

### Step F：区分“手动单轮”与“自动持续”（关键）

1. 手动单轮推进：发送第 12.3 节提示词给 `jjk_coder4_bot`，只执行 1 轮，不会持续轮询。
2. 自动持续推进：必须启用 cron（`enabled=true`），调度器按 `*/3 * * * *` 连续触发。
3. 仅发送提示词但未启用 cron，不会自动循环执行。

### Step G：最简对话式运维（推荐）

你可以只和 `jjk_coder4_bot` 对话来做启停与巡检，不需要额外脚本：

1. 查看状态：让它调用 cron `list`（含禁用项）并回报 coder4 job 的 `enabled`。
2. 开启/关闭：让它调用 cron `update`，把指定 `job_id` 的 `enabled` 改为 `true/false`。
3. 看运行记录：让它调用 cron `runs`，回报最近 N 次结果与失败原因。

说明：

1. 日常启停与状态查看，用对话即可。
2. `set_active_task.py` 仍建议保留，用于刷新 `_active_task.json` 真理源，避免作用域漂移。

---

## 9. 常见返回语义解释

- `RECONCILE_ONLY`：本轮只做对账/纠偏，不派单。
- `NO_INCREMENT`：本轮有检查但没有新增证据增量。
- `ALL_DONE`：当前作用域下已无可执行卡。
- `BLOCKED_DOC_CONTEXT`：文档链缺失或 task_key 不一致。
- `BLOCKED_EVIDENCE_GAP`：证据不足，不允许状态迁移。
- `BLOCKED_STALL`：触发一次 stop/continue 后仍卡住。

---

## 10. 当前状态快照（2026-02-24）

基于本地核对结果：

- coder4 cron：`enabled=false`（未启动自动跑）。
- `_active_task.json`：已指向 `PP-20260221-OPENCLAW-REBUILD-BASELINE`。
- 目标 project 当前 scoped 卡数量：`0`（尚未导入本任务 C01~C06）。
- 证据台账文件已存在，但记录数为 `0`。

这意味着：配置链已就绪，但运行链还未进入“可自动推进”状态。

---

## 11. 开跑前 5 分钟检查单

- [ ] `vk_cards.json` 已导入目标 project（能看到 scoped 卡）
- [ ] scoped 活动卡 <= 1
- [ ] `_active_task.json` 与 `vk_cards.json.task_key` 一致
- [ ] C00 preflight 条件已满足
- [ ] 同类 coder4 cron 仅 1 条 `enabled=true`（避免双调度）
- [ ] cron 已启用且投递通道正确
- [ ] 先做 2~3 轮 smoke，再放整夜

---

## 12. 可复用提示词模板（plan/vkplan/coder4）

以下模板用于“OpenClaw 迁移重建基线”类大任务，目标是让文档到执行链路可机读、可回放、可自动推进。

### 12.1 `/jjk-plan -p -h` 模板（生成主计划）

```text
/jjk-plan -p -h

主题：<主题名>

输入来源仅限：
- <输入文档绝对路径1>
- <输入文档绝对路径2>
- <输入文档绝对路径3>

强制要求：
1) 只产出：
   - <topic>_requirements.md
   - <topic>_implementation_plan.md
2) implementation_plan 必须包含完整 Feature Packet（每个 feature_id 都有机制、代码锚点、验收、回滚、证据入口）。
3) implementation_plan 末尾必须给 planning_contract：
   - execution_mode: serial
   - strict_single_active_card: true
   - auto_done_policy: implementation-card=hard_gate, inspection/question-card=policy_gate
   - card_order + cards[].feature_ids + depends_on + done_gate 完整
4) 必须输出 hydrate 覆盖率：
   - source_atoms_total
   - source_atoms_mapped
   - source_atoms_unmapped（明细）
   - source_conflicts（明细）
5) 若 source_atoms_unmapped 非空，计划状态必须标注 BLOCKED，并停止进入 vkplan。
6) 不允许重命名既有 card_id/feature_id（已有编号必须继承）。
```

### 12.2 `/jjk-vkplan` 模板（生成可执行拆解）

```text
/jjk-vkplan

主题：<主题名>
project_id：<VK_PROJECT_ID>

请只基于以下主计划拆解（禁止读取其他计划）：
1) <topic>_requirements.md 绝对路径
2) <topic>_implementation_plan.md 绝对路径

执行约束（强制）：
1. 严格继承 planning_contract，不得重命名 card_id/feature_id，不得弱化 depends_on。
2. execution_mode=serial：single_active_card=true，同一时刻仅一张卡可 Doing。
3. 写入 vk_cards.json 前必须做 FAIL_FAST 字段校验；任一缺失即停止：
   - feature_ids
   - mechanism_summary
   - code_anchor_refs
   - acceptance_checks
   - rollback_anchors
   - evidence_entry
   - task_mode
   - merge_required
4. 必须输出双向覆盖校验：
   - forward（每卡至少1个 feature）
   - reverse（每个 feature 恰好映射1张实现卡）
   - orphan（无遗漏）
   - duplicate（无重复漂移）
5. 若主计划包含 hydrate 映射，必须校验 FP-xx 全量落卡（缺失即 BLOCKED）。

产出目录（强制）：
- <task_split_dir>/parallel_plan.md
- <task_split_dir>/workstreams/WS-*.md
- <task_split_dir>/vk_cards.json
- docs/内部参考/任务拆解/_active_task.json

补充：
- vk_import_prompt.txt 非必需，只有在需要批量导卡时再生成。
- 若任何校验失败，请直接输出 BLOCKED 并给出缺失字段清单与修复建议。
```

### 12.3 启动 OpenClaw coder4 模板（串行自动执行）

```text
你现在是 OpenClaw coder4 自动执行器。
请按以下规则执行一轮任务推进（只推进 1 张卡，禁止并行）：

1) 读取并校验：
   - docs/内部参考/任务拆解/_active_task.json
   - <task_split_dir>/vk_cards.json
   - <task_split_dir>/parallel_plan.md
   - <task_split_dir>/workstreams/WS-*.md
2) 仅处理 task_key 作用域内卡片：
   - title 含 [task_key] 或 labels 含 task_key 或 key 前缀为 task_key::
3) 串行门禁：
   - single_active_card=true
   - inprogress + inreview <= 1
   - hard_depends_on 未满足时禁止推进
4) 状态迁移：
   - todo -> inprogress -> inreview
   - inreview -> done 仅在 auto_done_policy=hard_gate 且证据/验收/ledger 全通过
5) 输出要求：
   - 若成功推进：返回推进卡片、执行证据、下一张候选
   - 若不可推进：仅返回 NO_INCREMENT / RECONCILE_ONLY / BLOCKED_* 及最小修复动作
```

### 12.3.1 启动模板（仅状态回报，不输出修复建议）

```text
你现在是 OpenClaw coder4 自动执行器。
请按 active_task 作用域串行推进：每轮只推进 1 张卡，严格遵守 hard_depends_on 与 single_active_card=true。
若不可推进，仅返回状态码（NO_INCREMENT / RECONCILE_ONLY / BLOCKED_*）、阻断原因、缺失前置条件；不要提供修复建议或下一步动作。
```

### 12.4 一键联动命令（手工触发时）

```bash
# 1) 生成主计划
/jjk-plan -p -h

# 2) 生成拆解与执行真理源
/jjk-vkplan

# 3) 导入真实看板卡
/jjk-vktodo <YYYY-MM-DD_主题>

# 4) 绑定自动执行作用域
python3 scripts/set_active_task.py --task-split-dir <YYYY-MM-DD_主题> --project-id <VK_PROJECT_ID>
```
