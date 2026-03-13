# AI 响应契约统一澄清设计说明（SSE / Structured Result）

## 1. scope_contract
- 目标:
  - 把当前“仅传输层统一”的状态，升级为“传输 + 语义 + 渲染 + 回放”四层统一。
  - 确保“后端新增一种结构化结果”时，前端可预测渲染或可观测降级，不再静默丢失。
  - 冻结可直接进入 `/jjk-plan` 的实现契约，避免继续并行演进两套响应模型（`blocks` vs `result(data_type+data)`）。
- 范围:
  - 后端：`app/ai/events.py`、`app/ai/protocol.py`、`app/services/chat_service.py`、`app/core/types.py`
  - 前端：`web/src/lib/backend.ts`、`web/src/hooks/useSSEStream.ts`、`web/src/components/chat/messages/ai.tsx`、`web/src/types/message.ts`
  - 文档：`docs/开发文档/代码解读/SSE事件协议.md`、`docs/产品文档/聊天系统需求.md`
- 边界:
  - 不改变 `/api/v1/chat/stream` 接口路径与 SSE 基本机制。
  - 不重构多智能体编排策略（Supervisor / Expert 路由逻辑保持不变）。
  - 不引入第二条面向前端的并行协议（禁止新增“单独 blocks 通道”）。
- 成功标准:
  - 单一契约源可同时约束后端产出与前端消费（编译期/测试期可发现漏配）。
  - `result` 未知类型不再静默丢弃，必须落日志并展示安全降级 UI。
  - 历史回放、实时流、resume 三条路径对结构化数据口径一致。

## 2. architecture_contract
- 模块边界与职责:
  - **Contract Source（契约源）**
    - 新增统一结构化结果契约模块（后端权威定义），输出：
      - `data_type` 枚举
      - 每类 `data` 形状约束
      - 版本号（`result_contract_version`）
    - 禁止在 workflow/tool 内散落字符串常量定义类型。
  - **Producer（生产层）**
    - 所有结构化输出必须经 `build_streaming_result_payload_from_fields()` 统一组装后进入 `emit_result()`。
    - `ToolResultBuilder` 与 `additional_kwargs` 路径只负责业务数据，不直接决定传输协议细节。
  - **Transport Normalizer（传输归一层）**
    - `chat_service` 继续作为 SSE 输出总口，负责兜底补齐字段与兼容口径。
    - `done` 只做生命周期收口，不承载结构化数据。
  - **Consumer + Renderer（消费渲染层）**
    - `backend.ts` 只做协议校验与分发，不承载业务渲染分支。
    - `ai.tsx` 从硬编码 `if/else` 迁移为 renderer registry（`data_type -> renderer`），新增类型时可独立注册。
  - **Replay Consistency（回放一致层）**
    - `message-normalizer` 与历史消息回放路径统一使用同一结构化契约字段，避免“实时可见、刷新缺失”。

- 端到端数据流:
  1. 专家节点/工具产出业务对象（如 todo/sql/image）。
  2. Producer 用统一构建器生成 `StreamingResultPayload`。
  3. `emit_result` 发 SSE `event: result`，`data={data_type,data,message}`。
  4. `backend.ts` 按契约校验后分发 `onResult`。
  5. `useSSEStream` 写入 `additional_kwargs`（`data_type + data`）。
  6. `ai.tsx` 通过 renderer registry 渲染；未命中类型走 fallback 卡片。
  7. 历史回放从 `metadata/additional_kwargs` 还原同一渲染路径。

- 状态生命周期:
  - `raw_business_payload -> typed_result_payload -> sse_result_event -> normalized_result -> message.additional_kwargs -> rendered_component`
  - 生命周期约束：
    - 任一环节校验失败必须可观测（日志 + 前端告警标记）。
    - 失败不阻断主文本链路（`token/final_answer/done` 正常收口）。

- 异常语义与降级策略:
  - 缺失 `data_type`：后端标记协议错误并降级为 `data_type=error` 或前端 fallback 卡片（二选一统一，不可双标）。
  - 未知 `data_type`：前端展示“暂不支持的结构化结果”卡片 + 原始 JSON 摘要 + trace 标识。
  - `data` 形状不合法：渲染层拒绝组件渲染，退回 fallback，不抛致命异常。
  - 回退路径统一：关闭开关或触发降级策略（开关默认开启）。

