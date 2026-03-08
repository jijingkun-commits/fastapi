---
description: 测试入口（消费 review/plan/manifest）：执行可追溯测试矩阵并产出测试报告，支持大范围自动 Team
---

> 参考规则: @dual-database
> 测试质量门禁：`.cursor/rules/test_quality.mdc`

# 测试执行工作流 (Test Workflow)

`/jjk-test` 是 `jjk-*` 体系里的测试入口，负责按变更范围执行测试矩阵并沉淀可追溯测试资产。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 与 Superpowers / OMX 的分工（强制）
## 跨 IDE 调用方式
## 模板来源优先级（跨项目，强制）

`/jjk-test` 的模板按以下优先级读取：

1. 全局共享模板（默认主模板）：
   `${CODEX_HOME:-$HOME/.codex}/engineering/templates/jjk_test_templates.md`
2. 项目覆盖模板（仅放差异，不放全量复制）：
   `docs/内部参考/迭代需求/_templates/jjk_test_templates.md`

若全局模板缺失，输出标记 `GLOBAL_TEMPLATE_MISSING` 并提示先初始化共享模板目录。

## 输入前置（强制）

至少提供以下输入之一：

1. `review_report_<topic>.md`；
2. `pr_ready_manifest` / `pr_ready_manifest_ws`；
3. `implementation_plan` 中可追溯 `feature_id/task_id` 的测试范围。

硬约束：

1. 若无法解析 `task_id/pr_id/feature_id` 任一关键追溯字段，`FAIL_FAST` 输出 `TEST_INPUT_INCOMPLETE`。
2. 若测试范围无法映射到本次变更，`FAIL_FAST` 输出 `TEST_SCOPE_UNCLEAR`。
3. 若在线测试前置门禁失败（端口/健康检查），`FAIL_FAST` 输出 `TEST_ONLINE_GATE_FAILED`。
4. 若执行结束仍未产出报告，`FAIL_FAST` 输出 `TEST_REPORT_MISSING`。
5. DB 风险任务缺少 DB 证据闭环时，`FAIL_FAST` 输出 `TEST_DB_CHAIN_INCOMPLETE`。
6. 若无法建立本次变更的风险模型，`FAIL_FAST` 输出 `TEST_RISK_MODEL_MISSING`。
7. 若测试矩阵未覆盖关键失败模式，`FAIL_FAST` 输出 `TEST_FAILURE_MODE_UNCOVERED`。

## 执行流程（强制顺序）

### 0) 先探索上下文（强制）

至少检查：

1. 变更范围与风险边界（后端/API/前端/AI/数据库）。
2. 测试用例来源（模块案例文档 + 用例库 + `.cursor/rules/test_quality.mdc`）。
3. 当前端口与服务状态（worktree 场景优先 `scripts/vk_ports.sh`）。
4. 本次变更命中的高风险维度（边界、状态迁移、权限、幂等、部分失败、可观测性、外部依赖退化等）。

### 0.5) 大范围测试自动启用 Team（强制判定）

触发条件（满足任一即可）：

1. 待执行测试命令 `>= 10`；
2. 同时覆盖后端+前端+API 三类测试；
3. 待测模块 `>= 3`；
4. 涉及并行 worktree 的 Gate 验证。

执行策略：

1. **有 Team 能力时**：按测试维度并行执行，Leader 汇总统一报告。
2. **无 Team 能力时**：降级单代理执行，并输出 `TEAM_UNAVAILABLE_FALLBACK`。

### 0.6) Team 交叉质检约束

1. Team 模式下，每个成员提交阶段结果后，必须由另一名成员执行反方审查，至少包含：`1` 个质疑点、`1` 条验证命令、`1` 个通过/驳回结论。
2. `2` 人任务执行双向互审；`3+` 人任务执行环形互审（A 审 B，B 审 C，...，最后一人审 A）。
3. 未通过交叉审查的子任务不得标记完成；出现审查冲突时，必须创建复核子任务并附证据。
4. 阶段汇报至少包含：`结论`、`证据`、`剩余风险`。
5. 仅在 `pending=0`、`in_progress=0` 且交叉审查冲突清零后，才允许进入收尾或关停。

### 1) 环境门禁与服务准备

1. 统一端口来源（`vk_ports.sh` / `.env.vk.local`）。
2. 需要在线测试时先做后端健康检查与端口检查。
3. 自动拉起失败即阻断（`TEST_ENV_NOT_READY`）。

### 2) 生成测试矩阵（AAA + 风险建模）

