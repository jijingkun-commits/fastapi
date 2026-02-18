# 2026-02 迭代需求：AI 工具治理架构（全量方案，分期落地）

> 文档状态：`/plan core` 基线  
> 生成日期：2026-02-16  
> 关联输入：`output/工具治理架构-评审与方案V0.1.md`、`output/OpenClaw对标与智能度提升综合分析报告.md`、`output/openclaw源码解析/OpenClaw深度解析-工具策略管线与权限边界.md`  
> 关键决策：分期实施但方案全量、配置基线走 `settings.py`、策略来源走 DB、一期先做 `Registry + Policy`

---

## 1. 背景与目标

当前工具编排链路已具备可用能力，但随着工具数量增长（问数、待办、知识库、联网、多模态）出现以下结构性问题：

1. 工具装配逻辑主要集中在 `app/ai/workflow/multi_agent_graph.py` 的函数级拼装，新增工具需要改核心编排文件。
2. 工具可见性缺少统一策略层，难以按 Agent/角色/场景做差异化治理。
3. 缺少统一治理入口，横切能力（权限、审计、灰度）难以稳定接入。
4. 策略读取尚未形成“静态配置 + 动态策略”的统一契约。

本轮目标：

1. 形成**全量工具治理目标架构**（Registry、Policy、Hook、事件、审计、并发隔离）。
2. 以分期方式落地，**一期聚焦 `Registry + Policy`**，不破坏现有业务语义。
3. 明确配置治理基线：静态默认走 `app/core/settings.py`，动态策略走 DB（`chat_db`）。
4. 建立可追溯测试与门禁，确保后续 Hook/事件升级可无缝扩展。

---

## 2. 范围与边界

### 2.1 全量目标范围（架构终态）

1. 统一工具注册中心（Registry）与元数据模型。
2. 分层策略管线（Global/Agent/Role/Scene）与 allow/deny 规则。
3. DB 驱动策略源与配置契约（`t_system_config` + `ConfigResolver`）。
4. 工具调用钩子体系（before/after）与审计输出。
5. 工具事件生命周期升级（含 `tool_call_id`）。
6. 会话级并发隔离、取消传播、可观测与回滚机制。

### 2.2 本轮（Phase 1）纳入范围

1. 建立 Registry，并完成现有工具清单的统一注册与分组。
2. 建立 Policy Pipeline，并支持 DB 下发策略。
3. 建立 `settings.py` 侧治理配置入口（静态兜底 + 开关）。
4. 在不重写图编排的前提下，接入 `multi_agent_graph.py` 的工具获取路径。
5. 提供一期单元/集成测试基线（策略生效、回退、兼容）。

### 2.3 本轮不纳入范围（后续 Phase）

1. before/after Hook 的全量接入（Phase 2）。
2. 工具事件协议升级为 `start/update/result`（Phase 3）。
3. 会话锁、取消传播、审计持久化（Phase 4）。

---

## 3. 用户故事（银行场景）

| US-ID | 角色 | 场景 | 目标 |
|---|---|---|---|
| US-TG-01 | 客户经理 | 发起“按分行统计贷款余额并绘图” | 只暴露数据分析相关工具，避免误用待办/管理工具 |
| US-TG-02 | 支行运营 | 在待办对话中补充外部信息 | 仅使用待办相关能力，避免跨域工具污染任务链路 |
| US-TG-03 | 风控/合规 | 复盘敏感操作与调用路径 | 工具可见性与执行决策可审计、可追溯 |
| US-TG-04 | 系统管理员 | 临时收紧某类工具权限 | 无需发版，通过 DB 配置动态生效并可快速回滚 |
| US-TG-05 | 研发工程师 | 新增一个工具能力 | 不改核心图主文件，完成声明式注册并复用统一策略 |

---

## 4. 功能需求

### 4.1 工具注册中心（FR-REG）

1. 提供统一 Registry，支持工具注册、查询、分组和元数据管理。
2. 注册信息至少包含：`name`、`group`、`owner_only`、`enabled_by_default`。
3. 工具分组需覆盖现有真实工具名：
   - `data`：`semantic_query`、`execute_sql`、`fig_inter`
   - `web`：`tavily_search`（运行时取 `search_tool.name`）
   - `knowledge`：`knowledge_search`
   - `file`：`read_uploaded_file`、`analyze_image`
   - `todo`：`add_todo`、`list_todos`、`update_progress`、`update_todo`、`complete_todo`、`delete_todo`

### 4.2 策略管线（FR-POL）

1. 支持多层策略叠加：Global → Agent → Role/User → Scene。
2. 支持 `allow/deny`，并满足 `deny` 优先。
3. 支持 `glob` 与 `group:<name>` 规则表达。
4. 空策略默认“不过滤”（保持兼容），可通过 fail_mode 改为更严格策略。

### 4.3 DB 动态策略源（FR-DB）

1. 一期策略配置读取来源为 `chat_db` 的 `t_system_config`。
2. 策略读取统一走 `ConfigResolver` + `config_contract`，禁止在业务层直接 SQL 拼配置。
3. 需支持策略缓存与刷新，避免每次请求都查询 DB。

