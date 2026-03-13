# 工作包说明

> WS 编号: WS-C05
> 名称: P1 attempt与ledger本地化
> 类型: parallel
> 对应 feature_id: P1-04

## 0. 关联与来源

- 对应 task_key: PP-20260228-AUTO-LARGE-TASK-HOST
- 对应 card_id: C05
- 来源主计划: `workdocs/归档/正文/实施计划/自动化大型任务开发_主机方案_implementation_plan.md`
- 来源并行计划: `workdocs/归档/任务拆解/2026-02-28_自动化大型任务开发_主机方案/parallel_plan.md`

## 1. 目标

- 本包目标: P1 attempt与ledger本地化 的可执行落地。
- 完成定义（DoD）:
  - attempt 与 ledger 均可追溯
  - 单卡至少生成一条可核验证据记录

### 1.1 功能机制

  - 每轮执行将 gate/merge 证据内联写入 task-runner-state
  - ledger 追加写入完整推进证据
  - 证据按 task_key/card_id 键归档并可按窗口清理

### 1.2 代码锚点

  - scripts/coder4/coder4_bootstrap_kernel.py::record_attempt_evidence
  - scripts/coder4/coder4_bootstrap_kernel.py::advance_card
  - .artifacts/states/task_splits/2026-02-28_自动化大型任务开发_主机方案/<task_key>/task-ledger.jsonl

- 来源证据:
  - workdocs/归档/正文/设计/自动化大型任务开发设计方案.md#72-attempt-json-schema

## 2. 文件边界

### 可修改（白名单）
  - .artifacts/states/task_splits/2026-02-28_自动化大型任务开发_主机方案/<task_key>/task-runner-state.json
  - .artifacts/states/task_splits/2026-02-28_自动化大型任务开发_主机方案/<task_key>/task-ledger.jsonl

### 禁止修改（黑名单）
- 其他 card_id 白名单外文件

## 3. 串行门禁

- 前置卡: C04
- 解锁条件: 前置卡 done_gate 全部通过
- 本 WS 不得推进条件: 前置卡存在 TODO/IN_PROGRESS/BLOCKED

## 4. 测试与验收

- 验收命令:
  - test -f .artifacts/states/task_splits/2026-02-28_自动化大型任务开发_主机方案/<task_key>/task-runner-state.json || true
  - test -f .artifacts/states/task_splits/2026-02-28_自动化大型任务开发_主机方案/<task_key>/task-ledger.jsonl || true

## 5. 风险与回滚

- 回滚锚点:
  - restore_attempts_archive

## 6. card_export

```yaml
card_export:
  id: WS-C05
  card_id: C05
  feature_ids: ['P1-04']
  card_key: PP-20260228-AUTO-LARGE-TASK-HOST::WS-C05
  title: P1 attempt与ledger本地化
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  hard_depends_on: ['C04']
  depends_on: ['C04']
  file_whitelist:
  - .artifacts/states/task_splits/2026-02-28_自动化大型任务开发_主机方案/<task_key>/task-runner-state.json
  - .artifacts/states/task_splits/2026-02-28_自动化大型任务开发_主机方案/<task_key>/task-ledger.jsonl
  mechanism_summary:
  - 每轮执行将 gate/merge 证据内联写入 task-runner-state
  - ledger 追加写入完整推进证据
  - 证据按 task_key/card_id 键归档并可按窗口清理
  code_anchor_refs:
  - scripts/coder4/coder4_bootstrap_kernel.py::record_attempt_evidence
  - scripts/coder4/coder4_bootstrap_kernel.py::advance_card
  - .artifacts/states/task_splits/2026-02-28_自动化大型任务开发_主机方案/<task_key>/task-ledger.jsonl
  acceptance_checks:
  - test -f .artifacts/states/task_splits/2026-02-28_自动化大型任务开发_主机方案/<task_key>/task-runner-state.json || true
  - test -f .artifacts/states/task_splits/2026-02-28_自动化大型任务开发_主机方案/<task_key>/task-ledger.jsonl || true
  rollback_anchors:
  - restore_attempts_archive
  evidence_entry: workdocs/归档/正文/实施计划/自动化大型任务开发_主机方案_implementation_plan.md#p1-04-attemptledger-本地化
  done_gate:
  - 内联证据与 ledger 均可追溯
  - 单卡至少生成一条可核验证据记录
```
