# Memory Intent Resolver + Contract 重构 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 回退上一轮落在 `chat_service` 的删除词表补丁，重构为 `resolver + contract`，让 AI 在异步记忆链路中自行判断反向记忆与目标定位。

**Architecture:** 先更新设计文档与长期决策，再新增 `memory_intent_resolver_service` 统一构建上下文与装配持久化合同；`chat_service` 退化为 enqueue/flush/recall 编排层，`memory_intent_llm_service` 提供主判定与候选目标解析两个 JSON 合同入口，`document_memory_service` 继续作为最终写入真理源。

**Tech Stack:** FastAPI、Python、LangChain lightweight LLM、SQLAlchemy、pytest

---

### Task 1: 写文档并冻结口径

**Files:**
- Create: `workdocs/归档/正文/设计/2026-03-08-memory-intent-resolver-contract-design.md`
- Create: `workdocs/归档/正文/设计/2026-03-08-memory-intent-resolver-contract-plan.md`
- Modify: `memory-bank.md`

**Step 1: 写设计文档**
- 冻结模块边界、resolver 合同、异步主链口径与立即刷新规则。

**Step 2: 写实施计划**
- 列出要新增/修改的服务、提示词、测试文件与定向验证命令。

**Step 3: 更新长期决策记录**
- 记录“memory intent 删除解析从 chat_service 迁移到 resolver”的长期决策。

**Step 4: 自检文档同步**
Run: `rg -n 'resolver|contract|异步|chat_service|normalized_value' workdocs/归档/正文/设计/2026-03-08-memory-intent-resolver-contract-*.md memory-bank.md`
Expected: 设计文档、计划文档和 memory-bank 都能检索到统一口径。

### Task 2: 先写 resolver 侧失败测试

**Files:**
- Create: `tests/unit/test_memory_intent_resolver_service.py`
- Modify: `tests/unit/test_memory_intent_llm_service.py`

**Step 1: 写 resolver 上下文测试**
- 覆盖 `active_preference_candidates`、`recent_thread_messages`、`recent_memory_reference_candidates` 的构造。

**Step 2: 写 resolver 目标解析测试**
- 覆盖 primary accept 直通、primary reject 后 reference resolve 成功、reference ambiguous 需要澄清。

**Step 3: 写 LLM 目标解析测试**
- 覆盖 `resolve_reference_archive(...)` 的候选约束：只允许命中候选 slot_key，且仅允许单条 archive item。

**Step 4: 定向跑红灯**
Run: `export VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv && bash scripts/pytest_targeted.sh tests/unit/test_memory_intent_resolver_service.py tests/unit/test_memory_intent_llm_service.py -q`
Expected: 新增测试先失败，提示 resolver/service 尚未实现或断言不满足。

### Task 3: 实现 resolver + LLM 合同入口

**Files:**
- Create: `app/services/memory_intent_resolver_service.py`
- Modify: `app/services/memory_intent_llm_service.py`
- Modify: `app/ai/prompts/agent_prompts.py`

**Step 1: 新增 resolver 服务**
- 提供上下文构造、audit 补全、主判定与候选解析编排，统一输出 `resolution_status + persistence_contract`。

**Step 2: 扩展 LLM 服务**
- 新增候选目标解析 prompt 调用入口，并复用现有 JSON 合同归一化与敏感信息守卫。

**Step 3: 删除 chat_service 词表所依赖的专用 contract 逻辑**
- 保证“是否是删除记忆、删哪条”只由 resolver / LLM 输出。

**Step 4: 跑 resolver 侧测试**
Run: `export VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv && bash scripts/pytest_targeted.sh tests/unit/test_memory_intent_resolver_service.py tests/unit/test_memory_intent_llm_service.py -q`
Expected: resolver 与 LLM 测试通过。

### Task 4: 瘦身 chat_service 并修正同步上下文刷新

**Files:**
- Modify: `app/services/chat_service.py`
- Modify: `tests/unit/test_chat_service_memory_flags.py`

**Step 1: 拔掉 chat_service 词表和修复式补丁**
- 删除 `_REVERSE_INTENT_HINTS`、`_DEICTIC_MEMORY_HINTS`、指代修复、成功/失败 guidance 注入相关逻辑。

**Step 2: 改成 resolver 调用**
- 同步降级路径只拿 `persistence_contract` 送 `flush_document_memory(...)`；异步模式保持 enqueue-only。

**Step 3: 修正即时 memory_context 刷新语义**
- `_persist_document_memory_context(...)` 改为显式返回“是否更新上下文”，允许 archive 后用空字符串覆盖旧注入结果。

**Step 4: 跑 chat_service 定向测试**
Run: `export VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv && bash scripts/pytest_targeted.sh tests/unit/test_chat_service_memory_flags.py -q`
Expected: flags 与同步降级路径测试通过，旧的关键词断言已移除。

### Task 5: 端到端定向回归

**Files:**
- Modify: 无（验证）

**Step 1: 运行记忆链路定向回归**
Run: `export VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv && bash scripts/pytest_targeted.sh tests/unit/test_memory_intent_resolver_service.py tests/unit/test_memory_intent_llm_service.py tests/unit/test_chat_service_memory_flags.py tests/unit/test_document_memory_service.py -q`
Expected: 全部通过。

**Step 2: 静态检查关键词已拔除**
Run: `rg -n '_REVERSE_INTENT_HINTS|_DEICTIC_MEMORY_HINTS|_repair_referential_archive_decision|删除记忆请求已经执行成功|不要声称已经删除' app/services/chat_service.py`
Expected: 无命中。

**Step 3: 汇总结论**
- 给出删除清单、结构收敛点、保留的底层合同修复与验证结果。
