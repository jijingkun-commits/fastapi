# 意图优化需求基线（decomposed_goals 单轨收敛）

> 文档日期：2026-03-04  
> 文档定位：将“记忆/元信息请求误路由到数据专家”的问题收敛为可执行需求合同  
> 上游设计输入：`docs/plans/意图优化.design.md`

---

## 1. 背景与问题定义

当前多智能体路由链路在意图判定与门禁层存在口径漂移，导致以下业务问题：

1. 用户询问“查一下我的永久记忆有哪些内容”“你有哪些能力”等元信息请求时，可能误入 `data_expert`。
2. 路由门禁在运行时仍兼容 `intent_plan`，与 `decomposed_goals` 双轨并存，决策一致性不足。
3. handoff 协议在实现与文档层存在字段口径差异（`target_agent` vs `agent`），增加误用风险。

本轮需求目标是：在不拆旧骨架（按评审约束不展开 planner 全量移除）的前提下，完成意图路由合同收敛，确保元信息/记忆请求稳定不误派发。

---

## 2. 目标、范围与边界

### 2.1 目标（Goal）

1. 元信息/记忆请求不再路由到 `data_expert`。
2. Router Gate 仅基于 `decomposed_goals` 与 `allowed_agents` 做门禁。
3. handoff 协议字段统一为 `target_agent`，阻塞原因可观测可追溯。
4. 路由能力回归后，既有 `todo.query` / `data.query` / `external.lookup` 不退化。

### 2.2 范围（In Scope）

1. `SUPERVISOR_PROMPT` 的元信息/记忆识别分支增强。
2. `_apply_router_contract_guard` 的合同门禁收敛。
3. `_dispatch_values_mode_chunk` 的运行时 `intent_plan` 读取清理。
4. 目标类型归一与 `allowed_agents` 映射一致性修正。
5. 单测/集成测试与文档同步。

### 2.3 非范围（Out of Scope）

1. 本轮不展开 `_infer_initial_intent_plan` / `_build_planner_intent_plan` 的全链路移除。
2. 不新增 `external_info_expert` 专家节点。
3. 不引入新的多专家路由框架。

---

## 3. 用户故事（User Stories）

### US-01（普通用户）

作为聊天用户，我希望当我询问“我的记忆”“我的偏好”“你有哪些能力”时，系统直接给出解释或澄清，而不是把我带入数据查询流程。

### US-02（产品/运营）

作为运营同学，我希望路由误判率下降，并能在日志里看到被门禁拦截的原因，便于快速定位误路由问题。

### US-03（研发）

作为研发，我希望路由合同字段统一，测试可覆盖，避免同类问题反复出现。

---

## 4. 功能需求（Functional Requirements）

### FR-01 元信息/记忆请求识别

系统必须在 Supervisor 决策中优先识别元信息/记忆类请求，并默认不委派 `data_expert`。

### FR-02 目标类型与允许委派归一

系统必须将 `meta.query` / `memory.query` / `external.lookup` 归一为“非专家委派目标”（`allowed_agents=[]`），仅 `todo.*` 与 `data.query` 允许专家委派。

### FR-03 Router Gate 合同门禁

Router Gate 必须使用 `_apply_router_contract_guard` 对 handoff 做目标合同校验，并统一读取 `target_agent` 字段。

### FR-04 运行时意图状态收敛

`_dispatch_values_mode_chunk` 必须移除运行时 `intent_plan` 读取，门禁启用条件仅依赖 `decomposed_goals` 相关状态。

### FR-05 可观测与原因码

路由阻塞必须记录 `goal_id`、`target_agent`、`reason`，覆盖率检查必须输出 `must_answer` 覆盖结果。

### FR-06 验收与回归闭环

必须通过单测、集成测试与手动回归清单证明该能力可用，且不破坏既有路由行为。

---

## 5. FR 合同矩阵（工单可执行）

