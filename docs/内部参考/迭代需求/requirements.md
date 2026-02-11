# 2026-02 迭代需求（全量重生版）

> 文档状态：重生草案（基于当前工作区代码事实）
> 
> 生成时间：2026-02-10
> 
> 输入来源：`app/**`、`web/src/**`、`tests/**`、`scripts/**`、`docs/**`、`pyproject.toml`、`.pre-commit-config.yaml`、`web/eslint.config.js`、`web/tsconfig.json`

---

## 1. 需求背景与目标

本轮需求用于承接近期大规模代码调整，目标不是新增单点功能，而是把“问数 + 待办 + 聊天 + 模型路由 + 管理后台”统一收敛到**可持续维护**状态。核心问题集中在：

1. 后端关键测试存在结构性失败，无法支撑稳定迭代。
2. 前端类型与事件协议存在漂移，影响 SSE 多事件链路可靠性。
3. 工作流与接口层边界变得模糊，跨层调用增加维护成本。
4. 文档索引与代码现状出现错位，影响团队协作效率。

本需求作为后续实现与任务拆解的真理来源，不复用旧文案结论。

---

## 2. 范围与排除

### 2.1 本次纳入范围

- 后端业务：`app/**`
- 测试：`tests/**`、`app/tests/**`
- 脚本：`scripts/**`
- 前端：`web/src/**`
- 文档：`docs/**`
- 配置入口：`pyproject.toml`、`.pre-commit-config.yaml`、`web/eslint.config.js`、`web/tsconfig.json`

### 2.2 本次排除范围

- 运行产物与第三方目录：`venv/**`、`venv_test/**`、`venv_fix/**`、`lib_tests/**`、`web/node_modules/**`、`web/.next/**`、`htmlcov/**`、`.pytest_cache/**`、`logs/**`、`data/**`、`ragflow/**`

---

## 3. 银行业务用户故事（模块化）

### 3.1 问数助手

- 作为分行经营分析人员，我希望在“贷款余额/存款余额/分行维度”场景下进行多轮追问，并可在同一会话里补充筛选条件而不被误判为新问题。
- 作为风控与合规岗位，我希望系统严格阻断敏感表访问，且在 `chat_db` 与 `data_db` 之间不串库。
- 作为数据运营人员，我希望问数结果可按规则自动补齐展示字段（如客户名称），减少人工二次解释。

### 3.2 待办助手

- 作为客户经理，我希望“这个/上一个/那个任务”这类隐式指代能被正确关联，不出现重复确认循环。
- 作为团队主管，我希望澄清-确认-执行流程可收敛，且中断后恢复不会重复写入或丢失上下文。

### 3.3 聊天系统（SSE）

- 作为一线用户，我希望流式事件顺序稳定（`status` → `token/result` → `done`），并且 `message_id` 回传后能立即进行点赞点踩。
- 作为运维人员，我希望 interrupt/resume 链路在异常时可观测，便于排查对话中断问题。

### 3.4 模型路由

- 作为平台管理员，我希望按场景配置轻量任务模型与 SQL 生成模型，并具备可回滚、可审计的变更路径。
- 作为开发人员，我希望模型选择策略在测试环境可复现，不因 API Key 依赖导致单测普遍失败。

### 3.5 管理后台

- 作为管理员，我希望通过后台完成问数指标、结果增强规则、路由配置、开发工具等管理动作。
- 作为安全负责人，我希望开发工具接口仅在非生产环境可用，且需管理员权限。

---

## 4. 功能需求（按域）

### 4.1 问数助手需求

1. 问数工作流必须支持会话帧合并（current > handoff > state > default），并保留来源映射用于排障。
2. 问数 SQL 访问控制必须显式区分：白名单、黑名单、系统 schema 限制、元数据只读例外。
3. 结果增强规则必须支持：创建、更新、启停、优先级、测试、缓存刷新。
4. 指标类问题需支持总量、维度拆分、TopN 三种查询形态。

### 4.2 待办助手需求

1. 待办意图分析必须稳定识别 `NEW_QUERY/SUPPLEMENT/CORRECTION/CONFIRM`。
2. 待办确认卡片的数据模型需与后端操作 payload 对齐，避免弱类型断言。
3. `current_todo_id` 在发送前不得被提前清理，确保隐式指代链路可追踪。

### 4.3 聊天系统需求

1. SSE 主链路继续使用 `/api/v1/chat/stream`。
2. 恢复链路保持与当前实现一致（当前代码为 `/api/v1/chat/resume`），并在需求层明确兼容策略。
3. `done` 事件 payload 至少包含 `thread_id`，并可选携带 `message_id/final_content`。
4. interrupt/resume 必须支持人工 accept/reject/edit 三种决策。

### 4.4 模型路由需求

