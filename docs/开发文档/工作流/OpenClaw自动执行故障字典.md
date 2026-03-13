# OpenClaw自动执行故障字典

本文用于解释 `/jjk-plan + /jjk-vkplan + OpenClaw coder4` 自动执行链路中的常见状态码，帮助快速定位是“前置条件未满足”还是“执行器异常”。

## 1. 先看三个真理源

发生 `NO_INCREMENT/BLOCKED/RECONCILE_ONLY` 时，先核对以下文件：

1. `workdocs/任务拆解/<task_split_dir>/contracts/_active_task.json`
2. `workdocs/任务拆解/<YYYY-MM-DD_主题>/contracts/vk_cards.json`
3. `workdocs/任务拆解/<task_split_dir>/contracts/implementation_plan.md`（`planning_contract`）

若三者任一不一致，先修文档与作用域，再继续自动执行。

## 2. 状态码对照

| 状态码 | 含义 | 常见根因 | 最小修复动作 |
|---|---|---|---|
| `NO_INCREMENT(bootstrap_readonly)` | 首轮只读保险触发 | 新任务首次启动，执行器只做校验不派单 | 等下一轮，或确认状态文件已写回 `bootstrap_readonly_done=true` |
| `NO_INCREMENT(scope_no_active)` | 作用域内无可推进卡片 | 未执行 `/jjk-vktodo` 落卡；或卡片未命中 `task_key` | 执行 `/jjk-vktodo <task_split_dir>` 并检查标题/标签是否带 `task_key` |
| `NO_INCREMENT(main_busy)` | 主会话繁忙 | main 会话 queue depth > 0 | 等待下一轮，避免并发派单 |
| `NO_INCREMENT(duplicate_signature)` | 防重去重命中 | 短时间内签名完全相同 | 等冷却窗口结束后再推进 |
| `RECONCILE_ONLY(scope_conflict)` | 作用域冲突 | 当前 `task_key` 之外还有活动卡 | 先清理非当前任务的 `inprogress/inreview` 卡 |
| `RECONCILE_ONLY(multi_active_scoped)` | 串行门禁触发 | 同一 `task_key` 下活动卡超过 1 张 | 收敛到 1 张活动卡后再跑 |
| `BLOCKED_DOC_CONTEXT` | 文档上下文不完整/不一致 | `_active_task.json` 缺字段；`task_key` 对不上；主计划链断裂 | 重新执行 `python3 scripts/coder4/set_active_task.py`，并核对 `contracts/vk_cards.json` 与计划文档 |
| `BLOCKED_FEATURE_MAPPING` | 卡片字段不完整 | 缺 `feature_ids/mechanism_summary/code_anchor_refs/...` | 回到 `/jjk-vkplan` 重产，直到 fail-fast 校验通过 |
| `BLOCKED_SERIAL_DEPENDENCY` | 前置依赖未满足 | 当前卡 `hard_depends_on` 未完成 | 先完成前置卡，再推进当前卡 |
| `BLOCKED_EVIDENCE_GAP` | 证据不足，不能收口 | 证据绑定失败或验收证据缺失 | 补齐 `task_id/turn_id/process_id/status`，并确认 `target_task_id == evidence_task_id` 后重试 |
| `BLOCKED_CRON_POLICY_DRIFT` | cron 策略与规则文档冲突 | `WORKFLOW_AUTO.md` 与 cron payload 口径不一致 | 对齐两侧规则后再启用自动任务 |
| `BLOCKED_STALL` | 卡死恢复失败 | `stop -> continue` 后仍无增量 | 人工介入：检查会话、依赖、网关状态 |

## 3. 快速排查顺序（建议）

1. 先看作用域：`_active_task.json` 的 `task_key/project_id/task_split_dir`。
2. 再看卡片：`vk_cards.json` 是否包含完整字段和正确依赖。
3. 再看看板：是否存在 scoped 卡、是否只有 1 张活动卡。
4. 最后看执行器：是否因防重/冷却/首轮只读策略主动停步。

## 4. 与命令链路的关系

1. `/jjk-plan` 负责定义契约，不直接生成看板卡。
2. `/jjk-vkplan` 负责生成可执行拆解；`scripts/coder4/set_active_task.py` 负责写入 `_active_task.json`。
3. `/jjk-vktodo` 负责把拆解落成真实看板卡。
4. OpenClaw coder4 只在上述前置成立后，才会进入真实推进。
