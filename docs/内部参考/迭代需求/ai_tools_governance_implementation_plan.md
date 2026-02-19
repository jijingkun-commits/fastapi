# 2026-02 实施方案：AI 工具治理架构（主计划）

> 文档状态：`/plan core` 主计划（中度拆分）  
> 生成日期：2026-02-16  
> 最近更新：2026-02-18  
> 对应需求：`docs/内部参考/迭代需求/ai_tools_governance_requirements.md`

---

## 1. 实施目标与原则

1. 建立工具治理主链路，解决工具散落、策略分散、扩展困难的问题。
2. 保持现有多智能体主流程稳定，采用“增量替换”而非重写。
3. 一期严格聚焦 `Registry + Policy`，Hook/事件升级按阶段推进。
4. 治理配置采用“双层来源”：`settings.py` 静态基线 + DB 动态策略覆盖。
5. 所有改造均需可回滚、可观测、可测试。

---

## 2. 架构影响与约束（必查）

### 2.1 模块边界

1. 工具治理逻辑归属 `app/ai/tools/`，不得继续散落到 Workflow 节点函数中。
2. `app/ai/workflow/multi_agent_graph.py` 仅负责“按上下文请求工具集合”，不承担策略实现细节。
3. 权限与身份来源由现有用户上下文提供，治理层只消费标准化字段，不反向依赖前端。
4. 禁止引入不存在的历史函数（如 `_get_supervisor_tools_legacy`）作为前置假设。

### 2.2 状态契约

治理输入上下文字段冻结为：`user_id`、`thread_id`、`agent_name`、`scene_key`、`role_codes`、`task_mode`、`requires_evidence`。  
治理输出契约冻结为：`allowed_tools`、`decision_trace`、`fallback_reason`。
补充约束：`requires_evidence` 仅在执行型任务生效，闲聊任务不强制工具证据门禁。

### 2.3 路由闭环

统一闭环为：

`Workflow 上下文 -> Registry 候选工具 -> Policy Pipeline 过滤 -> Agent 可用工具集 -> 现有执行链路返回`

约束：不允许“策略过滤失败后再次进入策略过滤”的循环重试。

### 2.4 端到端链路

1. 前端上下文（用户、线程、场景）在请求进入图编排前完成注入。
2. 治理层仅做工具集合裁剪，不修改主业务消息内容。
3. DB 策略刷新与请求处理解耦，避免阻塞主链路。

### 2.5 状态与存储约束（修订）

1. Workflow state 仅保留摘要与引用（如 `ledger_ref`、计数、状态位）。
2. 大对象（tool ledger/evidence ledger 明细）落库或外部存储。
3. checkpoint 热路径禁止写入大体积事件明细，避免恢复与性能回退。

---

## 3. 分阶段路线图（全量方案，分期交付）

### Phase 0：基线冻结（D1-D2）

交付：

1. 冻结工具命名与分组清单（与仓库现状对齐）。
2. 在 `settings.py` 明确治理配置字段。
3. 在 `config_contract` 定义治理配置键契约。

门禁（G0）：

1. 文档评审通过。
2. 工具名/函数名与代码现状一致。

### Phase 1：Registry + Policy（P0，D3-D7）

交付：

1. Registry、Policy、PolicyStore 可运行。
2. `multi_agent_graph.py` 工具获取逻辑接入治理层。
3. DB 策略读取与缓存生效（`t_system_config`）。
4. 具备开关回退能力（默认灰度开启）。

门禁（G1）：

1. P1 相关 TC 全部通过。
2. 主链路无功能回归。
3. 热路径性能回归可接受（误差 ±5%）。

### Phase 2：Hook 扩展（P1）

交付：

1. before/after hook 运行框架。
2. 默认审计 Hook（耗时、摘要、异常）。
3. 可配置阻断 Hook（仅灰度启用）。

门禁（G2）：

1. hook 异常不影响主流程。
2. 审计字段可追溯。

### Phase 3：事件升级（P1）

交付：

