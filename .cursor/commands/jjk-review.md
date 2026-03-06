---
description: 审查入口（消费 PR/manifest）：结构化评审、风险分级与结论回填，支持大范围自动 Team
---

> 参考规则: @dual-database

# 代码审查工作流 (Code Review)

`/jjk-review` 是 `jjk-*` 体系里的审查入口，负责把实现结果转为可执行的审查结论（通过/阻断/有条件通过）。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 与 Superpowers / OMX 的分工（强制）
## 跨 IDE 调用方式
## 模板来源优先级（跨项目，强制）

`/jjk-review` 的模板按以下优先级读取：

1. 全局共享模板（默认主模板）：
   `${CODEX_HOME:-$HOME/.codex}/engineering/templates/jjk_review_templates.md`
2. 项目覆盖模板（仅放差异，不放全量复制）：
   `docs/内部参考/迭代需求/_templates/jjk_review_templates.md`

若全局模板缺失，输出标记 `GLOBAL_TEMPLATE_MISSING` 并提示先初始化共享模板目录。

## 输入前置（强制）

至少提供以下任一审查对象：

1. `pr_id` / PR 链接；
2. 当前分支相对 `main/master` 的 diff；
3. `pr_ready_manifest` / `pr_ready_manifest_ws`。

硬约束：

1. 必须可追溯到 `task_id` 与 `pr_id`；缺失时 `FAIL_FAST` 输出 `REVIEW_INPUT_INCOMPLETE`。
2. 若 manifest 与 `implementation_plan.task_to_pr_mapping` 不一致，`FAIL_FAST` 输出 `REVIEW_MAPPING_MISMATCH`。
3. 必须明确审查基线（`main/master`）；否则 `FAIL_FAST` 输出 `REVIEW_BASELINE_MISSING`。
4. 若无可复核的验证证据（`acceptance_cmds`/测试结果），`FAIL_FAST` 输出 `REVIEW_EVIDENCE_MISSING`。

## 执行流程（强制顺序）

### 0) 先探索上下文（强制）

至少检查：

1. 需求/计划/WS 与当前改动映射关系。
2. 变更文件范围与关键风险点（API/DB/权限/并发/跨端协议）。
3. 历史相关缺陷与已知豁免项。

### 0.5) 大范围审查自动启用 Team（强制判定）

触发条件（满足任一即可）：

1. 待审文件 `>= 20`；
2. 涉及模块 `>= 4`；
3. 反馈项或待核验项 `>= 10`；
4. 同时涉及功能正确性 + 安全 + 测试 + 文档四类审查。

执行策略：

1. **有 Team 能力时**：分维度并行审查，Leader 汇总统一结论。
2. **无 Team 能力时**：降级单代理执行，并输出 `TEAM_UNAVAILABLE_FALLBACK`。

### 0.6) Team 交叉质检约束

1. Team 模式下，每个成员提交阶段结果后，必须由另一名成员执行反方审查，至少包含：`1` 个质疑点、`1` 条验证命令、`1` 个通过/驳回结论。
2. `2` 人任务执行双向互审；`3+` 人任务执行环形互审（A 审 B，B 审 C，...，最后一人审 A）。
3. 未通过交叉审查的子任务不得标记完成；出现审查冲突时，必须创建复核子任务并附证据。
4. 阶段汇报至少包含：`结论`、`证据`、`剩余风险`。
5. 仅在 `pending=0`、`in_progress=0` 且交叉审查冲突清零后，才允许进入收尾或关停。

### 1) 审查范围锁定

1. 锁定“本 PR/本任务”改动范围，禁止扩散审查到无关历史债务。
2. 输出审查范围清单（文件、模块、风险边界）。

### 2) 四维审查（强制）

1. **功能正确性**：需求映射、边界行为、异常路径。
2. **代码质量**：可维护性、复杂度、重复逻辑、命名与结构一致性。
3. **安全与稳定性**：输入校验、权限、敏感信息、并发/资源风险。
4. **测试与文档一致性**：`acceptance_cmds`、测试覆盖、文档同步。

### 3) 证据校验（强制）

1. 引用并核验 `acceptance_cmds` 执行结果。
2. 无法验证的项必须显式标记 `REVIEW_EVIDENCE_MISSING`。
3. 禁止“凭感觉通过”或“只看代码不看证据”。

### 4) 发现分级与结论

发现项按严重级别分级：

- `P0`：阻断（必须修复）
- `P1`：高优先（建议阻断）
- `P2`：中优先（可跟进）
- `P3`：优化建议

结论类型：

1. `PASS`：可进入 `/jjk-verify` 或合并流程。
2. `CONDITIONAL_PASS`：存在非阻断项，需明确后续工单。
3. `BLOCKED`：存在阻断项，输出 `REVIEW_BLOCKER_FOUND` 并回退修复命令。

### 5) 产物回填与交接

必须输出审查报告：

- `docs/内部参考/迭代需求/review_report_<topic>.md`

最小内容：

1. 审查范围与输入映射（`task_id/card_id/pr_id`）
2. 发现清单（分级 + 证据 + 建议动作）
3. 结论（`PASS`/`CONDITIONAL_PASS`/`BLOCKED`）
4. 下一步建议命令（`/jjk-debug`、`/jjk-imp(-ws)`、`/jjk-verify`）

---

## 输出模板（推荐）

见全局模板：`${CODEX_HOME:-$HOME/.codex}/engineering/templates/jjk_review_templates.md`（`输出模板` 段）。
若本项目有覆盖规则，再查：`docs/内部参考/迭代需求/_templates/jjk_review_templates.md`。

## 禁止项（强制）

1. 禁止无映射输入（`task_id/pr_id`）直接给通过结论。
2. 禁止无证据支撑的“主观通过”。
3. 禁止发现阻断项后仍给 `PASS`。
4. 禁止把实现修复直接混入审查阶段提交。
5. 禁止忽略文档/测试同步影响。

## 推荐链路

`主链: /jjk-imp | /jjk-imp-ws | /jjk-wtimp -> /jjk-review -> /jjk-verify`

`可选分支: 需要远端 PR 交付时，先执行 /jjk-create-pr 再进入 /jjk-review`

## 使用示例

```text
/jjk-review
```

```text
/jjk-review @docs/内部参考/迭代需求/review_report_<topic>.md
```

---
*使用 `/jjk-review` 触发。目标是“有证据的审查结论”，不是形式化打勾。*
