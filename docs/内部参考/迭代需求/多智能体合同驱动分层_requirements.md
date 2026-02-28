# 多智能体合同驱动分层需求基线

> 文档日期：2026-02-28  
> 文档定位：将多智能体主图从“单文件混合编排”升级为“合同驱动分层编排”  
> 适用范围：`app/ai/workflow/**`（重点：`multi_agent_graph` 及其子图调用链）  
> 关联文档：
> - `docs/内部参考/迭代需求/多智能体完整交付架构重构_requirements.md`
> - `docs/内部参考/迭代需求/多智能体完整交付架构重构_implementation_plan.md`
> - `docs/内部参考/迭代需求/意图目标分解治理_requirements.md`

---

## 1. 背景与问题定义

当前多智能体链路已具备 Planner、Supervisor、专家子图、Coverage Gate、Final Composer 等能力，但在工程形态上仍存在单点耦合问题：

1. `multi_agent_graph` 体量过大，承担了路由、流式分发、合同补齐、覆盖率检查、最终答复渲染等多重职责。
2. 多问题请求（尤其包含子 agent handoff）时，执行层状态与交付层状态交叉，容易出现“执行完成但回复不稳”或“回复顺序与用户提问顺序不一致”。
3. 外部工具结果、专家文本、最终答案在同一编排上下文中混合处理，导致输出清洗策略分散，问题修复依赖局部补丁。
4. 现有结构增加新能力时，常需要同时修改多个远距离函数，回归成本高，定位根因慢。

结论：本问题属于**架构分层与状态契约不清**，不是单点 prompt 或单函数逻辑问题。

---

## 2. 目标与非目标

### 2.1 目标（In Scope）

1. 建立合同驱动五层编排：`Planner -> Router -> Subgraph -> Coverage -> Composer`。
2. 明确每层输入/输出合同（Contract），禁止跨层读写临时字段。
3. 将“执行正确”与“交付完整”解耦：执行层只产出结构化 deliverable，交付层统一收口。
4. 将多问题最终答复稳定在唯一出口（Composer），确保按 `intent_plan.order` 输出。
5. 形成可灰度、可回滚、可观测的迁移路径，避免一次性硬切。

### 2.2 非目标（Out of Scope）

1. 不在本期重写 todo/data 子图内部业务逻辑。
2. 不扩展新的业务域专家（仅重构编排层与合同层）。
3. 不变更前端整体消息框架，仅增量适配合同事件。

---

## 3. 方案选择（架构决策）

| 方案 | 优点 | 缺点 | 成本 | 推荐度 |
|---|---|---|---|---|
| 方案A：在现有主图继续局部补丁 | 上线快、改动小 | 耦合继续上升，回归风险累积，问题易反复 | 低 | ★★☆☆☆ |
| 方案B：合同驱动分层（Planner/Router/Subgraph/Coverage/Composer） | 彻底解决职责混叠，便于测试与灰度，符合长期演进 | 需要阶段迁移与契约治理 | 中 | ★★★★★ |
| 方案C：直接切换为全新 Swarm 主控 | 组织模型更灵活 | 改造面大、与现有链路兼容风险高 | 高 | ★★★☆☆ |

决策：采用**方案B**作为本期标准路径。

---

## 4. 目标架构（合同驱动分层）

### 4.1 分层调用链

```mermaid
flowchart LR
    U[User Prompt] --> P[Planner Layer\nintent_plan contract]
    P --> R[Router Layer\nroute_decision contract]
    R --> S[Subgraph Layer\nTodo/Data/External]
    S --> D[Deliverable Store\ndeliverables contract]
    D --> G[Coverage Gate\ncoverage_report contract]
    G --> C[Composer\nfinal_answer contract]
    C --> O[SSE final_answer + done]
```

### 4.2 层职责定义

1. Planner：只负责目标拆分与排序，不负责执行策略。
2. Router：只负责把目标映射到可委派目标集，不负责结果汇总。
3. Subgraph：只负责目标执行，输出标准化 deliverable，不直接生成最终结论。
4. Coverage：只负责 must_answer 覆盖判定与缺口反馈，不写用户可见正文。
5. Composer：唯一对外正文出口，负责按合同顺序渲染最终答复。

### 4.3 合同对象（强制）

1. `intent_plan`：`goal_id/order/kind/title/must_answer/allowed_agents/source/confidence`。
2. `route_decision`：`goal_id/target_agent/dispatch_reason/priority/blocked_by`。
3. `deliverable`：`goal_id/kind/status/summary/payload/error_code/evidence_ref`。
4. `coverage_report`：`pass/matched_goal_ids/missing_goals/failure_goals/checkpoint_at`。
5. `final_answer`：`content/coverage_pass/missing_goal_count/render_version`。

约束：

1. Subgraph 禁止直接写 `final_answer`。
2. Composer 禁止读取临时 handoff 字段，只读标准合同。
3. Coverage 结果为 Final Composer 的唯一准入门禁。

---

## 5. 功能需求（Functional Requirements）

### FR-01 Planner 合同化

1. Planner 必须输出完整 `intent_plan`，并为每个 goal 生成稳定 `goal_id`。
2. Planner 必须标注 `allowed_agents`，用于后续 Router 约束委派边界。
3. Planner 输出非法时允许 fallback，但 fallback 也必须满足合同字段齐全。

### FR-02 Router 可治理委派

1. Router 只能在 `allowed_agents` 范围内选择 target。
2. Router 必须输出 `route_decision`，并记录 `dispatch_reason`。
3. 当目标无法委派时，Router 必须返回结构化阻塞原因而非静默跳过。

### FR-03 Subgraph 交付物标准化