## 3. 最终方案
- 方案描述:
  - 保留现有 SSE 主协议不变，以 `result(data_type+data+message?)` 作为唯一结构化通道。
  - 引入“契约单一源 + 代码生成（或镜像同步）+ 渲染注册表 + 契约测试矩阵”的闭环治理。
  - 明确拒绝“并行维护 `AssistantResponse.blocks` 与 SSE result 两套外部契约”。
- 关键决策:
  - 决策1：统一口径以 SSE result 为外部标准；`blocks` 仅允许作为内部中间表示（若存在必须在 service 层映射到 result）。
  - 决策2：`data_type` 必须从受控枚举产生，不允许任意字符串直接下发。
  - 决策3：前端改为注册式渲染，不再把业务类型判断散落在消息组件中。
  - 决策4：新增契约演进必须同时提交“协议文档 + 后端校验 + 前端渲染 + 回放测试”，否则不可合入。

## 4. 决策权衡（仅放弃原因）
- 放弃路径: 维持现状（继续在 workflow/前端组件里按需硬编码新类型）。
- 放弃原因: 会持续制造“新增类型后静默不展示”的隐性故障，且回放链路容易再次分叉。
- 放弃路径: 另起一套 `AssistantResponse.blocks` API 与 SSE 并行。
- 放弃原因: 双协议会造成协议治理与兼容成本翻倍，违背“单入口流式链路”目标。

## 5. risk_rollback_contract
- 关键风险（含反例）:
  - R-01 协议收敛期出现“合法旧事件被误判非法”。
    - 反例：历史 `result` 仅有 `data_type/data`，无 `message`。
  - R-02 前端 registry 漏注册导致新类型不可见。
    - 反例：后端发出 `knowledge_card`，前端无 renderer 且无 fallback。
  - R-03 实时链路与历史回放字段名不一致导致刷新后卡片消失。
    - 反例：实时使用 `additional_kwargs.data`，历史只存 `metadata.raw_payload`。
- 回退锚点（默认开启 true，回退 false）:
  - `ENABLE_RESULT_CONTRACT_V1=true`（默认开启）；回退：`false`，恢复宽松解析。
  - `ENABLE_RESULT_RENDER_REGISTRY_V1=true`（默认开启）；回退：`false`，恢复旧分支渲染路径。
  - `ENABLE_RESULT_UNKNOWN_FALLBACK_CARD=true`（默认开启）；回退：`false`，未知类型仅日志告警。

## 6. requirement_seeds（字段级需求原子）
```yaml
requirement_seeds:
  - design_item: D-01
    fr_id: FR-RESULT-CONTRACT-SINGLE-SOURCE
    trigger: 任意节点发送结构化结果
    input_contract:
      required_fields: [data_type, data]
      optional_fields: [message, meta, contract_version]
      defaults:
        message: ""
    output_contract:
      required_fields: [event="result", data_type, data]
      optional_fields: [message, node]
    failure_semantics: 缺少必填字段时进入统一降级（error 或 fallback），不得静默丢弃
    observability_fields: [trace_id, thread_id, run_id, data_type, contract_version]
    rollback_anchor: ENABLE_RESULT_CONTRACT_V1=false
    acceptance_cmd_ref: venv/bin/python -m pytest tests/unit/test_chat_service_done_payload.py tests/unit/test_chat_service_turn_slice.py -q

  - design_item: D-02
    fr_id: FR-RESULT-RENDER-REGISTRY
    trigger: 前端收到 SSE result
    input_contract:
      required_fields: [data_type, data]
      optional_fields: [message]
      defaults: {}
    output_contract:
      required_fields: [renderer_hit_or_fallback]
      optional_fields: [warning_code]
    failure_semantics: 未知类型必须 fallback 可见且记录 warning，不得吞事件
    observability_fields: [thread_id, data_type, renderer_key, fallback_used]
    rollback_anchor: ENABLE_RESULT_RENDER_REGISTRY_V1=false
    acceptance_cmd_ref: pnpm --filter web test -- --runInBand

  - design_item: D-03
    fr_id: FR-RESULT-REPLAY-CONSISTENCY
    trigger: 历史回放/恢复流加载 AI 消息
    input_contract:
      required_fields: [message_id, additional_kwargs.data_type, additional_kwargs.data]
      optional_fields: [additional_kwargs.final_source]
      defaults: {}
    output_contract:
      required_fields: [render_same_as_stream]
      optional_fields: [degraded_reason]
    failure_semantics: 回放字段缺失时显示降级卡片并保留文本正文
    observability_fields: [message_id, thread_id, replay_source, data_type]
    rollback_anchor: ENABLE_RESULT_UNKNOWN_FALLBACK_CARD=false
    acceptance_cmd_ref: venv/bin/python -m pytest tests/unit/test_multi_intent_coverage_reconcile.py -q
```

