# 项目记忆（Layer4）

用于记录会影响后续实现的仓库级活跃决策索引。
本文件优先服务 AI/协作者的跨任务记忆，不等同于自动扫描产物，也不承接完整 ADR 正文；需要解释完整背景、决策与后果时，优先写入 `docs/内部参考/决策记录.md` 或对应真理源文档。

## 生效决策索引（ACTIVE 优先，建议最多 20 条）

- 2026-03-13｜Codex Agent 写法治理阶段一采用“仓库级路由 + app/ai 局部覆盖 + Layer2 专项规则 + review/verify smell 清单 + drift gate”（ACTIVE）→ `AGENTS.md`、`app/ai/AGENTS.md`、`.cursor/rules/agent_authoring.mdc`、`.github/workflows/agent-governance-gate.yml`
- 2026-03-13｜`memory-bank` 收敛为仓库级活跃决策索引；完整 ADR 正文写入 `docs/内部参考/决策记录.md`（ACTIVE）→ `AGENTS.md`、`memory-bank.md`、`docs/内部参考/决策记录.md`
- 2026-03-13｜改功能默认带一次“局部复盘 + 顺手减法”，`jjk-review/jjk-verify` 同步强化架构合理性与代码精简审查（ACTIVE）→ `AGENTS.md`、`.cursor/commands/jjk-review.md`、`.cursor/commands/jjk-verify.md`、`workdocs/_templates/jjk_{review,verify}_templates.md`
- 2026-03-12｜聊天复合提问耗时治理首轮采用局部重构版 B，先修 preview 回流、frozen todo.query、coverage 口径，不先上 `Send` 全并行（ACTIVE）→ `workdocs/归档/正文/设计/2026-03-12-chat-composite-latency-local-refactor-design.md`、`workdocs/归档/正文/实施计划/chat-composite-latency-local-refactor_implementation_plan.md`
- 2026-03-12｜日志已足够定责时先报告根因，禁止默认进入修复闭环（ACTIVE）→ `AGENTS.md`、`.cursor/rules/core.mdc`
- 2026-03-12｜聊天运行态状态条固定挂在消息流尾部，禁止重新挂回 footer（ACTIVE）→ `docs/开发文档/架构设计/前端架构.md`、`web/src/components/chat/index.tsx`、`web/src/app/globals.css`
- 2026-03-12｜`DB_ECHO` 默认改为显式开启，memory intent runtime 空闲轮询与观测采样统一降噪（ACTIVE）→ `app/core/config.py`、`app/core/memory_intent_runtime.py`、`app/services/memory_intent_worker_service.py`
- 2026-03-12｜文档信息架构细化为“最终/过程/运行态 × 人类/机器”双维模型；功能级过程 bundle 固定为 `需求/设计/任务拆解/contracts|reports`（ACTIVE）→ `docs/README.md`、`docs/SUMMARY.md`、`docs/开发文档/工作流/文档信息架构.md`、`workdocs/README.md`
- 2026-03-12｜瘦身判断收敛为“职责收口优先 + whole-change-set 统计”，新增文件与 helper 同样计入增长（ACTIVE）→ `AGENTS.md`、`.cursor/rules/core.mdc`、`.cursor/rules/bugfix-minimal-change.mdc`、`docs/工程规范/lean-guard.md`
- 2026-03-12｜聊天图表继续固定为客户端 `react-vega + svg`，Next 构建层单点隔离 `canvas` 可选依赖（ACTIVE）→ `web/next.config.mjs`、`web/src/components/chat/messages/sql-result-chart.tsx`
- 2026-03-12｜聊天 live 展示正式收口到 SSE `display_blocks`，前端退役 placeholder 编译器（ACTIVE）→ `docs/开发文档/架构设计/AI模块设计.md`、`docs/API文档/接口文档.md`、`web/src/hooks/useSSEStream.ts`
- 2026-03-11｜知识库占位符降级为中间语法，AI 回复最终展示收敛到 ordered content blocks（ACTIVE）→ `workdocs/归档/正文/设计/2026-03-11-ordered-content-blocks-design.md`、`app/core/message_display_blocks.py`
- 2026-03-11｜前端 lint 入口收敛为 `eslint .`，并直接接入 `@next/eslint-plugin-next`（ACTIVE）→ `web/package.json`、`web/eslint.config.js`
- 2026-03-11｜聊天页壳层样式 single entry owner 固定为 `chat-*` 主题 class，禁止组件继续保留第二套 inline 壳层（ACTIVE）→ `docs/开发文档/架构设计/前端架构.md`、`web/src/app/globals.css`、`web/src/components/chat/index.tsx`、`web/src/components/chat/ChatInput.tsx`
- 2026-03-11｜JJK 工程流重构为 `clarify(requirements) -> design -> plan(UAT) -> imp -> verify`，正式产品/设计文档改为 `--doc` 显式发布，API 文档继续自动同步（ACTIVE）→ `.cursor/commands/jjk-{clarify,design,plan,imp,verify,api-doc-sync,arch-gate}.md`、`.agents/skills/jjk-{clarify,design,plan,imp,verify,api-doc-sync,arch-gate}/SKILL.md`、`memory-bank.md`
- 2026-03-11｜task_split 机器契约/过程报告从 docs 彻底收口到 `workdocs/任务拆解/contracts|reports`，真实运行态只认 `.artifacts/states/task_splits`（ACTIVE）→ `workdocs/归档/正文/设计/2026-03-11-docs-governance-phase2-task-split-layering-design.md`、`workdocs/归档/正文/实施计划/docs-governance-phase2-task-split-layering_implementation_plan.md`
- 2026-03-11｜根 AGENTS 收敛为总则+路由，执行长流程下沉到 `PLANS.md`（ACTIVE）→ `AGENTS.md`、`PLANS.md`、`docs/README.md`
- 2026-03-11｜瘦身规则前置为 shrink contract，旧路径残留升级为硬阻断（ACTIVE）→ `AGENTS.md`、`.cursor/rules/core.mdc`、`docs/开发文档/规范/lean-guard.md`、`.cursor/commands/jjk-arch-gate.md`、`.cursor/commands/jjk-refactor.md`
- 2026-03-11｜文档记忆启用且 Worker 就绪时，`memory.intent_async_enabled` 默认保持开启（ACTIVE）→ `docs/开发文档/快速入门/配置说明.md`、`app/core/memory_intent_runtime.py`
- 2026-03-11｜JJK 命令执行统一采用单步单目标，禁止长链整串重跑（ACTIVE）→ `.cursor/rules/core.mdc`、`.cursor/commands/jjk-verify.md`、`docs/开发文档/流程与工具/指令用法_实现方式_工程流全景手册.md`
- 2026-03-10｜文档治理收敛为 `docs/workdocs/.artifacts` 三层分治（Phase 1 保留 task_split 契约兼容路径）（ACTIVE）→ `workdocs/归档/正文/设计/2026-03-10-docs-governance-layering-design.md`、`workdocs/归档/正文/实施计划/文档分层治理与信息架构收敛_implementation_plan.md`
- 2026-03-10｜Assistant 空壳文本块在消息契约层清洗，禁止进入 checkpoint（ACTIVE）→ `docs/开发文档/架构设计/AI模块设计.md`、`app/ai/message_utils.py`
- 2026-03-10｜CardRun 分支感知基线：首轮继承当前父分支，后续固化到 task state `integration_branch`（ACTIVE）→ `workdocs/归档/正文/设计/2026-03-10-cardrun-branch-aware-base-design.md`
- 2026-03-10｜问数 TopN/Ranking contract 贯穿 handoff -> session_frame -> SQL 生成（ACTIVE）→ `docs/产品文档/问数助手需求.md`、`docs/开发文档/架构设计/AI模块设计.md`
- 2026-03-09｜Lifespan 资源治理收口为 `app.state.runtime`（ACTIVE）→ `workdocs/归档/正文/设计/2026-03-09-lifespan-runtime-consolidation-design.md`

### 2026-03-13 `memory-bank` 收敛为仓库级活跃决策索引，ADR 正文写入 `docs/内部参考/决策记录.md`

- 状态：ACTIVE
- 决策主题：`memory-bank.md` 默认不承接一次性实现或执行过程，而是只保留仓库级活跃决策摘要；完整 ADR 正文统一写入 `docs/内部参考/决策记录.md`
- 背景与问题：`memory-bank.md` 逐渐被混入实现说明、排障经过和模块内细节，既增加 Codex 上下文成本，也削弱了它作为仓库级决策索引的信号强度
- 最终决策：默认不写 `memory-bank.md`；一次性实现、排障过程、测试/验收记录、临时 workaround、模块内部细节统一回对应真理源文档、`workdocs/`、review/verify 产物或测试报告；重大技术/架构决策的完整背景、决策与后果写入 `docs/内部参考/决策记录.md`；`memory-bank.md` 仅保留摘要、影响范围和跳转链接；若同主题已有 `ACTIVE` 条目，优先原位更新，不新增平行记录
- 取舍理由：项目真正需要长期保留的是“以后默认怎么做”，而不是“这次做了什么”；把 `memory-bank` 收口为仓库级活跃决策索引、把 ADR 正文收回给人读的稳定文档，更符合长期维护和上下文治理目标
- 影响范围：`AGENTS.md`、`memory-bank.md`、`docs/内部参考/决策记录.md`、后续所有 feature / bugfix / refactor 的文档回填口径，以及 `workdocs/`、review/verify 产物的职责边界
- 失效条件：若未来仓库引入更高优先级、自动化且可审计的仓库级决策系统，能稳定替代 `memory-bank.md` 承接长期决策，可将本条标记为 `SUPERSEDED`
- 关联文档/代码：`AGENTS.md`、`memory-bank.md`、`docs/内部参考/决策记录.md`、`workdocs/**`

### 2026-03-13 改功能默认带一次“局部复盘 + 顺手减法”，`jjk-review/jjk-verify` 强化架构与精简审查

- 状态：ACTIVE
- 决策主题：不把“架构复盘 / 垃圾代码清理”做成新的阻断门禁，而是把它收敛为实现期默认动作与 review 的显式审查重点
- 背景与问题：此前尝试过把“改某块功能要重新看架构、扫垃圾代码”写成合同和失败码，但这更像控制；同时现有 `jjk-review` 更偏需求/设计/计划对账，对 touched scope 的架构合理性、复杂度上升、过度抽象和冗余残留审得不够深
- 最终决策：在 `AGENTS.md` 中补一条提示式总则，要求 AI 改功能时顺手复盘局部架构并主动识别可收口的旧入口、重复逻辑、过期 fallback、空转 helper 和孤儿测试/文档；`jjk-review` 改为同时审需求落地、设计一致性、touched scope 架构合理性和代码精简效果，并在模板中显式记录四段式架构判断与瘦身结论；`jjk-verify` 再显式消费这些 review 结论，避免最终验收只看“测试过了没”
- 取舍理由：采用“告诉 AI 该做什么”的自然语言约束，而不是“出了问题再靠新门禁阻断”；这样既更符合当前使用方式，也能让 review 真正承担架构和精简审查职责
- 影响范围：`AGENTS.md`、`.cursor/commands/jjk-review.md`、`.cursor/commands/jjk-verify.md`、`.agents/skills/jjk-review/SKILL.md`、`.agents/skills/jjk-verify/SKILL.md`、`workdocs/_templates/jjk_{review,verify}_templates.md`、后续所有 feature / bugfix / refactor 的评审与验收口径
- 失效条件：若未来存在更上层、可解释且团队接受的 review 编排协议，能稳定覆盖同样的架构与精简审查语义，可将本决策标记为 `SUPERSEDED`
- 关联文档/代码：`AGENTS.md`、`.cursor/commands/jjk-review.md`、`.cursor/commands/jjk-verify.md`、`workdocs/_templates/jjk_review_templates.md`、`workdocs/_templates/jjk_verify_templates.md`

### 2026-03-13 Codex Agent 写法治理阶段一采用“仓库级路由 + app/ai 局部覆盖 + Layer2 专项规则 + review/verify smell 清单 + drift gate”

- 状态：ACTIVE
- 决策主题：把“以后 Codex 在本仓库怎么写 agent”收口为 repo-native 规则装配，而不是继续靠口头提醒、单次 review 评论或再加一个监管 agent
- 背景与问题：用户明确指出当前 agent 写法有两个长期坏味道：一是过度流程设计，二是关键词判主语义；仓库虽然已有通用精简规则和语义边界规则，但缺少 agent 写法专项入口、专项 smell 口径和专项 drift gate，导致同类问题容易回流
- 最终决策：根 `AGENTS.md` 只新增 agent 专项路由；`app/ai/AGENTS.md` 作为局部高信号入口；`.cursor/rules/agent_authoring.mdc` 作为技术真理源；`jjk-review/jjk-verify` 与 `workdocs/_templates/jjk_{review,verify}_templates.md` 统一消费 `multi_decider_stack / keyword_primary_routing / dual_truth_design / speculative_fallback / missing_eval_evidence` 五类 smell；新增 `tests/unit/test_agent_governance_contract_docs.py` 与 `.github/workflows/agent-governance-gate.yml` 冻结关键标记
- 取舍理由：相比把所有 agent 细则继续塞回根 `AGENTS.md`，或引入新的 meta-agent 做监管，这套方案更短、更贴近当前仓库分层，也更符合 OpenAI 对 `AGENTS.md` 的分层建议和 Anthropic 对 simple workflow / eval-first 的公开最佳实践
- 影响范围：`AGENTS.md`、`app/ai/AGENTS.md`、`.cursor/rules/agent_authoring.mdc`、`.cursor/commands/jjk-review.md`、`.cursor/commands/jjk-verify.md`、`workdocs/_templates/jjk_review_templates.md`、`workdocs/_templates/jjk_verify_templates.md`、`tests/unit/test_agent_governance_contract_docs.py`、`.github/workflows/agent-governance-gate.yml`、`docs/README.md`、`docs/开发文档/规范/多智能体开发规范.md`
- 失效条件：若未来仓库引入更高优先级且更靠近执行链的统一 agent authoring 协议，能稳定覆盖同样的规则装配与门禁语义，可将本条标记为 `SUPERSEDED`；在此之前保持当前分层
- 关联文档/代码：`workdocs/需求/2026-03-13_codex-agent-governance-and-refactor/requirements.md`、`workdocs/设计/2026-03-13_codex-agent-governance-and-refactor/design.md`、`workdocs/任务拆解/2026-03-13_codex-agent-governance-phase1/contracts/implementation_plan.md`、`docs/内部参考/决策记录.md`

### 2026-03-12 聊天 live 展示正式收口到 SSE `display_blocks`，前端退役 placeholder 编译器

- 状态：ACTIVE
- 决策主题：聊天 live 展示协议统一改为 SSE `display_blocks` 快照；前端不再根据 `final_answer + kb_images + result_events` 现场拼 UI。
- 背景与问题：旧链路里正文、知识库图片、结构化结果分散在多路字段，导致“首屏串位、刷新丢图、占位符泄漏”反复出现；前端临时 compiler 只能缓解，不能消灭双轨事实源。
- 最终决策：后端在 stream / resume 收口阶段编译 canonical ordered blocks，并通过 `display_blocks` 一次性发给前端；`AssistantMessage` 只做“有块渲块、无块渲纯文本”。
- 取舍理由：项目未上线，优先把展示协议收敛成单一 owner；相比继续保留占位符替换器或运行时猜结构，SSE canonical snapshot 更简单、更稳。
- 影响范围：`app/services/chat_service.py`、`app/ai/events.py`、`web/src/lib/backend.ts`、`web/src/hooks/useSSEStream.ts`、`web/src/components/chat/messages/ai.tsx`
- 回退/失效条件：若未来协议继续演进，也必须保持“单一 canonical blocks owner”不变；禁止恢复前端 placeholder 编译器。
- 关联文档/代码：`docs/API文档/接口文档.md`、`docs/开发文档/架构设计/AI模块设计.md`、`web/e2e/chat-ordered-content-blocks.spec.cjs`

### 2026-03-11 知识库占位符降级为中间语法，AI 回复最终展示收敛到 ordered content blocks

