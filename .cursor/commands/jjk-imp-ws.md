---
description: WS 执行入口（消费 /jjk-vkplan 契约）：按单个工作包实现、验证与回填，支持大 WS 自动 Team
---

> 参考规则: @dual-database

# 子任务实现工作流 (Implementation per Workstream)

`/jjk-imp-ws` 是 `jjk-*` 体系里的 WS 级实现入口，负责把单个 `WS-*.md` 按契约落到代码、测试和回填文档。


## 与 Superpowers / OMX 的分工（强制）
## 跨 IDE 调用方式
## 模板来源优先级（跨项目，强制）

`/jjk-imp-ws` 的模板按以下优先级读取：

1. 全局共享模板（默认主模板）：
   `${CODEX_HOME:-$HOME/.codex}/engineering/templates/jjk_imp_ws_templates.md`
2. 项目覆盖模板（仅放差异，不放全量复制）：
   `workdocs/_templates/jjk_imp_ws_templates.md`

若全局模板缺失，输出标记 `GLOBAL_TEMPLATE_MISSING` 并提示先初始化共享模板目录。

## 输入前置（强制）

必须输入并可解析：

1. 单个 `WS-*.md` 文档。
2. 同目录 `parallel_plan.md`（可选；自动生成总览）。
3. 同目录 `vk_cards.json`（唯一机器真理源）。
4. 同主题：`workdocs/需求/<topic>/requirements.md`。
5. 同主题：`workdocs/任务拆解/<YYYY-MM-DD_主题>/contracts/implementation_plan.md`。
6. 若 WS 引用专项附录：`workdocs/任务拆解/<YYYY-MM-DD_主题>/contracts/<appendix>_implementation_plan.md`。

硬约束：

1. 当前 WS 必须能唯一映射到 `card_id/task_id/pr_id`（来源优先级：`vk_cards.json` -> `implementation_plan.task_to_pr_mapping`）。
2. 若 `pr_id` 缺失/冲突，`FAIL_FAST` 输出 `IMP_WS_PR_MAPPING_MISSING`。
3. 若 `hard_depends_on` 未满足，`FAIL_FAST` 输出 `IMP_WS_DEPENDENCY_NOT_READY`。
4. 若当前 `WS` 与 `_active_task.json.task_split_dir` 不一致，`FAIL_FAST` 输出 `IMP_WS_ACTIVE_TASK_MISMATCH`。
5. 若卡片状态不在可执行集合（`Doing` 或已批准的 `Backlog` 应急执行），`FAIL_FAST` 输出 `IMP_WS_CARD_NOT_EXECUTABLE`。
6. 本轮必须产出可追溯提交证据（`commit_sha`）；若无文件改动且属于门禁/编排类 WS，必须生成带理由的空提交，否则 `FAIL_FAST` 输出 `IMP_WS_NO_COMMIT`。

## 执行约束（强制）

1. 只允许修改 WS 白名单文件；禁止修改黑名单文件。
2. 禁止跨 WS 改动与“顺手修”。
3. 发现必须跨 WS 才能完成时，停止并输出 `IMP_WS_SCOPE_BROKEN`。
4. Gate 层 WS 必须串行：`WS-G1 -> WS-G2`。
5. `WS-G1` 未通过且无批准豁免，不得执行 `WS-G2`（`IMP_WS_GATE_BLOCKED`）。
6. 执行 Gate WS 前，当前 `HEAD` 必须包含 `main/master` 最新提交；否则 `IMP_WS_BASELINE_NOT_READY`。
7. 必须消费 WS 的 `feature_id`、`机制摘要`、`代码锚点`、`acceptance_checks`，不得仅按标题发挥。
8. 结果回填必须附 `evidence_entry` 指向的权威入口。
9. 未确认 `pr_branch` 与 `pr_depends_on` 前，不得执行跨 PR 文件改动。

### Foundation / Gate 顺序（固定）

1. `WS-00` 在 `/jjk-vkplan` 阶段生成并冻结，默认不走 `/jjk-imp-ws`。
2. 先执行并行层 `WS-01 ... WS-N`。
3. 并行层完成后执行 `WS-G1_集成回归门禁.md`。
4. 最后执行 `WS-G2_文档终稿门禁.md`。
5. 不允许并行执行 `WS-G1/WS-G2`，也不允许跳过 `WS-G1` 直接执行 `WS-G2`。

---

## 执行流程（强制顺序）

### 0) 先探索上下文（强制）

补充执行约束：执行命令时统一遵循 `.cursor/rules/core.mdc` 的“命令执行拆分”规则：单步单目标、失败只重跑当前步、长任务只轮询不重启、输出截断时优先拆短当前步。

至少检查：

1. WS 文档与 `vk_cards.json` 映射是否一致。
2. 当前工作区改动与 WS 白名单边界是否冲突。
3. 相关测试入口、回归范围与证据入口位置。

### 0.5) 大 WS 自动启用 Team（强制判定）

触发条件（满足任一即可）：

1. 当前 WS 涉及文件 `>= 8`；
2. 当前 WS 含 `task_id >= 4`；
3. 同时跨后端/前端/AI-workflow/数据库中两类以上边界；
4. 预计需要并行子分片才能按期完成。

执行策略：

1. **有 Team 能力时**：并行执行子分片，Leader 汇总单 WS 回执。
2. **无 Team 能力时**：降级单代理执行，并输出 `TEAM_UNAVAILABLE_FALLBACK`。

### 0.6) Team 交叉质检约束

