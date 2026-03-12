---
description: 实施规划入口：消费 requirements 与 design，产出 implementation_plan 与完整 UAT cases
---

# 实施规划工作流（Execution Planning）

`/jjk-plan` 负责把已审批的需求与方案，转成**可执行任务**和**可消费的 UAT 用例**。

> **中文主导**：思考与输出统一中文。
>
> **唯一目标**：回答“先做什么、怎么做完、怎么验收”。

## 产物与边界

必须产出：

1. `docs/内部参考/迭代需求/<topic>_implementation_plan.md`
2. `docs/内部参考/迭代需求/<topic>_uat_cases.md`

本命令不做：

1. 不再产出 `requirements.md`；
2. 不再拍板架构方案；
3. 不直接改业务代码。

## 输入前置（强制）

1. 已审批的 `requirements.md`；
2. 已审批的 `design.md`；
3. 若命中 API 变化，应已明确 `api_doc_required`；
4. 若命中 refactor，应已明确 `shrink_contract`；
5. 若命中 DB 变化，应已明确 `db_migration_contract`。

失败时：

1. 缺少已审批需求：`PLAN_REQUIREMENTS_REQUIRED`
2. 缺少已审批方案：`PLAN_DESIGN_REQUIRED`
3. 缺少 shrink contract：`PLAN_SHRINK_CONTRACT_MISSING`
4. 方案与需求映射不完整：`PLAN_TRACEABILITY_MISSING`
5. UAT 不可消费：`PLAN_UAT_CASES_INCOMPLETE`
6. DB migration 合同缺失：`PLAN_DB_MIGRATION_CONTRACT_MISSING`

## 执行流程（强制顺序）

### 0) 上下文检查

至少检查：

1. `requirements.md` 与 `design.md` 是否同主题；
2. 设计中的 `change_map` 与 `shrink_contract` 是否可被拆成任务；
3. 是否存在同主题旧计划需原位更新；
4. 命中 DB 变化时，迁移步骤是否可被拆成独立任务与证据。

### 1) 输出 `implementation_plan.md`

至少包含：

1. `execution_strategy`
2. `task_breakdown`
3. `task_dependencies`
4. `acceptance_cmds`
5. `risk_and_rollback`
6. `db_migration_plan`
7. `done_criteria`

`task_breakdown[*]` 必填：

1. `task_id`
2. `goal`
3. `file_paths`
4. `symbols`
5. `depends_on`
6. `change_type`
7. `acceptance_cmds`
8. `rollback_point`
9. `risk_tags`
10. `mandatory_evidence`
11. `db_migration_cmds`

强约束：

1. 每个 `task_id` 都要能回溯到需求和设计；
2. 命中 `obsolete_paths` 的任务必须显式写删除或收口动作；
3. `acceptance_cmds[*]` 必须是对象，至少包含 `kind/cmd`；
4. `mandatory_evidence` 不能为空；
5. 命中 `db_migration_required=true` 时，必须新增专属 migration task；
6. 开发态默认 migration task 必须包含 `bash scripts/db/run_dev_migration.sh`；
7. 若 `release_migration_required=true`，还必须补 Alembic 任务，至少包含 `bash scripts/db/run_release_migration.sh --message "<message>"`。

### 2) 输出 `uat_cases.md`

至少包含：

1. `case_id`
2. `requirement_ids`
3. `user_role`
4. `preconditions`
5. `steps`
6. `expected_results`
7. `evidence_type`
8. `blocking_level`

强约束：

1. 每条 `functional_requirements` 至少对应一条 UAT；
2. `steps` 必须是用户可执行步骤，而不是代码实现步骤；
3. `expected_results` 必须可验证；
4. 不允许把“后续临场确认”当成默认 UAT 策略；
5. 命中 DB 变化时，UAT 前置条件必须写明迁移已执行。

### 3) 对齐实现与验收合同

必须明确：

1. 哪些 `acceptance_cmds` 对应自动验证；
2. 哪些 `uat_cases` 对应人工/UAT 验收；
3. 哪些需求由命令证据覆盖，哪些需求由 UAT 覆盖；
4. API 文档是否需要自动同步；
5. DB migration 由 `bash scripts/db/run_dev_migration.sh`、`bash scripts/db/run_release_migration.sh --message "<message>"` 还是两者组合完成。

## 输出要求（强制）

至少输出：

1. `implementation_plan.md` 路径；
2. `uat_cases.md` 路径；
3. 任务数与依赖摘要；
4. UAT 覆盖摘要；
5. `db_migration_required` / `release_migration_required` 状态；
6. `api_doc_required` 状态；
7. 下一步建议（仅限 `/jjk-imp` 或 `/jjk-vkplan`）。

## 禁止项（强制）

1. 禁止继续产出 `requirements.md`；
2. 禁止在计划阶段新增架构决策；
3. 禁止让 `/jjk-verify` 临场发明 UAT；
4. 禁止缺少 `uat_cases.md` 就进入 `/jjk-imp`；
5. 禁止把实现步骤伪装成 UAT。

## 推荐链路

`/jjk-clarify -> /jjk-design -> /jjk-plan -> /jjk-imp -> /jjk-verify`

## 使用示例

```text
/jjk-plan
```

---
*使用 `/jjk-plan` 触发。目标是“生成施工单与验收单”，不是“继续补需求或改方案”。*
