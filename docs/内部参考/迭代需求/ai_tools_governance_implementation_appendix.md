# AI 工具治理实施附录（技术细节）

> 文档状态：主计划附录（中度拆分）  
> 对应主计划：`docs/内部参考/迭代需求/ai_tools_governance_implementation_plan.md`  
> 最近更新：2026-02-18

---

## 1. 全量目标架构（终态）

### 1.1 核心组件

1. `ToolRegistry`：统一注册工具与元数据（分组、owner_only、启用状态）。
2. `ToolPolicyPipeline`：按层叠加策略（Global/Agent/Role/Scene）。
3. `ToolPolicyStore`：从 DB 拉取策略并缓存。
4. `ToolHookRunner`：before/after 调用扩展点（Phase 2）。
5. `ToolEventAdapter`：工具事件标准化（Phase 3）。
6. `ToolAuditSink`：审计持久化与统计（Phase 4）。

### 1.2 工具分组契约（真实名称）

| Group | 工具名 |
|---|---|
| `data` | `semantic_query`、`execute_sql`、`fig_inter` |
| `web` | `tavily_search`（运行时从 `search_tool.name` 解析） |
| `knowledge` | `knowledge_search` |
| `file` | `read_uploaded_file`、`analyze_image` |
| `todo` | `add_todo`、`list_todos`、`update_progress`、`update_todo`、`complete_todo`、`delete_todo` |

### 1.3 策略计算顺序

默认按以下顺序串行过滤：

1. Global Policy
2. Agent Policy
3. Role/User Policy
4. Scene Policy

规则：

1. 同层内 `deny` 优先于 `allow`。
2. 跨层采用“逐层收敛”语义（后层仅在前层结果上继续过滤）。
3. 任一层异常时按 fail_mode 降级，不中断主流程。

---

## 2. 配置与数据设计（`settings.py` + DB）

### 2.1 `settings.py` 静态配置基线

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `TOOL_GOVERNANCE_ENABLED` | `False` | 总开关 |
| `TOOL_POLICY_SOURCE` | `db` | 策略来源（当前固定 DB） |
| `TOOL_POLICY_CACHE_TTL_SECONDS` | `60` | 策略缓存 TTL |
| `TOOL_POLICY_FAIL_MODE` | `allow` | 降级策略（allow/deny/minimal） |
| `TOOL_HOOKS_ENABLED` | `False` | Hook 开关（Phase 2） |
| `TOOL_EVENTS_V2_ENABLED` | `False` | 事件升级开关（Phase 3） |

说明：一期需要先在 `app/core/settings.py` 提供统一读取入口，避免新治理模块继续散落读取环境变量。

### 2.2 DB 动态策略（`chat_db.t_system_config`）

| key | value_type | 默认值 | 说明 |
|---|---|---|---|
| `tool_governance.enabled` | boolean | `false` | 运行期总开关 |
| `tool_governance.policy.global` | json | `{}` | 全局策略 |
| `tool_governance.policy.agent.supervisor` | json | `{}` | Supervisor 策略 |
| `tool_governance.policy.agent.data_expert` | json | `{}` | Data Expert 策略 |
| `tool_governance.policy.agent.todo_expert` | json | `{}` | Todo Expert 策略 |
| `tool_governance.policy.role.owner` | json | `{}` | 管理角色策略 |
| `tool_governance.policy.role.user` | json | `{}` | 普通角色策略 |
| `tool_governance.policy.scene.data_analysis` | json | `{}` | 问数场景策略 |
| `tool_governance.policy.scene.todo_management` | json | `{}` | 待办场景策略 |
| `tool_governance.policy.version` | number | `1` | 策略版本号（用于缓存刷新） |

要求：这些键需补充到 `app/core/config_contract.py`，通过 `ConfigResolver` 读取。

### 2.3 配置优先级

1. 运行时优先：DB 动态值（`t_system_config`）。
2. DB 缺失或非法：回退 `settings.py` 默认值。
3. 读取失败：按 `TOOL_POLICY_FAIL_MODE` 走降级路径，并记录结构化日志。