## 7. implementation_seeds（轻量任务原子）
```yaml
implementation_seeds:
  - task_id: T-01
    feature_id: P1-contract-source
    file_paths:
      - app/ai/protocol.py
      - app/ai/events.py
      - app/core/types.py
      - app/services/chat_service.py
    symbols:
      - StreamingResultPayload
      - build_streaming_result_payload_from_fields
      - emit_result
      - _normalize_result_event_payload
    change_type: modify

  - task_id: T-02
    feature_id: P1-frontend-registry
    file_paths:
      - web/src/lib/backend.ts
      - web/src/hooks/useSSEStream.ts
      - web/src/components/chat/messages/ai.tsx
      - web/src/types/message.ts
    symbols:
      - normalizeResultEventData
      - handleStructuredResultEvent
      - AssistantMessage
    change_type: modify

  - task_id: T-03
    feature_id: P1-contract-doc-sync
    file_paths:
      - docs/开发文档/代码解读/SSE事件协议.md
      - docs/产品文档/聊天系统需求.md
    symbols:
      - SSE_result_contract
      - data_type_registry
    change_type: modify

  - task_id: T-04
    feature_id: P1-contract-tests
    file_paths:
      - tests/unit/test_chat_service_done_payload.py
      - tests/unit/test_chat_service_turn_slice.py
      - tests/unit/test_multi_intent_coverage_reconcile.py
      - web/src/lib/backend.ts
    symbols:
      - result_contract_validation
      - unknown_data_type_fallback
    change_type: modify
```

## 8. execution_chain_seed
```yaml
execution_chain_seed:
  preferred_mode: parallel
  task_key: PP-20260306-ai-response-contract-unify
  card_seed:
    - T-01
    - T-02
    - T-03
    - T-04
  execution_contract_hint:
    delivery_mode: staged
    execution_unit: per_pr
    commit_policy: per_pr
    stop_boundary: per_pr
```

## 9. 对标结论（OpenClaw + 外部参考）
- OpenClaw 对标（`../bot/openclaw/docs/zh-CN/concepts/streaming.md`）:
  - 其设计把“流式传输机制”与“渠道展示策略”分层，不把展示策略反向污染传输协议。
  - 本方案对齐点：保留 SSE 传输契约稳定，把前端渲染做成可替换 registry，而非协议层硬编码。
- 外部参考:
  - MDN EventSource/SSE 事件模型：强调事件名 + data 载荷分离，适合作为稳定 transport envelope。
  - OpenAPI/契约驱动实践：建议以单一契约源驱动多端类型一致性，减少手写镜像漂移。

## 10. 设计冻结回执（机读）
```yaml
design_freeze_summary:
  design_actionable: true
  missing_blocks: []
  risk_level: medium
  risk_counterexamples_count: 3
  handoff_contract_ready: true
  implementation_seed_count: 4
```

