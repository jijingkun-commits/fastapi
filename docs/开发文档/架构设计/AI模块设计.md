# AI 模块详解
> 更新时间：2026-03-14

> **用途**: 作为 AI 架构设计权威入口，定义模块边界、专题导航与阅读路径。
> **文档边界**: 当前文档只保留总览、owner 边界和导航；专题正文拆分到相邻专题页，代码解读细节继续放在 `代码解读/`。

## 权威源入口与辅助源

- AI 架构总览、owner 边界与专题导航：以当前文档为入口。
- Agent 写法治理与坏味道口径：以 `../规范/多智能体开发规范.md` 和 `app/ai/AGENTS.md` 为准；当前文档不再承载“以后怎么写 agent”的长清单。
- 多智能体实现走读与调试链路：参考 [多智能体工作流](../代码解读/多智能体工作流.md) 与 [多智能体系统详解](../代码解读/多智能体系统详解.md)。
- 当总览与专题正文不一致时，以对应专题正文为准，并在当前文档修正导航与边界说明。

## 文档导航

- 全局架构入口：[系统总览](系统总览.md)
- 多智能体与状态契约：[AI模块设计_多智能体与状态契约](AI模块设计_多智能体与状态契约.md)
- 待办协作契约：[AI模块设计_待办协作契约](AI模块设计_待办协作契约.md)
- 工具、事件与流式协议：[AI模块设计_工具事件与流式协议](AI模块设计_工具事件与流式协议.md)
- 问数语义层与结果增强：[AI模块设计_问数语义层与结果增强](AI模块设计_问数语义层与结果增强.md)
- 跨 Agent 意图与运行时契约：[AI模块设计_跨Agent意图与运行时契约](AI模块设计_跨Agent意图与运行时契约.md)
- 待办专项设计：[待办Agent设计](待办Agent设计.md)
- 问数专项设计：[问数引擎设计](问数引擎设计.md)
- 流式事件协议实现解读：[SSE事件协议](../代码解读/SSE事件协议.md)
- 接口与参数契约：[接口文档](../../API文档/接口文档.md)
- 需求来源总览：[系统需求](../../产品文档/系统需求.md)
- Agent 写法治理摘要：[多智能体开发规范](../规范/多智能体开发规范.md)

---

## 推荐阅读路径

| 修改范围 | 先看哪里 | 再看哪里 |
|---|---|---|
| Agent 编排写法、坏味道、review/verify 治理 | `../规范/多智能体开发规范.md` | `app/ai/AGENTS.md` + `.cursor/rules/agent_authoring.mdc` |
| Supervisor、状态字段、handoff、owner 边界 | `AI模块设计_多智能体与状态契约.md` | `AI模块设计_跨Agent意图与运行时契约.md` |
| Todo Graph、待办确认、待办补充语义 | `AI模块设计_待办协作契约.md` | `待办Agent设计.md` |
| Tools、SSE、Custom 事件、消息与图片流式 | `AI模块设计_工具事件与流式协议.md` | `代码解读/SSE事件协议.md` |
| Data Graph、语义层、结果增强、问数治理 | `AI模块设计_问数语义层与结果增强.md` | `问数引擎设计.md` |
| 统一意图内核、clarify/handoff 合同、运行时缺口 | `AI模块设计_跨Agent意图与运行时契约.md` | `AI模块设计_多智能体与状态契约.md` |

## 模块边界速览

| 主题 | 单一 owner | 关注点 | 专题页 |
|---|---|---|---|
| 多智能体主图 | `supervisor` / 主图编排层 | 状态归属、路由、handoff、运行时 owner | [多智能体与状态契约](AI模块设计_多智能体与状态契约.md) |
| 统一 research 执行单元 | `research_subagent`（受 `supervisor` 调度） | 多来源 research、结构化 insufficiency、knowledge/web source 收口 | 当前页 + [跨Agent意图与运行时契约](AI模块设计_跨Agent意图与运行时契约.md) |
| Todo 协作闭环 | `todo_graph` | 待办意图、确认、补充、工具调用协作 | [待办协作契约](AI模块设计_待办协作契约.md) |
| 工具与事件 | `tools` + `events` + service streaming layer | 工具可见性、SSE/custom 事件、图片流式、消息处理 | [工具、事件与流式协议](AI模块设计_工具事件与流式协议.md) |
| 问数语义层 | `data_graph` / data semantic layer | Vanna/RAG、语义推理、结果增强、权限与观测 | [问数语义层与结果增强](AI模块设计_问数语义层与结果增强.md) |
| 跨 Agent 运行时合同 | `intent/policy/resolver` + runtime contract | 统一帧、clarify、goal resolver、缺口可见性、独立工作流 | [跨 Agent 意图与运行时契约](AI模块设计_跨Agent意图与运行时契约.md) |

