# Agent Governance Real Task Eval

> 主题：Codex Agent 写法治理（阶段一）
> 目的：用真实任务表达验证当前 rule pack 能否识别本次要治理的坏味道，而不是只靠单条 happy path 或口头判断。

## 评测口径

- eval_type: manual_rule_coverage_check
- manual_eval_verdict: pass
- sample_source: 来自本轮需求、设计和用户原始抱怨中的真实任务表达
- smell_ids_checked:
  - multi_decider_stack
  - keyword_primary_routing
  - dual_truth_design
  - speculative_fallback
  - missing_eval_evidence

## Cases

### EC-01

- input: 请增加一个能查天气的 agent
- expected_result:
  - simple-first
  - 不默认新增多层 planner/router
  - 不命中 `multi_decider_stack`
- actual_rule_coverage:
  - `app/ai/AGENTS.md` 明确要求默认先单 agent 或简单 workflow
  - `.cursor/rules/agent_authoring.mdc` 要求复杂度升级先给证据
- verdict: pass

### EC-02

- input: 为了稳妥，我想加 planner -> router -> supervisor 三层去判定用户意图
- expected_result:
  - 命中 `multi_decider_stack`
  - 需要复杂度升级证据
- actual_rule_coverage:
  - `.cursor/rules/agent_authoring.mdc` 已定义 `multi_decider_stack`
  - `jjk-review` 模板已要求显式检查该 smell
- verdict: pass

### EC-03

- input: 在 router 层加一个 TODO_HINTS，通过关键词命中判断主路由
- expected_result:
  - 命中 `keyword_primary_routing`
  - 降级为 guardrail 或 extraction only
- actual_rule_coverage:
  - `app/ai/AGENTS.md` 和 `.cursor/rules/agent_authoring.mdc` 都明确禁止关键词主路由
  - 现有 `test_semantic_keyword_boundary_gate.py` 继续作为硬门禁复用
- verdict: pass

### EC-04

- input: 先保留 intent_plan、task_description、frame 三条语义来源，后面再慢慢删
- expected_result:
  - 命中 `dual_truth_design`
  - 需要收口到唯一真相状态
- actual_rule_coverage:
  - `.cursor/rules/agent_authoring.mdc` 已把 `dual_truth_design` 定义为阻断项
  - `jjk-review` / `jjk-verify` 都要求显式消费该 smell
- verdict: pass

### EC-05

- input: 这套 agent 方案更稳了，但我还没准备真实任务样本，先按这个走
- expected_result:
  - 命中 `missing_eval_evidence`
  - 默认不能给 PASS
- actual_rule_coverage:
  - `.cursor/rules/agent_authoring.mdc` 已要求 real-task eval first
  - `jjk-verify` 已新增 `real_task_eval_verified` 和 `missing_eval_evidence`
- verdict: pass

## 总结

1. 本次阶段一规则装配已经覆盖用户明确指出的两类核心坏味道：过度流程设计、关键词判主语义。
2. 当前评测是 manual rule coverage check，不是运行真实模型的离线 benchmark。
3. 下一阶段如果进入项目现有 agent 运行态重构，应把这五条 case 扩成可执行回归集，而不是只保留手工覆盖检查。
