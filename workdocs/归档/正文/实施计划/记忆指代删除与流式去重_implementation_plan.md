# 记忆指代删除与流式去重 Implementation Plan

## 1. 变更范围
- `app/ai/workflow/multi_agent_graph.py`
- `app/ai/prompts/agent_prompts.py`
- `app/ai/prompts/common_prompts.py`
- `app/services/memory_intent_resolver_service.py`
- `tests/unit/test_multi_agent_streaming_helpers.py`
- `tests/unit/test_memory_intent_resolver_service.py`
- `tests/unit/test_memory_intent_llm_service.py`

## 2. 实施步骤
### Step 1：修正流式去重真理源
- 在 `custom` 事件透传时同步提取 `message/content` 文本并写入 `ctx.collected_content`。
- 保持 values 模式以 `collected_content + emitted_message_ids` 作为统一跳过条件。

### Step 2：收紧 supervisor 路由边界与删除响应合同
- 在 `SUPERVISOR_PROMPT` 明确：记忆/偏好删除与确认不属于待办管理。
- 同时明确：系统支持原生记忆删除，禁止输出“去 Memory 页面手工删除”的 UI 指南。
- 在 `INTENT_CLASSIFY_PROMPT` 明确：此类请求应回到 `supervisor`，不能标成 `todo_management`。

### Step 3：增强 resolver 的确认删除解析
- 将二阶段 reference resolution 的进入条件从“必须有 `recent_memory_reference_candidates`”调整为“存在 `active_preference_candidates` 且存在 `recent_thread_messages`”。
- 增加“最近一轮已确认的删除目标/最近一条 assistant 记忆陈述”语义提示，提升 `删除这个记忆` 与 `1` 这类确认链路的稳定性。
- 保留 `recent_memory_reference_candidates` 作为提示候选，而不是硬门禁。

### Step 4：补回归测试
- 新增 custom clarification -> values replay 不重复的单测。
- 新增 prompt contract 测试，约束 Assistant 不得再输出手工 UI 删除指南。
- 新增确认回复（`1`）沿用已识别删除目标的 resolver 测试。
- 新增无 `recent_memory_reference_candidates` 但有 active candidates/recent messages 时仍能进入 reference resolution 的单测。
- 新增 `resolve_reference_archive` 仅凭 `active_preference_candidates` 也能接受候选 slot 的单测。

## 3. 回滚点
- `multi_agent_graph.py`: 回退 custom 文本登记逻辑。
- `memory_intent_resolver_service.py`: 回退 reference resolution 进入条件。
- `agent_prompts.py` / `common_prompts.py`: 回退路由语义约束文案。

## 4. 验证命令
- `bash scripts/repo_python.sh`
- `bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_memory_intent_resolver_service.py tests/unit/test_memory_intent_llm_service.py -q`
- `eval "$(bash scripts/vk_ports.sh --export)" && lsof -nP -iTCP:${VK_BACKEND_PORT} -sTCP:LISTEN && lsof -nP -iTCP:${VK_FRONTEND_PORT} -sTCP:LISTEN && curl -sf http://127.0.0.1:${VK_BACKEND_PORT}/health`
- 登录后复测 `POST /api/v1/chat/stream` 的记忆删除场景，并核对日志与 DB 状态。