## Research Subagent 一期冻结（2026-03-14）

| 主题 | 正式结论 | 禁止动作 |
|---|---|---|
| owner 边界 | `supervisor` 继续是唯一主会话 owner，负责 planning、最终答复和错误收口；`research_subagent` 只负责单次 research 执行 | 不允许把 research_subagent 变成新的对话 owner，也不允许直接向用户透传研究 scratchpad |
| research 语义出口 | `research` 语义固定长在 `intent/goal_resolver`，由 goal bucket 决定是否升级到 `research_subagent` | 不允许在 `multi_agent_graph`、`attachment_planning`、`app/services/**` 重新补 research 关键词主路由 |
| 首批范围 | 一期只引入 1 个统一 `research_subagent`，首批只覆盖 `knowledge + web` 多来源研究、对比、归纳、证据汇总 | 不允许把 `todo_graph`、`data_graph` 或附件系统一起 agent 化，也不拆 `knowledge/web/attachment` 三个平级 research agent |
| atomic tool 保留 | `knowledge_search` 与 `search_tool` 继续保留为 direct tool 快路径；`knowledge_research` / `web_research` 只允许退居内部 source provider 或兼容 helper | 不允许继续把 `knowledge_research` / `web_research` 作为 Supervisor 首选 research surface 并行暴露 |
| 附件合同 | 附件继续 route-agnostic，先进入 supervisor planning；只有用户真实目标命中 research bucket 时，附件才可作为一次性 research 输入 | 不允许因为“有附件 / 多附件 / document probe”就默认走 research_subagent |
| 结果与展示合同 | `research_subagent` 返回 `summary/evidence/insufficiency`，并可附带 `media_refs`；最终图文展示仍复用 canonical `display_blocks / kb_images` 链路 | 不允许为 research 新发明第二套图片协议，也不允许把 research 结果降级回“只剩纯文本摘要” |

补充说明：

1. `research_subagent` 的定位是受控执行单元，不是替代主图的第二条聊天主链。
2. research 失败或证据不足时，必须返回结构化 `insufficiency`，由 `supervisor` 决定如何向用户解释，不把原始网页噪声直接透传到最终答复。
3. 知识库图文展示的 canonical owner 仍然是 `display_blocks / kb_images`；research 只负责提供 `media_refs`，不持有最终渲染协议。

## 📂 目录结构

当前目录树与核心落点已迁入 [AI模块设计_多智能体与状态契约](AI模块设计_多智能体与状态契约.md#-目录结构)。

## 🔄 MultiAgentGraph 架构

多智能体主图、状态定义、生命周期治理、路由机制和运行时 owner 收口已迁入 [AI模块设计_多智能体与状态契约](AI模块设计_多智能体与状态契约.md)。
送模前上下文工程与预算账本入口当前仍由 `app/ai/context_engineering.py` 承担；在未单独拆出专题页前，相关实现调整默认从该模块与“多智能体与状态契约”专题一起追踪。

## 📋 Todo Graph 架构

Todo Graph 的节点职责、流程图、确认语义和协作约束已迁入 [AI模块设计_待办协作契约](AI模块设计_待办协作契约.md)。待办能力的更细节正文继续以 [待办Agent设计](待办Agent设计.md) 为补充源。

## 🛠️ Tools 详解

工具体系、事件发送方式、消息处理、图片双路径和流式协议相关正文已迁入 [AI模块设计_工具事件与流式协议](AI模块设计_工具事件与流式协议.md)。

## 📊 问数 Agent 语义层 (Semantic Layer)

问数语义层、Vanna/RAG、结果增强规则、权限控制与数据查询治理已迁入 [AI模块设计_问数语义层与结果增强](AI模块设计_问数语义层与结果增强.md)。

## 跨 Agent 会话意图内核

统一意图内核、统一帧、handoff 协议、澄清状态机和运行时落点已迁入 [AI模块设计_跨Agent意图与运行时契约](AI模块设计_跨Agent意图与运行时契约.md)。

## 运行态缺口可见性收敛（2026-03-08）

运行态缺口可见性相关规则已迁入 [AI模块设计_跨Agent意图与运行时契约](AI模块设计_跨Agent意图与运行时契约.md#运行态缺口可见性收敛2026-03-08)。

## 📝 AI 出题独立工作流（2026-03）

AI 出题独立工作流的当前落点与运行时协同说明已迁入 [AI模块设计_跨Agent意图与运行时契约](AI模块设计_跨Agent意图与运行时契约.md#-ai-出题独立工作流2026-03)。
