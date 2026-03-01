---
name: jjk-clarify
description: "Use when you need `jjk-clarify` in this repository. Source intent: 澄清入口（结合 brainstorming）：提高提问效率，产出标准 design 文档"
---
<!-- AUTO-GENERATED: jjk-skill-mirror -->
<!-- source: .cursor/commands/jjk-clarify.md -->

# 任务澄清 (Clarify Task)

本命令是你 `jjk-*` 体系里的澄清入口，目标是**复用** `brainstorming`，而不是复制它。

## 执行契约

1. 若当前环境可用 `brainstorming`，**必须先调用并遵循其流程**。
2. 若当前环境不可用 `brainstorming`，按本文件 fallback 流程执行，并在“执行备注”区块标记 `BRAINSTORM_UNAVAILABLE_FALLBACK`。
3. 设计未获用户审批前，禁止进入实现阶段。
4. 标准模式产物统一写入：`docs/plans/YYYY-MM-DD-<topic>-design.md`（轻量模式可不落盘）。
5. 禁止在本文件复制完整 brainstorming 正文，避免双份维护漂移。

## 执行意图门禁（新增，强制）

1. `$jjk-clarify` 默认只做澄清与设计，不自动进入 `$jjk-plan`、`$jjk-imp`、`$jjk-feature` 的执行链。
2. 用户若只回复“好的/继续/确认”但未明确“执行/落地/开始改”，本命令必须停留在澄清态。
3. 仅当用户在当前轮显式表达执行动词时，才允许输出“建议下一步执行命令”。
4. 若执行意图不明确，输出标记 `CLARIFY_EXECUTION_INTENT_REQUIRED`，并给出可选下一步（继续澄清或进入规划）。

## 跨 IDE 调用方式

1. Cursor / Claude Code：`$jjk-clarify`
2. Codex：`$jjk-clarify`

> 说明：Codex 推荐显式调用 `$jjk-clarify`。

---

## 与 brainstorming 的分工

1. `brainstorming`：流程门禁、设计审批、阶段收敛。
2. `jjk-clarify`：提问效率增强（单主题问题包）+ 多 IDE fallback。

---

## 模板来源优先级（跨项目，强制）

`$jjk-clarify` 统一使用仓库内相对路径模板，禁止依赖用户绝对路径。

模板按以下优先级读取：

1. 项目主模板（必需）：
   `docs/内部参考/迭代需求/_templates/jjk_clarify_templates.md`
2. 项目覆盖模板（可选，仅放差异）：
   `docs/内部参考/迭代需求/_templates/jjk_clarify_templates.override.md`

若主模板缺失，使用本命令内置最小模板兜底，并在“执行备注”输出 `TEMPLATE_FILE_MISSING`。

---

## 何时使用

| 场景 | 推荐命令 |
|------|----------|
| 需求模糊，先做高效澄清与方案对比 | `$jjk-clarify` ✅ |
| 需要更细粒度领域深挖 | `$jjk-clarify --deep` ✅ |
| 任务很大，需要并行澄清 | `$jjk-clarify`（自动启用 team） ✅ |
| 需要进入正式需求与技术方案产出 | `$jjk-plan` |

---

## 提问效率增强（单主题问题包）

在不破坏 brainstorming 约束的前提下，采用“**单主题问题包**”：

1. 每轮只聚焦一个主题（满足单主题约束）。
2. 同轮允许最多 3 个结构化子项，用户可一次回复（例如 `A2/B1/C3`）。
3. 默认模式最多 2 轮问题包；超过则建议切 `--deep`。
4. 若还有关键不确定项，再加 1 个精准追问。

模板见项目主模板：`docs/内部参考/迭代需求/_templates/jjk_clarify_templates.md`（`单主题问题包模板` 段）。  
若本项目有覆盖规则，再查：`docs/内部参考/迭代需求/_templates/jjk_clarify_templates.override.md`。

---

## 轻量澄清模式（小任务）

满足以下全部条件时，可走轻量模式（不强制写入 design 文档）：

1. 预计改动 `<= 3` 个文件；
2. 单模块内修改；
3. 不涉及架构/API/表结构/配置变更；
4. 不跨后端/前端/AI-workflow/数据库边界。

轻量模式仍需输出：

1. 目标、范围、成功标准；
2. 至少 2 个方案 + 推荐；
3. 若澄清中发现边界升级，立即切换为标准模式并落盘 design 文档。

---

## 执行流程（精简）