1. Team 模式下必须启用抽检互审：至少抽检 `20%` 工作项（向上取整，最少 `1` 项）。
2. 每个抽检项必须包含：`1` 个质疑点、`1` 条验证命令、`1` 个通过/驳回结论。
3. 抽检未通过的工作项不得推进到下一阶段，必须先复核并补齐证据。
4. 阶段汇报至少包含：`结论`、`证据`、`剩余风险`。

### 1) 契约校验与执行准备

1. 解析 `WS -> card_id/task_id/pr_id/pr_branch`。
2. 校验 `hard_depends_on`、Gate 前置、基线状态。
3. 生成本轮执行清单（文件/符号/验收命令/回滚点）。

### 2) 测试先行与最小实现

1. 可用 `test-driven-development` 时优先先写失败测试再改实现。
2. 不可用时输出 `TDD_UNAVAILABLE_FALLBACK`，但仍需补最小回归测试。
3. 按单 WS 边界执行最小实现，禁止越权。

### 3) 验证与证据收口

1. 执行 WS 中定义的 `acceptance_checks`。
2. 可用 `verification-before-completion` 时必须执行；不可用输出 `VERIFY_BEFORE_COMPLETION_UNAVAILABLE_FALLBACK`。
3. 无新鲜命令证据，禁止宣称完成（`IMP_WS_EVIDENCE_MISSING`）。

### 4) 回填与交接

必须完成：

1. 回填 WS 文档末尾“协作者自检卡”。
2. 回填 `pr_ready_manifest_ws`：
   - `ws_id`
   - `task_id`
   - `card_id`
   - `pr_id`
   - `pr_branch`
   - `pr_depends_on`
   - `changed_files`
   - `commit_sha`
   - `acceptance_cmds`
   - `rollback_point`
3. Gate WS 必须回填 TC-ID 映射表。
4. 命中浏览器测试触发条件时，回填命令、结果与证据路径。

提交门禁：

1. 合并前必须保证当前 WS 分支存在新提交（可通过 `git rev-parse HEAD` + `git rev-list --count <base>..HEAD` 佐证）。
2. 若属于门禁/编排类 WS 且无文件变更，允许 `--allow-empty` 空提交，但必须在 WS 回填中说明“空提交原因”。
3. 未回填 `commit_sha` 或无法证明提交归属当前 WS，`FAIL_FAST` 输出 `IMP_WS_NO_COMMIT`。

### 5) Gate 自动回填（WS-G1/WS-G2 必做）

执行 Gate WS 时，完成门禁命令后必须执行自动回填脚本，禁止手工改数字：

```bash
venv/bin/python scripts/backfill_gate_status.py --cards workdocs/任务拆解/<YYYY-MM-DD_主题>/contracts/vk_cards.json
```

规则：

1. 脚本自动执行 `pytest/tsc/lint/docs_guard` 并先回写 `vk_cards.json.gate_results`，再自动生成 `parallel_plan.md` 总览。
2. 默认执行基线硬拦截；未通过直接失败。
3. 任一命令失败返回非零退出码，Gate 判定失败。
4. 仅应急场景可用 `--skip-baseline-check`，并在 WS 文档记录批准人与原因。

---

## 浏览器测试触发规则

满足任一条件必须执行浏览器测试：

1. 改动 `web/src/**` 页面、组件、Hook 或交互流程。
2. 改动 SSE / 跨端契约并影响前端渲染或状态同步。
3. WS DoD 或需求文档明确要求 UI 验收。

可不执行（需同时满足）：

1. 仅后端/文档/脚本改动，且最小验证命令已覆盖风险。
2. 未改动前端消费链路。
3. 在“协作者自检卡”写明未执行原因。

---

## 输出模板（推荐）

见全局模板：`${CODEX_HOME:-$HOME/.codex}/engineering/templates/jjk_imp_ws_templates.md`（`输出模板` 段）。
若本项目有覆盖规则，再查：`workdocs/_templates/jjk_imp_ws_templates.md`。

## 禁止项（强制）

1. 禁止无 `WS-*.md` 直接执行 `/jjk-imp-ws`。
2. 禁止跨 WS 越权修改。
3. 禁止在 `IMP_WS_PR_MAPPING_MISSING` 或 `IMP_WS_DEPENDENCY_NOT_READY` 时继续编码。
4. 禁止跳过 `acceptance_checks` 直接宣称完成。
5. 禁止 Gate 结果手工改写而不经脚本回填。
6. 禁止无 `commit_sha` 证据结束 `/jjk-imp-ws`。

## 推荐链路

`主链: /jjk-plan -> /jjk-vkplan -> /jjk-cardrun -> /jjk-wtimp(executor_mode=cardrun_dispatch) -> /jjk-review -> /jjk-verify`

`可选分支: 需要远端 PR 交付时，在 /jjk-review 前插入 /jjk-create-pr`

## 使用示例

```text
/jjk-imp-ws @workdocs/任务拆解/<YYYY-MM-DD_主题>/workstreams/WS-01_<并行任务>.md
```

```text
/jjk-imp-ws @workdocs/任务拆解/<YYYY-MM-DD_主题>/workstreams/WS-G1_集成回归门禁.md
```

```text
/jjk-imp-ws @workdocs/任务拆解/<YYYY-MM-DD_主题>/workstreams/WS-G2_文档终稿门禁.md
```

---
*使用 `/jjk-imp-ws` 触发。目标是“单 WS 契约执行 + 证据闭环”，不是自由跨包开发。*