1. 每个子图执行完成后必须返回 `deliverable`，且绑定 `goal_id`。
2. 子图失败时必须填充 `error_code` 与 `summary`，禁止仅日志可见。
3. 子图可发过程事件，但不得作为最终用户结论。

### FR-04 Coverage Gate 门禁化

1. Coverage Gate 必须在每轮汇总前执行。
2. `must_answer` 未覆盖时，不得进入 `done` 完成态。
3. 缺失目标必须写入 `missing_goals`，并可驱动 Router 补齐。

### FR-05 Composer 唯一出口

1. Composer 按 `intent_plan.order` 生成最终答复。
2. 输出中不得暴露内部术语（如 `handoff`、`*_expert`、`assign_to_*`）。
3. `final_answer` 事件为用户正文唯一可信来源，`done` 仅作生命周期收口。

### FR-06 流式事件分层

1. 过程事件：`plan_ready/task_started/task_finished/coverage_check`。
2. 最终事件：`final_answer`。
3. 生命周期事件：`done`（仅 thread/message/final_content 等冻结字段）。

---

## 6. 验收标准（Acceptance Criteria）

### AC-01 多问题顺序一致性

1. 给定“先查待办，再看天气”与“先看天气，再查待办”两种输入，最终答复顺序必须分别匹配用户输入顺序。
2. 最终答复顺序不得受子图执行顺序影响。

### AC-02 覆盖完整性

1. `must_answer` 目标全部覆盖时，`coverage_report.pass=true`。
2. 存在缺口时，必须返回 `missing_goals`，且 `done` 不得提前结束。

### AC-03 子图失败可解释

1. 任一子图失败时，最终答复必须明确指出缺失目标与失败原因摘要。
2. 错误信息必须结构化可追溯（`goal_id` + `error_code`）。

### AC-04 输出纯净性

1. 用户可见文本不得包含内部调度术语。
2. 输出不得直接透传原始工具载荷（JSON/dict 长串）。

### AC-05 SSE 协议兼容

1. 新增事件字段不破坏现有前端消费。
2. `done` 冻结字段约束保持兼容。

### AC-06 稳定性与性能

1. 双目标复合请求端到端 P95 延迟增幅不超过现网基线 20%。
2. Coverage Gate 单次执行 P95 不超过 300ms。

---

## 7. 非功能需求（NFR）

1. 可维护性：编排层模块按职责拆分，单模块建议控制在 500 LOC 以内（超限需拆分）。
2. 可观测性：必须记录 `thread_id/run_id/goal_id/target_agent/coverage_pass`。
3. 可回滚性：保留旧路径开关，支持按租户/比例灰度。
4. 一致性：合同字段命名唯一，不允许同义别名并存。
5. 双库约束：新增持久化仅落 `chat_db`，`data_db` 继续只读。

---

## 8. 迁移策略（分阶段）

### Phase 1：合同抽离（不改行为）

1. 抽离合同定义与校验器。
2. 在现有链路旁路输出合同对象，开启影子校验。

### Phase 2：Router/Composer 收口

1. Router 改为严格消费 `allowed_agents`。
2. Composer 改为仅消费 `intent_plan + coverage_report + deliverables`。

### Phase 3：覆盖门禁硬切

1. 启用 Coverage Gate 强门禁。
2. 打通缺口补齐回路与回滚开关。

### Phase 4：旧路径下线

1. 删除跨层临时字段直读。
2. 清理冗余流程分支与重复汇总逻辑。

---

## 9. 风险与回滚

### 9.1 主要风险

1. 合同字段迁移期间，前后端事件口径可能短暂不一致。
2. Coverage 门禁过严会造成“可回答但被阻断”的体验。
3. 旧路径与新路径并行期，双写状态易发生偏差。

### 9.2 回滚策略

1. 保留 `delivery_orchestrator_v2` 级别开关，按租户快速回切。
2. Composer 支持降级到旧汇总模式（仅在紧急情况下启用）。
3. 所有阶段发布前必须完成回滚演练与验证记录。

---

## 10. 测试矩阵（需求追溯）

| 测试ID | 场景 | 期望 |
|---|---|---|
| TC-CDL-001 | 双目标复合请求（待办+天气） | `final_answer` 顺序与 `intent_plan.order` 一致 |
| TC-CDL-002 | 三目标复合请求（todo+data+external） | `must_answer` 全覆盖后才 done |
| TC-CDL-003 | 子图失败 | `coverage_report.pass=false` 且缺口可解释 |
| TC-CDL-004 | 过程事件重放 | 前端不重复渲染最终正文 |
| TC-CDL-005 | 旧客户端兼容 | 未消费新字段时不崩溃 |
| TC-CDL-006 | 回滚开关验证 | 30 秒内切回旧路径并恢复可用 |

---

## 11. 外部参考（GitHub）

1. `langgraph-supervisor-py`：Supervisor/多 agent 编排与输出模式（`output_mode`、handoff 消息控制）。
   - https://github.com/langchain-ai/langgraph-supervisor-py
2. `langgraph-swarm-py`：handoff 状态契约与多 agent 状态一致性要求。
   - https://github.com/langchain-ai/langgraph-swarm-py
3. `crewAI` `allowed_agents` 讨论与实现：委派范围治理实践。
   - https://github.com/crewAIInc/crewAI/pull/2068
4. `openai/swarm`：routines + handoffs 的编排思想参考。
   - https://github.com/openai/swarm

---

## 12. 完成定义（DoD）

1. AC-01 ~ AC-06 全部通过自动化验证并留存证据。
2. 新旧路径灰度运行至少 3 天，关键指标稳定。
3. `docs/SUMMARY.md` 已同步索引，`python3 scripts/docs_guard.py --strict` 通过。
4. 回滚演练完成，且有可复现操作记录。
