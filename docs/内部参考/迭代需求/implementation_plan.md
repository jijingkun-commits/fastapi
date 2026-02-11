# 2026-02 实施方案（全量重生版）

> 文档状态：实施规划草案（不改代码，仅定义执行方案）
> 
> 生成时间：2026-02-10
> 
> 对齐输入：当前工作区代码 + 实测质量基线



---

## 0. 文档分层与引用关系

1. 本文档（`implementation_plan.md`）是本轮迭代唯一主计划，负责范围、门禁、优先级与任务排期。
2. `implementation_plan_多智能体上下文管理重构.md` 作为 WS-01 的专项架构附录，仅覆盖“父子图上下文契约/适配层/记忆分层”能力。
3. 执行顺序：先满足主计划 P0 门禁，再按 WS-01 引用附录推进 Phase 1~4，避免架构改造与阻断修复互相打断。
4. 若主计划与附录存在冲突，以主计划的质量门禁与业务兼容约束为准。

---
## 1. 审查上下文与证据快照

### 1.1 工作区上下文

- 分支：`master`
- 基线提交：`4811b4f`（2026-02-07）
- 当前工作区：存在大量未提交改动（`git status` 统计 144 条）
- 差异规模：`git diff --stat` 显示 96 个文件变更，约 `+8057 / -1590`

### 1.2 工具版本

- `venv/bin/python --version` → Python 3.11.12
- `node --version` → v24.13.0
- `npm --version` → 11.6.2
- `venv/bin/python -m pytest --version` → pytest 9.0.2

### 1.3 自动化基线命令结果（最新重跑）

| 命令 | 退出码 | 结果摘要 |
|---|---:|---|
| `venv/bin/python -m compileall -q app scripts tests` | 0 | 编译通过 |
| `venv/bin/python -m pytest --collect-only -q` | 0 | 收集 414 条用例（47 个文件） |
| `venv/bin/python -m pytest -q --maxfail=20` | 1 | 13 个失败（见 2.1） |
| `cd web && npm run -s lint` | 0 | 40 条 warning（unused vars/fast-refresh/hooks） |
| `cd web && npx tsc --noEmit` | 2 | 2 个 error（`ConfirmationCard.tsx:67/79`） |
| `venv/bin/python scripts/docs_guard.py --strict` | 0 | 已通过（0 error，4 warning；初次采集曾为 1） |

---

## 2. 问题归因（根因聚合）

### 2.1 P0：阻断级问题

#### P0-1 测试基线阻断（13 fail）

- 证据链：`pytest -q --maxfail=20`
- 根因聚合：
  1. **数据访问控制默认白名单与测试契约失配**
     - 失败点：`app/tests/test_data_agent.py:135`、`app/tests/test_data_agent.py:164`、`tests/api/test_data_chat.py:211`
     - 触发点：`app/ai/semantic/data_access_control.py:209` 拒绝 `t_orders`
  2. **模型初始化在无密钥场景不可测**
     - 失败点：`app/tests/test_model_switch.py` 多个 case
     - 触发点：`app/ai/llm_util.py:431` 抛 `ValueError(API Key 缺失)`
  3. **待办集成测试 patch 路径漂移**
     - 失败点：`app/tests/test_todo_graph_integration.py`
     - 触发点：mock 目标 `app.ai.agents.todo_graph` 不存在，当前实现位于 `app.ai.workflow.todo_graph`
  4. **异步测试运行时依赖缺口**
     - 失败点：`app/tests/test_todo_multiround.py`
     - 触发信息：`async def functions are not natively supported`

#### P0-2 前端类型检查阻断

- 证据链：`npx tsc --noEmit`
- 失败点：`web/src/components/todo/ConfirmationCard.tsx:67`、`web/src/components/todo/ConfirmationCard.tsx:79`
- 根因：`Record<string, unknown>` 与 `TodoItem` 的双向断言/传参契约不一致。

#### P0-3 文档治理严格模式（已修复，纳入持续门禁）

- 证据链：`scripts/docs_guard.py --strict`
- 根因聚合：
  1. `docs/SUMMARY.md` 存在失效链接：`开发文档/规范/贡献指南.md`
  2. 多个文档未纳入 `docs/SUMMARY.md` 索引（含 `implementation_plan.md`）

### 2.2 P1：高维护成本问题

#### P1-1 分层边界被绕过

- 证据：
  - `app/api/v1/endpoints/chat_api.py` 直接依赖 `chat_repo`
  - `app/api/v1/endpoints/data_admin_api.py` 直接依赖 `ResultEnrichmentRuleRepo`
  - `app/api/v1/endpoints/data_admin_api.py:1132` 直接调用 `app.ai.workflow.data_graph._apply_lookup_enrichment_rule`
