# verify_report

> 验收时间：2026-03-14
> 验收对象：统一 `research_subagent` 一期实现
> 结论：`WARN`
> 建议下一步：`merge` 前补人工 UAT 烟测；若当前仅以代码/定向自动化为门禁，可带着 `WARN` 进入合并评估

## 1. 上下文校验

### 目标上下文

- 目标 worktree：`/Users/jijingkun/.codex/worktrees/26e5/fastapi`
- 目标任务：`T-01 -> T-06`
- 目标主题：`2026-03-13_research-subagent-phase1`

### 实际上下文

- `pwd`：`/Users/jijingkun/.codex/worktrees/26e5/fastapi`
- `git rev-parse --show-toplevel`：`/Users/jijingkun/.codex/worktrees/26e5/fastapi`
- `git branch --show-current`：`codex/supervisor-subagent`
- `git rev-parse HEAD`：`74cc531eff56b2686cf928ae88d12dad0fc3175d`
- `bash scripts/repo_python.sh`：`/Users/jijingkun/.codex/worktrees/26e5/fastapi/venv/bin/python`

### 比对结论

- worktree：一致
- 任务主题：一致
- 测试解释器：命中仓库解释器，符合 `PLANS.md` 约束
- 放行原因：不存在 `VERIFY_CONTEXT_MISMATCH`

## 2. 需求覆盖情况

| FR | 对应设计 | 对应任务 | 对应 UAT | 自动化证据 | 结论 |
|---|---|---|---|---|---|
| `FR-01` 主会话先按真实目标 planning | `D-01` `D-04` | `T-01` `T-04` | `TC-RS-03` `TC-RS-06` | `test_research_goal_resolver`、`test_multi_agent_streaming_helpers`、文档 rg | PASS |
| `FR-02` simple query 不误升 research | `D-01` `D-03` | `T-01` `T-03` | `TC-RS-01` | `test_research_goal_resolver`、`test_research_dispatch_contract` | PASS |
| `FR-03` 多来源研究进入统一入口 | `D-02` `D-03` | `T-02` `T-03` | `TC-RS-02` | `test_research_subagent`、`test_research_dispatch_contract` | PASS |
| `FR-04` research 返回结构化结果与 insufficiency | `D-02` | `T-02` | `TC-RS-05` | `test_research_subagent`、`test_ragflow_tool`、`test_research_dispatch_contract` | PASS |
| `FR-05` KB 图文展示不退化 | `D-05` | `T-05` | `TC-RS-04` | `test_message_display_blocks`、`test_chat_repo_serialization`、`test_chat_api` | PASS |
| `FR-06` 附件保持 route-agnostic | `D-04` | `T-04` | `TC-RS-03` | `test_multi_agent_streaming_helpers`、`test_chat_service_human_attachment_persistence` | PASS |
| `FR-07` `supervisor` 仍是唯一 owner | `D-03` | `T-03` | `TC-RS-02` `TC-RS-05` | `test_research_dispatch_contract`、文档同步证据 | PASS |

## 3. 设计符合情况

| 设计项 | 验收结论 | 关键证据 |
|---|---|---|
| `D-01-research-goal-bucket` | PASS | `app/ai/intent/goal_resolver.py` 已提供 `research.execute` 与 `research` bucket；`T-01` fresh 通过 |
| `D-02-unified-research-subagent` | PASS | `app/ai/agents/research_subagent.py` 已落统一 executor；payload v2 含 `media_refs` |
| `D-03-supervisor-surface-cleanup` | PASS | Supervisor 仅暴露统一 `research_subagent` + atomic `knowledge_search/search_tool` |
| `D-04-attachment-route-agnostic` | PASS | `attachment_planning` 已按 goal bucket 驱动，不再看 `attachment_count/document_probe` 直切 research |
| `D-05-research-media-preservation` | PASS | research `media_refs -> kb_images -> display_blocks/history` 已贯通 |
| `D-06-doc-sync` | PASS | 总览文档、产品文档、专题架构页、requirements traceability 已对齐 |

## 4. review 结论消费情况

- `review_report.md` 已生成，结论为 `PASS`
- review 中唯一发现是稳定文档平行口径：
  - 原问题：专题页还保留旧的双 research 入口和旧 contract 口径
  - 当前状态：已修复
  - verify 复核结果：问题已关闭，不再构成 `P1/P2`

## 5. 追溯链闭合情况

追溯链现状：

