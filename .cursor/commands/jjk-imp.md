---
description: 代码实现入口（结合 TDD + 完成前校验）：按计划执行代码改动与文档回填
---

> 参考规则: @dual-database

# 实现工作流 (Implementation Workflow)

`/jjk-imp` 是 `jjk-*` 体系里的实现入口，负责把已确认计划落到代码与测试。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 与 Superpowers / OMX 的分工（强制）

1. `test-driven-development`：负责“先测后改”方法。
2. `verification-before-completion`：负责“声称完成前必须有命令证据”。
3. `systematic-debugging`：仅在实现过程中出现异常时用于定位根因。
4. `team`（OMX）：大任务并行执行与证据汇总。
5. `/jjk-imp`：负责输入契约校验、任务落地顺序、文档回填、交接口径。

约束：

1. 禁止在 `/jjk-imp` 复制上述技能的完整正文。
2. 插件可用时优先调用；插件不可用时必须显式 fallback，不得静默降级。
3. `/jjk-imp` 必须消费 `jjk-plan` 或 `jjk-pc` 产物，禁止脱离计划自由发挥。

## 跨 IDE 调用方式

1. Cursor / Claude Code：`/jjk-imp`
2. Codex：`/prompts:jjk-imp`

> 说明：Codex 的自定义命令入口是 `/prompts:<name>`，不是 `/<name>`。

## 模板来源优先级（跨项目，强制）

`/jjk-imp` 的模板按以下优先级读取：

1. 全局共享模板（默认主模板）：
   `/Users/jijingkun/.codex/engineering/templates/jjk_imp_templates.md`
2. 项目覆盖模板（仅放差异，不放全量复制）：
   `docs/内部参考/迭代需求/_templates/jjk_imp_templates.md`

若全局模板缺失，输出标记 `GLOBAL_TEMPLATE_MISSING` 并提示先初始化共享模板目录。

## 何时使用

| 场景 | 推荐命令 |
|---|---|
| 已有可执行 implementation plan，开始编码 | `/jjk-imp` ✅ |
| 并行 WS 已拆解，执行单个子任务 | `/jjk-imp-ws` |
| 诊断后按修复计划落地 | `/jjk-pc` -> `/jjk-imp` ✅ |
| 尚未形成可执行 HOW | `/jjk-plan` |

---

## 执行流程（精简）

### 0) 先探索项目上下文（强制）

至少检查：

1. 相关计划文档与任务映射（`feature_id/task_id/card_id`）。
2. 当前工作区变更（`git status`）与上下游依赖文件。
3. 相关测试入口与回归范围。

### 0.5) 大任务自动启用 Team（强制判定）

`/jjk-team-imp` 不再作为主入口。
统一由 `/jjk-imp` 在大任务时自动升级 Team 执行模式。

触发条件（满足任一即可）：

1. 预期改动 `>= 8` 个文件；
2. 同时跨后端/前端/AI-workflow/数据库中的两类以上边界；
3. 待执行任务 `task_id` 数量 `>= 6`；
4. 预计需要并行 worktree 才能按期完成。

执行策略：

1. **有 Team 能力时**：按任务分片并行执行，Leader 汇总统一交付与证据。
2. **无 Team 能力时**：降级为单代理执行，并在输出标记 `TEAM_UNAVAILABLE_FALLBACK`。

### 1) 输入契约校验（强制）

按优先级读取输入：

1. `docs/内部参考/迭代需求/<topic>_implementation_plan.md`（首选）
2. `docs/内部参考/迭代需求/fix_plan_<topic>.md`
3. `docs/内部参考/迭代需求/<topic>_requirements.md`（仅兜底，不建议直接开工）

硬规则：

1. 若 `implementation_plan` 存在 `implementation_readiness` 且 `implementation_ready=false`，必须输出 `IMPLEMENTATION_NOT_READY` 并回退 `/jjk-plan`。
2. 若缺少工单级拆解（如 `task_id/file_paths/symbols/acceptance_cmds`），必须输出 `IMP_INPUT_TOO_COARSE` 并回退 `/jjk-plan`。
3. 仅有 `requirements` 而无可执行 HOW 时，不得直接进入编码。

### 2) 任务级执行（强制）

每次只执行明确任务单元（`task_id` 或 `feature_id`），并记录：

1. 目标文件（`file_paths`）
2. 代码锚点（`symbols`）
3. 改动类型（`change_type`）
4. 验收命令（`acceptance_cmds`）
5. 回滚点（`rollback_point`）

禁止项：

1. 禁止跨任务“顺手改”未授权范围。
2. 禁止跳过失败任务继续宣称“整体完成”。

### 3) 测试与验证策略（强制）

1. 能用 `test-driven-development` 时优先先写失败测试再改实现。
2. 若 TDD 技能不可用，输出 `TDD_UNAVAILABLE_FALLBACK`，但仍需先补最小回归测试。
3. 完成前必须执行计划中的 `acceptance_cmds`。
4. 能用 `verification-before-completion` 时必须执行；不可用时输出 `VERIFY_BEFORE_COMPLETION_UNAVAILABLE_FALLBACK` 并手工附命令结果证据。

### 4) 文档同步闭环（强制）

涉及以下变更时，必须同步文档：

1. API 变更 -> `docs/API文档/接口文档.md`
2. 表结构变更 -> `docs/开发文档/架构设计/数据库设计.md`
3. 配置变更 -> `docs/开发文档/快速入门/配置说明.md` + `.env.example`
4. 测试行为变更 -> `docs/开发文档/测试管理/测试用例库.md`

### 5) 交接输出（强制）

最终必须给出：

1. 已完成任务清单（`task_id -> 文件 -> 验收命令 -> 结果`）
2. 未完成/阻塞项（含原因与下一步）
3. 风险与回滚建议
4. 建议下一命令（`/jjk-verify` 或 `/jjk-review`）

---

## 禁止项（强制）

1. 禁止在输入不完整时直接编码。
2. 禁止跳过验收命令直接报告“完成”。
3. 禁止修改需求语义或计划目标。
4. 禁止只改代码不回填文档（当变更类型命中同步规则时）。

---

*使用 `/jjk-imp` 触发。目标是“按计划可追溯实施”，而不是自由编码。*