- 影响：Endpoint/Service/Workflow 边界模糊，改动波及面不可控。

#### P1-2 超大文件集中化导致变更风险

- Python 热点（>600 行）：
  - `app/ai/workflow/data_graph.py`（2965）
  - `app/ai/workflow/todo_graph.py`（1867）
  - `app/api/v1/endpoints/data_admin_api.py`（1200）
- TS 热点（>350 行）：
  - `web/src/components/admin/DataAdminPanel.tsx`（909）
  - `web/src/lib/backend.ts`（712）
  - `web/src/hooks/useSSEStream.ts`（474）
- 影响：单文件承担过多职责，回归成本与冲突概率上升。

#### P1-3 SSE 协议与类型契约存在漂移风险

- 证据：
  - 后端 `done` payload 可带 `thread_id/message_id/final_content`（`app/services/chat_service.py:352`, `:373`）
  - 前端 `onDone` 仅显式消费 `thread_id/message_id`（`web/src/lib/backend.ts:318`）
  - 前端统一消息模型和 `additional_kwargs` 逻辑分散在多处
- 影响：协议增量字段难以稳定落地，易形成“后端有字段、前端未消费”的隐性债务。

#### P1-4 Pydantic v2 迁移债务

- 证据：`class Config:` 在接口模型中仍存在多处（如 `chat_api.py:51`、`data_admin_api.py:51`、`llm_admin_api.py:39`）
- 影响：升级到 Pydantic v3 存在集中回归风险。

### 2.3 P2：中长期高回报优化

1. 前端 lint 警告聚类治理：40 条 warning 中，`@typescript-eslint/no-unused-vars` 占 27 条。
2. 测试分层与标记规范化（unit/integration/e2e + async 运行策略）。
3. 文档目录索引自动校验前置（提交前快速失败）。

---

## 3. 架构变更方案

### 3.1 总体变更方向

1. 统一“会话意图内核 + 工作流状态契约”在后端 workflow 层落地。
2. 统一“事件协议 + 前端消息模型”在 SSE 接口边界落地。
3. 统一“模型路由 + 管理后台配置”在配置中心和管理 API 落地。
4. 统一“结果增强规则”在数据管理域闭环（模型/仓储/服务/API）。

### 3.2 关键模块影响

- AI 工作流：`app/ai/workflow/*`（尤其 `data_graph.py`、`todo_graph.py`、`session_intent_kernel.py`）
- 接口与服务：`app/api/v1/endpoints/*`、`app/services/*`
- 数据模型：`app/models/result_enrichment_rule.py`
- 前端聊天链路：`web/src/hooks/useSSEStream.ts`、`web/src/lib/backend.ts`、`web/src/types/message.ts`

---

## 4. API 设计与兼容策略

### 4.1 保持兼容的公共接口

- `POST /api/v1/chat/stream`：继续作为 SSE 主链路。
- 聊天历史与反馈相关接口维持现有语义（`/api/v1/chat/threads*`、`/api/v1/chat/feedback`）。

### 4.2 中断恢复接口

- 当前代码事实：`POST /api/v1/chat/resume`（`chat_api.py`）
- 兼容策略：
  1. 文档统一记录当前主路径为 `/resume`
  2. 若外部依赖仍使用 `/resume-stream`，在实施阶段评估是否增加别名路由

### 4.3 管理接口（开发环境约束）

- `POST /api/v1/dev-tools/codex/exec`
- 约束：管理员权限 + `ENV != prod`（`dev_codex_api.py`）

### 4.4 SSE 事件契约（重点）

- 关键事件：`token/thinking/status/result/interrupt/done/error`
- `done` 建议规范：
  - 必选：`thread_id`
  - 可选：`message_id`、`final_content`
- 兼容策略：前端回调保持向后兼容，允许忽略新增字段但不得误判生命周期。

---

## 5. 数据与配置设计

### 5.1 结果增强规则

- 数据表：`t_result_enrichment_rule`、`t_result_enrichment_rule_audit`
- 能力：规则 CRUD、启停、优先级、审计、缓存刷新。

### 5.2 双数据库约束

- `DATABASE_URL` → `chat_db`
- `ANALYTICS_DATABASE_URL` → `data_db`（只读）
- 实施原则：分析查询走 analytics 会话，不允许反向写入。

### 5.3 路由配置中心

- 键：`model_routing.lightweight`、`model_routing.sql_generation`
- 来源优先级：`t_system_config` > 环境变量回退

