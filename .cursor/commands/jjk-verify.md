---
description: 验收入口（消费 review/pr/manifest 证据）：审查+测试+UAT 一体化判定，支持大范围自动 Team
---

> 参考规则: @dual-database
> 测试质量门禁：`.cursor/rules/test_quality.mdc`

# 组合验证工作流 (Verify Workflow)

`/jjk-verify` 是 `jjk-*` 体系里的验收入口，负责基于审查结论与测试证据给出最终可执行判定（`PASS|WARN|FAIL`）。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 与 Superpowers / OMX 的分工（强制）
## 跨 IDE 调用方式
## 模板来源优先级（跨项目，强制）

`/jjk-verify` 的模板按以下优先级读取：

1. 全局共享模板（默认主模板）：
   `${CODEX_HOME:-$HOME/.codex}/engineering/templates/jjk_verify_templates.md`
2. 项目覆盖模板（仅放差异，不放全量复制）：
   `docs/内部参考/迭代需求/_templates/jjk_verify_templates.md`

若全局模板缺失，输出标记 `GLOBAL_TEMPLATE_MISSING` 并提示先初始化共享模板目录。

## 输入前置（强制）

至少提供以下证据来源之一：

1. `review_report_<topic>.md`；
2. `pr_ready_manifest` / `pr_ready_manifest_ws`；
3. 当前分支可追溯到 `task_id/pr_id` 的改动与测试证据。

硬约束：

1. 若无法解析 `task_id` 或 `pr_id`，`FAIL_FAST` 输出 `VERIFY_INPUT_INCOMPLETE`。
2. 若映射与计划不一致（`task_to_pr_mapping`），`FAIL_FAST` 输出 `VERIFY_MAPPING_MISMATCH`。
3. 若无可复核的测试/命令证据，`FAIL_FAST` 输出 `VERIFY_EVIDENCE_MISSING`。
4. 若审查结论已 `BLOCKED` 且未修复，`FAIL_FAST` 输出 `VERIFY_BLOCKER_UNRESOLVED`。
5. DB 风险任务若无法对齐 `mandatory_evidence`，必须 `FAIL_FAST`。

## 执行硬约束（强制）

1. 无论成功、失败或中断，本轮最后都必须输出 `## 验证报告`。
2. 自动证据充分时，直接给最终结论；不得强制用户逐项手工确认。
3. 仅在自动证据不足时进入交互 UAT，问题数限制 1~3 条。
4. 任一关键命令失败，必须在报告记录：`命令原文 + 退出码 + 错误摘要 + 处理建议`。
5. 必须区分“本轮问题”与“历史问题”。
6. `PASS` 必须满足 `mandatory_evidence` 全量命中。
7. DB 风险任务缺少 DB 类证据不得降级为 `WARN`。
8. 若 review/test 证据无法证明测试质量达标，`FAIL_FAST` 输出 `VERIFY_TEST_QUALITY_UNPROVEN`。

---

## 执行流程（强制顺序）

### 0) 先探索上下文（强制）

补充执行约束：执行命令时统一遵循 `.cursor/rules/core.mdc` 的“命令执行拆分”规则：单步单目标、失败只重跑当前步、长任务只轮询不重启、输出截断时优先拆短当前步。

至少检查：

1. 变更范围（相对 `main/master` + 工作区未提交改动）。
2. 风险边界（AI workflow/API/DB/前端/SSE）。
3. 输入证据是否满足最小验收要求。
4. review/test 证据是否已覆盖 `.cursor/rules/test_quality.mdc` 的风险模型、失败模式覆盖与评分卡要求。

### 0.5) 大范围验收自动启用 Team（强制判定）

触发条件（满足任一即可）：

1. 待验文件 `>= 25`；
2. 涉及模块 `>= 4`；
3. 测试命令 `>= 8` 或跨后端+前端+AI 三类以上；
4. 同时需要审查复核 + 自动测试 + UAT 组合判定。

执行策略：

1. **有 Team 能力时**：分维度并行执行，Leader 汇总统一验收报告。
2. **无 Team 能力时**：降级单代理执行，并输出 `TEAM_UNAVAILABLE_FALLBACK`。

### 0.6) Team 交叉质检约束

1. Team 模式下，每个成员提交阶段结果后，必须由另一名成员执行反方审查，至少包含：`1` 个质疑点、`1` 条验证命令、`1` 个通过/驳回结论。
2. `2` 人任务执行双向互审；`3+` 人任务执行环形互审（A 审 B，B 审 C，...，最后一人审 A）。
3. 未通过交叉审查的子任务不得标记完成；出现审查冲突时，必须创建复核子任务并附证据。
4. 阶段汇报至少包含：`结论`、`证据`、`剩余风险`。
5. 仅在 `pending=0`、`in_progress=0` 且交叉审查冲突清零后，才允许进入收尾或关停。

### 0.7) 分支端口上下文校验（Web/E2E/UAT 涉及时强制）

