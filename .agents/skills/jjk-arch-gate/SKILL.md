---
name: jjk-arch-gate
description: "Use when you need `jjk-arch-gate` in this repository. Source intent: 架构门禁入口：任何改动前先提交模块边界/依赖方向/状态归属/错误处理责任四段式结论，并给出 GO/NO_GO 判定"
---
<!-- AUTO-GENERATED: jjk-skill-mirror -->
<!-- source: .cursor/commands/jjk-arch-gate.md -->

# 架构门禁工作流 (Architecture Gate)

`$jjk-arch-gate` 是 `jjk-*` 体系里的治理前置门禁，负责把“先想清楚再动手”固化为可执行输出，避免在未上线阶段用 patch、兼容层或 fallback 掩盖结构问题。

> **中文主导**：无论是思考过程（CoT）还是最终输出，**永远使用中文**。
>
> **原则来源**：`AGENTS.md` Layer1 第 `2/3/5` 条 + `.cursor/rules/core.mdc` 第 `6/7` 条。

## 输入前置（强制）

至少提供以下信息中的最小组合：

1. 明确改动意图（需求 / 缺陷 / 审查意见 / 重构目标）；
2. 影响范围（模块 / 文件 / 接口 / 状态字段 / 责任层）；
3. 任一上下文证据（`design.md` / `implementation_plan` / `review_report` / 变更文件列表）。

硬约束：

1. 缺少改动意图或影响范围，`FAIL_FAST` 输出 `ARCH_GATE_INPUT_INCOMPLETE`。
2. 未输出“模块边界、依赖方向、状态归属、错误处理责任”四段式结论，`FAIL_FAST` 输出 `ARCH_GATE_FOUR_SECTION_MISSING`。
3. 模块边界与依赖方向互相冲突，`FAIL_FAST` 输出 `ARCH_GATE_BOUNDARY_CONFLICT`。
4. 状态归属无法落到单一 owner 或存在多写入口，`FAIL_FAST` 输出 `ARCH_GATE_STATE_OWNER_UNCLEAR`。
5. 错误处理责任无法落到单一层级，`FAIL_FAST` 输出 `ARCH_GATE_ERROR_OWNER_UNCLEAR`。
6. 试图以 fallback、兼容层、重复分支、硬编码开关掩盖结构问题，`FAIL_FAST` 输出 `ARCH_GATE_STRUCTURAL_PATCH_FORBIDDEN`。
7. 涉及 `bugfix/refactor` 或替代旧职责但未输出 `shrink_contract`，`FAIL_FAST` 输出 `ARCH_GATE_SHRINK_CONTRACT_MISSING`。

## 执行流程（强制顺序）

### 0) 先探索上下文（强制）

补充执行约束：执行命令时统一遵循 `.cursor/rules/core.mdc` 的“命令执行拆分”规则：单步单目标、失败只重跑当前步、长任务只轮询不重启、输出截断时优先拆短当前步。

至少检查：

1. 当前变更影响哪些模块、上下游调用链与真理源；
2. 问题是否落在模块边界、依赖方向、状态归属、错误处理责任任一结构层；
3. 是否同时命中文档同步门禁、运行态验证门禁或 DB 证据门禁。

### 1) 产出四段式结论（强制）

必须按以下顺序输出：

1. **模块边界**：哪些模块该负责、哪些模块不该负责；
2. **依赖方向**：谁可以依赖谁，禁止的反向依赖是什么；
3. **状态归属**：状态/字段/缓存/会话信息由谁单写、谁只读；
4. **错误处理责任**：错误在何层拦截、转换、上抛、记录。

补充要求：

1. 每一段都必须同时写“当前问题 / 最终决策 / 禁止动作”；
2. 若任一段只能写成“待确认”，则不得放行到实现阶段；
3. 命中结构性问题时，必须显式写出“为什么应该 `refactor` 而不是 `patch`”。

### 2) 判定修复层级（强制）

1. 若问题只在局部文本/配置/注释层，且不影响四段式结论，可判定为 `patch`；
2. 若问题涉及结构、职责、状态流、错误流任一层，默认判定为 `refactor`；
3. 若问题本质是新增能力或新增契约，判定为 `new_feature`，并建议进入 `$jjk-plan`。

### 2.5) 冻结瘦身合同（`bugfix/refactor` / 职责替代强制）

1. 若结论属于 `bugfix/refactor`，或本次会以新实现替代旧职责，必须输出 `shrink_contract`。
2. `shrink_contract` 至少包含：`obsolete_paths`、`retained_paths`、`single_entry_owner`、`line_budget`。
3. `obsolete_paths` 为空时必须显式写 `none` 与原因，禁止省略。
4. 若新实现已覆盖旧职责，却仍计划保留旧路径且无唯一理由，`FAIL_FAST` 输出 `ARCH_GATE_OBSOLETE_PATH_UNCLEAR`。

### 3) 输出 Gate 结论（强制）

必须输出：

1. 四段式结论；
2. 根因层级（`module` / `dependency` / `state` / `error-handling` / `contract`）；
3. `Allowed Change Set`（允许动作）；
4. `Forbidden Change Set`（禁止动作）；
5. `GO/NO_GO` 结论；
6. `shrink_contract`（命中 `bugfix/refactor` 或职责替代时强制输出）；
7. `next_step`（仅限 `$jjk-plan`、`$jjk-imp`、`$jjk-refactor`、`$jjk-api-doc-sync` 之一或组合）。

放行规则：

1. `GO_PLAN`：需求或契约仍需冻结 / 拆解；
2. `GO_IMPL`：边界已清晰，可进入实现；
3. `GO_REFACTOR`：确认属于结构治理，应直接走重构链；
4. `NO_GO`：缺少输入、边界冲突、状态 owner 不清、错误责任未收口。

### 4) 文档与测试前置提醒（强制）

1. 若命中 API / Schema / Route / DTO / 接口语义变更，`next_step` 必须包含 `$jjk-api-doc-sync`；
2. 若命中运行态问题、端口问题、服务可用性问题，必须提醒后续补运行态校验；
3. 若命中 DB 风险任务，必须提醒后续链路补 `mandatory_evidence`。

## 输出模板（推荐）

至少包含以下标题：

1. `## 模块边界`
2. `## 依赖方向`
3. `## 状态归属`
4. `## 错误处理责任`
5. `## 根因层级`
6. `## Gate 结论`
7. `## 瘦身合同`
8. `## Next Step`

## 禁止项（强制）

1. 禁止跳过四段式结论直接给实现建议。
2. 禁止把结构性问题包装成“先 patch、后续再说”。
3. 禁止在状态 owner 未收敛时继续新增写入口。
4. 禁止用“看起来能跑”替代职责清晰。

## 推荐链路

`$jjk-clarify -> $jjk-arch-gate -> $jjk-plan`

`$jjk-review -> $jjk-arch-gate -> $jjk-refactor`

## 使用示例

```text
$jjk-arch-gate
```

```text
$jjk-arch-gate @docs/plans/2026-03-08-jjk-governance-skills-design.md
```

---
*使用 `$jjk-arch-gate` 触发。目标是“在动手前先把结构说清楚”，不是“先改出结果再事后解释”。*