- `requirements.md` 有完整 `traceability_matrix`
- `implementation_plan.md` 为 `T-01 -> T-06` 提供 acceptance_cmds
- `review_report.md` 已消费需求、设计、计划、证据
- `verify_report.md` 已回收 review 结论与 fresh acceptance 结果

结论：

- 代码追溯链：闭合
- 文档追溯链：闭合
- 人工 UAT 追溯链：未在本轮真实执行，只完成了 acceptance_cmd 对齐

## 6. fresh 自动化证据

以下命令已在本次 verify 中 fresh 执行：

1. `bash scripts/pytest_targeted.sh tests/unit/test_research_goal_resolver.py tests/unit/test_intent_layer_boundary.py -q`
   - 结果：`11 passed`
2. `bash scripts/pytest_targeted.sh tests/unit/test_research_subagent.py tests/unit/test_ragflow_tool.py tests/unit/test_research_dispatch_contract.py -q`
   - 结果：`29 passed`
3. `bash scripts/pytest_targeted.sh tests/unit/test_research_dispatch_contract.py tests/unit/test_multi_agent_tool_governance_runtime.py -q`
   - 结果：`6 passed`
4. `bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_streaming_helpers.py tests/unit/test_chat_service_human_attachment_persistence.py -q`
   - 结果：`63 passed`
5. `bash scripts/pytest_targeted.sh tests/unit/test_message_display_blocks.py tests/unit/test_chat_service_done_payload.py tests/unit/test_chat_repo_serialization.py tests/api/test_chat_api.py -q`
   - 结果：`55 passed`
6. `rg -n "research_subagent|knowledge_search|web_research|附件|图文展示" docs/开发文档/架构设计/AI模块设计.md docs/开发文档/架构设计/AI模块设计_跨Agent意图与运行时契约.md docs/开发文档/架构设计/AI模块设计_多智能体与状态契约.md docs/开发文档/架构设计/AI模块设计_待办协作契约.md docs/产品文档/聊天系统需求.md workdocs/需求/2026-03-13_research-subagent-phase1/requirements.md`
   - 结果：命中文档与 requirements 口径一致，未再出现“专题页仍指向旧主 surface”的冲突

## 7. UAT 结果

| UAT | 状态 | 说明 |
|---|---|---|
| `TC-RS-01` | AUTO PASS / MANUAL PENDING | 自动化证据已通过；未在真实知识库环境下做人工对话验收 |
| `TC-RS-02` | AUTO PASS / MANUAL PENDING | research dispatch contract 已通过；未在真实 KB + web 环境下做人工对话验收 |
| `TC-RS-03` | AUTO PASS / MANUAL PENDING | route-agnostic 附件 planning 已通过；未做真实附件上传对话验收 |
| `TC-RS-04` | AUTO PASS / MANUAL PENDING | live/history 图文链路自动化已通过；未做前端录屏验收 |
| `TC-RS-05` | AUTO PASS / MANUAL PENDING | insufficiency 自动化已通过；未做真实弱证据场景的人工体验验收 |
| `TC-RS-06` | PASS | 文档与过程合同已完成人工静态核对 |

## 8. 残余风险

1. 本轮没有执行真实聊天 UI、真实知识库和真实联网搜索的人工作业流，因此 UAT 仍有人工烟测空档。
2. targeted pytest 全绿，但仍有仓库既有 warning：
   - `passlib` 的 `crypt` 弃用 warning
   - 若干 Pydantic V2 deprecation warning
3. 本轮 verify 关注的是一期 `research_subagent` touched scope，不代表全仓回归已完成。

## 9. 最终判断

- 为什么不是 `FAIL`
  - 需求、设计、任务和自动化 acceptance 都已经对上
  - review 中的稳定文档冲突已关闭
  - 没有未关闭的 `P1/P2` 行为或架构问题

- 为什么不是 `PASS`
  - `uat_cases.md` 中要求的多条“真实对话操作 + 历史回放核对 + 录屏/截图”本轮没有实际执行
  - 因此只能确认“自动化与文档追溯通过”，不能假装“人工体验验收也已完成”

## 10. verify_summary

- 结论：`WARN`
- 推荐动作：`merge`
- 前提说明：若团队要求人工 UAT 才能放行，请先补 `TC-RS-01 ~ TC-RS-05` 的真实对话烟测；若当前迭代以代码门禁和定向自动化为主，本次改动已具备进入合并评估的条件。