1. 先执行 `eval "$(bash scripts/vk_ports.sh --export)"`，以当前分支/工作树自动计算 `VK_BACKEND_PORT`、`VK_FRONTEND_PORT`、`VK_BACKEND_BASE_URL`、`VK_FRONTEND_BASE_URL`。
2. 禁止在 Web/E2E/UAT 场景硬编码 `3000/8000`；必须使用上述变量或 `.env.vk.local` 同源值。
3. 运行态最小校验：  
   - `lsof -nP -iTCP:${VK_BACKEND_PORT} -sTCP:LISTEN`  
   - `lsof -nP -iTCP:${VK_FRONTEND_PORT} -sTCP:LISTEN`  
   - `curl -sf "${VK_BACKEND_BASE_URL}/api/v1/health"`  
4. 若浏览器访问目标与 `VK_FRONTEND_BASE_URL` 不一致，`FAIL_FAST` 输出 `VERIFY_PORT_CONTEXT_MISMATCH`。

### 1) 变更分析与验证策略

1. 解析变更范围（优先 `main/master...HEAD`，失败时降级为工作区 + 最近提交）。
2. 按变更类型选择最小必要验证集（后端/API/前端/AI/数据库）。
3. 生成验证计划（命令清单 + 断言点）。
4. 读取 `mandatory_evidence` 并构建“必需证据对账表”。
5. 若命中测试变更或关键 bugfix，必须把 `风险模型`、`失败模式覆盖`、`测试质量评分卡` 纳入验收计划。

### 2) 快速审查复核

1. 消费 `review_report` 或当前审查证据。
2. 若存在 `P0/P1` 未关闭项，标记 `VERIFY_BLOCKER_UNRESOLVED` 并阻断。
3. 若 review 未显式给出测试质量评分卡或评分结论不可复核，标记 `VERIFY_TEST_QUALITY_UNPROVEN` 并阻断。

### 3) 自动测试执行

1. 仅跑与变更相关的必要测试。
2. 记录每条命令的退出码与结果统计。
3. 测试失败不应静默吞掉，必须入报告。
4. 验收阶段必须确认关键失败模式已被验证，而不是只确认 Happy Path 通过。

### 4) UAT 判定

1. 默认自动判定（命令断言 + 回包字段 + 退出码）。
2. 证据不足时进入交互确认（1~3 项），并给出清晰通过标准。
3. UAT `FAIL` 时，输出回退修复建议。
4. 涉及浏览器路径时，报告中必须回填：`VK_GIT_BRANCH`、`VK_BACKEND_BASE_URL`、`VK_FRONTEND_BASE_URL`、实际访问 URL 与一致性结论。

### 5) 报告输出与结论

结论规则：

1. `PASS`：审查无阻断 + 关键测试通过 + `mandatory_evidence` 全量满足 + 测试质量评分卡达标。
2. `WARN`：仅允许出现在非 mandatory 证据缺口，且核心链路通过；不得用来掩盖测试质量不达标。
3. `FAIL`：阻断问题未解、关键测试/UAT 失败、mandatory 证据缺失，或测试质量达不到 `.cursor/rules/test_quality.mdc` 门槛。

必须输出：

1. 总结（PASS/WARN/FAIL）
2. 审查结果摘要
3. 测试统计
4. UAT 结论
5. 测试质量结论（风险模型 / 失败模式覆盖 / 评分卡）
6. 自动证据与降级记录
7. 文档同步状态（命中产品运行时 Skill 变更时，需逐项核对专项映射是否齐套）
8. 下一步建议命令（`合并/发布`、`/jjk-debug`、`/jjk-imp(-ws)`）

---


## 失败码补充（mandatory evidence）

1. `VERIFY_MANDATORY_EVIDENCE_MISSING`
2. `VERIFY_CHAT_DB_UNPROVEN`
3. `VERIFY_DATA_DB_UNPROVEN`
4. `VERIFY_TEST_QUALITY_UNPROVEN`
5. `VERIFY_FAILURE_MODE_UNCOVERED`

## 输出模板（推荐）

- 极简报告模板：`${CODEX_HOME:-$HOME/.codex}/engineering/templates/jjk_verify_templates.md`（`极简报告模板` 段）
- 标准报告模板：`${CODEX_HOME:-$HOME/.codex}/engineering/templates/jjk_verify_templates.md`（`标准报告模板` 段）
- 项目覆盖：`docs/内部参考/迭代需求/_templates/jjk_verify_templates.md`

## 禁止项（强制）

1. 禁止只输出“进行中/待确认”而不输出验收报告。
2. 禁止无证据直接给 `PASS`。
3. 禁止忽略阻断项继续推进到交付阶段。
4. 禁止把历史问题全部算作本次问题。
5. 禁止用“测试都通过了”替代“测试质量达标”。

## 推荐链路

`主链: /jjk-review -> /jjk-verify -> 合并/发布`

`可选分支: 若需远端 PR 交付，可在 /jjk-review 前先执行 /jjk-create-pr`

## 使用示例

```text
/jjk-verify
```

```text
/jjk-verify @docs/内部参考/迭代需求/review_report_<topic>.md
```

---
*使用 `/jjk-verify` 触发。目标是“证据驱动验收结论”，不是形式化汇总。*