### 0) 先探索项目上下文（强制）

至少检查：

1. 关键代码入口（如 `app/ai/workflow/*`, `app/services/*`, `web/src/*`）
2. 相关文档（如 `docs/**` 与历史计划）
3. 当前变更状态（`git status`）

### 0.5) Team 升级判定（先扫描后决策）

`$jjk-team-clarify` 已废弃，不再作为独立入口。  
统一由 `$jjk-clarify` 在大任务时自动升级为 Team 执行。

完成步骤 0 的上下文扫描后，先输出“Team 判定快照”：

1. `module_count`：涉及模块/子系统数量；
2. `boundary_count`：跨边界数量（后端/前端/AI-workflow/数据库）；
3. `uncertainty_count`：需要并行查证的不确定项数量；
4. `estimated_file_count`：预估改动文件数量。

判定规则：

1. 命中条件：`module_count >= 3`；
2. 命中条件：`boundary_count >= 2`；
3. 命中条件：`uncertainty_count >= 2`；
4. 命中条件：`estimated_file_count >= 8`。

执行阈值：

1. 命中条件 `>= 2` 条：自动升级 Team；
2. 命中条件 `<= 1` 条：默认单代理执行（除非用户明确指定 Team）。

执行策略：

1. **有 Team 能力时**：自动以 team 方式并行收集上下文与方案草稿，Leader 对外保持单线程提问口径。
2. **无 Team 能力时**：降级为单代理执行，并在“执行备注”区块标注 `TEAM_UNAVAILABLE_FALLBACK`。

### 0.6) Team 交叉质检约束（新增，轻量）

1. Team 模式下必须启用抽检互审：至少抽检 `20%` 工作项（向上取整，最少 `1` 项）。
2. 每个抽检项必须包含：`1` 个质疑点、`1` 条验证命令、`1` 个通过/驳回结论。
3. 抽检未通过的工作项不得推进到下一阶段，必须先复核并补齐证据。
4. 阶段汇报至少包含：`结论`、`证据`、`剩余风险`。

### 1) 进行澄清提问

- 默认模式：使用“单主题问题包”做快速对齐。
- Deep 模式：按领域逐个问题包深挖。

### 2) 复述确认

输出“我的理解”，至少包含：

1. 目标
2. 范围
3. 边界条件
4. 成功标准

### 3) 方案对比（强制）

必须给出 2-3 个方案，说明优缺点与成本，并明确推荐方案。

### 4) 设计审批（强制）

按 brainstorming 约束：设计需经用户确认后，才可进入下一阶段。

审批通过后，必须在 design 文档补充“审批记录”：

1. `design_approved: true`
2. `approved_at: <YYYY-MM-DD HH:mm>`
3. `approved_round: <轮次或版本>`

### 5) 产出物（与 brainstorming 名称和路径一致）

标准模式统一写入：

`docs/plans/YYYY-MM-DD-<topic>-design.md`

> 不再使用 `_context.md` 或 `*-clarify.md` 作为主产物。

建议结构见项目主模板：`docs/内部参考/迭代需求/_templates/jjk_clarify_templates.md`（`design 文档结构模板` 段）。  
若本项目有覆盖规则，再查：`docs/内部参考/迭代需求/_templates/jjk_clarify_templates.override.md`。

轻量模式可不落盘，但需在回复内给出简版结论与推荐方案。

### 6) 执行备注（结构化可观测）

若触发能力降级或模板异常，在回复末尾追加以下结构化区块，不插入正文主叙述：

```yaml
execution_notes:
  fallback:
    brainstorming: false
    team: false
  template:
    missing: false
    source: "docs/内部参考/迭代需求/_templates/jjk_clarify_templates.md"
  degrade_reason: ""
  alternative_tool: ""
  verification: ""
```

填写规则：

1. 触发 `brainstorming` 降级时，`fallback.brainstorming=true`。
2. 触发 Team 降级时，`fallback.team=true`。
3. 模板缺失时，`template.missing=true` 且补充 `degrade_reason`。
4. 发生任何降级时，必须填写 `alternative_tool` 与 `verification`。

---

## 禁止项（强制）

1. 禁止从 `$jjk-clarify` 直接跳到 `$jjk-imp` 或 `$jjk-feature`。
2. 禁止未审批设计就进入实现。
3. 禁止跳过“2-3 方案 + 推荐”。

---

*使用 `$jjk-clarify` 触发。目标是“结合 brainstorming，而不是复制 brainstorming”。*
