# 项目记忆（Layer4）

用于记录会影响后续实现的历史决策。  
本文件是“人工决策记录”，不等同于自动扫描产物。

## 生效决策索引（ACTIVE 优先，建议最多 20 条）
- 2026-03-09｜response guidance 收敛为结构化 contract（ACTIVE）→ `docs/plans/2026-03-09-memory-intent-lean-cleanup-design.md`
- 2026-03-09｜document_memory_repo 列表契约改为默认窄返回（ACTIVE）→ `docs/plans/2026-03-09-memory-intent-lean-cleanup-design.md`
- 2026-03-08｜memory intent 删除解析收敛到 resolver（ACTIVE）→ `docs/plans/2026-03-08-memory-intent-resolver-contract-design.md`
- 2026-03-07｜聊天控制面恢复/终止语义冻结（ACTIVE）→ `docs/API文档/接口文档.md`
- 2026-03-07｜DB 驱动渐进式 Skill Loader Phase A 冻结（ACTIVE）→ `docs/plans/2026-03-07-db-backed-progressive-skill-loading-design.md`
- 2026-03-05｜规则分层落地（ACTIVE）→ `AGENTS.md`
- 2026-03-06｜MCP 权威配置收敛（ACTIVE）→ `docs/plans/2026-03-06-mcp-governance-design.md`
- 2026-03-06｜复合提问多模态响应契约收敛（ACTIVE）→ `docs/plans/2026-03-06-composite-query-multimodal-response-design.md`
- 2026-03-06｜Clarify 发散/冻结分流口径调整（ACTIVE）→ `.cursor/commands/jjk-clarify.md`
- 2026-03-07｜`/ask` 退化为 clarify 兼容壳（ACTIVE）→ `.cursor/commands/ask.md`
- 2026-03-06｜cardrun 默认执行器切换至 wtimp（ACTIVE）→ `docs/plans/2026-03-06-cardrun-wtimp-executor-design.md`
- 2026-03-06｜工程减法退役流程冻结（ACTIVE）→ `docs/plans/2026-03-06-workflow-gate-retirement-design.md`
- 2026-03-07｜wt-flow merge 统一收口到 common repo（ACTIVE）→ `docs/plans/2026-03-07-cardrun-wtflow-execution-issues.md`

## 记录模板
- 日期：YYYY-MM-DD
- 状态：ACTIVE / SUPERSEDED / DEPRECATED
- 决策主题：
- 背景与问题：
- 最终决策：
- 取舍理由：
- 影响范围：
- 回退/失效条件：
- 关联文档/代码：

## 治理规则
- 仅记录长期有效决策，不记录一次性执行日志。
- 单条记录建议 8~12 行，聚焦“决策与理由”，不贴大段实现细节。
- 当决策被替代时，将原记录状态更新为 `SUPERSEDED` 并链接替代记录。
- 历史记录按月归档至 `docs/内部参考/决策归档/`，本文件保留近期生效与关键里程碑。

## 决策记录

### 2026-03-07 DB 驱动渐进式 Skill Loader Phase A 冻结
- 状态：ACTIVE
- 决策主题：Skill 运行时收敛到 progressive loader，Phase A 的 schema 真理源、会话态与 canonical replay 一次冻结
- 背景与问题：当前聊天主链仍依赖 hybrid 检索后静默注入 `skill_context`，导致命中决策、状态归属与回放语义散落；同时 catalog metadata 若继续落在 `t_agent_skills` 兼容表，会形成双真理源
- 最终决策：聊天主路径统一为 `catalog preload -> load_skills -> additional_kwargs.skill_runtime`；catalog/runtime metadata 真理源固定为 `t_agent_skill_definitions + t_agent_skill_versions`；Phase A 持久化字段最小集冻结为 `catalog_path/catalog_order/catalog_description/when_to_use`
- 取舍理由：先在正确层级消除“后端替模型选 Skill + 双源 metadata + replay 不可还原”的结构性问题，再按需演进目录树与资源包能力
- 影响范围：`app/services/skill_service.py`、`app/ai/workflow/multi_agent_graph.py`、`app/ai/state.py`、`app/ai/protocol.py`、`app/models/agent_skill.py`、`app/api/v1/endpoints/skill_admin_api.py`、`alembic/versions/*`
- 回退/失效条件：若仅靠 `catalog_path` 派生无法满足权限/排序/运营配置，可升级到 Phase B 增加层级字段或资源表；回退时关闭 `feature.enable_progressive_skill_loading` 并切回 `skill.runtime_mode=hybrid_rag`
- 关联文档/代码：`docs/plans/2026-03-07-db-backed-progressive-skill-loading-design.md`

