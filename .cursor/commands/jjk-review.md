---
description: 审查入口：消费 requirements、design、implementation_plan、uat_cases 与实现证据，输出结构化审查结论
---

# 代码审查工作流（Code Review）

`/jjk-review` 负责把实现结果转成**可执行的审查结论**，重点检查“需求是否实现、方案是否遵守、收口是否完整”。

> **中文主导**：思考与输出统一中文。
>
> **唯一目标**：发现阻断风险，不替代 `/jjk-verify` 做最终验收。

## 输入前置（强制）

至少提供以下审查对象之一：

1. 当前分支相对 `main/master` 的 diff；
2. `pr_id` / PR 链接；
3. `pr_ready_manifest` / `pr_ready_manifest_ws`。

并且必须可回溯到：

1. `requirements.md`
2. `design.md`
3. `implementation_plan.md`
4. `uat_cases.md`
5. 实现证据（`acceptance_cmds`、测试结果、文档同步结果、必要时 `db_migration_evidence`）

失败时：

1. 缺少审查对象：`REVIEW_INPUT_INCOMPLETE`
2. 缺少真理源映射：`REVIEW_TRACEABILITY_MISSING`
3. 缺少实现证据：`REVIEW_EVIDENCE_MISSING`
4. 缺少测试质量判定：`REVIEW_TEST_QUALITY_UNPROVEN`

## 执行流程（强制顺序）

### 0) 审查范围锁定

至少检查：

1. 当前改动映射到哪些 `task_id`；
2. 变更是否落在既有 `requirements/design/plan` 范围内；
3. 哪些文件属于本轮改动，哪些属于历史债务。

### 1) 三层一致性审查

1. **需求一致性**：是否完整覆盖 `functional_requirements`；
2. **方案一致性**：是否遵守 `module_boundaries/dependency_direction/state_ownership/error_handling`；
3. **计划一致性**：是否按 `implementation_plan` 执行，而不是临时漂移。

### 2) 收口与瘦身审查

至少检查：

1. `obsolete_paths` 是否被删除或收口；
2. `retained_paths` 是否有唯一保留理由；
3. `single_entry_owner` 是否真正收敛；
4. `line_budget` 是否满足，若不满足是否有明确必要性。

### 3) DB Migration 与文档审查

1. 命中 `db_migration_required=true` 时，检查 `db_migration_evidence`；
2. 开发态默认应有 `run_dev_migration.sh` 证据；
3. 若 `release_migration_required=true`，应有 Alembic 迁移脚本与 `bash scripts/db/run_release_migration.sh --upgrade-only` 证据；
4. 命中 API 变化时，API 文档必须同步；
5. 正式产品/设计文档只按 `publish_product_doc/publish_design_doc` 审查。

### 4) 测试质量评分卡

若命中测试变更、关键 bugfix 或关键链路，必须按 `.cursor/rules/test_quality.mdc` 打分：

1. `风险覆盖`
2. `失败模式覆盖`
3. `断言质量`
4. `脆弱性`
5. `可维护性`

默认规则：

1. 任一维度 `0`：`BLOCKED`
2. 总分 `< 7`：至少 `CONDITIONAL_PASS`

### 5) 输出发现与结论

发现项分级：

- `P0`：阻断
- `P1`：高优先
- `P2`：中优先
- `P3`：建议优化

结论类型：

1. `PASS`：可进入 `/jjk-verify`
2. `CONDITIONAL_PASS`：存在非阻断项，但可继续验收
3. `BLOCKED`：存在阻断项，必须先修复

## 输出要求（强制）

至少输出：

1. `review_report_<topic>.md` 路径；
2. 审查范围；
3. requirement/design/plan 一致性结论；
4. shrink contract 结论；
5. DB migration / API 文档 / 发布文档状态；
6. 测试质量评分卡；
7. `PASS|CONDITIONAL_PASS|BLOCKED`；
8. 下一步建议（`/jjk-verify`、`/jjk-imp`、`/jjk-refactor`、`/jjk-debug`）。

## 禁止项（强制）

1. 禁止把 `/jjk-review` 变成最终验收；
2. 禁止忽略 `design.md` 与 `uat_cases.md`；
3. 禁止无证据凭感觉通过；
4. 禁止把历史债务全部算作本次阻断；
5. 禁止忽略 DB migration 与 API 文档同步状态。

## 推荐链路

`/jjk-imp | /jjk-imp-ws | /jjk-wtimp -> /jjk-review -> /jjk-verify`

---
*使用 `/jjk-review` 触发。目标是“做结构化审查”，不是“替验收阶段判卷”。*