1. 工具事件增加 `tool_call_id`（可选字段）。
2. 为后续 `start/update/result` 三阶段预留字段。
3. 事件演进采用“少量新事件 + metadata 扩展 + version 字段”策略。

门禁（G3）：

1. 前端兼容旧事件消费。
2. 并发工具调用可稳定关联。
3. 枚举新增不影响旧版解析器默认分支。

### Phase 4：治理增强（P2）

交付：

1. 审计持久化。
2. 会话级工具并发隔离与取消传播。
3. 完整运行看板与告警阈值。

门禁（G4）：

1. 压测与故障演练通过。
2. 回滚演练完成并留档。

### Phase 4.5：插件扩展基线（后置，非阻塞）

交付：

1. `Plugin Registry` 最小骨架（元数据、注册、禁用、生命周期状态）。
2. 与策略层对齐：`group:plugins`、插件 allowlist 防误杀规则。
3. 插件失败降级路径：自动回退核心工具集，不中断主流程。

门禁（G4.5）：

1. 插件加载失败不影响核心链路。
2. 插件相关事件可观测（loaded/blocked/failed）。

---

## 4. 回滚总则

1. 通过 `tool_governance.enabled=false` 或 `TOOL_GOVERNANCE_ENABLED=false` 关闭治理链路。
2. DB 策略异常时可直接回退到空策略（兼容模式）并保留告警日志。
3. Hook/事件升级阶段均需独立开关，可单独回退。
4. 回滚后保留策略命中与降级日志，支撑复盘。

---

## 5. 验证与门禁

1. 单元：Registry、Policy、ConfigResolver 读策略逻辑。
2. 集成：`multi_agent_graph` 工具集合按策略变化。
3. 回归：问数与待办主流程无回归。
4. 文档门禁：`python3 scripts/docs_guard.py --strict`。
5. 发布策略：先灰度，再全量；每阶段必须具备可演练回滚。

---

## 6. 风险评估与应对

| 风险 | 等级 | 触发条件 | 应对策略 |
|---|---|---|---|
| 策略误配导致工具误杀 | 中高 | deny 配置过严 | 提供最小可用回退策略 + 告警 |
| DB 配置不可用 | 中 | `t_system_config` 读取异常 | 缓存兜底 + settings 默认值 |
| 接入点改动引发图行为变化 | 中 | `_get_supervisor_tools` 逻辑变化 | 增量替换 + 对照测试 |
| 性能回归 | 中 | 每请求重复取策略 | 策略缓存 + 版本增量刷新 |
| 前后端事件不兼容（后续） | 中 | Phase 3 新字段消费不一致 | 可选字段 + 契约测试 |

---

## 7. 与总控迁移方案映射

对应总控文档：`docs/内部参考/迭代需求/openclaw全量迁移_implementation_plan.md`

1. 批次映射：本专题对应 **Batch-2（工具治理一期）** 与 **Batch-5（治理增强与容错扩展）**。
2. 进入条件：Batch-0 文档治理拆分完成，Batch-1 去特殊化稳定。
3. 本批产出：
   - Batch-2：Registry + Policy + PolicyStore + Workflow 接线；
   - Batch-5：Hook/事件升级、审计增强与治理能力扩展。
4. 退出条件：
   - 阶段门禁 G1~G4 逐项通过；
   - 回滚演练留档；
   - 需求与实施、测试与观测保持可追溯。
5. 回滚锚点：治理开关、策略源回退、事件可选字段兼容。
6. Wave 对齐：执行波次归属 **P2（工具治理一期）**，详见 `迁移执行波次_implementation_plan.md`。

---

## 8. 文档分层与引用关系

1. 主计划（本文件）：记录目标、阶段路线、风险、门禁、回滚总则。
2. 技术附录：`docs/内部参考/迭代需求/ai_tools_governance_implementation_appendix.md`（配置键、代码清单、依赖矩阵、观测细项、并行拆解索引）。
3. 需求基线：`docs/内部参考/迭代需求/ai_tools_governance_requirements.md`。
