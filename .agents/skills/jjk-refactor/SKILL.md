---
name: jjk-refactor
description: "Use when you need `jjk-refactor` in this repository. Source intent: 重构入口：消费 design 或 review 结论，按 shrink contract 做行为等价重构并回填证据"
---
<!-- AUTO-GENERATED: jjk-skill-mirror -->
<!-- source: .cursor/commands/jjk-refactor.md -->

# 重构工作流（Refactor Workflow）

`$jjk-refactor` 负责在**需求不变**前提下完成结构治理，核心是按既有方案收口旧路径，而不是继续叠加兼容层。

> **中文主导**：思考与输出统一中文。
>
> **唯一目标**：结构升级且行为等价。

## 输入前置（强制）

至少提供以下输入之一：

1. 已审批的 `design.md`（推荐）；
2. `review_report` 中的结构性问题；
3. 明确的 `shrink_contract`。

若命中业务行为路径，还必须可回溯到：

1. `requirements.md`
2. `uat_cases.md`
3. 基线测试或可执行断言

失败时：

1. 缺少设计或 shrink contract：`REFACTOR_SHRINK_CONTRACT_MISSING`
2. 缺少行为基线：`REFACTOR_BASELINE_MISSING`
3. 试图引入新需求：`REFACTOR_SCOPE_EXPANDED`
4. 命中 DB 变化却缺少 migration 合同：`REFACTOR_DB_MIGRATION_CONTRACT_MISSING`

## 执行流程（强制顺序）

### 0) 锁定行为边界

至少明确：

1. 哪些需求行为必须保持不变；
2. 哪些异常语义必须保持不变；
3. 哪些 `uat_cases` 作为最终验收基线。

### 1) 冻结收口合同

必须复核：

1. `obsolete_paths`
2. `retained_paths`
3. `single_entry_owner`
4. `line_budget`

默认规则：

1. 新实现覆盖旧职责时，旧路径必须删或给唯一保留理由；
2. 若继续净增长，必须解释架构必要性；
3. 禁止新增双写入口或兼容层掩盖问题。

### 2) 小步实施重构

1. 每次只处理一个收口切片；
2. 每个切片完成后立即执行对应 `acceptance_cmds`；
3. 若命中 DB 结构变化，重构链也必须走 `db_migration_contract`；
4. 开发态默认自动执行 `run_dev_migration.sh`，发布态再补 Alembic 任务。

### 3) 结果验证

必须回填：

1. `obsolete_paths` 命中结果；
2. `retained_paths` 保留理由；
3. `single_entry_owner` 收敛结果；
4. 相关测试与 UAT 基线证据；
5. DB migration 证据（命中时）。

### 4) 报告输出

产出：

1. `refactor_report_<topic>.md`
2. 删除清单 / 收口清单
3. 复杂度或路径收敛变化
4. 风险与回滚点

## 输出要求（强制）

至少输出：

1. 重构范围；
2. 行为基线；
3. shrink contract 执行结果；
4. DB migration 状态（命中时）；
5. 验证结果；
6. 下一步建议（`$jjk-review`、`$jjk-verify`）。

## 禁止项（强制）

1. 禁止无基线就宣称行为等价；
2. 禁止在重构阶段引入新需求；
3. 禁止保留已废弃路径且不给理由；
4. 禁止命中 DB 变化却不回填 migration 证据。

## 推荐链路

`$jjk-review -> $jjk-refactor -> $jjk-review -> $jjk-verify`

---
*使用 `$jjk-refactor` 触发。目标是“收口旧职责并保持行为不变”，不是“换种写法继续长胖”。*
