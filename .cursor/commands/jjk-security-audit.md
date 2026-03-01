---
description: 安全审计入口（消费 review/manifest）：依赖+代码+配置+运行面多层审计并产出可执行修复清单
---

> 参考规则: @dual-database

# 安全审计工作流 (Security Audit)

`/jjk-security-audit` 是 `jjk-*` 体系里的安全审计入口，负责把安全风险识别、分级和修复建议沉淀为可执行交付物。

> **中文主导**: 无论是思考过程还是最终输出，**永远使用中文**。

## 与 Superpowers / OMX 的分工（强制）

1. `security-review`：提供代码级安全审查方法（威胁点与边界）。
2. `security-best-practices`：提供语言/框架安全最佳实践基线。
3. `verification-before-completion`：提供证据优先原则（无证据不宣称安全通过）。
4. `team`（OMX）：大范围审计并行执行与汇总。
5. `/jjk-security-audit`：负责输入映射校验、审计矩阵执行、风险分级、报告产出与回修建议。

约束：

1. 禁止在 `/jjk-security-audit` 复制上游 skill 正文；只保留调用契约与本地增强。
2. 禁止“发现漏洞后直接混入实现改码”；修复应回退 `/jjk-debug` 或 `/jjk-imp(-ws)`。
3. `/jjk-team-security-audit` 不再作为主入口，统一由 `/jjk-security-audit` 按规模自动升级 Team。

## 跨 IDE 调用方式

1. Cursor / Claude Code：`/jjk-security-audit`
2. Codex：`/prompts:jjk-security-audit`

> 说明：Codex 的自定义命令入口是 `/prompts:<name>`，不是 `/<name>`。

## 模板来源优先级（跨项目，强制）

`/jjk-security-audit` 的模板按以下优先级读取：

1. 全局共享模板（默认主模板）：
   `/Users/jijingkun/.codex/engineering/templates/jjk_security_audit_templates.md`
2. 项目覆盖模板（仅放差异，不放全量复制）：
   `docs/内部参考/迭代需求/_templates/jjk_security_audit_templates.md`

若全局模板缺失，输出标记 `GLOBAL_TEMPLATE_MISSING` 并提示先初始化共享模板目录。

## 何时使用

| 场景 | 推荐命令 |
|---|---|
| 发布前安全审计与风险分级 | `/jjk-security-audit` ✅ |
| 仅代码审查（非安全专项） | `/jjk-review` |
| 安全问题修复实施 | `/jjk-debug` 或 `/jjk-imp(-ws)` |
| 最终综合验收 | `/jjk-verify` |

---

## 输入前置（强制）

至少提供以下输入之一：

1. `review_report_<topic>.md`；
2. `pr_ready_manifest` / `pr_ready_manifest_ws`；
3. 可追溯本次改动的分支 diff（含 `task_id/pr_id` 对齐信息）。

硬约束：

1. 无 `task_id` 或 `pr_id` 追溯信息，`FAIL_FAST` 输出 `SECURITY_AUDIT_INPUT_INCOMPLETE`。
2. 审计范围无法确定（模块/文件/运行面），`FAIL_FAST` 输出 `SECURITY_AUDIT_SCOPE_UNCLEAR`。
3. 关键审计工具不可用且无替代路径，`FAIL_FAST` 输出 `SECURITY_AUDIT_TOOL_MISSING`。
4. 审计结束无证据清单（命令+结果），`FAIL_FAST` 输出 `SECURITY_AUDIT_EVIDENCE_MISSING`。

## 执行流程（强制顺序）

### 0) 先探索上下文（强制）

至少检查：

1. 变更范围与高风险边界（认证/授权/敏感数据/API/数据库/前端输入链路）。
2. 相关安全历史问题与豁免记录。
3. 环境与配置文件敏感项暴露风险。

### 0.5) 大范围审计自动启用 Team（强制判定）

触发条件（满足任一即可）：

