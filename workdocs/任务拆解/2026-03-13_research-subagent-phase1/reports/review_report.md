# review_report

> 评审时间：2026-03-14
> 评审对象：统一 `research_subagent` 一期实现
> 上游输入：
> - `workdocs/需求/2026-03-13_research-subagent-phase1/requirements.md`
> - `workdocs/设计/2026-03-13_research-subagent-phase1/design.md`
> - `workdocs/任务拆解/2026-03-13_research-subagent-phase1/contracts/implementation_plan.md`
> - `workdocs/任务拆解/2026-03-13_research-subagent-phase1/contracts/uat_cases.md`

## 1. 映射范围

- requirement_ids:
  - `FR-01` `FR-02` `FR-03` `FR-04` `FR-05` `FR-06` `FR-07`
- design_item_refs:
  - `D-01-research-goal-bucket`
  - `D-02-unified-research-subagent`
  - `D-03-supervisor-surface-cleanup`
  - `D-04-attachment-route-agnostic`
  - `D-05-research-media-preservation`
  - `D-06-doc-sync`
- task_ids:
  - `T-01`
  - `T-02`
  - `T-03`
  - `T-04`
  - `T-05`
  - `T-06`

## 2. Findings

### 无未关闭 findings

本轮 review 结束时，没有发现仍然阻断放行的 `P1/P2/P3` 问题。

### 已在 review 阶段关闭的发现

- `P2` 稳定文档平行口径
  - 问题：总览文档已切到“统一 `research_subagent` + atomic tool 保留 + `media_refs` contract”，但三个专题页仍保留“`knowledge_research/web_research` 是主 research 入口、结果合同只有 `summary + evidence + insufficiency`”的旧口径。
  - 为什么重要：`AI模块设计.md` 明确写了“总览与专题正文不一致时，以专题正文为准”。如果不修，这次 `T-06` 的文档同步实际上没有闭环，后续设计/评审会继续被旧口径误导。
  - 对应追溯：`FR-03`、`FR-05`、`FR-07` / `D-06-doc-sync` / `T-06`
  - 处理结果：已在 review 阶段原位修复下列文件，当前无残留 blocker。
    - `docs/开发文档/架构设计/AI模块设计_跨Agent意图与运行时契约.md`
    - `docs/开发文档/架构设计/AI模块设计_多智能体与状态契约.md`
    - `docs/开发文档/架构设计/AI模块设计_待办协作契约.md`

## 3. review_checklist

| 检查项 | 结论 | 说明 |
|---|---|---|
| requirements_conformance | PASS | `research` goal bucket、统一 `research_subagent`、route-agnostic 附件、图文保真、结构化 insufficiency 都已落地 |
| design_conformance | PASS | owner、依赖方向、状态归属、错误收口均与 design 一致 |
| architecture_conformance | PASS | `supervisor` 仍是唯一 owner；research 语义仍在 intent/resolver；未把 `todo/data` agent 化 |
| touched_scope_architecture | PASS | touched scope 的职责更集中，没有把路由/展示/错误收口重新打散 |
| complexity_conformance | PASS | 新增统一 executor 与 payload v2 的同时，删掉了 Supervisor 双入口和附件直切 research 的错误假设 |
| simplification_conformance | PASS | research surface 从双入口收口为单入口；KB 图文仍走 canonical pipeline |
| duplicate_cleanup_conformance | PASS | 旧的 `knowledge_research/web_research` 主 surface 已退役为内部 provider/helper，不再并行暴露 |
| evidence_conformance | PASS | 对应 acceptance_cmds 与 doc rg 证据已齐，且命中了仓库解释器 |

## 4. architecture_review

### 模块边界

- 结论：边界比改动前清晰。
- 证据：
  - `research` 语义出口固定在 `app/ai/intent/goal_resolver.py`
  - `research_subagent` 成为统一 research executor
  - `knowledge_search/search_tool` 保留 atomic tool
  - `todo/data` 继续保留 workflow

### 依赖方向

- 结论：依赖方向符合设计冻结。
- 证据：
  - `intent/goal_resolver -> supervisor planning -> research_subagent -> source provider -> deliverable -> display_blocks/history`
  - `attachment_planning` 只消费 goal bucket，不再反向定义 research 语义

### 状态归属

- 结论：主会话状态仍由 `supervisor` 单一持有。
- 证据：
  - `research_subagent` 只返回单次结构化 payload
  - `display_blocks / kb_images` 仍是最终展示 canonical owner

### 错误处理责任

- 结论：错误收口位置正确。
- 证据：
  - research 失败返回结构化 `insufficiency`
  - KB 图片失败时仍保文本与证据
  - 未出现把原始网页噪声直接透给最终用户的实现路径

## 5. slimming_review

### 正向收口

- `Supervisor` research surface 已从双入口收口到统一 `research_subagent`
- 附件 route 不再因为 `attachment_count/document_probe` 默认 research
- research payload 已扩成可携带 `media_refs` 的统一合同
- 历史持久化不再只依赖 `<!--KB_IMAGES:...-->` 单一路径

### 删除完成情况

- 已完成：
  - “Supervisor 直连 `knowledge_research/web_research` 作为主 research surface” 的职责收口
  - “多附件/文档探针直接 research” 的 planning 旧假设收口
  - “research 只能回纯文本摘要” 的展示旧假设收口
- 可接受保留：
  - `knowledge_research/web_research` 作为内部 provider/helper 仍保留，符合 design 明确允许的兼容边界

## 6. review_summary

- 结论：`PASS`
- 说明：代码实现没有发现未关闭的行为或结构性问题；review 中唯一发现的稳定文档平行口径已当场修复，当前可以进入 `$jjk-verify`。
