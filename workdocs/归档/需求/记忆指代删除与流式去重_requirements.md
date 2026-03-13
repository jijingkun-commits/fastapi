# 记忆指代删除与流式去重 Requirements

## 1. 背景
- 现有 `resolver + contract` 重构已把删除词表从 `chat_service` 中拔掉，但运行态仍暴露两个问题：
  - todo 澄清场景的 custom 事件与 values replay 造成重复回复。
  - “这是记忆吧？帮我删除这个记忆”会误进 `todo_expert`，且 resolver 在无 recent lexical hit 时不会进入二阶段候选解析。
- 项目未上线，以结构正确和职责收口为最高优先级。

## 2. 最终需求
1. 流式层必须保证同一条用户可见文本只对前端发一次；custom 已发出后，values 不得重复补发。
2. 讨论/撤销/删除长期记忆的请求必须留在 supervisor/general reply 链路，不能误委派 `todo_expert`。
3. resolver 的二阶段候选解析必须允许 AI 基于 `active_preference_candidates + recent_thread_messages` 自主定位目标，不能被 lexical `recent_memory_reference_candidates` 前置卡死。
4. Assistant 在确认系统已具备原生删除能力时，不得输出“我无法直接删除 / 请去 Memory 页面手工删除”的保守文案。
5. 若上一轮已唯一识别删除目标，本轮确认回复（如“1”）应继续沿用该目标，而不是重新退化到 UI 指南。
6. 最终 archive 合同的 `slot_key` 仍必须来自候选集合，不能放松到模型自由生成。
7. 保持“记忆在对话结束后异步处理，不影响主对话响应时长”的运行时口径不变。

## 3. 非目标
- 不新增前端去重逻辑。
- 不恢复 `chat_service` 删除关键词词表。
- 不修改数据库表结构或新增路由类型。

## 4. 验收标准
- 真实流式链路中，澄清类 custom 事件不再导致 values replay 重复输出。
- “这是记忆吧？帮我删除这个记忆”不再出现 `assign_to_todo_expert` 越权路径。
- 目标记忆在数据库中由 `active` 变为 `archived`。
- 定向回归覆盖 streaming helper、resolver、LLM candidate contract。
