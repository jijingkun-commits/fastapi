# 待办补充“答非所问”诊断与修复计划（`/pc`）

## 0. 时间线与证据（本次会话）

- **2026-02-18 13:03:38**：系统生成待办确认消息（`t_chat_message.id=4562`），文案为“直接说确认即可创建，或拒绝告诉我补充内容”。
- **2026-02-18 13:03:43**：前端触发 `POST /api/v1/chat/resume`，`decision={'type':'reject'}`；后端进入拒绝分支并返回“好的，已取消操作”（`id=4563`）。
- **2026-02-18 13:03:50**：用户输入“需要带纸和笔”（`id=4564`）。
- **2026-02-18 13:04:01**：`todo_graph.analyze_intent` 识别为 `update + need_clarify`，`missing=['target_todo']`，且 `response_message` 非空；但 `clarify_node` 仍走“response_message 为空”兜底，最终回复“还需要您补充：target_todo”（`id=4565`）。

> 结论：这是**设计与实现契约不一致 + 状态类型收敛缺陷**叠加导致，不是单点偶发。

---

## 1. 问题摘要

### 1.1 问题描述

用户按提示补充待办信息（“需要带纸和笔”）后，系统未把补充信息并入刚才待确认的创建草稿，而是输出技术字段 `target_todo`，出现“答非所问”。

### 1.2 根本原因（Root Cause）

1. **确认交互语义冲突（主因）**
   - 确认文案引导“拒绝=补充内容”，但执行语义是“拒绝=取消操作并清空上下文”。
   - 代码证据：`wait_for_confirmation` 对 `reject` 直接置 `user_confirmed=False`；`execute_operation` 收到 `False` 后直接返回取消文案并清空 `pending_operation`。

2. **Todo 状态类型双定义不一致（关键实现缺陷）**
   - `todo_graph.py` 内部 `TodoAgentState` 含 `response_message`，但 `todo_enhanced_nodes.py` 使用 `app.ai.state.TodoAgentState`（不含 `response_message`）。
   - 在图执行中，`clarify_node` 入参被按旧类型裁剪，导致明明已生成的 `response_message` 在澄清节点不可见，触发错误兜底。

3. **缺项字段未做用户态映射（体验缺陷）**
   - `pending_clarifications` 直接透传模型 `missing_info`，兜底拼接时把内部槽位名 `target_todo` 原样暴露给用户。

4. **与需求文档偏离**
   - `docs/产品文档/待办助手需求.md` §3.4 明确要求“拒绝后补充应恢复同一创建草稿”，当前实现未落地。

### 1.3 影响范围

- 待办创建确认后的补充场景（高频路径）。
- 所有可能走 `need_clarify` 兜底的场景（存在内部字段泄露风险）。
- 多智能体链路下 todo_expert 的补充轮稳定性。

### 1.4 严重程度

- **P1（高优）**：核心功能可用性明显受损，且与产品定义冲突。

---

## 2. 修复方案

### 2.1 方案概述

分两阶段修复：

1. **P0热修（先止血）**：统一确认文案与拒绝语义，修复 `response_message` 丢失，禁止内部字段外泄。
2. **P1能力补齐**：实现“拒绝后补充恢复创建草稿”的完整状态机链路，补齐测试与文档追溯。

### 2.2 涉及文件与修改点清单

#### `app/ai/state.py`
- [ ] 将 `response_message` 纳入 `TodoAgentState`（或 `BaseAgentState`）统一契约。
- [ ] 对齐 `todo_graph.py` 与全局状态定义，消除重复定义漂移。

#### `app/ai/workflow/todo_graph.py`
- [ ] `ask_confirmation` 文案与行为对齐：若 `reject` 语义为“取消”，文案不得再引导“拒绝后补充”。
- [ ] `wait_for_confirmation` 增加“拒绝后补充恢复草稿”判定分支（满足需求文档 §3.4 条件时，不直接取消）。
- [ ] `execute_operation` 对恢复场景不清空 `pending_operation`，转入 `need_confirm` 或 `need_clarify`。
- [ ] 将 `missing_info` 做用户态规范化映射，禁止 `target_todo/todo_id` 等内部字段直出。

#### `app/ai/agents/todo_enhanced_nodes.py`
- [ ] `clarify_node` 兜底文案改为用户可理解字段名（如“目标待办”），不透出内部键名。
- [ ] 增加保护：若 `response_message` 不为空，兜底逻辑不应覆盖。

#### `app/ai/prompts/todo_prompts.py`
- [ ] 明确约束 `missing_info` 仅允许中文用户态描述，禁止输出 schema/internal slot 名。
- [ ] 增补“确认后补充/拒绝后补充”few-shot，降低模型歧义。

