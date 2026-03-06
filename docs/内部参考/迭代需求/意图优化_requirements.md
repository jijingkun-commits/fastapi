# 意图优化需求文档（保留必要规划链路）

> 更新时间：2026-03-04  
> 上游设计：`docs/plans/意图优化.design.md`  
> 文档目标：定义 WHAT（需求合同、验收与追溯），供 `意图优化_implementation_plan.md` 承接

## 1. 业务目标与范围

### 1.1 用户故事

- 作为聊天用户，我希望询问“我的记忆/偏好/能力”时，系统不要误路由到数据专家。
- 作为产品运营，我希望误路由原因可观测，能快速定位是判定问题还是门禁问题。
- 作为研发，我希望在不破坏 `decompose_goals` 产能的前提下，收敛运行时路由语义。

### 1.2 范围

- 保留规划阶段中间契约（仅用于 `decompose_goals` 内部产出）。
- 运行阶段统一以 `decomposed_goals + target_agent` 进行路由与门禁。
- 兜底主体固定为 `supervisor`，专家节点不承担兜底职责。

### 1.3 非范围

- 本轮不删除 planner 旧策略链路（`model_primary/heuristic_only/shadow_metrics`）。
- 本轮不新增专家节点。
- 本轮不引入新的数据库依赖或跨库写入。

## 2. 机读需求合同（强制）

```yaml
requirements_contract:
  topic: "意图优化"
  status: "approved"
  design_source: docs/plans/意图优化.design.md
  clarify_handoff_source: docs/plans/意图优化.design.md#clarify_handoff_contract
  clarify_handoff_version: v1
  design_approved: true
  design_approval_evidence: "[$jjk-plan] 根据意图优化.design.md编写详细需求和计划"
  design_freeze_summary:
    design_actionable: true
    missing_blocks: []
    risk_level: medium
    blocked_by: []
    risk_counterexamples_count: 4
  owner: "ai-workflow"
  approver: "jijingkun"
  updated_at: "2026-03-04 21:52"
```

## 3. FR 合同矩阵（字段级）

```yaml
fr_contract_matrix:
  - fr_id: FR-01
    source_seed_ref: clarify_handoff_contract.requirement_seeds[0]
    user_value: 元信息与记忆类请求不误派发
    trigger: 用户请求命中能力/记忆/偏好语义
    input_contract:
      required_fields: [messages, semantic_user_query]
      source_of_truth: app/ai/workflow/multi_agent_graph.py::_resolve_semantic_user_query
    output_contract:
      required_fields: [decomposed_goals, pending_handoff]
      consumer: app/ai/workflow/multi_agent_graph.py::_dispatch_values_mode_chunk
    failure_semantics: 意图不清时先澄清，不得默认派发数据专家
    observability_fields: [event, turn_id, goal_id, reason]
    rollback_anchor: ENABLE_ROUTER_CONTRACT_GUARD=false（默认true）
    owner: ai-workflow

  - fr_id: FR-02
    source_seed_ref: clarify_handoff_contract.requirement_seeds[1]
    user_value: 规划阶段稳定产出目标集合，避免全量硬删回归
    trigger: 触发 decompose_goals 目标拆解
    input_contract:
      required_fields: [user_query, planner_mode]
      source_of_truth: app/ai/workflow/multi_agent_graph.py::_resolve_decomposed_goals_for_query
    output_contract:
      required_fields: [source, goals]
      consumer: app/ai/workflow/multi_agent_graph.py::decompose_goals
    failure_semantics: 模型失败触发 heuristic_fallback，不中断链路
    observability_fields: [planner_mode, source, fallback_hit_rate]
    rollback_anchor: intent_mode=heuristic_only（快速回退）
    owner: ai-workflow

  - fr_id: FR-03
    source_seed_ref: clarify_handoff_contract.requirement_seeds[2]
    user_value: 路由阻塞、覆盖缺口与异常统一由 supervisor 兜底
    trigger: 路由阻塞或覆盖率缺口出现
    input_contract:
      required_fields: [blocked_handoffs, missing_goals, runtime_error]
      source_of_truth: app/ai/workflow/multi_agent_graph.py
    output_contract:
      required_fields: [supervisor_fallback_activated, final_answer]
      consumer: final_composer
    failure_semantics: 兜底仅允许 supervisor 执行，不切换到专家兜底
    observability_fields: [event, turn_id, reason, missing_goal_ids]
    rollback_anchor: ENABLE_SUPERVISOR_FALLBACK_ONLY=true（保持开启）
    owner: ai-workflow

  - fr_id: FR-04
    source_seed_ref: derived.FR-04
    user_value: 运行态门禁判定单轨化
    trigger: values 模式 supervisor 分支执行
    input_contract:
      required_fields: [extracted_goals, runtime_goals]
      source_of_truth: app/ai/workflow/multi_agent_graph.py::_dispatch_values_mode_chunk
    output_contract:
      required_fields: [has_explicit_router_contract]
      consumer: app/ai/workflow/multi_agent_graph.py::_apply_router_contract_guard
    failure_semantics: 无显式合同时回退常规分发，不崩溃
    observability_fields: [router_contract_blocked_count]
    rollback_anchor: 回退 _dispatch_values_mode_chunk 变更
    owner: ai-workflow

  - fr_id: FR-05
    source_seed_ref: derived.FR-05
    user_value: 路由行为可观测且可追溯
    trigger: Router Gate block 或 coverage 计算完成
    input_contract:
      required_fields: [blocked_handoffs, coverage_report]
      source_of_truth: app/ai/workflow/multi_agent_graph.py
    output_contract:
      required_fields: [event, goal_id, target_agent, reason]
      consumer: metrics_and_logs
    failure_semantics: 事件字段缺失时降级记录最小事件，不影响主链路
    observability_fields: [router_handoff_blocked, coverage_result]
    rollback_anchor: 回退事件字段扩展
    owner: ai-workflow

  - fr_id: FR-06
    source_seed_ref: derived.FR-06
    user_value: 变更具备可执行验收与回归闭环
    trigger: 进入提测与发布门禁
    input_contract:
      required_fields: [implementation_tasks, acceptance_cmds]
      source_of_truth: docs/内部参考/迭代需求/意图优化_implementation_plan.md
    output_contract:
      required_fields: [test_report, readiness_status]
      consumer: release_gate
    failure_semantics: 任一关键用例失败即阻断发布
    observability_fields: [pytest_exit_code, failed_cases]
    rollback_anchor: 回退本轮代码与文档变更
    owner: ai-workflow
```

