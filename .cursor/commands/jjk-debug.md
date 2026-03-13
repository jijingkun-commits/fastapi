---
description: 问题修复入口（结合 systematic-debugging）：根因定位 -> 最小修复 -> 证据验证
---

> 参考规则: @dual-database

# 问题修复 (Debug)

`/jjk-debug` 是 `jjk-*` 体系里的修复入口，目标是**先根因后修复**，并以验证证据收口。


## 执行模式

### 默认模式：诊断 + 修复
- 根因定位 → 最小修复 → 证据验证

### 仅诊断模式：`/jjk-debug --diagnose-only`
- 仅做诊断与规划，**禁止修改代码**
- 产出修复计划（包含 2-3 个方案对比）
- 统一产物：`workdocs/任务拆解/<YYYY-MM-DD_主题>/contracts/fix_plan.md`
- 该模式替代旧 `jjk-pc` 入口

---

## 执行流程（强制顺序）

### 0) 先探索项目上下文（强制）

补充执行约束：执行命令时统一遵循 `.cursor/rules/core.mdc` 的“命令执行拆分”规则：单步单目标、失败只重跑当前步、长任务只轮询不重启、输出截断时优先拆短当前步。

至少检查：

1. 相关日志、报错栈、触发路径。
2. 最近相关改动与可疑提交。
3. 相关需求/测试/架构文档与现有监控信息。

### 0.5) 大任务自动启用 Team（强制判定）

`/jjk-debug` 在大任务时自动升级 Team 修复模式。

触发条件（满足任一即可）：

1. 涉及 `>= 3` 个模块/服务；
2. 同时涉及代码、数据库、外部网关/依赖两类以上边界；
3. 待验证根因假设 `>= 3`；
4. 需要并行比对多个环境（dev/stage/prod）。

执行策略：

1. **有 Team 能力时**：并行收集证据与验证假设，Leader 统一汇总根因与修复方案。
2. **无 Team 能力时**：降级为单代理执行，并输出 `TEAM_UNAVAILABLE_FALLBACK`。

### 0.6) Team 交叉质检约束

1. Team 模式下，每个成员提交阶段结果后，必须由另一名成员执行反方审查，至少包含：`1` 个质疑点、`1` 条验证命令、`1` 个通过/驳回结论。
2. `2` 人任务执行双向互审；`3+` 人任务执行环形互审（A 审 B，B 审 C，...，最后一人审 A）。
3. 未通过交叉审查的子任务不得标记完成；出现审查冲突时，必须创建复核子任务并附证据。
4. 阶段汇报至少包含：`结论`、`证据`、`剩余风险`。
5. 仅在 `pending=0`、`in_progress=0` 且交叉审查冲突清零后，才允许进入收尾或关停。

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
5. 若本次修复命中 Lean Guard 热点文件，完成修复前必须执行 `python3 scripts/ci/check_lean_budget.py --cached --strict`；失败则 `FAIL_FAST` 输出 `DEBUG_LEAN_GUARD_FAILED`。

### 5) 文档回填（强制）

命中以下条件时必须同步文档：

1. API 变更 -> `docs/API文档/接口文档.md`
2. 数据库变更 -> `docs/开发文档/架构设计/数据库设计.md`
3. 配置变更 -> `docs/开发文档/快速入门/配置说明.md` + `.env.example`
4. 测试行为变更 -> `docs/开发文档/测试管理/测试用例库.md`
5. 产品运行时 Skill 变更（如 `app/ai/skills/**`、`app/data/skills/**`、`app/services/skill_service.py`、`app/services/skill_bootstrap_service.py`、`app/main.py`、`app/api/v1/endpoints/skill_admin_api.py`、`app/api/v1/endpoints/user_skill_api.py`、`app/models/agent_skill.py`、`app/schemas/user_skill.py`、`scripts/data/import_skills.py`）-> 必须按 `.cursor/rules/doc_sync.mdc` 的“产品运行时 Skill 专项映射（强制）”同步 `技能系统需求.md`、`AI技能库.md`、`接口文档.md`、相关配置/部署/测试文档
6. 禁止只修 Skill 运行时问题而不回填 `技能系统需求.md` / `AI技能库.md` / 部署文档口径

### 6) 交付产物（强制）

必须输出调试交付文档：

`workdocs/任务拆解/<YYYY-MM-DD_主题>/reports/debug_report.md`

最小内容：

1. 问题现象与影响范围
2. 根因证据链（含被排除假设）
3. 修复内容（文件/符号/变更摘要）
4. 验证命令与结果（含失败->通过过程）
5. 风险、回滚点与后续建议

建议结构见全局模板：`${CODEX_HOME:-$HOME/.codex}/engineering/templates/jjk_debug_templates.md`。  
若本项目有覆盖规则，再查：`docs/内部参考/迭代需求/_templates/jjk_debug_templates.md`。

---

## 禁止项（强制）

1. 禁止未定位根因直接修改代码。
2. 禁止无回归测试证据就宣称“修复完成”。
3. 禁止一次提交混入多个无关问题修复。
4. 禁止命中文档同步规则时只改代码不回填文档。

---

*使用 `/jjk-debug` 触发。目标是“系统化修复 + 证据闭环”，不是猜测式打补丁。*