- 状态：ACTIVE
- 决策主题：`[IMG-N]` 继续保留在知识库生成链路里，但只作为上游锚点语法；最终展示与持久化统一收敛到 ordered content blocks。
- 背景与问题：过去既在前端替换占位符，又在仓储层落库前替换，还会在未引用时补图到正文末尾，导致协议分裂与历史回放不一致。
- 最终决策：新增 `app/core/message_display_blocks.py` 作为唯一编译入口；history 保存 `content_type="multimodal" + content=blocks[]`，legacy 消息只在接口层兼容编译。
- 取舍理由：保留锚点语法能继续利用现有知识库链路的稳定性，但展示 owner 必须从字符串替换升级为结构化 blocks，才能真正解决图文混排和刷新回放问题。
- 影响范围：`app/core/message_display_blocks.py`、`app/repositories/chat_repo.py`、`app/api/v1/endpoints/chat_api.py`、`tests/unit/test_message_display_blocks.py`
- 回退/失效条件：待上游能直接输出更显式的结构化锚点后，可继续缩窄 `[IMG-N]` 语法；在此之前禁止重新把 placeholder 当最终 UI 协议。
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-11-ordered-content-blocks-design.md`、`docs/开发文档/架构设计/防屎山记录手册.md`

### 2026-03-11 前端 lint 入口收敛为 `eslint .`，并直接接入 `@next/eslint-plugin-next`

- 状态：ACTIVE
- 决策主题：前端 lint 不再走 `next lint` 包装入口，统一改为 `eslint .`，并在 flat config 里直接接入 `@next/eslint-plugin-next` 官方规则
- 背景与问题：`next lint` 在当前 flat config 下持续提示 “The Next.js plugin was not detected in your ESLint configuration”；同时 `react-refresh` 对 provider/ui/headless 文件误报偏多，导致 lint 输出噪音高、可读性差
- 最终决策：`web/package.json` 中 `lint/lint:fix` 改为 `eslint .`；`web/eslint.config.js` 直接接入 `@next/eslint-plugin-next` 的 `recommended + core-web-vitals` 规则；`react-refresh/only-export-components` 只保留在适合的组件文件，对 `providers/ui/headless/barrel` 精准关闭
- 取舍理由：这是 Next/ESLint 官方更稳定的配置方向；相比继续依赖 `next lint` 包装层或放任规则误报，直接用 ESLint CLI + 精准 rule scope 更简单、更可维护
- 影响范围：`web/package.json`、`web/eslint.config.js`、前端 lint 工作流、后续 warning 基线
- 回退/失效条件：若未来升级到新的官方 lint 集成方案并明确替代 `eslint .`，可由新的入口替代；在此之前保持当前配置
- 关联文档/代码：`web/package.json`、`web/eslint.config.js`、`workdocs/归档/报告/重构报告/refactor_report_chat-shell-style-unification.md`

### 2026-03-12 日志已足够定责时先报告根因，禁止默认进入修复闭环

- 状态：ACTIVE
- 决策主题：调试/排障场景中，只要日志、报错栈、运行态证据或最小复现已足以锁定根因，必须先同步结论和证据，再由用户决定是否继续改代码
- 背景与问题：排障流程容易被 system debugging、TDD、文档回填和“顺手收口”惯性带着往下走；如果代理在根因已经清楚时仍默认进入修复/优化闭环，用户会失去对节奏和范围的控制
- 最终决策：在 `AGENTS.md` 增加治理口径，在 `.cursor/rules/core.mdc` 增加执行细则；统一要求先输出“根因结论 + 证据位置 + 是否继续改动”，未经用户明确同意，不得默认进入修复、优化、重构、补测或文档回填
- 取舍理由：这类问题不是技术难题，而是协作边界问题；相比继续依赖代理自觉，直接把沟通节点写成硬规则更简单，也更符合“结论先行、说人话、用户掌握决策权”的项目治理目标
- 影响范围：所有调试、日志排查、线上/本地异常定位类任务；尤其影响 `jjk-debug`、systematic debugging 相关执行节奏
- 回退/失效条件：若未来仓库引入更高优先级的统一协作协议并覆盖同一约束，可标记为 `SUPERSEDED`；在此之前保持该规则有效
- 关联文档/代码：`AGENTS.md`、`.cursor/rules/core.mdc`

### 2026-03-12 聊天运行态状态条固定挂在消息流尾部，禁止重新挂回 footer

- 状态：ACTIVE
- 决策主题：聊天运行态状态条 `runtime-status` 固定展示在消息流尾部，并与消息内容列宽对齐；footer 只承载输入区，不再承载运行态状态提示
- 背景与问题：2026-03-11 的聊天壳层统一重构把 `runtime-status` 重新挂进了 footer，导致状态条落在输入框上方、宽度走 `chat-stream-shell` 宽轨，和排版设计里“状态行与消息内容列对齐”的口径冲突
- 最终决策：`Thread` 继续保留 `runtime-status` 测试节点，但挂载位置改回消息流尾部；`chat-runtime-status` 保持 `chat-*` 主题 owner，同时收口为内容列内的 inline bubble，并补齐 `role="status"` / `aria-live="polite"`
- 取舍理由：短生命周期状态应贴近相关内容，而不是塞进输入区；相比继续在 footer 做视觉补丁，把 owner 收回消息流更简单，也更符合内容邻近性和可访问性最佳实践
- 影响范围：`docs/开发文档/架构设计/前端架构.md`、`web/src/components/chat/index.tsx`、`web/src/app/globals.css`、`tests/unit/test_chat_runtime_status_layout_guard.py`
- 回退/失效条件：若未来运行态状态被彻底并入 `AssistantMessage` 内部状态卡，且消息流仍是唯一展示 owner，可由新的消息级承载方案替代；在此之前禁止恢复 footer 挂载
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-08-chat-typography-cjk-design.md`、`docs/开发文档/架构设计/前端架构.md`、`web/src/components/chat/index.tsx`、`web/src/app/globals.css`

### 2026-03-12 `DB_ECHO` 默认改为显式开启，memory intent runtime 空闲轮询与观测采样统一降噪

- 状态：ACTIVE
- 决策主题：数据库原始 SQL 回显不再随 dev 环境默认开启；`memory_intent_runtime` 空闲时采用退避轮询，`memory_intent_worker_service` 的背压观测按 worker 本地短窗口复用快照
- 背景与问题：`logs/assistant.log` 被 `t_user_memory_intent_job` 的空轮询 SQL 持续刷大；根因是 `DB_ECHO=true` 放大了后台 worker 的空转查询，而 worker 空闲时固定每 `0.5s` 执行一轮整表观测
- 最终决策：`DB_ECHO` 默认值统一收口为 `false`，仅在显式排障窗口临时开启；`memory_intent_runtime` 的 idle/circuit_open 轮询节奏改为 `0.5s -> 1s -> 2s -> 5s` 退避；观测采样缓存窗口收口到 worker 本地 30 秒
- 取舍理由：项目未上线，优先消除日志噪音和无效热轮询，而不是引入更重的消息队列/事件驱动改造；相比继续依赖 SQLAlchemy `echo` 或保持每轮整表统计，这个方案更简单、边界更清晰
- 影响范围：`app/core/config.py`、`app/db/session.py`、`app/core/memory_intent_runtime.py`、`app/services/memory_intent_worker_service.py`、`.env.example`、记忆运行时与配置文档
- 回退/失效条件：若未来需要长期保留 SQL 级审计，应通过独立日志器/采样链路承接，而不是恢复 `DB_ECHO` 默认开启；若 memory intent runtime 被新的事件驱动执行器替代，可删除当前退避和缓存实现
- 关联文档/代码：`docs/开发文档/快速入门/配置说明.md`、`docs/开发文档/架构设计/用户个性化永久记忆.md`、`app/core/config.py`、`app/core/memory_intent_runtime.py`、`app/services/memory_intent_worker_service.py`

### 2026-03-12 聊天图表继续固定为客户端 `react-vega + svg`，Next 构建层单点隔离 `canvas` 可选依赖

- 状态：ACTIVE
- 决策主题：聊天页问数图表继续走客户端 `react-vega + renderer="svg"`；`vega-canvas` 触发的 Node 侧 `canvas` 可选依赖 warning 统一在 `web/next.config.mjs` 收口，不在业务组件里继续加条件分支或要求安装 `node-canvas`
- 背景与问题：`/chat` 开发编译会沿 `react-vega -> vega-embed -> vega -> vega-canvas.node.js` 扫到 `import('canvas')`，Next 因本仓未安装 `canvas` 输出 warning；但当前图表真实运行路径是客户端 SVG，不需要服务端 `node-canvas`
- 最终决策：保留 `web/src/components/chat/messages/sql-result-chart.tsx` 的动态客户端加载与 `renderer="svg"`；在 `web/next.config.mjs` 中将 `canvas` 作为可选 Node 依赖做单点隔离，避免无关 warning 污染前端编译输出
- 取舍理由：项目未上线，优先把边界收在配置层，而不是为一个 Node 侧可选分支引入额外原生依赖；相比安装 `canvas` 或在业务层堆 fallback，配置层收口更简单、更稳定
- 影响范围：`web/next.config.mjs`、聊天图表编译链路、前端 dev/build warning 基线、后续 `react-vega` 升级时的依赖判断
- 回退/失效条件：若未来明确需要服务端 PNG/Canvas 渲染，或图表导出能力改为依赖 `node-canvas`，则重新评估并显式引入服务端依赖；在此之前保持客户端 SVG 路径
- 关联文档/代码：`docs/开发文档/架构设计/前端架构.md`、`web/next.config.mjs`、`web/src/components/chat/messages/sql-result-chart.tsx`

### 2026-03-12 聊天复合提问耗时治理首轮采用局部重构版 B，而不是直接上 `Send` 全并行

