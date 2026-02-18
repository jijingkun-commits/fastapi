# OpenClaw 源码解析与本项目重构长期主档（四文档整编版）

> 文档类型：长期持续更新（Living Document）  
> 创建日期：2026-02-18  
> 最近更新：2026-02-18（v11：补齐 B0-2/B0-3/B1-B2 验证手册并完成补强闭环）  
> 适用项目：`/Users/jijingkun/bojxAI/fastapi`  
> 主问题：**OpenClaw 为什么“看起来会自己知道该做什么”？**

---

## 0. 使用说明

### 0.1 这份文档解决什么问题

本主档不是“再写一份摘要”，而是将四份核心调研文档的结论和方案，统一到一个可持续更新的架构主线里，目标是：

1. 让“原理—现状—方案—验收”能一条线读完。  
2. 让后续新会话能直接复用，不丢上下文。  
3. 让每一条改造建议都有来源、有优先级、有 done criteria。

### 0.2 阅读顺序建议

- 先读 **第 2 章（总答案）**：明确你关心的核心问题。  
- 再读 **第 7 章（统一重构蓝图）**：直接指导工程实施。  
- 需要追溯细节时，回看 **第 3~6 章（四份文档逐章整编）**。

### 0.3 更新规则（长期维护）

- 每次新增结论，先更新本主档，再回写专题文档。  
- 任何“建议”必须具备：影响模块、风险、回滚条件、验收标准。  
- 若结论发生变化，必须记录“变更原因”与“影响范围”。

---

## 1. 四份来源文档与覆盖矩阵

### 1.1 本次整编纳入的四份核心文档

| 编号 | 来源文档 | 文档角色 |
|---|---|---|
| D1 | `output/OpenClaw对标与智能度提升综合分析报告.md` | 全景总览 + 优先级 + 8 周计划 |
| D2 | `output/OpenClaw深挖分析-四大核心问题.md` | 源码机制深挖（动态加载/Subagent/队列/策略管线） |
| D3 | `output/深度分析-复合任务与Collect模式.md` | 多轮与复合任务专项落地方案 |
| D4 | `output/执行协议设计与诊断工具方案.md` | 执行协议、done criteria、证据链专项 |

### 1.2 覆盖结果（本主档章节映射）

| 来源章节 | 已吸收位置 | 覆盖状态 |
|---|---|---|
| D1 一~十一章（评分、差距、路线、Quick Wins） | 第 3 章 + 第 8~10 章 | 全量吸收（去重整合） |
| D2 Q1~Q4 + 实施路线图 | 第 4 章 + 第 7~8 章 | 全量吸收（细节保留） |
| D3 问题定义~实施路线图~风险 | 第 5 章 + 第 8~9 章 | 全量吸收（实施优先级已对齐） |
| D4 四问方案 + 模板 + 两周 MVP | 第 6 章 + 第 7~8 章 | 全量吸收（模板保留） |

### 1.3 整编后的统一口径

- **核心驱动力**：规则与协议，不是 skill 文案数量。  
- **核心缺口**：协议闭环、证据链、收敛判定、队列节奏。  
- **优先顺序**：先“会做且可证”，再“更灵活自治”。

---

## 2. 主问题总答案（先回答你最关心的）

### 2.1 一句话

OpenClaw 的“像自己知道该做什么”，本质是把 Agent 变成了“受规则约束的执行系统”：

**多层规则 + 固定执行协议 + 工具策略管线 + 队列节奏 + 证据化收敛**。

### 2.2 五个决定性机制

1. **规则分层**：不同层负责不同问题，不把所有约束塞进一个 prompt。  
2. **协议循环**：任务按固定步骤推进（而不是“想到哪说到哪”）。  
3. **工具可见性治理**：不是全工具裸露给模型，而是按策略过滤。  
4. **消息队列节奏**：用户追问进入队列、合并、排队、中断，行为可预测。  
5. **收敛可验证**：结束不是“模型说结束”，而是“满足 done criteria + evidence”。

### 2.3 对你当前项目的直接含义

- 你现有 Supervisor + 专家路由骨架没问题。  
- 真正短板在“执行协议”和“完成门禁”。  
- 所以路线应是：**先协议后 skill，先收敛后扩展，先可证后自治**。

---

## 3. D1 整编：综合分析报告（全景版）

> 对应来源：`output/OpenClaw对标与智能度提升综合分析报告.md`

### 3.1 对标总览（评分与差距）

D1 给出 7 维评分（5 分制），关键结论：

- 你方优势：意图路由、安全护栏。  
- 你方短板：技能/插件治理、工具策略治理、子 Agent 编排、可观测性。  
- 记忆层已从 1.5/2.5 提升（MVP 已落地），但仍缺 OpenClaw 的“自动沉淀 + 混合检索 + 预压缩 flush”机制。

### 3.2 记忆层章节的关键信息（2.1~2.6）

#### 3.2.1 已落地能力（你方）

- 偏好提取 + DB 持久化 + 上下文注入。  
- 冲突去重 + 摘要压缩。  
- 避免“全量注入”导致污染与成本上升。

#### 3.2.2 还可借鉴能力（OpenClaw）

- 会话切换自动沉淀。  
- 上下文压缩前先 flush 关键信息（防“晚期健忘症”）。  
- 混合检索（语义 + 关键词 + 去重 + 时间衰减）。

#### 3.2.3 五项评估（D1 的高价值部分）

