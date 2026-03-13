# memory intent resolver + contract 重构设计（冻结版）

## 1. `scope_contract`
```yaml
scope_contract:
  objective: "将记忆删除/撤销从 chat_service 的词表补丁重构为 resolver + contract，并对齐‘聊天主链只入队，异步 worker 决定是否落库’的真实架构。"
  scope:
    - "后端记忆意图链：chat_service -> memory_intent_resolver_service -> memory_intent_llm_service -> document_memory_service。"
    - "删除/撤销类反向记忆：由 AI 结合最近消息与候选记忆语义判断，不再使用 chat_service 关键词词表。"
    - "同步降级路径：仍可复用 resolver，但不再把‘已删除成功/删除失败’话术硬注入当前轮回复。"
    - "异步主链：保持 enqueue-only，不增加用户首包响应时长。"
  boundaries:
    - "本轮不改前端交互，不新增 UI 状态提示。"
    - "本轮不改 t_user_memory_intent_job 表结构。"
    - "本轮不引入规则词典、正则词库或硬编码触发词回退。"
    - "保留 archive 合同允许空 normalized_value 的校验修复，不回退到底层错误行为。"
  success_criteria:
    - "chat_service 不再包含删除/指代删除关键词词表与修复式补丁。"
    - "反向记忆是否成立、目标是否唯一定位，统一由 resolver 合同表达。"
    - "同步降级路径与未来 worker 消费路径复用同一 resolver。"
    - "异步主链维持 enqueue-only，主对话时延不因记忆判定增加。"
```

## 2. `architecture_contract`
```yaml
architecture_contract:
  module_boundaries:
    - module: "app/services/chat_service.py"
      responsibility: "聊天主链编排、保存 human 消息、入队异步记忆任务、同步降级下的 flush/recall 编排。"
      not_responsible:
        - "删除意图关键词判断"
        - "指代目标解析"
        - "成功/失败删除话术补丁"
    - module: "app/services/memory_intent_resolver_service.py"
      responsibility: "构建记忆判定上下文、调用 LLM 判定与候选解析、产出可持久化合同或澄清结论。"
      not_responsible:
        - "数据库写入"
        - "主对话流式响应拼装"
    - module: "app/services/memory_intent_llm_service.py"
      responsibility: "输出结构化 DecisionContract；提供主判定 prompt 与候选目标解析 prompt 的 JSON 合同归一化。"
      not_responsible:
        - "聊天服务层兜底补丁"
        - "数据库事务执行"
    - module: "app/services/document_memory_service.py"
      responsibility: "校验并执行最终 PersistenceContract，保证 atomic batch 与 archive 行为正确。"
      not_responsible:
        - "用户语义理解"
        - "指代记忆目标猜测"

  dependency_direction:
    - "chat_service -> memory_intent_resolver_service -> memory_intent_llm_service"
    - "memory_intent_resolver_service -> document_memory_repo/chat_repo (只读上下文)"
    - "chat_service -> document_memory_service (写入/召回)"
    - "禁止 document_memory_service 反向依赖 chat_service 词表策略"

  state_ownership:
    source_of_truth:
      - "是否真正删除成功：t_user_memory_document / archive 操作结果"
      - "是否应落库：resolver 产出的 PersistenceContract"
      - "是否需要澄清：resolver_contract.resolution_status"
    non_truth:
      - "当前轮 assistant 文案"
      - "chat_service 内部词表或硬编码提示"

  error_handling:
    - "主判定 reject 且无候选可解析：resolver 返回 rejected/needs_clarification，不进入 flush。"
    - "候选解析仍无法唯一定位：resolver 返回 needs_clarification，不进入 flush。"
    - "flush 返回 0：视为未持久化成功，但不在 chat_service 注入成功/失败话术补丁。"
    - "异步主链只保证入队，不把异步落库结果伪装为当前轮同步事实。"
```

## 3. `resolver_contract`
```yaml
resolver_contract:
  input_contract:
    required_fields: [user_text, thread_id]
    optional_fields: [user_id, source_message_id, intent_context]
    derived_context:
      - recent_thread_messages
      - active_preference_candidates
      - recent_memory_reference_candidates

  output_contract:
    required_fields: [resolution_status, reason_code, confidence, persistence_contract, audit]
    optional_fields: [intent_context]
    resolution_status_enum: [resolved, rejected, needs_clarification]

  semantics:
    resolved:
      meaning: "已产出可直接送 flush_document_memory 的 PersistenceContract。"
      persistence_contract: "必须为 accept 合同，且 archive 目标已唯一确定。"
    rejected:
      meaning: "本轮不是可持久化记忆操作，或不应继续执行。"
      persistence_contract: null
    needs_clarification:
      meaning: "用户意图可能是反向记忆，但目标未唯一定位。"
      persistence_contract: null

  invariants:
    - "resolver 不使用关键词词表判断反向记忆。"
    - "当走候选目标解析时，slot_key 必须来自上下文候选，不允许自造。"
    - "候选目标解析 accept 时仅允许单一 archive item。"
    - "archive 合同允许 normalized_value 为空字符串。"
```

## 4. `runtime_contract`
```yaml
runtime_contract:
  sync_chat_path:
    steps:
      - "保存 human 消息"
      - "若 memory_intent_async_enabled=true，则仅 enqueue 并返回，不阻塞主对话"
      - "若 async 关闭，调用 resolver -> flush -> recall"
    reply_policy:
      - "当前轮不再通过 chat_service 注入‘已成功删除/删除失败’补丁文案"
      - "同步降级路径仅更新 memory_context，不负责对删除结果做拟人化承诺"

  async_worker_path:
    target_state: "worker 未来直接复用 memory_intent_resolver_service.resolve(...)"
    guarantee:
      - "主对话响应时长不受记忆判定影响"
      - "真实删除与否只由异步任务执行结果决定"

  immediate_context_refresh:
    rule: "同步 flush 成功且开启 recall 时，使用 recall 的最新结果完整覆盖旧 memory_context；允许覆盖为空字符串，用于清除已归档记忆的当前轮注入。"
```

## 5. `decision_tradeoff`
- 不再沿用上一轮在 `chat_service` 中增加的删除词表、指代修复和成功/失败话术补丁，因为这些逻辑把语义判断、状态事实和回复策略耦合到了错误层级。
- 保留 `archive` 允许空 `normalized_value` 的修复，因为这是持久化合同正确性问题，属于底层 schema/validator 的真实缺陷，不应因上层重构被回滚。
- 采用 `resolver + contract` 而不是继续强化 prompt 直出 + chat_service 补丁，是为了让未来异步 worker 与同步降级复用同一条判断链，避免双实现漂移。

## 6. `acceptance_contract`
```yaml
acceptance_contract:
  unit_tests:
    - "tests/unit/test_memory_intent_resolver_service.py"
    - "tests/unit/test_memory_intent_llm_service.py"
    - "tests/unit/test_chat_service_memory_flags.py"
    - "tests/unit/test_document_memory_service.py"
  targeted_cmd: "bash scripts/pytest_targeted.sh tests/unit/test_memory_intent_resolver_service.py tests/unit/test_memory_intent_llm_service.py tests/unit/test_chat_service_memory_flags.py tests/unit/test_document_memory_service.py -q"
  runtime_expectations:
    - "chat_service 中不再保留删除/指代删除关键词词表。"
    - "同步 archive 成功且 recall 为空时，本轮 memory_context 可被清空。"
    - "异步模式仍只入队，不同步调用 resolver/flush。"
```
