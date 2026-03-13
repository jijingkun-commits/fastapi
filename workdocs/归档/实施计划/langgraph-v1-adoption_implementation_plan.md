# langgraph-v1-adoption 实施方案

> 更新时间：2026-03-10
> 上游设计：`workdocs/归档/设计/2026-03-09-langgraph-v1-adoption-design.md`
> 关联需求：`workdocs/归档/需求/langgraph-v1-adoption_requirements.md`

## 1. 实施概览

- 执行模式：`core`，按单主线串行推进，先锁依赖契约，再收口预构建 Agent API，最后做流式/回放回归与瘦身评估。
- 关键取舍：本轮不改 Graph 主架构，只处理 `LangGraph` 版本、`create_agent` 收口与 wrapper/persistence 契约；这样能把改动面压在最小必要范围。
- 成完成态：`implementation_ready=true`、`execution_contract_ready=true`，下一步直接进入 `$jjk-imp`。

## 2. implementation_tasks（机读）

```yaml
implementation_tasks:
  - task_id: T-01
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[0]
    feature_id: P1-langgraph-version-alignment
    phase: Phase-1
    change_type: modify
    owner: ai-workflow
    pr_id: PR-01
    risk_point: 依赖声明若只改一侧，会继续形成 pyproject 与 requirements 漂移
    rollback_point: revert:langgraph-version-alignment
    depends_on_tasks: [DESIGN-APPROVED]
    file_paths:
      - pyproject.toml
      - requirements.txt
    symbols:
      - project.dependencies.langgraph
      - requirements.langgraph
    risk_tags: [dependency_contract, install_contract]
    mandatory_evidence: [resolver_dry_run, version_drift_zero]
    acceptance_cmds:
      - cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && /Users/jijingkun/bojxAI/fastapi/venv/bin/python -m pip install --dry-run 'langchain==1.0.8' 'langgraph==1.0.10' 'langchain-openai==1.0.3' 'langgraph-checkpoint-postgres>=2.0.0'
      - cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && rg -n "langgraph==1.0.10" pyproject.toml requirements.txt

  - task_id: T-02
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[1]
    feature_id: P1-agent-api-convergence
    phase: Phase-2
    change_type: modify
    owner: ai-workflow
    pr_id: PR-02
    risk_point: supervisor 与 knowledge_agent 迁到 create_agent 时，若 prompt/system_prompt 或 handoff 工具语义不一致，会破坏主链
    rollback_point: revert:create-agent-convergence
    depends_on_tasks: [T-01]
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
      - app/ai/agents/knowledge_agent.py
      - app/ai/middleware.py
      - app/ai/agents/todo_agent.py
    symbols:
      - create_react_agent
      - create_agent
      - supervisor_agent
      - create_knowledge_agent
      - system_prompt
    risk_tags: [agent_contract, prompt_signature]
    mandatory_evidence: [agent_build_regression, api_surface_converged]
    acceptance_cmds:
      - cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh app/tests/test_model_switch.py app/tests/test_complex_scenario.py -q
      - cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && rg -n "create_agent\(|system_prompt=|create_react_agent" app/ai/workflow/multi_agent_graph.py app/ai/agents/knowledge_agent.py app/ai/middleware.py app/ai/agents/todo_agent.py

  - task_id: T-03
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[2]
    feature_id: P1-test-and-example-convergence
    phase: Phase-3
    change_type: modify
    owner: ai-workflow
    pr_id: PR-03
    risk_point: 测试脚本和示例若仍停留在旧 API，会让后续验证口径继续混乱
    rollback_point: revert:test-and-example-convergence
    depends_on_tasks: [T-02]
    file_paths:
      - app/ai/test_stream_modes.py
      - app/ai/test_tool_calls.py
      - app/ai/examples/advanced_agent_demo.py
    symbols:
      - create_react_agent
      - create_agent
      - test_stream_modes
      - test_simple_agent
    risk_tags: [test_contract, example_contract]
    mandatory_evidence: [stream_mode_contract, example_contract_green]
    acceptance_cmds:
      - cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh app/ai/test_stream_modes.py -q
      - cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && rg -n "create_agent\(|create_react_agent" app/ai/test_stream_modes.py app/ai/test_tool_calls.py app/ai/examples/advanced_agent_demo.py

  - task_id: T-04
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[3]
    feature_id: P1-subgraph-persistence-cleanup
    phase: Phase-4
    change_type: modify
    owner: ai-workflow
    pr_id: PR-04
    risk_point: 新版 persistence 与仓内手工 state 预填充叠加后，可能引发重复消息或 busy 误判
    rollback_point: revert:subgraph-persistence-cleanup
    depends_on_tasks: [T-02, T-03]
    file_paths:
      - app/ai/workflow/multi_agent_graph.py
      - app/services/chat_service.py
      - app/db/postgres_checkpoint.py
    symbols:
      - agent.aget_state
      - graph.aget_state
      - is_checkpointer_busy_error
      - _record_emitted_message_id
    risk_tags: [checkpoint_persistence, replay_contract]
    mandatory_evidence: [subgraph_replay_regression, busy_error_regression]
    acceptance_cmds:
      - cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh app/tests/test_complex_scenario.py -q
      - cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh app/ai/test_stream_modes.py -q

  - task_id: T-05
    source_seed_ref: clarify_handoff_contract.required.implementation_seeds[4]
    feature_id: P1-docs-and-regression
    phase: Phase-5
    change_type: modify
    owner: ai-workflow
    pr_id: PR-05
    risk_point: 若 design / requirements / implementation_plan / 回归门禁不同步，后续执行链会再次漂移
    rollback_point: revert:langgraph-plan-docs-and-gates
    depends_on_tasks: [T-01, T-02, T-03, T-04]
    file_paths:
      - workdocs/归档/设计/2026-03-09-langgraph-v1-adoption-design.md
      - workdocs/归档/需求/langgraph-v1-adoption_requirements.md
      - workdocs/归档/实施计划/langgraph-v1-adoption_implementation_plan.md
      - app/tests/test_complex_scenario.py
      - app/tests/test_model_switch.py
      - app/ai/test_stream_modes.py
    symbols:
      - design_freeze_summary
      - requirements_contract
      - implementation_tasks
      - implementation_readiness
    risk_tags: [docs_sync, regression_gate]
    mandatory_evidence: [clarify_plan_alignment, temporal_gate_clean, docs_guard_clean]
    acceptance_cmds:
      - cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && python3 scripts/check_workflow_contract.py --mode clarify_plan --requirements-path workdocs/归档/需求/langgraph-v1-adoption_requirements.md --implementation-path workdocs/归档/实施计划/langgraph-v1-adoption_implementation_plan.md --output workdocs/归档/机读校验/langgraph-v1-adoption_clarify_plan_alignment.json
      - cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && python3 scripts/check_workflow_contract.py --mode planning_temporal_gate --implementation-path workdocs/归档/实施计划/langgraph-v1-adoption_implementation_plan.md --output workdocs/归档/机读校验/langgraph-v1-adoption_planning_temporal_gate.json
      - cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && python3 scripts/docs_guard.py --strict
```