1. 偏好提取应做置信度分级，必要时确认式写入。  
2. 偏好模型需版本化，支持追溯与冲突处理。  
3. 注入策略应分硬/软偏好，约束力不同。  
4. 应引入 pre-compaction flush。  
5. 必须提供用户可见记忆管理接口（合规 + 可控）。

#### 3.2.4 源码复核补充（基于 OpenClaw `02025da35`）

- **预压缩 flush 触发细节**：`totalTokens >= contextWindow - reserveTokensFloor - softThresholdTokens`，并通过 `memoryFlushCompactionCount` 保证同一 compaction 周期只跑一次。  
- **`/new` 沉淀细节**：仅 `command:new` 触发；优先读 `previousSessionEntry`；会话文件缺失时含 `.reset.*` fallback；测试环境禁用 LLM slug 并回退 `HHMM`。  
- **builtin 检索细节**：FTS-only 先关键词提取再多词检索合并去重，不是单次 FTS。  
- **排序细节**：MMR 相似度是 token 集 Jaccard，不是 embedding 余弦；temporal decay 对 `MEMORY.md` 等 evergreen 文件不衰减。  
- **QMD 降级细节**：QMD 失败后 `FallbackMemoryManager` 切 builtin 且驱逐缓存；`search/vsearch` flags 不兼容时回退 `query`。

#### 3.2.5 与你当前实现的差异（代码快照）

- 你方当前记忆核心是**用户偏好 KV 入库**（`app/services/user_preference_memory_service.py` + `app/models/user_memory.py`），并非文件记忆 + 检索索引。  
- 你方注入点在请求入口组装 `SystemMessage`（`app/services/chat_service.py`），尚未形成 `memory_search/memory_get` 工具链。  
- 你方暂无 OpenClaw 的 pre-compaction flush / `/new` 自动沉淀 / watch+delta 增量索引闭环。  
- 你方当前更像“偏好记忆层”，OpenClaw 这一块是“记忆文件系统 + 检索系统 + 压缩保真联动”。

### 3.3 工具编排与策略（D1 第三章）

D1 将工具层拆成两个主问题：

1. 动态加载：建议先 API 触发重载，再做插件目录扫描。  
2. 用户级隔离：建议 role profile → user override → skill visibility 三阶段。

关键安全点：`stripPluginOnlyAllowlist` 思路值得照搬（防策略误杀核心工具）。

### 3.4 多意图与子 Agent（D1 第四章）

- OpenClaw 采用 subagent 工具体系，而非只靠 Supervisor 静态拆分。  
- 对你方建议：先做 Level 1（Supervisor 多意图拆分 + Send），后续再做 Session 隔离、steer/kill。

### 3.5 追问与消息队列（D1 第五章）

- 队列模式建议由易到难推进：`queue` → `collect` → `interrupt`。  
- 你方当前痛点：AI 回复中用户继续输入时行为不稳定。

### 3.6 技能/插件治理（D1 第六章）

- 技能层重点不是“多”，而是“优先级、版本、可见性、热刷新”。  
- 与工具治理关系：技能描述与工具能力必须通过策略层绑定，而非各自漂移。

### 3.7 D1 的实施路线与快速收益

- 给出了 8 周双周迭代和优先级矩阵。  
- Quick Wins：扩展偏好提取、意图分类 fallback、事件补充 `tool_call_id`。

---

## 4. D2 整编：四大核心问题深挖（源码机制细节）

> 对应来源：`output/OpenClaw深挖分析-四大核心问题.md`

### 4.1 Q1 动态加载：OpenClaw 是“半动态”

#### 4.1.1 机制细节

- 内置工具：代码注册 + 策略动态过滤。  
- 插件工具：`jiti` 动态导入 `plugins` 目录。  
- 加载链路包含 Schema 验证、权限检查、名称冲突防护、allowlist 过滤。

#### 4.1.2 对你方的启示

- 不要一上来就做完全插件系统。  
- 正确顺序：先有 registry + reload，再引入目录插件。

### 4.2 Q2 多意图与并行：Subagent 不是“并发”，是“可管理生命周期”

D2 的重点不在“能 spawn”，而在“spawn 后可控”：

- 运行记录（SubagentRunRecord）完整。  
- steer 可重定向进行中的子任务。  
- kill 支持级联终止，防孤儿任务。  
- 有深度限制与可见性规则，避免失控编排。

对你方建议分级：

- Level 1：Supervisor 先支持多意图拆分。  
- Level 2：引入任务隔离上下文。  
- Level 3：再做 steer/kill。

### 4.3 Q3 追问队列：重点是“队列状态机”

关键结构（可复用到你方）：

- 队列状态：items/draining/mode/debounce/cap/dropPolicy。  
- 去重模式：message-id / prompt / none。  
- 丢弃策略：old / new / summarize。

重点价值：把“插话行为”从不确定变成可配置。

### 4.4 Q4 用户级隔离：7 层策略管线是核心资产

D2 对策略管线的价值提炼：

- policy 不是单层 if-else，而是可组合流水线。  
- group policy 与 profile policy 组合，能显著降低配置复杂度。  
- 安全防护要防“配置失误”，不只防“恶意攻击”。

### 4.5 D2 路线图与风险

- 优先级：先工具过滤，再动态重载，再多意图，再队列。  
- 风险缓解：队列先做严格串行；拆分先加置信度阈值。

---

## 5. D3 整编：复合任务与 Collect 模式（多轮专项）

