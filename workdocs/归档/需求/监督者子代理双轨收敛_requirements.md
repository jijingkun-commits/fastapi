# 监督者子代理双轨收敛需求

> 日期：2026-03-01
> 状态：approved
> 主题：Supervisor 亲自处理主问题 + Subagent 处理子问题（A1 缺口策略）

## 1. 背景

当前多智能体链路在 planner 结构化阶段存在 tool_call -> json_object -> text_parse 串行回退，且复合问题场景中存在“委派后漏答可直接问题”的风险，导致首答时延高、完整性交付不稳定。

## 2. 用户故事

1. 作为用户，我在一轮里同时问主问题与子问题时，希望先拿到 Supervisor 的主问题结论。
2. 作为用户，当子问题由专家处理超时时，不希望主问题被阻塞。
3. 作为运维，我希望 planner 热路径只调用一次模型，失败直接走 heuristic，避免三段串行回退。

## 3. 范围

### 3.1 In Scope

1. Planner 默认禁用 tool_call 与 text_parse，主链路固定 json_object。
2. json_object 失败时直接 heuristic fallback。
3. Coverage Gate 支持 A1：仅子代理目标缺失时允许直接进入 final_composer。
4. 保留 Supervisor 在 handoff 前的直接可见回答，并纳入 deliverable。
5. 更新 Supervisor Prompt 的复合问题规则。

### 3.2 Out of Scope

1. 不引入新数据库表。
2. 不重构前端布局，仅沿用现有 final_answer 呈现。
3. 不做多 subagent 全并行编排（本轮限定 1+1 语义）。

## 4. 验收标准

1. 默认情况下 `_resolve_planner_structured_strategy` 返回 `legacy_json_object`。
2. 默认情况下 text_parse 不触发模型调用。
3. 子代理目标缺失且主目标已完成时，Coverage Gate 路由 `final_composer`。
4. `handoff_execution_trace` 含 `supervisor_excerpt` 时，`_build_delivery_artifacts` 产出 `general.reply` 交付物。
5. 关键单测全部通过（见 implementation plan 的 acceptance_cmds）。

## 5. 非功能要求

1. 变更保持 feature flag 可回滚。
2. 不破坏现有 SSE 事件类型与 done/result 兼容语义。
3. 关键路径新增逻辑应有单测覆盖。
