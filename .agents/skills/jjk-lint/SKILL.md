---
name: jjk-lint
description: "Use when you need `jjk-lint` in this repository. Source intent: 规范治理入口（消费 review/manifest）：按语言执行 lint/type 检查与可追溯修复，支持大范围自动 Team"
---
<!-- AUTO-GENERATED: jjk-skill-mirror -->
<!-- source: .cursor/commands/jjk-lint.md -->

# Lint 治理工作流 (Lint Workflow)

`$jjk-lint` 是 `jjk-*` 体系里的规范治理入口，负责在最小语义变更前提下修复代码规范、类型与静态检查问题。

> **中文主导**: 无论是思考过程还是最终输出，**永远使用中文**。

## 与 Superpowers / OMX 的分工（强制）

1. **Superpowers 调用契约**：
   `build-fix` 用于最小化修复构建/类型问题；`verification-before-completion` 用于证据先行验收。
2. **OMX Team 协作契约**：
   `team` 负责大规模文件分片执行与结果合并。
3. **`$jjk-lint` 主命令职责**：
   负责输入映射校验、lint 矩阵编排、自动修复边界控制、报告沉淀与下一步链路建议。

约束：

1. 仅保留上游 skill 的调用契约，禁止复制 skill 正文。
2. 本命令不承担架构重构，遇到结构性问题回退 `$jjk-refactor` 或 `$jjk-imp(-ws)`。
3. `$jjk-team-lint` 不再作为主入口，统一由 `$jjk-lint` 按规模自动升级 Team。

## 跨 IDE 调用方式

1. Cursor / Claude Code：`$jjk-lint`
2. Codex：`$jjk-lint`

> 说明：Codex 推荐显式调用 `$jjk-lint`。

## 模板来源优先级（跨项目，强制）

`$jjk-lint` 的模板按以下优先级读取：

1. 全局共享模板（默认主模板）：
   `/Users/jijingkun/.codex/engineering/templates/jjk_lint_templates.md`
2. 项目覆盖模板（仅放差异，不放全量复制）：
   `docs/内部参考/迭代需求/_templates/jjk_lint_templates.md`

若全局模板缺失，输出标记 `GLOBAL_TEMPLATE_MISSING` 并提示先初始化共享模板目录。
`GLOBAL_TEMPLATE_MISSING` 属于全局预检失败标记，可与命令级 `FAIL_FAST` 标记并存。

## 何时使用

| 场景 | 推荐命令 |
|---|---|
| 提交前执行 lint/type 检查并修复规范问题 | `$jjk-lint` ✅ |
| 代码语义或架构需大改 | `$jjk-refactor` 或 `$jjk-imp(-ws)` |
| 已出现运行时错误需调试 | `$jjk-debug` |
| 需要综合评审结论 | `$jjk-review` |

---

## 输入前置（强制）

至少提供以下输入之一：

1. 待处理路径（文件/目录）；
2. `pr_ready_manifest` / `pr_ready_manifest_ws`；
3. 相对 `main/master` 的 diff（含 `task_id` 映射，`pr_id` 可选）。

硬约束：

1. 无 `task_id` 追溯信息（`pr_id` 可选），`FAIL_FAST` 输出 `LINT_INPUT_INCOMPLETE`。
2. 未给定范围且无法从 diff 推断，`FAIL_FAST` 输出 `LINT_SCOPE_UNCLEAR`。
3. 关键工具链不可用且无降级方案，`FAIL_FAST` 输出 `LINT_TOOLCHAIN_UNAVAILABLE`。
4. 执行后无结果报告，`FAIL_FAST` 输出 `LINT_REPORT_MISSING`。

## 执行流程（强制顺序）

### 0) 先探索上下文（强制）

至少检查：

1. 技术栈与 lint/type 配置（Python/TypeScript/前端与后端差异）。
2. 本次改动边界、历史忽略规则与基线债务。
3. 可复用的验证命令与 CI 一致性要求。

### 0.5) 大范围治理自动启用 Team（强制判定）

触发条件（满足任一即可）：

1. 待处理文件 `>= 40`；
2. 同时覆盖 Python 与 TypeScript 且模块 `>= 3`；
3. 预计 lint 问题 `>= 30`；
4. 需要并行 worktree 或并行目录执行。

执行策略：

1. **有 Team 能力时**：按语言/目录并行执行，Leader 汇总统一报告。
2. **无 Team 能力时**：降级单代理执行，并输出 `TEAM_UNAVAILABLE_FALLBACK`。

### 1) 生成 lint 执行矩阵

1. 明确每类工具、目标范围、是否可自动修复。
2. 先执行无副作用检查，再执行自动修复。
3. 保证本地命令与 CI 命令口径一致。

### 2) 执行自动修复与人工补齐

1. 先处理格式、导入、明显类型问题等低风险项。
2. 对需人工修复项给出最小变更方案，禁止顺手做大改。
3. 若修复影响行为，必须在报告里标注并建议补测。

### 3) 回归验证

1. 至少重新执行相关 lint/type 检查。
2. 关键文件有语义调整时补充必要测试。
3. 无证据时标记 `LINT_EVIDENCE_MISSING`，不得宣称完成。

### 4) 报告产出与沉淀

必须产出：

- `docs/内部参考/迭代需求/lint_report_<topic>.md`

最小内容：

1. 输入映射（`task_id/pr_id|none`）
2. 执行矩阵（工具、范围、结果）
3. 自动修复与手动修复清单
4. 残留问题与阻塞项
5. 下一步建议命令

---

## 输出模板（推荐）

见全局模板：`/Users/jijingkun/.codex/engineering/templates/jjk_lint_templates.md`（`输出模板` 段）。
若本项目有覆盖规则，再查：`docs/内部参考/迭代需求/_templates/jjk_lint_templates.md`。

## 禁止项（强制）

1. 禁止通过关闭规则或扩大 ignore 列表掩盖问题。
2. 禁止把 lint 修复扩散为无关重构。
3. 禁止无验证证据给出“lint 已通过”结论。
4. 禁止复制 superpowers skill 正文到命令文档。
5. 禁止跳过报告直接结束流程。

## 推荐链路

`$jjk-deslop -> $jjk-lint -> $jjk-test -> $jjk-verify`

## 使用示例

```text
$jjk-lint
```

```text
$jjk-lint app/ web/
```

---
*使用 `$jjk-lint` 触发。目标是“最小语义变更的规范收敛 + 可追溯证据”。*
