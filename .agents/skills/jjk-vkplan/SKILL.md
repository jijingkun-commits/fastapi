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
6. `implementation_plan.implementation_tasks`（含 `task_id/feature_id/pr_id/risk_tags/mandatory_evidence/acceptance_cmds[*].kind`）

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

补充执行约束：执行命令时统一遵循 `.cursor/rules/core.mdc` 的“命令执行拆分”规则：单步单目标、失败只重跑当前步、长任务只轮询不重启、输出截断时优先拆短当前步。

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
5. 禁止把依赖自然时间流逝、观察窗口成熟、TTL 到期的条件生成到 `cards[].done_gate` 或 `cards[].acceptance_checks`。
6. `risk_tags/mandatory_evidence` 只允许继承或细化，禁止删除或弱化。
7. DB 链路拆成多卡时，必须声明 `cross_card_closure.required=true` 与 `closure_owner`。

### 2) 生成拆解产物

必须生成：

1. `workdocs/任务拆解/<YYYY-MM-DD_主题>/parallel_plan.md`（自动生成的人类可读总览，非机器真理源）
2. `workdocs/任务拆解/<YYYY-MM-DD_主题>/workstreams/WS-*.md`
3. `workdocs/任务拆解/<YYYY-MM-DD_主题>/contracts/vk_cards.json`

最小字段要求：

1. 卡片必须含 `card_id/feature_ids/task_ids/acceptance_checks/pr_id/pr_branch/risk_tags/mandatory_evidence`；
2. `vk_cards.json` 必须显式写入 `execution_contract`；`parallel_plan.md` 若生成，内容必须由 `vk_cards.json` 派生；
3. 若存在 `gate_contract.mode=as_cards`，Gate 必须实体化为卡片。
4. DB 风险链路卡必须补充 `cross_card_closure`（未拆链时可 `required=false`）。

### 3) 全量消费覆盖校验（必做）

```bash
python3 scripts/check_workflow_contract.py --mode plan_vk_coverage \
  --task-split-dir <YYYY-MM-DD_主题> \
  --output workdocs/任务拆解/<YYYY-MM-DD_主题>/reports/consumption_report.json
```

```bash
python3 scripts/check_workflow_contract.py --mode planning_temporal_gate \
  --task-split-dir <YYYY-MM-DD_主题> \
  --output workdocs/任务拆解/<YYYY-MM-DD_主题>/reports/temporal_gate_report.json
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
9. 无 `VKPLAN_TEMPORAL_BLOCKER_FORBIDDEN`
10. `evidence_mapping_missing=[]`
11. DB 拆链卡片满足 `cross_card_closure`

失败码：

1. `VKPLAN_CONSUMPTION_GAP`
2. `VKPLAN_EXECUTION_CONTRACT_MISMATCH`
3. `VKPLAN_ACCEPTANCE_MAPPING_BROKEN`
4. `VKPLAN_TASK_IDS_REQUIRED`
5. `CLARIFY_PLAN_ALIGNMENT_FAILED`
6. `PLAN_IMPLEMENTATION_DETAIL_INSUFFICIENT`
7. `VKPLAN_TEMPORAL_BLOCKER_FORBIDDEN`
8. `VKPLAN_EVIDENCE_MAPPING_BROKEN`
9. `VKPLAN_DB_CHAIN_SPLIT_UNCLOSED`


### 3.5) 数据库证据继承门禁（强制）

1. `vk_cards.json.cards[*]` 必须继承任务级 `risk_tags` 与 `mandatory_evidence`，不得仅保留 `acceptance_checks`。
2. 卡片的 `mandatory_evidence` 必须与 `task_ids` 对应任务并集一致；不一致时输出 `VKPLAN_EVIDENCE_MAPPING_BROKEN`。
3. 若 `risk_tags` 命中 `chat_db` 或 `data_db` 且链路拆分到多卡，必须显式声明 `cross_card_closure` 并指定闭环卡。
4. 未声明闭环卡时必须 `FAIL_FAST`：`VKPLAN_DB_CHAIN_SPLIT_UNCLOSED`。

### 4) 真理源写入与回读（必做）

拆卡后的唯一机器真理源为 `vk_cards.json`；`parallel_plan.md` 仅用于展示与兼容引用，不得再作为独立状态来源。

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
2. 禁止跳过 `check_workflow_contract.py --mode plan_vk_coverage`。
3. 禁止缺失 `task_ids` 的卡片“先生成后补齐”。
4. 禁止只写文档 Gate、不实体化 Gate 卡。
5. 禁止 `execution_contract` 缺失时用默认值继续执行。
6. 禁止生成依赖时间窗口成熟的串行阻断卡。

---

*使用 `$jjk-vkplan` 触发。目标是“最小流程生成可执行并行契约”。*
