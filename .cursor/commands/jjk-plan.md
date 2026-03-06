---
description: 正式规划入口：产出 requirements + implementation_plan，并给下游执行链提供稳定契约
---

> 参考规则: @dual-database

# 规划工作流（Planning Workflow）

将 `/jjk-clarify` 冻结后的设计，转成可执行的规划产物。

> **中文主导**：思考与输出统一中文。  
> **完成态**：同时具备 WHAT（`requirements`）+ HOW（`implementation_plan`），而不是只写思路。

---

## 产物与边界

必须产出：

1. `docs/内部参考/迭代需求/<topic>_requirements.md`
2. `docs/内部参考/迭代需求/<topic>_implementation_plan.md`

可选产出（parallel 模式）：

3. `card_seed`（供 `/jjk-vkplan` 继续拆解）

本命令不做：

1. 不直接改业务代码；
2. 不直接落看板卡；
3. 不跳过设计审批。

---

## 输入前置（强制）

1. 同主题 design 存在：`docs/plans/YYYY-MM-DD-<topic>-design.md`。
2. design 必须有审批记录：`design_approved=true`、`approved_at`、`approved_round`、`approval_evidence`。
3. design 必须有 `product_contract`（PRD-Lite），至少包含：
   - `target_users/core_scenarios/business_goals/non_goals/acceptance_gates`
4. design 必须有 `clarify_handoff_contract`：
   - 固定使用：`required.requirement_seeds/implementation_seeds/execution_chain_seed`
5. design 必须有 `clarify_consistency_check`：
   - `clarify_phase=approval`
   - `open_questions_count=0`
   - `question_mode in {package,single}`
6. 若 `implementation_seeds` 为轻量输入（仅 `task_id/file_paths/symbols/change_type`），必须在本命令补齐可执行字段再进入下游。

失败时：

1. 审批缺失：`DESIGN_APPROVAL_REQUIRED`
2. 产品契约缺失：`CLARIFY_PRODUCT_CONTRACT_MISSING`
3. handoff 缺失：`CLARIFY_HANDOFF_CONTRACT_MISSING`
4. 澄清状态缺失：`CLARIFY_CONSISTENCY_CHECK_MISSING`
5. 澄清状态无效：`CLARIFY_DESIGN_STATE_INVALID` / `CLARIFY_OPEN_QUESTIONS_REMAIN`
6. 桥接不完整：`CLARIFY_PLAN_BRIDGE_BROKEN`

---

## 参数与模式

参数：

1. `parallel`（或 `-p`）：产出并行拆解种子；
2. `hydrate`（或 `-h`）：历史资料归一化后再规划。

模式：

1. `core`（默认）：产出 requirements + implementation_plan；
2. `parallel`：额外产出可被 `/jjk-vkplan` 消费的最小 card_seed；
3. `hydrate`：记录历史来源映射，不新增主文档类型。

---

## 执行流程（精简版）

### 0) 上下文校验（必做）

至少检查：

1. 当前代码与文档上下文（`git status`、相关 docs）。
2. 主题命名是否与任务拆解目录语义一致。
3. 是否存在同主题旧文档需要续写/覆盖。

### 1) 产出 WHAT：`requirements`

`<topic>_requirements.md` 至少包含：

1. `requirements_contract`
2. `product_contract_matrix`
3. `fr_contract_matrix`
4. `traceability_matrix`

强约束：

1. 每条 `FR-*` 必须可追溯到 handoff `requirement_seeds`，并至少映射 1 条 `business_goal_metrics`；
2. `NFR-*` 必须写数字阈值；
3. 新开关默认 `true`，回退时 `false`（除非用户明确要求灰度）。

### 2) 产出 HOW：`implementation_plan`

`<topic>_implementation_plan.md` 至少包含：

1. `implementation_tasks`
2. `task_to_pr_mapping`
3. `planning_contract`
4. `execution_contract`
5. `implementation_readiness`

`implementation_tasks[*]` 必填：

1. `task_id`
2. `feature_id`
3. `source_seed_ref`
4. `phase`
5. `file_paths`
6. `symbols`
7. `change_type`
8. `acceptance_cmds`
9. `rollback_point`
10. `pr_id`
11. `depends_on_tasks`
12. `owner`
13. `risk_point`

补齐规则（v3 适配）：

1. 若上游是轻量 `implementation_seeds`，本步骤必须补齐 `feature_id/acceptance_cmds/rollback_point/pr_id/phase/depends_on_tasks`。
2. 补齐前禁止标记 `implementation_ready=true`。

### 3) 执行承接校验（必做）

```bash
python3 scripts/check_clarify_plan_alignment.py \
  --requirements-path docs/内部参考/迭代需求/<topic>_requirements.md \
  --implementation-path docs/内部参考/迭代需求/<topic>_implementation_plan.md \
  --output docs/内部参考/迭代需求/<topic>_clarify_plan_alignment.json
```

通过标准：

1. `ok=true`
2. 无 `CLARIFY_PLAN_BRIDGE_BROKEN`
3. 无 `PLAN_TRACEABILITY_MATRIX_BROKEN`
4. 无 `PLAN_ACCEPTANCE_REF_BROKEN`
5. 无 `PLAN_IMPLEMENTATION_DETAIL_INSUFFICIENT`

未通过：

1. 输出 `PLAN_CLARIFY_ALIGNMENT_FAILED`
2. 禁止进入 `/jjk-vkplan` 与 `/jjk-imp`
3. 按错误码回退 `/jjk-clarify` 或继续细化 `/jjk-plan`

### 4) 文档索引与完整性校验（按需）

若本轮新建/重命名了 `*_requirements.md` 或 `*_implementation_plan.md`：

```bash
python3 scripts/docs_guard.py --strict
```

命中 `summary_missing_doc` 时，本轮规划视为未完成。

### 5) 下游分流

1. 单线执行：`next_step=/jjk-imp`
2. 并行执行：`next_step=/jjk-vkplan`
3. 信息不足：`next_step=/jjk-plan`（继续细化）

---

## 输出要求（强制）

必须输出：

1. 规划结论：`implementation_ready`、`execution_contract_ready`
2. 阻塞项：`blocked_by`
3. 下一步命令：`/jjk-imp | /jjk-vkplan | /jjk-plan`
4. 产物路径：requirements、implementation_plan、alignment 报告

---

## 禁止项（强制）

1. 禁止在无审批设计时进入规划。
2. 禁止 requirements / implementation_plan 主文档写 A/B/C 对比。
3. 禁止 `implementation_tasks` 缺关键字段就宣称“可执行”。
4. 禁止跳过 `check_clarify_plan_alignment.py` 直接进入下游。
5. 禁止篡改上游 `task_id/feature_id` 的语义映射。

---

*使用 `/jjk-plan` 触发。目标是“最小文字、最大可执行性、稳定承接下游”。*
