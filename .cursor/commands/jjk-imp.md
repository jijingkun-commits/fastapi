---
description: 代码实现入口：严格消费 implementation_plan 与 uat_cases，执行实现、验证与文档回填
---

# 实现工作流（Implementation Workflow）

`/jjk-imp` 负责把已审批的需求、方案与计划落到代码、测试和文档证据。

> **中文主导**：思考与输出统一中文。

## 输入前置（强制）

1. `docs/内部参考/迭代需求/<topic>_requirements.md`
2. `docs/plans/YYYY-MM-DD-<topic>-design.md`
3. `docs/内部参考/迭代需求/<topic>_implementation_plan.md`
4. `docs/内部参考/迭代需求/<topic>_uat_cases.md`

失败时：

1. 缺少计划：`IMP_PLAN_REQUIRED`
2. 缺少 UAT：`IMP_UAT_CASES_REQUIRED`
3. 缺少 shrink contract：`IMP_SHRINK_CONTRACT_MISSING`
4. 工单字段不全：`IMP_INPUT_TOO_COARSE`

## 执行流程（四步）

### 0) 上下文校验

至少检查：

1. 当前任务对应哪些 `task_id`；
2. 相关 `acceptance_cmds` 与最小回归范围；
3. 是否命中 API 文档自动同步；
4. 是否命中 `db_migration_required=true`。

### 1) 按 `implementation_plan` 执行任务

1. 每次只实现当前 `task_id` 声明的职责；
2. 命中 `obsolete_paths` 时，必须同步执行删除或收口；
3. 若发现设计漂移，输出 `IMP_PLAN_DRIFT_DETECTED`，回退 `/jjk-design` 或 `/jjk-plan`；
4. 禁止在实现阶段私自改需求或改技术方案。

### 1.5) 自动执行 DB Migration（命中时强制）

1. 当 `db_migration_required=true` 时，必须自动解析仓库 Python：`PYTHON_BIN=$(bash scripts/repo_python.sh)`；
2. 开发态默认执行：`bash scripts/db/run_dev_migration.sh`；
3. 若 `release_migration_required=true`，还必须自动生成 Alembic 迁移草稿并复核，再执行 `bash scripts/db/run_release_migration.sh --upgrade-only`；
4. 必须把迁移文件路径、执行命令、退出码和摘要一并回填证据；
5. 命中 DB 结构变化却未执行 migration，直接失败：`IMP_DB_MIGRATION_MISSING`。

### 2) 测试与验证

1. 必须执行当前任务对应的 `acceptance_cmds`；
2. 必须回填 `mandatory_evidence`；
3. 命中 DB migration 时，必须回填 `db_migration_evidence`；
4. 可用时执行 `verification-before-completion`；
5. 无新鲜命令证据，不得宣称完成。

### 3) 文档回填与同步

1. 命中 API 变化时，API 文档必须自动同步；
2. 仅当 `publish_product_doc=true` 时，才回填正式产品/需求文档；
3. 仅当 `publish_design_doc=true` 时，才回填正式设计/架构文档；
4. 测试行为变化时，回填测试资产。

### 4) 交接给 `/jjk-verify`

至少交付：

1. 改动文件清单；
2. `acceptance_cmds` 结果；
3. `mandatory_evidence`；
4. 文档同步状态；
5. `obsolete_paths` 执行结果；
6. `db_migration_evidence`。

## 禁止项（强制）

1. 禁止跳过 `acceptance_cmds`；
2. 禁止缺少 `uat_cases` 就宣称“可验收”；
3. 禁止命中 API 同步规则却不更新 API 文档；
4. 禁止私自发布正式产品/设计文档；
5. 禁止保留已被新实现覆盖的旧路径且不给理由；
6. 禁止命中 DB 变化却把 migration 留给人工手补。

## 推荐链路

`/jjk-plan -> /jjk-imp -> /jjk-verify`

---
*使用 `/jjk-imp` 触发。目标是“按计划落地并回传证据”，不是“边做边改真理源”。*