## 3. planning_contract（含 task_to_pr_mapping，机读）

```yaml
planning_contract:
  task_to_pr_mapping:
    - task_id: T-01
      pr_id: PR-01
      pr_branch: codex/langgraph-v1-adoption-pr-01
      pr_subject: 后端 LangGraph 版本单源统一
      pr_depends_on: []
      acceptance_cmds:
        - cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && /Users/jijingkun/bojxAI/fastapi/venv/bin/python -m pip install --dry-run 'langchain==1.0.8' 'langgraph==1.0.10' 'langchain-openai==1.0.3' 'langgraph-checkpoint-postgres>=2.0.0'
      rollback_point: revert:langgraph-version-alignment

    - task_id: T-02
      pr_id: PR-02
      pr_branch: codex/langgraph-v1-adoption-pr-02
      pr_subject: 生产路径预构建 Agent API 收口
      pr_depends_on: [PR-01]
      acceptance_cmds:
        - cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh app/tests/test_model_switch.py app/tests/test_complex_scenario.py -q
      rollback_point: revert:create-agent-convergence

    - task_id: T-03
      pr_id: PR-03
      pr_branch: codex/langgraph-v1-adoption-pr-03
      pr_subject: 测试与示例 API 口径收口
      pr_depends_on: [PR-02]
      acceptance_cmds:
        - cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh app/ai/test_stream_modes.py -q
      rollback_point: revert:test-and-example-convergence

    - task_id: T-04
      pr_id: PR-04
      pr_branch: codex/langgraph-v1-adoption-pr-04
      pr_subject: subgraph persistence 与 replay 收敛评估
      pr_depends_on: [PR-02, PR-03]
      acceptance_cmds:
        - cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh app/tests/test_complex_scenario.py -q
      rollback_point: revert:subgraph-persistence-cleanup

    - task_id: T-05
      pr_id: PR-05
      pr_branch: codex/langgraph-v1-adoption-pr-05
      pr_subject: 文档与门禁报告收口
      pr_depends_on: [PR-01, PR-02, PR-03, PR-04]
      acceptance_cmds:
        - cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && python3 scripts/check_workflow_contract.py --mode clarify_plan --requirements-path workdocs/归档/需求/langgraph-v1-adoption_requirements.md --implementation-path workdocs/归档/实施计划/langgraph-v1-adoption_implementation_plan.md --output workdocs/归档/机读校验/langgraph-v1-adoption_clarify_plan_alignment.json
        - cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && python3 scripts/check_workflow_contract.py --mode planning_temporal_gate --implementation-path workdocs/归档/实施计划/langgraph-v1-adoption_implementation_plan.md --output workdocs/归档/机读校验/langgraph-v1-adoption_planning_temporal_gate.json
      rollback_point: revert:langgraph-plan-docs-and-gates
  execution_mode: serial
  card_order: [C01, C02, C03, C04, C05]
  strict_single_active_card: true
  cards:
    - card_id: C01
      title: 依赖版本统一
      feature_ids: [P1-langgraph-version-alignment]
      depends_on: []
      done_gate: [T-01 done]
      acceptance_checks:
        - cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && /Users/jijingkun/bojxAI/fastapi/venv/bin/python -m pip install --dry-run 'langchain==1.0.8' 'langgraph==1.0.10' 'langchain-openai==1.0.3' 'langgraph-checkpoint-postgres>=2.0.0'
      risk_tags: [dependency_contract, install_contract]
      mandatory_evidence: [resolver_dry_run, version_drift_zero]
    - card_id: C02
      title: 生产 Agent API 收口
      feature_ids: [P1-agent-api-convergence]
      depends_on: [C01]
      done_gate: [T-02 done]
      acceptance_checks:
        - cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh app/tests/test_model_switch.py app/tests/test_complex_scenario.py -q
      risk_tags: [agent_contract, prompt_signature]
      mandatory_evidence: [agent_build_regression, api_surface_converged]
    - card_id: C03
      title: 测试与示例收口
      feature_ids: [P1-test-and-example-convergence]
      depends_on: [C02]
      done_gate: [T-03 done]
      acceptance_checks:
        - cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh app/ai/test_stream_modes.py -q
      risk_tags: [test_contract, example_contract]
      mandatory_evidence: [stream_mode_contract, example_contract_green]
    - card_id: C04
      title: subgraph persistence 收敛
      feature_ids: [P1-subgraph-persistence-cleanup]
      depends_on: [C02, C03]
      done_gate: [T-04 done]
      acceptance_checks:
        - cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh app/tests/test_complex_scenario.py -q
      risk_tags: [checkpoint_persistence, replay_contract]
      mandatory_evidence: [subgraph_replay_regression, busy_error_regression]
    - card_id: C05
      title: 文档与门禁收口
      feature_ids: [P1-docs-and-regression]
      depends_on: [C01, C02, C03, C04]
      done_gate: [T-05 done]
      acceptance_checks:
        - cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && python3 scripts/check_workflow_contract.py --mode clarify_plan --requirements-path workdocs/归档/需求/langgraph-v1-adoption_requirements.md --implementation-path workdocs/归档/实施计划/langgraph-v1-adoption_implementation_plan.md --output workdocs/归档/机读校验/langgraph-v1-adoption_clarify_plan_alignment.json
        - cd /Users/jijingkun/.codex/worktrees/31a0/fastapi && python3 scripts/check_workflow_contract.py --mode planning_temporal_gate --implementation-path workdocs/归档/实施计划/langgraph-v1-adoption_implementation_plan.md --output workdocs/归档/机读校验/langgraph-v1-adoption_planning_temporal_gate.json
      risk_tags: [docs_sync, regression_gate]
      mandatory_evidence: [clarify_plan_alignment, temporal_gate_clean, docs_guard_clean]
```

## 4. execution_contract（机读）

```yaml
execution_contract:
  preferred_mode: core
  execution_contract_ready: true
  delivery_mode: staged
  execution_unit: all_tasks
  commit_policy: single_commit
  stop_boundary: none
  temporal_gate_forbidden: true
  context_verified: true
  design_source: workdocs/归档/设计/2026-03-09-langgraph-v1-adoption-design.md
  requirements_source: workdocs/归档/需求/langgraph-v1-adoption_requirements.md
```

## 5. implementation_readiness（机读）

```yaml
implementation_readiness:
  implementation_ready: true
  execution_contract_ready: true
  requirements_ready: true
  traceability_ready: true
  blocking_issue_count: 0
  readiness_note: approved_design_and_hydrated_tasks
```