```yaml
fr_contract_matrix:
  - fr_id: FR-01
    user_value: 元信息/记忆请求不再误入数据专家
    trigger: 用户输入包含“记忆/能力/偏好/系统元信息”等语义
    input_contract:
      required_fields: [messages, semantic_payload.user_query]
      source_of_truth: app/ai/workflow/multi_agent_graph.py::_resolve_semantic_user_query
    output_contract:
      required_fields: [decomposed_goals.kind, pending_handoff.target_agent]
      consumer: app/ai/workflow/multi_agent_graph.py::_dispatch_values_mode_chunk
    failure_semantics: 语义不确定时先澄清，不得直接委派 data_expert
    observability_fields: [goals_decomposed.kinds, router_handoff_blocked.reason]
    rollback_anchor: 回退 SUPERVISOR_PROMPT 对应增量片段
    owner: ai-workflow

  - fr_id: FR-02
    user_value: 目标类型与允许委派一致，避免假阳性委派
    trigger: decompose_goals 产出或规则归一触发 kind 规范化
    input_contract:
      required_fields: [decomposed_goals.kind, decomposed_goals.allowed_agents]
      source_of_truth: app/ai/workflow/multi_agent_graph.py::_normalize_active_goals
    output_contract:
      required_fields: [normalized_goals.kind, normalized_goals.allowed_agents]
      consumer: app/ai/workflow/multi_agent_graph.py::_build_router_dispatch_goal_queue
    failure_semantics: 非法/未知 kind 归一为 general.reply，且不专家委派
    observability_fields: [goals_decomposed.kinds]
    rollback_anchor: 回退 _normalize_model_goal_kind 与 _default_allowed_agents_for_goal_kind 变更
    owner: ai-workflow

  - fr_id: FR-03
    user_value: 错误委派被门禁拦截且可追踪
    trigger: supervisor 产生 handoff 批次
    input_contract:
      required_fields: [handoffs[].target_agent, active_goals[].allowed_agents]
      source_of_truth: app/ai/workflow/multi_agent_graph.py::_apply_router_contract_guard
    output_contract:
      required_fields: [accepted_handoffs, blocked_handoffs.reason, pending_goals]
      consumer: app/ai/workflow/multi_agent_graph.py::_dispatch_values_mode_chunk
    failure_semantics: target_agent 缺失记为 invalid_target_agent 并拦截
    observability_fields: [router_handoff_blocked.goal_id, router_handoff_blocked.target_agent, router_handoff_blocked.reason]
    rollback_anchor: ENABLE_ROUTER_CONTRACT_GUARD=false（默认 true）
    owner: ai-workflow

  - fr_id: FR-04
    user_value: 运行时门禁口径单一，减少双轨漂移
    trigger: values 模式 supervisor 分支处理 delta 消息
    input_contract:
      required_fields: [extracted_goals, final_state.decomposed_goals]
      source_of_truth: app/ai/workflow/multi_agent_graph.py::_dispatch_values_mode_chunk
    output_contract:
      required_fields: [has_explicit_router_contract]
      consumer: app/ai/workflow/multi_agent_graph.py::_apply_router_contract_guard
    failure_semantics: 无显式目标合同时退回现有常规分发，不崩溃
    observability_fields: [delivery_meta.router_contract_blocked_count]
    rollback_anchor: 回退 _dispatch_values_mode_chunk 相关改动
    owner: ai-workflow

  - fr_id: FR-05
    user_value: 线上可快速定位“为什么被拦截”
    trigger: Router Gate 发生 block 或 coverage 计算完成
    input_contract:
      required_fields: [blocked_handoffs, coverage_report]
      source_of_truth: app/ai/workflow/multi_agent_graph.py
    output_contract:
      required_fields: [event, goal_id, target_agent, reason, must_answer_count, missing_goals]
      consumer: 日志与监控系统
    failure_semantics: 缺字段时降级记录最小事件，不影响主链路
    observability_fields: [router_handoff_blocked, coverage_result]
    rollback_anchor: 关闭新增日志事件或回退事件字段扩展
    owner: ai-workflow

  - fr_id: FR-06
    user_value: 修复可验证且可回归
    trigger: 提交前 CI/本地验证执行
    input_contract:
      required_fields: [test_cases, acceptance_cmds]
      source_of_truth: tests/unit + tests/integration
    output_contract:
      required_fields: [test_report.pass_rate, regression_result]
      consumer: 评审与发布门禁
    failure_semantics: 任一关键用例失败则阻断交付
    observability_fields: [pytest_exit_code, failed_cases]
    rollback_anchor: 回退本轮改动并保留原测试基线
    owner: ai-workflow
```

---

## 6. 验收标准（Acceptance Criteria）

### 6.1 功能性（Happy Path）

1. 输入“查一下我的永久记忆有哪些内容”，不得路由 `data_expert`。
2. 输入“你有哪些能力”，由 Supervisor 直接回答或澄清。
3. 输入“查询上月贷款余额”，可正常路由 `data_expert`。
4. 输入“先查待办，再看我的记忆”，两个目标均被覆盖。

### 6.2 异常与边界

