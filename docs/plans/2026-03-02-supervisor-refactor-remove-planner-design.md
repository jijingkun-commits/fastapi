# Supervisor 移除 Planner 设计说明

> 文档来源：基于 `docs/plans/2026-03-02-supervisor-refactor-remove-planner.md` 的设计桥接版本
> 创建时间：2026-03-03
> 用途：作为 `$jjk-plan` 的设计输入与审批锚点

## 1. 目标

将多智能体主链由“Planner + Supervisor 双决策层”重构为“Supervisor 单决策层”，并保持复合任务拆解、覆盖率校验与最终答复收口能力。

## 2. 设计结论

1. 图拓扑从 `preprocess -> planner -> supervisor` 改为 `preprocess -> supervisor`。
2. 目标状态从 `intent_plan` 迁移到 `decomposed_goals`。
3. Supervisor 按需执行目标拆解（`decompose_goals`），简单请求不做额外拆解。
4. `plan_ready` 事件采取“兼容期保留、最终下线”的双阶段策略。

## 3. 关键约束

1. 不改 `todo_expert` / `data_expert` 子图内部业务逻辑。
2. 不改数据库 schema。
3. 覆盖率门禁、最终收口、SSE 主链不可退化。

## 4. 审批记录

- design_approved: true
- approved_at: 2026-03-03 19:10
- approved_round: v1（用户在本轮明确触发 `$jjk-plan`）
