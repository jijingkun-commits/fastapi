# 项目记忆（Layer4）

用于记录会影响后续实现的仓库级活跃决策索引。
本文件优先服务 AI/协作者的跨任务记忆，不等同于自动扫描产物，也不承接完整 ADR 正文；需要解释完整背景、决策与后果时，优先写入 `docs/内部参考/决策记录.md` 或对应真理源文档。

## 生效决策索引（ACTIVE 优先，建议最多 20 条）

- 2026-03-14｜Codex 命中项目工作流时默认走 `.agents/skills/*/SKILL.md`，`.cursor/commands/*.md` 只保留作者态真理源与镜像治理职责（ACTIVE）→ `AGENTS.md`、`.cursor/rules/core.mdc`、`docs/README.md`、`docs/项目上下文.md`、`docs/开发文档/流程与工具/Claude-Code上下文监控.md`
- 2026-03-14｜默认搜索面通过仓库根 `.rgignore` 收窄，阅读采用“先命中、再 80~200 行窗口”策略（ACTIVE）→ `.rgignore`、`AGENTS.md`、`.cursor/rules/core.mdc`、`docs/开发文档/流程与工具/Claude-Code上下文监控.md`
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


## 归档入口

- 详细正文已按月归档到 `docs/内部参考/决策归档/`，根文件只保留活跃决策索引。
- 2026-03 详细决策正文：[`docs/内部参考/决策归档/2026-03.md`](docs/内部参考/决策归档/2026-03.md)
- 归档总览：[`docs/内部参考/决策归档/README.md`](docs/内部参考/决策归档/README.md)