1. handoff 缺少 `target_agent` 时，返回 `invalid_target_agent` 阻塞原因。
2. 目标为空或不完整时，系统不崩溃并回退到可解释路径。
3. 输入“查询”这类模糊请求时，触发澄清而非误委派。

### 6.3 性能与稳定性

1. Router Gate 判定开销：`P95 < 50ms`。
2. 路由层异常率：`< 0.1%`（按日聚合）。
3. 目标覆盖率检查可用率：`>= 99.9%`。

---

## 7. 非功能需求（NFR）

### NFR-01 性能

1. route 判定增量耗时 `P50 < 20ms`、`P95 < 50ms`。
2. 不引入额外数据库写入路径（本轮仅逻辑与文档改造）。

### NFR-02 稳定性

1. 关键回归集通过率 `= 100%`（目标用例范围）。
2. 阻塞原因码覆盖率 `= 100%`（所有 blocked_handoffs 均有 reason）。

### NFR-03 可运维

1. `router_handoff_blocked` 事件缺失率 `< 1%`。
2. `coverage_result` 事件按轮可追溯率 `>= 99%`。

### NFR-04 安全与一致性

1. 不新增跨库写操作，`chat_db`/`data_db` 边界不变。
2. handoff 协议字段单一（`target_agent`），禁止双口径并存。

---

## 8. 测试追溯矩阵（TC 预留）

| TC 编号 | 对应需求 | 场景描述 | 预期结果 |
|---|---|---|---|
| TC-IO-01 | FR-01 | 记忆查询请求 | 不进入 `data_expert` |
| TC-IO-02 | FR-01 | 能力查询请求 | 直接回答或澄清 |
| TC-IO-03 | FR-02 | `meta.query` 归一 | `allowed_agents=[]` |
| TC-IO-04 | FR-03 | handoff 缺失 `target_agent` | 阻塞 reason=`invalid_target_agent` |
| TC-IO-05 | FR-03 | 目标不匹配 | 阻塞 reason=`target_not_in_allowed_agents` |
| TC-IO-06 | FR-04 | values 分支无 `intent_plan` 读取 | 门禁仍可正常启用 |
| TC-IO-07 | FR-05 | 路由拦截事件观测 | 事件字段完整 |
| TC-IO-08 | FR-06 | 数据查询请求 | 正常进入 `data_expert` |
| TC-IO-09 | FR-06 | 复合请求拆解 | 目标覆盖完整 |

---

## 9. 场景约束（架构迁移类）

1. 模块边界：策略归属 `Prompt + Workflow`，不得把同一策略散落到专家节点重复实现。
2. 状态契约：`decomposed_goals` 为运行时真理源，避免合同漂移。
3. 路由闭环：Supervisor 判定 -> Router Gate 校验 -> Coverage Gate 收口必须可追溯。
4. 回滚约束：优先通过开关或回退增量片段恢复，避免跨层临时补丁。

---

## 10. 设计到任务追溯矩阵（机读）

```yaml
traceability_matrix:
  - design_item: D-01 路由单一真理源
    fr_id: FR-03
    feature_id: P1-03
    task_id: T-03
    tc_id: TC-IO-05
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_router_contract_guard.py -q
    evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md

  - design_item: D-02 元信息/记忆请求防误路由
    fr_id: FR-01
    feature_id: P1-01
    task_id: T-01
    tc_id: TC-IO-01
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_supervisor_intent_prompt.py -q
    evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md

  - design_item: D-03 目标类型与 allowed_agents 对齐
    fr_id: FR-02
    feature_id: P1-02
    task_id: T-02
    tc_id: TC-IO-03
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_router_contract_guard.py -q
    evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md

  - design_item: D-04 values 运行时口径收敛
    fr_id: FR-04
    feature_id: P1-04
    task_id: T-04
    tc_id: TC-IO-06
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py -q
    evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md

  - design_item: D-05 可观测事件闭环
    fr_id: FR-05
    feature_id: P1-05
    task_id: T-05
    tc_id: TC-IO-07
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_observability.py -q
    evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md

  - design_item: D-06 测试与文档同步
    fr_id: FR-06
    feature_id: P1-06
    task_id: T-07
    tc_id: TC-IO-09
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/integration/test_intent_routing.py -q
    evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md
```

---

## 11. 机读合同与结论

```yaml
requirements_contract:
  topic: "意图优化"
  status: approved
  design_source: docs/plans/意图优化.design.md
  design_approved: true
  owner: ai-workflow
  approver: user-confirmed
  updated_at: "2026-03-04 18:50 CST"
```

本需求采用单一最终方案，不保留并行候选路径。