---

## 6. 架构影响与约束（五项必查）

### 6.1 模块边界

- 目标：Workflow 只负责决策与状态机，Endpoint 只负责协议与鉴权，Service 负责业务编排。
- 当前风险：存在 endpoint 直连 repository/workflow 私有函数的情况。
- 约束：实施时禁止新增跨层直连。

### 6.2 状态契约

- 关键字段：`session_frame`、`frame_source_map`、`turn_act`、`clarify_fsm_state`、`clarify_round`、`pending_operation`。
- 约束：同一字段语义只能有一个 canonical 写入点。

### 6.3 路由闭环

- 目标链路：意图分析 → 澄清/消歧 → 确认 → 执行。
- 当前风险：待办隐式指代与澄清循环仍可能回到重复追问。
- 约束：每轮必须可判定是否收敛。

### 6.4 端到端链路

- 关键点：`current_todo_id` 由前端在发送时注入，不得提前清理；done 后回填 `message_id`。
- 约束：前后端对同一字段命名与时序保持一致。

### 6.5 可测试性缺口

- 缺口 1：模型初始化测试依赖外部密钥，难以单测隔离。
- 缺口 2：todo integration patch 路径随模块迁移未同步。
- 缺口 3：异步测试执行框架（pytest 插件/marker）策略未统一。
- 缺口 4：文档索引校验未作为提交前强制门禁。

---

## 7. 风险评估与缓解

| 风险 | 级别 | 触发条件 | 缓解措施 |
|---|---|---|---|
| 测试持续红灯 | 高 | 多根因叠加（权限/模型/异步） | 先做 P0 清零，按根因拆任务 |
| 协议漂移导致前端异常 | 高 | done/result 字段演进无统一契约 | 锁定 SSE 契约文档并补齐类型层 |
| 大文件改动冲突频繁 | 中高 | 多人并发改同一文件 | 使用 WS 白名单与单所有者策略 |
| 文档与实现继续背离 | 中 | 仅改代码不改索引 | docs_guard 前置并修复 SUMMARY |

---

## 8. 分期实施路线图

### 8.1 第 1 周（P0 清零）

1. 修复 pytest 13 个失败（按根因四类并行处理）。
2. 修复 `ConfirmationCard.tsx` 类型错误（2 处）。
3. 校验 docs_guard 严格模式持续通过（防回退）。
4. 锁定 SSE done/result/interrupt payload 最小契约。

### 8.2 第 2~4 周（P1 收敛）

1. 分层治理：endpoint 直连 repo/workflow 收敛到 service 边界。
2. 大文件拆分：`data_graph.py`、`todo_graph.py`、`backend.ts` 优先拆职责。
3. Pydantic `class Config` 统一迁移到 v2 推荐写法。
4. 前端 lint 警告聚类治理与 hooks 依赖修正。
5. WS-01 按专项附录推进父子图 I/O 适配与结构化 handoff 信封。

---

## 9. 回滚策略

1. 接口层回滚：保留现网兼容路径，不删除旧字段。
2. 工作流回滚：关键分支通过 feature flag 或配置开关切换。
3. 数据回滚：新增表与字段采用迁移脚本可逆设计，保留审计日志。
4. 前端回滚：SSE 解析器变更与 UI 适配分步发布。

---

## 10. 门禁标准（DoD）

### 10.1 质量门禁

- `venv/bin/python -m pytest -q --maxfail=20` 通过（或有批准豁免）
- `cd web && npx tsc --noEmit` 通过
- `cd web && npm run -s lint` 关键告警清理到可接受阈值
- `venv/bin/python scripts/docs_guard.py --strict` 无 error

### 10.2 业务门禁

- 问数：贷款余额 + 分行维度 + 图表切换多轮链路可复现。
- 待办：隐式指代补充轮不重复确认。
- 聊天：SSE 事件顺序与消息持久化一致。
- 合规：双数据库链路不串库；管理接口环境约束生效。

---

## 11. 交付物映射

| 交付物 | 用途 | 责任层 |
|---|---|---|
| `requirements.md` | 需求真理来源 | 产品/架构 |
| `implementation_plan.md` | 实施约束与分期 | 架构/研发 |
| 模块需求文档（5 份） | 模块边界与验收 | 各模块负责人 |
| `/rwfj` 拆解文档 | 并行执行与门禁 | 项目管理/研发 |

---

## 12. 修复任务拆解（可直接排期）

### 12.1 T-P0-*（先清零阻断）

