---
description: 全流程开发入口（澄清->规划->实现->审查->验证）：单命令编排，禁止跳阶段
---

> 参考规则: @dual-database

# 全特性开发 (Feature Development)

`/jjk-feature` 是 `jjk-*` 的总线入口，负责把“想法”编排成“已验证交付”。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 与 Superpowers / OMX 的分工（强制）

1. `brainstorming`：负责澄清与设计审批。
2. `writing-plans`：负责细粒度计划方法。
3. `test-driven-development`：负责实现阶段先测后改。
4. `verification-before-completion`：负责完成前证据校验。
5. `team`（OMX）：负责大任务并行执行。
6. `/jjk-feature`：负责阶段编排、产物衔接、门禁判定与交接口径。

约束：

1. 禁止在 `/jjk-feature` 复制上述 skills 的完整正文。
2. 插件可用时优先调用；不可用时必须显式 fallback，不得静默降级。
3. `/jjk-feature` 不是“绕过 `/jjk-clarify` 和 `/jjk-plan` 的快捷入口”，而是“按顺序串联它们”的编排入口。

## 跨 IDE 调用方式

1. Cursor / Claude Code：`/jjk-feature`
2. Codex：`/prompts:jjk-feature`

> 说明：Codex 的自定义命令入口是 `/prompts:<name>`，不是 `/<name>`。

## 模板来源优先级（跨项目，强制）

`/jjk-feature` 的模板按以下优先级读取：

1. 全局共享模板（默认主模板）：
   `/Users/jijingkun/.codex/engineering/templates/jjk_feature_templates.md`
2. 项目覆盖模板（仅放差异，不放全量复制）：
   `docs/内部参考/迭代需求/_templates/jjk_feature_templates.md`

若全局模板缺失，输出标记 `GLOBAL_TEMPLATE_MISSING` 并提示先初始化共享模板目录。

## 何时使用

| 场景 | 推荐命令 |
|---|---|
| 从需求到交付的一站式执行 | `/jjk-feature` ✅ |
| 只做澄清与方案对比 | `/jjk-clarify` |
| 只做规划（WHAT+工单级 HOW） | `/jjk-plan` |
| 已有计划，直接实现 | `/jjk-imp` |

---

## 执行流程（强制顺序）

### 0) 先探索项目上下文（强制）

至少检查：

1. 相关历史设计/计划文档与当前变更。
2. 相关模块调用链、测试入口、文档索引状态。
3. 是否存在已有同主题产物（避免重复建档）。

### 0.5) 大任务自动启用 Team（强制判定）

当满足任一条件时，`/jjk-feature` 自动升级 Team 编排模式：

1. 预期改动 `>= 10` 文件；
2. 同时跨后端/前端/AI-workflow/数据库两类以上边界；
3. 涉及 `>= 2` 个里程碑阶段（如重构 + 迁移 + 验证）；
4. 预计需多 worktree 并行推进。

执行策略：

1. **有 Team 能力时**：按阶段并行分配子任务，Leader 汇总单一交付结论。
2. **无 Team 能力时**：降级单代理执行，并输出 `TEAM_UNAVAILABLE_FALLBACK`。

### 1) 澄清与设计阶段（必须）

1. 先执行 `/jjk-clarify` 的契约，确保有 design 文档：
   `docs/plans/YYYY-MM-DD-<topic>-design.md`
2. design 必须包含审批记录：
   - `design_approved: true`
   - `approved_at`
   - `approved_round`
3. 缺失审批记录时，输出 `FEATURE_NEEDS_CLARIFY`，不得进入后续阶段。

### 2) 规划阶段（必须）

1. 执行 `/jjk-plan` 契约，产出：
   - `docs/内部参考/迭代需求/<topic>_requirements.md`（WHAT）
   - `docs/内部参考/迭代需求/<topic>_implementation_plan.md`（工单级 HOW）
2. `implementation_plan` 必须具备：
   - `feature_id -> task_id` 映射
   - `implementation_tasks`（含 `file_paths/symbols/acceptance_cmds`）
   - `implementation_readiness`
3. 若 `implementation_ready=false`，输出 `FEATURE_NEEDS_PLAN_REFINEMENT`，不得进入实现。

### 3) 实现阶段（必须）

1. 执行 `/jjk-imp` 契约，按 `task_id` 粒度落地。
2. 过程中若发现计划缺口，标记 `FEATURE_PLAN_DRIFT_DETECTED`，回退 `/jjk-plan` 修订。
3. 禁止绕过计划直接修改需求语义。

### 4) 审查阶段（条件触发）

满足任一条件时，必须执行 `/jjk-review`：

1. 改动文件 `>= 5`；
2. 涉及跨模块/跨层边界；
3. 涉及公共契约字段变更。

未命中触发条件时可跳过，但必须在交付摘要说明原因。

### 5) 验证阶段（必须）

1. 必须执行 `/jjk-verify`（或等价命令链）并给出命令证据。
2. 若可用 `verification-before-completion`，必须遵循其证据优先原则。
3. 未有新鲜验证证据时，禁止宣称“完成”。

### 6) 交付产物（强制）

必须输出交付摘要：

`docs/内部参考/迭代需求/<topic>_feature_delivery.md`

最小内容：

1. 本轮阶段执行轨迹（clarify -> plan -> imp -> review -> verify）
2. 关键产物路径清单（design/requirements/implementation/delivery）
3. 关键验证命令与结果
4. 未完成项与后续建议命令

建议结构见全局模板：`/Users/jijingkun/.codex/engineering/templates/jjk_feature_templates.md`。  
若本项目有覆盖规则，再查：`docs/内部参考/迭代需求/_templates/jjk_feature_templates.md`。

---

## 禁止项（强制）

1. 禁止跳过 `/jjk-clarify` 直接实施新需求。
2. 禁止在 `implementation_ready=false` 时进入编码。
3. 禁止无验证证据宣称完成。
4. 禁止只改代码不回填文档（命中文档同步规则时）。

---

*使用 `/jjk-feature` 触发。目标是“有节奏的阶段编排交付”，不是“一条命令自由发挥”。*
