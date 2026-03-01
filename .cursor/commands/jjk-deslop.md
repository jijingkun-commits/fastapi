---
description: 去冗余入口（消费 review/manifest）：清理 AI 风格冗余实现并产出可追溯报告，支持大范围自动 Team
---

# 去冗余工作流 (Deslop Workflow)

`/jjk-deslop` 是 `jjk-*` 体系里的去冗余入口，负责在不改变业务语义的前提下清理 AI 风格冗余代码并沉淀证据。

> **中文主导**: 无论是思考过程还是最终输出，**永远使用中文**。

## 与 Superpowers / OMX 的分工（强制）

1. **Superpowers 调用契约**：
   `code-review` 提供冗余识别框架；`verification-before-completion` 提供“先证据后结论”校验原则。
2. **OMX Team 协作契约**：
   `team` 负责大范围并行扫描与汇总，避免单代理漏检。
3. **`/jjk-deslop` 主命令职责**：
   负责输入映射校验、清理计划执行、风险约束、报告产出与下一步链路建议。

约束：

1. 仅保留上游 skill 的调用契约，禁止复制 skill 正文。
2. 发现功能缺陷时回退 `/jjk-debug` 或 `/jjk-imp(-ws)`，本命令不承担业务修复。
3. `/jjk-team-deslop` 不再作为主入口，统一由 `/jjk-deslop` 按规模自动升级 Team。

## 跨 IDE 调用方式

1. Cursor / Claude Code：`/jjk-deslop`
2. Codex：`/prompts:jjk-deslop`

> 说明：Codex 的自定义命令入口是 `/prompts:<name>`，不是 `/<name>`。

## 模板来源优先级（跨项目，强制）

`/jjk-deslop` 的模板按以下优先级读取：

1. 全局共享模板（默认主模板）：
   `/Users/jijingkun/.codex/engineering/templates/jjk_deslop_templates.md`
2. 项目覆盖模板（仅放差异，不放全量复制）：
   `docs/内部参考/迭代需求/_templates/jjk_deslop_templates.md`

若全局模板缺失，输出标记 `GLOBAL_TEMPLATE_MISSING` 并提示先初始化共享模板目录。
`GLOBAL_TEMPLATE_MISSING` 属于全局预检失败标记，可与命令级 `FAIL_FAST` 标记并存。

## 何时使用

| 场景 | 推荐命令 |
|---|---|
| 提交前清理 AI 冗余注释/防御性分支/滥用转换 | `/jjk-deslop` ✅ |
| 已发现功能缺陷需先修复 | `/jjk-debug` 或 `/jjk-imp(-ws)` |
| 仅做规范修复（不做冗余识别） | `/jjk-lint` |
| 需要综合评审结论 | `/jjk-review` |

---

## 输入前置（强制）

至少提供以下输入之一：

1. `review_report_<topic>.md`；
2. `pr_ready_manifest` / `pr_ready_manifest_ws`；
3. 相对 `main/master` 的 diff（含 `task_id`，`pr_id` 可选追溯信息）。

硬约束：

1. 缺少 `task_id`（`pr_id` 可选），`FAIL_FAST` 输出 `DESLOP_INPUT_INCOMPLETE`。
2. 无法确定清理范围（模块/文件/语言），`FAIL_FAST` 输出 `DESLOP_SCOPE_UNCLEAR`。
3. 缺少可核验基线（审查结论或验证命令），`FAIL_FAST` 输出 `DESLOP_BASELINE_MISSING`。
4. 执行结束无清理报告，`FAIL_FAST` 输出 `DESLOP_REPORT_MISSING`。

## 执行流程（强制顺序）

### 0) 先探索上下文（强制）

至少检查：

1. 当前变更范围、模块边界、状态契约与外部接口。
2. 冗余热点：重复注释、过度防御分支、无意义 `try/except`、`as any` 滥用、风格漂移。
3. 已有验证证据（测试、类型检查、构建）与可复用命令。

### 0.5) 大范围清理自动启用 Team（强制判定）

触发条件（满足任一即可）：

1. 待处理文件 `>= 25`；
2. 同时覆盖后端+前端两端且模块 `>= 3`；
3. 候选冗余点 `>= 15`；
4. 需要并行 worktree 或并行目录验证。

执行策略：

1. **有 Team 能力时**：按语言或模块并行清理，Leader 汇总统一报告。
2. **无 Team 能力时**：降级单代理执行，并输出 `TEAM_UNAVAILABLE_FALLBACK`。

### 1) 建立清理清单

1. 以“保持语义等价”为第一约束，逐项标记可清理点与风险级别。
2. 必须记录每个候选点的文件位置、类型与预期收益。
3. 禁止把真实业务分支误判为冗余直接删除。

### 2) 执行去冗余改造

1. 删除无信息增量注释和重复日志包装。
2. 清理已由上游契约保证的防御性分支与无意义异常捕获。
3. 将 `any`/宽泛类型转换收敛为可验证类型定义。
4. 保持对外 API、错误码、数据契约不变。

### 3) 变更验证与回归

1. 至少执行与改动相关的 lint/type/test 验证。
2. 每个失败项必须记录命令、退出码、摘要与归因。
3. 缺少证据时标记 `DESLOP_EVIDENCE_MISSING`，不得宣称清理完成。

### 4) 报告产出与沉淀

必须产出：

- `docs/内部参考/迭代需求/deslop_report_<topic>.md`

最小内容：

1. 输入映射（`task_id/pr_id|none`）
2. 清理清单（删除/替换/保留项）
3. 验证证据（命令与结果）
4. 风险与回滚提示
5. 下一步建议命令

---

## 输出模板（推荐）

见全局模板：`/Users/jijingkun/.codex/engineering/templates/jjk_deslop_templates.md`（`输出模板` 段）。
若本项目有覆盖规则，再查：`docs/内部参考/迭代需求/_templates/jjk_deslop_templates.md`。

## 禁止项（强制）

1. 禁止以“去冗余”为名混入功能改造。
2. 禁止删除与安全、权限、数据一致性相关的真实防护逻辑。
3. 禁止无验证证据给出“清理完成”结论。
4. 禁止复制 superpowers skill 正文到命令文档。
5. 禁止跳过报告直接结束流程。

## 推荐链路

`/jjk-review -> /jjk-deslop -> /jjk-lint -> /jjk-test`

## 使用示例

```text
/jjk-deslop
```

```text
/jjk-deslop @docs/内部参考/迭代需求/review_report_<topic>.md
```

---
*使用 `/jjk-deslop` 触发。目标是“语义不变的去冗余 + 可追溯证据”。*
