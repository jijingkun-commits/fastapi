# 工作包说明

> WS 编号: WS-C06
> 名称: P2 payload迁移与仓外规则重写
> 类型: parallel
> 对应 feature_id: P2-01

## 0. 关联与来源

- 对应 task_key: PP-20260228-AUTO-LARGE-TASK-HOST
- 对应 card_id: C06
- 来源主计划: `workdocs/归档/正文/实施计划/自动化大型任务开发_主机方案_implementation_plan.md`
- 来源并行计划: `workdocs/归档/任务拆解/2026-02-28_自动化大型任务开发_主机方案/parallel_plan.md`

## 1. 目标

- 本包目标: P2 payload迁移与仓外规则重写 的可执行落地。
- 完成定义（DoD）:
  - 31 项迁移清单全部通过
  - docs_guard 严格校验通过

### 1.1 功能机制

  - 将 3000 字符 payload 拆分迁移到 AGENTS/WORKFLOW/PROMPTS
  - 按 31 项 checklist 做原子级映射校验
  - cron payload 缩减为 watchdog 巡检指令

### 1.2 代码锚点

  - workdocs/归档/正文/设计/自动化大型任务开发设计方案.md::附录 B.4
  - ~/.openclaw/workspace-dev/WORKFLOW_AUTO.md
  - ~/.openclaw/workspace-dev/VK_AGENT_PROMPTS.md

- 来源证据:
  - workdocs/归档/正文/设计/自动化大型任务开发设计方案.md#b4-payload-迁移逐条对照-checklist

## 2. 文件边界

### 可修改（白名单）
  - AGENTS.md
  - workdocs/归档/正文/设计/自动化大型任务开发设计方案.md
  - ~/.openclaw/workspace-dev/WORKFLOW_AUTO.md
  - ~/.openclaw/workspace-dev/VK_AGENT_PROMPTS.md

### 禁止修改（黑名单）
- 其他 card_id 白名单外文件

## 3. 串行门禁

- 前置卡: C05
- 解锁条件: 前置卡 done_gate 全部通过
- 本 WS 不得推进条件: 前置卡存在 TODO/IN_PROGRESS/BLOCKED

## 4. 测试与验收

- 验收命令:
  - python3 scripts/docs_guard.py --strict

## 5. 风险与回滚

- 回滚锚点:
  - scripts/coder4_external_restore.sh

## 6. card_export

```yaml
card_export:
  id: WS-C06
  card_id: C06
  feature_ids: ['P2-01']
  card_key: PP-20260228-AUTO-LARGE-TASK-HOST::WS-C06
  title: P2 payload迁移与仓外规则重写
  type: parallel
  task_mode: implementation-card
  merge_required: false
  execution_mode: serial
  hard_depends_on: ['C05']
  depends_on: ['C05']
  file_whitelist:
  - AGENTS.md
  - workdocs/归档/正文/设计/自动化大型任务开发设计方案.md
  - ~/.openclaw/workspace-dev/WORKFLOW_AUTO.md
  - ~/.openclaw/workspace-dev/VK_AGENT_PROMPTS.md
  mechanism_summary:
  - 将 3000 字符 payload 拆分迁移到 AGENTS/WORKFLOW/PROMPTS
  - 按 31 项 checklist 做原子级映射校验
  - cron payload 缩减为 watchdog 巡检指令
  code_anchor_refs:
  - workdocs/归档/正文/设计/自动化大型任务开发设计方案.md::附录 B.4
  - ~/.openclaw/workspace-dev/WORKFLOW_AUTO.md
  - ~/.openclaw/workspace-dev/VK_AGENT_PROMPTS.md
  acceptance_checks:
  - python3 scripts/docs_guard.py --strict
  rollback_anchors:
  - scripts/coder4_external_restore.sh
  evidence_entry: workdocs/归档/正文/设计/自动化大型任务开发设计方案.md#b4-payload-迁移逐条对照-checklist
  done_gate:
  - 31 项迁移清单全部通过
  - docs_guard 严格校验通过
```
