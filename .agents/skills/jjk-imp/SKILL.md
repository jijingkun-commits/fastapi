---
name: jjk-imp
description: "Use when you need `jjk-imp` in this repository. Source intent: 代码实现入口：按 implementation_plan 执行、验证与回填"
---
<!-- AUTO-GENERATED: jjk-skill-mirror -->
<!-- source: .cursor/commands/jjk-imp.md -->

> 参考规则: @dual-database

# 实现工作流（Implementation Workflow）

`$jjk-imp` 负责把已审批的计划落到代码、测试和文档证据。

> **中文主导**：思考与输出统一中文。

---

## 输入前置（强制）

按优先级读取：

1. `docs/内部参考/迭代需求/<topic>_implementation_plan.md`（首选）
2. `docs/内部参考/迭代需求/fix_plan_<topic>.md`
3. `docs/内部参考/迭代需求/<topic>_requirements.md`（仅兜底，不建议直接开工）

硬校验：

1. 若 `implementation_readiness.implementation_ready=false` -> `IMPLEMENTATION_NOT_READY`
2. 若缺少工单级字段（如 `task_id/file_paths/symbols/acceptance_cmds`）-> `IMP_INPUT_TOO_COARSE`
3. 若缺少 `execution_contract` -> `IMP_EXECUTION_CONTRACT_MISSING`

---

## 执行流程（四步）

### 0) 上下文校验

至少检查：

1. 任务映射（`feature_id/task_id/pr_id/card_id`）；
2. 当前工作区变更与依赖文件；
3. 相关测试入口与最小回归范围。

### 1) 按 `execution_contract` 执行任务

先读取：`delivery_mode/execution_unit/commit_policy/stop_boundary/stop_on_blocked`。

执行规则：

1. `one_shot`：连续执行到 `all_done` 或阻塞；
2. `staged`：按 `per_pr` 或 `per_task` 边界停下；
3. `single_commit`：全量完成后提交；
4. `per_pr`：每个 `pr_id` 完成后提交。

每次停下必须输出：

1. `IMP_STOP_REASON=all_done|stage_boundary|blocked|manual`
2. `IMP_STOP_CONTEXT=<pr_id|task_id|blocker>`

### 2) 测试与验证

1. 可用时优先 TDD；不可用输出 `TDD_UNAVAILABLE_FALLBACK`。
2. 必须执行计划中的 `acceptance_cmds`。
3. 可用时执行 `verification-before-completion`；不可用输出 `VERIFY_BEFORE_COMPLETION_UNAVAILABLE_FALLBACK` 并附手工证据。

### 3) 文档回填与交接

命中以下变更时必须同步文档：

1. API -> `docs/API文档/接口文档.md`
2. 表结构 -> `docs/开发文档/架构设计/数据库设计.md`
3. 配置 -> `docs/开发文档/快速入门/配置说明.md` + `.env.example`
4. 测试行为 -> `docs/开发文档/测试管理/测试用例库.md`

最终必须输出：

1. 已完成任务清单（`task_id -> 文件 -> 验收命令 -> 结果`）
2. 未完成/阻塞项
3. 风险与回滚建议
4. 下一命令建议（`$jjk-verify` 或 `$jjk-review`）
5. `pr_ready_manifest`（`task_id/pr_id/card_id/changed_files/acceptance_cmds/rollback_point`）

---

## Team 策略（简化）

命中任一条件可启用 Team：

1. 改动文件 `>=8`
2. 跨边界 `>=2`
3. 待执行 `task_id >=6`
4. 需要并行 worktree

无 Team 能力时降级单代理并输出 `TEAM_UNAVAILABLE_FALLBACK`。

---

## 禁止项（强制）

1. 禁止输入不完整就直接编码。
2. 禁止跳过 `acceptance_cmds` 就宣称完成。
3. 禁止更改需求语义或计划目标。
4. 禁止命中同步规则时只改代码不回填文档。
5. 若进入 `$jjk-create-pr`，禁止 `pr_ready_manifest` 缺失。

---

*使用 `$jjk-imp` 触发。目标是“按计划可追溯实施，不自由漂移”。*