- 状态：ACTIVE
- 决策主题：针对“显式复合提问已识别但后续仍串行、且 `todo.query` 误入澄清”的问题，首轮治理采用局部重构版 B：先修 preview 提前回流、frozen `todo.query` 直通、coverage answered 口径与 timing 观测；暂不上 LangGraph `Send` 全并行 fan-out/fan-in
- 背景与问题：当前慢点主要集中在图内串行链路与错误澄清，而不是 HTTP/SSE 建连；若直接上全量并行重写，会同时放大 state ownership、resume、coverage、回放风险
- 最终决策：保留当前主图拓扑与 `final_answer` 单一收口；`multi_agent_graph.py` 继续作为本轮 composite delivery policy owner；`todo_graph` 对 frozen `todo.query` 只执行不重判；请求级与 goal 级 timing 先走运行态 meta，不引入 DB migration
- 取舍理由：项目未上线，优先选择“低风险高收益”的结构收敛；先把 23 秒无正文和 6 秒误澄清打掉，比一开始重写成全并行图更稳、更容易验证
- 影响范围：`workdocs/归档/正文/需求/chat-composite-latency-local-refactor_requirements.md`、`workdocs/归档/正文/设计/2026-03-12-chat-composite-latency-local-refactor-design.md`、`workdocs/归档/正文/实施计划/chat-composite-latency-local-refactor_implementation_plan.md`、`workdocs/归档/正文/实施计划/chat-composite-latency-local-refactor_uat_cases.md`
- 回退/失效条件：若局部重构版 B 完成后仍无法显著改善 `first_visible_at_ms` 或仍存在串行瓶颈，再升级到 LangGraph `Send` 并行方案；在此之前不提前进入全量并行重构
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-10-composite-chat-latency-design.md`、`workdocs/归档/正文/设计/2026-03-12-chat-composite-latency-local-refactor-design.md`

### 2026-03-12 瘦身判断收敛为“职责收口优先 + whole-change-set 统计”

- 状态：ACTIVE
- 决策主题：瘦身不再以“当前文件删了几行”或全局 `added<=deleted` 口号判断，而是优先看旧职责是否退役、唯一 owner 是否收口，并按整个变更集统计增长
- 背景与问题：原有 `obsolete_paths/retained_paths/single_entry_owner/line_budget` 规则在 `AGENTS.md`、`core.mdc`、`lean-guard.md`、bugfix 规则中重复出现，但产物里几乎不稳定落 `line_budget`；AI 也容易把“当前文件净删行”误判成“已经瘦身”，忽略新增文件、helper 文件和外移模块
- 最终决策：Layer1 只保留“职责替换先收口、默认先收口再扩写”原则；技术细则统一落到 Layer2/Lean Guard；`line_budget` 明确按 whole-change-set 统计，新增文件、外移模块、helper 文件同样计入 added；只有同步删除旧路径/旧职责，才算真正收口
- 取舍理由：项目未上线，真正想要的是结构收敛，而不是表面删行；相比继续用抽象口号或单文件视角，whole-change-set 统计更接近真实复杂度变化，也更能约束 AI 常见的“拆新文件但不算增长”与“多造 helper/fallback”倾向
- 影响范围：`AGENTS.md`、`.cursor/rules/core.mdc`、`.cursor/rules/bugfix-minimal-change.mdc`、`docs/开发文档/规范/lean-guard.md`、设计/重构模板，以及后续所有 bugfix/refactor/替代实现任务
- 失效条件：若未来由脚本自动生成完整 replacement contract 与 whole-change-set 报告，并成为更高优先级真理源，可将本决策标记为 `SUPERSEDED`
- 关联文档/代码：`AGENTS.md`、`.cursor/rules/core.mdc`、`.cursor/rules/bugfix-minimal-change.mdc`、`docs/开发文档/规范/lean-guard.md`、`workdocs/_templates/jjk_design_templates.md`、`workdocs/_templates/jjk_refactor_templates.md`

### 2026-03-12 文档信息架构细化为“最终/过程/运行态 × 人类/机器”双维模型

- 状态：ACTIVE
- 决策主题：在原有 `docs / workdocs / .artifacts` 三层分治基础上，进一步明确每层的消费方式：最终文档区分“给人读”和“给机器读”，过程文档区分“给人读”和“给机器读”，运行态继续只给机器消费
- 背景与问题：当前仓库虽然已有“稳定文档 / 过程文档 / 运行态产物”方向，但 `docs/API文档` 与机读契约、`workdocs/任务拆解` 根目录与 `contracts/reports`、`docs/plans` 与 `docs/内部参考/迭代需求` 的角色仍不够直观；维护者容易知道三层，却不容易快速判断“这份材料是给人看还是给脚本读”
- 最终决策：`docs/` 继续承载给人读的最终文档，其中 `docs/产品文档`、`docs/开发文档`、`docs/API文档`、`docs/工程规范`、`docs/内部参考` 为稳定说明；`contracts/` 承载给机器读的最终契约（如 OpenAPI / AsyncAPI / JSON Schema）；`workdocs/` 承载过程文档，其中 `需求/` 与 `设计/` 只放给人读正文，功能级实施/审查/测试/验收/调试合同统一收进 `workdocs/任务拆解/<YYYY-MM-DD_主题>/contracts|reports`；`.artifacts/` 继续只承载运行态机器产物
- 取舍理由：相比额外再开 `方案/评审/验收` 目录，按 topic bundle 收口到 `任务拆解/contracts|reports` 更直观，也更符合“同一功能的过程材料放一起、最终文档不再被过程材料污染”的目标；人看根目录，机器读 `contracts/reports`，上下游更容易接住
- 影响范围：`docs/README.md`、`docs/SUMMARY.md`、`docs/开发文档/流程与工具/文档信息架构.md`、`workdocs/README.md`、`workdocs/任务拆解/README.md`、`workdocs/需求/README.md`、`workdocs/设计/README.md`、`.cursor/commands/jjk-{plan,vkplan,review,test,verify,wtimp,imp-ws,debug,commit,deleteworktree}.md`
- 失效条件：若未来把过程文档按 `topic bundle` 再次整体重构为 `workdocs/<topic>/{human,machine}` 统一结构，可由新的目录模型替代当前双维说明
- 关联文档/代码：`docs/README.md`、`docs/SUMMARY.md`、`docs/开发文档/流程与工具/文档信息架构.md`、`workdocs/README.md`

### 2026-03-11 聊天页壳层样式 single entry owner 固定为 `chat-*` 主题 class

- 状态：ACTIVE
- 决策主题：聊天页面壳层、状态条、输入区、消息工具条的皮肤 owner 统一收敛到 `web/src/app/globals.css` 的 `chat-*` 主题 class；组件不再保留第二套大段 inline Tailwind 壳层样式
- 背景与问题：`ChatHeader` 已切到新主题，但 `Thread`、`ChatInput`、消息工具条仍保留旧 inline 样式；结果是“新 class 已定义、组件却没接线”，技能加载状态条与输入区视觉割裂
- 最终决策：`Thread` 只负责页面壳层、滚动区与 `runtime-status` 接线，`ChatInput` 只负责输入区接线，消息组件只负责消息级接线；无消费者的聊天壳层 class 直接删除，不保留“以后也许会用”的死代码
- 取舍理由：项目未上线，优先消灭双轨样式 owner；相比继续在组件里堆 inline class 或保留未接线 theme class，单入口皮肤更简洁、更易验证，也更符合 CSS 变量/组件职责分离的最佳实践
- 影响范围：`web/src/app/globals.css`、`web/src/components/chat/index.tsx`、`web/src/components/chat/ChatInput.tsx`、`web/src/components/chat/messages/{ai,human,shared}.tsx`、聊天 UI/架构文档、相关 E2E testid 契约
- 回退/失效条件：若未来聊天页彻底迁移到另一套 design system 或 CSS-in-JS 方案，可由新的样式入口替代；在此之前保持 `chat-*` 为唯一皮肤 owner，不恢复 inline 双轨
- 关联文档/代码：`docs/开发文档/架构设计/前端架构.md`、`docs/开发文档/架构设计/前端UI设计方案.md`、`workdocs/归档/报告/重构报告/refactor_report_chat-shell-style-unification.md`、`web/src/app/globals.css`、`web/src/components/chat/index.tsx`、`web/src/components/chat/ChatInput.tsx`


### 2026-03-11 JJK 工程流分层重构为 requirements -> design -> plan(UAT) -> imp -> verify
- 状态：ACTIVE
- 决策主题：将 `jjk-*` 主工程流收敛为五阶段：`jjk-clarify` 只产出需求，新增 `jjk-design` 承接技术方案与 shrink contract，`jjk-plan` 只产出实施计划与完整 UAT 用例，`jjk-imp` 严格消费计划执行实现，`jjk-verify` 只消费既有合同判定结果
- 背景与问题：现有 `jjk-clarify` 直接产出 `design.md`、`jjk-plan` 仍同时产出 `requirements`、`jjk-verify` 仍保留临场 UAT 判定，导致需求/方案/计划/验收边界混杂，用户难以稳定判断每个阶段的唯一职责
- 最终决策：需求真理源收敛为 `requirements.md`，技术真理源收敛为 `design.md`，实施真理源收敛为 `implementation_plan.md` 与 `uat_cases.md`；正式产品文档与正式设计文档仅在 `--doc` 显式开启时发布；命中接口变化时 API 文档继续自动同步，不受 `--doc` 影响；命中 DB 结构变化时，开发态默认执行 `bash scripts/db/run_dev_migration.sh`，发布态通过 `bash scripts/db/run_release_migration.sh --message "<message>"` 与 `bash scripts/db/run_release_migration.sh --upgrade-only` 进入 Alembic 版本化迁移
- 取舍理由：项目未上线，优先把认知主链分层做对，而不是继续靠一个命令兼做需求、方案和验收；相比再堆更多工作流命令，新增 `jjk-design` 并缩减 `clarify/plan/verify` 职责更简洁、更可验证，也更符合需求-设计-验证分层的最佳实践；同时复用仓内统一的开发态 / 发布态 DB migration 入口，而不是继续暴露底层脚本给上层工作流
- 影响范围：`.cursor/commands/jjk-{clarify,design,plan,imp,verify,api-doc-sync,arch-gate}.md`、`.agents/skills/jjk-{clarify,design,plan,imp,verify,api-doc-sync,arch-gate}/SKILL.md`、`.claude/commands/jjk-{clarify,design,plan,imp,verify,api-doc-sync,arch-gate}.md`、相关工作流与速查文档
- 回退/失效条件：若未来统一工程流编排器把 requirements/design/plan/UAT 收敛到更高层单一协议，可将本记录标记为 `SUPERSEDED`；在此之前保持五阶段分层与 `--doc` 发布语义
- 关联文档/代码：`.cursor/commands/jjk-clarify.md`、`.cursor/commands/jjk-design.md`、`.cursor/commands/jjk-plan.md`、`.cursor/commands/jjk-imp.md`、`.cursor/commands/jjk-verify.md`、`.cursor/commands/jjk-api-doc-sync.md`、`.cursor/commands/jjk-arch-gate.md`

### 2026-03-11 task_split 机器契约与过程报告收口到 `workdocs/任务拆解`

- 状态：ACTIVE
- 决策主题：task_split 的 canonical 根目录从旧任务拆解入口切到 `workdocs/任务拆解/`；`contracts/` 承担过程契约，`reports/` 承担过程报告，真实运行态只认 `.artifacts/states/task_splits/`
- 背景与问题：Phase 1 只迁出了 `.state/.jsonl/.lock`，但 `_active_task.json`、`vk_cards.json`、`preflight_status.json`、`consumption_report.json` 等机器 JSON 仍留在 docs，导致 docs / workdocs / .artifacts 边界继续打架，脚本也各自硬编码旧路径
- 最终决策：新增 `scripts/task_split_paths.py` 作为唯一路径 owner；`wt-flow`、`coder4_*`、`workflow_contract_*` 全部改读 canonical path；task_split 目录整体迁到 `workdocs/任务拆解/`；旧任务拆解入口只保留说明页，不再承载 task_split 文件
- 取舍理由：项目未上线，优先一次性消灭双真源和散落 path resolver；相比继续靠 symlink、thin index 或双写保兼容，直接切 canonical path 更简洁、更可验证
- 影响范围：`scripts/task_split_paths.py`、`scripts/coder4/*.py|*.sh`、`scripts/workflow_contract_*`、`scripts/check_workflow_contract.py`、`scripts/docs_guard.py`、`.cursor/rules/doc_sync.mdc`、`workdocs/任务拆解/**`、`docs/README.md`、`docs/SUMMARY.md`、`workdocs/README.md`、`memory-bank.md`
- 回退/失效条件：若未来统一改到另一套工作流存储或正式文档站点，可由新的目录策略替代；在此之前保持 `workdocs/contracts|reports + .artifacts runtime` 这套边界，不恢复 docs 下 task_split 机器 JSON
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-11-docs-governance-phase2-task-split-layering-design.md`、`workdocs/归档/正文/需求/docs-governance-phase2-task-split-layering_requirements.md`、`workdocs/归档/正文/实施计划/docs-governance-phase2-task-split-layering_implementation_plan.md`、`scripts/task_split_paths.py`

### 2026-03-11 根 AGENTS 收敛为总则+路由，执行长流程下沉到 `PLANS.md`
- 状态：ACTIVE
- 决策主题：将仓库根 `AGENTS.md` 收敛为高信号常驻入口，把只在实现/测试/验收阶段才需要的长流程规则统一下沉到 `PLANS.md`
- 背景与问题：根 `AGENTS.md` 同时承担治理总则与执行型流程，默认加载面过大；规则内容虽然正确，但对日常对话和轻量任务来说噪音过高
- 最终决策：根 `AGENTS.md` 仅保留全局门禁、路由和真理源入口；`patch` 门槛、上下文校验、文件编辑工具契约、测试解释器、测试语义分层、运行态校验统一迁入 `PLANS.md`
- 取舍理由：这次不删除规则事实内容，只调整装配方式；让高频常驻内容更短，同时保留长流程规则的完整可追溯性，更符合 OpenAI 对仓库指令“短、稳、按需加载”的公开最佳实践
- 影响范围：`AGENTS.md`、`PLANS.md`、`docs/README.md` 中的 AI 协作者规则分层说明，以及后续所有仓内任务的规则读取路径
- 回退/失效条件：若后续 Codex / 仓内执行链改为新的统一计划载体，并由更高优先级真理源替代 `PLANS.md`，可将本决策标记为 `SUPERSEDED`；在此之前保持启用
- 关联文档/代码：`AGENTS.md`、`PLANS.md`、`docs/README.md`、`.cursor/rules/core.mdc`、`.cursor/rules/doc_sync.mdc`

### 2026-03-11 瘦身规则前置为 shrink contract，旧路径残留升级为硬阻断

- 状态：ACTIVE
- 决策主题：将“删旧代码”从交付后提醒前置为编码前 shrink contract，并把新实现覆盖旧职责但旧路径无理由残留定义为硬失败
- 背景与问题：现有 Layer1 / Lean Guard 已明确反对继续长胖，但执行时仍容易先加新逻辑、后解释旧路径为什么没删；规则知道要瘦身，却还不够像实现前合同
- 最终决策：在 `AGENTS.md`、`.cursor/rules/core.mdc`、`docs/开发文档/规范/lean-guard.md` 中统一引入 `obsolete_paths`、`retained_paths`、`single_entry_owner`、`line_budget`；并把 `jjk-arch-gate`、`jjk-refactor` 命令入口同步到同一 contract
- 取舍理由：相比继续堆长规则或事后要求“顺手删掉旧代码”，前置 shrink contract 更短、更硬、更可验证，也更符合 OpenAI 对仓库指令“高信号、少冗余”的最佳实践
- 影响范围：所有 `bugfix/refactor` 任务、Lean Guard 热点文件治理、`/jjk-arch-gate` 与 `/jjk-refactor` 输出模板、后续瘦身证据口径
- 回退/失效条件：若后续执行链改为脚本自动生成 shrink contract，或存在更高优先级治理文件统一承接同一 contract，可将本记录标记为 `SUPERSEDED`；在此之前保持启用
- 关联文档/代码：`AGENTS.md`、`.cursor/rules/core.mdc`、`.cursor/rules/bugfix-minimal-change.mdc`、`docs/开发文档/规范/lean-guard.md`、`.cursor/commands/jjk-arch-gate.md`、`.cursor/commands/jjk-refactor.md`

### 2026-03-11 文档记忆启用且 Worker 就绪时，`memory.intent_async_enabled` 默认保持开启

- 状态：ACTIVE
- 决策主题：只要文档记忆 runtime worker 已就绪且 `ENABLE_DOC_MEMORY_ASYNC_DELETE=true`，配置默认值 `memory.intent_async_enabled` 必须保持开启，不再允许通过默认关闭把“只入队不消费”伪装成同步链路正常
- 背景与问题：此前为绕过 runtime 缺口，配置曾长期保持“默认关闭”；worker 与删除链路补齐后，若仍默认关闭，会让真实能力长期停留在文档/代码不一致状态，也会误导后续实现继续围绕 fallback 打补丁
- 最终决策：在配置说明、实现与测试口径中统一把 `memory.intent_async_enabled` 视为默认开启；回退方式统一为显式关闭该开关或停用 async delete，而不是再把默认值改回关闭
- 取舍理由：项目未上线，优先让真实主链默认可用，而不是继续保留“为了历史不稳定先默认关掉”的过渡语义；这比保留双口径更简单、更符合当前治理目标
- 影响范围：`docs/开发文档/快速入门/配置说明.md`、`app/core/memory_intent_runtime.py`、相关记忆链路测试与运行时说明
- 回退/失效条件：若未来 runtime worker 被整体移除，或 async intent 主链被新的执行架构替代，可由新的运行时真理源接管默认值语义；在此之前保持默认开启
- 关联文档/代码：`docs/开发文档/快速入门/配置说明.md`、`app/core/memory_intent_runtime.py`、相关记忆链路实现与测试

### 2026-03-10 文档治理收敛为 `docs/workdocs/.artifacts` 三层分治（Phase 1 保留 task_split 契约兼容路径）

- 状态：ACTIVE
- 决策主题：文档体系收敛为 `docs/`（长期真理源）+ `workdocs/`（进行中工作文档）+ `.artifacts/`（运行/产物快照）三层结构；旧需求入口与旧任务拆解入口在当时仅作为兼容入口
- 背景与问题：当时的过程设计目录、旧需求入口、旧任务拆解入口、各类报告与中间 JSON 混杂，真理源、工作稿与机器产物边界不清，`doc_sync` / `docs_guard` / 执行链都在同一层目录相互踩踏
- 最终决策：长期真理源集中到 `docs/`；过程性工作文档迁到 `workdocs/`；机器产物迁到 `.artifacts/`；旧需求入口与旧任务拆解入口在当时仅保留兼容职能；`docs_guard/check_doc_sync/doc_sync` 全部对齐该分层
- 取舍理由：项目未上线，优先从目录边界消除双重职责；但 `jjk-cardrun` / `wt-flow` / `coder4_*` 仍依赖旧 `task_split` 路径，先把真实运行态迁出并冻结兼容边界，比一次性硬迁机器契约更稳、更可验证
- 影响范围：`docs/README.md`、`docs/SUMMARY.md`、`workdocs/归档/正文/设计/2026-03-10-docs-governance-layering-design.md`、`workdocs/归档/正文/需求/文档分层治理与信息架构收敛_requirements.md`、`workdocs/归档/正文/实施计划/文档分层治理与信息架构收敛_implementation_plan.md`、`workdocs/**`、`.artifacts/**`、旧任务拆解入口 README、`scripts/docs_guard.py`、`scripts/check_doc_sync.sh`、`.cursor/rules/doc_sync.mdc`
- 回退/失效条件：若未来统一迁移到正式文档站点或独立工作流存储，可由新的目录策略替代；在此之前保持三层分治；`Phase 1` 期间保留旧 `task_split` 兼容路径，待 `Phase 2` 完成脚本切换后再彻底移除
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-10-docs-governance-layering-design.md`、`workdocs/归档/正文/需求/文档分层治理与信息架构收敛_requirements.md`、`workdocs/归档/正文/实施计划/文档分层治理与信息架构收敛_implementation_plan.md`

### 2026-03-11 JJK 命令执行统一采用单步单目标

- 状态：ACTIVE
- 决策主题：`/jjk-*` 命令执行 shell / Git / 测试 / 验证步骤时，统一采用“单步单目标”，禁止把基础观测、期望比对、解释器解析、测试执行、统计汇总拼成一条长链
- 背景与问题：超长 one-liner 一旦失败或输出被截断，很难判断是哪一步失效，执行者容易整串重跑，既浪费时间，也会制造“同一命令反复调用”的糟糕体验
- 最终决策：把执行节奏收敛到 `.cursor/rules/core.mdc`；高频 `/jjk-*` 命令文档与工作流手册只做轻量引用，统一要求失败只重跑当前步、长任务只轮询不重启
- 取舍理由：这是执行契约问题，不是某一条 `/jjk-verify` 的局部 bug；放到总规则层比逐命令各写一套更简洁、更稳定，也更符合仓内“未上线先修结构”的原则
- 影响范围：`.cursor/rules/core.mdc`、高频 `.cursor/commands/jjk-*.md`、`.agents/skills/jjk-*/SKILL.md` 镜像、工作流/速查文档
- 回退/失效条件：若未来命令执行统一收敛到可复用脚本编排器，并由工具层天然提供单步状态与轮询协议，可把文档约束降级为实现说明；在此之前保持当前规则
- 关联文档/代码：`.cursor/rules/core.mdc`、`.cursor/commands/jjk-verify.md`、`.cursor/commands/jjk-test.md`、`.cursor/commands/jjk-review.md`、`docs/开发文档/流程与工具/指令用法_实现方式_工程流全景手册.md`

### 2026-03-11 Data handoff 与历史回放脏块统一收口

- 状态：ACTIVE
- 决策主题：`data.query` 委派必须在编排层落成 canonical `frame.query_text`；assistant 历史回放只保留用户可见文本，不再把 raw `Responses` 内部块或“继续补齐”泄漏文本重新喂回模型
- 背景与问题：`assign_to_data_expert(frame=null, task_description=...)` 会被 router guard 阻断，并诱发内部“请确认是否继续补齐”提示外泄；旧线程若残留 `function_call` 或空壳 `text` block，继续聊天时会在 `langchain-openai` Responses payload 构造阶段触发 `KeyError: 'text'`
- 最终决策：data handoff 的唯一真理源为 `frame.query_text`，缺失时只允许把 `task_description` / 当前轮问句作为编译输入补成 canonical `frame`；router blocked / coverage blocked 不再通过 `system_context` 注入自然语言补齐提示；消息契约层继续扩展为剥离 `function_call/tool_use/tool_result` 与空壳 text block，并过滤已知内部补齐提示
- 取舍理由：问题根因在 contract 和历史回放结构，而不是单条文案；把 owner 收回编排层与消息契约层，比继续在 UI 或 postprocess 追加兼容过滤更简洁、更稳定
- 影响范围：`app/ai/workflow/multi_agent_graph.py`、`app/ai/message_utils.py`、`app/ai/protocol.py`、聊天/问数需求与测试文档
- 回退/失效条件：若 supervisor 未来完全不再输出 task_description 型 data handoff，且上游 `langchain-openai` 对 Responses block 回放做了稳定兼容，可评估删除对应兜底编译与清洗分支；在此之前保持启用
- 关联文档/代码：`docs/产品文档/聊天系统需求.md`、`docs/产品文档/问数助手需求.md`、`docs/开发文档/架构设计/AI模块设计.md`、`app/ai/workflow/multi_agent_graph.py`、`app/ai/message_utils.py`

### 2026-03-10 Assistant 空壳文本块在消息契约层清洗

- 状态：ACTIVE
- 决策主题：assistant 历史消息中 `type=text/output_text/refusal` 但无可读正文的空壳 block 必须在消息契约层被丢弃，不允许进入 LangGraph checkpoint
- 背景与问题：`langchain-openai` 的 Responses 流式边界场景可能生成仅含 `id/index` 的空壳 text block；若直接写入 `state.messages`，后续复用同一 `thread_id` 时会在 payload 构造阶段触发 `KeyError: 'text'`
- 最终决策：将 assistant content 清洗收口到 `app/ai/message_utils.py.validate_messages()`；所有读取 checkpoint 历史进入模型/恢复链路的边界都必须复用同一契约层，不再分散添加本地特判
- 取舍理由：坏块治理属于消息结构合法性问题，不属于业务编排职责；同时 `messages` 使用的 `add_messages` reducer 是 append-only，不能指望 preprocess 仅靠返回删减列表就移除旧坏块，所以需要在真正消费历史的读取边界再次复用同一清洗契约
- 影响范围：`app/ai/message_utils.py`、`app/ai/workflow/multi_agent_graph.py` 调用链、所有复用 LangGraph checkpoint 的多轮对话线程
- 回退/失效条件：若上游 `langchain-openai` 后续彻底修复该边界行为，且仓内确认不再产生空壳 assistant block，可评估删除此兼容清洗；在此之前保持启用
- 关联文档/代码：`docs/开发文档/架构设计/AI模块设计.md`、`app/ai/message_utils.py`、`venv/lib/python3.11/site-packages/langchain_openai/chat_models/base.py`

### 2026-03-10 CardRun 分支感知基线收口到 task state

- 状态：ACTIVE
- 决策主题：`/jjk-cardrun -> wt-flow` 在非 `main/master` 分支上运行时，卡片 worktree 的集成目标必须首轮继承当前父分支，并写入 `task-runner-state.json.integration_branch`
- 背景与问题：当前 `wt-flow create/next` 默认把 `base_branch` 固定为 `master`，导致 `cardrun` 即使在 feature 分支上启动，后续卡片仍会基于 `master` 创建并最终误收口到 `master`
- 最终决策：首轮创建卡片时优先复用任务态 `integration_branch`，缺失时继承当前非 `main/master` 父分支，再回落到仓库主线；单卡 session 继续保存 `base_branch`，`merge` 只读该值，不由 `wtimp` 重算
- 取舍理由：集成目标属于任务运行态，而不是 `wtimp` 的局部上下文；把 owner 放回 `wt-flow/task state` 比在执行层猜当前分支更稳定，也避免恢复执行时目标漂移
- 影响范围：`scripts/coder4/wt-flow.sh`、`tests/unit/test_coder4_wt_flow_verified_state.py`、`/jjk-cardrun` 与 `/jjk-wtimp` 命令文档、开发工作流文档
- 回退/失效条件：若未来明确规定 `cardrun` 只能在 `main/master` 主线运行，且禁止 feature 分支收口，则可删除 `integration_branch` 逻辑并回退为固定主线；在此之前保持 branch-aware 语义
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-10-cardrun-branch-aware-base-design.md`、`workdocs/归档/正文/设计/2026-03-10-cardrun-branch-aware-base.md`

