# Supervisor 移除 Planner 设计说明

## 0. Team 判定快照

- module_count: 7（workflow/state/contracts/events/chat_service/web types/tests）
- boundary_count: 3（AI-workflow、服务层SSE、前端类型契约）
- uncertainty_count: 3（目标合同迁移、SSE兼容策略、测试重构规模）
- estimated_file_count: 20+
- 判定结果: 命中条件 >= 2，采用 Team 并行调研（已完成 3 个子调研任务）

## 1. 需求澄清结论

- 目标:
  - 按方案A实施，移除 `planner` 节点，统一由 `supervisor` 完成意图识别/拆解/路由。
  - 消除 `intent_plan` 长期状态，改为 `decomposed_goals` 单一目标源。
  - 降低简单请求首字延迟，减少一层固定串行模型调用。
- 范围:
  - 变更 `app/ai/workflow/*`、`app/ai/state.py`、`app/ai/contracts/*`、`app/ai/events.py`、`app/services/chat_service.py`、`web/src/types/message.ts` 与相关测试。
- 边界:
  - 不改 `todo_expert` / `data_expert` 子图业务逻辑。
  - 不改数据库 schema。
  - 前端 UI 行为保持无感（仅类型/事件契约收敛）。
- 成功标准:
  - 图拓扑变为 `preprocess -> supervisor`。
  - 复合任务拆解能力保留，coverage/final 流程正确。
  - `intent_plan` 主流程引用清零，`decomposed_goals` 成为唯一合同。
  - `plan_ready` 最终下线，并完成灰度兼容与回收。

## 2. 方案对比（2-3个）

| 方案 | 优点 | 缺点 | 成本 | 推荐度 |
|---|---|---|---|---|
| A. 一步到位（本次目标） | 架构最干净，职责边界最清晰，长期维护成本最低 | 迁移面广，链路断裂风险高 | 高 | 高 |
| B. 双轨过渡（intent_plan+decomposed_goals 长期共存） | 风险较低，回滚容易 | 双合同长期并存，复杂度上升 | 中 | 中 |
| C. 仅修 Prompt 与路由规则（不删 planner） | 实施快，短期风险低 | 不能解决重复决策与性能损耗 | 低 | 低 |

## 3. 推荐方案与理由

- 推荐: **方案A（一步到位）+“短期兼容层”执行策略**。
- 理由:
  - 用户已明确要求按方案A实施；
  - 子调研结论一致：当前耦合点虽多，但可通过“先兼容、后删旧”顺序平滑迁移；
  - 兼容层仅作为迁移手段，不引入长期双轨负担。

## 4. 设计概要

- 架构:
  - 目标拓扑:

```text
START -> preprocess -> supervisor -> (todo_expert | data_expert | evaluate)
                               -> coverage_gate -> final_composer -> postprocess
```

  - 删除节点: `planner`
  - 新能力: `supervisor` 按需调用 `decompose_goals`

- 组件:
  - `state`:
    - 删除 `intent_plan`
    - 新增 `decomposed_goals: List[Dict[str, Any]]`
  - `workflow`:
    - 增加 `_resolve_active_goals(state)` 统一读取目标（兼容期可回退旧字段，最终仅读 `decomposed_goals`）
    - `router/coverage/final` 全链路改读统一目标函数
  - `contracts`:
    - 新增/替换 `decomposed_goals` 合同校验
    - 兼容期保留旧校验入口；最终移除 `IntentPlanContract`
  - `events + service`:
    - `plan_ready` 加独立兼容开关 `ENABLE_PLAN_READY_COMPAT`
    - 兼容期开启；最终态关闭并清理 `emit_plan_ready` 与 chat_service 分支

- 数据流:

```text
user_input
  -> preprocess(注入 system_context/current_todo_id)
  -> supervisor
      -> 简单请求: 直接响应/直连工具
      -> 复合请求: decompose_goals -> state.decomposed_goals
      -> 委派请求: assign_to_* -> router_guard（基于decomposed_goals.allowed_agents）
  -> evaluate / coverage_gate（基于_active_goals）
  -> final_composer
```

- 异常与测试考虑:
  - 结构化拆解失败时降级为单目标 `general.reply`，确保主链可继续。
  - `plan_ready` 迁移采用“双层开关”（事件生产层 + 转发层）避免半升级状态漏网。
  - 测试分层迁移：单元（策略/降级矩阵）-> 集成（node聚合）-> API（SSE契约）-> 回归矩阵。

## 5. 关键改造清单（按优先级）

### P0（必须）

1. `app/ai/state.py`: 增加 `decomposed_goals` 并接管主状态。
2. `app/ai/workflow/multi_agent_graph.py`:
   - 删除 `_planner_node` 节点接线；
   - 将目标初始化迁移到 `preprocess/supervisor` 前置；
   - `_build_router_dispatch_goal_queue`、`_apply_router_contract_guard`、`_dispatch_values_mode_chunk` 改读新目标源；
   - `coverage_gate/final` 全链路改读 `_resolve_active_goals`。
3. `app/ai/contracts/*`: 引入 `decomposed_goals` 校验合同并替换旧主入口。
4. `app/ai/events.py` + `app/services/chat_service.py`: `plan_ready` 兼容开关与最终下线路径。
5. `tests/**`: planner/intent_plan/plan_ready 相关测试迁移，保证双模式到最终态收敛。

### P1（建议）

1. 清理 planner 专属策略与降级死代码。
2. 收敛 `intent_mode/intent_shadow` 命名与语义（去 planner 化）。
3. 前端 `StreamEventType` 去除 `plan_ready` 类型残留。

## 6. 里程碑与交付

| 里程碑 | 交付物 | 验收 |
|---|---|---|
| M1 兼容层建立 | `decomposed_goals` 写入 + `_resolve_active_goals` | 主流程可运行，旧测试不大规模崩溃 |
| M2 主链切换 | router/coverage/final 全量切换 | 复合任务与选中待办场景通过 |
| M3 节点删除 | 图中移除 planner + 删除旧字段引用 | `intent_plan` 主流程引用清零 |
| M4 事件收敛 | `plan_ready` 兼容开关下线 | SSE 契约测试通过，最终态稳定 |

## 7. Team 交叉质检（抽检）

- 抽检比例: 1/3（33%，满足 >=20%）
- 抽检项: `plan_ready` 迁移结论
- 质疑点: “前端是否真的依赖 `plan_ready` 事件？”
- 验证命令:
  - `rg -n "plan_ready" web/src/lib/backend.ts web/src/hooks/useSSEStream.ts web/src/types/message.ts`
- 结论: 前端运行时未消费 `plan_ready`，仅类型层声明残留；迁移风险主要在后端SSE链路。

## 8. 未决问题（如有）

- [ ] 是否存在外部 SSE 消费方依赖 `plan_ready`（非 Web 前端）？
- [ ] `ENABLE_PLAN_READY_COMPAT` 默认开启时长（建议 1-2 个发布窗口）？
- [ ] `intent_mode/intent_shadow` 是否在本次一并收敛，还是拆为后续优化？

## 9. 审批记录

- design_approved: false
- approved_at: 
- approved_round: v1（待审批）