- `T-P0-01`：DataAccessControl 白名单策略与测试契约统一
  - 范围：`app/ai/semantic/data_access_control.py`、相关测试
  - 验证：`pytest app/tests/test_data_agent.py tests/api/test_data_chat.py -q`
  - DoD：白名单/黑名单语义明确且测试通过

- `T-P0-02`：`get_llm` 测试可测性修复（无密钥场景）
  - 范围：`app/ai/llm_util.py`、`app/tests/test_model_switch.py`
  - 验证：`pytest app/tests/test_model_switch.py -q`
  - DoD：模型选择单测不依赖外部密钥

- `T-P0-03`：待办集成测试路径与 async 执行策略修复
  - 范围：`app/tests/test_todo_graph_integration.py`、`app/tests/test_todo_multiround.py`、pytest 配置
  - 验证：`pytest app/tests/test_todo_graph_integration.py app/tests/test_todo_multiround.py -q`
  - DoD：无 patch 路径错误与 async 执行错误

- `T-P0-04`：前端确认卡片类型契约收敛
  - 范围：`web/src/components/todo/ConfirmationCard.tsx`
  - 验证：`cd web && npx tsc --noEmit`
  - DoD：tsc 零错误

- `T-P0-05`：文档索引修复与 strict 门禁恢复（已完成，本轮已落地）
  - 范围：`docs/SUMMARY.md`、缺失文档路径
  - 验证：`venv/bin/python scripts/docs_guard.py --strict`
  - DoD：0 error

### 12.2 T-P1-*（结构收敛）

- `T-P1-01`：Endpoint-Service-Repository 分层收敛
- `T-P1-02`：SSE 协议字段规范化与前端统一消费
- `T-P1-03`：工作流巨型文件拆分（data/todo）
- `T-P1-04`：Pydantic v2 Config 迁移
- `T-P1-05`：多智能体上下文契约重构（WS-01 专项附录）

### 12.3 T-P2-*（中长期优化）

- `T-P2-01`：前端 lint 告警治理
- `T-P2-02`：测试标记与分层治理
- `T-P2-03`：文档自动索引与持续校验增强

---

## 13. 审查输出数据模型（用于追踪）

### 13.1 `Finding`

- `id`
- `severity`（`P0`/`P1`/`P2`）
- `category`
- `location`（`file:line`）
- `evidence`
- `impact`
- `recommendation`
- `effort`（`S`/`M`/`L`）
- `related_tests`

### 13.2 `Task`

- `task_id`
- `priority`
- `scope`
- `depends_on`
- `changes`
- `validation_cmds`
- `dod`

---

## 14. 明确假设

1. 以当前工作区（含未提交改动）为唯一事实来源。
2. 本文档阶段不直接改业务代码，只输出计划与任务拆解。
3. 并行执行以“文件白名单互斥 + 状态单写入权”为硬约束。

---

## 15. 本轮执行补充记录（2026-02-10）

### 15.1 问数图表补充回合闭环落地

已落地“同线程补充图表诉求（如：以柱状图方式展示）”能力，保持 SSE 单通道协议不变：

1. 后端 `sql_execute` 在 `data_type='sql_result'` 中可选附带 `chart` 字段；
2. 前端消息渲染改为“图在上、表在下”；
3. 图表推导失败时自动降级，仅渲染表格，不中断问答链路。

### 15.2 图表渲染引擎选型决策

本轮明确对比了两种方案：

- 方案 A：Vega-Lite（`react-vega`）
- 方案 B：ECharts（`echarts-for-react`）

最终选择 **Vega-Lite**，原因：

1. 面向 LLM 自动生成场景，声明式 Spec 结构更稳定；
2. 更利于做结构化校验与失败降级；
3. 与当前 `sql_result.chart` 语义字段（`type/x_key/y_key/data`）映射成本更低；
4. 可在后续复杂交互场景下再扩展到 ECharts，而不破坏现有 SSE 契约。

### 15.3 本轮交付范围

代码变更：

- 后端：`app/ai/workflow/data_graph.py`
- 前端：`web/src/components/chat/messages/sql-result-chart.tsx`、`web/src/components/chat/messages/ai.tsx`
- 类型：`web/src/types/message.ts`、`web/src/lib/backend.ts`
- 测试：`app/tests/test_data_graph_visualization.py`、`web/e2e/data-agent.spec.cjs`

文档变更：

- `docs/开发文档/架构设计/AI模块设计.md`
- `docs/开发文档/架构设计/前端架构.md`
- `docs/开发文档/测试管理/问数引擎测试案例.md`
- `docs/开发文档/测试管理/测试用例库.md`
