# 监督者移除Planner重构需求

> 日期：2026-03-03  
> 状态：implemented（2026-03-04 已完成 T-10/T-11 收口）  
> 主题：Supervisor 单决策层重构（方案A）

## 1. 用户故事

1. 作为终端用户，我希望简单问题（如问候、单一查询）更快拿到首字回复，不被额外规划步骤拖慢。
2. 作为终端用户，我在一轮里提多个目标（例如“查待办再看天气”）时，系统仍能按顺序完整回答，不漏项。
3. 作为研发与运维，我希望多智能体决策层职责清晰，减少状态重复与排查复杂度。
4. 作为产品与质量负责人，我希望重构后可灰度、可回滚、可观测，不牺牲现有稳定性。

## 2. 背景与问题陈述

当前主链路为 `preprocess -> planner -> supervisor`，存在以下结构性问题：

1. 决策职责重叠：Planner 与 Supervisor 均承担意图识别。
2. 固定串行开销：每轮请求至少多一次规划调用。
3. 上下文利用断层：`current_todo_id` 等系统上下文在前置规划层未被充分利用。
4. 合同复杂度偏高：`intent_plan` 贯穿 router/coverage/final，改造难度与回归面增大。

## 3. 目标与非目标

### 3.1 目标（In Scope）

1. 删除独立 `planner` 节点，建立 `supervisor` 单决策层。
2. 将目标合同主状态从 `intent_plan` 迁移为 `decomposed_goals`。
3. 保持复合问题拆解能力与覆盖率门禁能力。
4. 完成 `plan_ready` 事件兼容期到最终下线的迁移闭环。
5. 补齐分层测试（unit/integration/api）与回滚策略。

### 3.2 非目标（Out of Scope）

1. 不改 `todo_expert` / `data_expert` 子图业务逻辑。
2. 不引入新数据库表或修改 `chat_db` / `data_db` schema。
3. 不调整前端 UI 样式，仅调整事件类型契约与测试口径。

## 4. 功能需求

### FR-01 主图拓扑重构

系统必须将多智能体主图改为 `preprocess -> supervisor`，并移除 `planner` 节点接线及其运行路径。

### FR-02 目标拆解并入 Supervisor

系统必须在 Supervisor 中按需触发目标拆解：
1. 简单请求不拆解；
2. 复合请求调用 `decompose_goals` 生成结构化 goals；
3. 拆解失败时降级为单目标 `general.reply`。

### FR-03 状态合同迁移

系统必须以 `decomposed_goals` 作为唯一目标状态源，并完成：
1. Router 门禁读取迁移；
2. Coverage 计算读取迁移；
3. Final Composer 输出读取迁移；
4. Postprocess 清理路径迁移。

### FR-04 路由与覆盖率一致性

系统必须保证在迁移后：
1. `allowed_agents` 门禁语义不变；
2. 复合任务缺口识别与补齐逻辑可用；
3. 最终答案仍以统一出口收口。

### FR-05 SSE 事件迁移

系统必须支持两阶段策略：
1. 兼容期：`ENABLE_PLAN_READY_COMPAT=true` 时继续输出 `plan_ready`；
2. 最终态：关闭兼容并彻底移除 `plan_ready` 相关代码与测试断言。

### FR-06 可观测与回滚

系统必须提供：
1. 目标计数字段可观测（初判/确认/缺口）；
2. 事件级与流程级回滚开关；
3. 失败后可在发布窗口内快速回退。

## 5. 非功能需求

1. **性能**：简单请求首字延迟较基线显著下降（以阶段基线测量为准）。
2. **稳定性**：不允许出现覆盖率链路中断、最终答复空收口。
3. **可维护性**：删除 `intent_plan` 主流程引用，避免双状态并存。
4. **可测试性**：关键链路必须有单测与 API 契约测试，避免仅靠手工验证。

## 6. 验收标准（含 TC 编号）

| 编号 | 场景 | 输入 | 期望结果 |
|---|---|---|---|
| TC-SRP-01 | 简单问候 | “你好” | 不触发拆解；直接回复；无异常委派 |
| TC-SRP-02 | 单目标待办 | “列出今天待办” | 直接委派 todo_expert，链路完整 |
| TC-SRP-03 | 复合请求 | “查待办，再看天气” | 生成 2 个 goals，顺序执行并统一收口 |
| TC-SRP-04 | 选中待办更新 | `current_todo_id=88` + “现在需要两页了” | 优先走待办 update，命中 todo_id=88 |
| TC-SRP-05 | 拆解失败降级 | 伪造 `decompose_goals` 异常 | 自动降级为 `general.reply`，不崩溃 |
| TC-SRP-06 | SSE 兼容期 | `ENABLE_PLAN_READY_COMPAT=true` | `plan_ready` 仍可见，字段归一化正确 |
| TC-SRP-07 | SSE 最终态 | `ENABLE_PLAN_READY_COMPAT=false` | 不再输出 `plan_ready`，其余事件正常 |
| TC-SRP-08 | 覆盖率门禁 | 构造未完成目标 | 缺口可识别并触发补齐或阻断 |
| TC-SRP-09 | 最终答案收口 | 多目标均完成 | `final_answer` 聚合准确，顺序与目标一致 |
| TC-SRP-10 | 回滚演练 | 关闭关键开关 | 服务可快速回到稳定路径 |

## 7. 边界与约束

1. 本需求为架构治理任务，优先强调运行场景与系统约束，不绑定银行业务域特定口径。
2. 双数据库边界不变：不新增任何 `chat_db`/`data_db` 访问路径。
3. 严禁临时硬编码分支掩盖路由缺陷，必须在正确层级修复。

## 8. 风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|---|---|---|---|
| 迁移期双状态混用 | 路由/覆盖率错乱 | 中 | 设立 `_resolve_active_goals` 统一入口，并逐步替换读路径 |
| `plan_ready` 提前移除 | 兼容消费方异常 | 中 | 双层开关灰度，先监控外部依赖再下线 |
| 测试口径老化 | 发布后回归 | 高 | 按 unit/integration/api 分层重写并纳入回归矩阵 |

## 9. 关联文档

1. 设计输入：`docs/plans/2026-03-02-supervisor-refactor-remove-planner-design.md`
2. 报告输入：`docs/plans/2026-03-02-supervisor-refactor-remove-planner.md`
3. 技术方案：`docs/内部参考/迭代需求/监督者移除Planner重构_implementation_plan.md`
