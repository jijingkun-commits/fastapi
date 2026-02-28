---
description: 问题诊断入口（结合 systematic-debugging）：仅分析定位并产出修复计划，不修改代码
---

> 参考规则: @dual-database

# 问题诊断 (Diagnose)

`/jjk-pc` 是 `jjk-*` 体系里的诊断入口，目标是**复用** Superpowers 的 `systematic-debugging` 方法，而不是复制其正文。

## 执行契约（强制）

1. 仅做诊断与规划：**禁止修改代码**。
2. 若当前环境可用 `systematic-debugging`，必须优先按其“重现 -> 假设 -> 验证 -> 结论”路径执行。
3. 若当前环境不可用 `systematic-debugging`，按本文件 fallback 流程执行，并在输出中标记 `SYSTEMATIC_DEBUGGING_UNAVAILABLE_FALLBACK`。
4. 修复计划必须包含 2-3 个修复方案对比与推荐方案，禁止只给单一路径。
5. 统一产物写入：`docs/内部参考/迭代需求/fix_plan_<topic>.md`。

## 与 Superpowers / OMX 的分工（强制）

1. `systematic-debugging`：负责诊断方法论（重现、假设、验证、证据闭环）。
2. `team`（OMX）：负责大范围问题的并行证据收集与假设验证。
3. `/jjk-pc`：负责项目内诊断契约、产物结构、跨 IDE 调用和 fallback 标记。

约束：

1. 禁止在 `/jjk-pc` 复制 `systematic-debugging` 的完整流程正文。
2. 插件可用时优先调用；插件不可用时必须显式 fallback，不得静默降级。
3. `/jjk-pc` 产物是下游 `/jjk-imp fix_plan_<topic>` 的唯一输入，不允许临时口头计划替代。

## 跨 IDE 调用方式

1. Cursor / Claude Code：`/jjk-pc`
2. Codex：`/prompts:jjk-pc`

> 说明：Codex 的自定义命令入口是 `/prompts:<name>`，不是 `/<name>`。

## 模板来源优先级（跨项目，强制）

`/jjk-pc` 的模板按以下优先级读取：

1. 全局共享模板（默认主模板）：
   `/Users/jijingkun/.codex/engineering/templates/jjk_pc_templates.md`
2. 项目覆盖模板（仅放差异，不放全量复制）：
   `docs/内部参考/迭代需求/_templates/jjk_pc_templates.md`

若全局模板缺失，输出标记 `GLOBAL_TEMPLATE_MISSING` 并提示先初始化共享模板目录。

## 何时使用

| 场景 | 推荐命令 |
|---|---|
| 仅排查问题并产出修复计划 | `/jjk-pc` ✅ |
| 排查并直接修复 | `/jjk-debug` |
| 完整审查/测试/验收闭环 | `/jjk-verify` |

---

## 执行流程（精简）

### 0) 先探索项目上下文（强制）

至少检查：

1. 关键代码入口与最近变更（相关模块 + `git status`）
2. 相关需求/测试/架构文档
3. 日志与运行环境差异（开发/测试/生产）

### 0.5) 大任务自动启用 Team（强制判定）

`/jjk-team-pc` 不再作为主入口。
统一由 `/jjk-pc` 在大任务时自动升级为 Team 诊断模式。

触发条件（满足任一即可）：

1. 涉及 `>= 3` 个独立模块/服务；
2. 同时涉及代码、数据库、外部依赖/网关三类证据中的两类以上；
3. 待验证根因假设 `>= 3`，且单代理验证成本过高；
4. 需要并行比对多个环境（如 dev/stage/prod）。

执行策略：

1. **有 Team 能力时**：自动并行收集证据与验证假设，Leader 汇总唯一根因结论。
2. **无 Team 能力时**：降级为单代理执行，并在输出标记 `TEAM_UNAVAILABLE_FALLBACK`。

### 1) 证据收集与重现

1. 收集最小必要日志、配置、上下文。
2. 建立可重复验证的重现路径（测试/脚本/请求序列）。
3. 不可稳定重现时，必须标记 `REPRO_NOT_STABLE` 并说明继续策略。

### 2) 根因假设与验证

1. 列出 2-3 个候选根因（来源证据必须可追溯）。
2. 对每个假设给出验证动作与结果（PASS/FAIL）。
3. 输出“已排除原因”清单，避免后续重复排查。

### 3) 修复方案设计（强制）

必须提供 2-3 个修复方案，并使用表格比较：方案 | 优点 | 缺点 | 成本 | 推荐度。

### 4) 产出修复计划（强制）

统一写入：`docs/内部参考/迭代需求/fix_plan_<topic>.md`

必含最小结构：

1. 问题摘要（现象、影响范围、严重级别）
2. 根因结论（含证据链与被排除假设）
3. 修复方案对比（2-3 方案 + 推荐）
4. 变更清单（文件/数据库/配置）
5. 风险与回滚策略
6. 验证计划（单测/联测/手验）
7. 实施顺序与工作量估算

建议结构见全局模板：`/Users/jijingkun/.codex/engineering/templates/jjk_pc_templates.md`。  
若本项目有覆盖规则，再查：`docs/内部参考/迭代需求/_templates/jjk_pc_templates.md`。

### 5) 用户确认与下一步

1. 展示 `fix_plan_<topic>.md` 并请求确认。
2. 确认后进入：
   - `/jjk-imp fix_plan_<topic>`（按计划实施）
   - 或 `/jjk-debug`（重新从重现开始并直接修复）

---

## 禁止项（强制）

1. 禁止在 `/jjk-pc` 阶段修改代码。
2. 禁止未完成方案对比就直接给“唯一修复方案”。
3. 禁止无证据链地宣称“已定位根因”。
4. 禁止跳过修复计划产物直接进入实现。

---

*使用 `/jjk-pc` 触发。*
