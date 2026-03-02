---
name: jjk-vkplan
description: "Use when you need `jjk-vkplan` in this repository. Source intent: 并行拆解入口（消费 /jjk-plan 产物）：生成 WS 拆解与 vk_cards 执行契约"
---
<!-- AUTO-GENERATED: jjk-skill-mirror -->
<!-- source: .cursor/commands/jjk-vkplan.md -->

> 参考规则: @dual-database

# VKPlan 工作流 (Split to Executable Cards)

`$jjk-vkplan` 是 `jjk-*` 体系里的拆解入口，负责把 `jjk-plan` 的主计划转成“可落卡、可执行、可追溯”的并行产物。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 与 Superpowers / OMX 的分工（强制）

1. `writing-plans`：负责计划方法论（上游）。
2. `team`（OMX）：负责大规模拆解并行执行与证据汇总。
3. `$jjk-vkplan`：负责契约继承、卡片映射、Gate 实体化、真理源写入。

约束：

1. 禁止在 `$jjk-vkplan` 复制 `writing-plans` 正文。
2. `jjk-vkplan` 只消费 `jjk-plan` 主产物，不自行重写需求语义。
3. 插件可用时优先调用；不可用时必须显式 fallback。

## 跨 IDE 调用方式

1. Cursor / Claude Code：`$jjk-vkplan`
2. Codex：`$jjk-vkplan`

> 说明：Codex 推荐显式调用 `$jjk-vkplan`。

## 模板来源优先级（跨项目，强制）

`$jjk-vkplan` 模板按以下优先级读取：

1. 全局共享模板（默认主模板）：
   `/Users/jijingkun/.codex/engineering/templates/jjk_vkplan_templates.md`
2. 项目覆盖模板（仅放差异，不放全量复制）：
   `docs/内部参考/迭代需求/_templates/jjk_vkplan_templates.md`

若全局模板缺失，输出 `GLOBAL_TEMPLATE_MISSING` 并提示先初始化共享模板目录。

## 何时使用

| 场景 | 推荐命令 |
|---|---|
| 已完成 `$jjk-plan`，准备拆解为可执行卡 | `$jjk-vkplan` ✅ |
| 仅需诊断规划，不拆卡 | `$jjk-plan` |
| 已有 `vk_cards.json` 仅需落卡 | `$jjk-vktodo` |

---

## 输入前置（强制）

1. 同主题主产物必须存在：
   - `docs/内部参考/迭代需求/<topic>_requirements.md`
   - `docs/内部参考/迭代需求/<topic>_implementation_plan.md`
2. `implementation_plan` 必须含 `planning_contract`。
3. 若存在 `implementation_readiness` 且 `implementation_ready=false`，必须输出 `VKPLAN_INPUT_NOT_READY` 并回退 `$jjk-plan`。
4. 自动执行器场景必须拿到 `project_id`：
   - 显式参数优先；
   - 否则尝试读取 `docs/内部参考/任务拆解/_active_task.json`（活跃索引）；
   - 仍缺失则 `FAIL_FAST` 输出 `VKPLAN_MISSING_PROJECT_ID`。
5. `implementation_plan` 必须含 `task_to_pr_mapping`；缺失时 `FAIL_FAST` 输出 `VKPLAN_PR_MAPPING_MISSING`。

## 执行流程（强制顺序）

### 0) 先探索项目上下文（强制）

至少检查：

1. 同主题主计划与历史拆解目录。
2. `planning_contract` 的 `execution_mode/card_order/cards/gate_contract`。
3. 现有任务级 `_active_task.json`（`<task_split_dir>/_active_task.json`）与活跃索引是否与本轮主题冲突。

### 0.5) 大任务自动启用 Team（强制判定）

命中任一条件时自动启用 Team：

1. `cards` 数量 `>= 8`；
2. 涉及 `feature_id` `>= 12`；
3. 同时包含 Foundation + 并行层 + Gate 层拆解；
4. 预计需多 worktree 并行推进。

执行策略：

1. **有 Team 能力时**：并行生成 WS 草案与卡片映射，Leader 汇总唯一产物。
2. **无 Team 能力时**：降级单代理执行，并输出 `TEAM_UNAVAILABLE_FALLBACK`。

### 0.6) Team 交叉质检约束（新增，轻量）

1. Team 模式下必须启用抽检互审：至少抽检 `20%` 工作项（向上取整，最少 `1` 项）。
2. 每个抽检项必须包含：`1` 个质疑点、`1` 条验证命令、`1` 个通过/驳回结论。
3. 抽检未通过的工作项不得推进到下一阶段，必须先复核并补齐证据。
4. 阶段汇报至少包含：`结论`、`证据`、`剩余风险`。

