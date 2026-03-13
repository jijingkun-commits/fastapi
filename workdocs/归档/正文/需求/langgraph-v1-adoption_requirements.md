# langgraph-v1-adoption 需求文档

> 更新时间：2026-03-10
> 上游设计：`workdocs/归档/正文/设计/2026-03-09-langgraph-v1-adoption-design.md`

## 1. 规划结论

- 这次规划只解决 **LangGraph 后端依赖统一 + 预构建 Agent API 收口 + streaming/replay 契约守住** 三件事。
- 实施模式采用 `core/serial`：先锁依赖，再收口生产 Agent，再补测试与回归，最后评估能删掉哪些子图/持久化兜底逻辑。
- 不做 Functional API 全量重写，不引入 `langgraph-supervisor`，不升级前端 `@langchain/langgraph*`。

## 2. requirements_contract（机读）

```yaml
requirements_contract:
  topic: langgraph-v1-adoption
  status: approved
  design_source: workdocs/归档/正文/设计/2026-03-09-langgraph-v1-adoption-design.md
  design_approved: true
  design_approval_evidence: "用户明确指令：先帮我 /jjk-plan；将该指令视为对当前 LangGraph 单方案的正式确认。"
  clarify_handoff_source: workdocs/归档/正文/设计/2026-03-09-langgraph-v1-adoption-design.md#clarify_handoff_contract
  clarify_handoff_version: v2
  design_freeze_summary:
    design_actionable: true
    missing_blocks: []
    risk_level: medium
    risk_counterexamples_count: 4
    handoff_contract_ready: true
    product_contract_ready: true
    implementation_seed_count: 5
    semantic_frozen: true
    contract_source_decided: true
    handoff_seed_alignment_ok: true
    parallel_dependency_ready: true
    replay_canonical_field_set: true
    blocked_by: []
```

## 3. product_contract_matrix（PRD-Lite 承接）

```yaml
product_contract_matrix:
  target_users:
    - AI 工作流维护者
    - 后端开发者
    - QA / 验收人员
  core_scenarios:
    - 后端 LangGraph 版本统一，避免 pyproject 与 requirements 漂移
    - supervisor 与 knowledge_agent 收口到 create_agent
    - interrupt / resume / replay 语义不变
    - streaming wrapper 继续消费 messages / values / custom 三路输出
  business_goal_metrics:
    - 后端 LangGraph 版本漂移数=0
    - 生产路径 create_react_agent 引用数=0
    - interrupt/resume/replay 定向回归通过率=100%
    - streaming wrapper 三路分发定向回归通过率=100%
  non_goals:
    - 不升级前端 @langchain/langgraph / @langchain/langgraph-sdk
    - 不将 StateGraph 全量重写为 Functional API
    - 不引入 langgraph-supervisor 替换现有 supervisor 图
    - 不通过新增 fallback 掩盖 checkpointer busy 或 replay 结构问题
  acceptance_gates:
    - 版本安装解析通过，且 pyproject.toml 与 requirements.txt 保持一致
    - 生产路径不再依赖 create_react_agent
    - streaming wrapper 仍能消费 agent.astream(..., stream_mode=[messages, values, custom])
    - 结构化运行时元数据仍只写 additional_kwargs 命名空间
  release_constraints:
    - 仅在 codex/langgraph 分支实施
    - 文档先行，plan 与实现必须承接 design
    - 出现不兼容时走 Git 回退，不新增运行时开关层
```

## 4. fr_contract_matrix（字段级功能需求）

```yaml
fr_contract_matrix:
  - fr_id: FR-LG-01
    title: 后端 LangGraph 版本单源统一
    source_design_item: D-01
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[0]
    trigger: 开发者安装依赖或 CI 初始化 Python 运行时
    mapped_business_goal_metrics:
      - 后端 LangGraph 版本漂移数=0
    acceptance_gates:
      - 版本安装解析通过，且 pyproject.toml 与 requirements.txt 保持一致
    rollback_anchor: ENABLE_LANGGRAPH_1_0_10=true

  - fr_id: FR-LG-02
    title: 生产路径预构建 Agent 入口统一到 create_agent
    source_design_item: D-02
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[1]
    trigger: 构建 supervisor 或 knowledge_agent
    mapped_business_goal_metrics:
      - 生产路径 create_react_agent 引用数=0
    acceptance_gates:
      - 生产路径不再依赖 create_react_agent
      - prompt 与 system_prompt 参数语义完成收口
    rollback_anchor: ENABLE_CREATE_AGENT_MIGRATION=true

  - fr_id: FR-LG-03
    title: interrupt / resume / replay 与 streaming wrapper 契约稳定
    source_design_item: D-03
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[2]
    trigger: 图执行进入 interrupt / resume / replay 或 wrapper 事件分发
    mapped_business_goal_metrics:
      - interrupt/resume/replay 定向回归通过率=100%
      - streaming wrapper 三路分发定向回归通过率=100%
    acceptance_gates:
      - interrupt / resume / replay 语义不变
      - streaming wrapper 仍能消费 messages / values / custom 三路输出
      - 结构化运行时元数据仍只写 additional_kwargs 命名空间
    rollback_anchor: ENABLE_LANGGRAPH_REPLAY_CANONICAL=true

  - fr_id: FR-LG-04
    title: 子图持久化与手工预填充逻辑按证据收敛
    source_design_item: D-04
    source_seed_ref: clarify_handoff_contract.required.requirement_seeds[3]
    trigger: 迁移后评估现有 subgraph state 预填充与 checkpointer busy 兜底
    mapped_business_goal_metrics:
      - interrupt/resume/replay 定向回归通过率=100%
    acceptance_gates:
      - 仅在证据充分时删除冗余逻辑
      - 禁止通过新增 fallback 掩盖结构问题
    rollback_anchor: ENABLE_SUBGRAPH_PREFILL_CLEANUP=true
```