> 对应来源：`output/深度分析-复合任务与Collect模式.md`

### 5.1 问题定义（D3 第一章）

D3 明确了两个高频真实问题：

1. 单条用户请求含多个意图，如何拆分与执行。  
2. AI 正在回答时用户继续输入，如何处理后续消息。

### 5.2 当前架构问题（D3 第二章）

- 你方图结构是单次 handoff 主导，天然偏串行。  
- `evaluate` 节点可能导致“过早终止”。  
- SSE 入口缺明确 queue/collect 策略时，追问体验不稳定。

### 5.3 OpenClaw 在该问题上的做法（D3 第三章）

- 多意图不一定要 Supervisor 预拆分；可交给 Agent 编排/子任务机制。  
- Collect 模式通过消息队列 + 防抖合并输入，提升连续输入体验。

### 5.4 D3 给你的落地方案（第四章）

#### 5.4.1 Phase 1：Collect 模式

- 引入 `MessageCollector`（按 thread 维度维护）。  
- 支持防抖窗口内合并输入。  
- 先简化去重和丢弃策略（避免过度设计）。

#### 5.4.2 Phase 2：复合任务串行执行

- 将 `pending_handoff` 从单值升级为队列。  
- Supervisor 一次性规划多个意图并排序。  
- Expert 逐个消费，Evaluate 在每步校验。

#### 5.4.3 Phase 3：远期并行

- 基于 LangGraph `Send()` 逐步引入并行。  
- 明确属于远期，不应提前压进近期目标。

### 5.5 D3 风险与决策价值

D3 最重要的不是代码样例，而是以下决策：

- 先做 Collect，再做复杂并行。  
- 先把串行复合任务跑稳，再上 Subagent。  
- 进程内队列可作为 MVP，后续再考虑持久化队列。

---

## 6. D4 整编：执行协议与诊断工具（执行闭环专项）

> 对应来源：`output/执行协议设计与诊断工具方案.md`

### 6.1 D4 的核心贡献

D4 把“为什么会假执行”变成了可工程化处理的问题，给出四问解法：

1. 最小规则集长什么样。  
2. 协议放哪一层最稳。  
3. 诊断工具 schema 怎么设计。  
4. 如何建立证据链防“做没做不透明”。

### 6.2 Q1 最小规则集（6 条）

D4 的最小规则集是本主档建议直接采纳的基础协议：

1. 命中调研意图即 `investigate`。  
2. 先做后说（至少一个工具调用后再总结）。  
3. checklist 驱动推进。  
4. done criteria 收敛。  
5. 权限边界（读直执，写审批）。  
6. 结构化报告（status/findings/evidence/next_steps/blockers）。

### 6.3 Q2 协议层级：A + C 组合

- A：Supervisor 下发执行模式、checklist、done criteria。  
- C：Evaluate 负责收敛门禁（continue/end/force_converge）。  
- B（独立 Planner）短期不建议优先。

### 6.4 Q3 Schema 设计：稳定“先做后说”

D4 的关键是“两层 schema”：

- 模型可见输入：尽量 0/1 参数，降低调用摩擦。  
- 运行时信封：`task_id/check_item_id/trace_id/attempt` 由系统注入。

工具输出统一信封，强制产出 `evidence_id`，并提供 `next_recommended_tools`。

### 6.5 Q4 证据链与状态

D4 明确了三段式证据链：

1. 工具执行账本（真实调用记录）。  
2. checklist 状态机（pending/running/done/skipped/failed）。  
3. 最终报告校验（finding 必须有 evidence_ref）。

以及 Evaluate 门禁逻辑：

- `investigate` 模式下，未覆盖 required item 不可 done。  
- 连续无新增证据可强制 partial 收敛。  
- 发现“声称已完成但无证据”要纠偏继续执行。

### 6.6 D4 的两周 MVP 价值

- Week1：规则与收敛闭环。  
- Week2：诊断工具与证据可视化。  

这是当前最小高收益路径。

---

## 7. 四文档归一后的统一架构蓝图

### 7.1 目标状态（统一定义）

让系统从“会说”升级到“会做、可证、可控”，并具备稳定多轮能力。

### 7.2 分层架构（统一）

| 层级 | 职责 | 关键机制 |
|---|---|---|
| L0 行为层 | 角色/边界/模式判定 | Supervisor Prompt + execution_mode |
| L1 策略层 | 工具可见性治理 | Tool Registry + Policy Pipeline |
| L2 执行层 | 任务协议与收敛 | checklist + done criteria + Evaluate |
| L3 会话层 | 追问节奏治理 | queue/collect/debounce/drain |
| L4 证据层 | 可验证与观测 | execution ledger + evidence refs + events |

### 7.3 统一执行协议（Canonical Loop）

```text
User Request
  -> Supervisor: 判定 execution_mode + 下发 checklist/done_criteria
  -> Expert: 调工具执行检查项
  -> Evaluate: 校验 checklist 覆盖 + evidence 完整性
     -> 不满足：continue
     -> 满足：end(done/partial/blocked)
  -> Postprocess: 输出结构化报告 + 证据摘要
```

### 7.4 统一状态与事件约束

最小字段集：

- `protocol_context`：execution_mode/done_criteria/round limits  
- `checklist_state`：每项状态、工具调用、证据引用  
- `tool_execution_ledger`：真实调用账本  
- `final_report`：结构化输出对象  
- `events`：至少包含 tool_call_id、trace_id、convergence_reason