## 11. clarify_handoff_contract（机读）
```yaml
clarify_handoff_contract:
  version: v2
  topic: "ai-response-contract-unification"
  design_source: "workdocs/归档/正文/设计/2026-03-06-ai-response-contract-unification-design.md"
  handoff_ready: true
  required:
    requirement_seeds:
      - design_item: D-01
        fr_id: FR-RESULT-CONTRACT-SINGLE-SOURCE
        trigger: 任意节点发送结构化结果
        input_contract:
          required_fields: [data_type, data]
          optional_fields: [message, meta, contract_version]
          defaults:
            message: ""
        output_contract:
          required_fields: [event, data_type, data]
          optional_fields: [message, node]
        failure_semantics: 缺少必填字段时进入统一降级（error 或 fallback），不得静默丢弃
        observability_fields: [trace_id, thread_id, run_id, data_type, contract_version]
        rollback_anchor: ENABLE_RESULT_CONTRACT_V1=false
        acceptance_cmd_ref: venv/bin/python -m pytest tests/unit/test_chat_service_done_payload.py tests/unit/test_chat_service_turn_slice.py -q
      - design_item: D-02
        fr_id: FR-RESULT-RENDER-REGISTRY
        trigger: 前端收到 SSE result
        input_contract:
          required_fields: [data_type, data]
          optional_fields: [message]
          defaults: {}
        output_contract:
          required_fields: [renderer_hit_or_fallback]
          optional_fields: [warning_code]
        failure_semantics: 未知类型必须 fallback 可见且记录 warning，不得吞事件
        observability_fields: [thread_id, data_type, renderer_key, fallback_used]
        rollback_anchor: ENABLE_RESULT_RENDER_REGISTRY_V1=false
        acceptance_cmd_ref: pnpm --filter web test -- --runInBand
    implementation_seeds:
      - task_id: T-01
        feature_id: P1-contract-source
        file_paths:
          - app/ai/protocol.py
          - app/ai/events.py
          - app/core/types.py
          - app/services/chat_service.py
        symbols:
          - StreamingResultPayload
          - build_streaming_result_payload_from_fields
          - emit_result
          - _normalize_result_event_payload
        change_type: modify
      - task_id: T-02
        feature_id: P1-frontend-registry
        file_paths:
          - web/src/lib/backend.ts
          - web/src/hooks/useSSEStream.ts
          - web/src/components/chat/messages/ai.tsx
          - web/src/types/message.ts
        symbols:
          - normalizeResultEventData
          - handleStructuredResultEvent
          - AssistantMessage
        change_type: modify
      - task_id: T-03
        feature_id: P1-contract-doc-sync
        file_paths:
          - docs/开发文档/代码解读/SSE事件协议.md
          - docs/产品文档/聊天系统需求.md
        symbols:
          - SSE_result_contract
          - data_type_registry
        change_type: modify
      - task_id: T-04
        feature_id: P1-contract-tests
        file_paths:
          - tests/unit/test_chat_service_done_payload.py
          - tests/unit/test_chat_service_turn_slice.py
          - tests/unit/test_multi_intent_coverage_reconcile.py
          - web/src/lib/backend.ts
        symbols:
          - result_contract_validation
          - unknown_data_type_fallback
        change_type: modify
    execution_chain_seed:
      preferred_mode: parallel
      task_key: PP-20260306-ai-response-contract-unify
      card_seed: [T-01, T-02, T-03, T-04]
      execution_contract_hint:
        delivery_mode: staged
        execution_unit: per_pr
        commit_policy: per_pr
        stop_boundary: per_pr
  extended:
    observability_hints:
      - 为每个 result 增加 data_type 维度统计（成功渲染率、fallback 率、错误率）
      - 统一日志键：trace_id/thread_id/run_id/data_type/contract_version
    risk_counterexample_map:
      - risk_id: R-01
        counterexample: 旧 payload 无 message 字段被误拒
        verify_cmd: venv/bin/python -m pytest tests/unit/test_chat_service_done_payload.py -q
      - risk_id: R-02
        counterexample: 新 data_type 未注册导致 UI 空白
        verify_cmd: pnpm --filter web test -- --runInBand
      - risk_id: R-03
        counterexample: 实时可见但历史回放缺失结构化卡片
        verify_cmd: venv/bin/python -m pytest tests/unit/test_multi_intent_coverage_reconcile.py -q
    assumptions:
      - 当前 chat SSE 主链路继续保留，不新增并行外部协议
      - 本轮允许以最小侵入方式引入 renderer registry
      - 回退策略优先采用开关关闭，不回滚数据库结构
  requirement_seeds:
    - D-01
    - D-02
    - D-03
  implementation_seeds:
    - T-01
    - T-02
    - T-03
    - T-04
  execution_chain_seed:
    preferred_mode: parallel
    task_key: PP-20260306-ai-response-contract-unify
```

## 12. 审批记录
- design_approved: false
- approved_at: "2026-03-06T11:21:08+08:00"
- approved_round: "round-1-conditional-adoption"
- approval_evidence: "用户回复“好的”，确认将采纳评估回填；本轮结论为“修订后采纳（Adopt with Changes）”，P0（异常语义唯一化、契约源机制唯一化、handoff required 补齐 D-03）完成前维持 NO_GO，不进入 /jjk-plan。评估依据：workdocs/归档/正文/设计/2026-03-06-ai-response-contract-unification-adoption-review.md"
