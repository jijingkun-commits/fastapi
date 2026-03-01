---
description: 快速任务入口（小范围改动直达）：最小闭环实现与验证，支持越界自动升级 Team/正式流程
---

> 参考规则: @dual-database

# 快速任务工作流 (Quick Workflow)

`/jjk-quick` 是 `jjk-*` 体系里的快速改动入口，适用于目标清晰、风险可控、影响范围小的任务。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 与 Superpowers / OMX 的分工（强制）

1. `systematic-debugging`：仅在“小 Bug 根因不明”时先做根因定位。
2. `verification-before-completion`：保障快速任务也要有最小证据闭环。
3. `/jjk-plan`：当任务超出 quick 边界时接管正式规划。
4. `team`（OMX）：中等规模但可并行的小任务自动升级。
5. `/jjk-quick`：负责输入校验、边界判定、最小实现、最小验证与交付摘要。

约束：

1. 禁止在 `/jjk-quick` 复制上游 skill 正文；只保留调用契约与本地增强。
2. 禁止把快速任务扩展成隐式重构项目；越界必须升级流程。
3. `/jjk-team-quick` 不再作为主入口，统一由 `/jjk-quick` 按规模自动升级 Team。

## 跨 IDE 调用方式

1. Cursor / Claude Code：`/jjk-quick`
2. Codex：`/prompts:jjk-quick`

> 说明：Codex 的自定义命令入口是 `/prompts:<name>`，不是 `/<name>`。

## 模板来源优先级（跨项目，强制）

`/jjk-quick` 的模板按以下优先级读取：

1. 全局共享模板（默认主模板）：
   `/Users/jijingkun/.codex/engineering/templates/jjk_quick_templates.md`
2. 项目覆盖模板（仅放差异，不放全量复制）：
   `docs/内部参考/迭代需求/_templates/jjk_quick_templates.md`

若全局模板缺失，输出标记 `GLOBAL_TEMPLATE_MISSING` 并提示先初始化共享模板目录。
`GLOBAL_TEMPLATE_MISSING` 属于全局预检失败标记，可与命令级 `FAIL_FAST` 标记并存。

## 何时使用

| 场景 | 推荐命令 |
|---|---|
| typo/日志/小配置调整（低风险） | `/jjk-quick` ✅ |
| 根因明确的小 Bug 修复 | `/jjk-quick` ✅ |
| 单模块内小范围重构 | `/jjk-quick` ✅ |
| 涉及架构变更或跨层协议调整 | `/jjk-plan -> /jjk-imp(-ws)` |
| 根因未知的复杂故障 | `/jjk-debug` |

---

## 输入前置（强制）

至少提供以下输入之一（缺失字段可从上下文补齐；补齐失败即 `FAIL_FAST`）：

1. 明确任务目标与验收标准；
2. 预估影响范围（文件/模块）；
3. 风险边界（是否涉及 API/DB/权限/架构）。

硬约束：

1. 目标或验收标准不清晰，`FAIL_FAST` 输出 `QUICK_INPUT_INCOMPLETE`。
2. 预估影响超出 quick 上限，`FAIL_FAST` 输出 `QUICK_SCOPE_TOO_LARGE`。
3. 触及高风险边界（数据库结构/API 契约/权限模型），`FAIL_FAST` 输出 `QUICK_RISK_TOO_HIGH`。
4. 执行后无最小验证证据，`FAIL_FAST` 输出 `QUICK_VERIFY_MISSING`。

## 执行流程（强制顺序）

### 0) 先探索上下文（强制）

至少检查：

1. 真实变更范围与调用链影响。
2. 是否命中高风险文件（如 `agent_prompts.py`、`state.py`、`*_graph.py`）。
3. 是否需要文档同步（API/配置变更）。

### 0.5) 中大范围任务自动启用 Team（强制判定）

规模分段（强制）：

1. `<= 3` 个文件：单代理 quick；
2. `4 ~ 8` 个文件：可走 Team quick；
3. `> 8` 个文件：视为超出 quick 上限，输出 `QUICK_SCOPE_TOO_LARGE` 并转 `/jjk-plan`。

触发条件（满足任一即可）：

1. 影响文件数在 `4~8` 且可拆分为独立子任务；
2. 同时涉及后端+前端两个子域，但每个子域改动都较小；
3. 需要在多个 worktree 并行验证同类小改动；
4. 同一需求含 `>= 3` 个彼此独立的 quick 子任务。

执行策略：

1. **有 Team 能力时**：并行执行子任务，Leader 汇总统一交付摘要。
2. **无 Team 能力时**：降级单代理执行，并输出 `TEAM_UNAVAILABLE_FALLBACK`。
3. **超过 quick 边界时**：立即中止 quick，输出 `QUICK_SCOPE_TOO_LARGE` 并建议转 `/jjk-plan`。

### 1) 锁定 quick 边界

1. 定义本轮 `in-scope` 与 `out-of-scope`。
2. 明确不做事项（禁止扩散到无关模块）。

### 2) 实施最小改动

1. 先读后改，只改必要代码。
2. 复用现有模块，避免新增复杂抽象。
3. 不在本命令内引入跨层架构变更。

### 3) 最小验证

按改动类型执行最小必要验证：

| 改动类型 | 推荐验证 |
|---|---|
| Python 代码 | `python -m pytest tests/unit/<相关测试> -v --tb=short` |
| TypeScript 代码 | `cd web && npx tsc --noEmit` |
| 配置文件 | 关键服务启动/健康检查 |
| 纯文档/注释 | 结构与链接校验 |

规则：

1. 至少保留一条可复核命令证据。
2. 失败项必须记录命令、退出码、错误摘要与下一步建议。

### 4) 文档同步与交付

1. API 行为变更 -> 更新 `docs/API文档/接口文档.md`。
2. 配置项变更 -> 更新 `docs/开发文档/快速入门/配置说明.md`。
3. 输出 1~3 句交付摘要（改了什么、验证结果、后续建议）。

---

## 输出模板（推荐）

见全局模板：`/Users/jijingkun/.codex/engineering/templates/jjk_quick_templates.md`（`输出模板` 段）。
若本项目有覆盖规则，再查：`docs/内部参考/迭代需求/_templates/jjk_quick_templates.md`。

## 禁止项（强制）

1. 禁止借 quick 名义做无关重构。
2. 禁止修改高风险文件后仍声称“快速改动”。
3. 禁止新增数据库表或新 API 端点。
4. 禁止无验证证据直接宣称完成。

## 推荐链路

`/jjk-quick -> /jjk-doc-check -> /jjk-git-commit`

## 使用示例

```text
/jjk-quick
```

```text
/jjk-quick 修复聊天列表分页参数默认值错误，限定仅修改后端分页解析逻辑
```

---
*使用 `/jjk-quick` 触发。目标是“小步快跑且可回溯”，不是跳过工程约束。*
