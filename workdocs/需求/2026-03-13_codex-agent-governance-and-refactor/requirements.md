# Codex Agent 写法治理需求（阶段一）

本次只解决第一步：让 Codex 以后在本仓库写 agent 时，不再默认走过度流程设计、双轨兼容和关键词判主语义这条老路。现在先做这件事，是因为项目尚未上线，先把“默认怎么写”定对，后续无论是新需求还是重构，都会省掉大量返工。最直接受影响的是后续所有 AI 协作者、代码审查者和需求设计人员。做完后，团队会先看到一件事：Codex 在 agent 相关任务里，默认会先给更简单、contract-first、少启发式的方案，而不是一上来堆 planner、router 和 fallback。

## 业务流程图

```mermaid
flowchart LR
    A["问题暴露：Codex 默认把 agent 写复杂"] --> B["先核验官方最佳实践"]
    B --> C["冻结默认写法原则"]
    C --> D["写入需求合同与坏味道口径"]
    D --> E["建立评审与验收门禁"]
    E --> F["后续 agent 需求默认先走简单、可解释、可评测方案"]
```

这张图回答的是“第一步到底只做什么”。最关键的一步是“先核验官方最佳实践”，因为这件事不是靠个人偏好定规则；最容易歧义的一步是范围边界，本次只收口 Codex 的默认写法，不进入项目现有 agent 的重构设计。

## 最佳实践核验摘要

本需求以官方或一手资料为依据，当前先冻结以下判断：

