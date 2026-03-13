# chat-composite-latency-local-refactor UAT Cases

> 日期：2026-03-12
> 对应需求：`docs/内部参考/迭代需求/chat-composite-latency-local-refactor_requirements.md`
> 对应方案：`docs/plans/2026-03-12-chat-composite-latency-local-refactor-design.md`

```yaml
uat_cases:
  - case_id: UAT-CLLR-001
    requirement_ids: [FR-01]
    user_role: 对话终端用户
    preconditions:
      - `/api/v1/chat/stream` 可用
      - 显式复合请求已命中 fast lane
    steps:
      - 发送“先查一下我的待办，再看嘉兴天气”
      - 记录从提交到第一段用户可见正文出现的时间
      - 继续观察最终统一答复
    expected_results:
      - 最终统一答复前出现至少一段用户可见正文
      - `status/tool_start/handoff` 不被当成首个用户可见内容
      - 最终答复仍由统一出口返回
    evidence_type: SSE 事件序列 + 时延记录
    blocking_level: P0

  - case_id: UAT-CLLR-002
    requirement_ids: [FR-02]
    user_role: 高频待办用户
    preconditions:
      - 用户账号下存在可查询待办
      - 复合请求会冻结 `todo.query`
    steps:
      - 发送“先查一下我的待办，再看嘉兴天气”
      - 观察待办子目标的执行结果
    expected_results:
      - 待办查询不进入 `out_of_scope`
      - 待办子目标不进入错误澄清
      - 待办结果按待办域语义返回
    evidence_type: 聊天回放 + 后端结构化日志
    blocking_level: P0

  - case_id: UAT-CLLR-003
    requirement_ids: [FR-03, FR-04]
    user_role: 质量与运维支持
    preconditions:
      - 可构造一个只返回澄清或失败的子目标
    steps:
      - 发送一个“goal A 信息完整、goal B 信息不完整”的复合请求
      - 检查 coverage 与最终答复
    expected_results:
      - `clarify_needed/failed/pending` 不计入 answered_goals
      - final_answer 不出现“已全部覆盖”或等价表述
      - 未完成 goal 被显式标记
    evidence_type: coverage 报告 + 最终答复截图
    blocking_level: P0

  - case_id: UAT-CLLR-004
    requirement_ids: [FR-04]
    user_role: 对话终端用户
    preconditions:
      - 复合请求至少包含两个 must_answer goals
    steps:
      - 发送显式复合请求
      - 观察最终统一答复顺序
    expected_results:
      - 最终答复顺序与用户原始问题顺序一致
      - 已完成与未完成目标混合出现时，仍保持原始顺序
      - 最终答复只出现一个统一收口出口
    evidence_type: 最终答复截图 + SSE 事件序列
    blocking_level: P0

  - case_id: UAT-CLLR-005
    requirement_ids: [FR-05]
    user_role: 质量与运维支持
    preconditions:
      - 系统已开启本轮结构化 timing 观测
    steps:
      - 发送一条显式复合请求
      - 查看 `final_answer.meta` 与 `done.meta`
    expected_results:
      - `final_answer.meta` 含 `first_event_at_ms`
      - `final_answer.meta` 含 `first_visible_at_ms`
      - `final_answer.meta` 含 `final_answer_at_ms`
      - `done.meta` 含 `done_at_ms`
      - 若输出 per-goal timing，则能看到 started/first_visible/terminal/status
    evidence_type: SSE 事件抓取 + 结构化 meta 截图
    blocking_level: P0

  - case_id: UAT-CLLR-006
    requirement_ids: [FR-06]
    user_role: 回归测试人员
    preconditions:
      - 已有单一提问基线
    steps:
      - 发送单一待办查询
      - 发送单一天气查询
      - 对比本轮治理前后的首个可见正文与最终完成耗时
    expected_results:
      - 单一提问不新增无意义澄清
      - 单一提问的首个可见正文无明显回退
      - 单一提问结果质量与既有行为一致
    evidence_type: 基线对比记录 + 时延日志
    blocking_level: P1
```
