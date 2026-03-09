# debug_report_memory_delete_streaming

## 1. 问题摘要
- 现象:
  - 用户第二次发起“删除这个记忆”时，回复曾出现重复。
  - 回复曾退化成“去 Memory 页面手工删除”，与系统真实能力不符。
  - 在“删除这个记忆 -> 1”确认链路中，第二轮确认曾口头说会继续执行，但数据库没有真正归档。
- 影响范围:
  - `todo_expert` 澄清链路的 custom/value 双分发。
  - Supervisor 对记忆删除请求的语义路由。
  - `memory_intent_resolver_service` 的二阶段候选解析与确认链承接。
  - `chat_service` 对“已删除 / 已处理”回复语义的运行时注入。
- 严重等级:
  - 高。直接影响用户对“是否真的删除了记忆”的信任。

## 2. 根因证据链
- 最终根因:
  1. `todo_enhanced_nodes` 发出 `clarification` custom 事件后，`multi_agent_graph` 没把该文本登记进 `ctx.collected_content`，随后 values 模式把同一条 AIMessage 又补发一次，形成重复回复。
  2. 用户的“删除这个记忆”请求被 Supervisor 误委派给 `todo_expert`；同时 resolver 的二阶段解析曾被 `recent_memory_reference_candidates` 这个 lexical 命中前置卡住，导致即使 active candidates 与最近消息足够，也不会继续解析。
  3. prompt 未明确“系统具备原生记忆删除能力”，模型会保守生成“去 Memory 页面手工删除”的 UI 指南。
  4. 删除确认指导若混在 `memory_context`，会污染“当前记忆上下文是否已清空”的真理；因此必须拆成独立运行时字段，而不是继续堆在记忆注入文本里。
  5. 最新一轮真实运行态复测受外部模型配额阻断：OpenAI 返回 `429 DAILY_LIMIT_EXCEEDED`，后端统一降级为“系统繁忙”，导致无法在真实 LLM 路径上完成最终验收。
- 被排除假设:
  - 前端渲染重复：已排除。后端日志中同一轮请求同时出现 `透传 custom 事件` 与 `values 模式补发消息`。
  - 数据库 archive 能力缺失：已排除。历史目标槽位 `user.profile.relationship.parent.of` 在数据库中已有 `archived` 记录。
  - 当前 worktree 未生效：已排除。运行进程 cwd、端口与日志都指向 `/Users/jijingkun/.codex/worktrees/ac8e/fastapi`。
  - 本轮失败由新补丁引起：已排除。最新失败来自模型供应侧 `429`，不是应用内异常。

## 3. 修复内容
- 修改文件:
  - `app/ai/workflow/multi_agent_graph.py`
  - `app/ai/prompts/agent_prompts.py`
  - `app/ai/prompts/common_prompts.py`
  - `app/ai/state.py`
  - `app/services/chat_service.py`
  - `app/services/document_memory_service.py`
  - `app/services/memory_intent_llm_service.py`
  - `app/services/memory_intent_resolver_service.py`
  - `tests/unit/test_multi_agent_streaming_helpers.py`
  - `tests/unit/test_memory_intent_resolver_service.py`
  - `tests/unit/test_memory_intent_llm_service.py`
  - `tests/unit/test_chat_service_memory_flags.py`
  - `tests/unit/test_memory_route_prompt_contract.py`
  - `docs/plans/2026-03-08-memory-intent-runtime-followup-design.md`
  - `docs/内部参考/迭代需求/记忆指代删除与流式去重_requirements.md`
  - `docs/内部参考/迭代需求/记忆指代删除与流式去重_implementation_plan.md`
- 关键符号:
  - `_collect_custom_mode_text_segments`
  - `_remember_custom_mode_text`
  - `_build_memory_archive_response_guidance`
  - `_build_recent_dialogue_context`
  - `_should_attempt_reference_resolution`
  - `_collect_reference_candidate_slot_keys`
- 修复说明:
  - 在 custom 事件透传后同步登记 `message/content` 文本，供 values 模式统一去重。
  - 在 Supervisor / intent classify prompt 中明确“记忆/偏好删除不属于 todo_management，应保持 supervisor 处理”，并补充“系统具备原生删除能力，不得让用户去 UI 手工删除”的响应合同。
  - 将删除确认指导从 `memory_context` 中拆分为独立 `response_guidance_context`，避免污染“记忆上下文已清空”的语义。
  - 在 resolver 上补齐确认链上下文：新增 `latest_assistant_message`、`latest_user_message_before_source`，并允许用 `active_preference_candidates + recent_thread_messages` 进入二阶段解析；确认轮额外接受 `archived_preference_candidates`，避免“上一轮已删，本轮还在口头继续执行”。
  - 在 LLM slot 白名单校验中纳入 `archived_preference_candidates`，确保确认轮只能引用真实候选，不允许模型凭空造 slot。
  - 本轮补充收敛：`tests/unit/test_chat_service_memory_flags.py` 将旧断言“系统已确认”更新为新合同“系统已完成”，与 `response_guidance_context` 的正式语义保持一致。