#### `web/src/components/chat/CompactApproval.tsx`
- [ ] 将“拒绝”按钮文案调整为“取消本次操作”（与后端语义一致）。
- [ ] 若产品决定支持“拒绝并补充”，需新增独立按钮（非 `reject`）并走对应 resume 类型。

#### `tests/unit/test_todo_nodes.py`
- [ ] 新增 `TODO-TC-005`：拒绝后补充应恢复创建草稿（按需求文档）。
- [ ] 新增回归：澄清消息不得包含 `target_todo` 等内部字段。
- [ ] 新增回归：`response_message` 在 `analyze -> clarify` 链路不得丢失。

#### `web/e2e/*`（建议新增）
- [ ] 增加确认卡片交互 E2E：`确认 / 取消 / 补充后继续` 三分支。
- [ ] 增加真实对话回归：`明天9点开会 -> 拒绝 -> 补充“带纸和笔”`。

### 2.3 数据库变更

- 无 DDL/DML 变更。

### 2.4 配置变更

- 无环境变量变更。

---

## 3. 风险评估

1. **行为兼容风险**：`reject` 语义若调整，可能影响现有“快速取消”用户习惯。
2. **状态机分支风险**：恢复草稿逻辑若判定过宽，可能误把真实新任务当旧草稿继续。
3. **多智能体一致性风险**：Supervisor 与 todo_expert 对 `turn_act_hint/frame` 约束不一致会再次引发偏航。

### 回滚方案

- 若上线后出现误恢复，先回滚到“reject=取消”但保留文案修正与字段脱敏。
- 保留日志埋点开关，可快速定位恢复分支命中条件。

---

## 4. 验证计划

### 4.1 单元测试

- `pytest tests/unit/test_todo_nodes.py -k "reject or clarify or response_message" -q`

### 4.2 集成测试

- `pytest app/tests/test_todo_graph_integration.py -q`
- `pytest app/tests/test_todo_multiround.py -q`

### 4.3 手动验证（核心用例）

1. 输入：`明天上午9点去陆家嘴和张三开会`。
2. 在确认卡片执行“拒绝/取消”后，补充：`需要带纸和笔`。
3. 预期：
   - 不出现 `target_todo` 等内部字段；
   - 按需求策略要么恢复同一草稿并再次确认，要么明确提示“已取消，是否重新创建”，行为与文案一致。

### 4.4 回归验证

- 选中待办补充（`current_todo_id`）场景不回归。
- 非待办问答（天气/问数）路由不回归。

---

## 5. 预防措施

1. **状态单一真相**：Todo 状态定义只保留一份（禁止本地重复 TypedDict 漂移）。
2. **契约测试前置**：新增“用户可见文案不得包含内部字段名”自动化断言。
3. **交互语义审计**：确认卡片的按钮语义、文案语义、后端决策语义三方一致性纳入 CI 检查清单。
4. **日志增强**：记录 `decision.type`、`pending_operation.action`、`turn_act` 组合，支持快速溯源。

---

## 6. 实施建议

- 优先级：**高优先级，建议当日修复（P1）**。
- 建议顺序：
  1. 状态定义统一（先消除 `response_message` 丢失）；
  2. 文案与按钮语义对齐；
  3. 恢复草稿逻辑落地；
  4. 测试补齐与回归。
- 预计工作量：**0.5~1 人日**（含测试）。
- 建议分阶段：**是**（先止血后补齐能力）。

---

## 7. 文档关联检查

- [x] 需求文档：`docs/产品文档/待办助手需求.md`
- [ ] 测试案例：`docs/开发文档/测试管理/待办助手测试案例.md`
- [ ] 架构文档：`docs/开发文档/架构设计/待办Agent设计.md`
- [ ] AI 总体架构：`docs/开发文档/架构设计/AI模块设计.md`
- [ ] API 文档：`docs/API文档/接口文档.md`（若 resume 决策类型扩展）
- [ ] 防屎山记录：`docs/开发文档/架构设计/防屎山记录手册.md`（若引入兼容分支/SP）

---

## 附：已核验的关键证据点

1. `logs/assistant.log`：`decision=reject`（13:03:43）后立即走取消路径并清空操作状态。
2. `t_chat_message`：`4562(确认文案) -> 4563(已取消) -> 4564(补充) -> 4565(target_todo 泄露)`。
3. 最小复现实验：在图内 `analyze_intent` 可生成 `response_message`，但进入 `clarify_node` 后被判空；直接调用 `clarify_node` 则可正常使用 `response_message`。
4. 状态差异确认：`app.ai.workflow.todo_graph.TodoAgentState` 比 `app.ai.state.TodoAgentState` 多出 `response_message` 字段，存在契约漂移。
