---
description: WS 执行入口（消费 /jjk-vkplan 契约）：按单个工作包实现、验证与回填，支持大 WS 自动 Team
---

> 参考规则: @dual-database

# 子任务实现工作流 (Implementation per Workstream)

`/jjk-imp-ws` 是 `jjk-*` 体系里的 WS 级实现入口，负责把单个 `WS-*.md` 按契约落到代码、测试和回填文档。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 与 Superpowers / OMX 的分工（强制）

1. `/jjk-vkplan`：提供 `WS-*.md`、`vk_cards.json`、`parallel_plan.md` 执行契约。
2. `/jjk-vktodo`：负责卡片创建与状态推进（Doing/Review/Gate/Done）。
3. `test-driven-development`：负责测试先行方法（可用时优先）。
4. `verification-before-completion`：负责完成前证据校验（可用时优先）。
5. `systematic-debugging`：仅在 WS 执行异常时用于根因定位。
6. `team`（OMX）：当单个 WS 规模过大时并行执行与汇总。
7. `/jjk-imp-ws`：负责单 WS 边界控制、任务落地、证据回填与 PR 对齐。

约束：

1. 禁止在 `/jjk-imp-ws` 重写 `/jjk-vkplan` 的卡片与依赖语义。
2. 禁止把 `/jjk-imp-ws` 当“自由编码入口”；必须消费 WS 契约字段。
3. `/jjk-team-imp-ws` 不再作为主入口，由本命令按规模自动升级 Team。

## 跨 IDE 调用方式

1. Cursor / Claude Code：`/jjk-imp-ws`
2. Codex：`/prompts:jjk-imp-ws`

> 说明：Codex 的自定义命令入口是 `/prompts:<name>`，不是 `/<name>`。

## 模板来源优先级（跨项目，强制）

`/jjk-imp-ws` 的模板按以下优先级读取：

1. 全局共享模板（默认主模板）：
   `/Users/jijingkun/.codex/engineering/templates/jjk_imp_ws_templates.md`
2. 项目覆盖模板（仅放差异，不放全量复制）：
   `docs/内部参考/迭代需求/_templates/jjk_imp_ws_templates.md`

若全局模板缺失，输出标记 `GLOBAL_TEMPLATE_MISSING` 并提示先初始化共享模板目录。

## 何时使用

| 场景 | 推荐命令 |
|---|---|
| 已有并行拆解，执行某个 WS 实现 | `/jjk-imp-ws` ✅ |
| 没有 WS 文档，执行整体实现 | `/jjk-imp` |
| 仅做落卡/状态推进，不改代码 | `/jjk-vktodo` |

---

## 输入前置（强制）

必须输入并可解析：

1. 单个 `WS-*.md` 文档。
2. 同目录 `parallel_plan.md`。
3. 同目录 `vk_cards.json`。
4. 同主题：`docs/内部参考/迭代需求/<topic>_requirements.md`。
5. 同主题：`docs/内部参考/迭代需求/<topic>_implementation_plan.md`。
6. 若 WS 引用专项附录：`docs/内部参考/迭代需求/<topic>_<appendix>_implementation_plan.md`。

硬约束：

1. 当前 WS 必须能唯一映射到 `card_id/task_id/pr_id`（来源优先级：`vk_cards.json` -> `implementation_plan.task_to_pr_mapping`）。
2. 若 `pr_id` 缺失/冲突，`FAIL_FAST` 输出 `IMP_WS_PR_MAPPING_MISSING`。
3. 若 `hard_depends_on` 未满足，`FAIL_FAST` 输出 `IMP_WS_DEPENDENCY_NOT_READY`。
4. 若当前 `WS` 与 `_active_task.json.task_split_dir` 不一致，`FAIL_FAST` 输出 `IMP_WS_ACTIVE_TASK_MISMATCH`。
5. 若卡片状态不在可执行集合（`Doing` 或已批准的 `Backlog` 应急执行），`FAIL_FAST` 输出 `IMP_WS_CARD_NOT_EXECUTABLE`。

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
   - `acceptance_cmds`
   - `rollback_point`
3. Gate WS 必须回填 TC-ID 映射表。
4. 命中浏览器测试触发条件时，回填命令、结果与证据路径。

### 5) Gate 自动回填（WS-G1/WS-G2 必做）

执行 Gate WS 时，完成门禁命令后必须执行自动回填脚本，禁止手工改数字：

```bash
venv/bin/python scripts/backfill_gate_status.py --plan docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/parallel_plan.md
```

规则：

1. 脚本自动执行 `pytest/tsc/lint/docs_guard` 并回写 `parallel_plan.md` Gate 区块。
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

见全局模板：`/Users/jijingkun/.codex/engineering/templates/jjk_imp_ws_templates.md`（`输出模板` 段）。
若本项目有覆盖规则，再查：`docs/内部参考/迭代需求/_templates/jjk_imp_ws_templates.md`。

## 禁止项（强制）

1. 禁止无 `WS-*.md` 直接执行 `/jjk-imp-ws`。
2. 禁止跨 WS 越权修改。
3. 禁止在 `IMP_WS_PR_MAPPING_MISSING` 或 `IMP_WS_DEPENDENCY_NOT_READY` 时继续编码。
4. 禁止跳过 `acceptance_checks` 直接宣称完成。
5. 禁止 Gate 结果手工改写而不经脚本回填。

## 推荐链路

`/jjk-vkplan -> /jjk-vksync -> /jjk-vktodo -> /jjk-imp-ws -> /jjk-create-pr`

## 使用示例

```text
/jjk-imp-ws @docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/workstreams/WS-01_<并行任务>.md
```

```text
/jjk-imp-ws @docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/workstreams/WS-G1_集成回归门禁.md
```

```text
/jjk-imp-ws @docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/workstreams/WS-G2_文档终稿门禁.md
```

---
*使用 `/jjk-imp-ws` 触发。目标是“单 WS 契约执行 + 证据闭环”，不是自由跨包开发。*