## 5. nfr_contract_matrix（数字阈值）

```yaml
nfr_contract_matrix:
  - nfr_id: NFR-LG-01
    title: 依赖一致性
    metric: 后端 LangGraph 版本漂移数
    threshold: 0
    scope: pyproject.toml + requirements.txt

  - nfr_id: NFR-LG-02
    title: Agent API 一致性
    metric: 生产路径 create_react_agent 引用数
    threshold: 0
    scope: supervisor + knowledge_agent

  - nfr_id: NFR-LG-03
    title: 流式协议稳定性
    metric: messages/values/custom 三路分发定向回归通过率
    threshold: 100
    unit: percent
    scope: streaming wrapper

  - nfr_id: NFR-LG-04
    title: 中断恢复稳定性
    metric: interrupt/resume/replay 定向回归通过率
    threshold: 100
    unit: percent
    scope: todo_graph + multi_agent_graph + chat_service

  - nfr_id: NFR-LG-05
    title: 回放字段约束
    metric: 新增消息顶层字段数
    threshold: 0
    scope: AIMessage replay / SSE / frontend normalizer
```

## 6. traceability_matrix（机读）

```yaml
traceability_matrix:
  - task_id: T-01
    feature_id: P1-langgraph-version-alignment
    fr_ids: [FR-LG-01]
    source_design_items: [D-01]
    business_goal_metrics: [后端 LangGraph 版本漂移数=0]
    acceptance_cmd_ref: "cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && /Users/jijingkun/bojxAI/fastapi/venv/bin/python -m pip install --dry-run 'langchain==1.0.8' 'langgraph==1.0.10' 'langchain-openai==1.0.3' 'langgraph-checkpoint-postgres>=2.0.0'"

  - task_id: T-02
    feature_id: P1-agent-api-convergence
    fr_ids: [FR-LG-02]
    source_design_items: [D-02]
    business_goal_metrics: [生产路径 create_react_agent 引用数=0]
    acceptance_cmd_ref: cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh app/tests/test_model_switch.py app/tests/test_complex_scenario.py -q

  - task_id: T-03
    feature_id: P1-test-and-example-convergence
    fr_ids: [FR-LG-02, FR-LG-03]
    source_design_items: [D-02, D-03]
    business_goal_metrics:
      - 生产路径 create_react_agent 引用数=0
      - streaming wrapper 三路分发定向回归通过率=100%
    acceptance_cmd_ref: cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh app/ai/test_stream_modes.py -q

  - task_id: T-04
    feature_id: P1-subgraph-persistence-cleanup
    fr_ids: [FR-LG-03, FR-LG-04]
    source_design_items: [D-03, D-04]
    business_goal_metrics:
      - interrupt/resume/replay 定向回归通过率=100%
    acceptance_cmd_ref: cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh app/tests/test_complex_scenario.py -q

  - task_id: T-05
    feature_id: P1-docs-and-regression
    fr_ids: [FR-LG-01, FR-LG-02, FR-LG-03, FR-LG-04]
    source_design_items: [D-01, D-02, D-03, D-04]
    business_goal_metrics:
      - 后端 LangGraph 版本漂移数=0
      - 生产路径 create_react_agent 引用数=0
      - interrupt/resume/replay 定向回归通过率=100%
      - streaming wrapper 三路分发定向回归通过率=100%
    acceptance_cmd_ref: cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && python3 scripts/check_workflow_contract.py --mode clarify_plan --requirements-path workdocs/归档/正文/需求/langgraph-v1-adoption_requirements.md --implementation-path workdocs/归档/正文/实施计划/langgraph-v1-adoption_implementation_plan.md --output workdocs/归档/报告/机读校验/langgraph-v1-adoption_clarify_plan_alignment.json
```