### 2026-03-07 聊天控制面恢复/终止语义冻结
- 状态：ACTIVE
- 决策主题：`interrupt/resume/cancel/disconnect` 与普通聊天消息彻底分离，恢复旧 run 只能走控制面
- 背景与问题：用户在流式处理中遇到中断、断流或网关报错时，容易把“继续”“你刚刚中断了”作为普通消息发送，导致控制动作与新用户意图混杂，放大旧瞬态状态污染风险
- 最终决策：`interrupt` 后只能调用 `POST /api/v1/chat/resume`；`cancel/stopped` 属于终态，不允许 resume；`disconnect/transport error` 不得被翻译成聊天文本“继续”，应等待当前 run 收口或先 cancel 再重发；同线程历史继续保留，但当前轮只处理最后一条 `HumanMessage`
- 取舍理由：优先保持控制面与意图层职责单一，避免通过自然语言兼容层掩盖状态机问题，也避免把半成品 AI 回复当最终历史展示
- 影响范围：聊天前端状态机、`app/services/chat_service.py`、`app/services/run_control_service.py`、`app/ai/workflow/multi_agent_graph.py`、`app/repositories/chat_repo.py`、聊天 API/架构文档
- 回退/失效条件：若后续引入显式 reconnect/reset-checkpoint 能力，并把瞬态状态改为真正非持久化字段，可重新评估“断流后直接续跑/重发”的交互口径
- 关联文档/代码：`docs/API文档/接口文档.md`、`docs/开发文档/架构设计/AI模块设计.md`、`app/services/chat_service.py`、`app/ai/workflow/multi_agent_graph.py`

### 2026-03-06 MCP 权威配置收敛
- 状态：ACTIVE
- 决策主题：Codex MCP 配置统一以用户本地运行时配置为权威源，项目内 `.mcp.json` 退化为协作镜像
- 背景与问题：`/Users/jijingkun/.codex/config.toml` 与仓库内 `.mcp.json` 并存且不一致，导致 GitHub MCP 缺 Token、`vibe_kanban` 启动命令漂移、排障口径不统一
- 最终决策：当前会话统一以 `/Users/jijingkun/.codex/config.toml` 为权威配置；`.mcp.json` 只保留无敏感信息的镜像；新增项目体检脚本在业务使用前暴露缺 Token、缺本地二进制、缺运行态等根因
- 取舍理由：先修配置治理层而不是继续堆补丁，既消除双源漂移，也避免将敏感信息继续留在仓库
- 影响范围：`/Users/jijingkun/.codex/config.toml`、`.mcp.json`、MCP 使用流程、工作流文档、体检脚本
- 回退/失效条件：若后续 Codex 支持项目级单一 MCP 权威源且可安全管理密钥，可将镜像与全局配置再收敛为单源
- 关联文档/代码：`docs/plans/2026-03-06-mcp-governance-design.md`、`docs/plans/2026-03-06-mcp-governance-plan.md`、`docs/开发文档/工作流/开发工作流.md`

### 2026-03-05 规则分层落地
- 状态：ACTIVE
- 决策主题：建立 Layer1~Layer4 执行模型
- 背景与问题：规则散落在 AGENTS、rules、skills、工具偏好中，执行优先级不够显式
- 最终决策：在 `AGENTS.md` 明确层级顺序与冲突处理，并以本文件承接长期决策
- 取舍理由：降低规则冲突与口径漂移，提升可执行性与可审计性
- 影响范围：全仓库协作流程与代理执行方式
- 回退/失效条件：若后续引入统一规则编排系统，可将本文件迁移为该系统的 ADR 源
- 关联文档/代码：`AGENTS.md`