---

## 8. 综合实施路线图（四文档融合版）

### 8.1 总体节奏（建议）

- **P0（1 周）**：观测补齐（tool_call_id、trim 指标、stop reason）。  
- **P1（2 周）**：执行协议闭环（A+C、done criteria）。  
- **P2（2 周）**：诊断工具 + evidence 对象。  
- **P3（2~3 周）**：followup queue（先 queue 后 collect）。  
- **P4（2~3 周）**：工具策略分层（role/user/agent）。  
- **P5（远期）**：高阶编排（handoff queue 深化或 subagent）。

### 8.2 与四文档的优先级对齐

| 阶段 | 对齐来源 | 主要目标 |
|---|---|---|
| P0 | D1 Quick Wins + D3 问题诊断 | 先把“看不见的问题”变成可观测 |
| P1 | D4 Q1/Q2/Q4 | 先做执行协议与收敛门禁 |
| P2 | D4 Q3 + D1 工具层建议 | 先做关键诊断工具闭环 |
| P3 | D3 + D2 Q3 | 多轮消息节奏稳定 |
| P4 | D2 Q4 + D1 工具治理章节 | 工具可见性分层治理 |
| P5 | D2 Q2 + D1 多意图章节 | 高阶自治编排能力 |

### 8.3 每阶段最低验收标准

- P0：定位“答非所问”是否由裁剪/丢队列导致。  
- P1：调研任务 done 不再依赖 no-tool-call。  
- P2：结论与 evidence_refs 可一一映射。  
- P3：连续输入场景下错位回复明显下降。  
- P4：不同角色可见工具集可测且稳定。  
- P5：复合任务具备可中断、可追踪、可回收能力。

---

## 9. 观测指标、风险与回滚（统一版）

### 9.1 关键指标

1. 调研请求工具执行率。  
2. 结论 evidence 绑定率。  
3. 无证据宣称次数。  
4. 追问错位率（答非所问）。  
5. 队列等待时长与丢弃率。  
6. 工具策略误伤率（核心工具不可见事件）。

### 9.2 风险清单

- 协议过重导致时延增加。  
- 收敛门槛过严导致流程卡住。  
- 队列并发状态增加复杂度。  
- 策略配置误伤核心能力。

### 9.3 回滚策略

- 协议可按 execution_mode 灰度启用（仅 investigate）。  
- 队列可退回严格串行（queue only）。  
- 工具策略可回退到角色默认 profile。  
- 高阶编排失败时退回单 handoff 流程。

---

## 10. 代码落地映射（统一行动清单）

> 该清单来自四文档的交叉整合，用于直接开工。

### 10.1 协议与状态

- `app/ai/prompts/agent_prompts.py`：补 `execution_mode/checklist/done_criteria` 规则。  
- `app/ai/workflow/multi_agent_graph.py`：重写 evaluate 收敛条件。  
- `app/ai/state.py`：新增 `protocol_context/checklist_state/tool_execution_ledger/final_report`。  
- `app/ai/events.py`：补充 `tool_call_id/trace_id/convergence_reason` 字段。

### 10.2 诊断工具

- `app/ai/tools/diagnostic_tools.py`（建议新增）：  
  - `kb_inventory_scan`  
  - `ragflow_health_check`  
  - （可选）`kb_sample_query`

### 10.3 队列与多轮

- `app/services/chat_service.py`：接入 queue/collect 控制逻辑。  
- （建议新增）`app/ai/queue/followup_queue.py`：消息队列核心实现。  
- SSE 输出补充 queue 状态事件。

### 10.4 工具治理

- （建议新增）`app/ai/tool_registry.py`：统一注册。  
- （建议新增）`app/ai/tool_policy.py`：策略过滤管线。  
- 用 feature flag 控制新旧链路切换。

---

## 11. 新会话复用摘要（强化版）

> 你后续开启新会话可直接贴下面这段。

```markdown
你是我的架构重构助手。项目是 FastAPI + LangGraph，多 Agent（Supervisor + 专家路由）架构。

核心共识：
- OpenClaw“看起来会自己知道做什么”不是因为 skill 多，而是因为多层规则 + 执行协议 + 工具策略 + 队列节奏 + 证据化收敛。
- 我当前路线是“先协议后 skill，先可证后自治”。

请按以下优先级给出增量改造（禁止推倒重来）：
1) execution_mode + checklist + done_criteria；
2) evaluate 从 no-tool-call 改为 evidence-driven；
3) 新增 kb_inventory_scan/ragflow_health_check；
4) 接入 queue/collect，先 queue 后 collect；
5) 工具策略 role/user/agent 分层过滤。

输出必须包含：改动文件、状态字段、事件字段、验收用例、回滚策略。
参考主档：output/openclaw源码解析/OpenClaw源码解析-长期主档.md
```

---

## 12. 维护模板（持续更新必填）

### 12.1 ADR-Lite 模板

```markdown
### ADR-YYYYMMDD-XX: [决策标题]
- 背景：
- 决策：
- 影响模块：
- 风险：
- 回滚条件：
- 验收标准：
```

### 12.2 实验记录模板

```markdown
### EXP-YYYYMMDD-XX: [实验主题]
- 假设：
- 变更：
- 数据样本：
- 结果：
- 结论：
- 下一步：
```

### 12.3 版本快照模板

```markdown
### Snapshot YYYY-MM-DD
- 协议版本：
- 队列模式：
- 工具策略版本：
- 已知问题：
- 下周重点：
```

