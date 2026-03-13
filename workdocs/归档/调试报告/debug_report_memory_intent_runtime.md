# debug_report_memory_intent_runtime

## 1. 问题摘要
- 现象：聊天侧在异步模式下已提示“会处理删除这条长期记忆”，但管理后台中对应记忆仍长期停留在 `active`。
- 影响范围：所有依赖 `memory.intent_async_enabled` 的长期记忆写入与删除，尤其是“记忆确认删除”链路。
- 严重等级：高。用户会误以为系统已经受理且完成删除，实际后台状态未变。

## 2. 根因证据链
- 最终根因：`chat_service` 在异步模式下只负责入队 `t_user_memory_intent_job`，仓内没有运行时入口去常驻消费该队列，也没有 `process_job` 实现把合同写回 `t_user_memory_document`。
- 结构性缺口：现有 `memory_intent_worker_service.run_once()` 只有状态机壳，但缺少 `lifespan -> runtime loop -> process_job` 接线。
- 一致性风险：现有 `flush_canonical_memory()` 默认自带 `commit/rollback`，如果直接塞进 worker，会把“processing”状态提前提交，形成“记忆落库了，但任务状态未收口”的半提交窗口。

## 3. 修复内容
- 新增 `app/core/memory_intent_runtime.py`：负责开关判断、常驻 poller、`process_memory_intent_job()`、运行时启停。
- 修改 `app/main.py`：在 FastAPI `lifespan` 中启动/关闭记忆异步 worker。
- 修改 `app/services/document_memory_service.py`：为 `flush_canonical_memory()` 增加 `manage_transaction` 参数，让记忆落库与 job 状态机共用同一事务。

## 4. 验证命令与结果
- 目标/实际仓库：`/Users/jijingkun/bojxAI/fastapi`，结论 `VERIFY_CONTEXT_OK`。
- 测试解释器：`bash scripts/repo_python.sh` -> `/Users/jijingkun/bojxAI/fastapi/venv/bin/python`
- 回归：`bash scripts/pytest_targeted.sh tests/unit/test_memory_intent_runtime.py tests/unit/test_document_memory_service_worker_transaction.py tests/unit/test_memory_intent_worker_service.py tests/unit/test_chat_service_memory_flags.py tests/unit/test_document_memory_service.py -q` -> `34 passed`

## 5. 风险、回滚点与后续建议
- 回滚点：关闭 `memory.intent_async_enabled` 或 `ENABLE_DOCUMENT_MEMORY`。
- 剩余风险：当前只补齐了记忆意图 worker；embedding 补偿仍未接常驻运行时。
- 后续建议：若后续确认异步写入与 embedding 都要常驻化，应把 embedding 补偿也接入同一套 runtime 生命周期。
