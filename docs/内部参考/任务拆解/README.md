# 任务拆解目录说明

本目录用于沉淀“并行执行计划书”，服务于多人协作与复杂需求拆分。

## 目录结构

```text
docs/内部参考/任务拆解/
├── README.md
├── _templates/
│   ├── active_task_template.json
│   ├── parallel_plan_template.md
│   ├── workstream_template.md
│   └── merge_checklist_template.md
└── <YYYY-MM-DD_主题>/
    ├── _active_task.json          # 该任务的作用域真理源
    ├── .state/                    # 该任务运行态（state/session/ledger）
    ├── parallel_plan.md
    ├── workstreams/
    │   ├── WS-00_*.md
    │   ├── WS-01_*.md
    │   └── WS-G1_*.md
    └── merge_checklist.md
```

## 使用建议

1. 先执行 `/jjk-plan`（或并行场景用 `/jjk-vkplan`），确认需求与架构边界。
2. 再执行 `/jjk-vkplan`，基于模板输出 `WS-00 + WS-N` 并行工作包。
3. 执行 `/jjk-vktodo` 读取 `vk_cards.json` 批量落卡（卡片自动带 `task_key` 前缀）。
4. 成功落卡后执行 `scripts/coder4/set_active_task.py`，写入 `docs/内部参考/任务拆解/<task_split_dir>/_active_task.json`（任务级真理源）。
5. 每个工作包按 `/jjk-imp-ws` 独立实施。
6. 运行态规则、门禁与排障请参考 `docs/开发文档/工作流/Coder4自动执行总控手册.md`。

## OpenClaw 自动执行最短链路（串行）

当目标是让 OpenClaw coder4 自动执行时，推荐按以下最短链路推进：

1. `/jjk-plan -p -h`：产出 `<topic>_requirements.md` + `<topic>_implementation_plan.md`（含 `planning_contract`）。
2. `/jjk-vkplan`：产出 `parallel_plan.md`、`WS-*.md`、`vk_cards.json`。
3. `/jjk-vktodo <task_split_dir>`：把 `vk_cards.json` 落到真实看板卡片。
4. `python3 scripts/coder4/set_active_task.py --task-split-dir <dir> --project-id <id>`：写入任务级自动执行作用域。
5. 启动 coder4 自动任务（或 `cron run` 调试）。

关键提醒：

1. 只有 `vk_cards.json` 但没有 `/jjk-vktodo` 落卡，自动执行器会返回 `NO_INCREMENT(scope_no_active)`。
2. 串行模式下同一时刻仅允许 1 张 scoped 活动卡（`inprogress + inreview <= 1`）。
3. 首次启动建议先走“首轮只读保险”，确认作用域与门禁无误后再进入真实推进。
4. 可直接复用的 `/jjk-plan`、`/jjk-vkplan`、coder4 启动提示词模板见：`docs/开发文档/工作流/Coder4自动执行总控手册.md` 第 12 节。
5. 若你希望“不可推进时只报状态，不给修复建议”，使用总控手册第 `12.3.1` 节模板。
6. “手动单轮提示词”与“自动 cron 持续执行”的区别，以及只用对话做启停巡检，见总控手册第 8 节 Step F/Step G。

## 自动执行真理源（必填）

`_active_task.json` 采用“任务级单一真理源”：

- 任务级真理源：`docs/内部参考/任务拆解/<task_split_dir>/_active_task.json`
- 运行态目录（canonical）：`.artifacts/states/task_splits/<task_split_dir>/<task_key>/`
- 兼容路径（迁移期 symlink）：`docs/内部参考/任务拆解/<task_split_dir>/.state/<task_key>/`

- 必填字段：`project_id/task_split_dir/task_key/execution_mode/single_active_card/auto_done_policy/preflight_required`
- `task_key` 必须与对应 `vk_cards.json` 顶层 `task_key` 一致。
- 运行态文件（`task-runner-state/session/ledger/idempotency/run-lock`）统一落在当前任务目录 `.state` 下，避免跨任务串线。
- 默认最小运行态：`task-runner-state.json` + `task-ledger.jsonl` + `active-session-<session_id>.json`。
- scope request 默认文件（canonical）：`.artifacts/states/task_splits/<task_split_dir>/coder4_scope_request.json`。
- 幂等与锁文件：`coder4-idempotency.json`、`coder4-run.lock`、`*.lock`、`*.bak` 均位于 canonical 运行态目录 `.artifacts/states/task_splits/<task_split_dir>/<task_key>/`；旧 `docs/**/.state/` 路径仅保留迁移期兼容 symlink。
- 禁止使用仓库根目录 `.state` 或用户主目录全局 state 作为默认回退。
- `verify/merge` 结果固定内联写入 `task-runner-state.json.gate_results/merge_results`，不再写独立 attempt 文件。
- 当仓库存在多个任务级 `_active_task.json` 时，必须显式传入 `--active-task`（或设置 `WT_FLOW_ACTIVE_TASK_FILE` / `WT_FLOW_TASK_SPLIT_DIR` / `CODER4_ACTIVE_TASK_FILE`），避免默认推断串线。

推荐使用脚本更新（避免手改）：

```bash
python3 scripts/coder4/set_active_task.py \
  --task-split-dir 2026-02-21_openclaw迁移重建基线 \
  --project-id 2ea99dca-a111-43bb-ae73-f836bafe0fb0
```

## 作用域匹配规则（scope）

自动执行器只处理“当前任务目录 `_active_task.json` 指向的 task_key”作用域内卡片，匹配规则如下：

1. `title` 含 `[task_key]`
2. 或 `labels` 含 `task_key`
3. 或卡片 key 前缀为 `<task_key>::`

常见现象：

1. `NO_INCREMENT(scope_no_active)`：当前看板没有命中作用域的活动卡或待执行卡。
2. `RECONCILE_ONLY(scope_conflict)`：存在非当前 `task_key` 的活动卡，需先收敛看板。
3. `BLOCKED_DOC_CONTEXT`：`_active_task.json`、`vk_cards.json`、主计划链路不一致。

更多状态码含义与处理动作请参考：`docs/开发文档/工作流/OpenClaw自动执行故障字典.md`。

## 执行脚本目录约定

- 核心实现目录：`scripts/coder4/`（可跨项目整体迁移）。
- 兼容入口目录：`scripts/` 保留薄入口脚本，仅负责转发到 `scripts/coder4/`。
- 新增/重构 coder4 执行链脚本时，优先落在 `scripts/coder4/`，避免散落。

## 并行前 3 秒判断法

凡是“必须等别人先做完才能开始”的任务，一律不作为并行 WS。

- 可独立开始 + 可独立交付 + 无共享写冲突 → 可并行
- 其余情况 → 不并行（改为单任务 `/jjk-imp` 或先解耦再拆）

## 无总控协作流程（默认）

1. 拆解后由需求方将 `WS-*.md` 一对一分配给协作者。
2. 协作者仅修改各自白名单文件，不跨 WS 改动。
3. 协作者在各自 WS 文档末尾填写“协作者自检卡”并回传。
4. 仅当出现共享文件/共享字段冲突时，启用 `merge_checklist.md` 汇总检查。