1. 按 `feature_id` 生成最小可追溯测试矩阵。
2. 先建立风险模型：至少识别本次变更命中的 `Happy Path / Boundary / State Transition / Failure Mode / Error Contract` 适用项；命中 workflow/router/handoff/coverage/queue/streaming 时，必须补 `pending/blocked/success` 收口语义。
3. 测试矩阵不得只停留在 `Happy Path / Edge Cases / Error Handling` 三分法；必须显式列出关键失败模式与高风险维度。
4. 高风险链路补充稳定性/超时/重试/部分失败/外部依赖退化场景。
5. 矩阵必须显式列出：`Risk Model`、`Required Evidence`、`Actual Evidence`、`Scripted Flow Status`、`Historical Gap vs Current Gap`。

### 3) 执行三层验证

1. **UI/API 层**：Playwright 或 API 测试。
2. **数据层**：必要时校验持久化结果（按双库路由）。
3. **系统层**：日志与错误信号检查。

规则：

1. 只跑与本次变更相关的必要测试，不默认全量。
2. 失败项必须记录命令、退出码、摘要与责任归属。
3. Playwright 不可用时输出 `PLAYWRIGHT_UNAVAILABLE_FALLBACK`，并给替代验证路径。
4. `scripted_flow` 证据必须纳入主矩阵，不得作为口头补充。
5. 每个关键测试至少核对两类断言：`主结果断言` + `失败语义断言`；涉及状态/副作用时，继续补 `状态/副作用/可观测性` 断言。
6. 命中弱断言、实现耦合、快照滥用、绕开真实边界等坏测试反模式时，记录 `TEST_ASSERTION_WEAK` / `TEST_IMPL_COUPLED` / `TEST_SNAPSHOT_OVERUSE` / `TEST_REAL_BOUNDARY_SKIPPED`。

### 4) Gate 回填（并行拆解场景）

若存在 `vk_cards.json` 且本轮属于 Gate 校验，必须执行：

```bash
venv/bin/python scripts/backfill_gate_status.py --cards "$VK_CARDS_PATH"
```

1. 禁止手工改 Gate 数字。
2. 回填失败视为 Gate 未完成。

### 5) 报告产出与资产沉淀

必须在 `docs/开发文档/测试管理/测试报告/` 产出报告，命名遵循：

1. 主报告：`{模块名}测试报告.md`
2. 归档：`{模块名}测试报告_YYYYMMDD_{主题}.md`
3. 归档：`{模块名}测试报告_YYYY-MM-DD_{主题}.md`

报告最小内容：

1. `Executive Summary`（PASS/WARN/FAIL）
2. `Defect List`（含证据）
3. `Trace Matrix`（用例ID/结果/状态）
4. 本轮问题与历史问题区分
5. `Risk Model`（本轮命中的风险维度与失败模式）
6. `Required Evidence`（必需证据集合）
7. `Actual Evidence`（本轮实际执行证据）
8. `Scripted Flow Status`（脚本链路执行/缺失状态）
9. `Historical Gap vs Current Gap`（历史缺口与本轮新增缺口）
10. `Test Quality Review`（风险模型、失败模式覆盖、断言质量、实现耦合风险、低价值测试识别）

并同步：

1. `docs/开发文档/测试管理/<模块>测试案例.md`
2. `docs/开发文档/测试管理/测试用例库.md`
3. 相关索引（`docs/SUMMARY.md`、测试报告 README）

---


## 失败码补充（证据矩阵）

1. `TEST_EVIDENCE_COVERAGE_GAP`
2. `TEST_SCRIPTED_FLOW_UNTRACKED`
3. `TEST_DB_CHAIN_INCOMPLETE`
4. `TEST_RISK_MODEL_MISSING`
5. `TEST_FAILURE_MODE_UNCOVERED`
6. `TEST_ASSERTION_WEAK`
7. `TEST_IMPL_COUPLED`
8. `TEST_LOW_VALUE_CASE_DETECTED`

## 输出模板（推荐）

见全局模板：`${CODEX_HOME:-$HOME/.codex}/engineering/templates/jjk_test_templates.md`（`输出模板` 段）。
若本项目有覆盖规则，再查：`docs/内部参考/迭代需求/_templates/jjk_test_templates.md`。

## 禁止项（强制）

1. 禁止无追溯字段执行完整测试。
2. 禁止在线测试门禁失败后以 `SKIP` 冒充通过。
3. 禁止测试失败后直接在本命令内“顺手修复”。
4. 禁止无报告结束测试流程。
5. 禁止以“有测试命令”替代“有风险模型与失败模式覆盖”。
6. 禁止接受只断言 200 / 非空 / mock 次数的弱测试作为关键回归。

## 推荐链路

`/jjk-review -> /jjk-test -> /jjk-verify`

## 使用示例

```text
/jjk-test
```

```text
/jjk-test @docs/内部参考/迭代需求/review_report_<topic>.md
```

---
*使用 `/jjk-test` 触发。目标是“可追溯测试证据 + 可复用测试资产”，不是单次命令跑通。*