### 2026-03-05 Layer1/Layer2 去重口径
- 状态：ACTIVE
- 决策主题：Layer1 与 Layer2 重复条款收敛
- 背景与问题：`AGENTS.md` Layer1 与 `.cursor/rules/core.mdc` 在“架构先行/拒绝补丁/文档先行”存在重复描述，违反“Layer1 仅保留治理口径”的定位
- 最终决策：Layer1 改为“门禁 + 引用”写法，不再复述技术细则；细则唯一源保持在 `.cursor/rules/core.mdc` 与 `.cursor/rules/doc_sync.mdc`
- 取舍理由：减少双份维护与口径漂移，保留 Layer1 审核门禁能力
- 影响范围：规则维护流程、后续新增条款写法、代理执行一致性
- 回退/失效条件：若 Layer2 文件结构重构，需同步更新 Layer1 的引用路径与条款索引
- 关联文档/代码：`AGENTS.md`、`.cursor/rules/core.mdc`、`.cursor/rules/doc_sync.mdc`

### 2026-03-05 分支端口自动校验与 merge 防错门禁
- 状态：ACTIVE
- 决策主题：verify 与 cardrun 的上下文防错收敛
- 背景与问题：仅依赖 `pwd/branch/worktree` 观测不能证明“测对分支”；多会话并行时存在误 merge 风险
- 最终决策：Web/E2E/UAT 场景统一通过 `scripts/vk_ports.sh` 计算当前分支端口；`wt-flow merge` 增加“会话卡片=当前激活卡 + 状态已 verified”硬门禁，并在 `ahead=0` 时 `MERGE_NO_COMMITS` 直接阻断；`/jjk-imp-ws` 与 `/jjk-cardrun` 强制回填 `commit_sha`（门禁类无文件改动可用空提交并注明原因）
- 取舍理由：避免人工手输分支/端口，减少误测与误合并
- 影响范围：`/jjk-verify`、`/jjk-cardrun`、`scripts/wt-flow.sh`、`AGENTS.md`
- 回退/失效条件：若未来引入统一会话编排器并提供不可篡改的上下文绑定，可降级为软校验
- 关联文档/代码：`AGENTS.md`、`.cursor/commands/jjk-verify.md`、`.cursor/commands/jjk-cardrun.md`、`scripts/wt-flow.sh`

### 2026-03-06 复合提问多模态响应契约收敛
- 状态：ACTIVE
- 决策主题：SSE 复合输出（文字/表格/图片）统一契约与降级语义冻结
- 背景与问题：`data_type` 扩展依赖手工分支，易出现“新增类型前端静默丢失”与“实时/回放口径漂移”
- 最终决策：保持单通道 `result(data_type,data,message?)`；以后端 Pydantic union 作为单一契约源，生成 schema 与前端类型；未知类型前端可见 fallback，缺必填字段后端归一 `error` 事件；canonical 回放字段固定为 `additional_kwargs.result_event`（读旧写新）
- 取舍理由：在不重写协议的前提下，最小改造实现强类型、可观测、可回放一致与可演进门禁
- 影响范围：`app/ai/*`、`app/services/chat_service.py`、`web/src/lib/backend.ts`、`web/src/hooks/useSSEStream.ts`、`web/src/components/chat/messages/ai.tsx`、契约文档与 CI 门禁
- 回退/失效条件：若 OAS 3.2 工具链全面稳定并可直接覆盖 SSE 代码生成，可将过渡期 AsyncAPI 文档收敛回单一 OAS3.2 契约
- 关联文档/代码：`docs/plans/2026-03-06-composite-query-multimodal-response-design.md`