### 1) 契约继承与校验（强制）

从 `planning_contract` 继承：

1. `execution_mode`
2. `card_order`
3. `cards[].card_id`
4. `cards[].feature_ids`
5. `cards[].depends_on`
6. `cards[].done_gate`
7. `cards[].acceptance_checks`
8. `gate_contract`（如存在）
9. `task_to_pr_mapping`
10. `execution_contract`（如存在）

硬约束：

1. 禁止重命名 `card_id/feature_id`。
2. 禁止弱化硬依赖 `depends_on`。
3. `execution_mode=serial` 时必须保持“单活卡推进”语义。
4. 每个实现卡必须能映射到唯一 `pr_id`，禁止“卡片存在但无 PR 归属”。
5. 若 `execution_contract` 缺失，默认补齐：
   - `delivery_mode=staged`
   - `execution_unit=per_pr`
   - `commit_policy=per_pr`
   并输出标记 `VKPLAN_EXECUTION_CONTRACT_DEFAULTED`。
6. `delivery_mode=staged` 时，阶段边界停顿属于预期完成态，不得按“异常中断”处理。

### 2) 产物生成（强制）

必须生成：

1. `docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/parallel_plan.md`
2. `docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/workstreams/WS-*.md`
3. `docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/vk_cards.json`

规则：

1. 每个 `card_id` 必须绑定 `feature_id` 与 `acceptance_checks`。
2. 每个 WS 必须引用来源主计划与对应 `feature_id`。
3. `output/**` 只能作为证据引用，不允许长文直贴到卡描述。
4. `vk_cards.json.cards[*]` 必须新增：
   - `pr_id`
   - `pr_branch`
   - `pr_depends_on`
   - `pr_subject`
5. `parallel_plan.md` 与 `vk_cards.json` 必须显式写入 `execution_contract`（继承或默认补齐后的最终值）。
6. 当 `delivery_mode=staged` 时，`parallel_plan.md` 必须写明 `stage_boundary_is_expected=true`。

### 3) Gate 卡片化与映射闭环（强制）

1. 若 `gate_contract.mode=as_cards`，所有 `gate_ids` 必须实体化为卡片。
2. Gate 卡必须包含：
   - `task_mode`
   - `merge_required`
   - `acceptance_checks`
   - `evidence_entry`
3. 双向覆盖校验必须通过：
   - forward：每张卡至少 1 个 `feature_id`
   - reverse：每个 `feature_id` 必须映射到实现卡
   - orphan：无未承载 `feature_id`
   - duplicate：无异常重复映射

失败标记：

1. `VKPLAN_GATE_CONTRACT_BROKEN`
2. `VKPLAN_FEATURE_MAPPING_BROKEN`
3. `VKPLAN_PR_MAPPING_BROKEN`

### 4) 真理源写入（强制）

必须执行：

`python3 scripts/set_active_task.py --task-split-dir <YYYY-MM-DD_主题> --project-id <project_id>`

并回读校验：

1. `docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/_active_task.json`
2. `docs/内部参考/任务拆解/_active_task.json`（活跃索引）

两者都必须满足：

1. `task_key` 一致
2. `task_split_dir` 一致
3. `project_id` 非空

不一致时输出 `VKPLAN_ACTIVE_TASK_MISMATCH` 并阻断下游。

### 5) 下游衔接（强制）

1. 推荐链路：`$jjk-plan -> $jjk-vkplan -> $jjk-vktodo -> $jjk-cardrun -> $jjk-imp-ws`
2. 未通过本命令硬校验时，禁止进入 `$jjk-vktodo`。
3. 若本轮停在阶段边界，必须输出 `VKPLAN_STAGE_BOUNDARY_EXPECTED` 并附当前 `pr_id/card_id`。

---

## 禁止项（强制）

1. 禁止在无 `planning_contract` 时生成 `vk_cards.json`。
2. 禁止跳过任务级 `_active_task.json` 与活跃索引 `_active_task.json` 的写入与回读校验。
3. 禁止缺字段卡片“先落卡后补齐”。
4. 禁止把 Gate 仅保留为文档描述而不实体化。
5. 禁止在 `task_to_pr_mapping` 缺失时继续生成可执行卡片。

---

*使用 `$jjk-vkplan` 触发。目标是“契约可执行拆解”，不是自由写卡。*
