# 记忆意图链路瘦身设计（2026-03-09）

## 结论

本次做三个收口：
1. 删除未进入主运行链路、且仍依赖关键词/短语触发的旧 `document_memory_service.flush()` 日记写入入口。
2. 将 `chat_service` 中关于删除确认语的词面示例改为抽象删除链表述，避免编排层继续持有“1/确认/是这条”这类语义知识。
3. 将 memory 相关 prompt 与 prompt contract 测试，从“固定短语断言”改为“行为合同断言”，只保留上下文键、决策约束与承接语义，不再依赖具体词面。
4. 将 `document_memory_repo.list_documents()` 恢复为默认窄契约；只有 resolver 的 archived 候选查询显式申请 source refs。
5. 将 `response_guidance_context` 从文本提示升级为结构化 `response_guidance_contract`，由 graph 统一渲染为系统上下文。
6. 将 `multi_intent/router_blocked` 的 `system_context` 拼装 helper 也收敛到 `response_policy_service`，避免 graph 自带策略文案拼接。

## 模块边界

- `chat_service`：仅负责编排、产出运行时结构化回复约束，不承担语义识别或最终话术拼装。
- `memory_intent_resolver_service`：负责聚合上下文并组织二阶段判定。
- `memory_intent_llm_service`：负责基于合同 prompt 做语义判定，prompt 只描述行为规则与上下文契约，不把具体触发短语当作稳定依赖。
- `document_memory_service.flush_canonical_memory()`：负责最终结构化持久化。
- `document_memory_repo.list_documents()`：保持通用列表职责，source refs 仅作为显式 opt-in 的场景字段。
- `response_policy_service`：负责构造与渲染运行时回复策略，也负责 `multi_intent/router_blocked` 的 system_context 恢复提示，成为运行时策略文案的单一真理源。
- `multi_agent_graph`：只负责调用 `response_policy_service`，把渲染/构造结果注入 `system_context`。

## 依赖方向

仅保留 `chat_service -> resolver -> llm_service -> flush_canonical_memory` 主链路。
删除 `document_memory_service.flush()` 这条历史旁路，避免双入口。
repo 侧保持“默认窄返回 + 场景显式 opt-in”方向，避免公共列表接口被单个删除场景永久拉宽。

## 状态归属

- 删除目标、候选集、最近对话承接状态：归 resolver context。
- 回复约束：运行态保存为 `response_guidance_contract` 结构化字段，不再由 `chat_service` 直接拼接自然语言提示。
- 多目标补齐/Router 阻断提示：统一由 `response_policy_service` 按活动目标与缺口目标生成，graph 不再维护策略文案 helper。
- prompt contract：只校验“是否支持指代删除/短确认承接/候选约束”，不校验某个具体短语是否必须出现。
- archived 候选需要的 `source_thread_id/source_message_id` 归 resolver 场景上下文，不归通用文档列表默认视图。

## 错误处理责任

- 语义不明确：由 resolver/LLM 返回 reject 或 needs_clarification。
- 持久化未命中 active 槽位：由 `flush_canonical_memory()` 幂等处理。
- `chat_service` 不再用词面判断兜底，也不再承载删除成功/幂等删除的最终话术模板。

## 预期收益

- 删除旧关键词触发器，消除与“AI 自判断”目标相冲突的死代码。
- 收紧 `chat_service` 编排职责，降低后续再次回退为关键词实现的风险。
- 降低 prompt 与测试对少数固定表述的耦合，减少未来因为换说法导致能力退化或误判。
- 收窄 repo 通用返回面，避免 memory 删除场景把场景字段泄漏成全局契约。
- 将回复约束从文本片段升级为结构化 contract，减少 service 层继续持有提示文案的耦合。
- 将 multi_intent/router_blocked 的恢复提示统一进 response policy，进一步缩小 graph 的非编排职责。