### 2026-03-06 Clarify 发散/冻结分流口径调整
- 状态：ACTIVE
- 决策主题：`/jjk-clarify` 采用单指令闭环（命令内完成探索与冻结）
- 背景与问题：原口径要求“可用时必须先走 brainstorming”，与 `/jjk-clarify` 的单方案冻结目标冲突，导致执行时频繁输出“规则冲突声明”，降低可用性
- 最终决策：`/jjk-clarify` 默认在命令内执行“探索轮 + 冻结轮”；默认提问模式统一为问题包（`question_mode=package`），歧义场景降级为单题追问；审批前必须写出 `clarify_consistency_check`，并满足 `clarify_phase=approval`、`open_questions_count=0`；同时新增 `python3 scripts/check_clarify_contract_consistency.py` 体检命令
- 取舍理由：保留探索能力且不增加命令切换成本，并用显式状态机与自动体检降低命令/模板/镜像漂移
- 影响范围：`.cursor/commands/jjk-clarify.md`、`.agents/skills/jjk-clarify/SKILL.md`、命令速查文档与 Codex prompts 镜像
- 回退/失效条件：若后续统一流程框架强制探索与冻结命令解耦，可回退为“两阶段命令链”
- 关联文档/代码：`.cursor/commands/jjk-clarify.md`、`docs/开发文档/工作流/开发工作流.md`、`docs/开发文档/技巧与速查/AI协作速查表.md`、`docs/开发文档/技巧与速查/vibe-coding开发技巧.md`

### 2026-03-07 `/ask` 退化为 clarify 兼容壳
- 状态：ACTIVE
- 决策主题：`/ask` 从独立发散入口降级为 `/jjk-clarify` 兼容别名
- 背景与问题：`/ask` 与 `/jjk-clarify` 同时被描述为主入口，导致工作流主链、状态归属与用户心智出现双源漂移
- 最终决策：默认研发链路统一以 `/jjk-clarify` 起步；收到 `/ask` 时在当前会话内立即并入 `/jjk-clarify`，不再维护独立 `brainstorm.md` 或独立下游门禁；仅保留历史兼容说明
- 取舍理由：以最小兼容成本换取单一状态机、单一权威产物与更低命令切换负担
- 影响范围：`.cursor/commands/ask.md`、工作流手册、速查表、Codex prompts 镜像
- 回退/失效条件：若后续平台必须恢复独立“仅发散不冻结”命令，应以新命令或新契约恢复，而不是回滚旧 `/ask` 双入口语义
- 关联文档/代码：`.cursor/commands/ask.md`、`docs/开发文档/工作流/开发工作流.md`、`docs/开发文档/工作流/指令用法_实现方式_工程流全景手册.md`、`docs/开发文档/技巧与速查/vibe-coding开发技巧.md`

### 2026-03-06 cardrun 默认执行器切换至 wtimp
- 状态：ACTIVE
- 决策主题：`cardrun` dispatch 主链统一到 `jjk-wtimp`（`executor_mode=cardrun_dispatch`）
- 背景与问题：`cardrun` 原链路默认分派 `imp-ws`，导致“编排层强约束”与“执行层 worktree 生命周期”分离，commit 证据门禁难以在同一收口链上落地
- 最终决策：主链改为 `/jjk-plan -> /jjk-vkplan -> /jjk-cardrun -> /jjk-wtimp`；kernel 默认执行器设为 `wtimp`，dispatch 阶段缺失 `commit_sha` 直接 `CARDRUN_NO_COMMIT_EVIDENCE` 阻断；`wtimp` 在 `cardrun_dispatch` 模式禁止重复 merge
- 取舍理由：以最小改造统一“调度→执行→证据→收口”责任边界，降低双 merge 与伪完成风险
- 影响范围：`scripts/coder4/coder4_bootstrap_kernel.py`、`.cursor/commands/jjk-cardrun.md`、`.cursor/commands/jjk-wtimp.md`、`.cursor/commands/jjk-vkplan.md`、`.cursor/commands/jjk-create-pr.md` 及对应 skills
- 回退/失效条件：若 `wtimp` 执行链异常，可通过 `--dispatch-executor`/`CODER4_DISPATCH_EXECUTOR` 临时切回兼容执行器；若后续出现统一执行编排器，应将本决策升级为平台级执行契约
- 关联文档/代码：`docs/plans/2026-03-06-cardrun-wtimp-executor-design.md`、`docs/内部参考/迭代需求/cardrun内置wtimp执行器_requirements.md`、`docs/内部参考/迭代需求/cardrun内置wtimp执行器_implementation_plan.md`


