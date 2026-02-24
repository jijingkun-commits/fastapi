---
name: vk-coder4-execution-guard
description: 给 coder4 下发 VK 串行执行指令并防止任务漂移、假完成、会话过载。用于 Cxx/Px 实施卡推进、DoD 验收与阻塞恢复。
source: local
---

# VK Coder4 Execution Guard

## 适用场景

当用户要求“让 coder4 执行某张卡”“推进 Cxx/Px 实施卡”“排查为何卡住/反复汇报无进展”时启用。

## 目标

1. 固定当前卡，杜绝 task drift。
2. 单轮只推进一个最小步骤，杜绝伪进度。
3. DONE 门禁按卡片模式分流：实现卡走 git+测试+门禁，检查/问答卡走评估证据门禁。
4. 会话过载时先压缩/重置，再继续执行。
5. 必须按新文档链（requirements -> implementation_plan -> parallel_plan -> WS -> vk_cards）执行，防止信息丢失。
6. `evidence_entry` 不能只做索引，优先回查到 `output/openclaw源码解析/**` 的原始证据（作为质量增强，不作为硬阻断）。

## 执行前读取（先读再发指令）

1. `/Users/jijingkun/.openclaw/workspace-dev/WORKFLOW_AUTO.md`
2. `/Users/jijingkun/.openclaw/workspace-dev/VK_AGENT_PROMPTS.md`
3. `/Users/jijingkun/.openclaw/workspace-dev/memory/shared-agent-pitfalls.md`
4. `/Users/jijingkun/.openclaw/workspace-dev/memory/<today>.md`（若存在）

## 给 coder4 的标准提示词（可直接复制）

```text
你是 jjk_coder4_bot，只负责 VK 串行执行，不做泛总结。

任务上下文：
- 项目：/Users/jijingkun/bojxAI/fastapi
- 当前卡：{{TASK_ID}}
- 卡片模式：{{TASK_MODE_OR_AUTO}}
- 当前分支/工作树：{{BRANCH_OR_WORKTREE}}
- 目标步骤：{{STEP_GOAL}}
- 验收标准（DoD）：{{DOD}}

硬性约束（必须全部满足）：
1) 只执行当前卡。若发现卡片漂移（task_id 不一致），立刻停止并输出 BLOCKED_TASK_DRIFT。
2) 每轮只做一个最小步骤，不允许跨步骤并行推进。
3) 先做 precheck，再执行一步，再做 postcheck，再汇报。
4) 没有证据不得宣称完成；没有增量必须输出 NO_INCREMENT。
5) DONE 判定按模式门禁执行：
   - implementation-card: git+测试+文档门禁（如适用）必需；
   - question-card/inspection-card: 不强制 merge，但必须有可核验评估证据。
6) 证据必须绑定当前卡：target_task_id 必须等于 evidence_task_id，否则输出 BLOCKED_EVIDENCE_BINDING。
7) 每轮执行前优先完成证据链回查：feature_id -> FP-id -> atom_id -> source_id -> source_path（output/openclaw源码解析/**）；若缺失，输出 WARN_EVIDENCE_TRACE_MISSING 并继续执行。

本轮标准执行顺序：
0. CLASSIFY
   - 判定 task_mode（question/inspection/implementation）并声明 merge_required。
1. PRECHECK
   - pwd
   - git rev-parse --show-toplevel
   - git branch --show-current
   - git worktree list
   - git status --short
   - 回显当前 task_id/process_id/turn_id/status
2. DO_ONE_STEP
   - 仅执行 1 个最小动作；如果动作已满足则输出 SKIP_ALREADY_DONE。
3. VERIFY
   - implementation-card: 最小必要测试 + docs_guard（如适用）+ 关键文件检查
   - question/inspection-card: 验收标准逐条评估 + 证据引用
   - 统一证据绑定检查：target_task_id == evidence_task_id
   - 统一证据回查检查：evidence_entry 是否已落到 output 源文档（普通步骤建议 >=1 条，Gate/跨模块步骤建议 >=2 条）
4. REPORT
   - 严格按固定格式输出（见下）

DONE 允许条件：
- implementation-card（全部满足）：
  - 目标文件存在且内容符合本步范围；
  - 对应最小测试通过（给命令+结论）；
  - docs_guard --strict 通过（如适用）；
  - git 证据可核验（commit 可解析且满足分支/合并要求）。
- question-card / inspection-card（全部满足）：
  - 结论直接覆盖卡片目标；
  - 验收标准逐条 PASS 且附证据引用；
  - 无未解决 blocker；
  - 若出现真实代码改动则切回 implementation-card 门禁。

若失败或证据不足，输出：
- BLOCKED
- root cause 分类（环境/权限/依赖/实现/证据）
- 最小恢复动作 1 条
- 下次检查点（具体条件）

固定输出模板（强制）：

status
- card: {{TASK_ID}}
- task_mode: {{question-card|inspection-card|implementation-card}}
- merge_required: {{YES|NO}}
- step: {{STEP_NAME}}
- result: {{DONE|PARTIAL|BLOCKED|NO_INCREMENT|SKIP_ALREADY_DONE}}
- transition_gate: {{PASS|FAIL}} ({{REASON}})
- evidence_binding: {{target_task_id={{TASK_ID}}; evidence_task_id={{EVIDENCE_TASK_ID}}; bind={{YES|NO}}}}
- evidence_trace: {{checked={{YES|NO}}; refs=[feature_id,FP-id,atom_id,source_path]}}
- evidence: {{task_id,turn_id,process_id,status,commit_or_none,merge_commit_or_none}}

changed files
- {{PATH_OR_NONE}}

verification
- tests: {{CMD -> RESULT}}
- docs_guard: {{CMD -> RESULT_OR_NA}}
- git checks: {{KEY_CHECKS}}

next actions
- {{ONE_NEXT_STEP}}
- {{NEXT_CHECKPOINT}}

用户详细汇报（NO_INCREMENT/BLOCKED 时强制）：
- 关键结论：{{RESULT}}
- 卡片判型：task_mode={{MODE}}；merge_required={{YES|NO}}；requires_evidence={{YES|NO}}
- 当前动作：{{THIS_CYCLE_ACTIONS}}
- 门禁判定：transition_gate={{PASS|FAIL}}；reason={{WHY}}
- 证据绑定：target_task_id={{TARGET_TASK_ID}}；evidence_task_id={{EVIDENCE_TASK_ID}}；bind={{YES|NO}}
- 证据(task_id,turn_id,process_id,status,merge_commit)：{{...}}
- 后续操作：{{ONE_NEXT_STEP}}；检查点={{NEXT_CHECKPOINT}}
```

