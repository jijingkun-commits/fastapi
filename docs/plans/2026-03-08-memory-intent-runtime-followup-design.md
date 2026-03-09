# 记忆指代删除与流式去重收口设计（冻结版）

## 1. `scope_contract`
```yaml
scope_contract:
  objective: "在既有 memory intent resolver + contract 重构基础上，收口三类运行时缺陷：流式重复回复、记忆删除误路由、指代删除候选触发过窄。"
  scope:
    - "响应语义：当系统具备原生记忆删除能力时，Assistant 不得再输出‘去 Memory 页面手工删除’之类的 UI 指南。"
    - "流式层：custom 事件已向用户发出文本时，values 模式不得再次补发同一条 AIMessage。"
    - "路由层：用户讨论/删除长期记忆时，不得误委派给 todo_expert。"
    - "resolver 层：recent_memory_reference_candidates 仅作为提示，不再成为二阶段候选解析的硬前置条件。"
  boundaries:
    - "不修改前端 SSE 事件契约。"
    - "不回退到 chat_service 关键词词表或补丁式删除话术。"
    - "不改变异步记忆链 enqueue-only 的主链时延口径。"
```

## 2. `architecture_contract`
```yaml
architecture_contract:
  module_boundaries:
    - module: "app/ai/workflow/multi_agent_graph.py"
      responsibility: "统一收口 custom/messages/values 三路流式事件，并对用户可见文本做幂等去重。"
      not_responsible:
        - "推断用户是否真的要删除记忆"
        - "前端重复消息兜底"
    - module: "app/ai/prompts/agent_prompts.py"
      responsibility: "约束 Supervisor 的语义路由边界，避免把记忆管理类请求误派给 todo_expert。"
      not_responsible:
        - "硬编码路由规则"
    - module: "app/services/memory_intent_resolver_service.py"
      responsibility: "决定是否进入 reference-resolution 二阶段，并复用 active candidates + recent messages 做目标定位。"
      not_responsible:
        - "数据库写入"
        - "流式文案输出"

  dependency_direction:
    - "todo_enhanced_nodes -> emit_clarification -> multi_agent_graph"
    - "supervisor prompt -> assign_to_* 委派行为"
    - "chat_service -> memory_intent_resolver_service -> memory_intent_llm_service"

  state_ownership:
    source_of_truth:
      - "是否已向用户发过该段文本：StreamingContext.collected_content / emitted_message_ids"
      - "是否真正删除成功：t_user_memory_document.status"
      - "候选定位是否可继续：resolver_contract.resolution_status"
    non_truth:
      - "todo_expert 的兜底澄清文案"
      - "recent_memory_reference_candidates 的启发式命中结果"

  error_handling:
    - "custom 事件已发文本后，values replay 必须静默跳过，不允许前端自行去重。"
    - "用户讨论记忆但路由不清时，保持在 supervisor/general.reply，不越权委派 todo_expert。"
    - "二阶段候选解析若仍无法唯一定位，resolver 返回 needs_clarification/rejected，不伪造 archive 合同。"
```

## 3. `runtime_contract`
```yaml
runtime_contract:
  streaming_dedupe:
    custom_text_sources:
      - "clarification.data.message"
      - "result.data.message"
      - "final_answer.data.content"
      - "confirmation.data.message"
    rule: "custom 事件中的用户可见文本一旦透传，也必须同步登记到 ctx.collected_content，供 values 模式去重。"

  response_contract:
    rule: "若用户请求删除已识别的跨会话记忆，Assistant 应明确表示系统会处理该删除请求；禁止声称无法直接删除并要求用户去 UI 手工操作。"
    confirmation_rule: "若上一轮已唯一确认删除目标，用户本轮回复‘1/确认/是这条’等确认语义时，应继续沿用该目标，不再退化成手工删除说明。"

  routing_guard:
    rule: "当用户在讨论、撤销、确认或删除长期记忆/偏好时，保持 supervisor 处理，不委派 todo_expert。"
    rationale: "真正的记忆写入链在 chat_service -> resolver -> flush/worker，todo_expert 不拥有该状态真理。"

  reference_resolution:
    rule: "只要存在 active_preference_candidates 且存在 recent_thread_messages，就允许进入二阶段 reference resolution。"
    hint_policy: "recent_memory_reference_candidates 仅作为高相关提示，不再作为唯一入口门槛。"
    safety: "最终可接受的 slot_key 仍必须来自候选集合，不允许模型自造。"
```

## 4. `verification_contract`
```yaml
verification_contract:
  targeted_tests:
    - "tests/unit/test_multi_agent_streaming_helpers.py"
    - "tests/unit/test_memory_intent_resolver_service.py"
    - "tests/unit/test_memory_intent_llm_service.py"
  runtime_checks:
    - "eval "$(bash scripts/vk_ports.sh --export)""
    - "lsof -nP -iTCP:${VK_BACKEND_PORT} -sTCP:LISTEN"
    - "lsof -nP -iTCP:${VK_FRONTEND_PORT} -sTCP:LISTEN"
    - "curl -sf http://127.0.0.1:${VK_BACKEND_PORT}/health"
    - "登录后调用 /api/v1/chat/stream 复测记忆删除场景，确认不再路由 todo_expert、SSE 无重复、DB 已归档"
```
