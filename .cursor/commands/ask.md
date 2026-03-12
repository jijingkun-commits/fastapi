---
description: 兼容入口（已降级）：收到 /ask 时立即转入 /jjk-clarify
---

# Ask - 兼容入口（Deprecated）

`/ask` 已降级为历史兼容入口。  
收到 `/ask` 时，应在当前会话内立即转入 `/jjk-clarify`，由 `/jjk-clarify` 完成“探索 -> 需求冻结 -> 审批”的闭环。

## 定位

1. 只用于兼容历史习惯、旧文档或用户显式输入 `/ask`；
2. 不再作为独立主链阶段；
3. 默认单一权威产物是 `requirements.md`，不是 `design.md`。

## 入口行为（强制）

1. 首句明确：`/ask` 已降级，当前将按 `/jjk-clarify` 继续；
2. 若需求模糊，可先在当前会话内做探索轮；
3. 禁止要求用户再手动切换 `/jjk-clarify`。

## 输出与状态归属

1. 探索/冻结/审批状态统一归 `/jjk-clarify` 管理；
2. 默认不再产出独立 `brainstorm.md`；
3. 探索记录不得替代 `requirements.md`，也不得作为下游真理源。

## 完成门禁（强制）

1. 必须落到 `/jjk-clarify` 的审批门禁；
2. 进入 `/jjk-design`、`/jjk-plan`、`/jjk-imp`、`/jjk-vkplan` 的行为，都以 `/jjk-clarify` 产出的 `requirements.md` 为准；
3. 若只想讨论不想冻结，可停在探索轮，但必须明确“尚未形成可进入 `/jjk-design` 的需求合同”。

## 禁止项（强制）

1. 禁止把 `/ask` 写成默认推荐入口；
2. 禁止把 `/ask` 作为 `/jjk-plan`、`/jjk-imp`、`/jjk-vkplan` 的前置门禁；
3. 禁止新增长期依赖 `/ask` 的模板、脚本或文档链路。

*使用 `/ask` 触发时，目标不是继续扩展独立流程，而是兼容性并入 `/jjk-clarify`。*
