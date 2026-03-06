---
name: jjk-vkplan
description: "Use when you need `jjk-vkplan` in this repository. Source intent: 并行拆解入口：消费 /jjk-plan 产物并生成可执行卡片契约"
---
<!-- AUTO-GENERATED: jjk-skill-mirror -->
<!-- source: .cursor/commands/jjk-vkplan.md -->

> 参考规则: @dual-database

# VKPlan 工作流（Split to Executable Cards）

`$jjk-vkplan` 负责把规划产物转换为“可落卡、可执行、可追溯”的并行拆解产物。

> **中文主导**：思考与输出统一中文。

---

## 输入前置（强制）

必须存在：

1. `docs/内部参考/迭代需求/<topic>_requirements.md`
2. `docs/内部参考/迭代需求/<topic>_implementation_plan.md`
3. `implementation_plan.planning_contract`
4. `implementation_plan.execution_contract`
5. `implementation_plan.task_to_pr_mapping`
6. `implementation_plan.implementation_tasks`（含 `task_id/feature_id/pr_id/acceptance_cmds`）

自动执行场景还必须具备 `project_id`（显式参数优先；仅可从同任务目录 `_active_task.json` 推断，不再依赖根索引）。

失败码：

1. `VKPLAN_INPUT_NOT_READY`
2. `VKPLAN_MISSING_PROJECT_ID`
3. `VKPLAN_PR_MAPPING_MISSING`
4. `VKPLAN_EXECUTION_CONTRACT_MISSING`
5. `VKPLAN_TASKS_MISSING`

---

## 执行流程（五步）

### 0) 上下文校验

至少检查：

1. 同主题主计划与历史拆解目录；
2. `planning_contract.execution_mode/card_order/cards/gate_contract`；
3. 当前任务目录 `_active_task.json` 与 `vk_cards.json` 是否冲突。

### 1) 契约继承与硬校验

从 `planning_contract` 继承并保持不变：

1. `execution_mode`
2. `card_order`
3. `cards[].card_id`
4. `cards[].feature_ids`
5. `cards[].depends_on`
6. `cards[].done_gate`
7. `cards[].acceptance_checks`
8. `task_to_pr_mapping`
9. `execution_contract`

硬约束：

1. 禁止重命名 `card_id/feature_id`；
2. 禁止弱化 `depends_on`；
3. `execution_mode=serial` 必须保持单活卡推进语义；
4. 每张实现卡必须可映射唯一 `pr_id`。

### 2) 生成拆解产物

必须生成：

1. `docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/parallel_plan.md`
2. `docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/workstreams/WS-*.md`
3. `docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/vk_cards.json`

最小字段要求：

1. 卡片必须含 `card_id/feature_ids/task_ids/acceptance_checks/pr_id/pr_branch`；
2. `parallel_plan.md` 与 `vk_cards.json` 必须显式写入 `execution_contract`；
3. 若存在 `gate_contract.mode=as_cards`，Gate 必须实体化为卡片。

### 3) 全量消费覆盖校验（必做）

```bash
python3 scripts/check_plan_vk_coverage.py \
  --task-split-dir <YYYY-MM-DD_主题> \
  --output docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/consumption_report.json
```

通过标准：

1. `ok=true`
2. `missing_feature_ids=[]`
3. `missing_task_ids=[]`
4. `execution_contract_mismatch=[]`
5. `acceptance_mapping_missing=[]`
6. `missing_task_id_fields=[]`
7. `empty_task_ids=[]`
8. `clarify_plan_alignment.ok=true`

失败码：

1. `VKPLAN_CONSUMPTION_GAP`
2. `VKPLAN_EXECUTION_CONTRACT_MISMATCH`
3. `VKPLAN_ACCEPTANCE_MAPPING_BROKEN`
4. `VKPLAN_TASK_IDS_REQUIRED`
5. `CLARIFY_PLAN_ALIGNMENT_FAILED`
6. `PLAN_IMPLEMENTATION_DETAIL_INSUFFICIENT`

### 4) 真理源写入与回读（必做）

```bash
python3 scripts/set_active_task.py \
  --task-split-dir <YYYY-MM-DD_主题> \
  --project-id <project_id>
```

回读一致性要求（任务级真理源必须一致）：

1. `task_key`
2. `task_split_dir`
3. `project_id`

不一致时：`VKPLAN_ACTIVE_TASK_MISMATCH`。

### 5) 下游衔接

主链路：

`$jjk-plan -> $jjk-vkplan -> $jjk-cardrun -> $jjk-wtimp(executor_mode=cardrun_dispatch)`

可选建卡链路（只做可见性）：

`$jjk-vktodo(create-only)`

---

## Team 策略（简化）

命中任一条件可启用 Team：

1. `cards >= 8`
2. `feature_id >= 12`
3. 同时包含 Foundation + 并行层 + Gate
4. 预计需要多 worktree

无 Team 能力时输出 `TEAM_UNAVAILABLE_FALLBACK` 并降级单代理。

---

## 禁止项（强制）

1. 禁止缺 `planning_contract` 就生成卡片。
2. 禁止跳过 `check_plan_vk_coverage.py`。
3. 禁止缺失 `task_ids` 的卡片“先生成后补齐”。
4. 禁止只写文档 Gate、不实体化 Gate 卡。
5. 禁止 `execution_contract` 缺失时用默认值继续执行。

---

*使用 `$jjk-vkplan` 触发。目标是“最小流程生成可执行并行契约”。*