## 4. 验证证据
- 上下文观测:
  - `pwd` -> `/Users/jijingkun/.codex/worktrees/ac8e/fastapi`
  - `git branch --show-current` -> `vk/936c-`
  - `git worktree list` 已确认当前 worktree 在 `/Users/jijingkun/.codex/worktrees/ac8e/fastapi`
- `jjk-verify` 比对:
  - 目标 worktree: `/Users/jijingkun/.codex/worktrees/ac8e/fastapi`
  - 实际 `pwd` / `git rev-parse --show-toplevel` 均为该路径
  - 结论: 上下文一致，允许测试
- 测试解释器:
  - `bash scripts/repo_python.sh` -> `/opt/homebrew/bin/python3`
  - 测试实际以 `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv` 运行
- 回归命令:
  - `export VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv && bash scripts/pytest_targeted.sh tests/unit/test_memory_route_prompt_contract.py tests/unit/test_memory_intent_resolver_service.py tests/unit/test_chat_service_memory_flags.py tests/unit/test_memory_intent_llm_service.py -q`
  - `export VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv && bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_memory_intent_resolver_service.py tests/unit/test_memory_intent_llm_service.py tests/unit/test_chat_service_memory_flags.py tests/unit/test_document_memory_service.py tests/unit/test_memory_route_prompt_contract.py -q`
- 测试结果:
  - 最小定向集：`31 passed`（新增 recent archived confirm 红灯后转绿）
  - 扩展定向集：`98 passed`
- 运行态结果:
  - `bash scripts/vk_dev.sh status` 显示 backend `127.0.0.1:8230`、frontend `127.0.0.1:3652` 均在运行。
  - `curl -i http://127.0.0.1:8230/api/v1/health` -> `HTTP/1.1 200 OK` + `{"status":"ok"}`。
  - 修复前真实线程：`verify-parent-delete-1772984403`
    - 第 3 轮 `source_message_id=5395` 已成功 archive
    - 第 4 轮 `source_message_id=5397` 仍是 `low_confidence`
  - 修复后真实线程：`verify-parent-delete-fix-1772986658`
    - 四轮消息均成功写入 `t_chat_message`
    - 用户可见回复统一退化为“模型服务当前不可用（配额/订阅或权限异常）...”
    - 第 3/4 轮 `source_message_id=5433/5435` 不再是 `low_confidence`，而是上游 classifier `llm_invoke_failed`
    - 说明“确认链结构缺口”已由代码侧收口，但真实用户回复仍被外部模型不可用阻断，暂无法完成最终 LLM 验收
- 数据库核验:
  - 历史目标槽位 `user.profile.relationship.parent.of` 当前可见记录：`id=16, user_id=2, status=archived, operation=archive, source_thread_id=verify-memory-delete-20260308-1, source_message_id=5327`
  - 最新真实复测线程未产生新 active/archived 记录，原因与 `429` 外部阻断一致。

## 5. 风险与回滚
- 风险:
  - 当前 OpenAI 日配额耗尽，无法用真实模型完成最后一轮运行态 LLM 验收；因此“单元/定向回归已通过”与“真实用户链路已最终通过”不能画等号。
  - 现有 worktree 中累计未提交改动较大，后续若继续叠加，应先收口当前 memory delete 主题再扩散。
- 回滚点:
  - `app/ai/workflow/multi_agent_graph.py`：回退 custom 文本登记逻辑。
  - `app/services/memory_intent_resolver_service.py`：回退 reference resolution 进入条件与 archived candidate 接入。
  - `app/services/chat_service.py` / `app/ai/state.py`：回退 `response_guidance_context` 注入链。
  - `app/ai/prompts/agent_prompts.py` / `app/ai/prompts/common_prompts.py`：回退记忆删除不进 todo 的语义约束。

## 6. 下一步建议
- 配额恢复后，优先执行一次真实 `/api/v1/chat/stream` 四步复测：
  1. `永远记住，我是纪宇圩的爸爸`
  2. `谁是纪宇圩的爸爸`
  3. `删除这个记忆`
  4. `1`
- 验收标准:
  - 第 2 步不再重复回复。
  - 第 3 步不再出现“去 Memory 页面手工删除”。
  - 第 4 步回复应为“已删除 / 已处理，无需重复确认”，而不是“我继续执行”。
  - 数据库 `user.profile.relationship.parent.of` 最终状态为 `archived`。
