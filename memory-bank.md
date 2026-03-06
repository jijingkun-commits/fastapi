# 项目记忆（Layer4）

用于记录会影响后续实现的历史决策。  
本文件是“人工决策记录”，不等同于自动扫描产物。

## 生效决策索引（ACTIVE 优先，建议最多 20 条）
- 2026-03-05｜规则分层落地（ACTIVE）→ `AGENTS.md`
- 2026-03-06｜复合提问多模态响应契约收敛（ACTIVE）→ `docs/plans/2026-03-06-composite-query-multimodal-response-design.md`

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
