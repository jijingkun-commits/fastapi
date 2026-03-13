# 复合问题聊天耗时优化设计（2026-03-10）

## 背景
- 真实压测中，单次发送两个问题（问数 + 天气）端到端约 47s。
- 主要浪费点不是单一模型慢，而是：
  1. 显式复合问题先经过 Supervisor 再触发 `decompose_goals`，前半程存在空转；
  2. 已完成的直答子问题没有提前回流给用户；
  3. 数据子任务明明可以直接编译 handoff，却仍要等 Supervisor 完整走完。

## 最佳实践对照
- LangGraph 官方支持 fan-out/fan-in 并行与流式事件输出。
- SSE 适合先回已完成增量，再在最终事件统一收口。
- 结合当前实现，第一刀优先做“低风险高收益”的结构收敛，而不是直接重写整张图。

## 后续能力分层
- 本次为耗时优化先采用 `preprocess fast lane`，但天气类问题不应继续以专用特判散落在编排层。
- 后续建议把外部公开事实查询统一收敛为 `public_structured_fact` 能力层，与 `internal_data`、`open_web_search` 并列：
  - `internal_data`：答案来自库表/权限内业务数据；
  - `public_structured_fact`：答案来自公开世界、结构化且有时效性的事实，如天气、汇率、股价、节假日、时区；
  - `open_web_search`：需要开放网页检索、归纳和来源引用的开放问题。
- 该能力层职责只包含三件事：识别是否属于公开结构化事实、抽取事实槽位（如地点/日期/指标）、选择对应事实源并返回统一 contract。
- 编排层只消费结构化 contract 做路由与收口，不再继续累加“天气/汇率/股价”一类散装关键词分支。
- 这样做的收益是：避免语义规则散落、便于统一缓存/超时/降级、并为复合问题中的 `internal_data + public_structured_fact` 并行处理提供稳定边界。

## 方案对比
### A. 直接改成 LangGraph Send 全并行
- 优点：理论收益最大。
- 缺点：当前图是串行状态机，改动会扩散到路由、状态归属、测试矩阵，风险高。

### B. preprocess fast lane：预编译 goals + 预取外部信息 + 直达 data_expert（本次采用）
- 做法：
  1. 对“编号/分行/显式多问题”在 `preprocess` 直接生成 goals，并发 `plan_ready`；
  2. 若包含 `external.lookup`，在 `preprocess` 直接执行 Tavily 预取并立刻回流 `token`；
  3. 若同时包含 `data.query`，直接编译 canonical handoff，并从 `preprocess` 条件路由到 `data_expert`，跳过 Supervisor 的拆解往返；
  4. 最终仍由 `final_answer` 做唯一收口。
- 优点：不改 reducer、不重写整张图，但能同时改善首 token 和总耗时。
- 风险：外部信息文案更依赖 Tavily 结果清洗质量；英文天气页需额外做中文化收敛，避免把站点原文直接吐给用户；严格来说仍不是真正 fan-out 并行。

## 架构四段式结论
- 模块边界：只改 `app/ai/workflow/multi_agent_graph.py` 的规划/回流层，不把语义判定塞进 `chat_service`。
- 依赖方向：继续由 workflow 依赖已有 goal/delivery 能力，不新增反向依赖。
- 状态归属：`decomposed_goals` 仍是唯一目标状态源；`preprocess` 只预写 `pending_handoff`/外部 ToolMessage，最终正文仍由 `final_answer` 收口。
- 错误处理责任：fast path 命中失败回退现有模型规划；提前回流失败不阻断主链。

## 验证计划
- 单测：
  - 显式双问题命中 fast path，不再调用 planner。
  - `preprocess` 会预取外部信息并直接编译 `data_expert` handoff。
  - Supervisor 自动编译 handoff 时仍能保留提前回流能力。
- 运行态：复测“单次双问题”真实耗时，记录首事件/首有效输出/总完成耗时。
