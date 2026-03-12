---
description: 架构门禁入口：在进入设计或重构前冻结模块边界、依赖方向、状态归属与错误处理责任
---

# 架构门禁工作流（Architecture Gate）

`/jjk-arch-gate` 是轻量前置门禁：当你需要在正式出 `design.md` 前先判断结构方向是否合理时使用。


## 输入前置（强制）

至少提供：

1. 改动意图（需求 / 缺陷 / 审查意见 / 重构目标）；
2. 影响范围；
3. 任一上下文证据（`requirements.md` / `design.md` / `review_report` / 变更文件列表）。

失败时：

1. 缺少改动意图：`ARCH_GATE_INPUT_INCOMPLETE`
2. 四段式结论缺失：`ARCH_GATE_FOUR_SECTION_MISSING`
3. shrink contract 缺失：`ARCH_GATE_SHRINK_CONTRACT_MISSING`

## 执行流程（强制顺序）

### 1) 产出四段式结论

必须按顺序输出：

1. `模块边界`
2. `依赖方向`
3. `状态归属`
4. `错误处理责任`

每段都要写：当前问题 / 最终决策 / 禁止动作。

### 2) 冻结收口合同

必须输出：

1. `obsolete_paths`
2. `retained_paths`
3. `single_entry_owner`
4. `line_budget`

### 3) Gate 结论

必须输出：

1. `GO_DESIGN`：可进入 `/jjk-design`
2. `GO_REFACTOR`：可进入 `/jjk-refactor`
3. `NO_GO`：输入或边界仍不完整

### 4) 文档提醒

1. 命中 API 变化时，后续必须进入 `/jjk-api-doc-sync`；
2. 命中结构变更时，后续应进入 `/jjk-design`，而不是直接 `/jjk-plan`。

## 推荐链路

`/jjk-clarify -> /jjk-arch-gate -> /jjk-design`

`/jjk-review -> /jjk-arch-gate -> /jjk-refactor`

---
*使用 `/jjk-arch-gate` 触发。目标是“先把结构判清楚”，不是“替代正式设计文档”。*