### 2026-03-07 wt-flow merge 统一收口到 common repo
- 状态：ACTIVE
- 决策主题：`wt-flow merge` 的基线分支合并上下文固定归属 `common repo root`，不再依赖当前 card worktree checkout
- 背景与问题：当前 `cmd_merge` 在 card worktree 内执行时，会把当前 checkout 当成 merge 驱动仓并尝试 `git checkout master`；当 `master` 已被主工作区占用时，Git 会直接报 `already used by worktree`，导致已 verified 的卡片无法在原位完成 merge
- 最终决策：保留 `rebase` 在 card worktree 执行，但把 `dirty policy`、`checkout base_branch`、`git merge --no-ff` 与 merge 结果回写统一收口到 `common repo root`；执行目录不再作为 merge 成败前提
- 取舍理由：先修正“会话 worktree 与基线仓职责混淆”的结构性问题，保证 cardrun / wt-flow 在 worktree 体系下行为一致，而不是继续依赖“退回主仓手工 merge”的人工绕行
- 影响范围：`scripts/coder4/wt-flow.sh`、`tests/unit/test_coder4_wt_flow_verified_state.py`、`docs/plans/2026-03-07-cardrun-wtflow-execution-issues.md`
- 回退/失效条件：若后续引入专用 merge-driver worktree 或平台级 merge service，可将本决策升级为新的 merge 执行抽象；若 common repo root 不再承担基线仓职责，本决策失效
- 关联文档/代码：`docs/plans/2026-03-07-cardrun-wtflow-execution-issues.md`、`scripts/coder4/wt-flow.sh`

### 2026-03-06 工程减法退役流程冻结
- 状态：ACTIVE
- 决策主题：L1 门禁脚本退役执行口径统一为“迁移入口 -> 兼容壳 -> 零调用观测 -> 再删除”
- 背景与问题：`工程减法体检报告_2026-03-06.md` 中存在“候选可删”与“3.1 NO-GO 冻结”并存，团队执行口径易漂移
- 最终决策：以 `工程减法体检报告_2026-03-06_v3.md` 作为唯一执行基线；先建统一入口 `check_workflow_contract.py`，旧 L1 脚本先 wrapper 化并完成引用迁移，连续 7 天零调用后再删除旧实现
- 取舍理由：在减法目标下优先保证设计合理性与主干流程完整性，避免“先删后补”的架构级故障
- 影响范围：`scripts/check_*` L1 门禁脚本、`.cursor/commands/*`、`.agents/skills/*`、工作流与治理文档
- 回退/失效条件：若统一入口兼容性或验收矩阵失败，回退为“旧脚本主入口 + wrapper 反向代理”，并暂停删除阶段
- 关联文档/代码：`docs/plans/2026-03-06-workflow-gate-retirement-design.md`、`docs/内部参考/工程减法体检报告_2026-03-06_v3.md`