## 4. 验收标准

### 4.1 功能性验收（Happy Path）

- 输入“查一下我的永久记忆有哪些内容”，不进入数据专家。
- 输入“查询上月贷款余额”，允许进入数据专家。
- 输入“先查待办，再看我的记忆”，两个目标均被覆盖。

### 4.2 异常与边界验收

- handoff 缺失 `target_agent` 时，返回 `invalid_target_agent` 并触发 Supervisor 兜底。
- handoff 缺失 `task_description` 时，返回 `invalid_task_description` 并触发 Supervisor 兜底。
- 模糊输入“查询”时，优先澄清，不误派发。

### 4.3 NFR 验收（数字阈值）

- 路由门禁耗时：`P50 <= 30ms`，`P95 <= 150ms`。
- 规划回退率：`planner_model_failed <= 5%`。
- 误路由到数据专家比例：`<= 0.5%`。
- 异常恢复时长：`TTR <= 1` 回合。
- 配置回退生效时长：`<= 5min`。

## 5. 测试用例编号（TC）

- `TC-IO-01`：元信息请求不误派发。
- `TC-IO-02`：记忆请求不误派发。
- `TC-IO-03`：目标归一后 allowed_agents 正确。
- `TC-IO-04`：缺失 `target_agent` 阻塞并兜底。
- `TC-IO-05`：不在允许集的目标被阻塞。
- `TC-IO-06`：values 路径在单轨门禁下稳定运行。
- `TC-IO-07`：规划 fallback 事件可观测。
- `TC-IO-08`：覆盖率缺口由 Supervisor 补齐。
- `TC-IO-09`：端到端复合请求收口正确。

## 6. 追溯矩阵（机读）

```yaml
traceability_matrix:
  - design_item: D-01 运行态路由剥离共享状态旧字段
    fr_id: FR-01
    feature_id: P1-01
    task_id: T01
    tc_id: TC-IO-01
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_intent_layer_boundary.py -q
    evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md

  - design_item: D-02 规划链路保留并可回退
    fr_id: FR-02
    feature_id: P1-02
    task_id: T02
    tc_id: TC-IO-07
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_goal_planner_model_primary.py -q
    evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md

  - design_item: D-03 Router Gate 单轨门禁
    fr_id: FR-04
    feature_id: P1-03
    task_id: T03
    tc_id: TC-IO-05
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py -q
    evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md

  - design_item: D-04 values 分支合同收敛
    fr_id: FR-04
    feature_id: P1-04
    task_id: T04
    tc_id: TC-IO-06
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py -q
    evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md

  - design_item: D-05 可观测性事件闭环
    fr_id: FR-05
    feature_id: P1-05
    task_id: T05
    tc_id: TC-IO-08
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/integration/test_goal_shadow_metrics.py -q
    evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md

  - design_item: D-06 Supervisor 兜底固定
    fr_id: FR-03
    feature_id: P1-06
    task_id: T06
    tc_id: TC-IO-09
    acceptance_cmd_ref: cd /Users/jijingkun/bojxAI/fastapi && PYTHONPATH=. pytest tests/unit/test_supervisor_fallback_contract.py -q
    evidence_entry: docs/内部参考/迭代需求/意图优化_implementation_plan.md
```