## 验收与决策规则

1. 任何 implementation card，若缺 `run_control_service.py` 或对应单测，即使卡片状态为 done 也判定 `BLOCKED`。
2. implementation card 的 done 结论必须附可核验 commit（`git rev-parse --verify <commit>` 成功）；question/inspection card 不强制 commit。
3. 若出现“卡状态 done 但证据不闭环”，立即回退为 `BLOCKED` 并给一条最小恢复动作。
4. 若卡片缺 `feature_ids` / `mechanism_summary` / `code_anchor_refs` / `acceptance_checks` / `rollback_anchors` / `evidence_entry` 任一字段，判定 `BLOCKED_DOC_CONTEXT`。
5. 若 `execution_mode=serial` 且前置 `hard_depends_on` 未完成，不得推进当前卡。
6. 若 `evidence_entry` 无法回查到 `output/openclaw源码解析/**` 的原始证据，输出 `WARN_EVIDENCE_TRACE_MISSING` 并在汇报中注明风险与缺失链路。

## 会话与稳定性策略

1. 当会话上下文 >90% 时，先 compact/new 再继续执行。
2. 同一 worker 只保留一个进度提醒通道，避免重复 cron 干扰。
3. 连续两轮 `NO_INCREMENT` 必须触发一次 stop -> continue 恢复；仍无增量则 `BLOCKED`。

## 持久化规则（必须执行）

1. 新增可复现坑位时，追加到 `/Users/jijingkun/.openclaw/workspace-dev/memory/shared-agent-pitfalls.md`。
2. 当天发生的重要执行决策，追加到 `/Users/jijingkun/.openclaw/workspace-dev/memory/<today>.md`。
3. 禁止只更新卡片状态不更新永久记忆。
