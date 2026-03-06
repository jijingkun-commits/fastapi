---
description: 兼容入口（已降级）：收到 /ask 时立即转入 /jjk-clarify
---

# Ask - 兼容入口（Deprecated）

`/ask` 已降级为历史兼容入口。  
默认工作流不再推荐使用它；收到 `/ask` 时，应在当前会话内立即转入 `/jjk-clarify`，由 `/jjk-clarify` 完成“探索 -> 冻结 -> 审批”的完整闭环。

## 定位

1. 只用于兼容历史习惯、旧文档或用户显式输入 `/ask`。
2. 不再作为独立主链阶段，不再维护独立的“探索快照 -> 再切换命令”流程。
3. 默认单一权威产物仍是 `design.md` 及其中的 `design_freeze_summary`、`clarify_handoff_contract`、`clarify_consistency_check`。

## 入口行为（强制）

1. 首句明确：`/ask` 已降级，当前将按 `/jjk-clarify` 继续。
2. 若需求模糊，在当前会话内先执行探索轮，但探索内容只服务于最终单方案冻结。
3. 禁止要求用户再手动切换 `/jjk-clarify`；兼容重定向应在命令内部完成。

## 输出与状态归属

1. 探索/冻结/审批状态统一归 `clarify_phase` 管理。
2. 默认不再产出独立 `brainstorm.md`。
3. 如用户明确要求保留探索记录，可附加非权威探索附录，但不得替代 `design.md`，且不得作为下游输入。

## 完成门禁（强制）

1. 必须落到 `/jjk-clarify` 的冻结门禁：`clarify_phase=approval`、`open_questions_count=0`。
2. 必须输出 `clarify_consistency_check`。
3. 任何进入 `/jjk-plan`、`/jjk-imp`、`/jjk-vkplan` 的行为，都以 `/jjk-clarify` 契约为准，而不是 `/ask` 自定义结果。

## 错误处理（强制）

1. 若执行中仍试图维护独立 `/ask` 状态或独立交接物，输出 `ASK_DEPRECATED_REDIRECT_REQUIRED` 并收敛回 `/jjk-clarify`。
2. 若用户只想讨论不想冻结，可停在探索轮，但必须明确“尚未形成可进入 `/jjk-plan` 的冻结设计”。

## 禁止项（强制）

1. 禁止把 `/ask` 写成默认推荐入口。
2. 禁止把 `/ask` 作为 `/jjk-plan`、`/jjk-imp`、`/jjk-vkplan` 的前置门禁。
3. 禁止新增长期依赖 `/ask` 的模板、脚本或文档链路。

*使用 `/ask` 触发时，目标不是继续扩展独立流程，而是兼容性地并入 `/jjk-clarify` 单指令闭环。*