### 2.4 双数据库约束

1. 工具治理动态配置只允许来自 `chat_db`。
2. `ANALYTICS_DATABASE_URL`（`data_db`）仅用于问数业务数据查询，不承载治理配置。

---

## 3. 代码改造清单（按阶段）

### 3.1 Phase 1（必做）

1. 新增：`app/ai/tools/registry.py`
2. 新增：`app/ai/tools/policy.py`
3. 新增：`app/ai/tools/policy_store.py`（或同职责模块）
4. 修改：`app/ai/workflow/multi_agent_graph.py`（接入治理获取工具）
5. 修改：`app/core/settings.py`（治理配置入口）
6. 修改：`app/core/config_contract.py`（治理配置键契约）
7. 新增测试：`tests/unit/test_tool_registry.py`
8. 新增测试：`tests/unit/test_tool_policy.py`
9. 新增测试：`tests/integration/test_tool_policy_in_graph.py`

### 3.2 Phase 2~4（后续）

1. 新增：`app/ai/tools/hooks.py`
2. 修改：`app/ai/events.py`（事件增强）
3. 新增：`app/services/tool_audit_service.py`（审计持久化）
4. 新增：并发隔离/取消传播相关模块（命名待 Phase 4 定稿）

---

## 4. API 与协议影响

### 4.1 对外 API 影响

1. 一期不新增对外业务 API。
2. 一期不改变 `chat/stream` 入参语义。

### 4.2 SSE/跨端契约冻结

本轮冻结字段清单：

1. `done`：语义不变。
2. `result`：语义不变。
3. `interrupt`：语义不变。

补充：

1. `tool_call_id` 仅在 Phase 3 以**可选字段**引入。
2. 前端消费方按“未知字段忽略”原则兼容。

---

## 5. 跨模块依赖矩阵

| 能力 | 主责任模块 | 协作模块 | 关键依赖 |
|---|---|---|---|
| Registry | `app/ai/tools/registry.py` | `app/ai/tools/*` | 工具函数命名稳定 |
| Policy Pipeline | `app/ai/tools/policy.py` | `app/services/permission_service.py` | 用户角色上下文可获取 |
| DB 策略源 | `app/ai/tools/policy_store.py` | `app/services/config_resolver.py` | `config_contract` 键契约完整 |
| 配置入口 | `app/core/settings.py` | `app/core/config.py` | 新旧配置并存迁移策略 |
| Workflow 接入 | `app/ai/workflow/multi_agent_graph.py` | `app/ai/workflow/*` | 不破坏现有 handoff 路由 |
| 事件升级 | `app/ai/events.py` | `app/services/chat_service.py`、前端消费方 | SSE 契约兼容 |
| 审计与观测 | `app/services/*` | 日志/监控体系 | trace 字段统一 |

---

## 6. 观测方案

核心指标：

1. `tool_registry_total`：注册工具总数。
2. `tool_policy_eval_ms`：策略评估耗时。
3. `tool_policy_filtered_count`：每次过滤移除数量。
4. `tool_policy_fallback_count`：降级次数。
5. `tool_policy_db_refresh_fail_count`：DB 刷新失败次数。
6. `tool_hook_block_count`（Phase 2）。
7. `tool_event_unmatched_count`（Phase 3）。

日志最小字段：`thread_id`、`user_id`、`agent_name`、`scene_key`、`policy_version`、`fallback_reason`。

---

## 7. 并行拆解索引（`/jjk-vkplan`）

1. `task_key`：`PP-20260216-TOOL-GOVERNANCE`。
2. 拆解目录：`docs/内部参考/任务拆解/2026-02-16_AI工具治理架构并行拆解/`。
3. 契约文件：`contracts/sse_events_v1.json`（冻结 `done/result/interrupt` required 语义）。
4. 卡片导出：`vk_cards.json`（共 5 张落卡卡片，不含 `WS-00` Foundation）。
5. 导入提示：`vk_import_prompt.txt`（供 `/jjk-vktodo` 直接落卡）。
