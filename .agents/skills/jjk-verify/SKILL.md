---
name: jjk-verify
description: "Use when you need `jjk-verify` in this repository. Source intent: 验收入口：消费 requirements、design、implementation_plan、uat_cases 与证据，给出最终判定"
---
<!-- AUTO-GENERATED: jjk-skill-mirror -->
<!-- source: .cursor/commands/jjk-verify.md -->

# 组合验收工作流（Verify Workflow）

`$jjk-verify` 负责基于已冻结的需求、方案、计划和证据，给出最终可执行判定（`PASS|WARN|FAIL`）。

> **中文主导**：思考与输出统一中文。
>
> **唯一目标**：判卷，不出题。

## 输入前置（强制）

1. `docs/内部参考/迭代需求/<topic>_requirements.md`
2. `docs/plans/YYYY-MM-DD-<topic>-design.md`
3. `docs/内部参考/迭代需求/<topic>_implementation_plan.md`
4. `docs/内部参考/迭代需求/<topic>_uat_cases.md`
5. 实现阶段产出的命令证据、测试证据、文档同步证据

失败时：

1. 缺少需求真理源：`VERIFY_REQUIREMENTS_MISSING`
2. 缺少方案真理源：`VERIFY_DESIGN_MISSING`
3. 缺少计划真理源：`VERIFY_PLAN_MISSING`
4. 缺少 UAT 真理源：`VERIFY_UAT_CASES_MISSING`
5. 缺少可复核证据：`VERIFY_EVIDENCE_MISSING`
6. 试图临场发明 UAT：`VERIFY_UAT_STAGE_OWNERSHIP_VIOLATION`

## 执行硬约束（强制）

1. 先做期望上下文比对；
2. 验收只消费既有 `uat_cases`，不临场新建 UAT；
3. 仅当 `uat_cases` 明确标记需要人工确认时，才允许进入交互确认；
4. 命中 DB migration 时，迁移证据必须纳入验收；
5. API 文档同步状态必须纳入验收；
6. 正式产品/设计文档是否发布，只按 `publish_product_doc` / `publish_design_doc` 判定。

## 执行流程（强制顺序）

### 0) 上下文校验

至少输出并比对：

1. 目标上下文：`task_id/pr_id/branch/worktree/SHA`（能拿到什么就写什么）；
2. 实际上下文：`pwd`、`git rev-parse --show-toplevel`、`git branch --show-current`、`git rev-parse HEAD`；
3. 结论：`PASS|FAIL`；
4. 阻断或放行原因。

### 1) Requirement Coverage

1. 对照 `functional_requirements` 检查覆盖情况；
2. 标记每条需求的 `pass|warn|fail`；
3. 若存在未覆盖需求，直接失败。

### 2) Design Conformance

至少检查：

1. `module_boundaries`
2. `dependency_direction`
3. `state_ownership`
4. `error_handling`
5. `shrink_contract`
6. `db_migration_contract`

强约束：

1. `obsolete_paths` 未执行且无理由，直接失败；
2. `retained_paths` 无唯一保留理由，直接失败；
3. 命中 `db_migration_required=true` 却无迁移证据，直接失败。

### 3) Acceptance Commands

1. 执行或复核 `acceptance_cmds` 结果；
2. 汇总 `exit_code`、结果摘要与证据；
3. `mandatory_evidence` 缺失，直接失败。

### 4) DB Migration Evidence

1. 命中 `db_migration_required=true` 时，必须复核 `db_migration_evidence`；
2. 开发态至少要有 `run_dev_migration.sh` 执行证据；
3. 若 `release_migration_required=true`，还必须有 Alembic migration 文件与 `bash scripts/db/run_release_migration.sh --upgrade-only` 证据；
4. 迁移证据缺失时，输出 `VERIFY_DB_MIGRATION_UNPROVEN`。

### 5) UAT Cases

1. 逐条消费 `uat_cases.md`；
2. 每条 UAT 至少回填：`case_id/result/evidence/notes`；
3. 若某条 UAT 需要人工确认，必须基于该用例既有字段确认，不得现场扩写新的验收规则。

### 6) 文档同步状态

1. 命中 API 变化时，API 文档必须已同步；
2. 若 `publish_product_doc=true`，正式产品/需求文档必须已发布；
3. 若 `publish_design_doc=true`，正式设计/架构文档必须已发布；
4. 未发布但也未要求发布，不算失败。

### 7) 报告输出与结论

结论规则：

1. `PASS`：需求覆盖完整 + 方案收敛完成 + 命令证据通过 + DB migration 证据完整（命中时）+ UAT 通过 + 文档状态一致；
2. `WARN`：仅允许非阻断性残余风险；
3. `FAIL`：任一需求/UAT/收口合同/mandatory evidence/DB migration/API 文档同步失败。

必须输出：

1. `verify_report.md` 路径；
2. 总结（`PASS|WARN|FAIL`）；
3. requirement coverage；
4. design conformance；
5. acceptance command 结果；
6. DB migration 结果；
7. UAT 结果；
8. 文档同步状态；
9. 下一步建议（`merge|fix|replan`）。

## 禁止项（强制）

1. 禁止把 `$jjk-verify` 变成“补需求/补方案/补 UAT”的阶段；
2. 禁止没有 `uat_cases` 就做验收结论；
3. 禁止用“测试都过了”代替需求和 UAT 覆盖；
4. 禁止忽略 DB migration 证据；
5. 禁止忽略 API 文档同步状态；
6. 禁止把未要求发布的正式文档缺失误判为失败，也禁止把要求发布却未发布放过。

## 推荐链路

`$jjk-imp -> $jjk-verify -> 合并/修复/回退`

## 使用示例

```text
$jjk-verify
```

---
*使用 `$jjk-verify` 触发。目标是“按既有合同判定”，不是“现场补合同”。*