1. 路由配置统一落到 `t_system_config` 键：
   - `model_routing.lightweight`
   - `model_routing.sql_generation`
2. 后台页面提供路由总览、更新与有效性校验。
3. 运行时需优先读取配置中心，环境变量作为回退。

### 4.5 管理后台需求

1. 问数管理与富化规则管理需统一在 `data_admin` 模块内闭环。
2. 开发工具接口 `/api/v1/dev-tools/codex/exec` 仅管理员可用，且在 `ENV=prod` 必须拒绝。
3. 管理能力变更需有审计信息与回归验证命令。

---

## 5. 验收标准

### 5.1 Happy Path

- 用户可完成：
  - 问数多轮补充查询（贷款余额 + 分行维度 + 图表切换）
  - 待办隐式指代补充并成功确认执行
  - 聊天 SSE 完整闭环（含 interrupt/resume）
  - 管理后台完成模型路由与结果增强规则操作

### 5.2 异常与边界

- 输入为空、超长文本、非法字段、越权访问、无效模型代码、无效规则配置时，系统均返回可解释错误。
- 数据访问控制对敏感表与系统 schema 进行拒绝。
- 非生产以外环境禁止调用开发工具接口。

### 5.3 性能与稳定性

- 流式对话在超时后可正确回收状态，不出现前端卡死。
- 关键流程失败时必须有可观测日志（thread_id、trace_id、event_type）。
- 文档与代码索引需可追踪，避免“有实现无文档”或“有文档无入口”。

---

## 6. 非功能需求

### 6.1 安全与合规

- 双数据库隔离：
  - `DATABASE_URL` → `chat_db`
  - `ANALYTICS_DATABASE_URL` → `data_db`（只读）
- 管理接口必须管理员权限；开发工具接口必须受环境限制。

### 6.2 可观测性

- SSE 关键事件统一打点：`init/token/result/interrupt/done/error`。
- 关键状态字段变化需可追溯：`turn_act`、`session_frame`、`clarify_*`、`pending_*`。

### 6.3 一致性

- 前后端共享协议必须具备单一真理来源，避免同名字段不同语义。
- 模块文档与迭代文档术语统一：会话意图内核、SSE 协议、模型路由。

---

## 7. 关联测试矩阵（TC 追溯）

| TC 编号 | 场景 | 关联模块 | 验证入口 |
|---|---|---|---|
| TC-DATA-001 | 问数白名单允许业务表访问 | 问数/权限 | `app/tests/test_data_agent.py` |
| TC-DATA-002 | 问数敏感表拒绝 | 问数/权限 | `tests/api/test_data_chat.py` |
| TC-DATA-003 | 结果增强规则 CRUD + 测试 | 问数管理后台 | `tests/api/test_data_admin_api.py` |
| TC-TODO-001 | 待办隐式指代补充轮收敛 | 待办工作流 | `tests/unit/test_todo_nodes.py` |
| TC-TODO-002 | 待办集成时间解析 | 待办工作流 | `app/tests/test_todo_graph_integration.py` |
| TC-CHAT-001 | SSE done/message_id 回传 | 聊天/SSE | `tests/unit/test_chat_service_done_payload.py` |
| TC-CHAT-002 | 中断恢复链路 | 聊天/SSE | `app/services/chat_service.py` + `web/src/hooks/useSSEStream.ts` |
| TC-MODEL-001 | 模型路由更新与回退 | 模型路由 | `app/api/v1/endpoints/llm_admin_api.py` |
| TC-MODEL-002 | get_llm 多模型回退可测 | 模型基础能力 | `app/tests/test_model_switch.py` |
| TC-ADMIN-001 | dev-tools 环境限制 | 管理后台 | `tests/unit/test_dev_codex_api.py` |
| TC-DOC-001 | 文档治理严格检查 | 文档治理 | `scripts/docs_guard.py --strict` |

---

## 8. 版本化增量（本轮重点）

1. 问数：新增结果增强规则链路与后台管理能力。
2. 待办：引入会话意图内核并强化隐式指代上下文注入。
3. 聊天：增强 SSE `done/message_id/final_content` 生命周期收口。
4. 模型路由：后台可视化更新 + 配置中心优先读取。
5. 管理后台：新增开发工具执行入口（仅开发/测试环境）。

---

## 9. 回归硬门禁（需求层定义）

以下门禁用于后续实施阶段验收：

1. `pytest` 失败收敛到 0（或有明确豁免清单）。
2. `npx tsc --noEmit` 错误为 0。
3. `npm run -s lint` 关键告警按计划清理并可解释。
4. `venv/bin/python scripts/docs_guard.py --strict` 无 error。

---

## 10. 非目标

1. 本文档阶段不直接修改业务接口或数据库结构。
2. 不在本轮需求文档内引入全新业务域。
3. 不将第三方目录纳入结论。
