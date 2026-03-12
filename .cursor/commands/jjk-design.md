---
description: 技术方案入口：消费 requirements 产出 design 与 shrink contract；可选 --doc 发布正式设计文档
---

# 技术方案工作流（Technical Design）

`/jjk-design` 负责把已审批需求转成**技术方案**，并明确新代码职责、架构调整方式，以及哪些旧路径会因此废弃。

> **中文主导**：思考与输出统一中文。
>
> **唯一目标**：回答“系统怎么改、旧代码怎么收口”。

## 产物与边界

必须产出：

1. `docs/plans/YYYY-MM-DD-<topic>-design.md`

可选发布（仅显式 `--doc` 时）：

2. 对应正式设计/架构文档章节

本命令不做：

1. 不重写需求；
2. 不做详细任务拆解；
3. 不写完整 UAT 用例；
4. 不直接改业务代码。

## 参数

1. `--doc`：在生成内部 `design.md` 的同时，发布到正式设计/架构文档；
2. `--refactor`：显式声明本次以结构收敛为优先；
3. `--patch`：仅限局部非结构性问题；若形成新旧双轨，必须升级为 `refactor`。

约束：

1. 不带 `--doc` 时，内部 `design.md` 仍必须生成；
2. `--doc` 只控制“是否发布正式设计文档”，不控制“是否生成方案产物”。

## 输入前置（强制）

1. 已审批的 `requirements.md`；
2. 明确的主题与范围；
3. 若是 bugfix/refactor，必须给出待收敛旧路径线索。

失败时：

1. 缺少已审批需求：`DESIGN_REQUIREMENTS_REQUIRED`
2. 边界不清：`DESIGN_BOUNDARY_UNCLEAR`
3. 缺少 shrink contract：`DESIGN_SHRINK_CONTRACT_MISSING`
4. 试图跳过方案直接写实施计划：`DESIGN_STAGE_SKIPPED`

## 执行流程（强制顺序）

### 0) 上下文检查

至少检查：

1. 需求是否已审批；
2. 当前变更是否命中 API / Schema / DB / Config / 架构边界；
3. 现有实现里哪些路径可能被新方案替代；
4. 若命中表结构/索引/约束变化，DB migration 应采用 `run_dev_migration.sh` 还是 Alembic 版本化。

### 1) 输出四段式架构结论

必须按以下顺序输出：

1. `module_boundaries`
2. `dependency_direction`
3. `state_ownership`
4. `error_handling`

每一段都必须包含：

1. 当前问题；
2. 最终决策；
3. 禁止动作。

### 2) 输出 Change Map

`design.md` 必须显式列出：

1. `new_paths`：准备新增哪些代码/模块，各自作用是什么；
2. `modified_paths`：哪些现有路径会被调整，调整目的是什么；
3. `replaced_responsibilities`：哪些旧职责会被新实现覆盖。

### 3) 冻结 DB Migration Contract

命中 DB / Schema / 索引 / 约束变化时，必须输出：

1. `db_migration_required=true|false`
2. `db_change_scope`
3. `db_migration_mode=sync_database_only|alembic_versioned`
4. `release_migration_required=true|false`
5. `db_rollback_strategy`

强约束：

1. 开发态默认优先 `run_dev_migration.sh`；
2. 若该变更需要进入可回滚、可审计的发布链路，必须同时标记 `release_migration_required=true`，并在计划阶段补 Alembic 任务；
3. 禁止命中 DB 结构变化却不声明 migration 策略。

### 4) 冻结 Shrink Contract

必须输出：

1. `obsolete_paths`
2. `retained_paths`
3. `single_entry_owner`
4. `line_budget`

强约束：

1. `obsolete_paths` 为空时必须写 `none` 与原因；
2. `retained_paths` 必须给唯一保留理由；
3. 新实现若覆盖旧职责但旧路径仍残留且无理由，直接失败；
4. 默认 `line_budget=added<=deleted`；若不能满足，必须说明架构必要性。

### 5) 文档发布与 API 同步提示

1. 若命中 API 变化，必须标记 `api_doc_required=true`，后续进入 `/jjk-api-doc-sync`；
2. 仅当显式 `--doc` 时，`publish_design_doc=true`；
3. 不带 `--doc` 时，禁止修改正式设计/架构文档。

## 输出要求（强制）

至少输出：

1. 四段式架构结论；
2. `change_map` 摘要；
3. `db_migration_contract`；
4. `shrink_contract`；
5. `publish_design_doc` 状态；
6. `api_doc_required` 状态；
7. 下一步建议（仅限 `/jjk-plan` 或 `/jjk-api-doc-sync` 组合）。

## 禁止项（强制）

1. 禁止把需求澄清混回方案阶段；
2. 禁止省略 `obsolete_paths` / `retained_paths` / `single_entry_owner`；
3. 禁止用 fallback、兼容层、双轨路径掩盖结构问题；
4. 禁止在未出方案前进入 `/jjk-plan`；
5. 禁止把正式设计文档发布与内部 `design.md` 二选一。

## 推荐链路

`/jjk-clarify -> /jjk-design -> /jjk-plan`

`/jjk-design -> /jjk-api-doc-sync`（命中 API 变化时）

## 使用示例

```text
/jjk-design
```

```text
/jjk-design --doc
```

```text
/jjk-design --refactor
```

---
*使用 `/jjk-design` 触发。目标是“冻结技术方案与收口合同”，不是“边想边写代码”。*