### 4.4 配置入口（FR-SET）

1. 治理开关和静态默认值必须在 `app/core/settings.py` 定义。
2. 业务模块读取顺序统一为：`settings.py` 静态默认 → DB 动态覆盖（按契约）。
3. 禁止在治理新模块中新增散落 `os.getenv` 读取。

### 4.5 编排接入（FR-INT）

1. 一期仅改造工具“获取/过滤”路径，不重写 Supervisor/Expert 主流程。
2. `multi_agent_graph.py` 中 `_get_common_tools()`、`_get_supervisor_tools()` 接入治理层。
3. 特性开关关闭时，行为需与改造前保持一致。

### 4.6 Hook 体系（FR-HOOK，后续）

1. 预留 before/after 扩展点，支持阻断、改参、审计。
2. Hook 异常默认不影响主流程（可配置严格模式）。

### 4.7 事件与协议（FR-EVENT，后续）

1. 在保持现有 `tool_start/tool_end` 兼容前提下，增加 `tool_call_id` 能力。
2. 后续可平滑扩展为 `start/update/result` 三阶段协议。

---

## 5. 验收标准

### 5.1 Happy Path

1. 新增工具仅需注册与分组配置，不要求改核心编排逻辑。
2. 同一请求在不同 Agent/角色/场景下返回可预测的工具集合。
3. DB 策略变更后可通过缓存刷新在预期窗口内生效。
4. 一期接入后，现有问答主流程、待办主流程无功能回归。

### 5.2 异常与边界

1. DB 配置不可用时，系统按 `settings.py` 默认策略降级并记录告警。
2. 策略 JSON 非法或引用未知组时，不得导致请求失败。
3. 可选依赖未安装（如联网搜索）时，Registry 初始化不得中断。
4. 策略结果为空时，需有可观测告警并保持主流程可继续（至少保留 handoff 路径）。

### 5.3 性能与稳定性

1. 单次策略过滤开销 p95 ≤ 20ms（热路径，本地缓存命中条件下）。
2. 工具清单构建过程不引入每请求 DB 查询（DB 读取走缓存/定时刷新）。
3. 一期接入后 `POST /api/v1/chat/stream` 首 token 时延回归误差控制在 ±5% 内。

---

## 6. 非功能需求

1. **可回滚**：治理能力必须有独立开关，支持快速回退旧路径。
2. **可观测**：输出策略命中、过滤数量、降级原因、耗时指标。
3. **一致性**：不破坏现有对外响应语义与主事件契约。
4. **双库约束**：动态策略仅来自 `chat_db`，严禁从 `data_db` 写入或读取治理配置。
5. **安全合规**：策略与审计日志不泄露敏感字段值。

---

## 7. 关联测试（预留 TC 编号）

| TC-ID | 类型 | 验证目标 | Phase |
|---|---|---|---|
| TC-TG-REG-01 | 单元 | Registry 注册/查询/分组正确 | P1 |
| TC-TG-REG-02 | 单元 | 可选工具缺失时初始化不失败 | P1 |
| TC-TG-POL-01 | 单元 | allow/deny 规则与 deny 优先正确 | P1 |
| TC-TG-POL-02 | 单元 | glob 与 `group:` 扩展正确 | P1 |
| TC-TG-POL-03 | 单元 | 空策略兼容行为正确 | P1 |
| TC-TG-DB-01 | 集成 | 从 `t_system_config` 读取策略并生效 | P1 |
| TC-TG-DB-02 | 集成 | DB 不可用时按 settings 降级 | P1 |
| TC-TG-INT-01 | 集成 | `_get_supervisor_tools` 接入后行为可控 | P1 |
| TC-TG-INT-02 | 回归 | 待办与问数主链路无回归 | P1 |
| TC-TG-HOOK-01 | 单元 | before_hook 阻断/改参正确 | P2 |
| TC-TG-HOOK-02 | 单元 | hook 异常不影响主链路 | P2 |
| TC-TG-EVT-01 | 契约 | `tool_call_id` 向后兼容 | P3 |
| TC-TG-EVT-02 | 联调 | 前端可稳定关联并发工具事件 | P3 |
| TC-TG-CONC-01 | 集成 | 会话级工具调用互斥与取消收敛 | P4 |

---

## 8. 依赖与约束

1. 依赖 `app/core/settings.py` 成为治理配置的静态入口。
2. 依赖 `app/core/config_contract.py` + `app/services/config_resolver.py` 承接 DB 动态配置。
3. 依赖 `app/models/system_config.py` / `t_system_config` 提供策略存储。
4. 依赖 `app/ai/workflow/multi_agent_graph.py` 的局部接入点（工具获取函数）。
5. 不允许引入 `_get_supervisor_tools_legacy` 等不存在的历史接口。

---

## 9. 完成定义（DoD）

1. 需求项与测试用例形成可追溯关系（至少覆盖 P1 全部 TC）。
2. `ai_tools_governance_requirements.md` 与 `ai_tools_governance_implementation_plan.md` 对齐，不存在架构冲突。
3. 分期计划、回滚机制、观测指标完整且可执行。
4. 方案文本中的模块名、函数名、工具名与仓库现状一致。
