# `app/ai` 局部规则（Agent Authoring）

本文件只覆盖 `app/ai/**`。
目标很简单：别再把 agent 写成“模型很强，代码却更爱抢主导”的样子。

## 默认做法

1. `simple-first`：默认先单 agent、单 supervisor 或简单 workflow。只有简单方案被证据证明不够，才允许新增决策层或新增 agent。
2. `contract-first`：节点之间优先传结构化 contract，不靠自由文本 handoff 让下游自己猜语义。
3. `single semantic decider`：一次请求的主语义判定默认只允许一个 owner。不要再让 planner/router/supervisor/expert 连续重复判同一个问题。
4. `keyword_primary_routing` 视为坏味道：关键词、正则和 substring 只能用于 guardrail、格式抽取和安全校验，不能承担主语义路由。
5. 状态要有唯一真相：同一运行态语义不能同时由 `intent_plan`、`task_description`、`frame`、临时 fallback 各说各话。
6. 禁止 speculative fallback：不要为了“看起来更稳”先加一层 wrapper、兼容壳或假设性 fallback；需要例外时先写清证据。
7. 设计或改造 agent 路由、handoff、状态契约时，必须同时补真实样本评测，不要只靠单个 happy path 自证正确。

## 命中这些情况时必须停一下

1. 你准备新增第二个以上的主语义判定层。
2. 你准备新增 `*_HINTS/*_KEYWORDS/*_TRIGGERS` 一类业务词表做路由。
3. 你准备让 guardrail 结果反向改写主语义 contract。
4. 你准备同时保留新旧双轨状态源，且没有明确失效条件。
5. 你准备说“以后可能用到”，但拿不出复杂度升级证据。

## 常见坏味道 ID

1. `multi_decider_stack`
2. `keyword_primary_routing`
3. `dual_truth_design`
4. `speculative_fallback`
5. `missing_eval_evidence`

如果你命中这些 smell，请回到 `.cursor/rules/agent_authoring.mdc` 看完整口径，再决定怎么改。