---

## 13. 更新日志

| 日期 | 版本 | 变更摘要 |
|---|---|---|
| 2026-02-18 | v1 | 初版主档（摘要型） |
| 2026-02-18 | v2 | 四份核心文档全量整编，补充逐章吸收、覆盖矩阵、统一蓝图与落地清单 |
| 2026-02-18 | v3 | 新增三篇源码级专题：工具策略管线、Followup 队列、Subagent 生命周期，并更新目录索引与专题导航 |
| 2026-02-18 | v4 | 补充 OpenClaw 记忆机制源码复核细节（flush/`/new`/MMR/temporal/QMD fallback）并新增与你当前实现差异快照 |
| 2026-02-18 | v5 | 新增《OpenClaw迁移改造蓝图-代码级实施版》，包含 P0/P1/P2 路线、文件级改造清单、状态/事件/工具 schema、验收与回滚策略 |
| 2026-02-18 | v6 | 新增《OpenClaw吃透度补强清单-模块覆盖矩阵》，明确覆盖等级（L0~L4）、B0/B1/B2 补强任务与“吃透完成”DoD |
| 2026-02-18 | v6 | 固化实施决策：只上全版机制（扩展至 P0~P5），当前先文档冻结与方案融合，暂不立即进入开发排期 |
| 2026-02-18 | v7 | 新增 D5 整编（第 16 章）：模型解析层（provider 归一化/别名/白名单）、模型容错层（fallback 候选链/探测恢复/错误分类）、模型实例化层（四级 fallback 查找）、插件扩展架构（37 个官方插件/Plugin API/工厂模式）；更新专题导航至第 17 章 |
| 2026-02-18 | v8 | 蓝图补齐 D5 实施映射（模型解析/容错/插件治理）并纳入 P2.5（记忆闭环）/P4.5（模型容错与插件治理）阶段口径 |
| 2026-02-18 | v9 | 新增《OpenClaw吃透度补强清单-模块覆盖矩阵》并纳入第 17 章专题导航与目录索引，用于判定“是否真的吃透 OpenClaw” |
| 2026-02-18 | v10 | 新增《OpenClaw吃透度补强-B0-1审批链路脚本级验证手册》，固化 allow-once/allow-always/deny/timeout 四场景动态验证流程与证据模板 |
| 2026-02-18 | v11 | 新增《OpenClaw吃透度补强-B0-2注册表恢复与公告补发验证手册》《OpenClaw吃透度补强-B0-3跨Channel-Collect路由一致性验证手册》《OpenClaw吃透度补强-B1-B2扩展验证手册》，补齐 B0/B1/B2 验证文档闭环并同步专题导航 |

---

## 14. 当前最终结论（2026-02-18）

在你的项目阶段，最佳策略已经明确：

**第一阶段先做执行协议、收敛门禁、证据链；第二阶段再做队列与策略分层；第三阶段再引入高阶子任务编排。若启动实施则按全版路径推进（P0~P5，含 P2.5/P4.5），不做小版替代。**

当前执行状态补充：

- 已确认“只上全版机制”；
- 当前先完成文档融合与方案冻结；
- 待监控基线与风险台账就绪后再进入开发排期。

这样可以最快从“看起来像在做”进化到“真的在做、能证明在做、稳定地做”。

---

## 15. 四文档章节级覆盖核对表（审阅专用）

### 15.1 D1 覆盖核对（综合分析报告）

| D1 原章节 | 主档映射 | 核对结果 |
|---|---|---|
| 一、对标总览 | 第 3.1、第 2 章 | ✅ |
| 二、记忆层（2.1~2.6） | 第 3.2 | ✅ |
| 三、工具编排与策略 | 第 3.3、第 7.2、第 8 章 | ✅ |
| 四、多意图拆分与并行调度 | 第 3.4、第 8 章 | ✅ |
| 五、追问/消息队列 | 第 3.5、第 5 章、第 8 章 | ✅ |
| 六、技能/插件治理 | 第 3.6、第 7.2 | ✅ |
| 七、意图路由与安全护栏 | 第 2.3、第 7.2 | ✅ |
| 八、综合改进路线图 | 第 8 章 | ✅ |
| 九、关键设计决策 | 第 9、第 14 章 | ✅ |
| 十、与已有方案关系 | 第 1、第 3~6 章 | ✅ |
| 十一、Quick Wins | 第 8.1、第 10 章 | ✅ |

### 15.2 D2 覆盖核对（四大核心问题）

| D2 原章节 | 主档映射 | 核对结果 |
|---|---|---|
| Q1 动态加载 | 第 4.1、第 8 章 | ✅ |
| Q2 多意图与并行 | 第 4.2、第 8 章 | ✅ |
| Q3 队列机制 | 第 4.3、第 5 章、第 8 章 | ✅ |
| Q4 用户级隔离 | 第 4.4、第 7.2、第 8 章 | ✅ |
| 综合实施路线图 | 第 8.1、第 8.2 | ✅ |
| 风险提示 | 第 9 章 | ✅ |

### 15.3 D3 覆盖核对（复合任务与 Collect）

