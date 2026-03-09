# memory_intent lean cleanup 重构报告

## 输入映射
- task_id/card_id/pr_id: none
- 目标：删除旧关键词触发死代码，收敛 chat_service 中的词面知识。

## 改动清单
- 删除 `app/services/document_memory_service.py` 中未被主链路使用的 `_MEMORY_TRIGGER_PATTERN`、`_should_persist_memory()`、`flush()`。
- 删除对应旧单测。
- 将 `app/services/chat_service.py` 的删除确认回复指导，从“确认语示例”改为“抽象删除链”。
- 将 `app/ai/prompts/agent_prompts.py` 与 `tests/unit/test_memory_route_prompt_contract.py` 从词面断言改为行为合同断言。
- 将 `document_memory_repo.list_documents()` 收窄为默认不透出 source refs；resolver 的 archived 查询显式 opt-in。
- 将 `response_guidance_context` 重构为结构化 `response_guidance_contract`，并进一步抽到 `app/services/response_policy_service.py` 作为单一真理源，由 graph 调用后渲染到 `system_context`。
- 将 `multi_intent/router_blocked` 的恢复提示 helper 也并入 `response_policy_service`，graph 仅保留编排与调用职责。

## 行为等价边界
- 主运行链路仍为 `chat_service -> memory_intent_resolver_service -> memory_intent_llm_service -> flush_canonical_memory`。
- 不修改当前 resolver/LLM 的合同字段与持久化逻辑；仅把运行时回复提示从文本片段改为结构化 contract。

## 风险与待处理
- memory prompt 已去掉当前这轮新增的关键删除短语示例，但其他非本轮范围的 prompt 仍可能含业务举例。
- `document_memory_repo.list_documents()` 已恢复默认窄契约；若后续再出现 source refs 需求，应继续走显式 opt-in 或专用 repo 接口。
- graph 侧目前通过 `response_policy_service` 统一生成/渲染策略文本供模型消费；若后续模型执行层支持更强结构化控制，可再把该 service 升级为更专用的 responder/policy engine。

## 建议后续
- 继续评估是否把 archive 回复策略从文本 guidance 再进一步结构化。
- 继续审查非 memory 场景 prompt 是否也存在不必要的词面耦合。
