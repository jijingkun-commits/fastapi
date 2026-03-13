# chat-composite-latency-local-refactor 需求文档

> 更新时间：2026-03-12 22:04 +08:00
> 文档目标：冻结“局部重构版 B”的纯需求合同，供 `2026-03-12-chat-composite-latency-local-refactor-design.md` 与后续 `chat-composite-latency-local-refactor_implementation_plan.md` 消费

## 1. problem_statement

- 当前显式复合提问虽然已经能命中 fast path，但后端执行链路仍表现为“串行重活”，用户在大部分耗时窗口内只能看到 `status/tool_start`，看不到任何可消费正文。
- `todo.query` 在复合语境下仍可能被天气等外部子句污染，误入 `out_of_scope -> need_clarify`，把本应执行查询的时间浪费在错误澄清上。
- 现有 coverage 口径过于依赖 deliverable summary/attempt，容易把“仍在澄清/尚未完成”的 goal 误判为已回答。

## 2. target_users

- 对话终端用户：希望复合提问时尽快看到首段可消费结果，而不是长时间空等。
- 质量/运维支持：希望通过结构化 timing 和 coverage 结果快速定位慢点与误判点。
- 研发维护者：希望先用低风险局部重构收敛热点链路，而不是立刻重写整张 LangGraph 图。

## 3. core_scenarios

1. 用户发送“先查我的待办，再看嘉兴天气”这类显式复合提问。
2. 系统已识别出 `todo.query + external.lookup` 双目标，但当前只有最终收口时才出现正文。
3. `todo.query` 已被冻结为子目标后，不应再被整句天气子句重新打成 `out_of_scope`。
4. 某个 goal 只进入澄清或失败时，最终答复必须明确未完成，不能宣称“已全部覆盖”。
5. 同环境下单一提问回归时，不应因为本轮治理引入明显时延或交互回退。

## 4. in_scope

- 仅治理已经被识别为“显式复合提问”的聊天链路。
- 仅治理当前局部重构版 B：
  - 提前回流可直答 `external.lookup` 正文；
  - 冻结后的 `todo.query` 直通执行，不再被整句复合问题重判；
  - coverage 只把真正 answered 的 goal 计入已覆盖；
  - 输出请求级与 per-goal 结构化 timing 元数据。
- 保持现有 `/api/v1/chat/stream` 主接口与 SSE 主协议不变。

## 5. out_of_scope

- 不把显式复合问题整体改写为 LangGraph `Send` 全并行 fan-out/fan-in 图。
- 不新增数据库表、字段、索引或约束。
- 不扩展为完整 `public_structured_fact` 新能力层。
- 不修改 `/api/v1/chat/stream` 路径、认证方式或前端整体渲染协议。
- 不顺带重构 todo/data 子图的其他无关行为。

## 6. functional_requirements

```yaml
functional_requirements:
  - fr_id: FR-01
    title: 显式复合提问必须尽快回流首段用户可见正文
    description: |
      对已经命中显式复合 fast path 且包含可直答 external.lookup 的请求，
      系统必须在最终统一答复之前先回流该 goal 的用户可见正文；
      status/tool_start/handoff 不计入“首个用户可见内容”。
    priority: P0

  - fr_id: FR-02
    title: frozen todo.query 不得再被复合原句误裁成 out_of_scope
    description: |
      当 handoff contract 已冻结为 todo.query 时，
      todo 子链路必须优先执行该查询合同，
      不得因为整句里混有天气/知识库子句而转入 out_of_scope 或错误澄清。
    priority: P0

  - fr_id: FR-03
    title: clarify_needed/failed/pending 不得计入 answered_goals
    description: |
      coverage 判定必须基于标准化 goal outcome，
      只有真正 answered 的 must_answer goals 才能计入 answered_goals 与 coverage_pass。
    priority: P0

  - fr_id: FR-04
    title: 最终答复必须按用户问题顺序收口并显式标记未完成目标
    description: |
      最终答复继续由统一出口返回；
      若存在未完成 goal，必须按用户原始 goal 顺序明确展示“暂未完成/失败/待补齐”，
      不得输出“以上问题已全部覆盖”或等价表述。
    priority: P0

  - fr_id: FR-05
    title: 请求级与 per-goal 时延口径必须结构化输出
    description: |
      运行态至少需要输出 first_event_at_ms、first_visible_at_ms、final_answer_at_ms、done_at_ms，
      以及 per-goal 的 started/first_visible/terminal/status 字段，供 QA 与后续优化使用。
    priority: P1

  - fr_id: FR-06
    title: 单一提问回归不得出现明显时延或交互回退
    description: |
      本轮治理完成后，单一提问仍应维持现有主链路行为；
      不得新增无意义澄清，也不得把首个可见正文显著推迟。
    priority: P1
```

## 7. non_functional_requirements

```yaml
non_functional_requirements:
  - nfr_id: NFR-01
    requirement: 在同一测试环境下，显式复合请求的 first_visible_at_ms 必须显著早于 final_answer_at_ms。
  - nfr_id: NFR-02
    requirement: 本轮以局部重构为优先，禁止新增第二套并行执行框架或双轨运行时。
  - nfr_id: NFR-03
    requirement: 不引入 DB migration；运行态观测先走内存/日志/SSE meta。
  - nfr_id: NFR-04
    requirement: 单一提问路径不得出现明显性能回退或结果质量回退。
  - nfr_id: NFR-05
    requirement: 所有成功标准都必须能由定向 pytest 或 UAT 复测验证。
```

## 8. business_acceptance_criteria

1. 对“先查待办，再看天气”类显式复合请求，用户能在最终统一答复前先看到至少一段可消费正文。
2. `todo.query` 在复合天气场景下不再被误判为 `out_of_scope`。
3. 仅进入澄清/失败的 goal 不再被统计为 answered。
4. 最终答复对未完成 goal 明确标注，不再假装“全部覆盖”。
5. 运行输出能直接用于下一轮耗时复盘，而不必再手工从原始日志逐段抠时间。

## 9. constraints_and_assumptions

- 当前项目未上线，优先采用低风险局部重构，而不是全量并行重写。
- 现有显式复合 fast path 已能识别目标，因此本轮优先修复“识别后执行与回流”的问题，而不是重新发明 goal 识别器。
- SSE 自定义事件与命名事件仍继续复用现有协议，不额外引入 WebSocket 或第二套流式通道。
- 当前环境下最佳实践来源已核验为：
  - LangGraph Streaming: <https://docs.langchain.com/oss/python/langgraph/streaming>
  - LangGraph Graph API / Send: <https://docs.langchain.com/oss/python/langgraph/graph-api#send>
  - MDN SSE: <https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events>

## 10. publish_product_doc

```yaml
publish_product_doc: false
```

## 11. approval_gate

```yaml
requirements_approved: true
approved_at: "2026-03-12 22:04 +08:00"
approval_evidence: "用户显式确认：好的；并接受先补 requirements + design + jjk-plan，一次出完。"
```