| D3 原章节 | 主档映射 | 核对结果 |
|---|---|---|
| 一、问题定义 | 第 5.1 | ✅ |
| 二、当前架构现状分析 | 第 5.2 | ✅ |
| 三、OpenClaw 的解决方案 | 第 5.3 | ✅ |
| 四、本项目实现方案 | 第 5.4 | ✅ |
| 五、方案对比 | 第 5.5、第 8.2 | ✅ |
| 六、实施路线图 | 第 8.1、第 8.3 | ✅ |
| 七、风险与缓解 | 第 9 章 | ✅ |
| 八、关键决策记录 | 第 9.2、第 14 章 | ✅ |

### 15.4 D4 覆盖核对（执行协议与诊断工具）

| D4 原章节 | 主档映射 | 核对结果 |
|---|---|---|
| Q1 最小规则集模板 | 第 6.2、第 7.3 | ✅ |
| Q2 协议层级（A+C） | 第 6.3、第 7.3 | ✅ |
| Q3 诊断工具 Schema | 第 6.4、第 7.4 | ✅ |
| Q4 证据链与状态追踪 | 第 6.5、第 7.4、第 9 章 | ✅ |
| 落地路线图（两周） | 第 6.6、第 8 章 | ✅ |
| 附录模板 | 第 7、第 12 章 | ✅ |

### 15.5 核对结论

本主档已完成四份核心文档的章节级吸收与去重整编；后续新增内容仅需在本章补充一条映射关系并更新版本日志。

---

## 16. D5 整编：模型解析、容错与插件扩展架构（源码深挖）

> 对应来源：本轮源码阅读 `src/agents/model-selection.ts`、`src/agents/model-fallback.ts`、`src/agents/pi-embedded-runner/model.ts`、`extensions/memory-core/index.ts`

### 16.1 模型解析层（model-selection.ts）

#### 16.1.1 核心机制

OpenClaw 的模型选择不是简单的"配一个 model name"，而是一套完整的**多层解析 + 别名 + 白名单 + 归一化**体系：

1. **Provider 归一化**（`normalizeProviderId`）：将 `z.ai`/`z-ai` → `zai`、`qwen` → `qwen-portal`、`kimi-code` → `kimi-coding` 等变体统一为标准 ID，消除配置歧义。
2. **Model 归一化**（`normalizeProviderModelId`）：按 provider 分别处理，如 Anthropic 的 `opus-4.5` → `claude-opus-4-5`、Google 模型 ID 归一化。
3. **别名系统**（`buildModelAliasIndex`）：从 `agents.defaults.models` 配置中提取 alias 映射，支持用户用短名引用模型（如 `fast` → `anthropic/claude-sonnet-4-5`）。
4. **白名单过滤**（`buildConfiguredAllowlistKeys` + `buildAllowedModelSet`）：
   - 若配置了 `agents.defaults.models`，则只有白名单内的模型可用。
   - 白名单为空时 `allowAny: true`，不做限制。
   - 默认模型始终被加入白名单（防配置遗漏导致主模型不可用）。
5. **多级 fallback 解析**（`resolveConfiguredModelRef`）：
   - 先查 `agents.defaults.model.primary`。
   - 再查别名索引。
   - 无 provider 前缀时 fallback 到 `anthropic`（带 deprecation 警告）。
   - 最终兜底到 `DEFAULT_PROVIDER/DEFAULT_MODEL`。
6. **Agent 级模型覆盖**（`resolveDefaultModelForAgent`）：每个 Agent 可通过 `resolveAgentModelPrimary` 覆盖全局默认模型，实现"不同 Agent 用不同模型"。
7. **Thinking 级别解析**（`resolveThinkingDefault`）：根据配置或模型 catalog 的 `reasoning` 标记，自动决定 thinking level（off/minimal/low/medium/high/xhigh）。

#### 16.1.2 设计亮点

- **ModelRef 标准化**：所有模型引用统一为 `{ provider, model }` 二元组，消除字符串拼接歧义。
- **OpenAI Codex 特殊路由**：`gpt-5.3-codex` 前缀自动路由到 `openai-codex` provider，体现了对特殊模型的前瞻性处理。
- **Gmail Hook 模型独立配置**：`resolveHooksGmailModel` 允许 hook 使用独立模型，不与主 Agent 模型耦合。

#### 16.1.3 对你方的启示

- 你方当前模型配置是扁平的（`app/core/config.py` 中的环境变量），缺乏 provider 归一化、别名、白名单机制。
- 建议引入 `ModelRef` 标准化 + Agent 级模型覆盖，为后续多模型策略打基础。
- 白名单机制可防止用户/配置误用未授权模型。

### 16.2 模型容错层（model-fallback.ts）

#### 16.2.1 核心机制

`runWithModelFallback` 是 OpenClaw 模型调用的核心容错包装器，实现了**候选列表 + 逐个尝试 + 智能跳过 + 探测恢复**：

1. **候选列表构建**（`resolveFallbackCandidates`）：
   - 主模型（归一化后）作为第一候选。
   - `agents.defaults.model.fallbacks` 配置的备选模型按序加入。
   - 全局默认模型作为最终兜底。
   - 通过 `createModelCandidateCollector` 去重 + 白名单过滤。

2. **Auth Profile 冷却机制**：
   - 每个 provider 可有多个 auth profile（API key 轮换）。
   - 当某 provider 所有 profile 都在冷却期（rate limit），自动跳过该候选。
   - 但对主模型有**探测恢复机制**：当冷却即将到期（`PROBE_MARGIN_MS = 2min`）时，仍尝试主模型以检测是否已恢复。
   - 探测有节流保护（`MIN_PROBE_INTERVAL_MS = 30s`），防止频繁探测。

