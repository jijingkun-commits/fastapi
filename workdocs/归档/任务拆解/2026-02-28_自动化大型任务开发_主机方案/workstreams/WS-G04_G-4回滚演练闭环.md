# 工作包说明

> WS 编号: WS-G04
> 名称: G-4 回滚演练闭环
> 类型: gate
> 对应 feature_id: G-4

## 0. 关联与来源

- 对应 task_key: PP-20260228-AUTO-LARGE-TASK-HOST
- 对应 card_id: G04
- 来源主计划: `workdocs/归档/正文/实施计划/自动化大型任务开发_主机方案_implementation_plan.md`
- 来源并行计划: `workdocs/归档/任务拆解/2026-02-28_自动化大型任务开发_主机方案/parallel_plan.md`

## 1. 目标

- 本包目标: G-4 回滚演练闭环 的可执行落地。
- 完成定义（DoD）:
  - 备份恢复演练通过且形成证据记录

### 1.1 功能机制

  - 执行备份->注入故障->恢复->复验闭环演练
  - 验证 30 分钟内可恢复并恢复后可继续推进

### 1.2 代码锚点

  - scripts/coder4_external_backup.sh
  - scripts/coder4_external_restore.sh
  - workdocs/归档/正文/设计/自动化大型任务开发设计方案.md::16.4

- 来源证据:
  - workdocs/归档/正文/实施计划/自动化大型任务开发_全量打钩板清单.md#43-p3-exit-gate必须全绿

## 2. 文件边界

### 可修改（白名单）
  - scripts/coder4_external_backup.sh
  - scripts/coder4_external_restore.sh

### 禁止修改（黑名单）
- 其他 card_id 白名单外文件

## 3. 串行门禁

- 前置卡: G03
- 解锁条件: 前置卡 done_gate 全部通过
- 本 WS 不得推进条件: 前置卡存在 TODO/IN_PROGRESS/BLOCKED

## 4. 测试与验收

- 验收命令:
  - bash scripts/coder4_external_backup.sh

## 5. 风险与回滚

- 回滚锚点:
  - NO_GO_IF_RESTORE_FAIL

## 6. card_export

```yaml
card_export:
  id: WS-G04
  card_id: G04
  feature_ids: ['G-4']
  card_key: PP-20260228-AUTO-LARGE-TASK-HOST::WS-G04
  title: G-4 回滚演练闭环
  type: gate
  task_mode: inspection-card
  merge_required: false
  execution_mode: serial
  hard_depends_on: ['G03']
  depends_on: ['G03']
  file_whitelist:
  - scripts/coder4_external_backup.sh
  - scripts/coder4_external_restore.sh
  mechanism_summary:
  - 执行备份->注入故障->恢复->复验闭环演练
  - 验证 30 分钟内可恢复并恢复后可继续推进
  code_anchor_refs:
  - scripts/coder4_external_backup.sh
  - scripts/coder4_external_restore.sh
  - workdocs/归档/正文/设计/自动化大型任务开发设计方案.md::16.4
  acceptance_checks:
  - bash scripts/coder4_external_backup.sh
  rollback_anchors:
  - NO_GO_IF_RESTORE_FAIL
  evidence_entry: workdocs/归档/正文/实施计划/自动化大型任务开发_全量打钩板清单.md#43-p3-exit-gate必须全绿
  done_gate:
  - 备份恢复演练通过且形成证据记录
```
