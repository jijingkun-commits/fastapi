# 工作包说明

> WS 编号: WS-G01
> 名称: G-1 安全门禁闭环
> 类型: gate
> 对应 feature_id: G-1

## 0. 关联与来源

- 对应 task_key: PP-20260228-AUTO-LARGE-TASK-HOST
- 对应 card_id: G01
- 来源主计划: `workdocs/归档/实施计划/自动化大型任务开发_主机方案_implementation_plan.md`
- 来源并行计划: `workdocs/归档/任务拆解/2026-02-28_自动化大型任务开发_主机方案/parallel_plan.md`

## 1. 目标

- 本包目标: G-1 安全门禁闭环 的可执行落地。
- 完成定义（DoD）:
  - G-01~G-03 安全门禁全部 PASS

### 1.1 功能机制

  - 汇总 hooks token/监听地址/进程权限安全门禁
  - 任一安全项失败直接 No-Go

### 1.2 代码锚点

  - workdocs/归档/设计/自动化大型任务开发设计方案.md::17.2
  - workdocs/归档/实施计划/自动化大型任务开发_全量打钩板清单.md::1.4

- 来源证据:
  - workdocs/归档/设计/自动化大型任务开发设计方案.md#17-上线门禁清单gono-go

## 2. 文件边界

### 可修改（白名单）
  - workdocs/归档/实施计划/自动化大型任务开发_全量打钩板清单.md

### 禁止修改（黑名单）
- 其他 card_id 白名单外文件

## 3. 串行门禁

- 前置卡: C07
- 解锁条件: 前置卡 done_gate 全部通过
- 本 WS 不得推进条件: 前置卡存在 TODO/IN_PROGRESS/BLOCKED

## 4. 测试与验收

- 验收命令:
  - python3 scripts/docs_guard.py --strict

## 5. 风险与回滚

- 回滚锚点:
  - NO_GO_IF_SECURITY_FAIL

## 6. card_export

```yaml
card_export:
  id: WS-G01
  card_id: G01
  feature_ids: ['G-1']
  card_key: PP-20260228-AUTO-LARGE-TASK-HOST::WS-G01
  title: G-1 安全门禁闭环
  type: gate
  task_mode: inspection-card
  merge_required: false
  execution_mode: serial
  hard_depends_on: ['C07']
  depends_on: ['C07']
  file_whitelist:
  - workdocs/归档/实施计划/自动化大型任务开发_全量打钩板清单.md
  mechanism_summary:
  - 汇总 hooks token/监听地址/进程权限安全门禁
  - 任一安全项失败直接 No-Go
  code_anchor_refs:
  - workdocs/归档/设计/自动化大型任务开发设计方案.md::17.2
  - workdocs/归档/实施计划/自动化大型任务开发_全量打钩板清单.md::1.4
  acceptance_checks:
  - python3 scripts/docs_guard.py --strict
  rollback_anchors:
  - NO_GO_IF_SECURITY_FAIL
  evidence_entry: workdocs/归档/实施计划/自动化大型任务开发_全量打钩板清单.md#1-p0-打钩板触发器切换--主机安全基线
  done_gate:
  - G-01~G-03 安全门禁全部 PASS
```