3. **错误分类与处理**：
   - `AbortError`（用户主动取消）：直接抛出，不 fallback。
   - `ContextOverflowError`：直接抛出（换模型可能更差）。
   - `FailoverError`（可恢复错误）：记录 attempt，尝试下一候选。
   - 非 FailoverError：直接抛出（不可恢复）。

4. **Image Model 独立 Fallback**（`runWithImageModelFallback`）：
   - 图像模型有独立的 primary + fallbacks 配置。
   - 容错逻辑类似但更简化（无 auth profile 冷却）。

5. **错误聚合报告**：
   - 所有候选都失败时，生成包含每个 attempt 的 `provider/model: error (reason)` 摘要。
   - 单候选失败时直接抛原始错误（保留堆栈）。

#### 16.2.2 设计亮点

- **探测恢复**是关键创新：避免因一次 rate limit 就永久停留在 fallback 模型上。
- **错误分类精确**：区分"可 fallback"和"不可 fallback"的错误，避免无意义重试。
- **Scope 隔离**：探测节流按 `agentDir + provider` 维度隔离，不同 Agent 的探测互不干扰。

#### 16.2.3 对你方的启示

- 你方当前无模型 fallback 机制，单点故障风险高。
- 建议至少实现：主模型 + 1 个 fallback + 错误分类（区分 rate limit vs 不可恢复）。
- Auth profile 轮换可作为远期目标（当前单 API key 场景下优先级低）。

### 16.3 模型实例化层（pi-embedded-runner/model.ts）

#### 16.3.1 核心机制

`resolveModel` 是将 `provider + modelId` 解析为可执行 Model 实例的最终环节：

1. **Model Registry 发现**：通过 `discoverModels(authStorage, agentDir)` 扫描已注册的模型。
2. **四级 fallback 查找**：
   - Level 1：Registry 精确匹配。
   - Level 2：Inline 模型（`models.providers` 配置中内联定义的模型）。
   - Level 3：Forward-compat 模型（`resolveForwardCompatModel`，处理新模型 ID 的向前兼容）。
   - Level 4：Provider 配置兜底（有 provider 配置但无精确模型时，构造默认 Model 实例）。
3. **Model 归一化**：所有返回的 Model 都经过 `normalizeModelCompat` 处理，确保接口一致性。
4. **友好错误提示**：对 ollama/vllm 等本地 provider，提示用户设置 API key 的具体方法。

#### 16.3.2 对你方的启示

- 你方当前模型实例化是直接构造 `ChatOpenAI` / `ChatAnthropic`，缺乏 registry + fallback 查找。
- 建议引入 Model Registry 概念，将模型实例化与业务逻辑解耦。

### 16.4 插件扩展架构（extensions/）

#### 16.4.1 架构概览

OpenClaw 的 `extensions/` 目录包含 37 个官方插件，覆盖：

- **通信渠道**（17 个）：Telegram、WhatsApp、Discord、Slack、Signal、iMessage、IRC、Line、Feishu、GoogleChat、MSTeams、Matrix、Mattermost、Nostr、Tlon、Twitch、Zalo
- **记忆后端**（2 个）：memory-core（文件系统）、memory-lancedb（向量数据库）
- **认证扩展**（3 个）：google-antigravity-auth、google-gemini-cli-auth、qwen-portal-auth
- **功能扩展**（6 个）：copilot-proxy、diagnostics-otel、llm-task、lobster、open-prose、phone-control
- **基础设施**（3 个）：device-pair、thread-ownership、voice-call/talk-voice
- **共享库**（1 个）：shared

#### 16.4.2 插件结构规范（以 memory-core 为例）

每个插件的最小结构：

```
extensions/memory-core/
├── index.ts              # 插件入口（默认导出插件对象）
├── openclaw.plugin.json  # 插件元数据（ID、名称、描述、类型）
└── package.json          # 依赖声明
```

插件入口的标准契约：

```typescript
const memoryCorePlugin = {
  id: "memory-core",
  name: "Memory (Core)",
  description: "File-backed memory search tools and CLI",
  kind: "memory",                          // 插件类型标记
  configSchema: emptyPluginConfigSchema(),  // 配置 schema（可为空）
  register(api: OpenClawPluginApi) {        // 注册回调
    api.registerTool(/* ... */);            // 注册工具
    api.registerCli(/* ... */);             // 注册 CLI 命令
  },
};
```

#### 16.4.3 Plugin API 能力

从 memory-core 的 `register` 方法可见 `OpenClawPluginApi` 至少提供：

- `api.registerTool(factory, { names })` — 注册工具（支持上下文感知的工厂函数）
- `api.registerCli(factory, { commands })` — 注册 CLI 子命令
- `api.runtime.tools.createMemorySearchTool()` — 运行时工具工厂
- `api.runtime.tools.registerMemoryCli()` — 运行时 CLI 注册

工具注册的工厂模式值得注意：工具不是静态定义，而是接收 `ctx`（含 `config`、`sessionKey`）后动态创建，支持按会话/配置差异化。

#### 16.4.4 对你方的启示

- 你方当前工具注册是硬编码在 `app/ai/tools/` 中，缺乏插件化抽象。
- OpenClaw 的插件三件套（`index.ts` + `plugin.json` + `package.json`）是一个轻量但完整的插件协议。
- 建议远期引入类似的 Plugin Registry + Plugin API，但近期优先做 Tool Registry + Policy Pipeline。

### 16.5 模型层完整架构图

