---
description: 问题修复入口（结合 systematic-debugging）：根因定位 -> 最小修复 -> 证据验证
---

> 参考规则: @dual-database

# 问题修复 (Debug)

`/jjk-debug` 是 `jjk-*` 体系里的修复入口，目标是**先根因后修复**，并以验证证据收口。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 与 Superpowers / OMX 的分工（强制）

1. `systematic-debugging`：负责根因调查、假设验证、最小修复策略。
2. `test-driven-development`：负责回归测试先行（先失败后修复）。
3. `verification-before-completion`：负责完成前证据校验。
4. `team`（OMX）：负责大范围故障并行排查与修复分片。
5. `/jjk-debug`：负责阶段编排、输入输出契约、文档回填与交付口径。

约束：

1. 禁止在 `/jjk-debug` 复制上述 skills 的完整正文。
2. 插件可用时优先调用；插件不可用时必须显式 fallback，不得静默降级。
3. `/jjk-debug` 是“可改码修复”；若只做诊断不改码，必须回退 `/jjk-pc`。

## 跨 IDE 调用方式

1. Cursor / Claude Code：`/jjk-debug`
2. Codex：`/prompts:jjk-debug`

> 说明：Codex 的自定义命令入口是 `/prompts:<name>`，不是 `/<name>`。

## 模板来源优先级（跨项目，强制）

`/jjk-debug` 的模板按以下优先级读取：

1. 全局共享模板（默认主模板）：
   `/Users/jijingkun/.codex/engineering/templates/jjk_debug_templates.md`
2. 项目覆盖模板（仅放差异，不放全量复制）：
   `docs/内部参考/迭代需求/_templates/jjk_debug_templates.md`

若全局模板缺失，输出标记 `GLOBAL_TEMPLATE_MISSING` 并提示先初始化共享模板目录。

## 何时使用

| 场景 | 推荐命令 |
|---|---|
| 遇到 Bug，需要直接修复并回归验证 | `/jjk-debug` ✅ |
| 仅诊断并给修复计划，不改代码 | `/jjk-pc` |
| 已有可执行计划，按任务落地 | `/jjk-imp` |
| 修复后统一验收 | `/jjk-verify` |

---

## 执行流程（强制顺序）

### 0) 先探索项目上下文（强制）

至少检查：

1. 相关日志、报错栈、触发路径。
2. 最近相关改动与可疑提交。
3. 相关需求/测试/架构文档与现有监控信息。

### 0.5) 大任务自动启用 Team（强制判定）

`/jjk-team-debug` 不再作为主入口。
统一由 `/jjk-debug` 在大任务时自动升级 Team 修复模式。

触发条件（满足任一即可）：

1. 涉及 `>= 3` 个模块/服务；
2. 同时涉及代码、数据库、外部网关/依赖两类以上边界；
3. 待验证根因假设 `>= 3`；
4. 需要并行比对多个环境（dev/stage/prod）。

执行策略：

1. **有 Team 能力时**：并行收集证据与验证假设，Leader 统一汇总根因与修复方案。
2. **无 Team 能力时**：降级为单代理执行，并输出 `TEAM_UNAVAILABLE_FALLBACK`。

### 1) 根因调查（先于修复，强制）

1. 可用 `systematic-debugging` 时，必须先完成 root cause 调查再修复。
2. 不可用时输出 `SYSTEMATIC_DEBUGGING_UNAVAILABLE_FALLBACK`，但仍需遵守“先调查后改码”。
3. 若无法稳定重现，输出 `REPRO_NOT_STABLE` 并补充观测计划，禁止盲修。

### 2) 回归测试先行（强制）

1. 可用 `test-driven-development` 时，必须先写失败回归测试再改码。
2. 不可用时输出 `TDD_UNAVAILABLE_FALLBACK`，至少补最小复现测试并先验证失败。
3. 禁止“先改后补测”作为默认路径。

### 3) 最小修复与实现约束（强制）

1. 每次仅针对一个根因假设落最小修复。
2. 禁止打包多项无关修复或顺手重构。
3. 若修复过程中发现上游设计问题，应标记 `DEBUG_ARCH_RISK_DETECTED`，并提示回到 `/jjk-plan` 做结构修订。

### 4) 验证与证据收口（强制）

1. 必须执行：复现测试 + 受影响回归测试 + 最小验证命令。
2. 可用 `verification-before-completion` 时，必须遵循其证据优先原则。
3. 不可用时输出 `VERIFY_BEFORE_COMPLETION_UNAVAILABLE_FALLBACK`，并手工附命令结果证据。
4. 无新鲜命令证据，禁止宣称“修复完成”。

### 5) 文档回填（强制）

命中以下条件时必须同步文档：

1. API 变更 -> `docs/API文档/接口文档.md`
2. 数据库变更 -> `docs/开发文档/架构设计/数据库设计.md`
3. 配置变更 -> `docs/开发文档/快速入门/配置说明.md` + `.env.example`
4. 测试行为变更 -> `docs/开发文档/测试管理/测试用例库.md`

### 6) 交付产物（强制）

必须输出调试交付文档：

`docs/内部参考/迭代需求/debug_report_<topic>.md`

最小内容：

1. 问题现象与影响范围
2. 根因证据链（含被排除假设）
3. 修复内容（文件/符号/变更摘要）
4. 验证命令与结果（含失败->通过过程）
5. 风险、回滚点与后续建议

建议结构见全局模板：`/Users/jijingkun/.codex/engineering/templates/jjk_debug_templates.md`。  
若本项目有覆盖规则，再查：`docs/内部参考/迭代需求/_templates/jjk_debug_templates.md`。

---

## 禁止项（强制）

1. 禁止未定位根因直接修改代码。
2. 禁止无回归测试证据就宣称“修复完成”。
3. 禁止一次提交混入多个无关问题修复。
4. 禁止命中文档同步规则时只改代码不回填文档。

---

*使用 `/jjk-debug` 触发。目标是“系统化修复 + 证据闭环”，不是猜测式打补丁。*