### 2026-03-08 memory intent 删除解析收敛到 resolver
- 状态：ACTIVE
- 决策主题：删除/撤销类记忆解析统一下沉到 `memory_intent_resolver_service`，`chat_service` 只保留编排职责
- 背景与问题：上一轮为了修复“忘掉这个记忆”落库失败，把删除词表、指代修复和成功/失败话术补丁直接叠加到了 `chat_service`；但项目真实口径是“对话结束后异步记忆”，这导致语义判断、状态事实和回复策略错层耦合
- 最终决策：`chat_service` 不再维护删除关键词词表；反向记忆是否成立、目标是否唯一定位、是否需要澄清，统一由 `memory_intent_resolver_service` 输出 contract；异步主链继续 enqueue-only；`archive` 允许空 `normalized_value` 的底层校验修复保留
- 取舍理由：优先把语义判断放回正确层级，让异步 worker 与同步降级共享同一 resolver，而不是继续在聊天主链堆补丁
- 影响范围：`app/services/chat_service.py`、`app/services/memory_intent_resolver_service.py`、`app/services/memory_intent_llm_service.py`、`app/ai/prompts/agent_prompts.py`、相关 unit tests
- 回退/失效条件：若后续引入独立 memory intent worker handler/service，可把 resolver 继续上移为 worker 专属入口；若主链恢复同步记忆判定，也必须继续复用 resolver，不得把词表补丁放回 chat_service
- 关联文档/代码：`docs/plans/2026-03-08-memory-intent-resolver-contract-design.md`

### 2026-03-09 document_memory_repo 列表契约改为默认窄返回
- 状态：ACTIVE
- 决策主题：`document_memory_repo.list_documents()` 默认只返回通用文档列表字段，`source_thread_id/source_message_id` 改为调用方显式 opt-in
- 背景与问题：为了支持 memory 删除确认链，当前分支一度把 `source_thread_id/source_message_id` 直接加入 `list_documents()` 默认返回；这会让 resolver 场景字段上升为全局 repo 契约，扩大影响面
- 最终决策：`list_documents()` 新增 `include_source_refs=False`，默认保持窄返回；仅 `memory_intent_resolver_service` 的 archived 候选查询显式传入 `include_source_refs=True`
- 取舍理由：优先保持 repo 通用接口稳定、最小；场景字段只有在确实需要时才暴露，避免“为了一个调用方永久拉宽所有调用方”的设计回退
- 影响范围：`app/repositories/document_memory_repo.py`、`app/services/memory_intent_resolver_service.py`、相关 unit tests
- 回退/失效条件：若后续有多个独立场景都稳定依赖 source refs，可再评估是否升级为专用列表 DTO 或独立 repo 接口；禁止直接恢复为默认全量返回
- 关联文档/代码：`docs/plans/2026-03-09-memory-intent-lean-cleanup-design.md`、`app/repositories/document_memory_repo.py`、`app/services/memory_intent_resolver_service.py`

### 2026-03-09 response guidance 收敛为结构化 contract
- 状态：ACTIVE
- 决策主题：memory 删除后的运行时回复约束不再由 `chat_service` 直接拼接文本，而是收敛为 `response_guidance_contract` 结构化字段
- 背景与问题：上一轮虽然已把删除识别从 `chat_service` 拔到 resolver，但删除成功/幂等删除的提示文案仍由 service 直接拼接；这让状态事实与系统提示文本继续耦合在同一层
- 最终决策：`chat_service` 只输出结构化 guidance contract（如 kind/status/target/followup_behavior）；contract 的构造与渲染统一收敛到 `response_policy_service`。`multi_intent/router_blocked` 的恢复提示也统一迁入该 service，`multi_agent_graph` 只负责调用并注入 `system_context`
- 取舍理由：优先把“状态事实”“策略合同”“系统提示渲染/恢复提示”继续拆层，避免 graph/service 反复长出散落 helper，也为后续扩展到更完整的 responder/policy engine 留出稳定入口
- 影响范围：`app/services/chat_service.py`、`app/services/response_policy_service.py`、`app/ai/state.py`、`app/ai/workflow/multi_agent_graph.py`、`tests/unit/test_multi_agent_streaming_helpers.py`、相关 unit tests
- 回退/失效条件：若后续引入更完整的 response policy/responder 层，应继续以 `response_policy_service` 为迁移入口平滑演进；禁止再把文案模板直接塞回 `chat_service` 或 `multi_agent_graph`
- 关联文档/代码：`docs/plans/2026-03-09-memory-intent-lean-cleanup-design.md`、`app/services/chat_service.py`、`app/services/response_policy_service.py`、`app/ai/workflow/multi_agent_graph.py`