```
用户请求
  │
  ▼
resolveDefaultModelForAgent(cfg, agentId)
  │  ├─ Agent 级 model override?
  │  └─ resolveConfiguredModelRef(cfg)
  │       ├─ agents.defaults.model.primary
  │       ├─ alias index 查找
  │       └─ DEFAULT_PROVIDER / DEFAULT_MODEL
  │
  ▼
resolveModel(provider, modelId, agentDir, cfg)
  │  ├─ Level 1: Model Registry 精确匹配
  │  ├─ Level 2: Inline models (providers config)
  │  ├─ Level 3: Forward-compat fallback
  │  └─ Level 4: Provider config 兜底构造
  │
  ▼
runWithModelFallback(cfg, provider, model, run)
  │  ├─ 候选列表: [primary, ...fallbacks, global_default]
  │  ├─ Auth Profile 冷却检查 + 探测恢复
  │  ├─ 逐个尝试 run(provider, model)
  │  │    ├─ 成功 → 返回结果
  │  │    ├─ AbortError → 直接抛出
  │  │    ├─ ContextOverflow → 直接抛出
  │  │    └─ FailoverError → 记录 attempt, 下一候选
  │  └─ 全部失败 → 聚合错误报告
  │
  ▼
LLM 调用执行
```

---

## 17. 源码深挖专题导航

> 本章节用于把“总览结论”与“源码证据”对齐，后续每新增专题都在此登记。

### 17.1 专题列表

| 专题 | 文件 | 对应核心问题 |
|---|---|---|
| 记忆机制 | `output/openclaw源码解析/OpenClaw深度解析-记忆机制与流程图.md` | 记忆如何保存/检索/压缩/防丢失 |
| 工具策略管线 | `output/openclaw源码解析/OpenClaw深度解析-工具策略管线与权限边界.md` | 为什么工具调用"看起来有分寸" |
| Followup 队列 | `output/openclaw源码解析/OpenClaw深度解析-Followup队列与任务循环.md` | 多轮追问为何不乱节奏 |
| Subagent 生命周期 | `output/openclaw源码解析/OpenClaw深度解析-Subagent生命周期与编排控制.md` | 为什么并行任务可控且可回收 |
| 代码级实施蓝图 | `output/openclaw源码解析/OpenClaw迁移改造蓝图-代码级实施版.md` | 如何按 P0~P5（含 P2.5/P4.5）增量改造现有 FastAPI+LangGraph |
| 吃透度补强清单 | `output/openclaw源码解析/OpenClaw吃透度补强清单-模块覆盖矩阵.md` | 是否真的吃透 OpenClaw 核心链路、还缺哪些验证 |
| B0-1 审批链路验证 | `output/openclaw源码解析/OpenClaw吃透度补强-B0-1审批链路脚本级验证手册.md` | 如何动态验证 exec 审批机制在四类决策下的真实行为 |
| B0-2 注册表恢复验证 | `output/openclaw源码解析/OpenClaw吃透度补强-B0-2注册表恢复与公告补发验证手册.md` | 如何验证 deferred announce 在重启后的恢复与补发边界 |
| B0-3 跨 Channel 路由验证 | `output/openclaw源码解析/OpenClaw吃透度补强-B0-3跨Channel-Collect路由一致性验证手册.md` | collect 模式如何防止跨路由误合并与串频道回复 |
| B1/B2 扩展验证 | `output/openclaw源码解析/OpenClaw吃透度补强-B1-B2扩展验证手册.md` | 如何补齐 sandbox 生命周期、cron 边界与延后模块验收模板 |
| 模型解析/容错/插件 | 本主档第 16 章（D5 整编） | 模型选择、fallback 容错、插件扩展架构 |

### 17.2 与本项目重构的直接映射

- 对 `app/ai/prompts/agent_prompts.py`：优先引入“执行协议 + done criteria”，再增强提示词文案。  
- 对 `app/ai/workflow/multi_agent_graph.py`：新增 `plan -> execute -> evaluate -> drain` 闭环，evaluate 不再只看 tool_call。  
- 对 `app/ai/state.py`：补 `protocol_state / queue_state / subtask_registry / evidence_ledger`。  
- 对 `app/ai/events.py`：补 `policy_applied / queue_drain / subtask_lifecycle / convergence_reason` 事件。
- 对模型层（D5）：补 `ModelRef` 解析、fallback 候选链与 `model_fallback_attempt` 观测事件。  
- 对插件层（D5）：补 `plugin_registry` 与插件生命周期事件（loaded/blocked/failed）。
- 对治理层：用《吃透度补强清单》跟踪模块覆盖等级（L0~L4）与 B0/B1/B2 验证闭环。
- 对验证层：先按《B0-1 审批链路脚本级验证手册》跑审批四场景，再进入恢复与路由一致性验证。
- 对恢复层：按《B0-2 注册表恢复与公告补发验证手册》验证 restart/retry/expiry/giveup 的收敛边界。
- 对路由层：按《B0-3 跨 Channel Collect 路由一致性验证手册》验证 collect 的跨 route 拆分防护。
- 对扩展层：按《B1/B2 扩展验证手册》补齐 sandbox 生命周期、cron 边界与延后模块验收模板。

### 17.3 持续更新规则

- 新增源码专题时，必须同时更新：
  1) 本节 17.1 专题列表；  
  2) 第 13 章更新日志；  
  3) `output/openclaw源码解析/README.md`。
