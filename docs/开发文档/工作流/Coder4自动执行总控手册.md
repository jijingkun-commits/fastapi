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

## 8. 你日常怎么用（最短路径，尽量不手工）

### Step A：产出任务拆解（你做）

1. `/jjk-plan -p -h`
2. `/jjk-vkplan`（带 `project_id`）

建议输入优先使用合并报告：

- `output/全面代码审查报告_合并版_20260225.md`

### Step B：落卡到 VK（让 Bot 代办）

你不手工执行 `/jjk-vktodo`。  
直接让 `jjk_coder4_bot` 执行落卡，并强制“单卡滚动创建”：

1. 调用 `/jjk-vktodo <task_split_dir>`
2. 当前有 scoped 非 done 卡时，禁止再创建下一张
3. 仅在当前卡 `done` 后，按 `card_order` 创建下一张
4. 全程保持“每次最多 1 张 scoped 非 done 卡”

### Step C：更新自动作用域（让 Bot 代办）

你不手工跑脚本。  
让 `jjk_coder4_bot` 执行 scope guard（自动调用 `set_active_task.py`），并回报：

1. scope_guard action（`scope_switched|already_active|no_request`）
2. `_active_task.json` 的 `task_key / task_split_dir / project_id`
3. 与当前 `vk_cards.json` 是否一致

### Step D：开启自动执行（Bot 运维）

1. 先 `cron list`（含禁用项）获取实时 `job_id`
2. 再对该 `job_id` 执行 `cron update enabled=true`
3. 禁止写死历史 `job_id`

### Step E：区分单轮与持续

1. 只发执行提示词 = 只跑单轮
2. `cron enabled=true` = 持续自动跑（`*/3 * * * *`）

### Step F：日常只做三件事

1. 让 Bot 回报 cron 开关状态
2. 让 Bot 回报最近 N 次 runs
3. 发现阻断码后，按第 9 节语义处理

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

## 12. 可复用提示词模板（精简版）

默认场景：你只和 `jjk_coder4_bot` 对话，不手工跑脚本。

### 12.1 `/jjk-plan -p -h`（短模板）

```text
/jjk-plan -p -h
主题：<主题名>
输入：output/全面代码审查报告_合并版_20260225.md
要求：
1) 产出 <topic>_requirements.md 与 <topic>_implementation_plan.md
2) implementation_plan 必须含 planning_contract（execution_mode=serial, strict_single_active_card=true）
3) 若 hydrate 映射不全，标注 BLOCKED 并给出 unmapped 清单
```

### 12.2 `/jjk-vkplan`（短模板）

```text
/jjk-vkplan
主题：<主题名>
project_id：<VK_PROJECT_ID>
要求：
1) 严格继承 planning_contract，不改 card_id/feature_id/depends_on
2) 生成 vk_cards.json + parallel_plan.md + WS 文档
3) gate_contract.mode=as_cards 时必须产出 G 卡并闭环依赖
4) 任一字段缺失或映射失败，直接 BLOCKED
```

### 12.3 让 Bot 代办“落卡 + 绑定作用域”（你不手工）

```text
请在 /Users/jijingkun/bojxAI/fastapi 执行以下任务并回报结果：
1) 执行 /jjk-vktodo <task_split_dir> 落卡到 project_id=<VK_PROJECT_ID>
2) 按 card_order 单卡滚动创建：当前有 scoped 非 done 卡时，不创建下一张；仅在当前卡 done 后创建下一张
3) 写入 /Users/jijingkun/.openclaw/workspace-dev/state/coder4_scope_request.json：
   {"task_split_dir":"<task_split_dir>","project_id":"<VK_PROJECT_ID>","requested_by":"operator","requested_at":"<now>","applied":false}
4) 执行 python3 scripts/coder4_scope_guard.py --repo-root /Users/jijingkun/bojxAI/fastapi --active-task docs/内部参考/任务拆解/_active_task.json --scope-request /Users/jijingkun/.openclaw/workspace-dev/state/coder4_scope_request.json
5) 回报：
   - 当前 scoped 卡总数与非 done 数
   - scope_guard action
   - _active_task.json 的 task_key/task_split_dir/project_id
   - 与 vk_cards.json 是否一致
```

### 12.4 让 Bot 代办“cron 启停与巡检”

```text
请做 coder4 cron 运维（先查后改）：
1) cron list（含 disabled）找到当前 coder4 job_id
2) cron update enabled=true（或 false）
3) cron runs 返回最近 5 次结果
注意：禁止 create 新 job，只能 update 现有 job。
```

### 12.5 一条消息版（推荐）

```text
请在 /Users/jijingkun/bojxAI/fastapi 按顺序一次完成以下动作，并在最后给出结构化回报：

[输入]
- task_split_dir=<YYYY-MM-DD_主题>
- project_id=<VK_PROJECT_ID>
- mode=<start|stop>  # start=开启自动持续，stop=仅停止 cron

[执行步骤]
1) 执行 /jjk-vktodo <task_split_dir>，按 card_order 单卡滚动创建：
   - 当前有 scoped 非 done 卡时，禁止创建下一张
   - 仅在当前卡 done 后创建下一张
2) 写入 coder4_scope_request.json（task_split_dir/project_id/applied=false）
3) 执行 python3 scripts/coder4_scope_guard.py --repo-root /Users/jijingkun/bojxAI/fastapi --active-task docs/内部参考/任务拆解/_active_task.json --scope-request /Users/jijingkun/.openclaw/workspace-dev/state/coder4_scope_request.json
4) 校验 _active_task.json 与 vk_cards.json 一致性（task_key/task_split_dir/project_id）
4) 调用 cron list（含 disabled）定位 coder4 job_id
5) 若 mode=start：cron update enabled=true；若 mode=stop：cron update enabled=false
6) 调用 cron runs 返回最近 5 次结果

[输出格式]
- vktodo: success/fail + scoped总数 + scoped非done数
- scope_guard: action + reason_or_none
- active_task: task_key / task_split_dir / project_id / preflight_required
- consistency: pass/fail + 差异项
- cron: job_id / enabled(before->after)
- runs: 最近5次（status + reason）
- final_status: READY_AUTORUN | READY_MANUAL | BLOCKED
```

### 12.6 最短开跑口令（你只说一句）

```text
开始执行 <task_split_dir> project_id=<VK_PROJECT_ID>
```

期望 Bot 内部动作：
1) `/jjk-vktodo <task_split_dir>`（单卡滚动创建）
2) 写入 `coder4_scope_request.json`
3) 执行 `python3 scripts/coder4_scope_guard.py ...`
4) `cron list` 找到 coder4 job，再 `cron update enabled=true`