1. OpenAI 官方建议先把单 agent 用到位，再在确有收益时升级多 agent；同时强调把主语义理解和执行护栏分开。[A practical guide to building agents](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)
2. OpenAI 官方建议对 agent 节点之间使用 typed inputs / outputs 和结构化 contract，减少下游自由猜测和自由文本传播。[Agent Builder](https://platform.openai.com/docs/guides/agent-builder)
3. OpenAI 官方在 agent 安全指南中明确建议使用 structured outputs 约束数据流，并把 guardrails 与主行为控制分开。[Safety in building agents](https://platform.openai.com/docs/guides/agent-builder-safety)
4. OpenAI 官方对 Codex 的 `AGENTS.md` 指南强调：全局规则、仓库规则、目录覆盖应分层加载，且更具体的目录规则应更靠近实际工作路径。[Custom instructions with AGENTS.md](https://developers.openai.com/codex/guides/agents-md)
5. OpenAI 官方关于 `PLANS.md` 的 cookbook 建议：复杂实现流程应通过 `AGENTS.md` 明确何时使用 `PLANS.md`，不要把所有长流程混进常驻规则。[Using PLANS.md for multi-hour problem solving](https://developers.openai.com/cookbook/articles/codex_exec_plans)
6. Anthropic 官方建议能用工作流解决的问题，就不要过早上复杂自治 agent；只有复杂度真的带来效果时，才值得升级架构。[Building effective agents](https://www.anthropic.com/research/building-effective-agents/)
7. Anthropic 官方建议评测先从 20 到 50 个真实任务开始，先覆盖高频和高风险失败模式，再把改动交给评测验证，而不是靠直觉补规则。[Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)

## requirements_contract

```yaml
topic: codex_agent_governance_phase1
problem_statement:
  - Codex 在编写 agent 时，容易默认引入过多流程层、控制分支、兼容双轨和关键词语义判断。
business_goals:
  - bg_id: BG-01
    goal: 让 Codex 在后续 agent 相关任务中默认产出更简单、contract-first、少启发式的方案。
  - bg_id: BG-02
    goal: 让团队能用评测和门禁，而不是靠主观经验，判断 agent 设计是否退化。
primary_users:
  - AI 协作者
  - 评审者
  - 需求与设计人员
success_definition:
  - 后续 agent 需求默认先出简单方案，再证明复杂度必要性。
  - Codex 默认把语义理解交给结构化 contract，把 guardrail 留给护栏层，而不是再堆关键词主路由。
  - agent 设计的优劣能通过明确门禁和评测被观察到。
```

## product_contract_matrix

| bg_id | 业务目标 | 当前痛点 | 用户看到的变化 | 成功判定 |
|---|---|---|---|---|
| BG-01 | 治理 Codex 的默认写法 | 每次新需求都可能重新长出 planner、keyword router、双轨 fallback | Codex 先给简单方案，先说明为什么不该复杂化 | 新 agent 需求评审中，不再把“多层流程 + 关键词判语义”当默认起点 |
| BG-02 | 建立评测与门禁 | 发现一个问题就补一条规则，系统越补越脆 | 改动前后可对比，审查不再全靠经验 | 每次 agent 相关需求或设计变更都有最小评测和明确阻断条件 |

## fr_contract_matrix

```yaml
- fr_id: FR-01
  scenario_id: S-01
  user_value: AI 协作者在开始设计 agent 前，就知道什么是默认允许、什么是默认禁止的写法。
  trigger: 出现新的 agent 需求、agent 重构需求，或 Codex 被要求设计新编排逻辑时。
  input_contract:
    required_fields: [目标问题, 使用场景, 是否必须多 agent, 是否涉及语义路由]
    optional_fields: [历史失败案例, 现有痛点样本]
  output_contract:
    required_fields: [默认设计原则, 禁止模式, 复杂度升级条件]
  failure_semantics: 若缺少明确默认规则，需求评审必须标记为未收敛，禁止直接进入设计。
  acceptance_story: 评审者能在开工前判断“这个方案是不是又开始堆流程和关键词规则”。
  linked_business_goals: [BG-01]

- fr_id: FR-02
  scenario_id: S-01
  user_value: 团队能要求 Codex 在做 agent 决策前，先核验官方最佳实践，再给出判断依据。
  trigger: 任何新增或大改 agent 行为的需求进入澄清阶段时。
  input_contract:
    required_fields: [需求目标, 影响范围]
    optional_fields: [候选方案, 已知坏味道]
  output_contract:
    required_fields: [最佳实践核验摘要, 采用原因, 不采用原因]
  failure_semantics: 若方案没有最佳实践依据，只能视为个人偏好，不得作为默认做法固化。
  acceptance_story: 需求文档中能直接看到“为什么先单 agent、为什么不用关键词判主语义、为什么要结构化 contract”。
  linked_business_goals: [BG-01, BG-02]

- fr_id: FR-03
  scenario_id: S-01
  user_value: 复杂方案只有在简单方案被证明不够时才会被接受，避免 Codex 一上来过度设计。
  trigger: 候选方案包含额外决策层、额外 agent、额外 fallback 或新增语义规则时。
  input_contract:
    required_fields: [简单方案说明, 复杂方案说明, 升级理由]
    optional_fields: [试验结果, 历史对照]
  output_contract:
    required_fields: [复杂度升级门槛, 必要性证据, 拒绝条件]
  failure_semantics: 若复杂度升级没有证据，默认退回简单方案。
  acceptance_story: 新方案不能再只靠“以后可能会用到”来给复杂结构找理由。
  linked_business_goals: [BG-01, BG-02]

- fr_id: FR-04
  scenario_id: S-01
  user_value: 审查者和 AI 协作者能明确区分“主语义决策”和“护栏/抽取规则”，避免 Codex 再把关键词判定写进编排层。
  trigger: 方案中出现关键词词表、正则词表、substring 命中，且它们参与主意图识别、任务分解或主路由时。
  input_contract:
    required_fields: [候选规则, 所在层级, 作用说明]
    optional_fields: [格式抽取样例, 安全校验样例]
  output_contract:
    required_fields: [职责边界判定, 是否允许, 替代写法]
  failure_semantics: 若关键词或正则继续承担主语义决策职责，方案评审必须阻断。
  acceptance_story: 评审者能清楚指出哪些规则是护栏，哪些已经越界变成“伪语义理解”。
  linked_business_goals: [BG-01]

- fr_id: FR-05
  scenario_id: S-01
  user_value: Codex 写 agent 时，能优先通过仓库级规则、目录级规则和执行计划文档被约束，而不是只靠一次对话提醒。
  trigger: 需要把默认写法固化进长期协作规则时。
  input_contract:
    required_fields: [仓库级规则入口, 目录级覆盖点, 长流程入口]
    optional_fields: [历史规则痛点, 试点目录]
  output_contract:
    required_fields: [规则承载分层, 适用范围, 升级与覆盖关系]
  failure_semantics: 若所有规则仍混在单一长文中，后续约束容易失效或再次膨胀。
  acceptance_story: 团队能明确回答“什么规则放 AGENTS.md，什么规则放目录覆盖，什么流程放 PLANS.md”。
  linked_business_goals: [BG-01]

- fr_id: FR-06
  scenario_id: S-01
  user_value: Codex 写法是否退化，可以被及时发现，而不是等坏模式重新长出来才发现。
  trigger: agent 相关需求澄清、设计评审或规则修改发生时。
  input_contract:
    required_fields: [真实任务样本, 关键失败模式, 预期行为]
    optional_fields: [历史回归 case, 复杂度对照]
  output_contract:
    required_fields: [最小评测集, 门禁规则, 回归判断口径]
  failure_semantics: 若改动没有配套评测，不能宣称“已经变简单”或“已经更稳”。
  acceptance_story: 评审者能看到这次规则或方案是否减少过度流程、减少启发式、提高一致性。
  linked_business_goals: [BG-02]

- fr_id: FR-07
  scenario_id: S-01
  user_value: 审查者和 AI 协作者对“什么叫坏味道”有统一口径，不再每次靠吵架定。
  trigger: 需求、设计、实现、审查任一阶段涉及 agent 写法判断时。
  input_contract:
    required_fields: [坏味道清单, 审查问题单]
    optional_fields: [反例, 正例]
  output_contract:
    required_fields: [统一审查清单, 阻断条件, 例外条件]
  failure_semantics: 若没有统一口径，同一类坏味道会反复以不同名字回流。
  acceptance_story: 不同评审者对“是否过度流程设计”能得出基本一致的判断。
  linked_business_goals: [BG-01, BG-02]
```

## nfr_contract_matrix

```yaml
- nfr_id: NFR-01
  dimension: 简洁性
  requirement: 新增 agent 方案默认决策层级不超过两层；若超过，必须在评审材料中说明复杂度收益和替代方案为何不足。
  observable_signal: 方案文档可直接数出决策层级，并能看到复杂度升级理由。

- nfr_id: NFR-02
  dimension: 规则分层
  requirement: 仓库级默认规则、目录级覆盖规则和长流程执行规则必须分层承载，不得把所有内容混成一个常驻长文。
  observable_signal: 评审与设计材料中能明确看到 AGENTS.md、目录覆盖和 PLANS.md 的职责划分。

- nfr_id: NFR-03
  dimension: 语义边界
  requirement: 编排层新增主语义关键词词表数量必须等于 0；关键词、正则和 substring 仅允许用于护栏、格式抽取和安全校验。
  observable_signal: 审查材料和自动门禁中，restricted path 下无新增语义词表违规项。

- nfr_id: NFR-04
  dimension: 可验证性
  requirement: 每次 agent 相关规则或方案调整都必须至少覆盖一组真实任务评测，初始规模建议从 20 到 50 个真实样本起步，并持续补高频失败案例。
  observable_signal: 需求、设计或验收材料中能看到样本来源、预期行为和回归判断口径。

- nfr_id: NFR-05
  dimension: 可解释性
  requirement: 任何复杂度升级都必须能用一句人话说清“为什么非加不可”，不能只写“为了以后扩展”。
  observable_signal: 审查者在不读代码的情况下，也能理解该复杂度存在的业务理由。
```

## acceptance_seed_matrix

| acceptance_seed_id | 场景 | 输入种子 | 期望现象 |
|---|---|---|---|
| AS-01 | 新需求要求新增一个 agent | “请增加一个能查天气的 agent” | 文档先给单 agent 或现有 agent 扩展方案，只有证据不足时才允许拆新 agent |
| AS-02 | 复杂方案评审 | 候选方案包含 planner、router、supervisor 多层结构 | 评审材料必须出现简单方案、升级证据和拒绝条件，否则不能通过 |
| AS-03 | 审查坏味道 | 出现“为了稳妥先加一层关键词判定” | 审查清单能明确判定为坏味道并阻断，而不是作为经验性修补放过 |
| AS-04 | 规则分层设计 | 提议把所有 agent 规则、长流程和执行细节都塞进根 `AGENTS.md` | 评审材料会要求拆分到仓库级、目录级和 `PLANS.md`，而不是继续堆大文档 |
| AS-05 | 回归验证 | 调整 Codex 的 agent 写法门禁 | 能看到一组真实样本对照，说明是否减少过度流程和启发式，而不是只有主观描述 |

## traceability_seed_matrix

| bg_id | fr_id | scenario_id | acceptance_seed_ids | design_focus |
|---|---|---|---|---|
| BG-01 | FR-01 | S-01 | AS-01, AS-02, AS-03 | 如何把“默认简单、复杂度后置”固化为 Codex 可稳定遵守的规则 |
| BG-01 | FR-02 | S-01 | AS-01, AS-02 | 如何把最佳实践核验变成需求与设计阶段的固定输入，而不是可选动作 |
| BG-01 | FR-03 | S-01 | AS-01, AS-02 | 如何定义复杂度升级门槛，避免方案因“想象中的未来需求”而膨胀 |
| BG-01 | FR-04 | S-01 | AS-03 | 如何让语义理解和护栏职责彻底分层，避免编排层重新长出词表 |
| BG-01 | FR-05 | S-01 | AS-04 | 如何把仓库级规则、目录级覆盖和长流程文档分层承载 |
| BG-02 | FR-02 | S-01 | AS-02, AS-05 | 如何把官方最佳实践和本仓库协作方式结合成可复用的审查模板 |
| BG-02 | FR-06 | S-01 | AS-05 | 如何把写法复杂度和行为质量转成最小可持续评测集 |
| BG-02 | FR-07 | S-01 | AS-02, AS-03 | 如何沉淀统一坏味道清单、例外条件和阻断规则，减少审查口径漂移 |

## out_of_scope

1. 本次不直接决定具体代码文件怎么改，也不产出实现步骤。
2. 本次不进入项目现有 agent 的重构方案，不定义 supervisor、intent、goal、handoff 等运行态收口顺序。
3. 本次不讨论模型供应商更换、推理参数调优或 Prompt 细节文案优化。
4. 本次不把前端交互、接口字段或数据库结构扩写成实现方案。

## constraints_and_assumptions

1. 项目当前未上线，默认优先选择架构正确和职责收口，而不是保守兼容。
2. Codex 后续是否稳定遵守新规则，取决于仓库级规则、目录级规则、审查清单和验收门禁是否同时落地，不能只靠一段口头原则。
3. 最佳实践当前以 OpenAI 和 Anthropic 官方资料为主要依据；若后续官方建议发生明显变化，需要重新校验本需求中的默认判断。
4. 复杂 agent 不是绝对禁止，而是必须后置；只有当单 agent 或更简单 workflow 无法满足需求时，才允许升级复杂度。
5. 关键词、正则和 substring 不是完全禁用，但只能承担护栏和格式抽取职责，不能继续承担主语义决策职责。
6. 本次默认通过需求与后续设计阶段固化规则，不在本需求阶段直接承诺代码级实现。

## approval

```yaml
status: draft
owner: AI collaboration / product clarification
approved: false
next_step: jjk-design
approval_notes:
  - 待确认是否将“Codex 写法治理”直接作为仓库级长期规则，还是先在 agent 相关目录试点。
  - 项目现有 agent 重构已明确移出本阶段范围，留待下一阶段单独设计。
```