1. 待审文件 `>= 30`；
2. 同时覆盖后端+前端+配置/基础设施三类；
3. 依赖审计 + 代码审计 + 运行面审计均需执行；
4. 风险点 `>= 10` 需并行归类。

执行策略：

1. **有 Team 能力时**：分层并行审计（依赖/代码/配置/运行面），Leader 汇总统一报告。
2. **无 Team 能力时**：降级单代理执行，并输出 `TEAM_UNAVAILABLE_FALLBACK`。

### 0.6) Team 交叉质检约束（新增，强制）

1. Team 模式下，每个成员提交阶段结果后，必须由另一名成员执行反方审查，至少包含：`1` 个质疑点、`1` 条验证命令、`1` 个通过/驳回结论。
2. `2` 人任务执行双向互审；`3+` 人任务执行环形互审（A 审 B，B 审 C，...，最后一人审 A）。
3. 未通过交叉审查的子任务不得标记完成；出现审查冲突时，必须创建复核子任务并附证据。
4. 阶段汇报至少包含：`结论`、`证据`、`剩余风险`。
5. 仅在 `pending=0`、`in_progress=0` 且交叉审查冲突清零后，才允许进入收尾或关停。

### 1) 依赖安全审计

按技术栈执行：

```bash
# Python
pip-audit
safety check

# Node.js
npm audit
```

规则：

1. 工具不存在时先记录缺失并尝试替代方案。
2. 禁止“盲目自动升级所有依赖”；必须给出有范围的修复建议。

### 2) 代码安全审计

重点检查：

1. 注入风险（SQL/命令注入）。
2. XSS/输出编码问题。
3. 认证与授权缺口。
4. 敏感信息泄露（日志/配置/硬编码密钥）。
5. 不安全反序列化/任意文件访问风险。

### 3) 配置与运行面审计

检查项：

1. `.env` 与密钥管理策略。
2. CORS/HTTPS/Rate Limit/错误信息暴露。
3. 数据库连接与备份保护策略。
4. 生产/开发配置隔离。

### 4) 风险分级与结论

风险分级：

- `S0`：阻断（必须修复后再交付）
- `S1`：高风险（强烈建议阻断）
- `S2`：中风险（可排期）
- `S3`：低风险（优化建议）

结论类型：

1. `PASS`：无 `S0/S1` 且关键检查通过。
2. `WARN`：无阻断但存在 `S2/S3`。
3. `FAIL`：存在 `S0` 或关键审计失败。

若存在 `S0`，必须输出 `SECURITY_AUDIT_FINDING_BLOCKER`。

### 5) 报告产出与回修建议

必须产出：

- `docs/内部参考/迭代需求/security_audit_report_<topic>.md`

最小内容：

1. 输入映射（`task_id/card_id/pr_id`）
2. 审计范围与执行命令证据
3. 风险清单（`S0-S3`）
4. 修复建议（按优先级）
5. 结论（PASS/WARN/FAIL）
6. 下一步命令建议（`/jjk-debug`、`/jjk-imp(-ws)`、`/jjk-verify`）

---

## 输出模板（推荐）

见全局模板：`/Users/jijingkun/.codex/engineering/templates/jjk_security_audit_templates.md`（`输出模板` 段）。
若本项目有覆盖规则，再查：`docs/内部参考/迭代需求/_templates/jjk_security_audit_templates.md`。

## 禁止项（强制）

1. 禁止无输入映射直接给“安全通过”结论。
2. 禁止无证据的主观风险判断。
3. 禁止在审计命令中直接执行破坏性修复。
4. 禁止将阻断漏洞降级为建议项。

## 推荐链路

`/jjk-review -> /jjk-security-audit -> /jjk-verify`

## 使用示例

```text
/jjk-security-audit
```

```text
/jjk-security-audit @docs/内部参考/迭代需求/review_report_<topic>.md
```

---
*使用 `/jjk-security-audit` 触发。目标是“可追溯安全结论 + 可执行修复清单”。*