### 2026-03-09 记忆异步队列由 FastAPI lifespan 常驻 worker 消费

- 状态：ACTIVE
- 决策主题：`memory.intent_async_enabled` 开启时，记忆意图队列必须由 FastAPI `lifespan` 启动的常驻 worker 负责消费，禁止只入队不接消费者
- 背景与问题：聊天侧已切到“主链路只入队”，但运行时没有消费者和 `process_job` 接线，导致删除/写入承诺停留在口头，后台 `t_user_memory_document` 状态长期不变
- 最终决策：新增 `app/core/memory_intent_runtime.py` 作为运行时入口；`app/main.py` 在 `lifespan` 启停 worker；`flush_canonical_memory()` 增加 `manage_transaction`，让记忆落库与 job 状态机共用同一事务
- 取舍理由：FastAPI 官方推荐长期生命周期任务挂在 `lifespan`，而不是把需要状态机/重试的工作塞进 request background task；当前项目已具备 PostgreSQL 队列与 `SKIP LOCKED` 租约，补齐消费者比改文案或再堆 fallback 更直接、更简洁
- 影响范围：`app/main.py`、`app/core/memory_intent_runtime.py`、`app/services/document_memory_service.py`、所有 `memory.intent_async_enabled` 记忆写入/删除链路
- 回退/失效条件：若未来拆为独立 worker 进程或外部任务系统，`lifespan` 只保留健康探测与启动门禁；在此之前不得回退为“只入队无消费者”
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-03-user-personalized-memory-llm-async-design.md`、`workdocs/归档/正文/实施计划/用户个性化永久记忆与管理能力_implementation_plan.md`、`workdocs/归档/报告/调试报告/debug_report_memory_intent_runtime.md`

### 2026-03-09 待办完成态收敛为 `status` 单字段

- 状态：ACTIVE
- 决策主题：待办完成态统一由 `t_todo.status` 表达，不再保留旧完成布尔镜像
- 背景与问题：模型、仓储、前端展示已按 `status='done'` 工作，但初始化 SQL、增量脚本和前端类型仍残留旧布尔语义，导致 schema 脚本与运行时口径漂移
- 最终决策：`Todo.status` 为唯一状态 owner；完成时间使用 `actual_completion_time`；前端按 `status === 'done'` 计算展示；SQL 脚本统一改为围绕 `status/progress/actual_completion_time` 收口
- 取舍理由：项目未上线，优先消除双真源与误导性字段；直接删除遗留布尔语义比继续保留兼容层更简单、更可验证
- 影响范围：`app/models/todo.py`、`web/src/types/todo.ts`、`install/sql/init_postgres.sql`、`install/scripts/init_postgres.sql/*`、`docs/开发文档/架构设计/数据库设计.md`
- 回退/失效条件：若未来需要派生完成标记，只能作为只读计算字段存在，且不得承担持久化真理源或写入口
- 关联文档/代码：`app/repositories/todo_repository.py`、`docs/开发文档/架构设计/数据库设计.md`、`install/sql/init_postgres.sql`

### 2026-03-09 Lifespan 资源治理收口为 `app.state.runtime`

- 状态：ACTIVE
- 决策主题：FastAPI 应用级共享资源统一由 `lifespan + AppRuntime` 管理，`lifespan` 只做编排，`app.state.runtime` 成为唯一 owner
- 背景与问题：当前项目虽然已经使用 `lifespan`，但 DB engine、checkpointer、tracer、asset client、图缓存和导入期副作用仍散落在 `app/main.py`、`app/db/session.py`、`app/services/**` 与 `app/ai/**` 中；owner 分裂后，依赖方向、状态归属和 teardown 责任都不稳定
- 最终决策：采用 `AppRuntime` 收口应用级共享资源；`lifespan` 仅负责 `build_runtime() -> yield -> runtime.aclose()`；应用级共享对象优先经由 runtime 管理的 registry / getter 访问（如 graph cache、asset service），请求侧按需通过 `request.app.state.runtime` 读取；用户态/请求态缓存不进入 runtime
- 取舍理由：项目未上线，优先把结构收敛到单一 owner，而不是继续在 `main.py` 堆初始化或在 service 中维持模块级 singleton；相比引入完整 DI 容器，`app.state.runtime` 更轻、更贴近 FastAPI/Starlette 原生实践
- 影响范围：`workdocs/归档/正文/设计/2026-03-09-lifespan-runtime-consolidation-design.md`、`workdocs/归档/正文/设计/2026-03-09-lifespan-runtime-consolidation-phase1-implementation.md`、后续 `app/main.py`、`app/core/runtime.py`、`app/db/session.py`、`app/services/asset_service.py`、`app/ai/utils/observability.py`、`app/ai/workflow/runtime_graph_provider.py` 等应用级资源 owner 收口工作
- 回退/失效条件：若未来明确引入统一 DI 容器并以其替代 `app.state.runtime` 作为唯一应用级资源 owner，可将该决策升级或替换；在此之前，不得重新回退到模块全局 singleton 分散持有资源
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-09-lifespan-runtime-consolidation-design.md`、`workdocs/归档/正文/设计/2026-03-09-lifespan-runtime-consolidation-phase1-implementation.md`、`app/main.py`

### 2026-03-09 Git 交付收口分层为命令编排层 + 共享 delivery engine

- 状态：ACTIVE
- 决策主题：把 `jjk-commit` 从“交付门禁 + 半套 merge 口径”收敛为交付编排层，并将真实 Git 生命周期统一下沉到共享 delivery engine
- 背景与问题：当前 `jjk-commit` 文案仍以 `--ff-only` + 人工冲突处理为主，而 `wt-flow.sh` 已实现 `rebase + --no-ff merge + abort`；命令层和脚本层形成两套 merge 真理源，用户无法稳定判断应该信哪一套
- 最终决策：新增共享 `Git Delivery Engine` 作为 `rebase / merge / continue / abort / status / prepare-base` 的唯一执行层；`jjk-commit` 仅保留交付门禁、验证证据、提交摘要与错误码翻译；`wt-flow.sh` 复用 engine，只保留 card/worktree 状态语义
- 取舍理由：项目未上线，优先彻底收敛结构性分裂，而不是继续靠文案提醒或兼容补丁维持两套行为；这样既能提升可恢复性，也能让测试和文档只围绕一份真理源展开
- 影响范围：`workdocs/归档/正文/设计/2026-03-09-jjk-commit-delivery-engine-{design,implementation}.md`、`.cursor/commands/jjk-commit.md`、`.agents/skills/jjk-commit/SKILL.md`、`scripts/coder4/wt-flow.sh`、`scripts/coder4/git-delivery-engine.sh`、`docs/开发文档/流程与工具/*`、`docs/开发文档/流程与工具/*`
- 回退/失效条件：若未来由统一工程流编排器完全接管本地 Git 生命周期，可将共享 engine 再次内聚进新的单一入口；在此之前，不得回退到 `jjk-commit` 与 `wt-flow` 各写一套 merge 逻辑
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-09-jjk-commit-delivery-engine-design.md`、`workdocs/归档/正文/设计/2026-03-09-jjk-commit-delivery-engine-implementation.md`、`.cursor/commands/jjk-commit.md`、`scripts/coder4/wt-flow.sh`

### 2026-03-09 共享开发库 Alembic 漂移收口规则

- 状态：ACTIVE
- 决策主题：共享开发库 revision 漂移时，必须补齐缺失历史迁移并新增 merge revision 收口，禁止直接篡改 `alembic_version`
- 背景与问题：当前开发库记录在 `20260309_0023`，但本分支最初只携带另一条 `20260309_0022` 迁移，导致 `alembic current` 直接失败；若继续手工改版本表，会让数据库历史与代码历史永久脱钩
- 最终决策：把缺失的 `20260308_0022`、`20260309_0023` 作为历史链补回当前分支，并用 `20260309_0024` merge revision 把双 head 合并为单 head；运行库临时补表只能用于保活，不得替代正式迁移收口
- 取舍理由：让“代码认识数据库历史”比让“数据库伪装成当前分支历史”更稳，也更符合未上线阶段优先做结构正确性的原则
- 影响范围：`alembic/versions/*`、共享开发库升级流程、后续 worktree 之间的迁移兼容策略
- 回退/失效条件：若未来所有 worktree 改为独立数据库实例，跨分支 revision 漂移风险显著降低后，可把该规则降级为推荐项；在此之前保持强约束
- 关联文档/代码：`alembic/versions/20260308_0022_add_skill_tool_contract.py`、`alembic/versions/20260309_0023_seed_data_handoff_tool_contract.py`、`alembic/versions/20260309_0024_merge_runtime_bucket_and_skill_tool_contract_heads.py`

### 2026-03-09 管理后台总览旧快照表正式退役

- 状态：ACTIVE
- 决策主题：删除 `t_ops_metric_snapshot_minute`，总览运行态不再保留展示快照表
- 背景与问题：旧快照表仍被 `AdminOverviewQueryService` 当作 fallback 与持久化使用，形成分钟桶与展示快照双真源；继续保留只会掩盖聚合链路问题并扩大语义漂移
- 最终决策：总览读取与降级都只围绕 `t_runtime_metric_bucket_minute` 表达 `ok / no_data / stale / degraded`，删除 `OpsSnapshotService`、旧快照模型、相关测试与 Alembic 表结构
- 取舍理由：项目未上线，优先把状态 owner 收敛到单表真理源；相比“保留兼容缓存”，彻底删除双写链路更简单、风险更可验证
- 影响范围：`app/services/admin_overview_query_service.py`、`app/models/runtime_metric_bucket.py`、`alembic/versions/20260309_0025_drop_ops_metric_snapshot_minute.py`、总览相关测试与数据库设计文档
- 回退/失效条件：若未来确有明确性能瓶颈，需要新增派生缓存时，必须作为独立只写缓存重新设计，且不得再次承担总览事实源或降级真相
- 关联文档/代码：`docs/开发文档/架构设计/数据库设计.md`、`workdocs/归档/正文/设计/2026-03-09-admin-overview-metrics-v2-design.md`

### 2026-03-09 管理后台总览真理源切换完成

- 状态：ACTIVE
- 决策主题：总览 V2 正式退役旧 collector、旧聚合服务与进程内双写缓存
- 背景与问题：`AdminOverviewQueryService` 已经接管分钟桶读模型，但仓内仍保留 `admin_overview_service.py`、`overview_runtime_collector.py` 和 `runtime_request_metrics_store` 双写链路，导致状态 owner 与依赖方向仍有双源
- 最终决策：总览读取只保留 `AdminOverviewQueryService`；请求埋点只写分钟桶 writer；删除旧 `admin_overview_service.py`、旧 `overview_runtime_collector.py` 及其失效测试，服务层导出同步切换到新查询服务
- 取舍理由：项目未上线，优先让结构彻底收口而不是维持过渡兼容；删除双源后，`summary / trends / stream` 与埋点写入口的边界更稳定
- 影响范围：`app/services/admin_overview_query_service.py`、`app/services/runtime_request_metrics.py`、`app/services/__init__.py`、旧总览服务/collector 文件及相关测试
- 回退/失效条件：若未来确实需要单独的进程内观测缓存，只能作为独立调试工具引入，不得再次承担总览事实源或主查询链路职责
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-09-admin-overview-metrics-v2-design.md`、`workdocs/归档/正文/设计/2026-03-09-admin-overview-metrics-v2-implementation.md`、`app/services/runtime_request_metrics.py`
- 2026-03-08｜Lean Guard 上线：热点文件进入 shrink-only，禁止继续新增内部函数（ACTIVE）→ `docs/开发文档/规范/lean-guard.md`
- 2026-03-08｜Git 生命周期收口命令显式化：`/jjk-commit` 与 `/jjk-deleteworktree`（ACTIVE）→ `.cursor/commands/jjk-commit.md`
- 2026-03-08｜治理前置命令显式化：`/jjk-arch-gate` 与 `/jjk-api-doc-sync`（ACTIVE）→ `workdocs/归档/正文/设计/2026-03-08-jjk-governance-skills-design.md`
- 2026-03-08｜数据库证据门禁左移到 plan→vkplan→cardrun→wtimp→test→verify 主链（ACTIVE）→ `workdocs/归档/正文/设计/2026-03-08-engineering-flow-db-evidence-gate-design.md`
- 2026-03-08｜产品运行时 Skill 文档同步矩阵冻结为强制门禁（ACTIVE）→ `.cursor/rules/doc_sync.mdc`
- 2026-03-08｜工程流 wrapper 脱仓时必须直指实体脚本真理源（ACTIVE）→ `workdocs/归档/正文/设计/2026-03-07-cardrun-wtflow-execution-issues.md`
- 2026-03-08｜dirty path 统一以 `git status --porcelain -z` 为真理源（ACTIVE）→ `workdocs/归档/报告/调试报告/debug_report_wf04_porcelain_z_dirty_parser.md`
- 2026-03-08｜wtimp dispatch 失败路径由 bridge 负责 process-group 清理与唯一 JSON contract（ACTIVE）→ `workdocs/归档/正文/设计/2026-03-07-cardrun-wtflow-execution-issues.md`
- 2026-03-08｜parallel_plan 降级为 vk_cards 派生总览（ACTIVE）→ `workdocs/归档/正文/设计/2026-03-08-parallel-plan-vk-cards-unification-design.md`
- 2026-03-08｜`wt-flow status` 必须显式输出 active/stale state context（ACTIVE）→ `workdocs/归档/正文/设计/2026-03-07-cardrun-wtflow-execution-issues.md`
- 2026-03-08｜文件编辑必须以实际工具面为准（ACTIVE）→ `AGENTS.md`
- 2026-03-08｜测试解释器必须先解析仓级真理源（ACTIVE）→ `scripts/repo_python.sh`
- 2026-03-08｜定向红绿验证与最终 coverage 门禁必须分层（ACTIVE）→ `scripts/pytest_targeted.sh`
- 2026-03-08｜运行态日志与提交证据必须分轨（ACTIVE）→ `scripts/check_workflow_contract.py`
- 2026-03-07｜聊天控制面恢复/终止语义冻结（ACTIVE）→ `docs/产品文档/聊天系统需求.md`
- 2026-03-07｜DB 驱动渐进式 Skill Loader Phase A 冻结（ACTIVE）→ `workdocs/归档/正文/设计/2026-03-07-db-backed-progressive-skill-loading-design.md`
- 2026-03-05｜规则分层落地（ACTIVE）→ `AGENTS.md`
- 2026-03-06｜MCP 权威配置收敛（ACTIVE）→ `workdocs/归档/正文/设计/2026-03-06-mcp-governance-design.md`
- 2026-03-06｜复合提问多模态响应契约收敛（ACTIVE）→ `workdocs/归档/正文/设计/2026-03-06-composite-query-multimodal-response-design.md`
- 2026-03-06｜Clarify 发散/冻结分流口径调整（ACTIVE）→ `.cursor/commands/jjk-clarify.md`
- 2026-03-07｜`/ask` 退化为 clarify 兼容壳（ACTIVE）→ `.cursor/commands/ask.md`
- 2026-03-06｜cardrun 默认执行器切换至 wtimp（ACTIVE）→ `workdocs/归档/正文/设计/2026-03-06-cardrun-wtimp-executor-design.md`
- 2026-03-06｜工程减法退役流程冻结（ACTIVE）→ `workdocs/归档/正文/设计/2026-03-06-workflow-gate-retirement-design.md`
- 2026-03-07｜wt-flow merge 统一收口到 common repo（ACTIVE）→ `workdocs/归档/正文/设计/2026-03-07-cardrun-wtflow-execution-issues.md`
- 2026-03-07｜active-task `.state/<task_key>/` 纳入 dirty whitelist（ACTIVE）→ `workdocs/归档/正文/设计/2026-03-07-cardrun-wtflow-execution-issues.md`

- 2026-03-08｜Skill 真理源收敛为 DB-only，退役本地 SKILL.md 导入链（ACTIVE）→ `workdocs/归档/正文/设计/2026-03-07-db-backed-progressive-skill-loading-design.md`
- 2026-03-08｜聊天前端字体系统切换为 CJK WebFont + 内容列宽统一 token（ACTIVE）→ `workdocs/归档/正文/设计/2026-03-08-chat-typography-cjk-design.md`
- 2026-03-08｜编排层禁止硬编码语义关键词词表（ACTIVE）→ `AGENTS.md`
- 2026-03-09｜补充回合语义识别收敛到 session_intent_kernel，decompose_goals 只做 data.query 纠偏（ACTIVE）→ `app/ai/workflow/session_intent_kernel.py`
- 2026-03-08｜主文档只表达当前态，过程文档只承载历史与证据（ACTIVE）→ `workdocs/归档/正文/设计/2026-03-08-doc-single-source-dynamic-governance-design.md`

- 2026-03-09｜Git 交付收口分层为命令编排层 + 共享 delivery engine（ACTIVE）→ `workdocs/归档/正文/设计/2026-03-09-jjk-commit-delivery-engine-design.md`

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

### 2026-03-09 Git 交付收口分层为命令编排层 + 共享 delivery engine

- 状态：ACTIVE
- 决策主题：把 `jjk-commit` 从“交付门禁 + 半套 merge 口径”收敛为交付编排层，并将真实 Git 生命周期统一下沉到共享 delivery engine
- 背景与问题：当前 `jjk-commit` 文案仍以 `--ff-only` + 人工冲突处理为主，而 `wt-flow.sh` 已实现 `rebase + --no-ff merge + abort`；命令层和脚本层形成两套 merge 真理源，用户无法稳定判断应该信哪一套
- 最终决策：新增共享 `Git Delivery Engine` 作为 `rebase / merge / continue / abort / status / prepare-base` 的唯一执行层；`jjk-commit` 仅保留交付门禁、验证证据、提交摘要与错误码翻译；`wt-flow.sh` 复用 engine，只保留 card/worktree 状态语义
- 取舍理由：项目未上线，优先彻底收敛结构性分裂，而不是继续靠文案提醒或兼容补丁维持两套行为；这样既能提升可恢复性，也能让测试和文档只围绕一份真理源展开
- 影响范围：`workdocs/归档/正文/设计/2026-03-09-jjk-commit-delivery-engine-{design,implementation}.md`、`.cursor/commands/jjk-commit.md`、`.agents/skills/jjk-commit/SKILL.md`、`scripts/coder4/wt-flow.sh`、`scripts/coder4/git-delivery-engine.sh`、`docs/开发文档/流程与工具/*`、`docs/开发文档/流程与工具/*`
- 回退/失效条件：若未来由统一工程流编排器完全接管本地 Git 生命周期，可将共享 engine 再次内聚进新的单一入口；在此之前，不得回退到 `jjk-commit` 与 `wt-flow` 各写一套 merge 逻辑
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-09-jjk-commit-delivery-engine-design.md`、`workdocs/归档/正文/设计/2026-03-09-jjk-commit-delivery-engine-implementation.md`、`.cursor/commands/jjk-commit.md`、`scripts/coder4/wt-flow.sh`

### 2026-03-09 共享开发库 Alembic 漂移收口规则

- 状态：ACTIVE
- 决策主题：共享开发库 revision 漂移时，必须补齐缺失历史迁移并新增 merge revision 收口，禁止直接篡改 `alembic_version`
- 背景与问题：当前开发库记录在 `20260309_0023`，但本分支最初只携带另一条 `20260309_0022` 迁移，导致 `alembic current` 直接失败；若继续手工改版本表，会让数据库历史与代码历史永久脱钩
- 最终决策：把缺失的 `20260308_0022`、`20260309_0023` 作为历史链补回当前分支，并用 `20260309_0024` merge revision 把双 head 合并为单 head；运行库临时补表只能用于保活，不得替代正式迁移收口
- 取舍理由：让“代码认识数据库历史”比让“数据库伪装成当前分支历史”更稳，也更符合未上线阶段优先做结构正确性的原则
- 影响范围：`alembic/versions/*`、共享开发库升级流程、后续 worktree 之间的迁移兼容策略
- 回退/失效条件：若未来所有 worktree 改为独立数据库实例，跨分支 revision 漂移风险显著降低后，可把该规则降级为推荐项；在此之前保持强约束
- 关联文档/代码：`alembic/versions/20260308_0022_add_skill_tool_contract.py`、`alembic/versions/20260309_0023_seed_data_handoff_tool_contract.py`、`alembic/versions/20260309_0024_merge_runtime_bucket_and_skill_tool_contract_heads.py`

### 2026-03-09 管理后台总览旧快照表正式退役

- 状态：ACTIVE
- 决策主题：删除 `t_ops_metric_snapshot_minute`，总览运行态不再保留展示快照表
- 背景与问题：旧快照表仍被 `AdminOverviewQueryService` 当作 fallback 与持久化使用，形成分钟桶与展示快照双真源；继续保留只会掩盖聚合链路问题并扩大语义漂移
- 最终决策：总览读取与降级都只围绕 `t_runtime_metric_bucket_minute` 表达 `ok / no_data / stale / degraded`，删除 `OpsSnapshotService`、旧快照模型、相关测试与 Alembic 表结构
- 取舍理由：项目未上线，优先把状态 owner 收敛到单表真理源；相比“保留兼容缓存”，彻底删除双写链路更简单、风险更可验证
- 影响范围：`app/services/admin_overview_query_service.py`、`app/models/runtime_metric_bucket.py`、`alembic/versions/20260309_0025_drop_ops_metric_snapshot_minute.py`、总览相关测试与数据库设计文档
- 回退/失效条件：若未来确有明确性能瓶颈，需要新增派生缓存时，必须作为独立只写缓存重新设计，且不得再次承担总览事实源或降级真相
- 关联文档/代码：`docs/开发文档/架构设计/数据库设计.md`、`workdocs/归档/正文/设计/2026-03-09-admin-overview-metrics-v2-design.md`

### 2026-03-09 管理后台总览真理源切换完成

- 状态：ACTIVE
- 决策主题：总览 V2 正式退役旧 collector、旧聚合服务与进程内双写缓存
- 背景与问题：`AdminOverviewQueryService` 已经接管分钟桶读模型，但仓内仍保留 `admin_overview_service.py`、`overview_runtime_collector.py` 和 `runtime_request_metrics_store` 双写链路，导致状态 owner 与依赖方向仍有双源
- 最终决策：总览读取只保留 `AdminOverviewQueryService`；请求埋点只写分钟桶 writer；删除旧 `admin_overview_service.py`、旧 `overview_runtime_collector.py` 及其失效测试，服务层导出同步切换到新查询服务
- 取舍理由：项目未上线，优先让结构彻底收口而不是维持过渡兼容；删除双源后，`summary / trends / stream` 与埋点写入口的边界更稳定
- 影响范围：`app/services/admin_overview_query_service.py`、`app/services/runtime_request_metrics.py`、`app/services/__init__.py`、旧总览服务/collector 文件及相关测试
- 回退/失效条件：若未来确实需要单独的进程内观测缓存，只能作为独立调试工具引入，不得再次承担总览事实源或主查询链路职责
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-09-admin-overview-metrics-v2-design.md`、`workdocs/归档/正文/设计/2026-03-09-admin-overview-metrics-v2-implementation.md`、`app/services/runtime_request_metrics.py`

### 2026-03-08 治理前置命令显式化

- 状态：ACTIVE
- 决策主题：把架构门禁与 API 文档同步从散落规则显式收敛为 `jjk-*` 前置命令
- 背景与问题：Layer1 已要求任何改动前先给四段式架构结论，且 API / 契约变更必须先同步文档，但当前只有规则没有显式命令入口，执行者容易直接跳去 `/jjk-plan`、`/jjk-imp`、`/jjk-refactor`，遗漏治理动作
- 最终决策：新增 `.cursor/commands/jjk-arch-gate.md` 与 `.cursor/commands/jjk-api-doc-sync.md` 作为真理源，并同步镜像到 `.agents/skills/`；工作流手册与速查表统一把二者标注为治理前置门禁
- 取舍理由：用显式入口降低执行歧义，比继续依赖口头提醒或散落规则更稳；项目未上线，优先把结构性治理前置而不是事后补救
- 影响范围：`.cursor/commands/jjk-{arch-gate,api-doc-sync}.md`、`.agents/skills/jjk-{arch-gate,api-doc-sync}/SKILL.md`、`docs/开发文档/流程与工具/*`、`docs/开发文档/流程与工具/*`
- 回退/失效条件：若未来把架构门禁与文档同步门禁下沉为可执行脚本或 CI 自动判定，可让命令退化为可视化入口；在此之前保持显式命令形态
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-08-jjk-governance-skills-design.md`、`.cursor/commands/jjk-arch-gate.md`、`.cursor/commands/jjk-api-doc-sync.md`

### 2026-03-08 数据库证据门禁左移到六段主链

- 状态：ACTIVE
- 决策主题：数据库风险任务的证据责任统一左移到 `plan -> vkplan -> cardrun -> wtimp -> test -> verify` 主链，不再依赖末端人工补证据
- 背景与问题：当前工程流已把 worktree、dispatch、commit、merge 收口做得较强，但“哪些任务必须验证 `chat_db/data_db/scripted_flow/E2E`”仍未成为可机读契约，导致卡片可能局部通过、全链缺少数据库级证据
- 最终决策：在 `implementation_plan` 引入 `risk_tags`、`mandatory_evidence`、typed `acceptance_cmds`；`vk_cards.json` 继承到卡片；`wtimp` 输出 typed `acceptance_results` 与 `evidence_satisfied`；`cardrun` done gate、`jjk-test`、`jjk-verify` 统一按必需证据集合放行
- 取舍理由：优先修复结构性责任边界，而不是继续在 `/jjk-test` 或 `/jjk-verify` 末端堆补丁；这样更符合项目未上线阶段“设计合理性优先”的治理原则
- 影响范围：`.cursor/commands/jjk-{plan,vkplan,cardrun,wtimp,test,verify}.md`、`scripts/check_workflow_contract.py`、`scripts/coder4/*`、`docs/开发文档/测试管理/*`、`docs/开发文档/流程与工具/*`
- 回退/失效条件：若未来出现统一执行/测试编排平台，可将本决策升级为平台级证据契约；在此之前不得回退到“无 DB 证据也可 PASS”的旧语义
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-08-engineering-flow-db-evidence-gate-design.md`、`workdocs/归档/正文/设计/2026-03-08-engineering-flow-db-evidence-gate-implementation.md`、`.cursor/commands/jjk-cardrun.md`、`.cursor/commands/jjk-wtimp.md`

### 2026-03-08 产品运行时 Skill 文档同步矩阵冻结

- 状态：ACTIVE
- 决策主题：产品运行时 Skill 的文档同步不再依赖执行者自行猜测，统一冻结为显式强制矩阵
- 背景与问题：`技能系统需求.md`、`AI技能库.md`、`接口文档.md`、配置/部署/测试文档虽已存在，但 `doc_sync` 未对 `app/ai/skills`、`skill_service`、`skill_admin`、`import_skills` 等路径给出单一门禁，导致 AI 容易只更新部分文档
- 最终决策：在 `.cursor/rules/doc_sync.mdc` 新增“产品运行时 Skill 专项映射（强制）”，并将 `jjk-imp`、`jjk-debug`、`jjk-review`、`jjk-verify` 与工作流/速查文档统一引用该矩阵
- 取舍理由：把责任收敛到规则层而不是继续堆“经验提醒”，避免产品文档、内部机制文档、接口文档、部署文档长期漂移
- 影响范围：`.cursor/rules/doc_sync.mdc`、`.cursor/commands/jjk-{imp,debug,review,verify}.md`、`docs/开发文档/流程与工具/*`、`docs/开发文档/流程与工具/*`
- 回退/失效条件：若未来运行时 Skill 文档进一步收敛为单一主文档，可由新的单源矩阵替代；在此之前不得回退到泛化门禁
- 关联文档/代码：`.cursor/rules/doc_sync.mdc`、`docs/开发文档/流程与工具/开发工作流.md`、`docs/开发文档/流程与工具/指令用法_实现方式_工程流全景手册.md`

### 2026-03-08 wtimp dispatch 失败路径收口

- 状态：ACTIVE
- 决策主题：`wtimp_dispatch_bridge` 必须独占 dispatch 子执行器生命周期治理，失败路径统一负责 process-group 清理与唯一 JSON contract 校验
- 背景与问题：此前虽已补 `dispatch_timeout_seconds` 契约，但 bridge 仍使用 `subprocess.run(...)` + 宽松 JSON 提取；timeout 后只能杀最外层进程，stdout 中任意 dict 也可能被误判为成功回执
- 最终决策：bridge 改为 `Popen(..., start_new_session=True)`；timeout / 非零退出 / 非法回执统一附带 `session_cleanup` 证据并尝试回收当前 process-group；结果提取只接受唯一 contract payload，禁止 fallback 到任意 dict
- 取舍理由：把失败治理收敛在 bridge 边界内，避免 kernel 感知子进程细节，也避免通过宽松 coercion 或人工清理掩盖结构性问题
- 影响范围：`scripts/coder4/wtimp_dispatch_bridge.py`、`tests/unit/test_coder4_wtimp_dispatch_bridge.py`、`tests/unit/test_coder4_dispatch_executor.py`、`workdocs/归档/正文/设计/2026-03-07-cardrun-wtflow-execution-issues.md`
- 回退/失效条件：若后续 `wtimp` 引入主动脱离当前 session 的后台任务，需要升级为跨 session 清理机制；否则本决策持续有效
- 关联文档/代码：`workdocs/归档/报告/调试报告/debug_report_wf02_dispatch_timeout.md`、`workdocs/归档/正文/设计/2026-03-07-cardrun-wtflow-execution-issues.md`、`scripts/coder4/wtimp_dispatch_bridge.py`

### 2026-03-08 dirty path 解析协议收口

- 状态：ACTIVE
- 决策主题：`wt-flow` 与 `coder4_bootstrap_kernel` 的 dirty path 统一以 `git status --porcelain -z --untracked-files=no` 为真理源
- 背景与问题：此前虽已补 quoted-path decode，但 rename/copy 仍依赖文本箭头切割；当文件名自身包含 `->` 时，whitelist 命中会被误伤
- 最终决策：shell/python 两侧都改为解析 NUL 分隔记录；rename/copy 一律消费目标路径；删除 `core.quotePath=false` / 文本补码作为主路径依赖
- 取舍理由：把路径解析提升到 Git 原生记录协议层，消除“引号/箭头/空格/中文”交织时的字符串歧义
- 影响范围：`scripts/coder4/wt-flow.sh`、`scripts/coder4/coder4_bootstrap_kernel.py`、相关 dirty policy / merge / local-mode 回归测试
- 回退/失效条件：若未来改用更高层 Git 库统一封装，可由新封装替代；否则不应回退到文本行解析
- 关联文档/代码：`workdocs/归档/报告/调试报告/debug_report_wf04_porcelain_z_dirty_parser.md`、`workdocs/归档/正文/设计/2026-03-07-cardrun-wtflow-execution-issues.md`

### 2026-03-08 工程流 wrapper 真理源提示收口

- 状态：ACTIVE
- 决策主题：工程流 wrapper 在脱离仓库布局时必须 fail-fast，并直接提示实体脚本路径作为单一真理源
- 背景与问题：`scripts/wt-flow.sh` 被复制到仓库外时，旧行为只会抛出 `coder4/wt-flow.sh: No such file or directory`，用户难以判断自己拿错了 wrapper 还是实体脚本
- 最终决策：wrapper 缺失实体脚本时统一输出“当前只是 wrapper / 单一真理源是实体脚本 / 若需脱仓调试请复制实体脚本”的明确报错；仓库内正常布局继续透明转发
- 取舍理由：把错误提示提升到职责层，避免工程流使用者继续把 wrapper 当可独立运行的实体脚本，也避免为了迁就误用去复制实体实现
- 影响范围：`scripts/wt-flow.sh`、工程流手册中的脚本角色说明、后续同类 wrapper 入口
- 回退/失效条件：若未来彻底移除 wrapper 或统一由单一 Python/Bash 入口生成兼容壳，可由新入口策略替代；否则该提示规则持续有效
- 关联文档/代码：`docs/开发文档/流程与工具/指令用法_实现方式_工程流全景手册.md`、`workdocs/归档/正文/设计/2026-03-07-cardrun-wtflow-execution-issues.md`、`tests/unit/test_wt_flow_wrapper_entrypoint.py`

### 2026-03-08 Skill 真理源收敛为 DB-only，退役本地 SKILL.md 导入链

- 状态：ACTIVE
- 决策主题：Skill 的正式维护、管理面与运行时统一只认数据库 versioned 真理源，本地 `SKILL.md` 与目录导入脚本退出主路径
- 背景与问题：即使 runtime/admin 已切到 `definition/version`，只要仍保留本地目录导入链，就会继续诱发第二真理源与“重启/导入即可修复”的错误操作心智
- 最终决策：`t_agent_skill_definitions / t_agent_skill_versions / t_user_skill_bindings` 为唯一正式来源；`import_skill/import_all_skills/sync_changed_skills` 显式 fail-fast；`scripts/data/import_skills.py` 与 `tests/update_skills_db.py` 标记退役
- 取舍理由：项目未上线，优先彻底消灭双源结构，而不是保留历史脚本做软兼容；显式阻断比静默继续可维护性更高
- 影响范围：`app/services/skill_service.py`、`scripts/data/import_skills.py`、`tests/update_skills_db.py`、`docs/内部参考/AI技能库.md`、后续所有 Skill 运维/测试手册
- 回退/失效条件：若未来引入“DB 审核后再导出文件”的离线发布链，可新增只读导出工具；在此之前不得恢复本地文件导入为正式路径
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-07-db-backed-progressive-skill-loading-design.md`、`docs/内部参考/AI技能库.md`、`app/services/skill_service.py`

### 2026-03-07 DB 驱动渐进式 Skill Loader Phase A 冻结

- 状态：ACTIVE
- 决策主题：Skill 运行时收敛到 progressive loader，Phase A 的 schema 真理源、会话态与 canonical replay 一次冻结
- 背景与问题：当前聊天主链仍依赖 hybrid 检索后静默注入 `skill_context`，导致命中决策、状态归属与回放语义散落；同时 catalog metadata 若继续落在 `t_agent_skills` 兼容表，会形成双真理源
- 最终决策：聊天主路径统一为 `catalog preload -> load_skills -> additional_kwargs.skill_runtime`；catalog/runtime metadata 真理源固定为 `t_agent_skill_definitions + t_agent_skill_versions`；Phase A 持久化字段最小集冻结为 `catalog_path/catalog_order/catalog_description/when_to_use`
- 取舍理由：先在正确层级消除“后端替模型选 Skill + 双源 metadata + replay 不可还原”的结构性问题，再按需演进目录树与资源包能力
- 影响范围：`app/services/skill_service.py`、`app/ai/workflow/multi_agent_graph.py`、`app/ai/state.py`、`app/ai/protocol.py`、`app/models/agent_skill.py`、`app/api/v1/endpoints/skill_admin_api.py`、`alembic/versions/*`
- 回退/失效条件：若仅靠 `catalog_path` 派生无法满足权限/排序/运营配置，可升级到 Phase B 增加层级字段或资源表；回退时关闭 `feature.enable_progressive_skill_loading` 并切回 `skill.runtime_mode=hybrid_rag`
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-07-db-backed-progressive-skill-loading-design.md`

### 2026-03-07 聊天控制面恢复/终止语义冻结

- 状态：ACTIVE
- 决策主题：`interrupt/resume/cancel/disconnect` 与普通聊天消息彻底分离，恢复旧 run 只能走控制面
- 背景与问题：用户在流式处理中遇到中断、断流或网关报错时，容易把“继续”“你刚刚中断了”作为普通消息发送，导致控制动作与新用户意图混杂，放大旧瞬态状态污染风险
- 最终决策：`interrupt` 后只能调用 `POST /api/v1/chat/resume`；`cancel/stopped` 属于终态，不允许 resume；`disconnect/transport error` 不得被翻译成聊天文本“继续”，应等待当前 run 收口或先 cancel 再重发；同线程历史继续保留，但当前轮只处理最后一条 `HumanMessage`
- 取舍理由：优先保持控制面与意图层职责单一，避免通过自然语言兼容层掩盖状态机问题，也避免把半成品 AI 回复当最终历史展示
- 影响范围：聊天前端状态机、`app/services/chat_service.py`、`app/services/run_control_service.py`、`app/ai/workflow/multi_agent_graph.py`、`app/repositories/chat_repo.py`、聊天 API/架构文档
- 回退/失效条件：若后续引入显式 reconnect/reset-checkpoint 能力，并把瞬态状态改为真正非持久化字段，可重新评估“断流后直接续跑/重发”的交互口径
- 关联文档/代码：`docs/产品文档/聊天系统需求.md`、`docs/API文档/接口文档.md`、`docs/开发文档/架构设计/AI模块设计.md`、`app/services/chat_service.py`、`app/ai/workflow/multi_agent_graph.py`

### 2026-03-06 MCP 权威配置收敛

- 状态：ACTIVE
- 决策主题：Codex MCP 配置统一以用户本地运行时配置为权威源，项目内 `.mcp.json` 退化为协作镜像
- 背景与问题：`/Users/jijingkun/.codex/config.toml` 与仓库内 `.mcp.json` 并存且不一致，导致 GitHub MCP 缺 Token、`vibe_kanban` 启动命令漂移、排障口径不统一
- 最终决策：当前会话统一以 `/Users/jijingkun/.codex/config.toml` 为权威配置；`.mcp.json` 只保留无敏感信息的镜像；新增项目体检脚本在业务使用前暴露缺 Token、缺本地二进制、缺运行态等根因
- 取舍理由：先修配置治理层而不是继续堆补丁，既消除双源漂移，也避免将敏感信息继续留在仓库
- 影响范围：`/Users/jijingkun/.codex/config.toml`、`.mcp.json`、MCP 使用流程、工作流文档、体检脚本
- 回退/失效条件：若后续 Codex 支持项目级单一 MCP 权威源且可安全管理密钥，可将镜像与全局配置再收敛为单源
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-06-mcp-governance-design.md`、`workdocs/归档/正文/设计/2026-03-06-mcp-governance-plan.md`、`docs/开发文档/流程与工具/开发工作流.md`

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
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-06-composite-query-multimodal-response-design.md`

### 2026-03-06 Clarify 发散/冻结分流口径调整

- 状态：ACTIVE
- 决策主题：`/jjk-clarify` 采用单指令闭环（命令内完成探索与冻结）
- 背景与问题：原口径要求“可用时必须先走 brainstorming”，与 `/jjk-clarify` 的单方案冻结目标冲突，导致执行时频繁输出“规则冲突声明”，降低可用性
- 最终决策：`/jjk-clarify` 默认在命令内执行“探索轮 + 冻结轮”；默认提问模式统一为问题包（`question_mode=package`），歧义场景降级为单题追问；审批前必须写出 `clarify_consistency_check`，并满足 `clarify_phase=approval`、`open_questions_count=0`；同时新增 `python3 scripts/check_clarify_contract_consistency.py` 体检命令
- 取舍理由：保留探索能力且不增加命令切换成本，并用显式状态机与自动体检降低命令/模板/镜像漂移
- 影响范围：`.cursor/commands/jjk-clarify.md`、`.agents/skills/jjk-clarify/SKILL.md`、命令速查文档与 Codex prompts 镜像
- 回退/失效条件：若后续统一流程框架强制探索与冻结命令解耦，可回退为“两阶段命令链”
- 关联文档/代码：`.cursor/commands/jjk-clarify.md`、`docs/开发文档/流程与工具/开发工作流.md`、`docs/开发文档/流程与工具/AI协作速查表.md`、`docs/开发文档/流程与工具/vibe-coding开发技巧.md`

### 2026-03-07 `/ask` 退化为 clarify 兼容壳

- 状态：ACTIVE
- 决策主题：`/ask` 从独立发散入口降级为 `/jjk-clarify` 兼容别名
- 背景与问题：`/ask` 与 `/jjk-clarify` 同时被描述为主入口，导致工作流主链、状态归属与用户心智出现双源漂移
- 最终决策：默认研发链路统一以 `/jjk-clarify` 起步；收到 `/ask` 时在当前会话内立即并入 `/jjk-clarify`，不再维护独立 `brainstorm.md` 或独立下游门禁；仅保留历史兼容说明
- 取舍理由：以最小兼容成本换取单一状态机、单一权威产物与更低命令切换负担
- 影响范围：`.cursor/commands/ask.md`、工作流手册、速查表、Codex prompts 镜像
- 回退/失效条件：若后续平台必须恢复独立“仅发散不冻结”命令，应以新命令或新契约恢复，而不是回滚旧 `/ask` 双入口语义
- 关联文档/代码：`.cursor/commands/ask.md`、`docs/开发文档/流程与工具/开发工作流.md`、`docs/开发文档/流程与工具/指令用法_实现方式_工程流全景手册.md`、`docs/开发文档/流程与工具/vibe-coding开发技巧.md`

### 2026-03-06 cardrun 默认执行器切换至 wtimp

- 状态：ACTIVE
- 决策主题：`cardrun` dispatch 主链统一到 `jjk-wtimp`（`executor_mode=cardrun_dispatch`）
- 背景与问题：`cardrun` 原链路默认分派 `imp-ws`，导致“编排层强约束”与“执行层 worktree 生命周期”分离，commit 证据门禁难以在同一收口链上落地
- 最终决策：主链改为 `/jjk-plan -> /jjk-vkplan -> /jjk-cardrun -> /jjk-wtimp`；kernel 默认执行器设为 `wtimp`，dispatch 阶段缺失 `commit_sha` 直接 `CARDRUN_NO_COMMIT_EVIDENCE` 阻断；`wtimp` 在 `cardrun_dispatch` 模式禁止重复 merge
- 取舍理由：以最小改造统一“调度→执行→证据→收口”责任边界，降低双 merge 与伪完成风险
- 影响范围：`scripts/coder4/coder4_bootstrap_kernel.py`、`.cursor/commands/jjk-cardrun.md`、`.cursor/commands/jjk-wtimp.md`、`.cursor/commands/jjk-vkplan.md`、`.cursor/commands/jjk-create-pr.md` 及对应 skills
- 回退/失效条件：若 `wtimp` 执行链异常，可通过 `--dispatch-executor`/`CODER4_DISPATCH_EXECUTOR` 临时切回兼容执行器；若后续出现统一执行编排器，应将本决策升级为平台级执行契约
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-06-cardrun-wtimp-executor-design.md`、`workdocs/归档/正文/需求/cardrun内置wtimp执行器_requirements.md`、`workdocs/归档/正文/实施计划/cardrun内置wtimp执行器_implementation_plan.md`

### 2026-03-07 active-task `.state/<task_key>/` 纳入 dirty whitelist

- 状态：ACTIVE
- 决策主题：active task 运行态真理源 `.state/<task_key>/` 默认视为工程流运行产物，`wt-flow` 与 `bootstrap kernel` 的 dirty policy 必须自动放行该目录
- 背景与问题：此前 dirty whitelist 仅覆盖文档目录，导致 `task-runner-state.json`、`task-ledger.jsonl`、`coder4-idempotency.json` 等运行态文件一旦变脏，就会误阻断 `bootstrap/merge`；同时中文路径在 git quoted path 下又会进一步放大误判
- 最终决策：基于 `active_task.task_split_dir + task_key` 自动推导运行态状态目录并追加到 dirty whitelist；显式用户白名单不被覆盖，只做合并；quoted path 必须先解码后再参与匹配
- 取舍理由：运行态真理源不应再被当作“用户未提交脏改动”处理；优先恢复工程流稳定执行，再逐步细化 lock/session 等更小粒度分类
- 影响范围：`scripts/coder4/wt-flow.sh`、`scripts/coder4/coder4_bootstrap_kernel.py`、dirty policy 相关测试与工程流文档
- 回退/失效条件：若后续把运行态真理源整体迁出 Git 工作区，或引入独立运行态存储层，本决策可失效并转由新存储边界承担 dirty 隔离
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-07-cardrun-wtflow-execution-issues.md`、`workdocs/归档/报告/调试报告/debug_report_wf03_state_dirty_whitelist.md`

### 2026-03-07 wt-flow merge 统一收口到 common repo

- 状态：ACTIVE
- 决策主题：`wt-flow merge` 的基线分支合并上下文固定归属 `common repo root`，不再依赖当前 card worktree checkout
- 背景与问题：当前 `cmd_merge` 在 card worktree 内执行时，会把当前 checkout 当成 merge 驱动仓并尝试 `git checkout master`；当 `master` 已被主工作区占用时，Git 会直接报 `already used by worktree`，导致已 verified 的卡片无法在原位完成 merge
- 最终决策：保留 `rebase` 在 card worktree 执行，但把 `dirty policy`、`checkout base_branch`、`git merge --no-ff` 与 merge 结果回写统一收口到 `common repo root`；执行目录不再作为 merge 成败前提
- 取舍理由：先修正“会话 worktree 与基线仓职责混淆”的结构性问题，保证 cardrun / wt-flow 在 worktree 体系下行为一致，而不是继续依赖“退回主仓手工 merge”的人工绕行
- 影响范围：`scripts/coder4/wt-flow.sh`、`tests/unit/test_coder4_wt_flow_verified_state.py`、`workdocs/归档/正文/设计/2026-03-07-cardrun-wtflow-execution-issues.md`
- 回退/失效条件：若后续引入专用 merge-driver worktree 或平台级 merge service，可将本决策升级为新的 merge 执行抽象；若 common repo root 不再承担基线仓职责，本决策失效
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-07-cardrun-wtflow-execution-issues.md`、`scripts/coder4/wt-flow.sh`

### 2026-03-06 工程减法退役流程冻结

- 状态：ACTIVE
- 决策主题：L1 门禁脚本退役执行口径统一为“迁移入口 -> 兼容壳 -> 零调用观测 -> 再删除”
- 背景与问题：`工程减法体检报告_2026-03-06.md` 中存在“候选可删”与“3.1 NO-GO 冻结”并存，团队执行口径易漂移
- 最终决策：以 `工程减法体检报告_2026-03-06_v3.md` 作为唯一执行基线；先建统一入口 `check_workflow_contract.py`，旧 L1 脚本先 wrapper 化并完成引用迁移，连续 7 天零调用后再删除旧实现
- 取舍理由：在减法目标下优先保证设计合理性与主干流程完整性，避免“先删后补”的架构级故障
- 影响范围：`scripts/check_*` L1 门禁脚本、`.cursor/commands/*`、`.agents/skills/*`、工作流与治理文档
- 回退/失效条件：若统一入口兼容性或验收矩阵失败，回退为“旧脚本主入口 + wrapper 反向代理”，并暂停删除阶段
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-06-workflow-gate-retirement-design.md`、`workdocs/归档/专题/治理专题/工程减法治理/工程减法体检报告_2026-03-06_v3.md`

### 2026-03-08 parallel_plan 降级为 vk_cards 派生总览

- 状态：ACTIVE
- 决策主题：`parallel_plan.md` 从拆卡阶段并列真理源降级为 `vk_cards.json` 自动生成的人类可读总览
- 背景与问题：当前 `parallel_plan.md` 与 `vk_cards.json` 同时承载执行策略、Gate 契约与总览信息，而实际执行链主要消费 `vk_cards.json`，双写带来漂移与心智负担
- 最终决策：`vk_cards.json` 作为拆卡后唯一机器真理源；新增/统一 `gate_results` 等运行态字段写回 `vk_cards.json`；`parallel_plan.md` 仅作为由 `vk_cards.json` 渲染生成的展示视图保留
- 取舍理由：在不污染上游 `implementation_plan.md` 的前提下收敛运行态真理源，减少并行文档双写，同时保留人工阅读与历史目录兼容性
- 影响范围：`scripts/backfill_gate_status.py`、`scripts/workflow_contract_gate_contract_impl.py`、任务拆解模板、`jjk-vkplan/jjk-cardrun/jjk-imp-ws/jjk-test/jjk-vktodo` 文档口径
- 回退/失效条件：若后续平台引入独立 Gate 状态存储或统一视图服务，可继续下沉 `parallel_plan.md`；若必须恢复人工可编辑并行总览，应新建独立文档而不是恢复其真理源职责
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-08-parallel-plan-vk-cards-unification-design.md`、`workdocs/任务拆解/_templates/parallel_plan_template.md`

### 2026-03-08 wt-flow status 状态发现契约显式化

- 状态：ACTIVE
- 决策主题：`wt-flow status` 必须显式输出 active task 与 stale state 候选的映射，不允许再让人工靠目录名猜真理源
- 背景与问题：历史 `.state/<task_key>/` 与当前 active task 的 `.state/<task_key>/` 可同时存在；此前 `status` 只给 session/worktree 信息，无法直接看出当前命中的 active task file、task_key 与 state root
- 最终决策：`status` 统一输出 `ACTIVE_TASK_FILE`、`ACTIVE_TASK_SPLIT_DIR`、`ACTIVE_TASK_KEY`、`TASK_STATE_ROOT`、`STALE_STATE_CANDIDATES`；仅做只读发现，不在该命令内自动清理历史状态目录
- 取舍理由：先把“状态发现”与“状态治理”边界切清，降低误判真理源的概率，同时避免把自动清理做成新的隐式 fallback 或误删风险
- 影响范围：`scripts/coder4/wt-flow.sh`、`tests/unit/test_coder4_wt_flow_verified_state.py`、工程流状态诊断与人工排障路径
- 回退/失效条件：若后续引入独立状态浏览器或编排服务，并以更强契约提供同等 active/stale 映射，可把 CLI `status` 简化为该服务代理；否则本决策持续有效
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-07-cardrun-wtflow-execution-issues.md`、`scripts/coder4/wt-flow.sh`

### 2026-03-08 文件编辑工具面契约冻结

- 状态：ACTIVE
- 决策主题：文件编辑必须以当前会话**实际暴露**的工具面为准；若无独立 `apply_patch` 入口，禁止通过 `exec_command` 包装 `apply_patch`
- 背景与问题：本轮执行中外层提示持续要求“使用 apply_patch tool”，但真实工具清单并未暴露该入口，导致代理在遵从提示与遵从工具事实之间反复空转
- 最终决策：在 `AGENTS.md` 与工程流手册中冻结同一条契约；命中该场景时统一记录 `APPLY_PATCH_TOOL_UNAVAILABLE_FALLBACK`，并改用当前可用的直接写回方式，不再尝试伪造不存在的编辑工具
- 取舍理由：优先尊重真实工具边界，先修“指令链冲突”而不是继续制造 wrapper/兼容壳，避免把工具提示漂移演化成执行链稳定性问题
- 影响范围：`AGENTS.md`、`CLAUDE.md`、`docs/开发文档/流程与工具/指令用法_实现方式_工程流全景手册.md`、相关文档一致性回归测试
- 回退/失效条件：若后续运行环境正式暴露独立 `apply_patch` 工具并同步修正文案，本决策可退化为“优先真实 apply_patch，删除 fallback 标记”
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-07-cardrun-wtflow-execution-issues.md`、`tests/unit/test_workflow_tooling_contract_docs.py`

### 2026-03-08 仓级测试解释器真理源冻结

- 状态：ACTIVE
- 决策主题：测试/验证命令必须先解析仓级 Python 解释器真理源，不再默认裸用 `python3 -m pytest`
- 背景与问题：本轮定向回归首次失败并非业务断言失败，而是系统 `python3` 缺少 pytest；而仓内 `venv` 已具备完整依赖，说明问题出在解释器入口漂移
- 最终决策：新增 `scripts/repo_python.sh` 作为单一解析入口；优先级固定为 `VK_RUNTIME_VENV -> venv -> .venv -> .vibe/venv -> python3 -> python`；`AGENTS.md` 与测试指南统一引用该入口
- 取舍理由：把解释器选择从分散命令模板中抽离出来，避免每个测试命令各自猜环境，也避免“环境失败掩盖真实回归”再次发生
- 影响范围：`scripts/repo_python.sh`、`AGENTS.md`、`docs/开发文档/测试管理/测试指南与环境配置.md`、测试/验证执行链与相关回归测试
- 回退/失效条件：若未来平台提供更上层的仓级解释器发现机制并稳定覆盖 worktree 场景，可由新机制替代；否则应继续维持脚本为单一入口
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-07-cardrun-wtflow-execution-issues.md`、`tests/unit/test_repo_python_script.py`、`scripts/repo_python.sh`

### 2026-03-08 定向 pytest 与最终 gate 语义分层

- 状态：ACTIVE
- 决策主题：开发期定向红绿验证与最终 coverage 门禁必须使用不同入口，禁止再混成同一条 pytest 命令
- 背景与问题：本轮新回归测试 RED 时，真实失败之外又叠加了全局 coverage 阈值失败，说明开发期最小验证被最终门禁语义污染
- 最终决策：新增 `scripts/pytest_targeted.sh` 作为开发期定向入口，固定注入 `--no-cov` 并拒绝 `--cov*` 混用；最终收口继续使用常规 pytest/coverage 命令
- 取舍理由：先让 TDD/调试阶段只对“是否命中当前根因”负责，避免 coverage 噪音掩盖红灯；同时不削弱最终收口门禁
- 影响范围：`scripts/pytest_targeted.sh`、`AGENTS.md`、`docs/开发文档/测试管理/测试指南与环境配置.md`、开发期回归与最终验收的测试命令模板
- 回退/失效条件：若未来测试平台原生支持“targeted-no-cov / final-gate-cov”双模式，并能稳定覆盖本仓工作流，可由平台模式替代脚本；否则应继续维持双入口
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-07-cardrun-wtflow-execution-issues.md`、`tests/unit/test_pytest_targeted_script.py`、`scripts/pytest_targeted.sh`

### 2026-03-08 usage 运行日志与提交证据分轨

- 状态：ACTIVE
- 决策主题：`logs/workflow-gate-usage.jsonl` 只承担运行态观测；提交证据必须由 `usage-report` 显式导出到 tracked report 文件
- 背景与问题：此前 `C05` 把 ignored `logs/` 文件同时当作运行态台账和验收证据，导致默认提交链路需要 `git add -f` 才能携带关键证据
- 最终决策：保留运行态日志在 `logs/`；`check_workflow_contract.py --mode usage-report` 新增 `--log-path` / `--report-output`，统一导出 `workdocs/任务拆解/2026-03-06_工程减法治理/reports/workflow-gate-usage-report.json` 作为提交证据
- 取舍理由：先切清“滚动日志”和“可提交证据”边界，既保留运行时观测体验，又避免 ignored 目录与提交流程天然冲突
- 影响范围：`scripts/check_workflow_contract.py`、`workdocs/归档/正文/设计/2026-03-06-workflow-gate-retirement-design.md`、workflow-gate retirement 需求/实现计划、`WS-C05` / `vk_cards.json` 契约与相关回归测试
- 回退/失效条件：若后续平台为观测证据提供独立存储/导出服务，可由平台服务替代 report 导出；否则应继续维持 runtime log 与 tracked report 双轨
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-07-cardrun-wtflow-execution-issues.md`、`tests/unit/test_workflow_gate_usage_report_contract.py`、`scripts/check_workflow_contract.py`

### 2026-03-08 聊天前端字体系统切换为 CJK WebFont + 内容列宽统一 token

- 状态：ACTIVE
- 决策主题：聊天前端统一采用 CJK 主字体、阅读型 typography 与共享会话内容列宽契约
- 背景与问题：原方案以 `Inter` 作为全局主字体，中文主要依赖系统 fallback，导致英文与中文气质割裂；同时 AI 正文、用户气泡、状态行与底部输入框分别挂在不同宽度层，出现“会话元素脱离统一内容列”的布局割裂。
- 最终决策：根布局统一注入 `Noto Sans SC`，全局样式收口字体与排版 token，并让 AI 正文、用户气泡、状态行、加载占位、操作栏与 `ChatInput` 共同消费同一内容列宽 token；图表/SQL/工具结果继续保留较宽展示宽度；Markdown 段落/列表/表格间距统一由 `markdown-styles.css` 负责，`MarkdownText` 组件只保留语义与行为渲染。
- 取舍理由：未上线阶段优先消除字体入口分散与内容列宽双源配置的结构性问题，用一次收敛换取后续内容产品一致性。
- 影响范围：`web/src/app/layout.tsx`、`web/src/app/globals.css`、`web/src/components/chat/ChatInput.tsx`、`web/src/components/chat/messages/human.tsx`、`web/src/components/chat/messages/ai.tsx`、`web/src/components/chat/markdown-text.tsx`、`web/src/components/chat/markdown-styles.css`、`web/src/components/chat/index.tsx`、会话消息渲染链路。
- 回退/失效条件：若后续需要按平台或品牌拆分多套字体系统，或针对图表工作台引入独立内容栅格，可在保留单一 token 入口的前提下按场景拆分。
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-08-chat-typography-cjk-design.md`

### 2026-03-10 问数 TopN/Ranking contract 贯穿 handoff -> session_frame -> SQL 生成

- 状态：ACTIVE
- 决策主题：`data.query` 的 `query_shape/ranking` 必须成为问数 SQL 生成的稳定真值源，禁止在 handoff 后退化为“只看重建摘要文本”
- 背景与问题：TopN 查询在 `pending_handoff.frame` 已带 `query_shape=top_n/ranking.limit=10`，但 `analyze_data_intent` 会把补充轮问题重建成“查询贷款余额，时间范围…，按客户聚合”，`metric_resolve` 再次只按自然语言判断形态，导致 `ORDER BY/LIMIT 10` 丢失，最终被 SQL 安全层补成默认 `LIMIT 1000`
- 最终决策：新增独立 query contract 归一层；`build_data_query_handoff_frame`、`session_frame`、`query_context` 统一携带 `query_shape/ranking`；`metric_resolve/_derive_metric_sql/_is_sql_semantically_compatible` 直接消费结构化 contract；重建问题文本仅用于展示与日志，不再承担 TopN 真理源
- 取舍理由：与其在 SQL 安全层或展示层做“前10”特判，不如把结构化 contract 真正贯通到执行层；这样既修当前 bug，也避免未来补充轮/多意图 handoff 再次丢槽
- 影响范围：`app/ai/workflow/data_query_contract.py`、`app/ai/workflow/data_graph.py`、`app/ai/workflow/session_intent_kernel.py`、`tests/unit/test_data_graph_semantic_guard.py`、`tests/unit/test_data_graph_clarify_guard.py`
- 回退/失效条件：若未来问数 SQL 生成完全切换到更强的 schema-driven planner，可由新的 contract owner 接管；在此之前不得回退为“重新拼自然语言再猜 TopN”
- 关联文档/代码：`docs/产品文档/问数助手需求.md`、`docs/开发文档/架构设计/AI模块设计.md`、`app/ai/workflow/data_query_contract.py`

### 2026-03-09 补充回合语义识别收敛到 intent 层

- 状态：ACTIVE
- 决策主题：图表/维度/时间/筛选类补充回合统一由 `session_intent_kernel` 输出结构化信号，`decompose_goals` 仅基于该信号和 persisted visible window 做 `data.query` 纠偏
- 背景与问题：同线程第二轮输入“以柱状图方式展示”时，planner 可能退化成 `general.reply`，并把内部 coverage 缺口暴露成“问题回复未完成”
- 最终决策：新增轻量文本 frame 提取与 `classify_turn_act_from_text(...)`，在 `multi_agent_graph._resolve_decomposed_goals_for_query(...)` 中仅对“上一轮存在问数上下文 + 当前轮存在结构化补充信号 + planner/rule 同时退化为 general.reply”执行单点纠偏
- 取舍理由：把语义识别继续留在编排层会违反“编排层禁止硬编码语义词表”；下沉到 intent 层后，规划层职责更单一，也能避免把“好的”之类确认短句误扩成 `data.query`
- 影响范围：`app/ai/workflow/session_intent_kernel.py`、`app/ai/workflow/multi_agent_graph.py`、`tests/unit/test_intent_plan_model_primary.py`、问数需求/测试文档
- 回退/失效条件：若未来 planner prompt 已稳定消费会话窗口并能可靠输出补充回合目标，可保留 intent 层解析作为兜底；若出现跨域补充误判，需以更细粒度 contract 替代当前轻量 frame
- 关联文档/代码：`app/ai/workflow/session_intent_kernel.py`、`app/ai/workflow/multi_agent_graph.py`、`docs/产品文档/问数助手需求.md`、`docs/开发文档/测试管理/问数引擎测试案例.md`

### 2026-03-08 编排层禁止硬编码语义关键词词表

- 状态：ACTIVE
- 决策主题：把“自然语言语义识别不得下沉到编排层”冻结为仓级治理门禁
- 背景与问题：Codex 在修复聊天/记忆等链路时，倾向于在 `chat_service`、API endpoint 等编排层直接补 `*_HINTS`、`*_KEYWORDS` 或 substring 判断，短期可跑通，长期会把语义 owner 打散到多层
- 最终决策：在 `AGENTS.md` 与 `.cursor/rules/core.mdc` 明确禁止编排层新增业务语义关键词词表/正则词表/substring 判定；同时新增静态边界测试，发现 `*_HINTS/*_KEYWORDS/*_TRIGGERS` 直接 fail-fast
- 取舍理由：项目未上线，优先用治理门禁阻断错误设计继续扩散，而不是接受“先补词表再慢慢收敛”的伪修复路径
- 影响范围：`AGENTS.md`、`.cursor/rules/core.mdc`、`tests/unit/test_semantic_keyword_boundary_gate.py`
- 回退/失效条件：若未来编排层被完全替换为统一的 schema-driven contract adapter，且语义规则可由中心化 policy 自动校验，可将静态测试迁移到新的治理入口；在此之前保持仓级 fail-fast
- 关联文档/代码：`AGENTS.md`、`.cursor/rules/core.mdc`、`tests/unit/test_semantic_keyword_boundary_gate.py`

### 2026-03-08 Git 生命周期收口命令显式化

- 状态：ACTIVE
- 决策主题：把“提交并合并到 master”与“删除当前分支/worktree”从零散 Git 口头操作提升为显式命令 `/jjk-commit`、`/jjk-deleteworktree`
- 背景与问题：此前工程流虽覆盖规划、实现、验收与 PR 交付，但本地 Git 收尾仍依赖临时口述，容易出现“未验证先 merge”“删错 worktree”“在主工作区误删”等高风险操作
- 最终决策：新增 `/jjk-commit` 负责当前分支提交 + 合并到主工作区 `master`；新增 `/jjk-deleteworktree` 负责当前附加 worktree 与当前分支的生命周期清理；两者都必须做上下文、干净度、合并状态与证据门禁
- 取舍理由：把高风险 Git 生命周期动作收敛到清晰边界，避免继续把流程知识散落在聊天指令和人工习惯里
- 影响范围：`.cursor/commands/jjk-commit.md`、`.cursor/commands/jjk-deleteworktree.md`、`.agents/skills/jjk-commit/`、`.agents/skills/jjk-deleteworktree/`、`docs/开发文档/流程与工具/*`、`docs/开发文档/流程与工具/*`
- 回退/失效条件：若未来统一由单一工程流编排器接管本地 merge/cleanup 生命周期，可将两条命令退役并收敛到新入口；在此之前保持显式命令入口
- 关联文档/代码：`.cursor/commands/jjk-commit.md`、`.cursor/commands/jjk-deleteworktree.md`、`docs/开发文档/流程与工具/开发工作流.md`

### 2026-03-08 Lean Guard 上线：热点文件进入 shrink-only

- 状态：ACTIVE
- 决策主题：把“热点文件禁止继续膨胀”从软约束升级为 `lean-guard` 硬门禁
- 背景与问题：此前虽已在 `AGENTS.md` 与 `core.mdc` 强调 lean/refactor，但没有自动阻断；执行者会自然选择在大文件中继续添加 `_helper`、嵌套函数与包装层
- 最终决策：对 `app/ai/workflow/**/*.py`、`app/services/**/*.py`、`scripts/**/*.py` 启用 Lean Guard；超阈值文件进入 shrink-only，并禁止继续新增私有 helper 与嵌套函数
- 取舍理由：项目未上线，优先把结构债务阻断在继续扩散之前，而不是依赖后续人工治理
- 影响范围：`AGENTS.md`、`.cursor/rules/core.mdc`、`docs/开发文档/规范/lean-guard.md`、`scripts/ci/check_lean_budget.py`、工作流/速查文档
- 回退/失效条件：若未来热点目录和阈值有统一配置中心，可将脚本内阈值迁移到配置文件；在此之前保持脚本单一真理源
- 关联文档/代码：`docs/开发文档/规范/lean-guard.md`、`scripts/ci/check_lean_budget.py`

### 2026-03-08 文档单一真相源与动态融合治理

- 状态：ACTIVE
- 决策主题：主文档动态融合治理口径冻结
- 背景与问题：当前产品文档、架构文档持续通过“增量需求 / 实现进展 / 日期补充”承载新事实，导致当前态与历史过程混杂，review 与执行链无法稳定判断哪份文档才是最新口径
- 最终决策：主文档只表达当前态；设计、实施、审批与风险证据只保留在 `workdocs/设计/`、`workdocs/归档/` 与少量旧入口历史材料；一旦触达主文档，必须把旧增量内容吸收进原章节并删除旧堆叠段
- 取舍理由：项目未上线，优先保证长期设计合理性与单一真相源，而不是保留看似方便的历史追加写法
- 影响范围：`docs/产品文档/*`、`docs/开发文档/架构设计/*`、`docs/API文档/*`、`.cursor/rules/doc_sync.mdc`、`scripts/docs_guard.py`、`scripts/check_doc_sync.sh`
- 回退/失效条件：仅允许通过受控 allowlist 针对存量历史债务短时放行；若未来统一文档平台内建角色化治理，可由平台规则替代当前仓内脚本
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-08-doc-single-source-dynamic-governance-design.md`、`workdocs/归档/正文/需求/文档单一真相源与动态融合治理_requirements.md`、`workdocs/归档/正文/实施计划/文档单一真相源与动态融合治理_implementation_plan.md`

### 2026-03-08 运行态补齐缺口不再进入用户交互

- 状态：ACTIVE
- 决策主题：Coverage 缺口与编排型工具调用统一收回内部运行态，不再暴露为用户确认动作或原始工具名
- 背景与问题：单目标问数在模型主判定退化为 `general.reply` 时，coverage gate 会把内部补齐缺口转成“请回复继续”，前端同时直出 `assign_to_data_expert` 等内部工具名，导致用户看到编排状态而不是产品语义
- 最终决策：保持模型主判定优先，但在“模型=通用单目标、规则=专家型单目标”时执行单目标强语义纠偏；coverage gate 与 final composer 不再发送补齐类 clarification；前端过滤编排型工具面板
- 取舍理由：项目未上线，优先让运行态边界清晰、用户契约稳定，而不是继续叠加兼容提示或引导用户配合内部补齐流程
- 影响范围：`app/ai/workflow/multi_agent_graph.py`、`app/ai/prompts/agent_prompts.py`、`web/src/components/chat/messages/{ai,tool-calls}.tsx`、相关回归测试与需求/设计文档
- 回退/失效条件：若未来引入独立的“面向用户任务进度卡”并有稳定契约，可重新开放部分编排观测；在此之前禁止原始工具名和 coverage 缺口提问直出
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-08-multi-agent-coverage-gap-visible-contract-design.md`

### 2026-03-08 memory intent 删除解析收敛到 resolver

- 状态：ACTIVE
- 决策主题：删除/撤销类记忆解析统一下沉到 `memory_intent_resolver_service`，`chat_service` 只保留编排职责
- 背景与问题：上一轮为了修复“忘掉这个记忆”落库失败，把删除词表、指代修复和成功/失败话术补丁直接叠加到了 `chat_service`；但项目真实口径是“对话结束后异步记忆”，这导致语义判断、状态事实和回复策略错层耦合
- 最终决策：`chat_service` 不再维护删除关键词词表；反向记忆是否成立、目标是否唯一定位、是否需要澄清，统一由 `memory_intent_resolver_service` 输出 contract；异步主链继续 enqueue-only；`archive` 允许空 `normalized_value` 的底层校验修复保留
- 取舍理由：优先把语义判断放回正确层级，让异步 worker 与同步降级共享同一 resolver，而不是继续在聊天主链堆补丁
- 影响范围：`app/services/chat_service.py`、`app/services/memory_intent_resolver_service.py`、`app/services/memory_intent_llm_service.py`、`app/ai/prompts/agent_prompts.py`、相关 unit tests
- 回退/失效条件：若后续引入独立 memory intent worker handler/service，可把 resolver 继续上移为 worker 专属入口；若主链恢复同步记忆判定，也必须继续复用 resolver，不得把词表补丁放回 chat_service
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-08-memory-intent-resolver-contract-design.md`

### 2026-03-09 document_memory_repo 列表契约改为默认窄返回

- 状态：ACTIVE
- 决策主题：`document_memory_repo.list_documents()` 默认只返回通用文档列表字段，`source_thread_id/source_message_id` 改为调用方显式 opt-in
- 背景与问题：为了支持 memory 删除确认链，当前分支一度把 `source_thread_id/source_message_id` 直接加入 `list_documents()` 默认返回；这会让 resolver 场景字段上升为全局 repo 契约，扩大影响面
- 最终决策：`list_documents()` 新增 `include_source_refs=False`，默认保持窄返回；仅 `memory_intent_resolver_service` 的 archived 候选查询显式传入 `include_source_refs=True`
- 取舍理由：优先保持 repo 通用接口稳定、最小；场景字段只有在确实需要时才暴露，避免“为了一个调用方永久拉宽所有调用方”的设计回退
- 影响范围：`app/repositories/document_memory_repo.py`、`app/services/memory_intent_resolver_service.py`、相关 unit tests
- 回退/失效条件：若后续有多个独立场景都稳定依赖 source refs，可再评估是否升级为专用列表 DTO 或独立 repo 接口；禁止直接恢复为默认全量返回
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-09-memory-intent-lean-cleanup-design.md`、`app/repositories/document_memory_repo.py`、`app/services/memory_intent_resolver_service.py`

### 2026-03-09 response guidance 收敛为结构化 contract

- 状态：ACTIVE
- 决策主题：memory 删除后的运行时回复约束不再由 `chat_service` 直接拼接文本，而是收敛为 `response_guidance_contract` 结构化字段
- 背景与问题：上一轮虽然已把删除识别从 `chat_service` 拔到 resolver，但删除成功/幂等删除的提示文案仍由 service 直接拼接；这让状态事实与系统提示文本继续耦合在同一层
- 最终决策：`chat_service` 只输出结构化 guidance contract（如 kind/status/target/followup_behavior）；contract 的构造与渲染统一收敛到 `response_policy_service`。`multi_intent/router_blocked` 的恢复提示也统一迁入该 service，`multi_agent_graph` 只负责调用并注入 `system_context`
- 取舍理由：优先把“状态事实”“策略合同”“系统提示渲染/恢复提示”继续拆层，避免 graph/service 反复长出散落 helper，也为后续扩展到更完整的 responder/policy engine 留出稳定入口
- 影响范围：`app/services/chat_service.py`、`app/services/response_policy_service.py`、`app/ai/state.py`、`app/ai/workflow/multi_agent_graph.py`、`tests/unit/test_multi_agent_streaming_helpers.py`、相关 unit tests
- 回退/失效条件：若后续引入更完整的 response policy/responder 层，应继续以 `response_policy_service` 为迁移入口平滑演进；禁止再把文案模板直接塞回 `chat_service` 或 `multi_agent_graph`
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-09-memory-intent-lean-cleanup-design.md`、`app/services/chat_service.py`、`app/services/response_policy_service.py`、`app/ai/workflow/multi_agent_graph.py`

### 2026-03-09 docs_guard 提交门禁降级为提醒模式

- 状态：ACTIVE
- 决策主题：本地提交链路中的 `docs_guard` 从严格阻断改为提醒模式，手动校验与 CI 继续保留严格门禁
- 背景与问题：当前 `docs_guard` 同时挂在 `.githooks/pre-commit` 与 `scripts/check_doc_sync.sh` 的 `--strict` 路径上，broken link 等存量文档债务会频繁阻断代码提交，影响正常收口
- 最终决策：`scripts/docs_guard.py` 新增 `--non-blocking`；提交 hook 与 `check_doc_sync.sh` 在提交场景统一改走非阻断模式；显式 `--strict` 仍保留非零退出码
- 取舍理由：保留文档治理可见性，但把“提交提醒”和“严格门禁”拆层，避免本地提交体验持续被历史文档债务打断
- 影响范围：`.githooks/pre-commit`、`scripts/check_doc_sync.sh`、`scripts/docs_guard.py`、`scripts/README.md`
- 回退/失效条件：若后续 CI 已稳定承接 docs_guard 严格门禁，可继续保持本地提醒模式；若需要恢复本地强门禁，必须显式改回 `--strict`
- 关联文档/代码：`scripts/docs_guard.py`、`scripts/check_doc_sync.sh`、`.githooks/pre-commit`、`scripts/README.md`

### 2026-03-10 Phase 4 收尾：service getter 只保留薄入口

- 状态：ACTIVE
- 决策主题：应用级共享 service 若继续保留 `get_xxx_service()` 入口，该入口只能做 registry 访问，不能再持有 singleton 状态
- 背景与问题：`permission_service` 同时存在 `__new__` 单例和模块级 `_permission_service`，`result_enrichment_rule_service` 存在 `_service_singleton`，`data_admin_api` 还在导入期提前取实例；这会让 `lifespan -> AppRuntime -> CacheRegistry` 主干外再长出第二套 owner
- 最终决策：删除类级 / 模块级 singleton owner；`get_permission_service()`、`get_result_enrichment_rule_service()` 保留为无状态薄入口，内部统一走 `CacheRegistry`；endpoint 禁止在 import 阶段缓存共享 service 实例
- 取舍理由：这样既保住现有调用面，避免无意义签名扩散，又能把状态归属重新收回 runtime 管理域，符合 FastAPI lifespan 的单 owner 最佳实践
- 影响范围：`app/services/permission_service.py`、`app/services/result_enrichment_rule_service.py`、`app/api/v1/endpoints/data_admin_api.py`、相关 registry/runtime 测试
- 回退/失效条件：若未来引入统一 DI 容器并明确替代薄 getter，可让 getter 进一步退场；在那之前禁止恢复模块级 singleton 或导入期实例化
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-09-lifespan-runtime-consolidation-design.md`、`workdocs/归档/正文/设计/2026-03-09-lifespan-runtime-consolidation-phase4-closeout-implementation.md`、`app/services/permission_service.py`、`app/services/result_enrichment_rule_service.py`

### 2026-03-10 run_control_service 收口到 runtime registry

- 状态：ACTIVE
- 决策主题：`RunControlService` 这类跨请求共享、持有可变内存态的 service，不再允许用模块级实例持有状态
- 背景与问题：`run_control_service = RunControlService()` 被 `chat_service` 与 `chat_api` 直接导入使用，导致运行中任务状态藏在模块全局，和 `lifespan -> AppRuntime -> CacheRegistry` 主干形成双 owner
- 最终决策：删除模块级 `run_control_service`；改为 `get_run_control_service()` / `reset_run_control_service()` 走 runtime registry；`chat_service`、`chat_api` 只按需获取共享实例
- 取舍理由：这样能把跨请求共享内存态收回单一 owner，同时不扩大函数签名；相比继续保留模块实例或引入兼容代理，更符合未上线阶段的 lean 收口原则
- 影响范围：`app/services/run_control_service.py`、`app/services/chat_service.py`、`app/api/v1/endpoints/chat_api.py`、`app/core/runtime.py`、相关 run control/chat/API 测试
- 回退/失效条件：若未来引入统一 DI 容器，可让 getter 进一步退场；在那之前禁止恢复模块级 `run_control_service` 或 import 期共享实例绑定
- 关联文档/代码：`workdocs/归档/正文/设计/2026-03-09-lifespan-runtime-consolidation-design.md`、`app/services/run_control_service.py`、`app/services/chat_service.py`、`app/api/v1/endpoints/chat_api.py`
