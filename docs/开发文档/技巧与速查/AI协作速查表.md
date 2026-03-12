# AI 协作速查表

## 结论先行

- 主链已经收敛为：`/jjk-clarify -> /jjk-design -> /jjk-plan -> /jjk-imp -> /jjk-review -> /jjk-verify`
- `clarify` 只产出需求，`design` 只产出方案，`plan` 只产出实施计划与 UAT。
- API 文档命中接口变化时始终自动同步；正式产品/设计文档只在 `--doc` 时发布。
- 命中 DB 结构变化时，`imp` 默认自动执行 `bash scripts/db/run_dev_migration.sh`；若进入发布链路，再补 `bash scripts/db/run_release_migration.sh --message "<message>"`。

## 主链速查

```text
新功能：/jjk-clarify -> /jjk-design -> /jjk-plan -> /jjk-imp -> /jjk-review -> /jjk-verify
并行功能：/jjk-clarify -> /jjk-design -> /jjk-plan -> /jjk-vkplan -> /jjk-vktodo -> /jjk-cardrun -> /jjk-review -> /jjk-verify
结构重构：/jjk-review -> /jjk-refactor -> /jjk-review -> /jjk-verify
缺陷修复：/jjk-debug -> /jjk-review -> /jjk-verify
```

## 每个命令干什么

| 阶段 | 命令 | 产物 | 关键点 |
|---|---|---|---|
| 需求 | `/jjk-clarify` | `requirements.md` | 只写做什么；`--doc` 才发布正式产品/需求文档 |
| 方案 | `/jjk-design` | `design.md` | 写四段式架构结论、`change_map`、`db_migration_contract`、`shrink_contract`；`--doc` 才发布正式设计文档 |
| 计划 | `/jjk-plan` | `implementation_plan.md` + `uat_cases.md` | 既要施工单，也要验收单 |
| 实现 | `/jjk-imp` | 代码 + 证据 | DB 变化默认自动跑 `bash scripts/db/run_dev_migration.sh` |
| 审查 | `/jjk-review` | `review_report.md` | 检查需求/方案/计划/收口/迁移是否一致 |
| 验收 | `/jjk-verify` | `verify_report.md` | 只判卷，不临场发明 UAT |

## `--doc` 规则

| 命令 | 不带 `--doc` | 带 `--doc` |
|---|---|---|
| `/jjk-clarify` | 生成内部 `requirements.md` | 额外发布正式产品/需求文档 |
| `/jjk-design` | 生成内部 `design.md` | 额外发布正式设计/架构文档 |

## DB migration 速查

### 开发态默认模板

```bash
bash scripts/db/run_dev_migration.sh
```

### 发布态补充模板

```bash
bash scripts/db/run_release_migration.sh --message "<message>"
```

## Go / No-Go

| 阶段 | GO | NO-GO |
|---|---|---|
| Clarify | `requirements_approved=true` | 需求不清、混入技术实现 |
| Design | 四段式结论 + `shrink_contract` + `db_migration_contract` 完整 | 边界不清、旧路径收口不清 |
| Plan | `implementation_plan.md` + `uat_cases.md` 完整 | 无 UAT、无 migration task（命中 DB 时） |
| Imp | `acceptance_cmds` 与 migration 都有证据 | 边做边改真理源 |
| Verify | 需求/方案/UAT/迁移证据全部对上 | 缺证据、临场补合同 |

## 高频误区

- “`clarify` 顺手把方案也写了” → 错，现在方案归 `/jjk-design`。
- “`plan` 只写 task，不写 UAT” → 错，`plan` 必须把 UAT 写全。
- “DB migration 后面手动补” → 错，命中 DB 变化时，`imp` 默认自动执行。
- “API 文档也要 `--doc` 才更新” → 错，API 文档命中接口变化就自动同步。
