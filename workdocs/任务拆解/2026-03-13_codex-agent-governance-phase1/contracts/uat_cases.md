# Codex Agent 写法治理（阶段一）UAT 用例

> 适用范围：验证“以后 Codex 在本仓库怎么写 agent”的治理装配是否已经对人、对规则、对门禁同时可见。
> 对应实施计划：`workdocs/任务拆解/2026-03-13_codex-agent-governance-phase1/contracts/implementation_plan.md`

## UAT 总体说明

- 验收角色：AI 协作者、评审者、仓库维护者
- 验收方式：文档核对 + 规则核对 + 模板核对 + 轻量门禁执行
- 非目标：本轮不验证项目现有 agent 运行态是否已重构

## UAT Cases

### TC-01 默认简单优先

- 关联需求：`FR-01`、`FR-03`
- 关联任务：`T-01`、`T-03`
- 验收角色：评审者
- 前置条件：
  - `T-01` 已完成
  - `T-03` 已完成
- 用户操作：
  1. 阅读 `AGENTS.md`、`app/ai/AGENTS.md` 和 `.cursor/rules/agent_authoring.mdc`
  2. 以“请增加一个能查天气的 agent”为例检查默认策略
  3. 再查看 `jjk-review` 模板，确认复杂度升级需要证据
- 期望结果：
  - 默认建议先单 agent 或简单 workflow
  - 复杂度升级必须给出明确证据
  - 不会把“多 agent 更高级”当默认起点
- 证据：
  - `rg -n "复杂度升级|默认简单|单 agent|simple-first" AGENTS.md app/ai/AGENTS.md .cursor/rules/agent_authoring.mdc .cursor/commands/jjk-review.md`
- acceptance_cmd_ref:
  - `T-01.acceptance_cmds[0]`
  - `T-03.acceptance_cmds[0]`

### TC-02 关键词主路由被阻断

- 关联需求：`FR-04`
- 关联任务：`T-01`、`T-03`、`T-04`
- 验收角色：评审者
- 前置条件：
  - `T-01`、`T-03`、`T-04` 已完成
- 用户操作：
  1. 准备一段故意违规的设计描述，例如“在编排层新增 `TODO_HINTS`，通过关键词命中判断主意图”
  2. 查看 `.cursor/rules/agent_authoring.mdc` 和 `jjk-review` 模板
  3. 运行 agent governance 相关测试
- 期望结果：
  - 该方案会被标成 `keyword_primary_routing` 或等价 smell
  - 现有 `test_semantic_keyword_boundary_gate.py` 继续作为复用门禁，而不是被绕开
- 证据：
  - `rg -n "keyword_primary_routing|语义边界|guardrail" .cursor/rules/agent_authoring.mdc .cursor/commands/jjk-review.md`
  - `bash scripts/pytest_targeted.sh tests/unit/test_semantic_keyword_boundary_gate.py tests/unit/test_agent_governance_contract_docs.py`
- acceptance_cmd_ref:
  - `T-04.acceptance_cmds[0]`
  - `T-04.acceptance_cmds[1]`

### TC-03 规则分层对人可见

- 关联需求：`FR-05`
- 关联任务：`T-01`、`T-02`
- 验收角色：需求与设计人员
- 前置条件：
  - `T-01`、`T-02` 已完成
- 用户操作：
  1. 阅读 `docs/README.md`
  2. 对照 `AGENTS.md`、`app/ai/AGENTS.md`、`PLANS.md`
  3. 确认“什么规则放哪里”是否能一句话说清
- 期望结果：
  - 仓库级总则、局部高信号规则、Layer2 技术细则、长流程执行规则各归其位
  - 规范文档不再承载大段运行态架构说明
- 证据：
  - `rg -n "AGENTS.md|PLANS.md|app/ai/AGENTS.md|规则分层" docs/README.md docs/开发文档/规范/多智能体开发规范.md`
- acceptance_cmd_ref:
  - `T-01.acceptance_cmds[0]`
  - `T-02.acceptance_cmds[0]`

### TC-04 规则漂移能被自动发现

- 关联需求：`FR-06`
- 关联任务：`T-04`
- 验收角色：仓库维护者
- 前置条件：
  - `T-04` 已完成
- 用户操作：
  1. 查看 `.github/workflows/agent-governance-gate.yml`
  2. 运行 `tests/unit/test_agent_governance_contract_docs.py`
  3. 确认 workflow 触发路径覆盖规则、模板、文档和测试
- 期望结果：
  - 本地可以跑通轻量 drift gate
  - 规则、模板或 smell ID 关键标记缺失时能被阻断
- 证据：
  - `bash scripts/pytest_targeted.sh tests/unit/test_agent_governance_contract_docs.py`
  - `rg -n "agent-governance-gate|test_agent_governance_contract_docs" .github/workflows/agent-governance-gate.yml`
- acceptance_cmd_ref:
  - `T-04.acceptance_cmds[0]`
  - `T-04.acceptance_cmds[2]`

### TC-05 长期决策已沉淀

- 关联需求：`FR-02`、`FR-07`
- 关联任务：`T-05`
- 验收角色：仓库维护者
- 前置条件：
  - `T-05` 已完成
- 用户操作：
  1. 阅读 `memory-bank.md`
  2. 阅读 `docs/内部参考/决策记录.md`
  3. 确认阶段一主方案、取舍理由、影响范围和失效条件都能找到
- 期望结果：
  - `memory-bank.md` 有 ACTIVE 决策摘要
  - ADR 正文解释为什么采用“仓库级路由 + 局部覆盖 + Layer2 专项规则 + 门禁”
  - 不再只有 workdocs 过程文档知道这件事
- 证据：
  - `rg -n "Codex Agent 写法治理|agent authoring|复杂度升级" memory-bank.md docs/内部参考/决策记录.md`
- acceptance_cmd_ref:
  - `T-05.acceptance_cmds[0]`

## UAT 通过标准

1. 五条 UAT 用例全部通过。
2. 任意验收者都能明确回答：仓库级总则、局部 agent 规则、Layer2 技术细则、长流程规则分别放在哪里。
3. 任意验收者都能指出：哪些规则是 guardrail，哪些已经越界成主语义决策。
4. 任意验收者都能找到复杂度升级证据要求和真实任务样本要求。
